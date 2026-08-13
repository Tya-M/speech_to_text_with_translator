# 🎤 Голосовой Переводчик (Russian Voice Translator)

Офлайн macOS-приложение для распознавания русской речи с переводом на английский.

## Возможности

- **Два движка распознавания:** Vosk (быстро) и GigaAM (точно, SberDevices)
- **Офлайн перевод** с Argos Translate (RU → EN)
- **Тёмная тема** с современным интерфейсом
- **Real-time визуализация** уровня громкости
- **Экспорт** в TXT, JSON, SRT (субтитры)

## Требования

- macOS 10.15+, Python 3.10+, ~2GB RAM

## Быстрый старт

```bash
# 1. Установка зависимостей
brew install portaudio
pip install -r requirements.txt

# 2. Скачивание модели Vosk
mkdir -p models && cd models
wget https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip
unzip vosk-model-ru-0.42.zip && mv vosk-model-ru-0.42 vosk-model-ru
cd ..

# 3. Запуск
python main.py
```

## Настройка GigaAM (SberDevices)

Базовое приложение работает и только на Vosk. GigaAM — более точный офлайн-движок для русской речи. Установите его, когда нужна максимальная точность:

```bash
source venv/bin/activate
# ffmpeg обязателен для чтения аудио GigaAM
brew install ffmpeg
# GigaAM v3 (модели v3_e2e_ctc / v3_e2e_rnnt) устанавливается из исходников GitHub
pip install "gigaam @ git+https://github.com/salute-developers/GigaAM.git"
```

Зависимости PyTorch и torchaudio устанавливаются автоматически вместе с `gigaam`.

Модели:

- **v3 RNNT** (`v3_e2e_rnnt`) — точнее, выбрана по умолчанию.
- **v3 CTC** (`v3_e2e_ctc`) — быстрее.
- Обе модели end-to-end: возвращают текст с пунктуацией и нормализацией.
- Веса скачиваются с Hugging Face при первом запуске, далее работают офлайн.

Устройство (`gigaam_device`) по умолчанию `cpu`; при наличии CUDA-GPU можно указать `cuda` в `config.json`.

Проверка после установки:

```bash
python -c "import gigaam; print('gigaam import ok')"
python -m py_compile recognition/gigaam_engine.py recognition/__init__.py app/gui.py
python main.py
```

В приложении выберите `GigaAM` → `Модель GigaAM` (`v3 RNNT` или `v3 CTC`). Если пакет `gigaam` не установлен, приложение автоматически откатывается на Vosk.

## Горячие клавиши

| Клавиша | Действие |
|---------|----------|
| `Cmd+R` | Начать/остановить запись |
| `Cmd+S` | Экспорт в TXT |
| `Esc`   | Остановить запись |

## Troubleshooting

**OpenMP crash на macOS** — переменные окружения уже установлены в main.py

**Vosk не найден** — проверьте путь `models/vosk-model-ru/`

**GigaAM не установлен / ошибка импорта** — установите пакет (`pip install "gigaam @ git+https://github.com/salute-developers/GigaAM.git"`) и `ffmpeg`; до этого приложение работает на Vosk

**Медленный GigaAM** — используйте Vosk для real-time, модель `v3 CTC` или уменьшите chunk_duration
