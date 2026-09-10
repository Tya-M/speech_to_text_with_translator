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
    engine: Literal["vosk", "gigaam"] = "gigaam"

    # Параметры GigaAM (SberDevices)
    gigaam_model: Literal["v3_e2e_ctc", "v3_e2e_rnnt"] = "v3_e2e_rnnt"
    gigaam_device: Literal["auto", "cpu", "cuda"] = "cpu"
    gigaam_language: str = "ru"

    # Параметры Vosk
    vosk_model_size: Literal["small", "large"] = "small"  # small=0.42, large=0.22
    vosk_phrase_timeout: float = 1.5  # Секунды тишины до финализации фразы

    # Параметры аудио
    sensitivity: int = 1000  # 100-2000
    vad_threshold: int = 500  # 200-1000
    device_index: int = 0
    device_name: str = ""  # Имя устройства для поиска при загрузке
    sample_rate: int = 16000
    chunk_duration: float = 3.0  # секунд на окно распознавания (GigaAM работает с записями до ~25 с)

    # UI настройки
    font_size: int = 14
    window_width: int = 900
    window_height: int = 450

    # Пути к моделям
    vosk_model_path: str = "models/vosk-model-ru"
    vosk_large_model_path: str = "models/vosk-model-ru-0.22"

    # Кэш переводов
    translation_cache_size: int = 100

    # Троттлинг partial-обновлений (мс)
    partial_throttle_ms: int = 100

    # Глобальная диктовка «речь → текст под курсором»
    dictation_key: str = "f9"          # горячая клавиша (f7..f12, alt_r, cmd_r)
    dictation_mode: Literal["hold", "toggle"] = "hold"
    dictation_engine: Literal["gigaam", "parakeet"] = "gigaam"

    # Параметры английской диктовки Parakeet Unified EN
    parakeet_model_path: str = "sherpa-onnx-nemo-parakeet-unified-en-0.6b-int8-non-streaming"
    parakeet_num_threads: int = 2
    
    def __post_init__(self):
        """Валидация значений после инициализации."""
        self.sensitivity = max(100, min(2000, self.sensitivity))
        self.vad_threshold = max(200, min(1000, self.vad_threshold))
        self.font_size = max(10, min(24, self.font_size))
        self.chunk_duration = max(1.0, min(10.0, self.chunk_duration))

        allowed_engines = {"vosk", "gigaam"}
        self.engine = str(self.engine).strip().lower()
        if self.engine not in allowed_engines:
            logger.warning("Неизвестный движок '%s', используем gigaam", self.engine)
            self.engine = "gigaam"

        allowed_models = {"v3_e2e_ctc", "v3_e2e_rnnt"}
        self.gigaam_model = str(self.gigaam_model).strip().lower()
        if self.gigaam_model not in allowed_models:
            logger.warning("Неизвестная модель GigaAM '%s', используем v3_e2e_rnnt", self.gigaam_model)
            self.gigaam_model = "v3_e2e_rnnt"

        allowed_devices = {"auto", "cpu", "cuda"}
        self.gigaam_device = str(self.gigaam_device).strip().lower()
        if self.gigaam_device not in allowed_devices:
            logger.warning("Неизвестное GigaAM device '%s', используем cpu", self.gigaam_device)
            self.gigaam_device = "cpu"

        self.gigaam_language = str(self.gigaam_language or "ru").strip().lower() or "ru"

        # Валидация троттлинга partial (50–300 мс)
        try:
            self.partial_throttle_ms = int(self.partial_throttle_ms)
        except Exception:
            self.partial_throttle_ms = 100
        self.partial_throttle_ms = max(50, min(300, self.partial_throttle_ms))

        # Валидация настроек диктовки (речь → текст под курсором)
        self.dictation_key = str(self.dictation_key or "f9").strip().lower() or "f9"
        allowed_dictation_modes = {"hold", "toggle"}
        self.dictation_mode = str(self.dictation_mode).strip().lower()
        if self.dictation_mode not in allowed_dictation_modes:
            self.dictation_mode = "hold"

        self.dictation_engine = str(self.dictation_engine or "gigaam").strip().lower()
        if self.dictation_engine not in {"gigaam", "parakeet"}:
            self.dictation_engine = "gigaam"

        self.parakeet_model_path = str(
            self.parakeet_model_path
            or "sherpa-onnx-nemo-parakeet-unified-en-0.6b-int8-non-streaming"
        ).strip()
        try:
            self.parakeet_num_threads = int(self.parakeet_num_threads)
        except Exception:
            self.parakeet_num_threads = 2
        self.parakeet_num_threads = max(1, min(8, self.parakeet_num_threads))
    
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
