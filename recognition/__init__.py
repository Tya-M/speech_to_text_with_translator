"""Recognition package - движки распознавания речи."""
from .base import BaseRecognizer
from .vosk_engine import VoskRecognizer, VOSK_AVAILABLE
from .whisper_engine import WhisperRecognizer, WHISPER_AVAILABLE, HallucinationFilter
from .faster_whisper_engine import FasterWhisperRecognizer, FASTER_WHISPER_AVAILABLE

__all__ = [
    'BaseRecognizer',
    'VoskRecognizer',
    'VOSK_AVAILABLE',
    'WhisperRecognizer',
    'WHISPER_AVAILABLE',
    'FasterWhisperRecognizer',
    'FASTER_WHISPER_AVAILABLE',
    'HallucinationFilter',
]
