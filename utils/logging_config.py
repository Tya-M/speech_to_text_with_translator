"""
Настройка логирования с ротацией файлов и форматированием.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys


def setup_logging(
    log_file: str = "voice_translator.log",
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    max_bytes: int = 5 * 1024 * 1024,  # 5MB
    backup_count: int = 3
) -> logging.Logger:
    """
    Настраивает логирование для приложения.
    
    Args:
        log_file: Путь к файлу логов
        console_level: Уровень логирования для консоли
        file_level: Уровень логирования для файла
        max_bytes: Максимальный размер файла логов
        backup_count: Количество резервных копий
    
    Returns:
        Настроенный logger
    """
    # Корневой logger для приложения
    logger = logging.getLogger("voice_translator")
    logger.setLevel(logging.DEBUG)
    
    # Удаляем существующие handlers (для переинициализации)
    logger.handlers.clear()
    
    # Формат для консоли (краткий)
    console_formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )
    
    # Формат для файла (подробный)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler с ротацией
    try:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
    except (IOError, PermissionError) as e:
        logger.warning(f"Не удалось создать файл логов: {e}")
    
    # Снижаем уровень логирования для сторонних библиотек
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("numba").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)
    
    return logger


class LoggerMixin:
    """Миксин для добавления логирования к классам."""
    
    @property
    def logger(self) -> logging.Logger:
        """Возвращает logger с именем модуля класса."""
        if not hasattr(self, "_logger"):
            self._logger = logging.getLogger(
                f"voice_translator.{self.__class__.__module__}.{self.__class__.__name__}"
            )
        return self._logger
