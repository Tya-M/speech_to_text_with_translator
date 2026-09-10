#!/usr/bin/env python3
"""
Самостоятельный запуск глобальной диктовки (речь → текст в месте курсора).

Источники настроек (в порядке приоритета):
    1. Аргументы командной строки: --key / --mode
    2. Переменные окружения: DICTATION_KEY / DICTATION_MODE
    3. Значения по умолчанию: F9 / hold

Примеры:
    python3 dictation_main.py
    python3 dictation_main.py --key f8
    python3 dictation_main.py --key cmd_r
    python3 dictation_main.py --mode toggle

Правый Command в pynput обозначается как ``cmd_r``.

Перед первым запуском выдайте разрешения: Accessibility, Input Monitoring,
Microphone (Системные настройки → Конфиденциальность и безопасность).
"""

import argparse
import logging
import os

from input_injection import DictationService


DEFAULT_KEY = "f9"
DEFAULT_MODE = "hold"
DEFAULT_ENGINE = "gigaam"
VALID_MODES = ("hold", "toggle")
VALID_ENGINES = ("gigaam", "parakeet")


def _env_key() -> str:
    """Возвращает клавишу диктовки из окружения или безопасный default."""
    value = os.environ.get("DICTATION_KEY", DEFAULT_KEY).strip().lower()
    return value or DEFAULT_KEY


def _env_mode() -> str:
    """Возвращает режим диктовки из окружения или безопасный default."""
    value = os.environ.get("DICTATION_MODE", DEFAULT_MODE).strip().lower()
    if value not in VALID_MODES:
        return DEFAULT_MODE
    return value


def _env_engine() -> str:
    """Возвращает движок диктовки из окружения или безопасный default."""
    value = os.environ.get("DICTATION_ENGINE", DEFAULT_ENGINE).strip().lower()
    return value if value in VALID_ENGINES else DEFAULT_ENGINE


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Офлайн-диктовка в место курсора (GigaAM или Parakeet)"
    )
    parser.add_argument(
        "--key",
        default=_env_key(),
        help=(
            "Горячая клавиша. Примеры: f7, f8, f9, f10, f11, f12, "
            "alt_r, cmd_r. По умолчанию: DICTATION_KEY или f9."
        ),
    )
    parser.add_argument(
        "--mode",
        default=_env_mode(),
        choices=VALID_MODES,
        help=(
            "Режим триггера: hold — удержание, toggle — нажать/нажать. "
            "По умолчанию: DICTATION_MODE или hold."
        ),
    )
    parser.add_argument(
        "--engine",
        default=_env_engine(),
        choices=VALID_ENGINES,
        help=(
            "Движок диктовки: gigaam — русский, parakeet — английский. "
            "По умолчанию: DICTATION_ENGINE или gigaam."
        ),
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    try:
        service = DictationService(
            trigger_key=args.key,
            mode=args.mode,
            engine=args.engine,
            on_status=print,
        )
    except ValueError as exc:
        parser.error(str(exc))

    logging.getLogger(__name__).info(
        "Запуск диктовки: key=%s, mode=%s",
        args.key,
        args.mode,
        extra={"engine": args.engine},
    )
    service.run_forever()


if __name__ == "__main__":
    main()
