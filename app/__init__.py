"""App package - UI приложения."""
from .gui import VoiceTranslatorApp
from .styles import COLORS, FONTS, SPACING
from .components import (
    RecordButton,
    LevelMeter,
    StatusBar
)

__all__ = [
    'VoiceTranslatorApp',
    'COLORS',
    'FONTS',
    'SPACING',
    'RecordButton',
    'LevelMeter',
    'StatusBar',
]
