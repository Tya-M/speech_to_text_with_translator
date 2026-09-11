"""
Модуль захвата аудио с использованием PyAudio.
Включает управление устройствами и thread-safe буферизацию.
"""

import pyaudio
import numpy as np
import threading
import logging
from typing import Optional, List, Callable
from dataclasses import dataclass
from contextlib import contextmanager

from utils.threading_utils import ThreadSafeQueue, StoppableThread

logger = logging.getLogger("voice_translator.audio")


@dataclass
class AudioDevice:
    """Информация об аудиоустройстве."""
    index: int
    name: str
    channels: int
    sample_rate: int
    is_input: bool
    
    def __str__(self) -> str:
        return f"{self.name} (ch: {self.channels})"


class AudioCapture:
    """
    Менеджер захвата аудио с PyAudio.
    Поддерживает context manager для автоматической очистки ресурсов.
    """
    
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    DEFAULT_RATE = 16000
    CHUNK_SIZE = 512
    
    def __init__(
        self,
        sample_rate: int = DEFAULT_RATE,
        chunk_size: int = CHUNK_SIZE,
        device_index: Optional[int] = None,
        sensitivity: int = 1000,
    ):
        try:
            sample_rate = int(sample_rate)
        except (TypeError, ValueError):
            sample_rate = self.DEFAULT_RATE
        self.sample_rate = sample_rate if 8000 <= sample_rate <= 48000 else self.DEFAULT_RATE

        try:
            chunk_size = int(chunk_size)
        except (TypeError, ValueError):
            chunk_size = self.CHUNK_SIZE
        self.chunk_size = chunk_size if 64 <= chunk_size <= 8192 else self.CHUNK_SIZE

        try:
            device_index = None if device_index is None else int(device_index)
        except (TypeError, ValueError):
            device_index = None
        self.device_index = device_index if device_index is None or device_index >= 0 else None
        self.set_sensitivity(sensitivity)
        
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._audio_queue: ThreadSafeQueue[bytes] = ThreadSafeQueue(maxsize=2000)
        self._capture_thread: Optional[StoppableThread] = None
        self._is_capturing = False
        self._lock = threading.Lock()

        # Callbacks
        self._level_callback: Optional[Callable[[float], None]] = None
        self._error_callback: Optional[Callable[[str], None]] = None
        self._failure_reported = False

        # Сглаживание уровня для предотвращения мерцания UI
        self._smoothed_level: float = 0.0
        self._smoothing_factor: float = 0.3  # 0.0-1.0, меньше = плавнее
        
    def __enter__(self) -> "AudioCapture":
        """Инициализирует PyAudio при входе в context."""
        self._pyaudio = pyaudio.PyAudio()
        logger.info("PyAudio инициализирован")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Освобождает ресурсы при выходе из context."""
        self.stop_capture()
        
        if self._stream:
            try:
                self._stream.close()
            except Exception as e:
                logger.warning(f"Ошибка закрытия потока: {e}")
            self._stream = None
            
        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception as e:
                logger.warning(f"Ошибка завершения PyAudio: {e}")
            self._pyaudio = None
            
        logger.info("PyAudio ресурсы освобождены")
    
    def get_input_devices(self) -> List[AudioDevice]:
        """Возвращает список доступных входных устройств."""
        if not self._pyaudio:
            raise RuntimeError("AudioCapture не инициализирован. Используйте context manager.")
        
        devices = []
        for i in range(self._pyaudio.get_device_count()):
            try:
                info = self._pyaudio.get_device_info_by_index(i)
                if info.get('maxInputChannels', 0) > 0:
                    devices.append(AudioDevice(
                        index=i,
                        name=info.get('name', f'Device {i}'),
                        channels=int(info.get('maxInputChannels', 1)),
                        sample_rate=int(info.get('defaultSampleRate', self.DEFAULT_RATE)),
                        is_input=True
                    ))
            except Exception as e:
                logger.debug(f"Пропуск устройства {i}: {e}")
                
        logger.info(f"Найдено {len(devices)} входных устройств")
        return devices
    
    def get_default_input_device(self) -> Optional[AudioDevice]:
        """Возвращает устройство ввода по умолчанию."""
        if not self._pyaudio:
            raise RuntimeError("AudioCapture не инициализирован")
            
        try:
            info = self._pyaudio.get_default_input_device_info()
            return AudioDevice(
                index=int(info['index']),
                name=info.get('name', 'Default'),
                channels=int(info.get('maxInputChannels', 1)),
                sample_rate=int(info.get('defaultSampleRate', self.DEFAULT_RATE)),
                is_input=True
            )
        except IOError as e:
            logger.error(f"Не удалось получить устройство по умолчанию: {e}")
            return None
    
    def set_device(self, device_index: int) -> bool:
        """Устанавливает устройство захвата."""
        try:
            device_index = int(device_index)
        except (TypeError, ValueError):
            logger.warning("Некорректный индекс устройства: %r", device_index)
            return False
        if device_index < 0:
            logger.warning("Индекс устройства не может быть отрицательным: %s", device_index)
            return False
        with self._lock:
            if self._is_capturing:
                logger.warning("Нельзя сменить устройство во время записи")
                return False
            self.device_index = device_index
            logger.info(f"Установлено устройство: {device_index}")
            return True

    def set_sensitivity(self, sensitivity: int) -> None:
        """Sets software microphone gain; 1000 is neutral."""
        try:
            sensitivity = int(sensitivity)
        except (TypeError, ValueError):
            sensitivity = 1000
        sensitivity = max(100, min(2000, sensitivity))
        self.sensitivity = sensitivity
        self._gain = sensitivity / 1000.0
    
    def set_level_callback(self, callback: Optional[Callable[[float], None]]) -> None:
        """Устанавливает callback для уровня громкости (0.0-1.0)."""
        self._level_callback = callback

    def set_error_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        """Sets a callback for unrecoverable capture-worker failures."""
        self._error_callback = callback
    
    def start_capture(self) -> bool:
        """Начинает захват аудио в фоновом потоке."""
        with self._lock:
            if self._is_capturing:
                logger.warning("Захват уже запущен")
                return False
            
            if not self._pyaudio:
                raise RuntimeError("AudioCapture не инициализирован")
            
            candidates: List[Optional[int]] = []
            if self.device_index is not None:
                candidates.append(self.device_index)

            default_device = self.get_default_input_device()
            if default_device and default_device.index not in candidates:
                candidates.append(default_device.index)

            # Последняя попытка: пусть PortAudio выберет устройство по умолчанию.
            if None not in candidates:
                candidates.append(None)

            last_error: Optional[Exception] = None
            for device_idx in candidates:
                try:
                    self._stream = self._pyaudio.open(
                        format=self.FORMAT,
                        channels=self.CHANNELS,
                        rate=self.sample_rate,
                        input=True,
                        input_device_index=device_idx,
                        frames_per_buffer=self.chunk_size,
                    )

                    if device_idx is not None and self.device_index != device_idx:
                        logger.warning(
                            f"Сохранённое устройство недоступно, переключаемся на device={device_idx}"
                        )
                        self.device_index = device_idx

                    # Очищаем очередь
                    self._audio_queue.clear()

                    # Запускаем поток захвата
                    self._capture_thread = StoppableThread(
                        target=self._capture_loop,
                        name="AudioCaptureThread"
                    )
                    self._failure_reported = False
                    self._is_capturing = True
                    self._capture_thread.start()

                    logger.info(f"Захват аудио начат (device={device_idx}, rate={self.sample_rate})")
                    return True
                except Exception as e:
                    last_error = e
                    logger.warning(f"Не удалось открыть устройство {device_idx}: {e}")
                    if self._stream:
                        try:
                            self._stream.close()
                        except Exception:
                            pass
                        self._stream = None

            logger.error(f"Ошибка запуска захвата: {last_error}")
            self._is_capturing = False
            return False
    
    def stop_capture(self) -> None:
        """Останавливает захват аудио."""
        with self._lock:
            if not self._is_capturing and not self._capture_thread and not self._stream:
                return

            self._is_capturing = False
            capture_thread = self._capture_thread
            self._capture_thread = None
            stream = self._stream
            self._stream = None

        if capture_thread:
            capture_thread.stop()
            capture_thread.join(timeout=2.0)

        if stream:
            try:
                stream.stop_stream()
                stream.close()
            except Exception as e:
                logger.warning(f"Ошибка остановки потока: {e}")

        logger.info("Захват аудио остановлен")

    def _mark_capture_failed(self, reason: str = "Неизвестная ошибка аудиопотока") -> None:
        """Помечает захват остановленным after an unrecoverable read error."""
        # This helper is only called by _capture_loop.  Do not rely on the
        # thread reference here: tests and shutdown paths may invoke the loop
        # directly, and the reference can be cleared concurrently by stop().
        with self._lock:
            if not self._is_capturing or self._failure_reported:
                return
            self._is_capturing = False
            self._failure_reported = True
            callback = self._error_callback
        if callback:
            try:
                callback(reason)
            except Exception:
                logger.exception("Ошибка callback аудиосбоя")

    def _capture_loop(self) -> None:
        """Основной цикл захвата аудио."""
        try:
            while self._is_capturing and self._capture_thread and not self._capture_thread.stopped():
                try:
                    if self._stream and self._stream.is_active():
                        data = self._stream.read(self.chunk_size, exception_on_overflow=False)
                        data = self._apply_sensitivity(data)

                        # Вычисляем уровень громкости со сглаживанием
                        if self._level_callback:
                            audio_array = np.frombuffer(data, dtype=np.int16)
                            raw_level = np.abs(audio_array).mean() / 32768.0
                            raw_level = min(1.0, raw_level * 3)  # Усиливаем для визуализации

                            # Экспоненциальное сглаживание (EMA)
                            self._smoothed_level = (
                                self._smoothing_factor * raw_level +
                                (1 - self._smoothing_factor) * self._smoothed_level
                            )
                            self._level_callback(self._smoothed_level)

                        # Добавляем в очередь
                        try:
                            self._audio_queue.put(data, block=False)
                        except Exception:
                            pass  # Очередь переполнена, пропускаем chunk
                    else:
                        # Не допускаем busy-spin при неожиданно неактивном stream.
                        self._mark_capture_failed("Аудиопоток стал неактивен")
                        logger.error("Аудиопоток стал неактивен")
                        break

                except IOError as e:
                    if "Input overflowed" in str(e):
                        logger.debug("Audio buffer overflow, пропускаем")
                    else:
                        logger.error(f"Ошибка чтения аудио: {e}")
                        self._mark_capture_failed(f"Ошибка чтения аудио: {e}")
                        break
                except Exception as e:
                    logger.error(f"Неожиданная ошибка в capture loop: {e}")
                    self._mark_capture_failed(f"Неожиданная ошибка аудиопотока: {e}")
                    break
        finally:
            # Не оставляем владельцев записи в состоянии capturing после сбоя.
            self._mark_capture_failed()

    def _apply_sensitivity(self, data: bytes) -> bytes:
        """Applies bounded PCM16 gain without wrapping/clipping artifacts."""
        if self._gain == 1.0 or not data:
            return data
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        amplified = np.clip(samples * self._gain, -32768, 32767)
        return amplified.astype(np.int16).tobytes()
    
    def get_audio_chunk(self, timeout: float = 0.1) -> Optional[bytes]:
        """Получает chunk аудио из очереди."""
        return self._audio_queue.get(timeout=timeout)
    
    def get_audio_data(self, duration: float) -> Optional[bytes]:
        """
        Собирает аудиоданные за указанную длительность (в секундах).
        """
        chunks_needed = int(duration * self.sample_rate / self.chunk_size)
        chunks = []
        
        for _ in range(chunks_needed):
            chunk = self.get_audio_chunk(timeout=0.5)
            if chunk:
                chunks.append(chunk)
        
        if chunks:
            return b''.join(chunks)
        return None
    
    @property
    def is_capturing(self) -> bool:
        """Проверяет, идёт ли захват."""
        return self._is_capturing
    
    def audio_to_numpy(self, data: bytes) -> np.ndarray:
        """Конвертирует bytes в numpy array для распознавания."""
        audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        return audio_array / 32768.0  # Нормализация [-1, 1]
