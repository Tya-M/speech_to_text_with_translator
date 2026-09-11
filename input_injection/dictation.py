"""
Глобальная диктовка (push-to-talk) для macOS.

Сценарий (как в jot): зажал клавишу → говоришь → отпустил → текст появляется
в месте курсора в том приложении, где вы уже работаете. Всё офлайн: распознаёт
локальная модель GigaAM или Parakeet, без сторонних сервисов. Переводчик не
задействован.

GigaAM — распознаватель целых высказываний, поэтому push-to-talk для него идеален:
мы копим весь захваченный звук пока клавиша зажата, а на отпускании отправляем
целую фразу на распознавание — без дробления по паузам.

Требования macOS: разрешения Accessibility (печать в чужие окна),
 Input Monitoring (глобальный перехват клавиш) и Microphone.
"""

import logging
import queue
import sys
import threading
from typing import Callable, Optional

import numpy as np
from pynput import keyboard

from audio.capture import AudioCapture
from recognition.gigaam_engine import GigaAMRecognizer
from recognition.parakeet_engine import ParakeetRecognizer
from utils.config import AppConfig, RecognitionConfig
from .cursor_typer import (
    CursorTyper,
    app_display_name,
    get_frontmost_app,
    is_accessibility_trusted,
)

logger = logging.getLogger("voice_translator.input_injection.dictation")


def resolve_key(spec: str):
    """Преобразует строку вроде 'f9' или '<f9>' или 'v' в объект pynput."""
    s = (spec or "").strip().lower().strip("<>")
    if hasattr(keyboard.Key, s):
        return getattr(keyboard.Key, s)
    if len(s) == 1:
        return keyboard.KeyCode.from_char(s)
    raise ValueError(f"Не распознана клавиша: {spec!r}")


