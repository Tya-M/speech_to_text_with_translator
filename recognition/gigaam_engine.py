"""
GigaAM recognizer (SberDevices) для офлайн-распознавания русской речи.

Использует официальный пакет ``gigaam`` (https://github.com/salute-developers/GigaAM):

    import gigaam
    model = gigaam.load_model("v3_e2e_rnnt")
    text = model.transcribe(audio_path)

Особенности, подтверждённые документацией GigaAM:
- ``model.transcribe`` принимает путь к аудиофайлу и рассчитан на записи
  длиной до ~25 секунд, что согласуется с потоковой схемой приложения
  (chunk_duration ограничен 10 с).
- модели ``v3_e2e_ctc`` / ``v3_e2e_rnnt`` возвращают текст с пунктуацией
  и нормализацией (end-to-end).
- требуется ffmpeg в PATH; PyTorch/torchaudio устанавливаются как зависимости gigaam.

Первый запуск скачивает веса модели с Hugging Face; далее работает офлайн.
"""

import importlib.util
import logging
import os
import tempfile
import wave
from typing import Generator, Optional

import numpy as np

from .base import BaseRecognizer
from .filters import HallucinationFilter
from utils.threading_utils import RecognitionResult
from utils.config import RecognitionConfig

logger = logging.getLogger("voice_translator.recognition.gigaam")

GIGAAM_AVAILABLE = importlib.util.find_spec("gigaam") is not None


class GigaAMRecognizer(BaseRecognizer):
    """GigaAM ASR recognizer (русский язык, офлайн после первой загрузки модели)."""

    def __init__(
        self,
        config: RecognitionConfig,
        model_name: str = "v3_e2e_rnnt",
        device: str = "cpu",
        language: str = "ru",
    ):
        super().__init__(config)
        self.model_name = model_name
        self.device = (device or "cpu").strip().lower()
        self.language = (language or "ru").strip().lower()
        self._model = None
        self._buffer = bytearray()
        self._filter = HallucinationFilter()
        self._model_name = f"GigaAM {model_name}"

    def load(self) -> bool:
        """Загружает модель GigaAM через gigaam.load_model."""
        if not GIGAAM_AVAILABLE:
            logger.error(
                "gigaam недоступен. Установите пакет (и ffmpeg): "
                "pip install 'gigaam @ git+https://github.com/salute-developers/GigaAM.git'"
            )
            return False

        if self._is_loaded:
            logger.debug("GigaAM модель уже загружена")
            return True

        try:
            import gigaam

            logger.info("Загрузка GigaAM модели: %s (device=%s)", self.model_name, self.device)
            self._model = self._load_model(gigaam)
            self._is_loaded = True
            logger.info("GigaAM модель загружена успешно")
            return True
        except Exception as e:
            logger.error("Ошибка загрузки GigaAM: %s", e)
            self._model = None
            self._is_loaded = False
            return False

    def _load_model(self, gigaam):
        """Загружает модель, учитывая device и совместимость сигнатуры load_model."""
        if self.device == "auto":
            return gigaam.load_model(self.model_name)
        try:
            return gigaam.load_model(self.model_name, device=self.device)
        except TypeError:
            # Старые сборки gigaam могут не принимать аргумент device.
            logger.warning(
                "gigaam.load_model не принимает device=, загружаем с настройками по умолчанию"
            )
            return gigaam.load_model(self.model_name)

    def unload(self) -> None:
        """Выгружает модель и очищает буфер."""
        self._model = None
        self._buffer.clear()
        self._is_loaded = False
        logger.info("GigaAM модель выгружена")

    def recognize(self, audio_data: bytes) -> Optional[RecognitionResult]:
        """Распознаёт PCM16 mono 16 кГц чанк через временный WAV-файл."""
        if not self._is_loaded or self._model is None:
            logger.error("GigaAM не загружен")
            return None

        if not audio_data:
            return None

        tmp_path = None
        try:
            tmp_path = self._write_temp_wav(audio_data)
            raw = self._model.transcribe(tmp_path)
            text = self._filter.clean(self._extract_text(raw))
            if not text:
                return None

            return RecognitionResult(
                text=text,
                is_final=True,
                confidence=0.0,
                engine="gigaam",
            )
        except Exception as e:
            logger.error("Ошибка распознавания GigaAM: %s", e)
            return None
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def recognize_stream(self, audio_chunk: bytes) -> Generator[RecognitionResult, None, None]:
        """Буферизует живой звук и распознаёт полные окна длиной chunk_duration."""
        if not self._is_loaded or self._model is None:
            logger.error("GigaAM не загружен")
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
        """Очищает буфер потокового звука."""
        self._buffer.clear()

    def _write_temp_wav(self, audio_data: bytes) -> str:
        """Пишет PCM16 mono во временный WAV-файл для model.transcribe(path)."""
        fd, path = tempfile.mkstemp(suffix=".wav", prefix="gigaam_")
        os.close(fd)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # PCM16 = 2 байта
            wf.setframerate(int(self.config.sample_rate))
            wf.writeframes(audio_data)
        return path

    @staticmethod
    def _extract_text(raw) -> str:
        """Извлекает строку из результата transcribe (str или объект с .text)."""
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw
        text = getattr(raw, "text", None)
        if isinstance(text, str):
            return text
        return str(raw)

    def _is_silence(self, audio_data: bytes) -> bool:
        samples = np.frombuffer(audio_data, np.int16).astype(np.int32)
        if samples.size == 0:
            return True
        return float(np.max(np.abs(samples))) < float(self.config.vad_threshold)
