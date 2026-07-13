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

## Optional Whisper + Metal setup

The base app works with Vosk only. Install Whisper extras only when you need the GUI Whisper backends:

```bash
source venv/bin/activate
pip install faster-whisper openai-whisper
pip install --no-binary :all: pywhispercpp
```

macOS prerequisites for whisper.cpp/Metal builds:

```bash
xcode-select --install
brew install cmake ninja ffmpeg
```

On this Intel macOS + AMD RX 580 target:

- `faster-whisper` and `openai-whisper` are CPU-only.
- The only GPU path is `pywhispercpp`/whisper.cpp with Metal.
- Do not accept GPU status unless runtime logs show `ggml_metal_init` selecting `AMD Radeon RX 580`.

Optional whisper.cpp CLI fallback build:

```bash
git clone https://github.com/ggml-org/whisper.cpp
cmake -B whisper.cpp/build -DGGML_METAL=1 whisper.cpp
cmake --build whisper.cpp/build -j --config Release
```

Models:

- Vosk stays in `models/vosk-model-ru` or `models/vosk-model-ru-0.22`.
- pywhispercpp uses `models/whisper-cpp` from `whisper_cpp_model_dir`; it can auto-download by model name when network is available.
- Offline placement: put a matching `ggml-small*.bin` or `ggml-medium*.bin` file in `models/whisper-cpp`.
- openai-whisper and faster-whisper use their configured cache dirs under `models/`.

Verification after installing/building on the AMD RX 580 machine:

```bash
python -c "import pywhispercpp; print('pywhispercpp import ok')"
python -m py_compile recognition/whispercpp_engine.py recognition/__init__.py app/gui.py
python main.py
```

In the app, choose `Whisper` → `whisper.cpp (GPU)` → `small`, then verify logs contain `ggml_metal_init` picking the RX 580, Activity Monitor shows GPU activity, and the Russian sample transcribes.

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
