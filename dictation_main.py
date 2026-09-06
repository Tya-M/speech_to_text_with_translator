#!/usr/bin/env python3
"""
Самостоятельный запуск глобальной диктовки (речь → текст в месте курсора).

Запуск:
    python3 dictation_main.py                 # клавиша F9, push-to-talk
    python3 dictation_main.py --key f8         # другая клавиша
    python3 dictation_main.py --mode toggle    # нажать/нажать вместо удержания

Перед первым запуском выдайте разрешения: Accessibility, Input Monitoring, Microphone
(Системные настройки → Конфиденциальность и безопасность).
"""

import argparse
import logging

from input_injection import DictationService


def main() -> None:
    parser = argparse.ArgumentParser(description="Офлайн-диктовка в место курсора (GigaAM)")
    parser.add_argument("--key", default="f9", help="Горячая клавиша (например f9, f8)")
    parser.add_argument("--mode", default="hold", choices=["hold", "toggle"], help="Режим триггера")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    service = DictationService(trigger_key=args.key, mode=args.mode, on_status=print)
    service.run_forever()


if __name__ == "__main__":
    main()
