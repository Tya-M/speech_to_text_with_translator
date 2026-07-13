"""
Кастомные UI компоненты для приложения.
RecordButton, LevelMeter, StatusBar.
Совместимо с CustomTkinter.
"""

import tkinter as tk
import customtkinter as ctk
from typing import Callable, Optional
import logging

from .styles import COLORS, FONTS, SPACING, get_font_tuple

logger = logging.getLogger("voice_translator.app.components")


class RecordButton(tk.Canvas):
    """
    Компактная кнопка записи с анимацией пульсации.
    Использует tk.Canvas для кастомной отрисовки.
    """

    def __init__(
        self,
        parent,
        command: Optional[Callable[[bool], None]] = None,
        size: int = 80,
        **kwargs
    ):
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=COLORS.ctk_bg_dark,
            highlightthickness=0,
            **kwargs
        )
        try:
            self.configure(cursor="pointinghand")
        except tk.TclError:
            self.configure(cursor="hand2")

        self.command = command
        self.size = size
        self._is_recording = False
        self._pulse_state = 0
        self._animation_id = None

        self._draw()
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda _event: self._draw(hover=True))
        self.bind("<Leave>", lambda _event: self._draw())

    def _rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Рисует скругленный прямоугольник на Canvas."""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _draw(self, hover: bool = False):
        """Перерисовывает кнопку."""
        self.delete("all")

        center = self.size // 2
        padding = 3
        corner_radius = max(6, self.size // 5)
        inner_radius = max(6, int(self.size * 0.28))

        border_color = COLORS.recording_pulse if self._is_recording else COLORS.border
        shell_color = COLORS.button_hover if hover else "#15181f"

        self._rounded_rect(
            padding, padding,
            self.size - padding, self.size - padding,
            corner_radius,
            fill=shell_color,
            outline=border_color,
            width=2
        )

        # Внутренний элемент
        if self._is_recording:
            # Квадрат для стопа
            sq_size = inner_radius * 0.75
            self._rounded_rect(
                center - sq_size, center - sq_size,
                center + sq_size, center + sq_size,
                max(2, int(sq_size * 0.35)),
                fill=COLORS.recording_pulse,
                outline=""
            )
        else:
            # Круг для записи
            self.create_oval(
                center - inner_radius + 5, center - inner_radius + 5,
                center + inner_radius - 5, center + inner_radius - 5,
                fill=COLORS.accent_error,
                outline=""
            )

    def _on_click(self, event):
        """Обработчик клика."""
        self._is_recording = not self._is_recording

        if self._is_recording:
            self._start_pulse()
        else:
            self._stop_pulse()

        self._draw()

        if self.command:
            self.command(self._is_recording)

    def _start_pulse(self):
        """Запускает анимацию пульсации."""
        self._pulse_state = 0
        self._animate_pulse()

    def _stop_pulse(self):
        """Останавливает анимацию."""
        if self._animation_id:
            self.after_cancel(self._animation_id)
            self._animation_id = None
        self._pulse_state = 0

    def _animate_pulse(self):
        """Анимация пульсации."""
        if not self._is_recording:
            return

        self._pulse_state += 0.1
        if self._pulse_state > 1.0:
            self._pulse_state = 0

        self._draw()
        self._animation_id = self.after(50, self._animate_pulse)

    @property
    def is_recording(self) -> bool:
        """Состояние записи."""
        return self._is_recording

    def set_recording(self, recording: bool):
        """Устанавливает состояние записи."""
        if self._is_recording != recording:
            self._is_recording = recording
            if recording:
                self._start_pulse()
            else:
                self._stop_pulse()
            self._draw()


class LevelMeter(tk.Canvas):
    """
    Визуализатор уровня громкости.
    Использует tk.Canvas для кастомной отрисовки.
    """

    def __init__(
        self,
        parent,
        width: int = 300,
        height: int = SPACING.meter_height,
        segments: int = 30,
        **kwargs
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=COLORS.ctk_bg_dark,
            highlightthickness=0,
            **kwargs
        )

        self.meter_width = width
        self.meter_height = height
        self.segments = segments
        self._level = 0.0
        self._peak = 0.0
        self._peak_hold = 0

        self._draw()

    def _draw(self):
        """Перерисовывает meter."""
        self.delete("all")

        segment_width = (self.meter_width - (self.segments - 1) * 2) // self.segments

        for i in range(self.segments):
            x = i * (segment_width + 2)

            # Определяем цвет сегмента
            segment_pos = i / self.segments

            if segment_pos < self._level:
                if segment_pos < 0.6:
                    color = COLORS.level_meter
                elif segment_pos < 0.85:
                    color = COLORS.accent_warning
                else:
                    color = COLORS.accent_error
            elif segment_pos <= self._peak and self._peak_hold > 0:
                color = COLORS.level_meter_peak
            else:
                color = COLORS.ctk_frame_dark

            self.create_rectangle(
                x, 0,
                x + segment_width, self.meter_height,
                fill=color,
                outline=""
            )

    def set_level(self, level: float):
        """
        Устанавливает уровень (0.0 - 1.0).
        """
        self._level = max(0.0, min(1.0, level))

        # Peak hold
        if self._level > self._peak:
            self._peak = self._level
            self._peak_hold = 30  # Удержание ~1.5 сек при 50ms обновлении
        elif self._peak_hold > 0:
            self._peak_hold -= 1
            if self._peak_hold == 0:
                self._peak = self._level

        self._draw()

    def reset(self):
        """Сбрасывает meter."""
        self._level = 0.0
        self._peak = 0.0
        self._peak_hold = 0
        self._draw()


class StatusBar(ctk.CTkFrame):
    """
    Строка статуса с индикаторами.
    Использует CustomTkinter виджеты.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            height=28,
            corner_radius=0,
            fg_color="transparent",
            **kwargs
        )

        # Статус движка
        self._engine_label = ctk.CTkLabel(
            self,
            text="● Движок: —",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_muted
        )
        self._engine_label.pack(side="left", padx=SPACING.md)

        # Статус модели
        self._model_label = ctk.CTkLabel(
            self,
            text="Модель: —",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_muted
        )
        self._model_label.pack(side="left", padx=SPACING.md)

        # CPU
        self._cpu_label = ctk.CTkLabel(
            self,
            text="CPU: —%",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_muted
        )
        self._cpu_label.pack(side="right", padx=SPACING.md)

        # Кэш переводов
        self._cache_label = ctk.CTkLabel(
            self,
            text="Кэш: 0%",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_muted
        )
        self._cache_label.pack(side="right", padx=SPACING.md)

    def set_engine(self, engine: str, ready: bool = False):
        """Устанавливает статус движка."""
        color = COLORS.accent_success if ready else COLORS.accent_warning
        self._engine_label.configure(
            text=f"● Движок: {engine}",
            text_color=color
        )

    def set_model(self, model: str):
        """Устанавливает название модели."""
        self._model_label.configure(text=f"Модель: {model}")

    def set_cpu(self, percent: float):
        """Устанавливает загрузку CPU."""
        color = COLORS.text_muted
        if percent > 80:
            color = COLORS.accent_error
        elif percent > 50:
            color = COLORS.accent_warning

        self._cpu_label.configure(text=f"CPU: {percent:.0f}%", text_color=color)

    def set_cache(self, hit_rate: float):
        """Устанавливает hit rate кэша."""
        self._cache_label.configure(text=f"Кэш: {hit_rate*100:.0f}%")