class DictationService:
    """Глобальная диктовка с печатью в место курсора."""

    def __init__(
        self,
        app_config: Optional[AppConfig] = None,
        trigger_key: str = "f9",
        mode: str = "hold",              # "hold" (push-to-talk) или "toggle"
        engine: str = "gigaam",
        on_status: Optional[Callable[[str], None]] = None,
        recognizer=None,                 # можно передать уже загруженный распознаватель
    ):
        self.config = app_config or AppConfig.load()
        self.rec_config = RecognitionConfig.from_app_config(self.config)
        self.trigger = resolve_key(trigger_key)
        self.mode = mode
        self.engine = (engine or "gigaam").strip().lower()
        if self.engine not in {"gigaam", "parakeet"}:
            raise ValueError(f"Неизвестный движок диктовки: {engine!r}")
        self.on_status = on_status or (lambda s: logger.info(s))
        self._secondary_recognizer = None
        self._owns_secondary_recognizer = False

        # Если распознаватель передан извне (например, из GUI) — переиспользуем его,
        # чтобы не грузить тяжёлую модель GigaAM второй раз и не занимать лишнюю память.
        if recognizer is not None:
            self.recognizer = recognizer
            self._owns_recognizer = False
        else:
            if self.engine == "parakeet":
                self.recognizer = ParakeetRecognizer(
                    self.rec_config,
                    model_path=self.config.parakeet_model_path,
                    num_threads=self.config.parakeet_num_threads,
                )
            else:
                self.recognizer = GigaAMRecognizer(
                    self.rec_config,
                    model_name=self.config.gigaam_model,
                    device=self.config.gigaam_device,
                    language=self.config.gigaam_language,
                )
            self._owns_recognizer = True

        # Parakeet Unified EN has an English-only vocabulary. Keep it as the
        # primary model, but also load GigaAM so Russian utterances can be
        # recognized automatically when Parakeet is selected.
        if self.engine == "parakeet":
            self._secondary_recognizer = GigaAMRecognizer(
                self.rec_config,
                model_name=self.config.gigaam_model,
                device=self.config.gigaam_device,
                language=self.config.gigaam_language,
            )
            self._owns_secondary_recognizer = True

        # Вставка через буфер сохраняет Unicode и не зависит от активной раскладки.
        # Клавиатурные способы остаются резервом, если буфер недоступен.
        self.typer = CursorTyper(prefer="paste")

        self._audio: Optional[AudioCapture] = None
        self._listener: Optional[keyboard.Listener] = None
        self._control_queue: queue.Queue[Optional[str]] = queue.Queue()
        self._control_thread: Optional[threading.Thread] = None
        self._collector: Optional[threading.Thread] = None
        self._transcription_queue: queue.Queue[Optional[bytes]] = queue.Queue()
        self._transcription_thread: Optional[threading.Thread] = None
        self._buffer = bytearray()
        self._recording = threading.Event()
        self._lock = threading.Lock()
        self._running = False
        self._target_app = None                 # приложение, активное в момент начала записи
        self._trigger_vk = self._compute_trigger_vk()

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> bool:
        """Загружает модель, открывает микрофон и вешает глобальный хук."""
        if self._running:
            return True

        # Свою модель загружаем; переданную извне считаем уже загруженной.
        if self._owns_recognizer:
            model_label = (
                "Parakeet + GigaAM (Russian/English)"
                if self.engine == "parakeet"
                else "GigaAM Russian"
            )
            self.on_status(f"Загрузка модели {model_label}…")
            if not self.recognizer.load():
                self.on_status(f"Ошибка: не удалось загрузить {model_label}")
                return False
        else:
            self.on_status("Использую уже загруженную модель…")

        # stop() releases the secondary model; recreate it if this service is
        # started again instead of silently reverting to English-only mode.
        if self.engine == "parakeet" and self._secondary_recognizer is None:
            self._secondary_recognizer = GigaAMRecognizer(
                self.rec_config,
                model_name=self.config.gigaam_model,
                device=self.config.gigaam_device,
                language=self.config.gigaam_language,
            )
            self._owns_secondary_recognizer = True

        if self._secondary_recognizer:
            self.on_status("Загрузка русской модели GigaAM…")
            if not self._secondary_recognizer.load():
                logger.warning("GigaAM unavailable; Parakeet will run in English-only mode")
                self._secondary_recognizer = None

        self._audio = AudioCapture(
            sample_rate=self.config.sample_rate,
            device_index=self.config.device_index,
            sensitivity=self.config.sensitivity,
        )
        self._audio.__enter__()  # инициализируем PyAudio

        self._running = True
        self._control_thread = threading.Thread(
            target=self._control_loop, name="DictationControl", daemon=True
        )
        self._control_thread.start()
        self._transcription_thread = threading.Thread(
            target=self._transcription_loop, name="DictationTranscription", daemon=True
        )
        self._transcription_thread.start()

        listener_kwargs = dict(on_press=self._on_press, on_release=self._on_release)
        # На macOS подавляем САМУ клавишу-триггер, чтобы она не уходила в
        # активное приложение (иначе F9 вызывает бип/escape-код).
        if sys.platform == "darwin":
            listener_kwargs["darwin_intercept"] = self._darwin_intercept
        try:
            self._listener = keyboard.Listener(**listener_kwargs)
            self._listener.start()
        except Exception as exc:
            logger.error("Не удалось запустить глобальный перехват клавиш: %s", exc)
            self._running = False
            self._control_queue.put(None)
            self._transcription_queue.put(None)
            if self._control_thread:
                self._control_thread.join(timeout=2.0)
                self._control_thread = None
            if self._transcription_thread:
                self._transcription_thread.join(timeout=2.0)
                self._transcription_thread = None
            if self._audio:
                try:
                    self._audio.__exit__(None, None, None)
                except Exception:
                    pass
                self._audio = None
            if self._owns_recognizer:
                self.recognizer.unload()
            if self._owns_secondary_recognizer and self._secondary_recognizer:
                self._secondary_recognizer.unload()
                self._secondary_recognizer = None
            self.on_status("Ошибка: не удалось включить глобальную диктовку")
            return False

        # Предупреждаем заранее, если нет Accessibility — иначе текст не будет
        # вставляться под курсор (синтетические нажатия будут отброшены).
        if is_accessibility_trusted() is False:
            self.on_status(
                "⚠ Нет разрешения «Универсальный доступ» (Accessibility): текст НЕ будет "
                "печататься под курсором. Выдайте его терминалу и перезапустите."
            )

        self.on_status(
            f"Готово. Поставьте курсор в ДРУГОЕ окно, удерживайте [{self._key_label()}] и говорите."
        )
        return True

    def stop(self) -> None:
        """Останавливает сервис и освобождает ресурсы."""
        self._running = False

        if self._listener:
            self._listener.stop()
            self._listener = None

        if self._recording.is_set():
            self._finish_recording()

        if self._control_thread:
            self._control_queue.put(None)
            self._control_thread.join(timeout=2.0)
            self._control_thread = None

        if self._transcription_thread:
            # Queue the sentinel after all pending utterances so normal shutdown
            # preserves output order and gives the last utterance a chance to finish.
            self._transcription_queue.put(None)
            self._transcription_thread.join(timeout=5.0)
            if self._transcription_thread.is_alive():
                logger.warning("Поток распознавания не завершился вовремя")
            self._transcription_thread = None

        if self._audio:
            try:
                self._audio.__exit__(None, None, None)
            except Exception:
                pass
            self._audio = None
        # Выгружаем модель только если она наша; общий распознаватель GUI не трогаем.
        if self._owns_recognizer:
            self.recognizer.unload()
        if self._owns_secondary_recognizer and self._secondary_recognizer:
            self._secondary_recognizer.unload()
            self._secondary_recognizer = None
        self.on_status("Остановлено.")

    def run_forever(self) -> None:
        """Блокирующий запуск для standalone-режима."""
        if not self.start():
            return
        try:
            if self._listener:
                self._listener.join()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    # --------------------------------------------------------------- workers
    def _control_loop(self) -> None:
        """Выполняет команды записи вне macOS event-tap callback."""
        while True:
            action = self._control_queue.get()
            try:
                if action is None:
                    return
                if action == "begin":
                    self._begin_recording()
                elif action == "finish":
                    self._finish_recording()
                elif action == "toggle":
                    if self._recording.is_set():
                        self._finish_recording()
                    else:
                        self._begin_recording()
            except Exception:
                logger.exception("Ошибка обработки команды диктовки: %s", action)
                self.on_status("Ошибка управления записью")
            finally:
                self._control_queue.task_done()

    def _transcription_loop(self) -> None:
        """Последовательно распознаёт завершённые диктовочные записи."""
        while True:
            data = self._transcription_queue.get()
            try:
                if data is None:
                    return
                self._transcribe_and_type(data)
            except Exception:
                logger.exception("Ошибка потока распознавания диктовки")
                self.on_status("Ошибка распознавания")
            finally:
                self._transcription_queue.task_done()

    # ------------------------------------------------------------------ hotkey
    def _compute_trigger_vk(self):
        """Виртуальный keycode триггера (для подавления через darwin_intercept)."""
        t = self.trigger
        val = getattr(t, "value", None) or t
        return getattr(val, "vk", None)

    def _darwin_intercept(self, event_type, event):
        """Подавляет ТОЛЬКО клавишу-триггер (остальные клавиши пропускаем)."""
        try:
            import Quartz
            keycode = Quartz.CGEventGetIntegerValueField(
                event, Quartz.kCGKeyboardEventKeycode
            )
            if self._trigger_vk is not None and keycode == self._trigger_vk:
                return None  # поглощаем событие → нет бипа и не уходит в приложение
        except Exception:
            pass
        return event

    def _matches(self, key) -> bool:
        try:
            return key == self.trigger or (
                self._listener is not None and self._listener.canonical(key) == self.trigger
            )
        except Exception:
            return key == self.trigger

    def _on_press(self, key) -> None:
        if not self._matches(key):
            return
        if self.mode == "toggle":
            self._request_recording_action("toggle")
        else:  # hold
            self._request_recording_action("begin")

    def _on_release(self, key) -> None:
        if self.mode != "hold":
            return
        if self._matches(key):
            # Do not check _recording here: a release can arrive while the
            # worker is still opening the stream, and queue order must be kept.
            self._request_recording_action("finish")

    def _request_recording_action(self, action: str) -> None:
        """Queues a recording action; safe to call from the event tap callback."""
        if self._running:
            self._control_queue.put(action)

    # ------------------------------------------------------------------ recording
    def _begin_recording(self) -> None:
        with self._lock:
            if self._recording.is_set() or not self._audio or not self._running:
                return
            self._buffer = bytearray()
            if not self._audio.start_capture():
                self.on_status("Ошибка: не удалось начать захват аудио")
                return
            self._recording.set()
            self._collector = threading.Thread(
                target=self._collect_loop, name="DictationCollector", daemon=True
            )
            self._collector.start()
            self.on_status("Запись… говорите (держите курсор в нужном окне)")

    def _collect_loop(self) -> None:
        """Копит чанки из очереди AudioCapture, пока идёт запись."""
        audio = self._audio
        if audio is None:
            return
        while self._recording.is_set():
            chunk = audio.get_audio_chunk(timeout=0.1)
            if chunk:
                with self._lock:
                    if self._recording.is_set():
                        self._buffer.extend(chunk)

    def _finish_recording(self) -> None:
        with self._lock:
            if not self._recording.is_set():
                return
            self._recording.clear()
            audio = self._audio
            collector = self._collector
            self._collector = None

        # Stop/close PortAudio outside the keyboard callback. The collector
        # exits after _recording is cleared, then its final chunk is copied
        # under the same lock used by the collector.
        if audio:
            audio.stop_capture()
        if collector:
            collector.join(timeout=2.0)

        with self._lock:
            data = bytes(self._buffer)
            self._buffer.clear()

        if not data:
            self.on_status("Пустая запись")
            return

        # A single worker keeps model calls ordered and avoids concurrent access
        # to recognizers that are not guaranteed to be thread-safe.
        self._transcription_queue.put(data)

    def _transcribe_and_type(self, data: bytes) -> None:
        # Диагностика захвата: длительность и громкость сигнала.
        samples = np.frombuffer(data, dtype=np.int16)
        rate = float(self.config.sample_rate or 16000)
        duration = samples.size / rate if rate else 0.0
        if samples.size:
            rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
            peak = int(np.abs(samples).max())
        else:
            rms = 0.0
            peak = 0
        self.on_status(f"Аудио: {duration:.1f} c, RMS={rms:.0f}, пик={peak}")
        if peak < 50:
            self.on_status(
                "⚠ Микрофон отдаёт тишину. Проверьте разрешение «Микрофон» для терминала "
                f"и устройство ввода (сейчас device_index={self.config.device_index})."
            )

        self.on_status("Распознавание…")
        result = self._recognize_cursor(data)

        text = (result.text if result else "").strip()
        if not text:
            self.on_status("Ничего не распознано")
            return

        self.on_status("Распознано: " + text)

        # ВАЖНО: не переносим фокус принудительно. Печатаем в то окно, которое
        # активно ПРЯМО СЕЙЧАС — туда, где пользователь держит курсор. Раньше
        # мы возвращали фокус на окно, где была нажата F9, из-за чего текст
        # уходил не туда, если пользователь успевал переключиться.
        dest = app_display_name(get_frontmost_app())

        # Печатаем распознанный текст без перевода; добавляем пробел для удобства.
        method = self.typer.type_text(text + " ")
        if method:
            where = f" в {dest}" if dest else " под курсором"
            self.on_status(f"✓ Напечатано{where} (способ: {method})")
        else:
            self.on_status(
                "⚠ Распознано, но не удалось напечатать под курсором "
                "(проверьте разрешение Accessibility и перезапустите терминал)."
            )

    def _recognize_cursor(self, data: bytes):
        """Recognize one cursor-dictation utterance in the selected language set."""
        candidates = []
        recognizers = [self.recognizer]
        if self.engine == "parakeet" and self._secondary_recognizer:
            recognizers.append(self._secondary_recognizer)

        for recognizer in recognizers:
            try:
                result = recognizer.recognize(data)
            except Exception as exc:
                logger.error("Ошибка распознавания (%s): %s", recognizer.name, exc)
                continue
            if result and result.text and result.text.strip():
                candidates.append(result)

        if not candidates:
            self.on_status("Ошибка распознавания")
            return None
        if len(candidates) == 1 or self.engine != "parakeet":
            return candidates[0]

        # GigaAM is the Russian candidate. Prefer it whenever its output
        # contains Cyrillic; otherwise keep Parakeet's English transcription.
        russian = next(
            (result for result in candidates if self._contains_cyrillic(result.text)),
            None,
        )
        return russian or candidates[0]

    @staticmethod
    def _contains_cyrillic(text: str) -> bool:
        return any(
            ("а" <= char.lower() <= "я") or char.lower() == "ё"
            for char in text
        )

    # ------------------------------------------------------------------ helpers
    def _key_label(self) -> str:
        try:
            return getattr(self.trigger, "name", None) or self.trigger.char
        except Exception:
            return str(self.trigger)
