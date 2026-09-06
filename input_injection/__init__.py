"""
Модуль ввода распознанного текста в место курсора (глобальная диктовка).

Состав:
- cursor_typer.CursorTyper — вставка Unicode-текста (в т.ч. кириллицы) туда, где курсор.
- dictation.DictationService — push-to-talk по глобальной горячей клавише +
  офлайн-распознавание GigaAM + печать результата в место курсора.
"""

from .cursor_typer import CursorTyper
from .dictation import DictationService

__all__ = ["CursorTyper", "DictationService"]
