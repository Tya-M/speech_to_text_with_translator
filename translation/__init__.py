"""Translation package with selectable offline translation backends."""

from .translator import Translator, TranslationCache, ARGOS_AVAILABLE
from .translategemma import TranslateGemmaTranslator, TRANSLATEGEMMA_AVAILABLE

TRANSLATION_ENGINE_LABELS = {
    "Argos": "argos",
    "TranslateGemma 4B": "translategemma",
}
TRANSLATION_ENGINE_VALUES = list(TRANSLATION_ENGINE_LABELS.keys())


def create_translator(
    engine: str,
    cache_size: int = 100,
    translategemma_model_id: str = TranslateGemmaTranslator.DEFAULT_MODEL_ID,
):
    """Create a configured translator backend without loading its model."""
    if engine == "translategemma":
        return TranslateGemmaTranslator(
            cache_size=cache_size,
            model_id=translategemma_model_id,
        )
    return Translator(cache_size=cache_size)

__all__ = [
    "Translator",
    "TranslationCache",
    "ARGOS_AVAILABLE",
    "TranslateGemmaTranslator",
    "TRANSLATEGEMMA_AVAILABLE",
    "TRANSLATION_ENGINE_LABELS",
    "TRANSLATION_ENGINE_VALUES",
    "create_translator",
]
