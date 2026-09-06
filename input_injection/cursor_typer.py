"""
Вставка текста в место курсора в любом приложении macOS.

Два способа («лестница», как в jot):
  1) PASTE  — кладём текст в буфер обмена (NSPasteboard) и шлём ⌘V, затем
     восстанавливаем прежний буфер. Надёжно для длинного текста и любых языков.
  2) KEYSTROKES — синтез Unicode-нажатий через Quartz
     CGEventKeyboardSetUnicodeString. Не трогает буфер обмена; подходит как
     запасной вариант. Отправляем порциями ≤ CHUNK символов (у этой функции
     есть недокументированный лимит примерно в 20 символов на одно событие).

Требования:
- macOS разрешение Accessibility (Системные настройки → Конфиденциальность →
  Универсальный доступ) — без него ни ⌘V, ни синтез клавиш не работают.
- pyobjc (Quartz + AppKit) и pynput. На macOS они уже тянутся как зависимости
  pynput, но AppKit (NSPasteboard) требует pyobjc-framework-Cocoa (см. requirements).
"""

import logging
import time
from typing import Optional

logger = logging.getLogger("voice_translator.input_injection.typer")

# --- Опциональные зависимости (только macOS) ---
try:
    import Quartz  # часть pyobjc-framework-Quartz
    _QUARTZ_OK = True
except Exception:  # pragma: no cover - зависит от окружения
    Quartz = None
    _QUARTZ_OK = False

try:
    from AppKit import NSPasteboard, NSPasteboardTypeString  # pyobjc-framework-Cocoa
    _APPKIT_OK = True
except Exception:  # pragma: no cover
    NSPasteboard = None
    NSPasteboardTypeString = None
    _APPKIT_OK = False

try:
    from pynput.keyboard import Controller, Key
    _PYNPUT_OK = True
except Exception:  # pragma: no cover
    Controller = None
    Key = None
    _PYNPUT_OK = False


def is_accessibility_trusted() -> Optional[bool]:
    """Грант ли процессу разрешение Accessibility.

    True/False — известно; None — проверить не удалось (не macOS / нет pyobjc).
    Без этого разрешения синтетические нажатия (⌘V / Unicode) отбрасываются.
    """
    try:
        from ApplicationServices import AXIsProcessTrusted
        return bool(AXIsProcessTrusted())
    except Exception:
        return None


def get_frontmost_app():
    """Возвращает текущее активное приложение (NSRunningApplication) или None."""
    try:
        from AppKit import NSWorkspace
        return NSWorkspace.sharedWorkspace().frontmostApplication()
    except Exception:
        return None


def app_display_name(app) -> Optional[str]:
    """Имя приложения для логов/статуса."""
    if app is None:
        return None
    try:
        return app.localizedName()
    except Exception:
        return None


def activate_app(app) -> bool:
    """Возвращает фокус на указанное приложение перед вставкой."""
    if app is None:
        return False
    try:
        from AppKit import NSApplicationActivateIgnoringOtherApps
        app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
        return True
    except Exception:
        try:
            app.activate()  # macOS 14+
            return True
        except Exception:
            return False


class CursorTyper:
    """Вставляет текст там, где сейчас курсор."""

    # Лимит символов на одно Unicode-событие (см. ограничение ~20 символов).
    KEYSTROKE_CHUNK = 18
    # Паузы (сек) для надёжной работы буфера/⌘V.
    PASTE_SETTLE = 0.05
    CLIPBOARD_RESTORE_DELAY = 0.25

    def __init__(self, prefer: str = "type", restore_clipboard: bool = True):
        """
        :param prefer: "type" (по умолчанию, прямой ввод Unicode — надёжнее всего
            на новых macOS), "keystrokes" или "paste".
        :param restore_clipboard: восстанавливать ли буфер обмена после paste.
        """
        self.prefer = prefer
        self.restore_clipboard = restore_clipboard
        self._keyboard = Controller() if _PYNPUT_OK else None

    # ------------------------------------------------------------------ public
    def type_text(self, text: str) -> Optional[str]:
        """Вставляет text в место курсора.

        Возвращает имя сработавшего метода ("type"/"keystrokes"/"paste") или None.
        """
        if not text:
            return None

        methods = {
            "type": self._type_via_pynput_type,
            "keystrokes": self._type_via_keystrokes,
            "paste": self._type_via_paste,
        }
        if self.prefer == "paste":
            order = ["paste", "type", "keystrokes"]
        elif self.prefer == "keystrokes":
            order = ["keystrokes", "type", "paste"]
        else:  # "type" — прямой ввод Unicode, самый надёжный на новых macOS
            order = ["type", "keystrokes", "paste"]

        for name in order:
            method = methods[name]
            try:
                if method(text):
                    logger.info("Текст вставлен методом %s", name)
                    return name
            except Exception as e:
                logger.warning("Метод ввода %s не сработал: %s", name, e)

        logger.error("Не удалось вставить текст ни одним способом")
        return None

    # --------------------------------------------------------- прямой ввод
    def _type_via_pynput_type(self, text: str) -> bool:
        """Прямой ввод символов через pynput (CGEventKeyboardSetUnicodeString).

        Не трогает буфер обмена и не зависит от ⌘V; на новых macOS (вкл. Tahoe)
        это самый надёжный способ вставить текст под курсор.
        """
        if not (_PYNPUT_OK and self._keyboard is not None):
            return False
        self._keyboard.type(text)
        return True

    # ------------------------------------------------------------- paste-based
    def _type_via_paste(self, text: str) -> bool:
        if not (_APPKIT_OK and _PYNPUT_OK and self._keyboard is not None):
            return False

        pb = NSPasteboard.generalPasteboard()
        old_value: Optional[str] = None
        if self.restore_clipboard:
            try:
                old_value = pb.stringForType_(NSPasteboardTypeString)
            except Exception:
                old_value = None

        pb.clearContents()
        pb.setString_forType_(text, NSPasteboardTypeString)
        time.sleep(self.PASTE_SETTLE)

        # Отправляем ⌘V.
        self._keyboard.press(Key.cmd)
        self._keyboard.press("v")
        self._keyboard.release("v")
        self._keyboard.release(Key.cmd)

        # Восстанавливаем прежний буфер (после того, как вставка успела пройти).
        if self.restore_clipboard and old_value is not None:
            time.sleep(self.CLIPBOARD_RESTORE_DELAY)
            try:
                pb.clearContents()
                pb.setString_forType_(old_value, NSPasteboardTypeString)
            except Exception:
                pass

        return True

    # --------------------------------------------------------- keystroke-based
    def _type_via_keystrokes(self, text: str) -> bool:
        if not _QUARTZ_OK:
            return False

        for i in range(0, len(text), self.KEYSTROKE_CHUNK):
            piece = text[i : i + self.KEYSTROKE_CHUNK]
            self._post_unicode(piece)
            time.sleep(0.005)
        return True

    @staticmethod
    def _post_unicode(piece: str) -> None:
        """Синтезирует down/up события с привязанной Unicode-строкой."""
        for is_down in (True, False):
            event = Quartz.CGEventCreateKeyboardEvent(None, 0, is_down)
            Quartz.CGEventKeyboardSetUnicodeString(event, len(piece), piece)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

    # ----------------------------------------------------------------- helpers
    @staticmethod
    def availability() -> dict:
        """Диагностика: какие бэкенды доступны в текущем окружении."""
        return {
            "quartz": _QUARTZ_OK,
            "appkit": _APPKIT_OK,
            "pynput": _PYNPUT_OK,
            "accessibility_trusted": is_accessibility_trusted(),
        }
