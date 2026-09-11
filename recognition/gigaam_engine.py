"""
GigaAM recognizer (SberDevices) для офлайн-распознавания русской речи.

Использует официальный пакет ``gigaam`` (https://github.com/salute-developers/GigaAM):

    import gigaam
    model = gigaam.load_model("v3_e2e_rnnt")
    text = model.transcribe(audio_path)

ВАЖНО про потоковый режим:
GigaAM — НЕ потоковая модель, а распознаватель целых высказываний (до ~25 с).
Поэтому живой звук сегментируется по паузам (VAD): копим речь, пока не
наступит тишина достаточной длины, и только затем отправляем ЦЕЛУЮ фразу.

Сегментация по паузам (что важно для медленной речи):
- фраза завершается ТОЛЬКО после паузы длиной SILENCE_FLUSH_SEC. Значение
  намеренно сделано большим (1.5 с), иначе при медленной речи естественные
  паузы между словами дробят одно предложение на отдельные абзацы и ухудшают
  качество распознавания (GigaAM хуже работает с обрывками из 1–2 слов).
- перед началом речи хранится небольшой «пре-ролл» (PREROLL_SEC): когда VAD
  наконец срабатывает, тихое начало слова уже прошло, поэтому мы добавляем
  предшествующие кадры в начало фразы. Без этого начало фраз обрезалось.
- короткие провалы громкости внутри слова НЕ завершают фразу: они просто
  копятся как «хвостовая тишина» и обнуляются, как только речь возобновилась
  (эффект hangover).

Детектор голоса (VAD) адаптивный:
- громкость кадра считается по RMS (среднеквадратичная энергия), а не по пику,
  так как пик чувствителен к любому щелчку;
- уровень фонового шума оценивается на лету и ТОЛЬКО по «нешумовым» кадрам,
  чтобы во время длинной речи порог не «уползал» вверх и не срезал концы фраз;
- пользовательский порог (config.vad_threshold, ползунок «Порог голоса (VAD)»)
  используется как абсолютный нижний предел, поэтому ползунок снова влияет на
  чувствительность.

Требуется ffmpeg в PATH. Первый запуск скачивает веса модели с Hugging Face.
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

    # --- Параметры сегментации по паузам ---
    # Длина тишины, завершающая фразу. Должна быть заметно больше типичной паузы
    # между словами при медленной речи, иначе одно предложение дробится на
    # отдельные абзацы. 1.5 с — безопасный компромисс между связностью и задержкой.
    SILENCE_FLUSH_SEC = 1.5
    # Короче — не отправляем (случайный шум/щелчок).
    MIN_SPEECH_SEC = 0.3
    # Жёсткий предел длины фразы (защита; GigaAM рассчитан на записи до ~25 с).
    MAX_UTTERANCE_SEC = 20.0
    # Сколько звука ДО срабатывания VAD сохранять, чтобы не терять тихое начало слова.
    PREROLL_SEC = 0.3

    # --- Параметры адаптивного VAD ---
    SPEECH_FACTOR = 2.0        # речь должна быть в N раз громче фона
    SPEECH_MARGIN = 100.0      # абсолютный запас над фоном (ед. int16 RMS)

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
        self._buffer = bytearray()       # накопленная фраза (речь + внутренние паузы)
        self._preroll = bytearray()      # последние кадры до начала речи (пре-ролл)
        self._trailing_silence = 0       # байт подряд идущей тишины в хвосте
        self._has_speech = False         # идёт ли сейчас накопление фразы
        self._noise_rms = None           # текущая оценка фонового шума (RMS)
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
            logger.warning(
                "gigaam.load_model не принимает device=, загружаем с настройками по умолчанию"
            )
            return gigaam.load_model(self.model_name)

    def unload(self) -> None:
        """Выгружает модель и очищает буфер."""
        self._model = None
        self._reset_buffer()
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
        """Сегментирует живой звук по паузам и распознаёт целые фразы."""
        if not self._is_loaded or self._model is None:
            logger.error("GigaAM не загружен")
            return

        if not audio_chunk:
            return

        bytes_per_sec = int(self.config.sample_rate) * 2  # PCM16 mono
        silence_flush_bytes = int(bytes_per_sec * self.SILENCE_FLUSH_SEC)
        max_bytes = int(bytes_per_sec * self.MAX_UTTERANCE_SEC)
        min_speech_bytes = int(bytes_per_sec * self.MIN_SPEECH_SEC)
        preroll_bytes = int(bytes_per_sec * self.PREROLL_SEC)

        is_speech = self._is_speech(audio_chunk)

        # Фраза ещё не началась.
        if not self._has_speech:
            if is_speech:
                # Начало фразы: добавляем сохранённый пре-ролл, чтобы не потерять
                # тихое начало слова, затем текущий кадр.
                self._has_speech = True
                self._trailing_silence = 0
                self._buffer.extend(self._preroll)
                self._preroll.clear()
                self._buffer.extend(audio_chunk)
            else:
                # Тишина до начала речи: копим только небольшой пре-ролл.
                self._push_preroll(audio_chunk, preroll_bytes)
            return

        # Фраза уже идёт — добавляем кадр в буфер.
        self._buffer.extend(audio_chunk)

        if is_speech:
            # Речь продолжается — сбрасываем счётчик хвостовой тишины (hangover).
            self._trailing_silence = 0
        else:
            # Короткие паузы не завершают фразу; завершаем только после
            # достаточно долгой тишины.
            self._trailing_silence += len(audio_chunk)
            if self._trailing_silence >= silence_flush_bytes:
                yield from self._flush(min_speech_bytes)
                return

        # Защита от бесконечно длинной фразы (непрерывная речь без пауз).
        if len(self._buffer) >= max_bytes:
            yield from self._flush(min_speech_bytes)

    def _flush(self, min_speech_bytes: int) -> Generator[RecognitionResult, None, None]:
        """Отправляет накопленную фразу на распознавание и очищает буфер."""
        data = bytes(self._buffer)
        self._buffer.clear()
        self._trailing_silence = 0
        self._has_speech = False

        if len(data) < min_speech_bytes:
            return

        result = self.recognize(data)
        if result:
            yield result

    def reset(self) -> None:
        """Очищает буфер потокового звука и калибровку шума."""
        self._reset_buffer()

    def finalize_stream(self) -> Generator[RecognitionResult, None, None]:
        """Распознаёт накопленную фразу при остановке записи."""
        if not self._is_loaded or self._model is None or not self._has_speech:
            return

        bytes_per_sec = int(self.config.sample_rate) * 2
        min_speech_bytes = int(bytes_per_sec * self.MIN_SPEECH_SEC)
        yield from self._flush(min_speech_bytes)

    def _reset_buffer(self) -> None:
        self._buffer.clear()
        self._preroll.clear()
        self._trailing_silence = 0
        self._has_speech = False
        self._noise_rms = None

    def _push_preroll(self, audio_chunk: bytes, preroll_bytes: int) -> None:
        """Хранит скользящее окно последних кадров до начала речи."""
        if preroll_bytes <= 0:
            return
        self._preroll.extend(audio_chunk)
        if len(self._preroll) > preroll_bytes:
            # Оставляем только последние preroll_bytes байт.
            del self._preroll[:-preroll_bytes]

    def _is_speech(self, audio_data: bytes) -> bool:
        """Адаптивный VAD по RMS с автооценкой фонового шума.

        Оценка шума обновляется ТОЛЬКО по кадрам, которые не были признаны
        речью, поэтому во время длинной речи порог не растёт и не срезает
        концы фраз. Пользовательский порог vad_threshold задаёт абсолютный
        нижний предел срабатывания.
        """
        rms = self._frame_rms(audio_data)

        if self._noise_rms is None:
            self._noise_rms = rms

        abs_floor = float(getattr(self.config, "vad_threshold", 0) or 0)
        threshold = max(
            self._noise_rms * self.SPEECH_FACTOR,
            self._noise_rms + self.SPEECH_MARGIN,
            abs_floor,
        )
        is_speech = rms >= threshold

        if not is_speech:
            # Обновляем оценку фона только на «нешумовых» кадрах:
            # быстро опускаем на тишине, медленно поднимаем на слабом фоне.
            if rms < self._noise_rms:
                self._noise_rms = 0.9 * self._noise_rms + 0.1 * rms
            else:
                self._noise_rms = 0.995 * self._noise_rms + 0.005 * rms

        return is_speech

    @staticmethod
    def _frame_rms(audio_data: bytes) -> float:
        samples = np.frombuffer(audio_data, np.int16).astype(np.float32)
        if samples.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(samples))))

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
