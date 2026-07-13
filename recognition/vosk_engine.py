"""
Vosk движок для быстрого real-time распознавания русской речи.
С улучшенным накоплением фраз для предотвращения обрезки предложений.
"""

import json
import logging
import time
from typing import Optional, Generator, List
from pathlib import Path

from .base import BaseRecognizer
from utils.threading_utils import RecognitionResult
from utils.config import RecognitionConfig

logger = logging.getLogger("voice_translator.recognition.vosk")

# Импортируем vosk с обработкой ошибки
try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logger.warning("Vosk не установлен. Используйте: pip install vosk")


class VoskRecognizer(BaseRecognizer):
    """
    Vosk-based распознаватель для быстрого real-time распознавания.
    Низкая латентность, работает офлайн.

    Включает накопление фраз для предотвращения преждевременной обрезки предложений.
    """

    # URL для скачивания моделей
    MODEL_URL_SMALL = "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip"
    MODEL_URL_LARGE = "https://alphacephei.com/vosk/models/vosk-model-ru-0.22.zip"
    MODEL_NAME_SMALL = "vosk-model-ru-0.42"
    MODEL_NAME_LARGE = "vosk-model-ru-0.22"

    # Для обратной совместимости
    MODEL_URL = MODEL_URL_SMALL
    MODEL_NAME = MODEL_NAME_SMALL

    # Параметры накопления фраз
    DEFAULT_PHRASE_TIMEOUT = 1.5  # Секунды тишины до финализации
    MIN_PHRASE_WORDS = 2  # Минимум слов для отдельной фразы

    def __init__(self, config: RecognitionConfig, model_path: str = "models/vosk-model-ru",
                 phrase_timeout: float = DEFAULT_PHRASE_TIMEOUT):
        super().__init__(config)
        self.model_path = Path(model_path)
        self.phrase_timeout = phrase_timeout
        self._model = None
        self._recognizer = None
        self._model_name = "Vosk Russian"

        # Буфер для накопления фраз
        self._phrase_buffer: List[str] = []
        self._last_speech_time: float = 0.0
        self._pending_final: Optional[str] = None

        # Кэш для partial JSON чтобы избежать повторного парсинга
        self._cached_partial_json: Optional[str] = None
        self._cached_partial_text: str = ""
        # Максимальный размер буфера фраз для предотвращения утечки памяти
        self._max_phrase_buffer: int = 50
    
    def load(self) -> bool:
        """Загружает Vosk модель."""
        if not VOSK_AVAILABLE:
            logger.error("Vosk библиотека недоступна")
            return False
        
        if self._is_loaded:
            logger.debug("Vosk модель уже загружена")
            return True
        
        # Отключаем логи Vosk
        SetLogLevel(-1)
        
        # Проверяем наличие модели
        if not self.model_path.exists():
            logger.error(f"Модель Vosk не найдена: {self.model_path}")
            logger.info(f"Скачайте модель: {self.MODEL_URL}")
            logger.info(f"Распакуйте в: {self.model_path}")
            return False
        
        try:
            logger.info(f"Загрузка Vosk модели: {self.model_path}")
            self._model = Model(str(self.model_path))
            self._recognizer = KaldiRecognizer(self._model, self.config.sample_rate)
            self._recognizer.SetWords(True)
            self._is_loaded = True
            logger.info("Vosk модель загружена успешно")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка загрузки Vosk: {e}")
            self._model = None
            self._recognizer = None
            return False
    
    def unload(self) -> None:
        """Выгружает Vosk модель."""
        self._recognizer = None
        self._model = None
        self._is_loaded = False
        logger.info("Vosk модель выгружена")
    
    def recognize(self, audio_data: bytes) -> Optional[RecognitionResult]:
        """
        Распознаёт речь в аудиоданных (batch mode).
        """
        if not self._is_loaded or not self._recognizer:
            logger.error("Vosk не загружен")
            return None
        
        try:
            # Передаём все данные
            self._recognizer.AcceptWaveform(audio_data)
            
            # Получаем финальный результат
            result_json = self._recognizer.FinalResult()
            result = json.loads(result_json)
            
            text = result.get("text", "").strip()
            if text:
                return RecognitionResult(
                    text=text,
                    is_final=True,
                    confidence=self._calculate_confidence(result),
                    engine="vosk"
                )
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга Vosk результата: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка распознавания Vosk: {e}")
            return None
    
    def recognize_stream(self, audio_chunk: bytes) -> Generator[RecognitionResult, None, None]:
        """
        Потоковое распознавание для real-time обработки.
        С накоплением фраз для предотвращения преждевременной обрезки.
        """
        if not self._is_loaded or not self._recognizer:
            logger.error("Vosk не загружен")
            return

        current_time = time.time()

        try:
            if self._recognizer.AcceptWaveform(audio_chunk):
                # Vosk считает фразу законченной
                result_json = self._recognizer.Result()
                result = json.loads(result_json)

                text = result.get("text", "").strip()
                if text:
                    # Добавляем в буфер вместо немедленной отправки
                    self._phrase_buffer.append(text)
                    self._last_speech_time = current_time
                    self._pending_final = result  # Сохраняем для confidence
                    logger.debug(f"Vosk фраза в буфер: '{text}' (всего: {len(self._phrase_buffer)})")

            else:
                # Частичный результат - речь продолжается
                partial_json = self._recognizer.PartialResult()
                # Кэшируем partial JSON чтобы избежать повторного парсинга
                if partial_json == self._cached_partial_json:
                    text = self._cached_partial_text
                else:
                    partial = json.loads(partial_json)
                    text = partial.get("partial", "").strip()
                    self._cached_partial_json = partial_json
                    self._cached_partial_text = text

                if text:
                    self._last_speech_time = current_time
                    # Показываем накопленное + текущее как partial
                    full_partial = self._get_accumulated_text(text)
                    yield RecognitionResult(
                        text=full_partial,
                        is_final=False,
                        confidence=0.0,
                        engine="vosk"
                    )

            # Проверяем timeout для финализации накопленной фразы
            if self._phrase_buffer and self._last_speech_time > 0:
                silence_duration = current_time - self._last_speech_time
                if silence_duration >= self.phrase_timeout:
                    # Достаточно тишины - финализируем накопленную фразу
                    accumulated = self._finalize_accumulated()
                    if accumulated:
                        yield accumulated

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга Vosk: {e}")
        except Exception as e:
            logger.error(f"Ошибка потокового распознавания: {e}")

    def _get_accumulated_text(self, current_partial: str = "") -> str:
        """Возвращает накопленный текст + текущий partial."""
        # Ограничиваем буфер фраз чтобы избежать бесконечного роста
        if len(self._phrase_buffer) > self._max_phrase_buffer:
            # Удаляем старые фразы с запасом
            self._phrase_buffer = self._phrase_buffer[-self._max_phrase_buffer + 10:]
        parts = self._phrase_buffer.copy()
        if current_partial:
            parts.append(current_partial)
        return " ".join(parts)

    def _finalize_accumulated(self) -> Optional[RecognitionResult]:
        """Финализирует накопленную фразу и очищает буфер."""
        if not self._phrase_buffer:
            return None

        accumulated_text = " ".join(self._phrase_buffer)
        self._phrase_buffer.clear()
        self._last_speech_time = 0.0

        # Вычисляем confidence
        confidence = 0.5
        if self._pending_final:
            confidence = self._calculate_confidence(self._pending_final)
        self._pending_final = None

        logger.debug(f"Vosk финализация: '{accumulated_text}'")

        return RecognitionResult(
            text=accumulated_text,
            is_final=True,
            confidence=confidence,
            engine="vosk"
        )
    
    def reset(self) -> None:
        """Сбрасывает состояние recognizer для новой сессии."""
        if self._recognizer and self._model:
            self._recognizer = KaldiRecognizer(self._model, self.config.sample_rate)
            self._recognizer.SetWords(True)

        # Очищаем буфер фраз и кэш partial
        self._phrase_buffer.clear()
        self._last_speech_time = 0.0
        self._pending_final = None
        self._cached_partial_json = None
        self._cached_partial_text = ""
        logger.debug("Vosk recognizer сброшен")
    
    def _calculate_confidence(self, result: dict) -> float:
        """Вычисляет средний confidence из результатов по словам."""
        words = result.get("result", [])
        if not words:
            return 0.5  # Default confidence
        
        confidences = [w.get("conf", 0.5) for w in words]
        return sum(confidences) / len(confidences)
