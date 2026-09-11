"""
Базовый интерфейс для движков распознавания речи.
"""

from abc import ABC, abstractmethod
from typing import Optional, Generator
from dataclasses import dataclass
import numpy as np

from utils.threading_utils import RecognitionResult
from utils.config import RecognitionConfig


class BaseRecognizer(ABC):
    """Абстрактный базовый класс для движков распознавания."""
    
    def __init__(self, config: RecognitionConfig):
        self.config = config
        self._is_loaded = False
        self._model_name = "unknown"
    
    @property
    def name(self) -> str:
        """Имя движка."""
        return self.__class__.__name__.replace("Recognizer", "").replace("Engine", "")
    
    @property
    def is_loaded(self) -> bool:
        """Проверяет, загружена ли модель."""
        return self._is_loaded
    
    @abstractmethod
    def load(self) -> bool:
        """
        Загружает модель.
        Должен быть вызван перед использованием.
        Возвращает True при успехе.
        """
        pass
    
    @abstractmethod
    def unload(self) -> None:
        """Выгружает модель и освобождает ресурсы."""
        pass
    
    @abstractmethod
    def recognize(self, audio_data: bytes) -> Optional[RecognitionResult]:
        """
        Распознаёт речь в аудиоданных.
        
        Args:
            audio_data: Аудио в формате PCM16, mono, 16kHz
            
        Returns:
            RecognitionResult или None если нет распознанного текста
        """
        pass
    
    @abstractmethod
    def recognize_stream(self, audio_chunk: bytes) -> Generator[RecognitionResult, None, None]:
        """
        Потоковое распознавание для real-time обработки.
        
        Args:
            audio_chunk: Один chunk аудиоданных
            
        Yields:
            RecognitionResult с partial=True для промежуточных результатов
        """
        pass

    def finalize_stream(self) -> Generator[RecognitionResult, None, None]:
        """Flushes any pending audio at the end of a recording session."""
        yield from ()
    
    def reset(self) -> None:
        """Сбрасывает внутреннее состояние (для потокового распознавания)."""
        pass
    
    def __enter__(self):
        self.load()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unload()
