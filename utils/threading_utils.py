"""
Thread-safe утилиты для работы с многопоточностью.
"""

import threading
import queue
from contextlib import contextmanager
from typing import TypeVar, Generic, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum, auto
import logging
import time

logger = logging.getLogger("voice_translator.threading")

T = TypeVar('T')


class ThreadSafeQueue(Generic[T]):
    """Thread-safe очередь с типизацией."""
    
    def __init__(self, maxsize: int = 0):
        self._queue: queue.Queue[T] = queue.Queue(maxsize=maxsize)
    
    def put(self, item: T, block: bool = True, timeout: Optional[float] = None) -> None:
        """Добавляет элемент в очередь."""
        self._queue.put(item, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[T]:
        """Извлекает элемент из очереди. Возвращает None при таймауте."""
        try:
            return self._queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None
    
    def get_nowait(self) -> Optional[T]:
        """Извлекает элемент без ожидания."""
        return self.get(block=False)
    
    def clear(self) -> int:
        """Очищает очередь. Возвращает количество удалённых элементов."""
        count = 0
        while True:
            try:
                self._queue.get_nowait()
                count += 1
            except queue.Empty:
                break
        return count
    
    def qsize(self) -> int:
        """Приблизительный размер очереди."""
        return self._queue.qsize()
    
    def empty(self) -> bool:
        """Проверяет, пуста ли очередь."""
        return self._queue.empty()


class EngineState(Enum):
    """Состояния движка распознавания."""
    IDLE = auto()
    LOADING = auto()
    READY = auto()
    RECORDING = auto()
    PROCESSING = auto()
    SWITCHING = auto()
    ERROR = auto()


@dataclass
class RecognitionResult:
    """Результат распознавания речи."""
    text: str
    is_final: bool
    confidence: float = 0.0
    engine: str = ""
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class TranslationResult:
    """Результат перевода."""
    original: str
    translated: str
    cached: bool = False
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class EngineManager:
    """
    Менеджер состояния движка с thread-safe переключением.
    Предотвращает race conditions при смене движка.
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._state = EngineState.IDLE
        self._switching = threading.Event()
        self._state_callbacks: list[Callable[[EngineState], None]] = []
    
    @property
    def state(self) -> EngineState:
        """Текущее состояние движка."""
        with self._lock:
            return self._state
    
    @state.setter
    def state(self, new_state: EngineState) -> None:
        """Устанавливает новое состояние и уведомляет callbacks."""
        with self._lock:
            old_state = self._state
            self._state = new_state
            logger.debug(f"Engine state: {old_state.name} -> {new_state.name}")
            # Копируем callbacks под lock чтобы избежать race condition
            callbacks = self._state_callbacks.copy()
        
        # Вызываем callbacks вне lock чтобы не блокировать другие потоки
        for callback in callbacks:
            try:
                callback(new_state)
            except Exception as e:
                logger.error(f"State callback error: {e}")
    
    def add_state_callback(self, callback: Callable[[EngineState], None]) -> None:
        """Добавляет callback для отслеживания изменений состояния."""
        self._state_callbacks.append(callback)
    
    @property
    def is_switching(self) -> bool:
        """Проверяет, идёт ли переключение движка."""
        return self._switching.is_set()
    
    @contextmanager
    def switch_engine(self):
        """
        Context manager для безопасного переключения движка.
        Предотвращает одновременное переключение из нескольких потоков.
        """
        if self._switching.is_set():
            raise RuntimeError("Переключение движка уже выполняется")
        
        self._switching.set()
        old_state = self.state
        self.state = EngineState.SWITCHING
        
        try:
            with self._lock:
                yield
        finally:
            self._switching.clear()
            # Восстанавливаем состояние если переключение не завершилось нормально
            if self.state == EngineState.SWITCHING:
                self.state = old_state
    
    def wait_for_switch(self, timeout: float = 10.0) -> bool:
        """Ожидает завершения переключения движка."""
        start = time.time()
        while self._switching.is_set():
            if time.time() - start > timeout:
                return False
            time.sleep(0.1)
        return True


class StoppableThread(threading.Thread):
    """Поток с возможностью корректной остановки."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.daemon = True
    
    def stop(self) -> None:
        """Запрашивает остановку потока."""
        self._stop_event.set()
    
    def stopped(self) -> bool:
        """Проверяет, запрошена ли остановка."""
        return self._stop_event.is_set()
    
    def wait_stop(self, timeout: Optional[float] = None) -> bool:
        """Ожидает события остановки."""
        return self._stop_event.wait(timeout)


class AtomicCounter:
    """Thread-safe счётчик."""
    
    def __init__(self, initial: int = 0):
        self._value = initial
        self._lock = threading.Lock()
    
    def increment(self, delta: int = 1) -> int:
        """Увеличивает счётчик и возвращает новое значение."""
        with self._lock:
            self._value += delta
            return self._value
    
    def decrement(self, delta: int = 1) -> int:
        """Уменьшает счётчик и возвращает новое значение."""
        return self.increment(-delta)
    
    @property
    def value(self) -> int:
        """Текущее значение счётчика."""
        with self._lock:
            return self._value
    
    def reset(self, value: int = 0) -> None:
        """Сбрасывает счётчик."""
        with self._lock:
            self._value = value
