"""Recognition package - движки распознавания речи."""

import logging
from typing import Callable, Optional

from .base import BaseRecognizer
from .filters import HallucinationFilter
from .gigaam_engine import GigaAMRecognizer, GIGAAM_AVAILABLE
from .parakeet_engine import ParakeetRecognizer, SHERPA_AVAILABLE
from utils.config import AppConfig, RecognitionConfig

logger = logging.getLogger("voice_translator.recognition")


def create_recognizer(config: AppConfig, rec_config: RecognitionConfig) -> Optional[BaseRecognizer]:
    """
    Creates and loads the configured GigaAM recognizer.
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
    return requested


def _requested_candidates(
    config: AppConfig,
    rec_config: RecognitionConfig,
) -> list[tuple[str, Callable[[], BaseRecognizer]]]:
    if config.engine == "gigaam":
        return [_gigaam_candidate(config, rec_config)]

    logger.warning("Unknown recognition engine '%s', using fallback chain", config.engine)
    return []


def _requested_label(config: AppConfig) -> str:
    if config.engine == "gigaam":
        return "gigaam"
    return "unknown"


def _gigaam_candidate(
    config: AppConfig,
    rec_config: RecognitionConfig,
) -> tuple[str, Callable[[], BaseRecognizer]]:
    return (
        "gigaam",
        lambda: GigaAMRecognizer(
            rec_config,
            model_name=config.gigaam_model,
            device=config.gigaam_device,
            language=config.gigaam_language,
        ),
    )


def _build_recognizer(
    label: str,
    factory: Callable[[], BaseRecognizer],
) -> Optional[BaseRecognizer]:
    if label == "gigaam" and not GIGAAM_AVAILABLE:
        logger.warning("GigaAM is unavailable, trying fallback")
        return None
    try:
        return factory()
    except Exception as e:
        logger.warning("Could not create recognizer %s: %s", label, e)
        return None


__all__ = [
    'BaseRecognizer',
    'GigaAMRecognizer',
    'GIGAAM_AVAILABLE',
    'ParakeetRecognizer',
    'SHERPA_AVAILABLE',
    'HallucinationFilter',
    'create_recognizer',
]
