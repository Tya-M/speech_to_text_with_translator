"""
Стили и цветовые схемы для UI приложения.
Тёмная тема с акцентами. CustomTkinter совместимый.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ColorScheme:
    """Цветовая схема приложения."""

    # Основные цвета фона (CustomTkinter dark theme compatible)
    bg_primary: str = "#1a1a2e"      # Тёмно-синий
    bg_secondary: str = "#16213e"    # Чуть светлее
    bg_tertiary: str = "#0f3460"     # Акцентный фон

    # CTk-compatible фоновые цвета
    ctk_bg_dark: str = "#2b2b2b"     # Для Canvas компонентов в тёмной теме
    ctk_frame_dark: str = "#242424"  # Фон CTkFrame
    ctk_frame_border: str = "#3d3d3d"  # Границы фреймов

    # Цвета текста
    text_primary: str = "#e8e8e8"    # Основной текст
    text_secondary: str = "#a0a0a0"  # Вторичный текст
    text_muted: str = "#606060"      # Приглушённый

    # Акцентные цвета
    accent_primary: str = "#00d4ff"   # Голубой (перевод)
    accent_secondary: str = "#7b68ee" # Фиолетовый
    accent_success: str = "#00ff88"   # Зелёный (запись)
    accent_warning: str = "#ffaa00"   # Оранжевый
    accent_error: str = "#ff4444"     # Красный

    # Цвета для элементов управления
    button_bg: str = "#2d2d44"
    button_hover: str = "#3d3d54"
    button_active: str = "#4d4d64"
    button_disabled: str = "#1d1d2e"

    # Границы
    border: str = "#3d3d54"
    border_focus: str = "#00d4ff"

    # Индикаторы
    recording_pulse: str = "#ff4444"
    level_meter: str = "#00ff88"
    level_meter_peak: str = "#ffaa00"

    # CTk Button цвета
    ctk_button_fg: str = "#1f6aa5"
    ctk_button_hover: str = "#144870"


@dataclass(frozen=True)
class Fonts:
    """Шрифты приложения."""

    # Основные шрифты (macOS)
    family_primary: str = "SF Pro Display"
    family_mono: str = "SF Mono"
    family_fallback: str = "Helvetica Neue"

    # Размеры
    size_small: int = 11
    size_normal: int = 13
    size_large: int = 15
    size_xlarge: int = 18
    size_title: int = 24

    # Веса
    weight_normal: str = "normal"
    weight_bold: str = "bold"


@dataclass(frozen=True)
class Spacing:
    """Отступы и размеры."""

    # Отступы
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32

    # Скругления
    radius_sm: int = 4
    radius_md: int = 8
    radius_lg: int = 12
    radius_xl: int = 16

    # CTk corner radius
    ctk_corner_radius: int = 10

    # Размеры элементов
    button_height: int = 40
    button_width: int = 120
    toggle_width: int = 200
    toggle_height: int = 36
    slider_height: int = 24
    meter_height: int = 8


# Глобальные экземпляры
COLORS = ColorScheme()
FONTS = Fonts()
SPACING = Spacing()


def get_font_tuple(size: int = FONTS.size_normal, weight: str = FONTS.weight_normal) -> Tuple[str, int, str]:
    """Возвращает tuple для tkinter font."""
    return (FONTS.family_primary, size, weight)


def get_ctk_font(size: int = FONTS.size_normal, weight: str = FONTS.weight_normal) -> Tuple[str, int, str]:
    """Возвращает tuple для CustomTkinter font."""
    return (FONTS.family_primary, size, weight)


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Конвертирует HEX в RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Конвертирует RGB в HEX."""
    return f"#{r:02x}{g:02x}{b:02x}"


def blend_colors(color1: str, color2: str, factor: float = 0.5) -> str:
    """Смешивает два цвета."""
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)

    r = int(r1 + (r2 - r1) * factor)
    g = int(g1 + (g2 - g1) * factor)
    b = int(b1 + (b2 - b1) * factor)

    return rgb_to_hex(r, g, b)
