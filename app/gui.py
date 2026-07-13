"""
Главный класс GUI приложения.
Объединяет все компоненты и управляет логикой.
Использует CustomTkinter для современного тёмного интерфейса.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import threading
import time
import logging
import json
from datetime import datetime
from typing import Optional, List
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from .styles import COLORS, FONTS, SPACING, get_font_tuple
from .components import RecordButton, LevelMeter, StatusBar
from utils.config import AppConfig, RecognitionConfig
from utils.threading_utils import (
    ThreadSafeQueue, EngineState, EngineManager,
    RecognitionResult, StoppableThread
)
from audio.capture import AudioCapture, AudioDevice
from recognition import (
    VoskRecognizer,
    VOSK_AVAILABLE
)
from translation import Translator, ARGOS_AVAILABLE

logger = logging.getLogger("voice_translator.app.gui")

# CustomTkinter настройки
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class TranscriptEntry:
    """Запись в транскрипте."""

    def __init__(self, original: str, translated: str = "", timestamp: float = 0):
        self.original = original
        self.translated = translated
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "translated": self.translated,
            "timestamp": self.timestamp,
            "time_str": datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")
        }


class VoiceTranslatorApp:
    """Главное приложение для распознавания русской речи и перевода."""

    TITLE = "Голосовой Переводчик"
    VERSION = "1.0.0"

    def __init__(self, config: AppConfig):
        self.config = config
        self.root: Optional[ctk.CTk] = None

        # Состояние
        self.engine_manager = EngineManager()
        self.result_queue: ThreadSafeQueue[RecognitionResult] = ThreadSafeQueue()
        self.transcript: List[TranscriptEntry] = []

        # Компоненты
        self.audio_capture: Optional[AudioCapture] = None
        self.vosk_recognizer: Optional[VoskRecognizer] = None
        self.translator: Optional[Translator] = None
        self.current_recognizer = None

        # Потоки
        self.recognition_thread: Optional[StoppableThread] = None
        self.init_thread: Optional[threading.Thread] = None

        # UI элементы
        self.text_area: Optional[tk.Text] = None
        self.level_meter: Optional[LevelMeter] = None
        self.record_button: Optional[RecordButton] = None
        self.model_toggle: Optional[ctk.CTkSegmentedButton] = None
        self.status_bar: Optional[StatusBar] = None
        self.device_menu: Optional[ctk.CTkOptionMenu] = None
        self.sensitivity_slider: Optional[ctk.CTkSlider] = None
        self.sensitivity_label: Optional[ctk.CTkLabel] = None
        self.vad_slider: Optional[ctk.CTkSlider] = None
        self.vad_label: Optional[ctk.CTkLabel] = None
        self.recording_status: Optional[ctk.CTkLabel] = None

        # Устройства
        self.audio_devices: List[AudioDevice] = []
        self._device_names: List[str] = ["Загрузка..."]

        # Флаги
        self._is_recording = False
        # Partial-обновления (троттлинг и одна "живая" строка)
        self._pending_partial_text: str = ""
        self._last_applied_partial: str = ""
        self._partial_timer_id = None
        self._partial_mark_name = "partial_start"
        # Значение троттлинга из конфига (валидация уже в AppConfig)
        # Для Intel i5 4-core: 150ms чтобы разгрузить CPU от частых GUI-обновлений
        self._partial_throttle_ms: int = getattr(self.config, "partial_throttle_ms", 150)
        logger.info(f"Partial throttle: {self._partial_throttle_ms} ms")

    def run(self):
        """Запускает приложение."""
        self._create_window()
        self._create_ui()
        self._setup_bindings()
        self._start_init_thread()
        self._start_polling()

        logger.info("Приложение запущено")
        self.root.mainloop()

    def _create_window(self):
        """Создаёт главное окно."""
        self.root = ctk.CTk()
        self.root.title(f"{self.TITLE} v{self.VERSION}")
        self.root.geometry(f"{self.config.window_width}x{self.config.window_height}")
        self.root.minsize(500, 550)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_ui(self):
        """Создаёт UI."""
        main_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=SPACING.sm, pady=SPACING.xs)

        # Статус бар
        self.status_bar = StatusBar(main_frame)
        self.status_bar.pack(fill="x", pady=(0, SPACING.xs))

        # Заголовок
        header = ctk.CTkFrame(main_frame, corner_radius=0, fg_color="transparent")
        header.pack(fill="x", pady=(0, SPACING.xs))

        title_label = ctk.CTkLabel(
            header, text=self.TITLE,
            font=get_font_tuple(FONTS.size_xlarge, FONTS.weight_bold),
            text_color=COLORS.text_primary
        )
        title_label.pack(side="left")

        # Панель управления
        control_panel = ctk.CTkFrame(main_frame, corner_radius=SPACING.ctk_corner_radius)
        control_panel.pack(fill="x", pady=(0, SPACING.xs), padx=0)

        top_controls = ctk.CTkFrame(control_panel, corner_radius=0, fg_color="transparent")
        top_controls.pack(fill="x", padx=SPACING.sm, pady=(SPACING.xs, 2))

        # Выбор модели Vosk
        engine_frame = ctk.CTkFrame(top_controls, corner_radius=0, fg_color="transparent")
        engine_frame.pack(side="left")

        ctk.CTkLabel(
            engine_frame, text="Модель Vosk:",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_secondary
        ).pack(anchor="w")

        self.model_toggle = ctk.CTkSegmentedButton(
            engine_frame,
            values=["Быстрая (0.42)", "Точная (0.22)"],
            command=self._on_model_change,
            font=get_font_tuple(FONTS.size_small),
            selected_color="#1a5a7a",
            selected_hover_color="#1a6a8a",
            unselected_color="#1a1a2e",
            unselected_hover_color="#252540"
        )
        # Устанавливаем начальное значение
        initial_model = "Точная (0.22)" if self.config.vosk_model_size == "large" else "Быстрая (0.42)"
        self.model_toggle.set(initial_model)
        self.model_toggle.pack(anchor="w", pady=(2, 0))

        # Выбор устройства (CTkOptionMenu)
        device_frame = ctk.CTkFrame(top_controls, corner_radius=0, fg_color="transparent")
        device_frame.pack(side="right")

        ctk.CTkLabel(
            device_frame, text="Микрофон:",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_secondary
        ).pack(anchor="w")

        self.device_menu = ctk.CTkOptionMenu(
            device_frame,
            values=self._device_names,
            command=self._on_device_change,
            width=240,
            font=get_font_tuple(FONTS.size_small)
        )
        self.device_menu.pack(pady=(2, 0))

        # Слайдеры
        bottom_controls = ctk.CTkFrame(control_panel, corner_radius=0, fg_color="transparent")
        bottom_controls.pack(fill="x", padx=SPACING.sm, pady=(0, SPACING.xs))

        # Слайдер чувствительности
        sensitivity_frame = ctk.CTkFrame(bottom_controls, corner_radius=0, fg_color="transparent")
        sensitivity_frame.pack(side="left", fill="x", expand=True, padx=(0, SPACING.md))

        sens_header = ctk.CTkFrame(sensitivity_frame, corner_radius=0, fg_color="transparent")
        sens_header.pack(fill="x")

        ctk.CTkLabel(
            sens_header, text="Чувствительность микрофона:",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_secondary
        ).pack(side="left")

        self.sensitivity_label = ctk.CTkLabel(
            sens_header, text=str(self.config.sensitivity),
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.accent_primary,
            width=50
        )
        self.sensitivity_label.pack(side="right")

        self.sensitivity_slider = ctk.CTkSlider(
            sensitivity_frame,
            from_=100, to=2000,
            number_of_steps=38,
            command=self._on_sensitivity_change
        )
        self.sensitivity_slider.set(self.config.sensitivity)
        self.sensitivity_slider.pack(fill="x", pady=(2, 0))

        # Слайдер VAD
        vad_frame = ctk.CTkFrame(bottom_controls, corner_radius=0, fg_color="transparent")
        vad_frame.pack(side="right", fill="x", expand=True)

        vad_header = ctk.CTkFrame(vad_frame, corner_radius=0, fg_color="transparent")
        vad_header.pack(fill="x")

        ctk.CTkLabel(
            vad_header, text="Порог голоса (VAD):",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_secondary
        ).pack(side="left")

        self.vad_label = ctk.CTkLabel(
            vad_header, text=str(self.config.vad_threshold),
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.accent_primary,
            width=50
        )
        self.vad_label.pack(side="right")

        self.vad_slider = ctk.CTkSlider(
            vad_frame,
            from_=200, to=1000,
            number_of_steps=16,
            command=self._on_vad_change
        )
        self.vad_slider.set(self.config.vad_threshold)
        self.vad_slider.pack(fill="x", pady=(2, 0))

        # Центральная панель
        center_panel = ctk.CTkFrame(main_frame, corner_radius=0, fg_color="transparent", border_width=0)
        center_panel.pack(fill="x", pady=(0, SPACING.xs))

        # Контейнер для кнопки записи
        record_container = ctk.CTkFrame(center_panel, corner_radius=0, fg_color="transparent", border_width=0)
        record_container.pack(side="left", padx=(0, SPACING.sm), pady=0, anchor="n")

        self.record_button = RecordButton(record_container, command=self._on_record_toggle, size=34)
        self.record_button.pack(pady=0)

        meter_frame = ctk.CTkFrame(center_panel, corner_radius=0, fg_color="transparent", border_width=0)
        meter_frame.pack(side="left", fill="x", expand=True, pady=0, anchor="n")

        self.recording_status = ctk.CTkLabel(
            meter_frame, text="Нажмите кнопку для начала записи",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_secondary
        )
        self.recording_status.pack(anchor="w", pady=0)

        self.level_meter = LevelMeter(meter_frame, width=360, height=12)
        self.level_meter.pack(anchor="w", pady=0)

        # Кнопки копирования
        export_frame = ctk.CTkFrame(center_panel, corner_radius=0, fg_color="transparent", border_width=0)
        export_frame.pack(side="right", pady=0, anchor="n")

        ctk.CTkButton(
            export_frame, text="Копировать RU",
            command=self._copy_russian,
            width=104,
            height=30,
            font=get_font_tuple(FONTS.size_small, FONTS.weight_bold),
            fg_color=COLORS.button_bg,
            hover_color=COLORS.button_hover,
            text_color=COLORS.text_primary
        ).pack(side="left", padx=1, pady=0, anchor="n")

        ctk.CTkButton(
            export_frame, text="Копировать EN",
            command=self._copy_english,
            width=104,
            height=30,
            font=get_font_tuple(FONTS.size_small, FONTS.weight_bold),
            fg_color=COLORS.button_bg,
            hover_color=COLORS.button_hover,
            text_color=COLORS.accent_primary
        ).pack(side="left", padx=1, pady=0, anchor="n")

        # Область текста - используем CTkFrame как контейнер + tk.Text для tag поддержки
        text_frame = ctk.CTkFrame(main_frame, corner_radius=SPACING.ctk_corner_radius, border_width=0)
        text_frame.pack(fill="both", expand=True, pady=0)

        text_header = ctk.CTkFrame(text_frame, corner_radius=0, fg_color="transparent")
        text_header.pack(fill="x", padx=SPACING.sm, pady=(SPACING.xs, SPACING.xs))

        ctk.CTkLabel(
            text_header, text="Транскрипция и перевод",
            font=get_font_tuple(FONTS.size_normal, FONTS.weight_bold),
            text_color=COLORS.text_primary
        ).pack(side="left")

        ctk.CTkButton(
            text_header, text="Очистить",
            command=self._clear_transcript,
            width=80,
            height=28,
            font=get_font_tuple(FONTS.size_small),
            fg_color=COLORS.button_bg,
            hover_color=COLORS.button_hover,
            text_color=COLORS.text_secondary
        ).pack(side="right")

        # Контейнер для текстовой област�� (tk.Text для поддержки tag_config)
        text_container = ctk.CTkFrame(text_frame, corner_radius=0, fg_color=COLORS.bg_tertiary)
        text_container.pack(fill="both", expand=True, padx=SPACING.sm, pady=(0, SPACING.xs))

        # Scrollbar
        scrollbar = ctk.CTkScrollbar(text_container)
        scrollbar.pack(side="right", fill="y")

        # tk.Text для поддержки tag_configure и tag_add
        self.text_area = tk.Text(
            text_container, font=get_font_tuple(self.config.font_size),
            fg=COLORS.text_primary, bg=COLORS.bg_tertiary,
            insertbackground=COLORS.text_primary,
            selectbackground=COLORS.accent_primary,
            selectforeground=COLORS.bg_primary,
            wrap="word", padx=SPACING.sm, pady=SPACING.sm,
            yscrollcommand=scrollbar.set, state="normal",
            undo=True,
            borderwidth=0,
            highlightthickness=0
        )
        self.text_area.pack(fill="both", expand=True)
        scrollbar.configure(command=self.text_area.yview)

        # Контекстное меню для редактирования
        self._create_context_menu()

        # Теги форматирования
        self.text_area.tag_configure("timestamp", foreground=COLORS.text_muted,
                                     font=get_font_tuple(FONTS.size_small))
        self.text_area.tag_configure("original", foreground=COLORS.text_primary)
        self.text_area.tag_configure("translation", foreground=COLORS.accent_primary,
                                     lmargin1=30, lmargin2=30)
        self.text_area.tag_configure("partial", foreground=COLORS.text_secondary,
                                     font=get_font_tuple(self.config.font_size, "italic"))

    def _create_context_menu(self):
        """Создаёт контекстное меню для текстовой области."""
        self.context_menu = tk.Menu(self.root, tearoff=0,
                                    bg=COLORS.bg_secondary, fg=COLORS.text_primary,
                                    activebackground=COLORS.accent_primary,
                                    activeforeground=COLORS.bg_primary)
        self.context_menu.add_command(label="Вырезать", command=self._cut_text,
                                      accelerator="⌘X")
        self.context_menu.add_command(label="Копировать", command=self._copy_selection,
                                      accelerator="⌘C")
        self.context_menu.add_command(label="Вставить", command=self._paste_text,
                                      accelerator="⌘V")
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Выделить всё", command=self._select_all,
                                      accelerator="⌘A")
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Отменить", command=self._undo,
                                      accelerator="⌘Z")
        self.context_menu.add_command(label="Повторить", command=self._redo,
                                      accelerator="⇧⌘Z")
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Скопировать 🇷🇺 русский", command=self._copy_russian)
        self.context_menu.add_command(label="Скопировать 🇺🇸 английский", command=self._copy_english)

        # Привязка контекстного меню
        self.text_area.bind("<Button-2>", self._show_context_menu)  # Middle click
        self.text_area.bind("<Control-Button-1>", self._show_context_menu)  # Ctrl+click (macOS)
        if self.root.tk.call('tk', 'windowingsystem') == 'aqua':
            self.text_area.bind("<Button-3>", self._show_context_menu)  # Right click

    def _show_context_menu(self, event):
        """Показывает контекстное меню."""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _cut_text(self):
        """Вырезает выделенный текст."""
        try:
            self._copy_selection()
            self.text_area.delete("sel.first", "sel.last")
        except tk.TclError:
            pass

    def _paste_text(self):
        """Вставляет текст из буфера обмена."""
        try:
            text = self.root.clipboard_get()
            try:
                self.text_area.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
            self.text_area.insert("insert", text)
        except tk.TclError:
            pass

    def _select_all(self):
        """Выделяет весь текст."""
        self.text_area.tag_add("sel", "1.0", "end")
        return "break"

    def _undo(self):
        """Отменяет последнее действие."""
        try:
            self.text_area.edit_undo()
        except tk.TclError:
            pass

    def _redo(self):
        """Повторяет отменённое действие."""
        try:
            self.text_area.edit_redo()
        except tk.TclError:
            pass

    def _setup_bindings(self):
        """Настраивает горячие клавиши."""
        self.root.bind("<Command-r>", lambda e: self._toggle_recording())
        self.root.bind("<Command-s>", lambda e: self._export_txt())
        self.root.bind("<Command-c>", lambda e: self._copy_selection())
        self.root.bind("<Escape>", lambda e: self._stop_recording())
        # Дополнительные горячие клавиши для редактирования
        self.text_area.bind("<Command-a>", lambda e: self._select_all())
        self.text_area.bind("<Command-z>", lambda e: self._undo())
        self.text_area.bind("<Command-Shift-z>", lambda e: self._redo())

    def _start_init_thread(self):
        """Запускает фоновую инициализацию."""
        self.init_thread = threading.Thread(target=self._init_components, name="InitThread", daemon=True)
        self.init_thread.start()

    def _init_components(self):
        """Инициализирует аудио, распознаватели и переводчик."""
        logger.info("Инициализация компонентов...")
        self.engine_manager.state = EngineState.LOADING

        # Аудио
        try:
            self.audio_capture = AudioCapture(
                sample_rate=self.config.sample_rate,
                device_index=self.config.device_index
            )
            self.audio_capture.__enter__()
            self.audio_capture.set_level_callback(self._on_audio_level)

            self.audio_devices = self.audio_capture.get_input_devices()
            self.root.after(0, self._update_device_list)
            logger.info(f"Аудио инициализировано, {len(self.audio_devices)} устройств")
        except Exception as e:
            logger.error(f"Ошибка инициализации аудио: {e}")
            self.root.after(0, lambda: self._show_error("Ошибка", f"Микрофон: {e}"))
            return

        # Vosk
        if VOSK_AVAILABLE:
            try:
                rec_config = RecognitionConfig.from_app_config(self.config)
                # Выбираем путь к модели в зависимости от размера
                model_path = self.config.vosk_model_path
                if self.config.vosk_model_size == "large":
                    model_path = self.config.vosk_large_model_path

                self.vosk_recognizer = VoskRecognizer(
                    rec_config, model_path,
                    phrase_timeout=self.config.vosk_phrase_timeout
                )
                if self.vosk_recognizer.load():
                    logger.info(f"Vosk загружен (модель: {self.config.vosk_model_size})")
                else:
                    self.vosk_recognizer = None
            except Exception as e:
                logger.error(f"Ошибка загрузки Vosk: {e}")
                self.vosk_recognizer = None

        # Переводчик
        if ARGOS_AVAILABLE:
            try:
                self.translator = Translator(cache_size=self.config.translation_cache_size)
                if self.translator.load():
                    logger.info("Переводчик загружен")
                else:
                    self.translator = None
            except Exception as e:
                logger.error(f"Ошибка загрузки переводчика: {e}")
                self.translator = None

        # Устанавливаем текущий движок (только Vosk)
        if self.vosk_recognizer:
            self.current_recognizer = self.vosk_recognizer

        self.engine_manager.state = EngineState.READY
        self.root.after(0, self._update_status)
        logger.info("Инициализация завершена")

    def _update_device_list(self):
        """Обновляет список устройств."""
        self._device_names = [d.name for d in self.audio_devices]
        if self._device_names:
            self.device_menu.configure(values=self._device_names)

            # Ищем устройство по сохранённому имени
            idx = 0
            if self.config.device_name:
                for i, device in enumerate(self.audio_devices):
                    if device.name == self.config.device_name:
                        idx = i
                        break
                else:
                    # Если не нашли по имени, используем device_index
                    idx = min(self.config.device_index, len(self.audio_devices) - 1)
            else:
                idx = min(self.config.device_index, len(self.audio_devices) - 1)

            self.device_menu.set(self._device_names[idx])

            # Устанавливаем устройство в audio_capture
            if self.audio_capture and idx < len(self.audio_devices):
                device = self.audio_devices[idx]
                self.audio_capture.set_device(device.index)
                self.config.device_index = device.index
                self.config.device_name = device.name
                logger.info(f"Восстановлено устройство: {device.name}")

    def _update_status(self):
        """Обновляет статус бар."""
        if self.current_recognizer:
            engine_name = "Vosk"
            self.status_bar.set_engine(engine_name, ready=True)
            model_name = "Russian 0.22" if self.config.vosk_model_size == "large" else "Russian 0.42"
            self.status_bar.set_model(model_name)
        else:
            self.status_bar.set_engine("Не загружен", ready=False)

    def _start_polling(self):
        """Запускает polling."""
        self._poll_results()
        self._poll_stats()

    def _poll_results(self):
        """Проверяет очередь результатов. Ограничиваем до 5 за вызов чтобы не блокировать GUI."""
        try:
            for _ in range(5):
                result = self.result_queue.get_nowait()
                if result is None:
                    break
                self._process_result(result)
        except Exception as e:
            logger.error(f"Ошибка обработки результата: {e}")

        if self.root:
            self.root.after(50, self._poll_results)

    def _poll_stats(self):
        """Обновляет статистику."""
        try:
            if PSUTIL_AVAILABLE:
                cpu = psutil.cpu_percent(interval=None)
                self.status_bar.set_cpu(cpu)

            if self.translator and self.translator.is_loaded:
                stats = self.translator.cache_stats
                self.status_bar.set_cache(stats["hit_rate"])
        except Exception as e:
            logger.debug(f"Ошибка статистики: {e}")

        if self.root:
            self.root.after(1000, self._poll_stats)

    def _process_result(self, result: RecognitionResult):
        """Обрабатывает результат распознавания."""
        if result.is_final:
            # Очистить возможный запланированный partial и удалить его из UI
            if hasattr(self, "_partial_timer_id") and self._partial_timer_id:
                try:
                    self.root.after_cancel(self._partial_timer_id)
                except Exception:
                    pass
                self._partial_timer_id = None
            self._pending_partial_text = ""
            self._clear_partial_text()

            # Добавляем финальную русскую фразу сразу (без перевода)
            entry = TranscriptEntry(result.text, "", result.timestamp)
            self.transcript.append(entry)

            ui_insert_index = self._append_final_original(entry)

            # Асинхронный перевод только финальных фраз, чтобы не блокировать GUI
            if self.translator and self.translator.is_loaded:
                t0 = time.perf_counter()
                future = self.translator.translate_async(result.text)

                def _on_done(fut):
                    try:
                        translated = fut.result() or ""
                    except Exception as e:
                        logger.error(f"Ошибка асинхронного перевода: {e}")
                        translated = ""

                    t1 = time.perf_counter()
                    logger.debug(f"[translate] done in {(t1 - t0):.3f}s, len={len(result.text)} cache={translated != ''}")

                    # Обновляем UI в главном потоке
                    if self.root:
                        def _apply():
                            entry.translated = translated
                            if translated:
                                try:
                                    # Вставляем перевод под оригиналом, даже если появились новые строки
                                    self.text_area.insert(ui_insert_index, "→ " + translated + "\n\n", ("translation",))
                                except Exception as ex:
                                    logger.debug(f"UI insert translation failed: {ex}")
                            # Прокрутка вниз
                            self.text_area.see("end")
                        try:
                            self.root.after(0, _apply)
                        except Exception:
                            _apply()

                future.add_done_callback(_on_done)
        else:
            # Троттлим обновления partial: одна "живая" строка, не чаще ~120мс
            self._pending_partial_text = result.text
            self._schedule_partial_update()

    def _add_to_text_area(self, entry: TranscriptEntry):
        """Добавляет запись в текстовую область (устаревший метод, оставлен для совместимости)."""
        return self._append_final_original(entry)

    def _append_final_original(self, entry: TranscriptEntry) -> str:
        """Добавляет финальную русскую фразу и возвращает mark-индекс для последующей вставки перевода."""
        try:
            t0 = time.perf_counter()
            time_str = datetime.fromtimestamp(entry.timestamp).strftime("[%H:%M:%S] ")
            self.text_area.insert("end", time_str, ("timestamp",))
            self.text_area.insert("end", entry.original + "\n", ("original",))

            # Создаём mark, куда позже вставим перевод
            mark_name = f"tr_mark_{int(entry.timestamp * 1000)}"
            try:
                self.text_area.mark_set(mark_name, "end")
                self.text_area.mark_gravity(mark_name, "left")
            except Exception as ex:
                logger.debug(f"Mark set failed: {ex}")
                mark_name = "end"

            self.text_area.see("end")
            t1 = time.perf_counter()
            logger.debug(f"[final-insert] len={len(entry.original)} took={(t1 - t0):.3f}s")

            # Ограничиваем размер текстовой области — удаляем старые строки при превышении лимита
            self._trim_text_area_if_needed()

            return mark_name
        except Exception as e:
            logger.error(f"Ошибка в��тавки финального текста: {e}")
            return "end"

    def _trim_text_area_if_needed(self, max_lines: int = 500):
        """Удаляет старые строки из текстовой области если превышен лимит."""
        try:
            line_count = int(self.text_area.index("end-1c").split(".")[0])
            if line_count > max_lines:
                # Удаляем первые строки с запасом
                delete_to = f"{line_count - max_lines + 50}.0"
                self.text_area.delete("1.0", delete_to)
        except Exception as e:
            logger.debug(f"Trim text area failed: {e}")

    def _clear_partial_text(self):
        """Удаляет partial текст (одна живая строка) из области."""
        try:
            if self.text_area:
                # Удаляем от mark до конца
                if self._partial_mark_name in self.text_area.mark_names():
                    self.text_area.delete(self._partial_mark_name, "end")
                    try:
                        self.text_area.mark_unset(self._partial_mark_name)
                    except Exception:
                        pass
                try:
                    self.text_area.tag_remove("partial", "1.0", "end")
                except tk.TclError:
                    pass
            self._last_applied_partial = ""
        except tk.TclError:
            pass

    def _schedule_partial_update(self):
        """Планирует отложённое обновление partial с троттлингом из конфига."""
        if not self.root:
            return
        # Отменяем предыдущий таймер
        if self._partial_timer_id:
            try:
                self.root.after_cancel(self._partial_timer_id)
            except Exception:
                pass
            self._partial_timer_id = None
        # Планируем новый с учётом конфига
        delay_ms = int(self._partial_throttle_ms)
        self._partial_timer_id = self.root.after(delay_ms, self._apply_partial_update)

    def _apply_partial_update(self):
        """Применяет отложенное обновление partial-строки."""
        self._partial_timer_id = None
        text = (self._pending_partial_text or "").strip()
        if not text:
            self._clear_partial_text()
            return

        if not self.text_area:
            return

        # Ограничиваем длину partial-текста чтобы избежать переполнения
        MAX_PARTIAL_LEN = 500
        if len(text) > MAX_PARTIAL_LEN:
            text = text[:MAX_PARTIAL_LEN] + "..."

        try:
            t0 = time.perf_counter()
            # Устанавливаем mark при первом обновлении
            if self._partial_mark_name not in self.text_area.mark_names():
                self.text_area.mark_set(self._partial_mark_name, "end")
                self.text_area.mark_gravity(self._partial_mark_name, "left")

            try:
                self.text_area.tag_remove("partial", "1.0", "end")
            except tk.TclError:
                pass

            # Переписываем только хвост от mark до конца
            self.text_area.delete(self._partial_mark_name, "end")
            self.text_area.insert("end", "⏳ " + text + "...\n", ("partial",))
            self.text_area.see("end")
            t1 = time.perf_counter()
            logger.debug(f"[partial-insert] len={len(text)} took={(t1 - t0):.3f}s")
            self._last_applied_partial = text
        except Exception as e:
            logger.debug(f"Partial update failed: {e}")

    def _clear_partial_text_compat(self):
        """Совместимость: устаревший метод, не используется."""
        pass

    def _update_partial_text(self):
        """Обновляет частичный текст."""
        if not self._partial_text:
            return

        # Удаляем предыдущий partial
        self._clear_partial_text()

        # Добавляем новый partial текст
        self.text_area.insert("end", "⏳ " + self._partial_text + "...\n", ("partial",))
        self.text_area.see("end")

    def _on_record_toggle(self, is_recording: bool):
        """Обработчик переключения записи."""
        if is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _toggle_recording(self):
        """Переключает состояние записи."""
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Начинает запись."""
        if self._is_recording:
            return

        if not self.current_recognizer:
            self._show_error("Ошибка", "Движок распознавания не загружен")
            self.record_button.set_recording(False)
            return

        if not self.audio_capture:
            self._show_error("Ошибка", "Аудио не инициализировано")
            self.record_button.set_recording(False)
            return

        if not self.audio_capture.start_capture():
            self._show_error("Ошибка", "Не удалось начать запись")
            self.record_button.set_recording(False)
            return

        self.current_recognizer.reset()
        self.result_queue.clear()
        self._partial_text = ""

        self.recognition_thread = StoppableThread(target=self._recognition_loop, name="RecognitionThread")
        self._is_recording = True
        self.recognition_thread.start()

        self.engine_manager.state = EngineState.RECORDING
        self.recording_status.configure(text="🔴 Запись...", text_color=COLORS.accent_error)
        self.record_button.set_recording(True)

        logger.info("Запись начата")

    def _stop_recording(self):
        """Останавливает запись."""
        if not self._is_recording:
            return

        self._is_recording = False

        if self.recognition_thread:
            self.recognition_thread.stop()
            self.recognition_thread.join(timeout=2.0)
            self.recognition_thread = None

        if self.audio_capture:
            self.audio_capture.stop_capture()

        self.engine_manager.state = EngineState.READY
        self.recording_status.configure(text="Нажмите кнопку для начала записи", text_color=COLORS.text_secondary)
        self.level_meter.reset()
        self.record_button.set_recording(False)

        # Очищаем partial текст
        self._clear_partial_text()

        logger.info("Запись остановлена")

    def _recognition_loop(self):
        """Основной цикл распознавания."""
        logger.debug("Recognition loop запущен")

        while self._is_recording and self.recognition_thread and not self.recognition_thread.stopped():
            try:
                chunk = self.audio_capture.get_audio_chunk(timeout=0.1)
                if chunk is None:
                    continue

                for result in self.current_recognizer.recognize_stream(chunk):
                    self.result_queue.put(result)

            except Exception as e:
                logger.error(f"Ошибка в recognition loop: {e}")
                break

        logger.debug("Recognition loop завершён")

    def _on_device_change(self, device_name: str):
        """Обработчик смены устройства."""
        if self._is_recording:
            self._show_error("Внимание", "Остановите запись перед сменой устройства")
            return

        # Находим индекс устройства по имени
        idx = -1
        for i, name in enumerate(self._device_names):
            if name == device_name:
                idx = i
                break

        if 0 <= idx < len(self.audio_devices):
            device = self.audio_devices[idx]
            if self.audio_capture:
                self.audio_capture.set_device(device.index)
            self.config.device_index = device.index
            self.config.device_name = device.name
            self._save_config()
            logger.info(f"Выбрано устройство: {device.name}")

    def _on_sensitivity_change(self, value: float):
        """Обработчик изменения чувствительности."""
        int_value = int(value)
        self.sensitivity_label.configure(text=str(int_value))
        self.config.sensitivity = int_value
        self._save_config()

    def _on_vad_change(self, value: float):
        """Обработчик изменения VAD порога."""
        int_value = int(value)
        self.vad_label.configure(text=str(int_value))
        self.config.vad_threshold = int_value
        if self.vosk_recognizer:
            self.vosk_recognizer.config.vad_threshold = int_value
        self._save_config()

    def _on_model_change(self, model_name: str):
        """Обработчик смены модели Vosk."""
        if self._is_recording:
            self._show_error("Внимание", "Остановите запись перед сменой модели")
            # Возвращаем предыдущее значение
            prev_model = "Точная (0.22)" if self.config.vosk_model_size == "large" else "Быстрая (0.42)"
            self.model_toggle.set(prev_model)
            return

        # Определяем новый размер модели
        new_size = "large" if "0.22" in model_name else "small"

        if new_size == self.config.vosk_model_size:
            return  # Модель не изменилась

        # Проверяем наличие модели
        from pathlib import Path
        model_path = self.config.vosk_large_model_path if new_size == "large" else self.config.vosk_model_path
        if not Path(model_path).exists():
            self._show_error(
                "Модель не найдена",
                f"Модель не найдена: {model_path}\n\n"
                f"Скачайте модель:\n"
                f"wget https://alphacephei.com/vosk/models/vosk-model-ru-{'0.22' if new_size == 'large' else '0.42'}.zip\n"
                f"unzip vosk-model-ru-{'0.22' if new_size == 'large' else '0.42'}.zip -d models/"
            )
            # Возвращаем предыдущее значение
            prev_model = "Точная (0.22)" if self.config.vosk_model_size == "large" else "Быстрая (0.42)"
            self.model_toggle.set(prev_model)
            return

        # Обновляем конфигурацию
        self.config.vosk_model_size = new_size
        self._save_config()

        # Перезагружаем Vosk с новой моделью
        self._reload_vosk_model()

    def _reload_vosk_model(self):
        """Перезагружает Vosk с текущей моделью из config."""
        if not VOSK_AVAILABLE:
            return

        # Показываем статус загрузки
        self.status_bar.set_engine("Загрузка...", ready=False)
        self.status_bar.set_model("...")

        def reload_in_thread():
            # Выгружаем старую модель
            if self.vosk_recognizer:
                self.vosk_recognizer.unload()
                self.vosk_recognizer = None
                self.current_recognizer = None

            # Загружаем новую модель
            try:
                rec_config = RecognitionConfig.from_app_config(self.config)
                model_path = self.config.vosk_model_path
                if self.config.vosk_model_size == "large":
                    model_path = self.config.vosk_large_model_path

                self.vosk_recognizer = VoskRecognizer(
                    rec_config, model_path,
                    phrase_timeout=self.config.vosk_phrase_timeout
                )
                if self.vosk_recognizer.load():
                    self.current_recognizer = self.vosk_recognizer
                    logger.info(f"Vosk перезагружен (модель: {self.config.vosk_model_size})")
                else:
                    self.vosk_recognizer = None
                    logger.error("Не удалось загрузить Vosk модель")
            except Exception as e:
                logger.error(f"Ошибка перезагрузки Vosk: {e}")
                self.vosk_recognizer = None

            # Обновляем UI в главном потоке
            self.root.after(0, self._update_status)

        # Запускаем в фоновом потоке
        threading.Thread(target=reload_in_thread, name="VoskReloadThread", daemon=True).start()

    def _save_config(self):
        """Сохраняет конфигурацию в файл."""
        self.config.save()

    def _on_audio_level(self, level: float):
        """Обработчик уровня громкости (вызывается из audio thread)."""
        # ВАЖНО: Маршалим обновление UI в главный поток для thread safety
        if self.level_meter and self.root:
            self.root.after(0, lambda l=level: self.level_meter.set_level(l))

    def _clear_transcript(self):
        """Очищает транскрипт."""
        self.transcript.clear()
        self.text_area.delete("1.0", "end")
        logger.info("Транскрипт очищен")

    def _copy_selection(self):
        """Копирует выделенный текст."""
        try:
            selection = self.text_area.get("sel.first", "sel.last")
            self.root.clipboard_clear()
            self.root.clipboard_append(selection)
        except tk.TclError:
            pass

    def _copy_russian(self):
        """Копирует весь русский текст (оригинал) в буфер обмена."""
        if not self.transcript:
            return

        russian_text = "\n".join(entry.original for entry in self.transcript)
        self.root.clipboard_clear()
        self.root.clipboard_append(russian_text)
        logger.info("Русский текст скопирован в буфер обмена")

    def _copy_english(self):
        """Копирует весь английский текст (перевод) в буфер обмена."""
        if not self.transcript:
            return

        english_text = "\n".join(entry.translated for entry in self.transcript if entry.translated)
        self.root.clipboard_clear()
        self.root.clipboard_append(english_text)
        logger.info("Английский текст скопирован в буфер обмена")

    def _export_txt(self):
        """Экспортирует в TXT."""
        if not self.transcript:
            self._show_error("Внимание", "Нет данных для экспорта")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    for entry in self.transcript:
                        time_str = datetime.fromtimestamp(entry.timestamp).strftime("[%H:%M:%S]")
                        f.write(f"{time_str} {entry.original}\n")
                        if entry.translated:
                            f.write(f"         → {entry.translated}\n")
                        f.write("\n")
                logger.info(f"Экспортировано в {path}")
            except IOError as e:
                self._show_error("Ошибка", f"Не удалось сохранить: {e}")

    def _export_json(self):
        """Экспортирует в JSON."""
        if not self.transcript:
            self._show_error("Внимание", "Нет данных для экспорта")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        if path:
            try:
                data = {
                    "version": self.VERSION,
                    "engine": self.config.engine,
                    "entries": [e.to_dict() for e in self.transcript]
                }
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"Экспортировано в {path}")
            except IOError as e:
                self._show_error("Ошибка", f"Не удалось сохранить: {e}")

    def _export_srt(self):
        """Экспортирует в SRT."""
        if not self.transcript:
            self._show_error("Внимание", "Нет данных для экспорта")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".srt",
            filetypes=[("SRT files", "*.srt"), ("All files", "*.*")],
            initialfile=f"subtitles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.srt"
        )

        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    for i, entry in enumerate(self.transcript, 1):
                        start_time = datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S,000")
                        end_time = datetime.fromtimestamp(entry.timestamp + 3).strftime("%H:%M:%S,000")

                        f.write(f"{i}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{entry.original}\n")
                        if entry.translated:
                            f.write(f"{entry.translated}\n")
                        f.write("\n")
                logger.info(f"Экспортировано в {path}")
            except IOError as e:
                self._show_error("Ошибка", f"Не удалось сохранить: {e}")

    def _show_error(self, title: str, message: str):
        """Показывает сообщение об ошибке."""
        messagebox.showerror(title, message)

    def _on_close(self):
        """Обработчик закрытия окна."""
        logger.info("Закрытие приложения...")

        self._stop_recording()
        self.config.save()

        if self.audio_capture:
            self.audio_capture.__exit__(None, None, None)

        if self.vosk_recognizer:
            self.vosk_recognizer.unload()

        if self.translator:
            self.translator.unload()

        self.root.destroy()
        self.root = None
