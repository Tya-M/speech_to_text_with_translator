"""
CPU-only faster-whisper recognizer.
"""

import importlib.util
import logging
from pathlib import Path
from typing import Generator, Optional

import numpy as np

from .base import BaseRecognizer
from .whisper_engine import HallucinationFilter
from utils.threading_utils import RecognitionResult
from utils.config import RecognitionConfig

logger = logging.getLogger("voice_translator.recognition.faster_whisper")

FASTER_WHISPER_AVAILABLE = importlib.util.find_spec("faster_whisper") is not None


class FasterWhisperRecognizer(BaseRecognizer):
    """faster-whisper recognizer forced to CPU int8 by default."""

    def __init__(
        self,
        config: RecognitionConfig,
        model_name: str = "small",
        cache_dir: str = "models/faster-whisper",
        compute_type: str = "int8",
    ):
        super().__init__(config)
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self.compute_type = compute_type
        self._model = None
        self._buffer = bytearray()
        self._filter = HallucinationFilter()
        self._model_name = f"faster-whisper {model_name} CPU"

    def load(self) -> bool:
        """Loads faster-whisper on CPU only."""
        if not FASTER_WHISPER_AVAILABLE:
            logger.error("faster-whisper недоступен. Используйте: pip install faster-whisper")
            return False

        if self._is_loaded:
            logger.debug("faster-whisper модель уже загружена")
            return True

        try:
            from faster_whisper import WhisperModel

            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(
                "Загрузка faster-whisper CPU модели: %s, compute_type=%s",
                self.model_name,
                self.compute_type,
            )
            self._model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type=self.compute_type,
                download_root=str(self.cache_dir),
            )
            self._is_loaded = True
            logger.info("faster-whisper CPU модель загружена успешно")
            return True
        except Exception as e:
            logger.error("Ошибка загрузки faster-whisper CPU: %s", e)
            self._model = None
            self._is_loaded = False
            return False

    def unload(self) -> None:
        """Unloads the model and clears buffered audio."""
        self._model = None
        self._buffer.clear()
        self._is_loaded = False
        logger.info("faster-whisper CPU модель выгружена")

    def recognize(self, audio_data: bytes) -> Optional[RecognitionResult]:
        """Transcribes a PCM16 mono 16 kHz chunk."""
        if not self._is_loaded or self._model is None:
            logger.error("faster-whisper CPU не загружен")
            return None

        audio_f32 = self._pcm16_to_float32(audio_data)
        if audio_f32.size == 0:
            return None

        try:
            segments, _info = self._model.transcribe(
                audio_f32,
                language=self._language,
                vad_filter=True,
            )
            text = self._filter.clean(" ".join(segment.text.strip() for segment in segments))
            if not text:
                return None

            return RecognitionResult(
                text=text,
                is_final=True,
                confidence=0.0,
                engine="faster-whisper (CPU)",
            )
        except Exception as e:
            logger.error("Ошибка распознавания faster-whisper CPU: %s", e)
            return None

    def recognize_stream(self, audio_chunk: bytes) -> Generator[RecognitionResult, None, None]:
        """Buffers live audio and transcribes complete chunk-duration windows."""
        if not self._is_loaded or self._model is None:
            logger.error("faster-whisper CPU не загружен")
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

    @property
    def _language(self) -> str:
        return str(getattr(self.config, "whisper_language", "ru") or "ru")

    def _is_silence(self, audio_data: bytes) -> bool:
        samples = np.frombuffer(audio_data, np.int16).astype(np.int32)
        if samples.size == 0:
            return True
        return float(np.max(np.abs(samples))) < float(self.config.vad_threshold)

    @staticmethod
    def _pcm16_to_float32(audio_data: bytes) -> np.ndarray:
        return np.frombuffer(audio_data, np.int16).astype(np.float32) / 32768.0
