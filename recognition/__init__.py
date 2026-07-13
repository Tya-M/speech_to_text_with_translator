"""Recognition package - движки распознавания речи."""

import logging
from typing import Callable, Optional

from .base import BaseRecognizer
from .vosk_engine import VoskRecognizer, VOSK_AVAILABLE
from .whisper_engine import WhisperRecognizer, WHISPER_AVAILABLE, HallucinationFilter
from .faster_whisper_engine import FasterWhisperRecognizer, FASTER_WHISPER_AVAILABLE
from utils.config import AppConfig, RecognitionConfig

logger = logging.getLogger("voice_translator.recognition")

WHISPER_CPP_AVAILABLE = False
WhisperCppRecognizer = None


def create_recognizer(config: AppConfig, rec_config: RecognitionConfig) -> Optional[BaseRecognizer]:
    """
    Creates and loads the requested recognizer, falling back to CPU engines and Vosk.

    Fallback order after the requested engine fails:
    faster-whisper (CPU) -> openai-whisper (CPU) -> Vosk.
    whisper_cpp is reserved for T04 and treated as unavailable for now.
    """
    attempted: set[str] = set()

    for label, factory in _recognizer_candidates(config, rec_config):
        if label in attempted:
            continue
        attempted.add(label)

        recognizer = _build_recognizer(label, factory)
        if recognizer is None:
            continue

        try:
            if recognizer.load():
                if label != _requested_label(config):
                    logger.warning("Fallback recognizer selected: %s", label)
                return recognizer
            logger.warning("Recognizer failed to load: %s", label)
            recognizer.unload()
        except Exception as e:
            logger.warning("Recognizer %s failed, trying fallback: %s", label, e)
            try:
                recognizer.unload()
            except Exception:
                pass

    logger.error("No recognition engine could be loaded")
    return None


def _recognizer_candidates(
    config: AppConfig,
    rec_config: RecognitionConfig,
) -> list[tuple[str, Callable[[], BaseRecognizer]]]:
    requested = _requested_candidates(config, rec_config)
    fallbacks = [
        _faster_whisper_candidate(config, rec_config),
        _whisper_candidate(config, rec_config),
        _vosk_candidate(config, rec_config),
    ]
    return requested + fallbacks


def _requested_candidates(
    config: AppConfig,
    rec_config: RecognitionConfig,
) -> list[tuple[str, Callable[[], BaseRecognizer]]]:
    if config.engine == "vosk":
        return [_vosk_candidate(config, rec_config)]

    if config.engine != "whisper":
        logger.warning("Unknown recognition engine '%s', using fallback chain", config.engine)
        return []

    if config.whisper_backend == "faster":
        return [_faster_whisper_candidate(config, rec_config)]
    if config.whisper_backend == "openai":
        return [_whisper_candidate(config, rec_config)]
    if config.whisper_backend == "whisper_cpp":
        logger.warning("whisper.cpp backend is not available until T04; using CPU fallback")
        return []

    logger.warning("Unknown Whisper backend '%s', using fallback chain", config.whisper_backend)
    return []


def _requested_label(config: AppConfig) -> str:
    if config.engine == "vosk":
        return "vosk"
    if config.engine == "whisper":
        if config.whisper_backend == "faster":
            return "faster-whisper (CPU)"
        if config.whisper_backend == "openai":
            return "whisper (CPU)"
        if config.whisper_backend == "whisper_cpp":
            return "whisper.cpp"
    return "unknown"


def _faster_whisper_candidate(
    config: AppConfig,
    rec_config: RecognitionConfig,
) -> tuple[str, Callable[[], BaseRecognizer]]:
    return (
        "faster-whisper (CPU)",
        lambda: FasterWhisperRecognizer(
            rec_config,
            model_name=config.whisper_model,
            cache_dir=config.faster_whisper_cache_dir,
            compute_type=config.whisper_compute_type,
        ),
    )


def _whisper_candidate(
    config: AppConfig,
    rec_config: RecognitionConfig,
) -> tuple[str, Callable[[], BaseRecognizer]]:
    return (
        "whisper (CPU)",
        lambda: WhisperRecognizer(
            rec_config,
            model_name=config.whisper_model,
            cache_dir=config.whisper_cache_dir,
        ),
    )


def _vosk_candidate(
    config: AppConfig,
    rec_config: RecognitionConfig,
) -> tuple[str, Callable[[], BaseRecognizer]]:
    model_path = config.vosk_large_model_path if config.vosk_model_size == "large" else config.vosk_model_path
    return (
        "vosk",
        lambda: VoskRecognizer(
            rec_config,
            model_path=model_path,
            phrase_timeout=config.vosk_phrase_timeout,
        ),
    )


def _build_recognizer(
    label: str,
    factory: Callable[[], BaseRecognizer],
) -> Optional[BaseRecognizer]:
    if label == "faster-whisper (CPU)" and not FASTER_WHISPER_AVAILABLE:
        logger.warning("faster-whisper is unavailable, trying fallback")
        return None
    if label == "whisper (CPU)" and not WHISPER_AVAILABLE:
        logger.warning("openai-whisper is unavailable, trying fallback")
        return None
    if label == "vosk" and not VOSK_AVAILABLE:
        logger.warning("Vosk is unavailable")
        return None

    try:
        return factory()
    except Exception as e:
        logger.warning("Could not create recognizer %s: %s", label, e)
        return None

__all__ = [
    'BaseRecognizer',
    'VoskRecognizer',
    'VOSK_AVAILABLE',
    'WhisperRecognizer',
    'WHISPER_AVAILABLE',
    'FasterWhisperRecognizer',
    'FASTER_WHISPER_AVAILABLE',
    'WhisperCppRecognizer',
    'WHISPER_CPP_AVAILABLE',
    'HallucinationFilter',
    'create_recognizer',
]
