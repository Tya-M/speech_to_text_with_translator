"""
CPU-only openai-whisper recognizer.
"""

import importlib.util
import logging
import re
from pathlib import Path
from typing import Generator, Optional

import numpy as np

from .base import BaseRecognizer
from utils.threading_utils import RecognitionResult
from utils.config import RecognitionConfig

logger = logging.getLogger("voice_translator.recognition.whisper")

WHISPER_AVAILABLE = importlib.util.find_spec("whisper") is not None


class HallucinationFilter:
    """Lightweight filter for common Whisper filler/hallucination outputs."""

    _KNOWN_PHRASES = {
        "редактор субтитров",
        "субтитры создавал",
        "субтитры сделал",
        "спасибо за просмотр",
        "продолжение следует",
    }
    _FILLER_WORDS = {"а", "ага", "да", "угу", "мм", "м", "эм", "ээ", "ну"}

    def is_hallucination(self, text: str) -> bool:
        normalized = self._normalize(text)
        if not normalized:
            return True

        if normalized in self._KNOWN_PHRASES:
            return True

        words = normalized.split()
        if len(words) >= 5 and len(set(words)) == 1:
            return True

        return bool(words) and all(word in self._FILLER_WORDS for word in words)

    def clean(self, text: str) -> str:
        text = text.strip()
        if self.is_hallucination(text):
            return ""
        return text

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.strip().lower().replace("ё", "е")
        text = re.sub(r"[^\w\s]+", " ", text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", text).strip()


class WhisperRecognizer(BaseRecognizer):
    """openai-whisper recognizer forced to CPU."""

    def __init__(
        self,
        config: RecognitionConfig,
        model_name: str = "small",
        cache_dir: str = "models/whisper",
    ):
        super().__init__(config)
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self._model = None
        self._buffer = bytearray()
        self._filter = HallucinationFilter()
        self._model_name = f"Whisper {model_name} CPU"

    def load(self) -> bool:
        """Loads openai-whisper on CPU only."""
        if not WHISPER_AVAILABLE:
            logger.error("openai-whisper недоступен. Используйте: pip install openai-whisper")
            return False

        if self._is_loaded:
            logger.debug("Whisper модель уже загружена")
            return True

        try:
            import whisper

            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Загрузка Whisper CPU модели: %s", self.model_name)
            self._model = whisper.load_model(
                self.model_name,
                device="cpu",
                download_root=str(self.cache_dir),
            )
            self._is_loaded = True
            logger.info("Whisper CPU модель загружена успешно")
            return True
        except Exception as e:
            logger.error("Ошибка загрузки Whisper CPU: %s", e)
            self._model = None
            self._is_loaded = False
            return False

    def unload(self) -> None:
        """Unloads the model and clears buffered audio."""
        self._model = None
        self._buffer.clear()
        self._is_loaded = False
        logger.info("Whisper CPU модель выгружена")

    def recognize(self, audio_data: bytes) -> Optional[RecognitionResult]:
        """Transcribes a PCM16 mono 16 kHz chunk."""
        if not self._is_loaded or self._model is None:
            logger.error("Whisper CPU не загружен")
            return None

        audio_f32 = self._pcm16_to_float32(audio_data)
        if audio_f32.size == 0:
            return None

        try:
            result = self._model.transcribe(
                audio_f32,
                language=self._language,
                fp16=False,
            )
            text = self._filter.clean(result.get("text", ""))
            if not text:
                return None

            return RecognitionResult(
                text=text,
                is_final=True,
                confidence=0.0,
                engine="whisper (CPU)",
            )
        except Exception as e:
            logger.error("Ошибка распознавания Whisper CPU: %s", e)
            return None

    def recognize_stream(self, audio_chunk: bytes) -> Generator[RecognitionResult, None, None]:
        """Buffers live audio and transcribes complete chunk-duration windows."""
        if not self._is_loaded or self._model is None:
            logger.error("Whisper CPU не загружен")
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
