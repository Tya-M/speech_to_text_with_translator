"""
Optional whisper.cpp recognizer using pywhispercpp.

This is the only planned GPU path for the target Intel macOS + AMD RX 580
machine. GPU use is reported only when runtime initialization output confirms
Metal and the expected AMD device.
"""

import importlib.util
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Generator, Optional

import numpy as np

from .base import BaseRecognizer
from .whisper_engine import HallucinationFilter
from utils.config import RecognitionConfig
from utils.threading_utils import RecognitionResult

logger = logging.getLogger("voice_translator.recognition.whispercpp")

try:
    if importlib.util.find_spec("pywhispercpp") is None:
        raise ImportError("pywhispercpp is not installed")
    from pywhispercpp.model import Model as WhisperCppModel
except Exception as e:
    WhisperCppModel = None
    WHISPER_CPP_AVAILABLE = False
    WHISPER_CPP_IMPORT_ERROR = e
else:
    WHISPER_CPP_AVAILABLE = True
    WHISPER_CPP_IMPORT_ERROR = None


class WhisperCppRecognizer(BaseRecognizer):
    """whisper.cpp recognizer with Metal verification and CPU fallback."""

    METAL_MARKERS = ("ggml_metal", "metal")
    AMD_DEVICE_MARKERS = ("AMD Radeon RX 580", "Radeon RX 580", "RX 580")
    ENGLISH_FILLER_WORDS = {
        "the",
        "you",
        "yeah",
        "yes",
        "no",
        "ok",
        "okay",
        "uh",
        "um",
        "hmm",
        "music",
        "blurgy",
        "blurry",
    }
    ENGLISH_FILLER_PHRASES = {
        "thank you",
        "thanks",
        "thanks for watching",
        "subscribe",
    }
    RUSSIAN_NOISE_PHRASES = {
        "смотрите на видео",
        "спокойная музыка",
        "музыка",
        "смех",
        "смешка",
        "аплодисменты",
        "субтитры",
    }
    NON_RUSSIAN_SCRIPT_RE = re.compile(
        r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]"
    )

    def __init__(
        self,
        config: RecognitionConfig,
        model_name: str = "small",
        model_dir: str = "models/whisper-cpp",
        use_gpu: bool = True,
        language: str = "ru",
    ):
        super().__init__(config)
        self.model_name = model_name
        self.model_dir = Path(model_dir)
        self.use_gpu = bool(use_gpu)
        self.language = language or "ru"
        self.gpu_active = False
        self.init_log = ""
        self._model = None
        self._buffer = bytearray()
        self._filter = HallucinationFilter()
        self._model_name = f"whisper.cpp {model_name}"

    def load(self) -> bool:
        """Loads pywhispercpp and records whether Metal/RX 580 initialized."""
        if not WHISPER_CPP_AVAILABLE:
            logger.error(
                "pywhispercpp недоступен. Соберите/установите pywhispercpp с Metal: %s",
                WHISPER_CPP_IMPORT_ERROR,
            )
            return False

        if self._is_loaded:
            logger.debug("whisper.cpp модель уже загружена")
            return True

        log_path = self._init_log_path()
        try:
            self.model_dir.mkdir(parents=True, exist_ok=True)
            self._model = self._create_model(use_gpu=self.use_gpu, log_path=log_path)

            self.init_log = self._read_init_log(log_path)
            self.gpu_active = self._detect_metal_gpu(self.init_log)
            if self.use_gpu and not self.gpu_active:
                logger.warning(
                    "whisper.cpp loaded, but AMD RX 580 Metal initialization was not verified; using CPU label"
                )
            elif self.gpu_active:
                logger.info("whisper.cpp Metal GPU verified from runtime init output")

            self._is_loaded = True
            return True
        except Exception as e:
            if not self.use_gpu:
                self.init_log = self._read_init_log(log_path)
                logger.error("Ошибка загрузки whisper.cpp CPU: %s", e)
                self._model = None
                self._is_loaded = False
                self.gpu_active = False
                return False

            self.init_log = self._read_init_log(log_path)
            logger.warning("Ошибка загрузки whisper.cpp с GPU, повтор CPU: %s", e)
            return self._load_cpu_fallback()

    def unload(self) -> None:
        """Unloads the model and clears buffered audio."""
        self._model = None
        self._buffer.clear()
        self._is_loaded = False
        self.gpu_active = False
        logger.info("whisper.cpp модель выгружена")

    def recognize(self, audio_data: bytes) -> Optional[RecognitionResult]:
        """Transcribes a PCM16 mono 16 kHz chunk."""
        if not self._is_loaded or self._model is None:
            logger.error("whisper.cpp не загружен")
            return None

        audio_f32 = self._pcm16_to_float32(audio_data)
        if audio_f32.size == 0:
            return None

        try:
            segments = self._model.transcribe(audio_f32, **self._decode_params())
            text = self._clean_text(self._segments_to_text(segments))
            if not text:
                return None

            return RecognitionResult(
                text=text,
                is_final=True,
                confidence=0.0,
                engine="whisper.cpp (Metal)" if self.gpu_active else "whisper.cpp (CPU)",
            )
        except Exception as e:
            logger.error("Ошибка распознавания whisper.cpp: %s", e)
            return None

    def recognize_stream(self, audio_chunk: bytes) -> Generator[RecognitionResult, None, None]:
        """Buffers live audio and transcribes complete chunk-duration windows."""
        if not self._is_loaded or self._model is None:
            logger.error("whisper.cpp не загружен")
            return

        self._buffer.extend(audio_chunk)
        target_bytes = int(self.config.sample_rate * self.config.chunk_duration * 2)
        if len(self._buffer) < target_bytes:
            return

        chunk = bytes(self._buffer[:target_bytes])
        del self._buffer[:target_bytes]

        if self._is_silence(chunk):
            return

        result = self.recognize(chunk)
        if result:
            yield result

    def reset(self) -> None:
        """Clears buffered stream audio."""
        self._buffer.clear()

    def _load_cpu_fallback(self) -> bool:
        log_path = self._init_log_path()
        try:
            self._model = self._create_model(use_gpu=False, log_path=log_path)
            self.init_log = self._read_init_log(log_path)
            self.gpu_active = False
            self._is_loaded = True
            logger.info("whisper.cpp загружен в CPU fallback режиме")
            return True
        except Exception as e:
            self.init_log = self._read_init_log(log_path)
            logger.error("Ошибка CPU fallback whisper.cpp: %s", e)
            self._model = None
            self._is_loaded = False
            self.gpu_active = False
            return False

    def _create_model(self, use_gpu: bool, log_path: str):
        return WhisperCppModel(
            self._model_path(),
            models_dir=str(self.model_dir),
            redirect_whispercpp_logs_to=log_path,
            context_params={"use_gpu": use_gpu},
            n_threads=self._thread_count(),
            **self._decode_params(),
        )

    def _model_path(self) -> str:
        direct = Path(self.model_name).expanduser()
        if direct.is_file():
            return str(direct)

        local_names = [self.model_name]
        if not self.model_name.startswith("ggml-"):
            local_names.insert(0, f"ggml-{self.model_name}.bin")
        elif not self.model_name.endswith(".bin"):
            local_names.insert(0, f"{self.model_name}.bin")

        for name in local_names:
            candidate = self.model_dir / name
            if candidate.is_file():
                return str(candidate)

        from pywhispercpp.utils import resolve_model_path

        return resolve_model_path(self.model_name, str(self.model_dir))

    def _decode_params(self) -> dict[str, object]:
        return {
            "language": self.language,
            "translate": False,
            "no_context": True,
            "no_timestamps": True,
            "single_segment": True,
            "print_progress": False,
            "print_realtime": False,
            "print_timestamps": False,
            "suppress_blank": True,
            "suppress_nst": True,
            "temperature": 0.0,
            "temperature_inc": 0.0,
        }

    @staticmethod
    def _thread_count() -> int:
        for name in ("WHISPER_CPP_THREADS", "OMP_NUM_THREADS"):
            value = os.environ.get(name)
            if not value:
                continue
            try:
                threads = int(value)
            except ValueError:
                continue
            if threads > 0:
                return threads
        return min(4, os.cpu_count() or 1)

    def _clean_text(self, text: str) -> str:
        text = self._filter.clean(text)
        if (
            not text
            or self._is_missing_required_script(text)
            or self._is_english_filler(text)
            or self._is_russian_noise_cue(text)
            or self._is_garbled_mixed_script(text)
        ):
            return ""
        return text

    def _is_missing_required_script(self, text: str) -> bool:
        if self.language.lower() != "ru":
            return False
        return re.search(r"[а-яё]", text, flags=re.IGNORECASE) is None

    @classmethod
    def _is_russian_noise_cue(cls, text: str) -> bool:
        normalized = cls._normalize_words(text)
        return normalized in cls.RUSSIAN_NOISE_PHRASES

    @classmethod
    def _is_garbled_mixed_script(cls, text: str) -> bool:
        if "�" in text:
            return True
        if cls.NON_RUSSIAN_SCRIPT_RE.search(text):
            return True

        cyrillic = len(re.findall(r"[а-яё]", text, flags=re.IGNORECASE))
        latin = len(re.findall(r"[a-z]", text, flags=re.IGNORECASE))
        if cyrillic == 0:
            return False
        return latin >= 8 and latin > cyrillic * 2

    @classmethod
    def _is_english_filler(cls, text: str) -> bool:
        if re.search(r"[а-яё]", text, flags=re.IGNORECASE):
            return False

        normalized = cls._normalize_words(text, alphabet=r"a-zA-Z")
        if not normalized:
            return True

        if normalized in cls.ENGLISH_FILLER_PHRASES:
            return True

        words = normalized.split()
        if words and words[0] in {"blurgy", "blurry"}:
            return True
        if len(words) >= 3 and len(set(words)) == 1:
            return True
        return bool(words) and all(word in cls.ENGLISH_FILLER_WORDS for word in words)

    @staticmethod
    def _normalize_words(text: str, alphabet: str = r"\w") -> str:
        text = text.strip().lower().replace("ё", "е")
        text = re.sub(rf"[^{alphabet}\s]+", " ", text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def _detect_metal_gpu(cls, init_log: str) -> bool:
        normalized = init_log.lower()
        has_metal = any(marker.lower() in normalized for marker in cls.METAL_MARKERS)
        has_amd_rx580 = any(marker.lower() in normalized for marker in cls.AMD_DEVICE_MARKERS)
        return has_metal and has_amd_rx580

    def _is_silence(self, audio_data: bytes) -> bool:
        samples = np.frombuffer(audio_data, np.int16).astype(np.int32)
        if samples.size == 0:
            return True
        return float(np.max(np.abs(samples))) < float(self.config.vad_threshold)

    @staticmethod
    def _pcm16_to_float32(audio_data: bytes) -> np.ndarray:
        return np.frombuffer(audio_data, np.int16).astype(np.float32) / 32768.0

    @staticmethod
    def _segments_to_text(segments) -> str:
        parts = []
        for segment in segments or []:
            text = getattr(segment, "text", segment)
            if text is not None:
                parts.append(str(text).strip())
        return " ".join(part for part in parts if part)

    @staticmethod
    def _init_log_path() -> str:
        handle = tempfile.NamedTemporaryFile(prefix="whispercpp-init-", suffix=".log", delete=False)
        path = handle.name
        handle.close()
        return path

    @staticmethod
    def _read_init_log(path: str) -> str:
        try:
            return Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        finally:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass
