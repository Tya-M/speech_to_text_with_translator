# 🎤 Голосовой Переводчик (Russian Voice Translator)

Офлайн macOS-приложение для распознавания русской речи с переводом на английский.

## Возможности

- **Два движка распознавания:** Vosk (быстро) и Whisper (точно)
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

## Горячие клавиши

| Клавиша | Действие |
|---------|----------|
| `Cmd+R` | Начать/остановить запись |
| `Cmd+S` | Экспорт в TXT |
| `Esc`   | Остановить запись |

## Troubleshooting

**OpenMP crash на macOS** — переменные окружения уже установлены в main.py

**Vosk не найден** — проверьте путь `models/vosk-model-ru/`

**Медленный Whisper** — используйте Vosk для real-time или уменьшите chunk_duration
