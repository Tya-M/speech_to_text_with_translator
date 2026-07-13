"""
Модуль конфигурации приложения.
Использует dataclasses для типизации и валидации настроек.
"""

from dataclasses import dataclass, asdict, field
from typing import Literal, Optional
from pathlib import Path
import json
import logging

logger = logging.getLogger("voice_translator.config")

# Определяем путь к конфигу относительно корня проекта
CONFIG_DIR = Path(__file__).parent.parent
DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.json"


@dataclass
class AppConfig:
    """Конфигурация приложения с валидацией."""

    # Движок распознавания
    engine: Literal["vosk", "whisper"] = "whisper"
    whisper_model: Literal["tiny", "base", "small", "medium", "large-v2", "large-v3"] = "small"
    whisper_backend: Literal["openai", "faster", "whisper_cpp"] = "whisper_cpp"

    # Параметры Vosk
    vosk_model_size: Literal["small", "large"] = "small"  # small=0.42, large=0.22
    vosk_phrase_timeout: float = 1.5  # Секунды тишины до финализации фразы

    # Параметры аудио
    sensitivity: int = 1000  # 100-2000
    vad_threshold: int = 500  # 200-1000
    device_index: int = 0
    device_name: str = ""  # Имя устройства для поиска при загрузке
    sample_rate: int = 16000
    chunk_duration: float = 3.0  # секунд для Whisper

    # UI настройки
    font_size: int = 14
    window_width: int = 900
    window_height: int = 450

    # Пути к моделям
    vosk_model_path: str = "models/vosk-model-ru"
    vosk_large_model_path: str = "models/vosk-model-ru-0.22"
    whisper_cache_dir: str = "models/whisper"
    faster_whisper_cache_dir: str = "models/faster-whisper"
    whisper_compute_type: str = "int8"
    whisper_device: Literal["auto", "cpu", "gpu"] = "auto"
    whisper_cpp_model_dir: str = "models/whisper-cpp"
    whisper_cpp_use_gpu: bool = True
    whisper_language: str = "ru"

    # Кэш переводов
    translation_cache_size: int = 100

    # Троттлинг partial-обновлений (мс)
    partial_throttle_ms: int = 100
    
    def __post_init__(self):
        """Валидация значений после инициализации."""
        self.sensitivity = max(100, min(2000, self.sensitivity))
        self.vad_threshold = max(200, min(1000, self.vad_threshold))
        self.font_size = max(10, min(24, self.font_size))
        self.chunk_duration = max(1.0, min(10.0, self.chunk_duration))
        allowed_backends = {"openai", "faster", "whisper_cpp"}
        self.whisper_backend = str(self.whisper_backend).strip().lower()
        if self.whisper_backend not in allowed_backends:
            logger.warning("Неизвестный Whisper backend '%s', используем whisper_cpp", self.whisper_backend)
            self.whisper_backend = "whisper_cpp"

        allowed_devices = {"auto", "cpu", "gpu"}
        self.whisper_device = str(self.whisper_device).strip().lower()
        if self.whisper_device not in allowed_devices:
            logger.warning("Неизвестное Whisper device '%s', используем auto", self.whisper_device)
            self.whisper_device = "auto"

        self.whisper_compute_type = str(self.whisper_compute_type or "int8").strip() or "int8"
        self.whisper_cpp_model_dir = str(self.whisper_cpp_model_dir or "models/whisper-cpp").strip()
        self.whisper_language = str(self.whisper_language or "ru").strip().lower() or "ru"
        # Валидация троттлинга partial (50–300 мс)
        try:
            self.partial_throttle_ms = int(self.partial_throttle_ms)
        except Exception:
            self.partial_throttle_ms = 100
        self.partial_throttle_ms = max(50, min(300, self.partial_throttle_ms))
    
    @classmethod
    def load(cls, path: Optional[str] = None) -> "AppConfig":
        """
        Загружает конфигурацию из JSON файла.
        При ошибке возвращает настройки по умолчанию.
        """
        config_path = Path(path) if path else DEFAULT_CONFIG_PATH
        
        if not config_path.exists():
            logger.info(f"Файл конфигурации {config_path} не найден, используем настройки по умолчанию")
            return cls()
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Фильтруем только известные поля
            valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
            config = cls(**valid_fields)
            logger.info(f"Конфигурация загружена из {path}")
            return config
            
        except json.JSONDecodeError as e:
            logger.warning(f"Ошибка парсинга JSON в {path}: {e}")
            return cls()
        except TypeError as e:
            logger.warning(f"Неверный формат данных в {path}: {e}")
            return cls()
    
    def save(self, path: Optional[str] = None) -> bool:
        """
        Сохраняет конфигурацию в JSON файл атомарно.
        Возвращает True при успехе.
        """
        config_path = Path(path) if path else DEFAULT_CONFIG_PATH
        temp_path = config_path.with_suffix(".tmp")
        try:
            # Атомарная запись: пишем во временный файл, затем rename
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2, ensure_ascii=False)
            temp_path.replace(config_path)
            logger.info(f"Конфигурация сохранена в {config_path}")
            return True
        except IOError as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
            # Удаляем временный файл при ошибке
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass
            return False
    
    def copy_with(self, **kwargs) -> "AppConfig":
        """Создаёт копию конфигурации с изменёнными параметрами."""
        data = asdict(self)
        data.update(kwargs)
        return AppConfig(**data)


@dataclass  
class RecognitionConfig:
    """Конфигурация для движка распознавания."""
    vad_threshold: int = 500
    chunk_duration: float = 3.0
    sample_rate: int = 16000
    channels: int = 1
    buffer_size: int = 4096
    
    @classmethod
    def from_app_config(cls, app_config: AppConfig) -> "RecognitionConfig":
        """Создаёт RecognitionConfig из AppConfig."""
        return cls(
            vad_threshold=app_config.vad_threshold,
            chunk_duration=app_config.chunk_duration,
            sample_rate=app_config.sample_rate,
        )
