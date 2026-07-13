"""Utils package - утилиты для приложения."""
from .config import AppConfig, RecognitionConfig
from .logging_config import setup_logging, LoggerMixin
from .threading_utils import (
    ThreadSafeQueue, 
    EngineState, 
    EngineManager,
    RecognitionResult,
    TranslationResult,
    StoppableThread,
    AtomicCounter
)

__all__ = [
    'AppConfig',
    'RecognitionConfig', 
    'setup_logging',
    'LoggerMixin',
    'ThreadSafeQueue',
    'EngineState',
    'EngineManager',
    'RecognitionResult',
    'TranslationResult',
    'StoppableThread',
    'AtomicCounter',
]
