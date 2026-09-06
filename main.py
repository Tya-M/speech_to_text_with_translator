#!/usr/bin/env python3
"""
Russian Voice Translator - macOS Application
Офлайн распознавание русской речи с переводом на английский.

КРИТИЧЕСКИ ВАЖНО: Эти переменные окружения ДОЛЖНЫ быть установлены
ДО импорта torch/gigaam.

Про потоки и краши на macOS (важно):
- Многопоточный OpenMP (libomp) на этом Intel-Mac вызывает сегфолт
  (SIGSEGV в __kmp_fork_barrier). Поэтому OMP_NUM_THREADS ОБЯЗАТЕЛЬНО = 1.
  НЕ увеличивайте это значение — иначе приложение падает при запуске.
- Ускорение безопасно даёт OpenBLAS: у него свой пул потоков (не libomp),
  и матричные операции можно распараллелить через OPENBLAS_NUM_THREADS.

По умолчанию всё = 1 поток (гарантированно без краша, как раньше).
Чтобы попробовать ускорение, задайте число потоков OpenBLAS через переменную
окружения, например: VT_BLAS_THREADS=4 python main.py
"""

import os

# Обязательно для macOS: разрешает дублирующийся рантайм OpenMP.
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# OpenMP — строго 1 поток (иначе SIGSEGV в libomp на этой машине).
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

# OpenBLAS — безопасное ускорение матричных операций.
# По умолчанию 1 (стабильно); поднимите через VT_BLAS_THREADS.
_blas = os.environ.get('VT_BLAS_THREADS', '1')
os.environ['OPENBLAS_NUM_THREADS'] = _blas
os.environ['VECLIB_MAXIMUM_THREADS'] = _blas
os.environ['NUMEXPR_NUM_THREADS'] = _blas

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
    logger.info("OpenMP=1 (защита от краша), OpenBLAS threads=%s", _blas)

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
