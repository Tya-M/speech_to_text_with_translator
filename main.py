#!/usr/bin/env python3
"""
Russian Voice Translator - macOS Application
Офлайн распознавание русской речи с переводом на английский.

КРИТИЧЕСКИ ВАЖНО: Эти переменные окружения ДОЛЖНЫ быть установлены
ДО импорта torch/gigaam для предотвращения OpenMP crash на macOS.
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import sys
import logging
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.logging_config import setup_logging
from utils.config import AppConfig
from app.gui import VoiceTranslatorApp


def main():
    """Точка входа приложения."""
    logger = setup_logging()
    logger.info("=" * 50)
    logger.info("Запуск Russian Voice Translator")
    logger.info("=" * 50)
    
    try:
        # Загружаем конфигурацию
        config = AppConfig.load()
        model_name = config.gigaam_model if config.engine == "gigaam" else config.vosk_model_size
        logger.info(f"Конфигурация загружена: engine={config.engine}, model={model_name}")
        
        # Создаём и запускаем приложение
        app = VoiceTranslatorApp(config)
        app.run()
        
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем (Ctrl+C)")
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        sys.exit(1)
    finally:
        logger.info("Приложение завершено")


if __name__ == "__main__":
    main()
