# Project Codebase Dump

## File: `AGENTS.md`

```markdown
Never create long read README, SUMMARY and the files like that. Just provide not more than 2-3 of the task that's been done. 
 Never make any changes in the files that are not related to the task. 
 Never make any changes in the files until I approve it.

Before writing any code, describe your approach and wait for approval. Always ask clarifying questions before writing any code if requirements are ambiguous.

When you    offer several approaches for edittig, fixing, improving or refactoring the code, please highlight from all options recommended one which is the best and most modern, and corresponds to the best web development practices

If a task requires changes to more than 3 files, stop and break it into smaller tasks first.

 After writing code, list what could break and suggest tests to cover it.

When there’s a bug, start by writing a test that reproduces it, then fix it until the test passes

 Every time I correct you, add a new rule to the AGENTS.md file so it never happens again.

When the user says "app icon", treat it as the macOS .app icon unless they explicitly say the in-app button or control.
```

---

## File: `README.md`

```markdown
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
```

---

## File: `VERIFICATION.md`

```markdown
# T07 Verification

Date: 2026-07-13
Branch: `feat/T07-verification`
Sample: `models/vosk-model-ru/decoder-test.wav` (7.08s, 8 kHz mono PCM16; repeated to 16 kHz for app recognizers)

## Environment

- Python venv: 3.11.15
- Optional deps present: `faster-whisper 1.2.1`, `openai-whisper 20250625`, `pywhispercpp 1.5.0`, `vosk 0.3.44`
- `pywhispercpp` rebuilt from source after forcing `DEBUG=0` and CMake Python executable to the venv Python.
- Native `_pywhispercpp.cpython-311-darwin.so` imports successfully after adding site-packages rpath.
- `_pywhispercpp` links `libggml-metal.0.dylib`.

## Matrix Results

| Engine | Device | Load | Transcribe | xRT | Result |
|---|---:|---:|---:|---:|---|
| Vosk | CPU | 89.581s | 2.018s | 0.285 | PASS |
| faster-whisper `small` int8 | CPU | 15.247s | 11.338s | 1.601 | PASS |
| openai-whisper `small` | CPU | 13.912s | 15.655s | 2.211 | PASS |
| whisper.cpp `small` | Metal (AMD Radeon RX 580) | 36.169s | 14.857s | 2.098 | PASS headless; Activity Monitor confirmation pending |

Transcript quality:

- Vosk: `родион потапыч высчитывал каждый новый вершок углубления и давно определил про себя`
- faster-whisper: `Родион Потапыч высчитывал каждый новый вершок углубления и давно определил про себя`
- openai-whisper: `Родион Потапыч высчитывал каждый новый вершок углубления и давно определил про себя`
- whisper.cpp: `Родион Потапыч высчитывал каждый новый вершок углубления и давно определил про себя.`

## whisper.cpp / Metal Status

`pywhispercpp` is importable, linked against Metal, and transcribed the bundled sample after `ggml-small.bin` was placed in `models/whisper-cpp`.

- Model file: `models/whisper-cpp/ggml-small.bin` (~465 MiB on disk).
- Metal selected device: `AMD Radeon RX 580`.
- Headless command used OpenMP guards: `KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1`.

Full init/system log:

```text
whisper_init_from_file_with_params_no_state: loading model from '/Applications/russian_voice_translator/models/whisper-cpp/ggml-small.bin'
whisper_init_with_params_no_state: use gpu    = 1
whisper_init_with_params_no_state: flash attn = 1
whisper_init_with_params_no_state: gpu_device = 0
whisper_init_with_params_no_state: dtw        = 0
ggml_metal_device_init: tensor API disabled for pre-M5 and pre-A19 devices
ggml_metal_library_init: using embedded metal library
ggml_metal_library_init: loaded in 0.041 sec
ggml_metal_rsets_init: creating a residency set collection (keep_alive = 180 s)
ggml_metal_device_init: GPU name:   MTL0
ggml_metal_device_init: GPU family: MTLGPUFamilyCommon3 (3003)
ggml_metal_device_init: simdgroup reduction   = false
ggml_metal_device_init: simdgroup matrix mul. = false
ggml_metal_device_init: has unified memory    = false
ggml_metal_device_init: has bfloat            = false
ggml_metal_device_init: has tensor            = false
ggml_metal_device_init: use residency sets    = true
ggml_metal_device_init: use shared buffers    = false
ggml_metal_device_init: recommendedMaxWorkingSetSize  =  8589.93 MB
whisper_init_with_params_no_state: devices    = 3
whisper_init_with_params_no_state: backends   = 3
whisper_model_load: loading model
whisper_model_load: n_vocab       = 51865
whisper_model_load: n_audio_ctx   = 1500
whisper_model_load: n_audio_state = 768
whisper_model_load: n_audio_head  = 12
whisper_model_load: n_audio_layer = 12
whisper_model_load: n_text_ctx    = 448
whisper_model_load: n_text_state  = 768
whisper_model_load: n_text_head   = 12
whisper_model_load: n_text_layer  = 12
whisper_model_load: n_mels        = 80
whisper_model_load: ftype         = 1
whisper_model_load: qntvr         = 0
whisper_model_load: type          = 3 (small)
whisper_model_load: adding 1608 extra tokens
whisper_model_load: n_langs       = 99
whisper_model_load: MTL0_Private total size =   487.01 MB
whisper_model_load: model size    =  487.01 MB
whisper_backend_init_gpu: device 0: MTL0 (type: 1)
whisper_backend_init_gpu: found GPU device 0: MTL0 (type: 1, cnt: 0)
whisper_backend_init_gpu: using MTL0 backend
ggml_metal_init: allocating
ggml_metal_init: found device: AMD Radeon RX 580
ggml_metal_init: found device: Intel(R) KBL Unknown
ggml_metal_init: picking default device: AMD Radeon RX 580
ggml_metal_init: use fusion         = true
ggml_metal_init: use concurrency    = true
ggml_metal_init: use graph optimize = true
whisper_backend_init: using BLAS backend
whisper_init_state: kv self size  =   18.87 MB
whisper_init_state: kv cross size =   56.62 MB
whisper_init_state: kv pad  size  =    4.72 MB
whisper_init_state: compute buffer (conv)   =   32.78 MB
whisper_init_state: compute buffer (encode) =   57.00 MB
whisper_init_state: compute buffer (cross)  =   16.59 MB
whisper_init_state: compute buffer (decode) =  183.83 MB
```

## Fallback / Compatibility

- Real factory fallback passed: requesting `whisper_cpp` failed on model download, then loaded `FasterWhisperRecognizer`.
- Current `config.json` loads.
- Old minimal config loads and fills new defaults.
- Config persistence round-trip passed.
- GUI import with Whisper deps hidden passed; optional flags became `False`.

## Manual Confirmation Still Required

- AMD RX 580 GPU activity in Activity Monitor during whisper.cpp recognition.
- Live transcription quality in the app window.
```

---

## File: `config.json`

```json
{
  "engine": "vosk",
  "whisper_model": "small",
  "whisper_backend": "whisper_cpp",
  "vosk_model_size": "large",
  "vosk_phrase_timeout": 1.5,
  "sensitivity": 1150,
  "vad_threshold": 700,
  "device_index": 6,
  "device_name": "Unknown USB Audio Device",
  "sample_rate": 16000,
  "chunk_duration": 3.0,
  "font_size": 14,
  "window_width": 900,
  "window_height": 450,
  "vosk_model_path": "models/vosk-model-ru",
  "vosk_large_model_path": "models/vosk-model-ru-0.22",
  "whisper_cache_dir": "models/whisper",
  "faster_whisper_cache_dir": "models/faster-whisper",
  "whisper_compute_type": "int8",
  "whisper_device": "auto",
  "whisper_cpp_model_dir": "models/whisper-cpp",
  "whisper_cpp_use_gpu": true,
  "whisper_language": "ru",
  "translation_cache_size": 100,
  "partial_throttle_ms": 100
}
```

---

## File: `create_icon.py`

```python
#!/usr/bin/env python3
"""
Creates a rounded app icon for Voice Translator.
Uses pillow if available, otherwise creates a placeholder.
"""

import subprocess
import struct
from pathlib import Path


def _render_icon(size: int):
    """Renders one icon image at the requested square size."""
    from PIL import Image, ImageDraw, ImageFilter

    scale = 4
    canvas = size * scale
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = int(canvas * 0.06)
    radius = int(canvas * 0.30)  # более скруглённые, "squircle"-углы
    box = [margin, margin, canvas - margin, canvas - margin]

    # Мягкая тень под иконкой.
    shadow = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [box[0], box[1] + int(canvas * 0.035), box[2], box[3] + int(canvas * 0.035)],
        radius=radius,
        fill=(0, 0, 0, 120),
    )
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(max(2, canvas // 48))))

    # Один плоский тёмный фон — без доп. рамок и колец.
    draw.rounded_rectangle(box, radius=radius, fill=(24, 26, 32, 255))

    # Чистый красный круг по центру.
    center = canvas // 2
    r = int(canvas * 0.30)
    draw.ellipse([center - r, center - r, center + r, center + r], fill=(229, 50, 58, 255))

    # Мягкий глянцевый хайлайт в левом верхнем углу круга.
    highlight = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    hl_r = int(r * 0.8)
    hl_cx, hl_cy = center - int(r * 0.32), center - int(r * 0.38)
    ImageDraw.Draw(highlight).ellipse(
        [hl_cx - hl_r, hl_cy - hl_r, hl_cx + hl_r, hl_cy + hl_r],
        fill=(255, 255, 255, 140),
    )
    highlight = highlight.filter(ImageFilter.GaussianBlur(max(2, canvas // 16)))

    circle_mask = Image.new("L", (canvas, canvas), 0)
    ImageDraw.Draw(circle_mask).ellipse([center - r, center - r, center + r, center + r], fill=255)
    masked_highlight = Image.composite(highlight, Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0)), circle_mask)
    img.alpha_composite(masked_highlight)

    return img.resize((size, size), Image.Resampling.LANCZOS)


def _write_icns(iconset_path: Path, icns_path: Path) -> None:
    """Writes an ICNS file by packaging PNG chunks directly."""
    entries = [
        ("icp4", "icon_16x16.png"),
        ("ic11", "icon_16x16@2x.png"),
        ("icp5", "icon_32x32.png"),
        ("ic12", "icon_32x32@2x.png"),
        ("ic07", "icon_128x128.png"),
        ("ic13", "icon_128x128@2x.png"),
        ("ic08", "icon_256x256.png"),
        ("ic14", "icon_256x256@2x.png"),
        ("ic09", "icon_512x512.png"),
        ("ic10", "icon_512x512@2x.png"),
    ]

    chunks = []
    for icon_type, filename in entries:
        data = (iconset_path / filename).read_bytes()
        chunks.append(icon_type.encode("ascii") + struct.pack(">I", len(data) + 8) + data)

    payload = b"".join(chunks)
    icns_path.write_bytes(b"icns" + struct.pack(">I", len(payload) + 8) + payload)


def create_icon():
    """Creates an app icon."""
    resources_dir = Path(__file__).parent / "Voice Translator.app" / "Contents" / "Resources"
    resources_dir.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image, ImageDraw, ImageFont

        iconset_path = resources_dir / "AppIcon.iconset"
        iconset_path.mkdir(exist_ok=True)

        icon_sizes = [
            (16, 1), (16, 2),
            (32, 1), (32, 2),
            (128, 1), (128, 2),
            (256, 1), (256, 2),
            (512, 1), (512, 2),
        ]

        for logical_size, scale in icon_sizes:
            pixel_size = logical_size * scale
            suffix = "@2x" if scale == 2 else ""
            _render_icon(pixel_size).save(
                iconset_path / f"icon_{logical_size}x{logical_size}{suffix}.png",
                "PNG",
            )

        # Convert iconset to icns using iconutil
        icns_path = resources_dir / "AppIcon.icns"
        result = subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_path), "-o", str(icns_path)],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            print(f"Icon created successfully: {icns_path}")
            # Clean up iconset
            import shutil
            shutil.rmtree(iconset_path)
        else:
            print(f"iconutil failed: {result.stderr}")
            _write_icns(iconset_path, icns_path)
            print(f"Icon created with Python fallback: {icns_path}")
            import shutil
            shutil.rmtree(iconset_path)

    except ImportError:
        print("Pillow not installed. Creating placeholder icon instructions.")
        print(f"Please add an icon file to: {resources_dir / 'AppIcon.icns'}")

if __name__ == "__main__":
    create_icon()
```

---

## File: `main.py`

```python
#!/usr/bin/env python3
"""
Russian Voice Translator - macOS Application
Офлайн распознавание русской речи с переводом на английский.

КРИТИЧЕСКИ ВАЖНО: Эти переменные окружения ДОЛЖНЫ быть установлены
ДО импорта torch/whisper для предотвращения OpenMP crash на macOS.
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
        logger.info(f"Конфигурация загружена: engine={config.engine}, model={config.whisper_model}")
        
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
```

---

## File: `requirements.txt`

```
# Russian Voice Translator - Dependencies
# Tested on macOS with Python 3.10+

# Core Audio
pyaudio>=0.2.14
numpy>=1.21.0,<2.0.0

# Speech Recognition - Vosk (fast, offline)
vosk>=0.3.44

# Optional Speech Recognition - Whisper
# Install these only when using Whisper backends. The app keeps running with Vosk only.
# faster-whisper is CPU-only on this Intel/AMD macOS target.
# faster-whisper>=1.0.0
# openai-whisper>=20231117
# pywhispercpp must be built from source for Metal; see README.
# pywhispercpp

# Translation - Argos (offline)
argostranslate>=1.9.0

# Utilities
psutil>=5.9.0

# GUI
customtkinter>=5.2.0

# Optional: for building .app bundle
# py2app>=0.28.0
# pyinstaller>=6.0.0

# Vosk Large Model (опционально, ~1.5GB):
# wget https://alphacephei.com/vosk/models/vosk-model-ru-0.22.zip
# unzip vosk-model-ru-0.22.zip -d models/
```

---

## File: `run.sh`

```bash
#!/bin/bash
# Russian Voice Translator - Launch Script

cd "$(dirname "$0")"
source venv/bin/activate
python main.py
```

---

## File: `voice_translator_preview.jsx`

```javascript
import React, { useState, useEffect, useRef } from 'react';

// Цветовая схема приложения
const COLORS = {
  bgPrimary: '#1a1a2e',
  bgSecondary: '#16213e',
  bgTertiary: '#0f3460',
  textPrimary: '#e8e8e8',
  textSecondary: '#a0a0a0',
  textMuted: '#606060',
  accentPrimary: '#00d4ff',
  accentSuccess: '#00ff88',
  accentWarning: '#ffaa00',
  accentError: '#ff4444',
  buttonBg: '#2d2d44',
  border: '#3d3d54',
};

// Компонент Toggle для выбора движка
const EngineToggle = ({ value, onChange }) => {
  const options = ['Vosk (Быстро)', 'Whisper (Точно)'];
  
  return (
    <div className="relative flex bg-opacity-50 rounded-full p-1" style={{ backgroundColor: COLORS.bgTertiary }}>
      <div
        className="absolute h-8 rounded-full transition-all duration-300"
        style={{
          width: '50%',
          backgroundColor: COLORS.accentPrimary,
          left: value === 0 ? '2px' : '50%',
          top: '2px',
          bottom: '2px',
        }}
      />
      {options.map((option, idx) => (
        <button
          key={idx}
          onClick={() => onChange(idx)}
          className="relative z-10 px-4 py-1.5 text-sm font-medium transition-colors"
          style={{
            color: value === idx ? COLORS.bgPrimary : COLORS.textSecondary,
            width: '50%',
          }}
        >
          {option}
        </button>
      ))}
    </div>
  );
};

// Компонент кнопки записи
const RecordButton = ({ isRecording, onClick }) => {
  const [pulse, setPulse] = useState(0);
  
  useEffect(() => {
    if (isRecording) {
      const interval = setInterval(() => {
        setPulse(p => (p + 0.1) % 1);
      }, 50);
      return () => clearInterval(interval);
    }
    setPulse(0);
  }, [isRecording]);

  return (
    <button
      onClick={onClick}
      className="relative w-20 h-20 rounded-full transition-transform hover:scale-105 active:scale-95"
      style={{
        backgroundColor: COLORS.bgTertiary,
        border: `3px solid ${isRecording ? COLORS.accentError : COLORS.border}`,
        boxShadow: isRecording ? `0 0 ${20 + pulse * 10}px ${COLORS.accentError}40` : 'none',
      }}
    >
      <div
        className="absolute inset-3 rounded-full transition-all duration-200"
        style={{
          backgroundColor: COLORS.accentError,
          borderRadius: isRecording ? '4px' : '50%',
          transform: isRecording ? 'scale(0.6)' : 'scale(1)',
        }}
      />
    </button>
  );
};

// Компонент индикатора уровня
const LevelMeter = ({ level }) => {
  const segments = 30;
  
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: segments }).map((_, i) => {
        const segmentPos = i / segments;
        const isActive = segmentPos < level;
        let color = COLORS.bgTertiary;
        
        if (isActive) {
          if (segmentPos < 0.6) color = COLORS.accentSuccess;
          else if (segmentPos < 0.85) color = COLORS.accentWarning;
          else color = COLORS.accentError;
        }
        
        return (
          <div
            key={i}
            className="h-3 rounded-sm transition-colors"
            style={{
              width: `${100 / segments}%`,
              backgroundColor: color,
            }}
          />
        );
      })}
    </div>
  );
};

// Компонент слайдера
const Slider = ({ label, value, onChange, min, max }) => (
  <div className="flex-1">
    <div className="text-xs mb-1" style={{ color: COLORS.textSecondary }}>{label}</div>
    <div className="flex items-center gap-3">
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="flex-1 h-2 rounded-full appearance-none cursor-pointer"
        style={{ backgroundColor: COLORS.bgTertiary }}
      />
      <span className="text-sm w-12 text-right" style={{ color: COLORS.accentPrimary }}>{value}</span>
    </div>
  </div>
);

// Запись транскрипта
const TranscriptEntry = ({ entry }) => (
  <div className="mb-4">
    <div className="flex items-start gap-2">
      <span className="text-xs" style={{ color: COLORS.textMuted }}>[{entry.time}]</span>
      <span style={{ color: COLORS.textPrimary }}>{entry.original}</span>
    </div>
    {entry.translated && (
      <div className="ml-12 mt-1" style={{ color: COLORS.accentPrimary }}>
        → {entry.translated}
      </div>
    )}
  </div>
);

// Главное приложение
export default function VoiceTranslatorPreview() {
  const [engine, setEngine] = useState(1);
  const [isRecording, setIsRecording] = useState(false);
  const [level, setLevel] = useState(0);
  const [sensitivity, setSensitivity] = useState(1000);
  const [vad, setVad] = useState(500);
  const [transcript, setTranscript] = useState([
    { time: '10:32:15', original: 'Привет, как дела сегодня?', translated: 'Hello, how are you today?' },
    { time: '10:32:22', original: 'Я хочу заказать кофе', translated: 'I want to order coffee' },
    { time: '10:32:30', original: 'Где находится ближайшая станция метро?', translated: 'Where is the nearest metro station?' },
  ]);
  const [partialText, setPartialText] = useState('');

  // Симуляция уровня звука и распознавания
  useEffect(() => {
    if (isRecording) {
      const levelInterval = setInterval(() => {
        setLevel(Math.random() * 0.7 + 0.1);
      }, 100);

      const textInterval = setInterval(() => {
        const phrases = [
          'Это тестовое сообщение...',
          'Распознавание речи работает...',
          'Говорю по-русски...',
        ];
        setPartialText(phrases[Math.floor(Math.random() * phrases.length)]);
      }, 2000);

      return () => {
        clearInterval(levelInterval);
        clearInterval(textInterval);
      };
    }
    setLevel(0);
    setPartialText('');
  }, [isRecording]);

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: COLORS.bgPrimary }}>
      <div className="max-w-4xl mx-auto">
        {/* Заголовок */}
        <h1 className="text-2xl font-bold mb-6" style={{ color: COLORS.textPrimary }}>
          🎤 Голосовой Переводчик
        </h1>

        {/* Панель управления */}
        <div className="rounded-xl p-4 mb-4" style={{ backgroundColor: COLORS.bgSecondary }}>
          {/* Верхняя строка */}
          <div className="flex justify-between items-start mb-4">
            <div>
              <div className="text-xs mb-2" style={{ color: COLORS.textSecondary }}>
                Движок распознавания:
              </div>
              <EngineToggle value={engine} onChange={setEngine} />
            </div>
            
            <div>
              <div className="text-xs mb-2" style={{ color: COLORS.textSecondary }}>
                Микрофон:
              </div>
              <select
                className="px-3 py-2 rounded-lg text-sm"
                style={{
                  backgroundColor: COLORS.bgTertiary,
                  color: COLORS.textPrimary,
                  border: `1px solid ${COLORS.border}`,
                }}
              >
                <option>MacBook Pro Microphone</option>
                <option>External USB Microphone</option>
              </select>
            </div>
          </div>

          {/* Слайдеры */}
          <div className="flex gap-8">
            <Slider
              label="Чувствительность микрофона:"
              value={sensitivity}
              onChange={setSensitivity}
              min={100}
              max={2000}
            />
            <Slider
              label="Порог голоса (VAD):"
              value={vad}
              onChange={setVad}
              min={200}
              max={1000}
            />
          </div>
        </div>

        {/* Центральная панель */}
        <div className="flex items-center gap-6 mb-4">
          <RecordButton
            isRecording={isRecording}
            onClick={() => setIsRecording(!isRecording)}
          />
          
          <div className="flex-1">
            <div className="text-sm mb-2" style={{ color: isRecording ? COLORS.accentError : COLORS.textSecondary }}>
              {isRecording ? '🔴 Запись...' : 'Нажмите кнопку для начала записи'}
            </div>
            <LevelMeter level={level} />
          </div>

          <div className="flex gap-2">
            {['TXT', 'JSON', 'SRT'].map(format => (
              <button
                key={format}
                className="px-3 py-1.5 rounded text-sm transition-colors hover:opacity-80"
                style={{
                  backgroundColor: COLORS.buttonBg,
                  color: COLORS.textPrimary,
                }}
              >
                {format}
              </button>
            ))}
          </div>
        </div>

        {/* Область транскрипции */}
        <div className="rounded-xl overflow-hidden" style={{ backgroundColor: COLORS.bgSecondary }}>
          <div className="flex justify-between items-center px-4 py-3" style={{ borderBottom: `1px solid ${COLORS.border}` }}>
            <span className="font-medium" style={{ color: COLORS.textPrimary }}>
              📝 Транскрипция и перевод
            </span>
            <button
              className="text-sm px-3 py-1 rounded transition-colors hover:opacity-80"
              style={{ backgroundColor: COLORS.buttonBg, color: COLORS.textSecondary }}
            >
              Очистить
            </button>
          </div>
          
          <div className="p-4 h-64 overflow-y-auto" style={{ backgroundColor: COLORS.bgTertiary }}>
            {transcript.map((entry, i) => (
              <TranscriptEntry key={i} entry={entry} />
            ))}
            
            {partialText && (
              <div className="italic" style={{ color: COLORS.textSecondary }}>
                ⏳ {partialText}
              </div>
            )}
          </div>
        </div>

        {/* Статус бар */}
        <div className="flex justify-between mt-4 text-xs" style={{ color: COLORS.textMuted }}>
          <div className="flex gap-4">
            <span style={{ color: COLORS.accentSuccess }}>
              ● Движок: {engine === 0 ? 'Vosk' : 'Whisper'}
            </span>
            <span>Модель: {engine === 0 ? 'Russian 0.42' : 'small'}</span>
          </div>
          <div className="flex gap-4">
            <span>Кэш: 67%</span>
            <span>CPU: 12%</span>
          </div>
        </div>

        {/* Инструкция */}
        <div className="mt-6 p-4 rounded-lg text-sm" style={{ backgroundColor: COLORS.bgSecondary, color: COLORS.textSecondary }}>
          <strong style={{ color: COLORS.textPrimary }}>Горячие клавиши:</strong>
          <span className="ml-4">Cmd+R — Запись</span>
          <span className="ml-4">Cmd+S — Экспорт</span>
          <span className="ml-4">Esc — Стоп</span>
        </div>
      </div>
    </div>
  );
}
```

---

## File: `app/__init__.py`

```python
"""App package - UI приложения."""
from .gui import VoiceTranslatorApp
from .styles import COLORS, FONTS, SPACING
from .components import (
    RecordButton,
    LevelMeter,
    StatusBar
)

__all__ = [
    'VoiceTranslatorApp',
    'COLORS',
    'FONTS',
    'SPACING',
    'RecordButton',
    'LevelMeter',
    'StatusBar',
]
```

---

## File: `app/components.py`

```python
"""
Кастомные UI компоненты для приложения.
RecordButton, LevelMeter, StatusBar.
Совместимо с CustomTkinter.
"""

import tkinter as tk
import customtkinter as ctk
from typing import Callable, Optional
import logging

from .styles import COLORS, FONTS, SPACING, get_font_tuple

logger = logging.getLogger("voice_translator.app.components")


class RecordButton(tk.Canvas):
    """
    Компактная кнопка записи с анимацией пульсации.
    Использует tk.Canvas для кастомной отрисовки.
    """

    def __init__(
        self,
        parent,
        command: Optional[Callable[[bool], None]] = None,
        size: int = 80,
        **kwargs
    ):
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=COLORS.ctk_bg_dark,
            highlightthickness=0,
            **kwargs
        )
        try:
            self.configure(cursor="pointinghand")
        except tk.TclError:
            self.configure(cursor="hand2")

        self.command = command
        self.size = size
        self._is_recording = False
        self._pulse_state = 0
        self._animation_id = None

        self._draw()
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda _event: self._draw(hover=True))
        self.bind("<Leave>", lambda _event: self._draw())

    def _rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Рисует скругленный прямоугольник на Canvas."""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _draw(self, hover: bool = False):
        """Перерисовывает кнопку."""
        self.delete("all")

        center = self.size // 2
        padding = 3
        corner_radius = max(6, self.size // 5)
        inner_radius = max(6, int(self.size * 0.28))

        border_color = COLORS.recording_pulse if self._is_recording else COLORS.border
        shell_color = COLORS.button_hover if hover else "#15181f"

        self._rounded_rect(
            padding, padding,
            self.size - padding, self.size - padding,
            corner_radius,
            fill=shell_color,
            outline=border_color,
            width=2
        )

        # Внутренний элемент
        if self._is_recording:
            # Квадрат для стопа
            sq_size = inner_radius * 0.75
            self._rounded_rect(
                center - sq_size, center - sq_size,
                center + sq_size, center + sq_size,
                max(2, int(sq_size * 0.35)),
                fill=COLORS.recording_pulse,
                outline=""
            )
        else:
            # Круг для записи
            self.create_oval(
                center - inner_radius + 5, center - inner_radius + 5,
                center + inner_radius - 5, center + inner_radius - 5,
                fill=COLORS.accent_error,
                outline=""
            )

    def _on_click(self, event):
        """Обработчик клика."""
        self._is_recording = not self._is_recording

        if self._is_recording:
            self._start_pulse()
        else:
            self._stop_pulse()

        self._draw()

        if self.command:
            self.command(self._is_recording)

    def _start_pulse(self):
        """Запускает анимацию пульсации."""
        self._pulse_state = 0
        self._animate_pulse()

    def _stop_pulse(self):
        """Останавливает анимацию."""
        if self._animation_id:
            self.after_cancel(self._animation_id)
            self._animation_id = None
        self._pulse_state = 0

    def _animate_pulse(self):
        """Анимация пульсации."""
        if not self._is_recording:
            return

        self._pulse_state += 0.1
        if self._pulse_state > 1.0:
            self._pulse_state = 0

        self._draw()
        self._animation_id = self.after(50, self._animate_pulse)

    @property
    def is_recording(self) -> bool:
        """Состояние записи."""
        return self._is_recording

    def set_recording(self, recording: bool):
        """Устанавливает состояние записи."""
        if self._is_recording != recording:
            self._is_recording = recording
            if recording:
                self._start_pulse()
            else:
                self._stop_pulse()
            self._draw()


class LevelMeter(tk.Canvas):
    """
    Визуализатор уровня громкости.
    Использует tk.Canvas для кастомной отрисовки.
    """

    def __init__(
        self,
        parent,
        width: int = 300,
        height: int = SPACING.meter_height,
        segments: int = 30,
        **kwargs
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=COLORS.ctk_bg_dark,
            highlightthickness=0,
            **kwargs
        )

        self.meter_width = width
        self.meter_height = height
        self.segments = segments
        self._level = 0.0
        self._peak = 0.0
        self._peak_hold = 0

        self._draw()

    def _draw(self):
        """Перерисовывает meter."""
        self.delete("all")

        segment_width = (self.meter_width - (self.segments - 1) * 2) // self.segments

        for i in range(self.segments):
            x = i * (segment_width + 2)

            # Определяем цвет сегмента
            segment_pos = i / self.segments

            if segment_pos < self._level:
                if segment_pos < 0.6:
                    color = COLORS.level_meter
                elif segment_pos < 0.85:
                    color = COLORS.accent_warning
                else:
                    color = COLORS.accent_error
            elif segment_pos <= self._peak and self._peak_hold > 0:
                color = COLORS.level_meter_peak
            else:
                color = COLORS.ctk_frame_dark

            self.create_rectangle(
                x, 0,
                x + segment_width, self.meter_height,
                fill=color,
                outline=""
            )

    def set_level(self, level: float):
        """
        Устанавливает уровень (0.0 - 1.0).
        """
        self._level = max(0.0, min(1.0, level))

        # Peak hold
        if self._level > self._peak:
            self._peak = self._level
            self._peak_hold = 30  # Удержание ~1.5 сек при 50ms обновлении
        elif self._peak_hold > 0:
            self._peak_hold -= 1
            if self._peak_hold == 0:
                self._peak = self._level

        self._draw()

    def reset(self):
        """Сбрасывает meter."""
        self._level = 0.0
        self._peak = 0.0
        self._peak_hold = 0
        self._draw()


class StatusBar(ctk.CTkFrame):
    """
    Строка статуса с индикаторами.
    Использует CustomTkinter виджеты.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            height=28,
            corner_radius=0,
            fg_color="transparent",
            **kwargs
        )

        # Статус движка
        self._engine_label = ctk.CTkLabel(
            self,
            text="● Движок: —",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_muted
        )
        self._engine_label.pack(side="left", padx=SPACING.md)

        # Статус модели
        self._model_label = ctk.CTkLabel(
            self,
            text="Модель: —",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_muted
        )
        self._model_label.pack(side="left", padx=SPACING.md)

        # CPU
        self._cpu_label = ctk.CTkLabel(
            self,
            text="CPU: —%",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_muted
        )
        self._cpu_label.pack(side="right", padx=SPACING.md)

        # Кэш переводов
        self._cache_label = ctk.CTkLabel(
            self,
            text="Кэш: 0%",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_muted
        )
        self._cache_label.pack(side="right", padx=SPACING.md)

    def set_engine(self, engine: str, ready: bool = False):
        """Устанавливает статус движка."""
        color = COLORS.accent_success if ready else COLORS.accent_warning
        self._engine_label.configure(
            text=f"● Движок: {engine}",
            text_color=color
        )

    def set_model(self, model: str):
        """Устанавливает название модели."""
        self._model_label.configure(text=f"Модель: {model}")

    def set_cpu(self, percent: float):
        """Устанавливает загрузку CPU."""
        color = COLORS.text_muted
        if percent > 80:
            color = COLORS.accent_error
        elif percent > 50:
            color = COLORS.accent_warning

        self._cpu_label.configure(text=f"CPU: {percent:.0f}%", text_color=color)

    def set_cache(self, hit_rate: float):
        """Устанавливает hit rate кэша."""
        self._cache_label.configure(text=f"Кэш: {hit_rate*100:.0f}%")
```

---

## File: `app/gui.py`

```python
"""
Главный класс GUI приложения.
Объединяет все компоненты и управляет логикой.
Использует CustomTkinter для современного тёмного интерфейса.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import threading
import time
import logging
import json
from datetime import datetime
from typing import Optional, List
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from .styles import COLORS, FONTS, SPACING, get_font_tuple
from .components import RecordButton, LevelMeter, StatusBar
from utils.config import AppConfig, RecognitionConfig
from utils.threading_utils import (
    ThreadSafeQueue, EngineState, EngineManager,
    RecognitionResult, StoppableThread
)
from audio.capture import AudioCapture, AudioDevice
from recognition import create_recognizer
from translation import Translator, ARGOS_AVAILABLE

logger = logging.getLogger("voice_translator.app.gui")

# CustomTkinter настройки
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class TranscriptEntry:
    """Запись в транскрипте."""

    def __init__(self, original: str, translated: str = "", timestamp: float = 0):
        self.original = original
        self.translated = translated
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "translated": self.translated,
            "timestamp": self.timestamp,
            "time_str": datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")
        }


class VoiceTranslatorApp:
    """Главное приложение для распознавания русской речи и перевода."""

    TITLE = "Голосовой Переводчик"
    VERSION = "1.0.0"
    ENGINE_LABELS = {"Vosk": "vosk", "Whisper": "whisper"}
    ENGINE_VALUES = list(ENGINE_LABELS.keys())
    WHISPER_BACKEND_LABELS = {
        "whisper.cpp (GPU)": "whisper_cpp",
        "faster-whisper (CPU)": "faster",
        "openai (CPU)": "openai",
    }
    WHISPER_BACKEND_VALUES = list(WHISPER_BACKEND_LABELS.keys())
    WHISPER_MODEL_VALUES = ["tiny", "base", "small", "medium", "large-v3"]

    def __init__(self, config: AppConfig):
        self.config = config
        self.root: Optional[ctk.CTk] = None

        # Состояние
        self.engine_manager = EngineManager()
        self.result_queue: ThreadSafeQueue[RecognitionResult] = ThreadSafeQueue()
        self.transcript: List[TranscriptEntry] = []

        # Компоненты
        self.audio_capture: Optional[AudioCapture] = None
        self.translator: Optional[Translator] = None
        self.current_recognizer = None

        # Потоки
        self.recognition_thread: Optional[StoppableThread] = None
        self.init_thread: Optional[threading.Thread] = None

        # UI элементы
        self.text_area: Optional[tk.Text] = None
        self.level_meter: Optional[LevelMeter] = None
        self.record_button: Optional[RecordButton] = None
        self.engine_menu: Optional[ctk.CTkOptionMenu] = None
        self.backend_menu: Optional[ctk.CTkOptionMenu] = None
        self.whisper_model_menu: Optional[ctk.CTkOptionMenu] = None
        self.model_toggle: Optional[ctk.CTkSegmentedButton] = None
        self.status_bar: Optional[StatusBar] = None
        self.device_menu: Optional[ctk.CTkOptionMenu] = None
        self.sensitivity_slider: Optional[ctk.CTkSlider] = None
        self.sensitivity_label: Optional[ctk.CTkLabel] = None
        self.vad_slider: Optional[ctk.CTkSlider] = None
        self.vad_label: Optional[ctk.CTkLabel] = None
        self.recording_status: Optional[ctk.CTkLabel] = None

        # Устройства
        self.audio_devices: List[AudioDevice] = []
        self._device_names: List[str] = ["Загрузка..."]

        # Флаги
        self._is_recording = False
        # Partial-обновления (троттлинг и одна "живая" строка)
        self._pending_partial_text: str = ""
        self._last_applied_partial: str = ""
        self._partial_timer_id = None
        self._partial_mark_name = "partial_start"
        # Значение троттлинга из конфига (валидация уже в AppConfig)
        # Для Intel i5 4-core: 150ms чтобы разгрузить CPU от частых GUI-обновлений
        self._partial_throttle_ms: int = getattr(self.config, "partial_throttle_ms", 150)
        logger.info(f"Partial throttle: {self._partial_throttle_ms} ms")

    def run(self):
        """Запускает приложение."""
        self._create_window()
        self._create_ui()
        self._setup_bindings()
        self._start_init_thread()
        self._start_polling()

        logger.info("Приложение запущено")
        self.root.mainloop()

    def _create_window(self):
        """Создаёт главное окно."""
        self.root = ctk.CTk()
        self.root.title(f"{self.TITLE} v{self.VERSION}")
        self.root.geometry(f"{self.config.window_width}x{self.config.window_height}")
        self.root.minsize(500, 550)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_ui(self):
        """Создаёт UI."""
        main_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=SPACING.sm, pady=SPACING.xs)

        # Статус бар
        self.status_bar = StatusBar(main_frame)
        self.status_bar.pack(fill="x", pady=(0, SPACING.xs))

        # Заголовок
        header = ctk.CTkFrame(main_frame, corner_radius=0, fg_color="transparent")
        header.pack(fill="x", pady=(0, SPACING.xs))

        title_label = ctk.CTkLabel(
            header, text=self.TITLE,
            font=get_font_tuple(FONTS.size_xlarge, FONTS.weight_bold),
            text_color=COLORS.text_primary
        )
        title_label.pack(side="left")

        # Панель управления
        control_panel = ctk.CTkFrame(main_frame, corner_radius=SPACING.ctk_corner_radius)
        control_panel.pack(fill="x", pady=(0, SPACING.xs), padx=0)

        top_controls = ctk.CTkFrame(control_panel, corner_radius=0, fg_color="transparent")
        top_controls.pack(fill="x", padx=SPACING.sm, pady=(SPACING.xs, 2))

        # Выбор движка
        engine_frame = ctk.CTkFrame(top_controls, corner_radius=0, fg_color="transparent")
        engine_frame.pack(side="left", padx=(0, SPACING.sm))

        ctk.CTkLabel(
            engine_frame, text="Движок:",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_secondary
        ).pack(anchor="w")

        self.engine_menu = ctk.CTkOptionMenu(
            engine_frame,
            values=self.ENGINE_VALUES,
            command=self._on_engine_change,
            width=96,
            font=get_font_tuple(FONTS.size_small)
        )
        self.engine_menu.set(self._engine_label_from_config())
        self.engine_menu.pack(anchor="w", pady=(2, 0))

        backend_frame = ctk.CTkFrame(top_controls, corner_radius=0, fg_color="transparent")
        backend_frame.pack(side="left", padx=(0, SPACING.sm))

        ctk.CTkLabel(
            backend_frame, text="Backend:",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_secondary
        ).pack(anchor="w")

        self.backend_menu = ctk.CTkOptionMenu(
            backend_frame,
            values=self.WHISPER_BACKEND_VALUES,
            command=self._on_backend_change,
            width=168,
            font=get_font_tuple(FONTS.size_small)
        )
        self.backend_menu.set(self._backend_label_from_config())
        self.backend_menu.pack(anchor="w", pady=(2, 0))

        whisper_model_frame = ctk.CTkFrame(top_controls, corner_radius=0, fg_color="transparent")
        whisper_model_frame.pack(side="left", padx=(0, SPACING.sm))

        ctk.CTkLabel(
            whisper_model_frame, text="Whisper:",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_secondary
        ).pack(anchor="w")

        self.whisper_model_menu = ctk.CTkOptionMenu(
            whisper_model_frame,
            values=self.WHISPER_MODEL_VALUES,
            command=self._on_whisper_model_change,
            width=96,
            font=get_font_tuple(FONTS.size_small)
        )
        self.whisper_model_menu.set(self._whisper_model_from_config())
        self.whisper_model_menu.pack(anchor="w", pady=(2, 0))

        # Выбор модели Vosk
        vosk_model_frame = ctk.CTkFrame(top_controls, corner_radius=0, fg_color="transparent")
        vosk_model_frame.pack(side="left")

        ctk.CTkLabel(
            vosk_model_frame, text="Модель Vosk:",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_secondary
        ).pack(anchor="w")

        self.model_toggle = ctk.CTkSegmentedButton(
            vosk_model_frame,
            values=["Быстрая (0.42)", "Точная (0.22)"],
            command=self._on_model_change,
            font=get_font_tuple(FONTS.size_small),
            selected_color="#1a5a7a",
            selected_hover_color="#1a6a8a",
            unselected_color="#1a1a2e",
            unselected_hover_color="#252540"
        )
        # Устанавливаем начальное значение
        initial_model = "Точная (0.22)" if self.config.vosk_model_size == "large" else "Быстрая (0.42)"
        self.model_toggle.set(initial_model)
        self.model_toggle.pack(anchor="w", pady=(2, 0))
        self._sync_engine_controls()

        # Выбор устройства (CTkOptionMenu)
        device_frame = ctk.CTkFrame(top_controls, corner_radius=0, fg_color="transparent")
        device_frame.pack(side="right")

        ctk.CTkLabel(
            device_frame, text="Микрофон:",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_secondary
        ).pack(anchor="w")

        self.device_menu = ctk.CTkOptionMenu(
            device_frame,
            values=self._device_names,
            command=self._on_device_change,
            width=240,
            font=get_font_tuple(FONTS.size_small)
        )
        self.device_menu.pack(pady=(2, 0))

        # Слайдеры
        bottom_controls = ctk.CTkFrame(control_panel, corner_radius=0, fg_color="transparent")
        bottom_controls.pack(fill="x", padx=SPACING.sm, pady=(0, SPACING.xs))

        # Слайдер чувствительности
        sensitivity_frame = ctk.CTkFrame(bottom_controls, corner_radius=0, fg_color="transparent")
        sensitivity_frame.pack(side="left", fill="x", expand=True, padx=(0, SPACING.md))

        sens_header = ctk.CTkFrame(sensitivity_frame, corner_radius=0, fg_color="transparent")
        sens_header.pack(fill="x")

        ctk.CTkLabel(
            sens_header, text="Чувствительность микрофона:",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_secondary
        ).pack(side="left")

        self.sensitivity_label = ctk.CTkLabel(
            sens_header, text=str(self.config.sensitivity),
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.accent_primary,
            width=50
        )
        self.sensitivity_label.pack(side="right")

        self.sensitivity_slider = ctk.CTkSlider(
            sensitivity_frame,
            from_=100, to=2000,
            number_of_steps=38,
            command=self._on_sensitivity_change
        )
        self.sensitivity_slider.set(self.config.sensitivity)
        self.sensitivity_slider.pack(fill="x", pady=(2, 0))

        # Слайдер VAD
        vad_frame = ctk.CTkFrame(bottom_controls, corner_radius=0, fg_color="transparent")
        vad_frame.pack(side="right", fill="x", expand=True)

        vad_header = ctk.CTkFrame(vad_frame, corner_radius=0, fg_color="transparent")
        vad_header.pack(fill="x")

        ctk.CTkLabel(
            vad_header, text="Порог голоса (VAD):",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_secondary
        ).pack(side="left")

        self.vad_label = ctk.CTkLabel(
            vad_header, text=str(self.config.vad_threshold),
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.accent_primary,
            width=50
        )
        self.vad_label.pack(side="right")

        self.vad_slider = ctk.CTkSlider(
            vad_frame,
            from_=200, to=1000,
            number_of_steps=16,
            command=self._on_vad_change
        )
        self.vad_slider.set(self.config.vad_threshold)
        self.vad_slider.pack(fill="x", pady=(2, 0))

        # Центральная панель
        center_panel = ctk.CTkFrame(main_frame, corner_radius=0, fg_color="transparent", border_width=0)
        center_panel.pack(fill="x", pady=(0, SPACING.xs))

        # Контейнер для кнопки записи
        record_container = ctk.CTkFrame(center_panel, corner_radius=0, fg_color="transparent", border_width=0)
        record_container.pack(side="left", padx=(0, SPACING.sm), pady=0, anchor="n")

        self.record_button = RecordButton(record_container, command=self._on_record_toggle, size=34)
        self.record_button.pack(pady=0)

        meter_frame = ctk.CTkFrame(center_panel, corner_radius=0, fg_color="transparent", border_width=0)
        meter_frame.pack(side="left", fill="x", expand=True, pady=0, anchor="n")

        self.recording_status = ctk.CTkLabel(
            meter_frame, text="Нажмите кнопку для начала записи",
            font=get_font_tuple(FONTS.size_small),
            text_color=COLORS.text_secondary
        )
        self.recording_status.pack(anchor="w", pady=0)

        self.level_meter = LevelMeter(meter_frame, width=360, height=12)
        self.level_meter.pack(anchor="w", pady=0)

        # Кнопки копирования
        export_frame = ctk.CTkFrame(center_panel, corner_radius=0, fg_color="transparent", border_width=0)
        export_frame.pack(side="right", pady=0, anchor="n")

        ctk.CTkButton(
            export_frame, text="Копировать RU",
            command=self._copy_russian,
            width=104,
            height=30,
            font=get_font_tuple(FONTS.size_small, FONTS.weight_bold),
            fg_color=COLORS.button_bg,
            hover_color=COLORS.button_hover,
            text_color=COLORS.text_primary
        ).pack(side="left", padx=1, pady=0, anchor="n")

        ctk.CTkButton(
            export_frame, text="Копировать EN",
            command=self._copy_english,
            width=104,
            height=30,
            font=get_font_tuple(FONTS.size_small, FONTS.weight_bold),
            fg_color=COLORS.button_bg,
            hover_color=COLORS.button_hover,
            text_color=COLORS.accent_primary
        ).pack(side="left", padx=1, pady=0, anchor="n")

        # Область текста - используем CTkFrame как контейнер + tk.Text для tag поддержки
        text_frame = ctk.CTkFrame(main_frame, corner_radius=SPACING.ctk_corner_radius, border_width=0)
        text_frame.pack(fill="both", expand=True, pady=0)

        text_header = ctk.CTkFrame(text_frame, corner_radius=0, fg_color="transparent")
        text_header.pack(fill="x", padx=SPACING.sm, pady=(SPACING.xs, SPACING.xs))

        ctk.CTkLabel(
            text_header, text="Транскрипция и перевод",
            font=get_font_tuple(FONTS.size_normal, FONTS.weight_bold),
            text_color=COLORS.text_primary
        ).pack(side="left")

        ctk.CTkButton(
            text_header, text="Очистить",
            command=self._clear_transcript,
            width=80,
            height=28,
            font=get_font_tuple(FONTS.size_small),
            fg_color=COLORS.button_bg,
            hover_color=COLORS.button_hover,
            text_color=COLORS.text_secondary
        ).pack(side="right")

        # Контейнер для текстовой област�� (tk.Text для поддержки tag_config)
        text_container = ctk.CTkFrame(text_frame, corner_radius=0, fg_color=COLORS.bg_tertiary)
        text_container.pack(fill="both", expand=True, padx=SPACING.sm, pady=(0, SPACING.xs))

        # Scrollbar
        scrollbar = ctk.CTkScrollbar(text_container)
        scrollbar.pack(side="right", fill="y")

        # tk.Text для поддержки tag_configure и tag_add
        self.text_area = tk.Text(
            text_container, font=get_font_tuple(self.config.font_size),
            fg=COLORS.text_primary, bg=COLORS.bg_tertiary,
            insertbackground=COLORS.text_primary,
            selectbackground=COLORS.accent_primary,
            selectforeground=COLORS.bg_primary,
            wrap="word", padx=SPACING.sm, pady=SPACING.sm,
            yscrollcommand=scrollbar.set, state="normal",
            undo=True,
            borderwidth=0,
            highlightthickness=0
        )
        self.text_area.pack(fill="both", expand=True)
        scrollbar.configure(command=self.text_area.yview)

        # Контекстное меню для редактирования
        self._create_context_menu()

        # Теги форматирования
        self.text_area.tag_configure("timestamp", foreground=COLORS.text_muted,
                                     font=get_font_tuple(FONTS.size_small))
        self.text_area.tag_configure("original", foreground=COLORS.text_primary)
        self.text_area.tag_configure("translation", foreground=COLORS.accent_primary,
                                     lmargin1=30, lmargin2=30)
        self.text_area.tag_configure("partial", foreground=COLORS.text_secondary,
                                     font=get_font_tuple(self.config.font_size, "italic"))

    def _create_context_menu(self):
        """Создаёт контекстное меню для текстовой области."""
        self.context_menu = tk.Menu(self.root, tearoff=0,
                                    bg=COLORS.bg_secondary, fg=COLORS.text_primary,
                                    activebackground=COLORS.accent_primary,
                                    activeforeground=COLORS.bg_primary)
        self.context_menu.add_command(label="Вырезать", command=self._cut_text,
                                      accelerator="⌘X")
        self.context_menu.add_command(label="Копировать", command=self._copy_selection,
                                      accelerator="⌘C")
        self.context_menu.add_command(label="Вставить", command=self._paste_text,
                                      accelerator="⌘V")
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Выделить всё", command=self._select_all,
                                      accelerator="⌘A")
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Отменить", command=self._undo,
                                      accelerator="⌘Z")
        self.context_menu.add_command(label="Повторить", command=self._redo,
                                      accelerator="⇧⌘Z")
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Скопировать 🇷🇺 русский", command=self._copy_russian)
        self.context_menu.add_command(label="Скопировать 🇺🇸 английский", command=self._copy_english)

        # Привязка контекстного меню
        self.text_area.bind("<Button-2>", self._show_context_menu)  # Middle click
        self.text_area.bind("<Control-Button-1>", self._show_context_menu)  # Ctrl+click (macOS)
        if self.root.tk.call('tk', 'windowingsystem') == 'aqua':
            self.text_area.bind("<Button-3>", self._show_context_menu)  # Right click

    def _show_context_menu(self, event):
        """Показывает контекстное меню."""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _cut_text(self):
        """Вырезает выделенный текст."""
        try:
            self._copy_selection()
            self.text_area.delete("sel.first", "sel.last")
        except tk.TclError:
            pass

    def _paste_text(self):
        """Вставляет текст из буфера обмена."""
        try:
            text = self.root.clipboard_get()
            try:
                self.text_area.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
            self.text_area.insert("insert", text)
        except tk.TclError:
            pass

    def _select_all(self):
        """Выделяет весь текст."""
        self.text_area.tag_add("sel", "1.0", "end")
        return "break"

    def _undo(self):
        """Отменяет последнее действие."""
        try:
            self.text_area.edit_undo()
        except tk.TclError:
            pass

    def _redo(self):
        """Повторяет отменённое действие."""
        try:
            self.text_area.edit_redo()
        except tk.TclError:
            pass

    def _setup_bindings(self):
        """Настраивает горячие клавиши."""
        self.root.bind("<Command-r>", lambda e: self._toggle_recording())
        self.root.bind("<Command-s>", lambda e: self._export_txt())
        self.root.bind("<Command-c>", lambda e: self._copy_selection())
        self.root.bind("<Escape>", lambda e: self._stop_recording())
        # Дополнительные горячие клавиши для редактирования
        self.text_area.bind("<Command-a>", lambda e: self._select_all())
        self.text_area.bind("<Command-z>", lambda e: self._undo())
        self.text_area.bind("<Command-Shift-z>", lambda e: self._redo())

    def _start_init_thread(self):
        """Запускает фоновую инициализацию."""
        self.init_thread = threading.Thread(target=self._init_components, name="InitThread", daemon=True)
        self.init_thread.start()

    def _init_components(self):
        """Инициализирует аудио, распознаватели и переводчик."""
        logger.info("Инициализация компонентов...")
        self.engine_manager.state = EngineState.LOADING

        # Аудио
        try:
            self.audio_capture = AudioCapture(
                sample_rate=self.config.sample_rate,
                device_index=self.config.device_index
            )
            self.audio_capture.__enter__()
            self.audio_capture.set_level_callback(self._on_audio_level)

            self.audio_devices = self.audio_capture.get_input_devices()
            self.root.after(0, self._update_device_list)
            logger.info(f"Аудио инициализировано, {len(self.audio_devices)} устройств")
        except Exception as e:
            logger.error(f"Ошибка инициализации аудио: {e}")
            self.root.after(0, lambda: self._show_error("Ошибка", f"Микрофон: {e}"))
            return

        # Распознаватель
        try:
            self.current_recognizer = self._load_configured_recognizer()
            if self.current_recognizer:
                logger.info("Распознаватель загружен: %s", self._recognizer_engine_status(self.current_recognizer))
            else:
                logger.error("Не удалось загрузить распознаватель")
        except Exception as e:
            logger.error(f"Ошибка загрузки распознавателя: {e}")
            self.current_recognizer = None

        # Переводчик
        if ARGOS_AVAILABLE:
            try:
                self.translator = Translator(cache_size=self.config.translation_cache_size)
                if self.translator.load():
                    logger.info("Переводчик загружен")
                else:
                    self.translator = None
            except Exception as e:
                logger.error(f"Ошибка загрузки переводчика: {e}")
                self.translator = None

        self.engine_manager.state = EngineState.READY if self.current_recognizer else EngineState.ERROR
        self.root.after(0, self._update_status)
        logger.info("Инициализация завершена")

    def _update_device_list(self):
        """Обновляет список устройств."""
        self._device_names = [d.name for d in self.audio_devices]
        if self._device_names:
            self.device_menu.configure(values=self._device_names)

            # Ищем устройство по сохранённому имени
            idx = 0
            if self.config.device_name:
                for i, device in enumerate(self.audio_devices):
                    if device.name == self.config.device_name:
                        idx = i
                        break
                else:
                    # Если не нашли по имени, используем device_index
                    idx = min(self.config.device_index, len(self.audio_devices) - 1)
            else:
                idx = min(self.config.device_index, len(self.audio_devices) - 1)

            self.device_menu.set(self._device_names[idx])

            # Устанавливаем устройство в audio_capture
            if self.audio_capture and idx < len(self.audio_devices):
                device = self.audio_devices[idx]
                self.audio_capture.set_device(device.index)
                self.config.device_index = device.index
                self.config.device_name = device.name
                logger.info(f"Восстановлено устройство: {device.name}")

    def _engine_label_from_config(self) -> str:
        return "Whisper" if self.config.engine == "whisper" else "Vosk"

    def _backend_label_from_config(self) -> str:
        for label, backend in self.WHISPER_BACKEND_LABELS.items():
            if backend == self.config.whisper_backend:
                return label
        return "whisper.cpp (GPU)"

    def _whisper_model_from_config(self) -> str:
        if self.config.whisper_model in self.WHISPER_MODEL_VALUES:
            return self.config.whisper_model
        return "small"

    def _sync_engine_controls(self):
        """Keeps selector states aligned with the selected engine."""
        if not self.engine_menu:
            return

        is_whisper = self.config.engine == "whisper"
        self.engine_menu.set(self._engine_label_from_config())
        if self.backend_menu:
            self.backend_menu.set(self._backend_label_from_config())
            self.backend_menu.configure(state="normal" if is_whisper else "disabled")
        if self.whisper_model_menu:
            self.whisper_model_menu.set(self._whisper_model_from_config())
            self.whisper_model_menu.configure(state="normal" if is_whisper else "disabled")
        if self.model_toggle:
            model = "Точная (0.22)" if self.config.vosk_model_size == "large" else "Быстрая (0.42)"
            self.model_toggle.set(model)
            self.model_toggle.configure(state="disabled" if is_whisper else "normal")

    def _load_configured_recognizer(self):
        """Loads the configured recognizer through the shared factory."""
        rec_config = RecognitionConfig.from_app_config(self.config)
        return create_recognizer(self.config, rec_config)

    def _recognizer_engine_status(self, recognizer) -> str:
        class_name = recognizer.__class__.__name__
        if class_name == "VoskRecognizer":
            return "Vosk · CPU"
        if class_name == "WhisperCppRecognizer":
            device = "Metal (AMD RX 580)" if getattr(recognizer, "gpu_active", False) else "CPU"
            return f"Whisper · whisper.cpp · {device}"
        if class_name == "FasterWhisperRecognizer":
            return "Whisper · faster-whisper · CPU"
        if class_name == "WhisperRecognizer":
            return "Whisper · openai · CPU"
        return getattr(recognizer, "_model_name", recognizer.name)

    def _recognizer_model_status(self, recognizer) -> str:
        class_name = recognizer.__class__.__name__
        if class_name == "VoskRecognizer":
            return "Russian 0.22" if self.config.vosk_model_size == "large" else "Russian 0.42"
        return str(getattr(recognizer, "model_name", getattr(recognizer, "_model_name", "—")))

    def _recognizer_matches_config(self, recognizer) -> bool:
        expected_by_config = {
            ("vosk", ""): "VoskRecognizer",
            ("whisper", "whisper_cpp"): "WhisperCppRecognizer",
            ("whisper", "faster"): "FasterWhisperRecognizer",
            ("whisper", "openai"): "WhisperRecognizer",
        }
        expected = expected_by_config.get((self.config.engine, self.config.whisper_backend if self.config.engine == "whisper" else ""))
        return recognizer.__class__.__name__ == expected

    def _update_status(self):
        """Обновляет статус бар."""
        self._sync_engine_controls()
        if self.current_recognizer:
            self.status_bar.set_engine(self._recognizer_engine_status(self.current_recognizer), ready=True)
            self.status_bar.set_model(self._recognizer_model_status(self.current_recognizer))
        else:
            self.status_bar.set_engine("Не загружен", ready=False)
            self.status_bar.set_model("—")

    def _start_polling(self):
        """Запускает polling."""
        self._poll_results()
        self._poll_stats()

    def _poll_results(self):
        """Проверяет очередь результатов. Ограничиваем до 5 за вызов чтобы не блокировать GUI."""
        try:
            for _ in range(5):
                result = self.result_queue.get_nowait()
                if result is None:
                    break
                self._process_result(result)
        except Exception as e:
            logger.error(f"Ошибка обработки результата: {e}")

        if self.root:
            self.root.after(50, self._poll_results)

    def _poll_stats(self):
        """Обновляет статистику."""
        try:
            if PSUTIL_AVAILABLE:
                cpu = psutil.cpu_percent(interval=None)
                self.status_bar.set_cpu(cpu)

            if self.translator and self.translator.is_loaded:
                stats = self.translator.cache_stats
                self.status_bar.set_cache(stats["hit_rate"])
        except Exception as e:
            logger.debug(f"Ошибка статистики: {e}")

        if self.root:
            self.root.after(1000, self._poll_stats)

    def _process_result(self, result: RecognitionResult):
        """Обрабатывает результат распознавания."""
        if result.is_final:
            # Очистить возможный запланированный partial и удалить его из UI
            if hasattr(self, "_partial_timer_id") and self._partial_timer_id:
                try:
                    self.root.after_cancel(self._partial_timer_id)
                except Exception:
                    pass
                self._partial_timer_id = None
            self._pending_partial_text = ""
            self._clear_partial_text()

            # Добавляем финальную русскую фразу сразу (без перевода)
            entry = TranscriptEntry(result.text, "", result.timestamp)
            self.transcript.append(entry)

            ui_insert_index = self._append_final_original(entry)

            # Асинхронный перевод только финальных фраз, чтобы не блокировать GUI
            if self.translator and self.translator.is_loaded:
                t0 = time.perf_counter()
                future = self.translator.translate_async(result.text)

                def _on_done(fut):
                    try:
                        translated = fut.result() or ""
                    except Exception as e:
                        logger.error(f"Ошибка асинхронного перевода: {e}")
                        translated = ""

                    t1 = time.perf_counter()
                    logger.debug(f"[translate] done in {(t1 - t0):.3f}s, len={len(result.text)} cache={translated != ''}")

                    # Обновляем UI в главном потоке
                    if self.root:
                        def _apply():
                            entry.translated = translated
                            if translated:
                                try:
                                    # Вставляем перевод под оригиналом, даже если появились новые строки
                                    self.text_area.insert(ui_insert_index, "→ " + translated + "\n\n", ("translation",))
                                except Exception as ex:
                                    logger.debug(f"UI insert translation failed: {ex}")
                            # Прокрутка вниз
                            self.text_area.see("end")
                        try:
                            self.root.after(0, _apply)
                        except Exception:
                            _apply()

                future.add_done_callback(_on_done)
        else:
            # Троттлим обновления partial: одна "живая" строка, не чаще ~120мс
            self._pending_partial_text = result.text
            self._schedule_partial_update()

    def _add_to_text_area(self, entry: TranscriptEntry):
        """Добавляет запись в текстовую область (устаревший метод, оставлен для совместимости)."""
        return self._append_final_original(entry)

    def _append_final_original(self, entry: TranscriptEntry) -> str:
        """Добавляет финальную русскую фразу и возвращает mark-индекс для последующей вставки перевода."""
        try:
            t0 = time.perf_counter()
            time_str = datetime.fromtimestamp(entry.timestamp).strftime("[%H:%M:%S] ")
            self.text_area.insert("end", time_str, ("timestamp",))
            self.text_area.insert("end", entry.original + "\n", ("original",))

            # Создаём mark, куда позже вставим перевод
            mark_name = f"tr_mark_{int(entry.timestamp * 1000)}"
            try:
                self.text_area.mark_set(mark_name, "end")
                self.text_area.mark_gravity(mark_name, "left")
            except Exception as ex:
                logger.debug(f"Mark set failed: {ex}")
                mark_name = "end"

            self.text_area.see("end")
            t1 = time.perf_counter()
            logger.debug(f"[final-insert] len={len(entry.original)} took={(t1 - t0):.3f}s")

            # Ограничиваем размер текстовой области — удаляем старые строки при превышении лимита
            self._trim_text_area_if_needed()

            return mark_name
        except Exception as e:
            logger.error(f"Ошибка в��тавки финального текста: {e}")
            return "end"

    def _trim_text_area_if_needed(self, max_lines: int = 500):
        """Удаляет старые строки из текстовой области если превышен лимит."""
        try:
            line_count = int(self.text_area.index("end-1c").split(".")[0])
            if line_count > max_lines:
                # Удаляем первые строки с запасом
                delete_to = f"{line_count - max_lines + 50}.0"
                self.text_area.delete("1.0", delete_to)
        except Exception as e:
            logger.debug(f"Trim text area failed: {e}")

    def _clear_partial_text(self):
        """Удаляет partial текст (одна живая строка) из области."""
        try:
            if self.text_area:
                # Удаляем от mark до конца
                if self._partial_mark_name in self.text_area.mark_names():
                    self.text_area.delete(self._partial_mark_name, "end")
                    try:
                        self.text_area.mark_unset(self._partial_mark_name)
                    except Exception:
                        pass
                try:
                    self.text_area.tag_remove("partial", "1.0", "end")
                except tk.TclError:
                    pass
            self._last_applied_partial = ""
        except tk.TclError:
            pass

    def _schedule_partial_update(self):
        """Планирует отложённое обновление partial с троттлингом из конфига."""
        if not self.root:
            return
        # Отменяем предыдущий таймер
        if self._partial_timer_id:
            try:
                self.root.after_cancel(self._partial_timer_id)
            except Exception:
                pass
            self._partial_timer_id = None
        # Планируем новый с учётом конфига
        delay_ms = int(self._partial_throttle_ms)
        self._partial_timer_id = self.root.after(delay_ms, self._apply_partial_update)

    def _apply_partial_update(self):
        """Применяет отложенное обновление partial-строки."""
        self._partial_timer_id = None
        text = (self._pending_partial_text or "").strip()
        if not text:
            self._clear_partial_text()
            return

        if not self.text_area:
            return

        # Ограничиваем длину partial-текста чтобы избежать переполнения
        MAX_PARTIAL_LEN = 500
        if len(text) > MAX_PARTIAL_LEN:
            text = text[:MAX_PARTIAL_LEN] + "..."

        try:
            t0 = time.perf_counter()
            # Устанавливаем mark при первом обновлении
            if self._partial_mark_name not in self.text_area.mark_names():
                self.text_area.mark_set(self._partial_mark_name, "end")
                self.text_area.mark_gravity(self._partial_mark_name, "left")

            try:
                self.text_area.tag_remove("partial", "1.0", "end")
            except tk.TclError:
                pass

            # Переписываем только хвост от mark до конца
            self.text_area.delete(self._partial_mark_name, "end")
            self.text_area.insert("end", "⏳ " + text + "...\n", ("partial",))
            self.text_area.see("end")
            t1 = time.perf_counter()
            logger.debug(f"[partial-insert] len={len(text)} took={(t1 - t0):.3f}s")
            self._last_applied_partial = text
        except Exception as e:
            logger.debug(f"Partial update failed: {e}")

    def _clear_partial_text_compat(self):
        """Совместимость: устаревший метод, не используется."""
        pass

    def _update_partial_text(self):
        """Обновляет частичный текст."""
        if not self._partial_text:
            return

        # Удаляем предыдущий partial
        self._clear_partial_text()

        # Добавляем новый partial текст
        self.text_area.insert("end", "⏳ " + self._partial_text + "...\n", ("partial",))
        self.text_area.see("end")

    def _on_record_toggle(self, is_recording: bool):
        """Обработчик переключения записи."""
        if is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _toggle_recording(self):
        """Переключает состояние записи."""
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Начинает запись."""
        if self._is_recording:
            return

        if not self.current_recognizer:
            self._show_error("Ошибка", "Движок распознавания не загружен")
            self.record_button.set_recording(False)
            return

        if not self.audio_capture:
            self._show_error("Ошибка", "Аудио не инициализировано")
            self.record_button.set_recording(False)
            return

        if not self.audio_capture.start_capture():
            self._show_error("Ошибка", "Не удалось начать запись")
            self.record_button.set_recording(False)
            return

        self.current_recognizer.reset()
        self.result_queue.clear()
        self._partial_text = ""

        self.recognition_thread = StoppableThread(target=self._recognition_loop, name="RecognitionThread")
        self._is_recording = True
        self.recognition_thread.start()

        self.engine_manager.state = EngineState.RECORDING
        self.recording_status.configure(text="🔴 Запись...", text_color=COLORS.accent_error)
        self.record_button.set_recording(True)

        logger.info("Запись начата")

    def _stop_recording(self):
        """Останавливает запись."""
        if not self._is_recording:
            return

        self._is_recording = False

        if self.recognition_thread:
            self.recognition_thread.stop()
            self.recognition_thread.join(timeout=2.0)
            self.recognition_thread = None

        if self.audio_capture:
            self.audio_capture.stop_capture()

        self.engine_manager.state = EngineState.READY
        self.recording_status.configure(text="Нажмите кнопку для начала записи", text_color=COLORS.text_secondary)
        self.level_meter.reset()
        self.record_button.set_recording(False)

        # Очищаем partial текст
        self._clear_partial_text()

        logger.info("Запись остановлена")

    def _recognition_loop(self):
        """Основной цикл распознавания."""
        logger.debug("Recognition loop запущен")

        while self._is_recording and self.recognition_thread and not self.recognition_thread.stopped():
            try:
                chunk = self.audio_capture.get_audio_chunk(timeout=0.1)
                if chunk is None:
                    continue

                for result in self.current_recognizer.recognize_stream(chunk):
                    self.result_queue.put(result)

            except Exception as e:
                logger.error(f"Ошибка в recognition loop: {e}")
                break

        logger.debug("Recognition loop завершён")

    def _on_device_change(self, device_name: str):
        """Обработчик смены устройства."""
        if self._is_recording:
            self._show_error("Внимание", "Остановите запись перед сменой устройства")
            return

        # Находим индекс устройства по имени
        idx = -1
        for i, name in enumerate(self._device_names):
            if name == device_name:
                idx = i
                break

        if 0 <= idx < len(self.audio_devices):
            device = self.audio_devices[idx]
            if self.audio_capture:
                self.audio_capture.set_device(device.index)
            self.config.device_index = device.index
            self.config.device_name = device.name
            self._save_config()
            logger.info(f"Выбрано устройство: {device.name}")

    def _on_sensitivity_change(self, value: float):
        """Обработчик изменения чувствительности."""
        int_value = int(value)
        self.sensitivity_label.configure(text=str(int_value))
        self.config.sensitivity = int_value
        self._save_config()

    def _on_vad_change(self, value: float):
        """Обработчик изменения VAD порога."""
        int_value = int(value)
        self.vad_label.configure(text=str(int_value))
        self.config.vad_threshold = int_value
        if self.current_recognizer:
            self.current_recognizer.config.vad_threshold = int_value
        self._save_config()

    def _on_engine_change(self, engine_label: str):
        """Обработчик смены движка распознавания."""
        if self._is_recording:
            self._show_error("Внимание", "Остановите запись перед сменой движка")
            self._sync_engine_controls()
            return

        new_engine = self.ENGINE_LABELS.get(engine_label, "vosk")
        if new_engine == self.config.engine:
            return

        self.config.engine = new_engine
        self._save_config()
        self._sync_engine_controls()
        self._reload_recognizer(show_messages=True)

    def _on_backend_change(self, backend_label: str):
        """Обработчик смены Whisper backend."""
        if self._is_recording:
            self._show_error("Внимание", "Остановите запись перед сменой backend")
            self._sync_engine_controls()
            return

        new_backend = self.WHISPER_BACKEND_LABELS.get(backend_label, "whisper_cpp")
        if self.config.engine != "whisper" or new_backend == self.config.whisper_backend:
            return

        self.config.whisper_backend = new_backend
        self.config.whisper_cpp_use_gpu = new_backend == "whisper_cpp"
        self._save_config()
        self._reload_recognizer(show_messages=True)

    def _on_whisper_model_change(self, model_name: str):
        """Обработчик смены Whisper модели."""
        if self._is_recording:
            self._show_error("Внимание", "Остановите запись перед сменой модели")
            self._sync_engine_controls()
            return

        if self.config.engine != "whisper" or model_name == self.config.whisper_model:
            return

        self.config.whisper_model = model_name
        self._save_config()
        self._reload_recognizer(show_messages=True)

    def _on_model_change(self, model_name: str):
        """Обработчик смены модели Vosk."""
        if self._is_recording:
            self._show_error("Внимание", "Остановите запись перед сменой модели")
            # Возвращаем предыдущее значение
            prev_model = "Точная (0.22)" if self.config.vosk_model_size == "large" else "Быстрая (0.42)"
            self.model_toggle.set(prev_model)
            return

        # Определяем новый размер модели
        new_size = "large" if "0.22" in model_name else "small"

        if new_size == self.config.vosk_model_size:
            return  # Модель не изменилась

        # Проверяем наличие модели
        from pathlib import Path
        model_path = self.config.vosk_large_model_path if new_size == "large" else self.config.vosk_model_path
        if not Path(model_path).exists():
            self._show_error(
                "Модель не найдена",
                f"Модель не найдена: {model_path}\n\n"
                f"Скачайте модель:\n"
                f"wget https://alphacephei.com/vosk/models/vosk-model-ru-{'0.22' if new_size == 'large' else '0.42'}.zip\n"
                f"unzip vosk-model-ru-{'0.22' if new_size == 'large' else '0.42'}.zip -d models/"
            )
            # Возвращаем предыдущее значение
            prev_model = "Точная (0.22)" if self.config.vosk_model_size == "large" else "Быстрая (0.42)"
            self.model_toggle.set(prev_model)
            return

        # Обновляем конфигурацию
        self.config.vosk_model_size = new_size
        self._save_config()

        self._reload_recognizer(show_messages=True)

    def _reload_recognizer(self, show_messages: bool = False):
        """Перезагружает текущий распознаватель без блокировки Tk main loop."""
        if self.engine_manager.is_switching:
            self._show_error("Внимание", "Переключение движка уже выполняется")
            self._sync_engine_controls()
            return

        requested_label = self._configured_engine_summary()
        # Показываем статус загрузки
        self.status_bar.set_engine("Загрузка...", ready=False)
        self.status_bar.set_model("...")
        if self.recording_status:
            self.recording_status.configure(text="Загрузка движка...", text_color=COLORS.accent_warning)

        def reload_in_thread():
            new_recognizer = None
            error = None
            try:
                with self.engine_manager.switch_engine():
                    old_recognizer = self.current_recognizer
                    self.current_recognizer = None
                    if old_recognizer:
                        old_recognizer.unload()

                    new_recognizer = self._load_configured_recognizer()
                    self.current_recognizer = new_recognizer
                    self.engine_manager.state = EngineState.READY if new_recognizer else EngineState.ERROR
            except Exception as e:
                error = e
                logger.error(f"Ошибка перезагрузки распознавателя: {e}")
                self.current_recognizer = None
                self.engine_manager.state = EngineState.ERROR

            # Обновляем UI в главном потоке
            self.root.after(0, lambda: self._finish_recognizer_reload(new_recognizer, requested_label, error, show_messages))

        # Запускаем в фоновом потоке
        threading.Thread(target=reload_in_thread, name="RecognizerReloadThread", daemon=True).start()

    def _finish_recognizer_reload(self, recognizer, requested_label: str, error: Optional[Exception], show_messages: bool):
        """Applies recognizer reload results on the Tk main thread."""
        self._update_status()
        if self.recording_status:
            self.recording_status.configure(text="Нажмите кнопку для начала записи", text_color=COLORS.text_secondary)

        if error:
            self._show_error("Ошибка", f"Не удалось загрузить {requested_label}: {error}")
            return

        if not recognizer:
            self._show_error("Ошибка", f"Не удалось загрузить {requested_label}. Проверьте модели и зависимости.")
            return

        if show_messages and not self._recognizer_matches_config(recognizer):
            self._show_warning(
                "Fallback",
                f"{requested_label} недоступен. Загружен: {self._recognizer_engine_status(recognizer)}"
            )
            return

        if (
            show_messages
            and self.config.engine == "whisper"
            and self.config.whisper_backend == "whisper_cpp"
            and self.config.whisper_cpp_use_gpu
            and recognizer.__class__.__name__ == "WhisperCppRecognizer"
            and not getattr(recognizer, "gpu_active", False)
        ):
            self._show_warning(
                "Fallback",
                "whisper.cpp GPU не подтвердил Metal. Загружен CPU fallback."
            )

    def _configured_engine_summary(self) -> str:
        if self.config.engine == "vosk":
            model = "0.22" if self.config.vosk_model_size == "large" else "0.42"
            return f"Vosk {model}"
        return f"Whisper {self.config.whisper_backend} {self.config.whisper_model}"

    def _save_config(self):
        """Сохраняет конфигурацию в файл."""
        self.config.save()

    def _on_audio_level(self, level: float):
        """Обработчик уровня громкости (вызывается из audio thread)."""
        # ВАЖНО: Маршалим обновление UI в главный поток для thread safety
        if self.level_meter and self.root:
            self.root.after(0, lambda l=level: self.level_meter.set_level(l))

    def _clear_transcript(self):
        """Очищает транскрипт."""
        self.transcript.clear()
        self.text_area.delete("1.0", "end")
        logger.info("Транскрипт очищен")

    def _copy_selection(self):
        """Копирует выделенный текст."""
        try:
            selection = self.text_area.get("sel.first", "sel.last")
            self.root.clipboard_clear()
            self.root.clipboard_append(selection)
        except tk.TclError:
            pass

    def _copy_russian(self):
        """Копирует весь русский текст (оригинал) в буфер обмена."""
        if not self.transcript:
            return

        russian_text = "\n".join(entry.original for entry in self.transcript)
        self.root.clipboard_clear()
        self.root.clipboard_append(russian_text)
        logger.info("Русский текст скопирован в буфер обмена")

    def _copy_english(self):
        """Копирует весь английский текст (перевод) в буфер обмена."""
        if not self.transcript:
            return

        english_text = "\n".join(entry.translated for entry in self.transcript if entry.translated)
        self.root.clipboard_clear()
        self.root.clipboard_append(english_text)
        logger.info("Английский текст скопирован в буфер обмена")

    def _export_txt(self):
        """Экспортирует в TXT."""
        if not self.transcript:
            self._show_error("Внимание", "Нет данных для экспорта")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    for entry in self.transcript:
                        time_str = datetime.fromtimestamp(entry.timestamp).strftime("[%H:%M:%S]")
                        f.write(f"{time_str} {entry.original}\n")
                        if entry.translated:
                            f.write(f"         → {entry.translated}\n")
                        f.write("\n")
                logger.info(f"Экспортировано в {path}")
            except IOError as e:
                self._show_error("Ошибка", f"Не удалось сохранить: {e}")

    def _export_json(self):
        """Экспортирует в JSON."""
        if not self.transcript:
            self._show_error("Внимание", "Нет данных для экспорта")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        if path:
            try:
                data = {
                    "version": self.VERSION,
                    "engine": self.config.engine,
                    "entries": [e.to_dict() for e in self.transcript]
                }
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"Экспортировано в {path}")
            except IOError as e:
                self._show_error("Ошибка", f"Не удалось сохранить: {e}")

    def _export_srt(self):
        """Экспортирует в SRT."""
        if not self.transcript:
            self._show_error("Внимание", "Нет данных для экспорта")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".srt",
            filetypes=[("SRT files", "*.srt"), ("All files", "*.*")],
            initialfile=f"subtitles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.srt"
        )

        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    for i, entry in enumerate(self.transcript, 1):
                        start_time = datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S,000")
                        end_time = datetime.fromtimestamp(entry.timestamp + 3).strftime("%H:%M:%S,000")

                        f.write(f"{i}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{entry.original}\n")
                        if entry.translated:
                            f.write(f"{entry.translated}\n")
                        f.write("\n")
                logger.info(f"Экспортировано в {path}")
            except IOError as e:
                self._show_error("Ошибка", f"Не удалось сохранить: {e}")

    def _show_error(self, title: str, message: str):
        """Показывает сообщение об ошибке."""
        messagebox.showerror(title, message)

    def _show_warning(self, title: str, message: str):
        """Показывает предупреждение."""
        messagebox.showwarning(title, message)

    def _on_close(self):
        """Обработчик закрытия окна."""
        logger.info("Закрытие приложения...")

        self._stop_recording()
        self.config.save()

        if self.audio_capture:
            self.audio_capture.__exit__(None, None, None)

        if self.current_recognizer:
            self.current_recognizer.unload()

        if self.translator:
            self.translator.unload()

        self.root.destroy()
        self.root = None
```

---

## File: `app/styles.py`

```python
"""
Стили и цветовые схемы для UI приложения.
Тёмная тема с акцентами. CustomTkinter совместимый.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ColorScheme:
    """Цветовая схема приложения."""

    # Основные цвета фона (CustomTkinter dark theme compatible)
    bg_primary: str = "#1a1a2e"      # Тёмно-синий
    bg_secondary: str = "#16213e"    # Чуть светлее
    bg_tertiary: str = "#0f3460"     # Акцентный фон

    # CTk-compatible фоновые цвета
    ctk_bg_dark: str = "#2b2b2b"     # Для Canvas компонентов в тёмной теме
    ctk_frame_dark: str = "#242424"  # Фон CTkFrame
    ctk_frame_border: str = "#3d3d3d"  # Границы фреймов

    # Цвета текста
    text_primary: str = "#e8e8e8"    # Основной текст
    text_secondary: str = "#a0a0a0"  # Вторичный текст
    text_muted: str = "#606060"      # Приглушённый

    # Акцентные цвета
    accent_primary: str = "#00d4ff"   # Голубой (перевод)
    accent_secondary: str = "#7b68ee" # Фиолетовый
    accent_success: str = "#00ff88"   # Зелёный (запись)
    accent_warning: str = "#ffaa00"   # Оранжевый
    accent_error: str = "#ff4444"     # Красный

    # Цвета для элементов управления
    button_bg: str = "#2d2d44"
    button_hover: str = "#3d3d54"
    button_active: str = "#4d4d64"
    button_disabled: str = "#1d1d2e"

    # Границы
    border: str = "#3d3d54"
    border_focus: str = "#00d4ff"

    # Индикаторы
    recording_pulse: str = "#ff4444"
    level_meter: str = "#00ff88"
    level_meter_peak: str = "#ffaa00"

    # CTk Button цвета
    ctk_button_fg: str = "#1f6aa5"
    ctk_button_hover: str = "#144870"


@dataclass(frozen=True)
class Fonts:
    """Шрифты приложения."""

    # Основные шрифты (macOS)
    family_primary: str = "SF Pro Display"
    family_mono: str = "SF Mono"
    family_fallback: str = "Helvetica Neue"

    # Размеры
    size_small: int = 11
    size_normal: int = 13
    size_large: int = 15
    size_xlarge: int = 18
    size_title: int = 24

    # Веса
    weight_normal: str = "normal"
    weight_bold: str = "bold"


@dataclass(frozen=True)
class Spacing:
    """Отступы и размеры."""

    # Отступы
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32

    # Скругления
    radius_sm: int = 4
    radius_md: int = 8
    radius_lg: int = 12
    radius_xl: int = 16

    # CTk corner radius
    ctk_corner_radius: int = 10

    # Размеры элементов
    button_height: int = 40
    button_width: int = 120
    toggle_width: int = 200
    toggle_height: int = 36
    slider_height: int = 24
    meter_height: int = 8


# Глобальные экземпляры
COLORS = ColorScheme()
FONTS = Fonts()
SPACING = Spacing()


def get_font_tuple(size: int = FONTS.size_normal, weight: str = FONTS.weight_normal) -> Tuple[str, int, str]:
    """Возвращает tuple для tkinter font."""
    return (FONTS.family_primary, size, weight)


def get_ctk_font(size: int = FONTS.size_normal, weight: str = FONTS.weight_normal) -> Tuple[str, int, str]:
    """Возвращает tuple для CustomTkinter font."""
    return (FONTS.family_primary, size, weight)


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Конвертирует HEX в RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Конвертирует RGB в HEX."""
    return f"#{r:02x}{g:02x}{b:02x}"


def blend_colors(color1: str, color2: str, factor: float = 0.5) -> str:
    """Смешивает два цвета."""
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)

    r = int(r1 + (r2 - r1) * factor)
    g = int(g1 + (g2 - g1) * factor)
    b = int(b1 + (b2 - b1) * factor)

    return rgb_to_hex(r, g, b)
```

---

## File: `translation/__init__.py`

```python
"""Translation package - офлайн перевод."""
from .translator import Translator, TranslationCache, ARGOS_AVAILABLE

__all__ = ['Translator', 'TranslationCache', 'ARGOS_AVAILABLE']
```

---

## File: `translation/translator.py`

```python
"""
Модуль перевода с использованием Argos Translate.
Включает LRU кэширование для производительности.
"""

import logging
import re
import threading
from collections import OrderedDict
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, Future
import time

logger = logging.getLogger("voice_translator.translation")

# Импортируем argostranslate с обработкой ошибки
try:
    import argostranslate.package
    import argostranslate.translate
    ARGOS_AVAILABLE = True
except ImportError:
    ARGOS_AVAILABLE = False
    logger.warning("Argos Translate не установлен. Используйте: pip install argostranslate")


class TranslationCache:
    """
    Thread-safe LRU кэш для переводов.
    """
    
    def __init__(self, maxsize: int = 100):
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._maxsize = maxsize
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[str]:
        """
        Получает значение из кэша.
        Перемещает элемент в конец (LRU).
        """
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None
    
    def put(self, key: str, value: str) -> None:
        """
        Добавляет значение в кэш.
        Удаляет старейший элемент при переполнении.
        """
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self._maxsize:
                    self._cache.popitem(last=False)
                self._cache[key] = value
    
    def clear(self) -> None:
        """Очищает кэш."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    @property
    def stats(self) -> dict:
        """Статистика кэша."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                "size": len(self._cache),
                "maxsize": self._maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate
            }


class OfflineSentenceSplitter:
    """Small offline sentence splitter for short live phrases."""

    def split_sentences(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []

        parts = re.findall(r"[^.!?…]+[.!?…]*", text)
        sentences = [part.strip() for part in parts if part.strip()]
        return sentences or [text]


class Translator:
    """
    Офлайн переводчик Russian → English с использованием Argos Translate.
    """
    
    SOURCE_LANG = "ru"
    TARGET_LANG = "en"
    
    def __init__(self, cache_size: int = 100):
        self._cache = TranslationCache(maxsize=cache_size)
        self._translation_fn = None
        self._is_loaded = False
        self._lock = threading.Lock()
        # 1 worker для Intel i5 4-core — избегаем конкуренции с Vosk за CPU
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="Translator")
    
    def load(self) -> bool:
        """
        Загружает и инициализирует переводчик.
        Скачивает языковой пакет если нужно.
        """
        if not ARGOS_AVAILABLE:
            logger.error("Argos Translate недоступен")
            return False
        
        if self._is_loaded:
            return True
        
        try:
            logger.info("Инициализация Argos Translate...")

            # Проверяем, установлен ли нужный пакет
            installed_languages = argostranslate.translate.get_installed_languages()
            
            source_lang = None
            target_lang = None
            
            for lang in installed_languages:
                if lang.code == self.SOURCE_LANG:
                    source_lang = lang
                elif lang.code == self.TARGET_LANG:
                    target_lang = lang
            
            # Если пакет не установлен, устанавливаем
            if source_lang is None or target_lang is None:
                logger.info("Установка языкового пакета ru→en...")

                # Обновляем индекс только если локального пакета нет.
                import socket
                original_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(10.0)
                try:
                    argostranslate.package.update_package_index()
                finally:
                    socket.setdefaulttimeout(original_timeout)
                
                available_packages = argostranslate.package.get_available_packages()
                package_to_install = None
                
                for pkg in available_packages:
                    if pkg.from_code == self.SOURCE_LANG and pkg.to_code == self.TARGET_LANG:
                        package_to_install = pkg
                        break
                
                if package_to_install is None:
                    logger.error("Языковой пакет ru→en не найден")
                    return False
                
                download_path = package_to_install.download()
                argostranslate.package.install_from_path(download_path)
                logger.info("Языковой пакет установлен")
                
                # Обновляем список языков
                installed_languages = argostranslate.translate.get_installed_languages()
                for lang in installed_languages:
                    if lang.code == self.SOURCE_LANG:
                        source_lang = lang
                    elif lang.code == self.TARGET_LANG:
                        target_lang = lang
            
            # Получаем функцию перевода
            if source_lang and target_lang:
                self._translation_fn = source_lang.get_translation(target_lang)
                
                if self._translation_fn is None:
                    logger.error("Не удалось создать функцию перевода")
                    return False

                self._force_offline_sentence_splitter(self._translation_fn)
                
                self._is_loaded = True
                logger.info("Argos Translate инициализирован")
                return True
            
            logger.error("Не удалось найти языки после установки")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка инициализации Argos: {e}")
            return False

    def _force_offline_sentence_splitter(self, translation_fn) -> None:
        splitter = OfflineSentenceSplitter()
        self._replace_sentencizer(translation_fn, splitter)

    def _replace_sentencizer(self, translation_fn, splitter: OfflineSentenceSplitter) -> None:
        if hasattr(translation_fn, "sentencizer"):
            translation_fn.sentencizer = splitter

        for attr in ("underlying", "t1", "t2"):
            child = getattr(translation_fn, attr, None)
            if child is not None:
                self._replace_sentencizer(child, splitter)
    
    def unload(self) -> None:
        """Выгружает переводчик."""
        self._translation_fn = None
        self._is_loaded = False
        self._cache.clear()
        self._executor.shutdown(wait=False)
        logger.info("Переводчик выгружен")
    
    def translate(self, text: str) -> Optional[str]:
        """
        Синхронный перевод текста.
        Использует кэш для повторных запросов.
        """
        if not text or not text.strip():
            return None
        
        text = text.strip()
        
        # Проверяем кэш
        cached = self._cache.get(text)
        if cached is not None:
            logger.debug(f"Cache hit: {text[:30]}...")
            return cached
        
        if not self._is_loaded or self._translation_fn is None:
            logger.error("Переводчик не загружен")
            return None
        
        try:
            start_time = time.time()
            
            with self._lock:
                translated = self._translation_fn.translate(text)
            
            translation_time = time.time() - start_time
            logger.debug(f"Перевод за {translation_time:.3f}с: {text[:30]} → {translated[:30]}")
            
            # Сохраняем в кэш
            self._cache.put(text, translated)
            
            return translated
            
        except Exception as e:
            logger.error(f"Ошибка перевода: {e}")
            return None
    
    def translate_async(self, text: str) -> Future:
        """
        Асинхронный перевод текста.
        Возвращает Future с результатом.
        """
        return self._executor.submit(self.translate, text)
    
    @property
    def is_loaded(self) -> bool:
        """Проверяет, загружен ли переводчик."""
        return self._is_loaded
    
    @property
    def cache_stats(self) -> dict:
        """Возвращает статистику кэша."""
        return self._cache.stats
    
    def __enter__(self):
        self.load()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unload()
```

---

## File: `tests/__init__.py`

```python
"""Tests package."""
```

---

## File: `tests/test_audio_capture.py`

```python
"""
Тесты отказоустойчивости AudioCapture.
"""

import unittest
from unittest.mock import patch

from audio.capture import AudioCapture, AudioDevice


class _FakeStream:
    def __init__(self):
        self.stopped = False
        self.closed = False

    def is_active(self) -> bool:
        return True

    def read(self, chunk_size: int, exception_on_overflow: bool = False) -> bytes:
        return b"\x00" * chunk_size

    def stop_stream(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


class _FakePyAudio:
    def __init__(self, fail_on: set[int], fallback_ok_index: int):
        self.fail_on = fail_on
        self.fallback_ok_index = fallback_ok_index
        self.calls: list[int | None] = []
        self.stream = _FakeStream()

    def open(self, **kwargs):
        idx = kwargs.get("input_device_index")
        self.calls.append(idx)
        if idx in self.fail_on:
            raise OSError("[Errno -9986] Internal PortAudio error")
        if idx != self.fallback_ok_index:
            raise OSError(f"Unexpected device index: {idx}")
        return self.stream


class TestAudioCapture(unittest.TestCase):
    def test_start_capture_retries_with_default_device_when_selected_fails(self):
        """Если сохранённое устройство недоступно, захват должен переключиться на fallback."""
        capture = AudioCapture(device_index=7)
        fake_pa = _FakePyAudio(fail_on={7}, fallback_ok_index=2)
        capture._pyaudio = fake_pa

        with patch.object(AudioCapture, "_capture_loop", lambda self: None):
            with patch.object(
                capture,
                "get_default_input_device",
                lambda: AudioDevice(index=2, name="Default Mic", channels=1, sample_rate=16000, is_input=True),
            ):
                self.assertTrue(capture.start_capture())
                self.assertEqual(fake_pa.calls, [7, 2])

        capture.stop_capture()
```

---

## File: `tests/test_core.py`

```python
"""
Тесты для Russian Voice Translator.
Запуск: python -m pytest tests/ -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfig:
    """Тесты конфигурации."""
    
    def test_config_defaults(self):
        from utils.config import AppConfig
        config = AppConfig()
        assert config.engine in ["vosk", "whisper"]
        assert 100 <= config.sensitivity <= 2000
    
    def test_config_validation(self):
        from utils.config import AppConfig
        config = AppConfig(sensitivity=5000, vad_threshold=50)
        assert config.sensitivity == 2000
        assert config.vad_threshold == 200


class TestTranslationCache:
    """Тесты LRU кэша."""
    
    def test_cache_lru_eviction(self):
        from translation.translator import TranslationCache
        cache = TranslationCache(maxsize=3)
        cache.put("a", "1")
        cache.put("b", "2")
        cache.put("c", "3")
        cache.get("a")
        cache.put("d", "4")
        assert cache.get("a") == "1"
        assert cache.get("b") is None


class TestHallucinationFilter:
    """Тесты фильтра галлюцинаций."""
    
    def test_filter_hallucinations(self):
        from recognition.whisper_engine import HallucinationFilter
        filt = HallucinationFilter()
        assert filt.is_hallucination("Редактор субтитров")
        assert filt.is_hallucination("да да да да да да")
        assert not filt.is_hallucination("Привет, как дела?")


class TestWhisperCppRecognizer:
    """Тесты wrapper-логики whisper.cpp без загрузки модели."""

    def test_recognize_uses_stable_russian_decode_params(self):
        import numpy as np

        from recognition.whispercpp_engine import WhisperCppRecognizer
        from utils.config import RecognitionConfig

        class Segment:
            text = "Привет мир"

        class FakeModel:
            def __init__(self):
                self.params = {}

            def transcribe(self, _audio, **params):
                self.params = params
                required = {
                    "language": "ru",
                    "translate": False,
                    "no_context": True,
                    "no_timestamps": True,
                    "single_segment": True,
                    "print_progress": False,
                    "suppress_nst": True,
                }
                if all(params.get(key) == value for key, value in required.items()):
                    return [Segment()]
                return []

        fake_model = FakeModel()
        recognizer = WhisperCppRecognizer(RecognitionConfig(), language="ru")
        recognizer._is_loaded = True
        recognizer._model = fake_model
        recognizer.gpu_active = True

        audio = np.array([1000, -1000], dtype=np.int16).tobytes()
        result = recognizer.recognize(audio)

        assert result is not None
        assert result.text == "Привет мир"
        assert result.engine == "whisper.cpp (Metal)"
        assert fake_model.params["translate"] is False

    def test_filters_english_live_fillers(self):
        from recognition.whispercpp_engine import WhisperCppRecognizer
        from utils.config import RecognitionConfig

        recognizer = WhisperCppRecognizer(RecognitionConfig(), language="ru")

        assert recognizer._clean_text("the") == ""
        assert recognizer._clean_text("ist") == ""
        assert recognizer._clean_text("multingatt") == ""
        assert recognizer._clean_text("funded") == ""
        assert recognizer._clean_text("thanks for watching") == ""
        assert recognizer._clean_text("Нихера не работает сюда.") == "Нихера не работает сюда."

    def test_filters_subtitle_and_garbled_hallucinations(self):
        from recognition.whispercpp_engine import WhisperCppRecognizer
        from utils.config import RecognitionConfig

        recognizer = WhisperCppRecognizer(RecognitionConfig(), language="ru")

        assert recognizer._clean_text("Смотрите на видео!") == ""
        assert recognizer._clean_text("СПОКОЙНАЯ МУЗЫКА") == ""
        assert recognizer._clean_text("Смешка.") == ""
        assert recognizer._clean_text("fl этотですdskem, that нель-c lives than- onère") == ""
        assert recognizer._clean_text("�-ice�ice predideаа е, yсьто mak") == ""
        assert recognizer._clean_text("Однажды в студию") == "Однажды в студию"

    def test_prefers_local_ggml_model_file(self):
        import tempfile
        from pathlib import Path

        from recognition.whispercpp_engine import WhisperCppRecognizer
        from utils.config import RecognitionConfig

        with tempfile.TemporaryDirectory() as tmp:
            model_file = Path(tmp) / "ggml-medium.bin"
            model_file.write_bytes(b"local model placeholder")
            recognizer = WhisperCppRecognizer(
                RecognitionConfig(),
                model_name="medium",
                model_dir=tmp,
                language="ru",
            )

            assert recognizer._model_path() == str(model_file)


class TestOfflineArgosSentencizer:
    """Тесты локального разбиения фраз для Argos."""

    def test_short_live_phrases_stay_offline(self):
        from translation.translator import OfflineSentenceSplitter

        splitter = OfflineSentenceSplitter()

        assert splitter.split_sentences("однажды в студёную зимнюю пору") == [
            "однажды в студёную зимнюю пору"
        ]
        assert splitter.split_sentences("Привет. Как дела?") == ["Привет.", "Как дела?"]


class TestThreadingUtils:
    """Тесты thread-safe утилит."""
    
    def test_queue(self):
        from utils.threading_utils import ThreadSafeQueue
        queue = ThreadSafeQueue()
        queue.put("item")
        assert queue.get() == "item"
    
    def test_counter(self):
        from utils.threading_utils import AtomicCounter
        counter = AtomicCounter()
        assert counter.increment() == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## File: `utils/__init__.py`

```python
"""Utils package - утилиты для приложения."""
from .config import AppConfig, RecognitionConfig
from .logging_config import setup_logging, LoggerMixin
from .threading_utils import (
    ThreadSafeQueue, 
    EngineState, 
    EngineManager,
    RecognitionResult,
    TranslationResult,
    StoppableThread,
    AtomicCounter
)

__all__ = [
    'AppConfig',
    'RecognitionConfig', 
    'setup_logging',
    'LoggerMixin',
    'ThreadSafeQueue',
    'EngineState',
    'EngineManager',
    'RecognitionResult',
    'TranslationResult',
    'StoppableThread',
    'AtomicCounter',
]
```

---

## File: `utils/config.py`

```python
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
```

---

## File: `utils/logging_config.py`

```python
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
```

---

## File: `utils/threading_utils.py`

```python
"""
Thread-safe утилиты для работы с многопоточностью.
"""

import threading
import queue
from contextlib import contextmanager
from typing import TypeVar, Generic, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum, auto
import logging
import time

logger = logging.getLogger("voice_translator.threading")

T = TypeVar('T')


class ThreadSafeQueue(Generic[T]):
    """Thread-safe очередь с типизацией."""
    
    def __init__(self, maxsize: int = 0):
        self._queue: queue.Queue[T] = queue.Queue(maxsize=maxsize)
    
    def put(self, item: T, block: bool = True, timeout: Optional[float] = None) -> None:
        """Добавляет элемент в очередь."""
        self._queue.put(item, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[T]:
        """Извлекает элемент из очереди. Возвращает None при таймауте."""
        try:
            return self._queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None
    
    def get_nowait(self) -> Optional[T]:
        """Извлекает элемент без ожидания."""
        return self.get(block=False)
    
    def clear(self) -> int:
        """Очищает очередь. Возвращает количество удалённых элементов."""
        count = 0
        while True:
            try:
                self._queue.get_nowait()
                count += 1
            except queue.Empty:
                break
        return count
    
    def qsize(self) -> int:
        """Приблизительный размер очереди."""
        return self._queue.qsize()
    
    def empty(self) -> bool:
        """Проверяет, пуста ли очередь."""
        return self._queue.empty()


class EngineState(Enum):
    """Состояния движка распознавания."""
    IDLE = auto()
    LOADING = auto()
    READY = auto()
    RECORDING = auto()
    PROCESSING = auto()
    SWITCHING = auto()
    ERROR = auto()


@dataclass
class RecognitionResult:
    """Результат распознавания речи."""
    text: str
    is_final: bool
    confidence: float = 0.0
    engine: str = ""
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class TranslationResult:
    """Результат перевода."""
    original: str
    translated: str
    cached: bool = False
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class EngineManager:
    """
    Менеджер состояния движка с thread-safe переключением.
    Предотвращает race conditions при смене движка.
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._state = EngineState.IDLE
        self._switching = threading.Event()
        self._state_callbacks: list[Callable[[EngineState], None]] = []
    
    @property
    def state(self) -> EngineState:
        """Текущее состояние движка."""
        with self._lock:
            return self._state
    
    @state.setter
    def state(self, new_state: EngineState) -> None:
        """Устанавливает новое состояние и уведомляет callbacks."""
        with self._lock:
            old_state = self._state
            self._state = new_state
            logger.debug(f"Engine state: {old_state.name} -> {new_state.name}")
            # Копируем callbacks под lock чтобы избежать race condition
            callbacks = self._state_callbacks.copy()
        
        # Вызываем callbacks вне lock чтобы не блокировать другие потоки
        for callback in callbacks:
            try:
                callback(new_state)
            except Exception as e:
                logger.error(f"State callback error: {e}")
    
    def add_state_callback(self, callback: Callable[[EngineState], None]) -> None:
        """Добавляет callback для отслеживания изменений состояния."""
        self._state_callbacks.append(callback)
    
    @property
    def is_switching(self) -> bool:
        """Проверяет, идёт ли переключение движка."""
        return self._switching.is_set()
    
    @contextmanager
    def switch_engine(self):
        """
        Context manager для безопасного переключения движка.
        Предотвращает одновременное переключение из нескольких потоков.
        """
        if self._switching.is_set():
            raise RuntimeError("Переключение движка уже выполняется")
        
        self._switching.set()
        old_state = self.state
        self.state = EngineState.SWITCHING
        
        try:
            with self._lock:
                yield
        finally:
            self._switching.clear()
            # Восстанавливаем состояние если переключение не завершилось нормально
            if self.state == EngineState.SWITCHING:
                self.state = old_state
    
    def wait_for_switch(self, timeout: float = 10.0) -> bool:
        """Ожидает завершения переключения движка."""
        start = time.time()
        while self._switching.is_set():
            if time.time() - start > timeout:
                return False
            time.sleep(0.1)
        return True


class StoppableThread(threading.Thread):
    """Поток с возможностью корректной остановки."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.daemon = True
    
    def stop(self) -> None:
        """Запрашивает остановку потока."""
        self._stop_event.set()
    
    def stopped(self) -> bool:
        """Проверяет, запрошена ли остановка."""
        return self._stop_event.is_set()
    
    def wait_stop(self, timeout: Optional[float] = None) -> bool:
        """Ожидает события остановки."""
        return self._stop_event.wait(timeout)


class AtomicCounter:
    """Thread-safe счётчик."""
    
    def __init__(self, initial: int = 0):
        self._value = initial
        self._lock = threading.Lock()
    
    def increment(self, delta: int = 1) -> int:
        """Увеличивает счётчик и возвращает новое значение."""
        with self._lock:
            self._value += delta
            return self._value
    
    def decrement(self, delta: int = 1) -> int:
        """Уменьшает счётчик и возвращает новое значение."""
        return self.increment(-delta)
    
    @property
    def value(self) -> int:
        """Текущее значение счётчика."""
        with self._lock:
            return self._value
    
    def reset(self, value: int = 0) -> None:
        """Сбрасывает счётчик."""
        with self._lock:
            self._value = value
```

---

## File: `audio/__init__.py`

```python
"""Audio package - захват и обработка аудио."""
from .capture import AudioCapture, AudioDevice

__all__ = ['AudioCapture', 'AudioDevice']
```

---

## File: `audio/capture.py`

```python
"""
Модуль захвата аудио с использованием PyAudio.
Включает управление устройствами и thread-safe буферизацию.
"""

import pyaudio
import numpy as np
import threading
import logging
from typing import Optional, List, Callable
from dataclasses import dataclass
from contextlib import contextmanager

from utils.threading_utils import ThreadSafeQueue, StoppableThread

logger = logging.getLogger("voice_translator.audio")


@dataclass
class AudioDevice:
    """Информация об аудиоустройстве."""
    index: int
    name: str
    channels: int
    sample_rate: int
    is_input: bool
    
    def __str__(self) -> str:
        return f"{self.name} (ch: {self.channels})"


class AudioCapture:
    """
    Менеджер захвата аудио с PyAudio.
    Поддерживает context manager для автоматической очистки ресурсов.
    """
    
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    DEFAULT_RATE = 16000
    CHUNK_SIZE = 512
    
    def __init__(
        self,
        sample_rate: int = DEFAULT_RATE,
        chunk_size: int = CHUNK_SIZE,
        device_index: Optional[int] = None
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.device_index = device_index
        
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._audio_queue: ThreadSafeQueue[bytes] = ThreadSafeQueue(maxsize=100)
        self._capture_thread: Optional[StoppableThread] = None
        self._is_capturing = False
        self._lock = threading.Lock()

        # Callbacks
        self._level_callback: Optional[Callable[[float], None]] = None

        # Сглаживание уровня для предотвращения мерцания UI
        self._smoothed_level: float = 0.0
        self._smoothing_factor: float = 0.3  # 0.0-1.0, меньше = плавнее
        
    def __enter__(self) -> "AudioCapture":
        """Инициализирует PyAudio при входе в context."""
        self._pyaudio = pyaudio.PyAudio()
        logger.info("PyAudio инициализирован")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Освобождает ресурсы при выходе из context."""
        self.stop_capture()
        
        if self._stream:
            try:
                self._stream.close()
            except Exception as e:
                logger.warning(f"Ошибка закрытия потока: {e}")
            self._stream = None
            
        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception as e:
                logger.warning(f"Ошибка завершения PyAudio: {e}")
            self._pyaudio = None
            
        logger.info("PyAudio ресурсы освобождены")
    
    def get_input_devices(self) -> List[AudioDevice]:
        """Возвращает список доступных входных устройств."""
        if not self._pyaudio:
            raise RuntimeError("AudioCapture не инициализирован. Используйте context manager.")
        
        devices = []
        for i in range(self._pyaudio.get_device_count()):
            try:
                info = self._pyaudio.get_device_info_by_index(i)
                if info.get('maxInputChannels', 0) > 0:
                    devices.append(AudioDevice(
                        index=i,
                        name=info.get('name', f'Device {i}'),
                        channels=int(info.get('maxInputChannels', 1)),
                        sample_rate=int(info.get('defaultSampleRate', self.DEFAULT_RATE)),
                        is_input=True
                    ))
            except Exception as e:
                logger.debug(f"Пропуск устройства {i}: {e}")
                
        logger.info(f"Найдено {len(devices)} входных устройств")
        return devices
    
    def get_default_input_device(self) -> Optional[AudioDevice]:
        """Возвращает устройство ввода по умолчанию."""
        if not self._pyaudio:
            raise RuntimeError("AudioCapture не инициализирован")
            
        try:
            info = self._pyaudio.get_default_input_device_info()
            return AudioDevice(
                index=int(info['index']),
                name=info.get('name', 'Default'),
                channels=int(info.get('maxInputChannels', 1)),
                sample_rate=int(info.get('defaultSampleRate', self.DEFAULT_RATE)),
                is_input=True
            )
        except IOError as e:
            logger.error(f"Не удалось получить устройство по умолчанию: {e}")
            return None
    
    def set_device(self, device_index: int) -> bool:
        """Устанавливает устройство захвата."""
        with self._lock:
            if self._is_capturing:
                logger.warning("Нельзя сменить устройство во время записи")
                return False
            self.device_index = device_index
            logger.info(f"Установлено устройство: {device_index}")
            return True
    
    def set_level_callback(self, callback: Optional[Callable[[float], None]]) -> None:
        """Устанавливает callback для уровня громкости (0.0-1.0)."""
        self._level_callback = callback
    
    def start_capture(self) -> bool:
        """Начинает захват аудио в фоновом потоке."""
        with self._lock:
            if self._is_capturing:
                logger.warning("Захват уже запущен")
                return False
            
            if not self._pyaudio:
                raise RuntimeError("AudioCapture не инициализирован")
            
            candidates: List[Optional[int]] = []
            if self.device_index is not None:
                candidates.append(self.device_index)

            default_device = self.get_default_input_device()
            if default_device and default_device.index not in candidates:
                candidates.append(default_device.index)

            # Последняя попытка: пусть PortAudio выберет устройство по умолчанию.
            if None not in candidates:
                candidates.append(None)

            last_error: Optional[Exception] = None
            for device_idx in candidates:
                try:
                    self._stream = self._pyaudio.open(
                        format=self.FORMAT,
                        channels=self.CHANNELS,
                        rate=self.sample_rate,
                        input=True,
                        input_device_index=device_idx,
                        frames_per_buffer=self.chunk_size,
                    )

                    if device_idx is not None and self.device_index != device_idx:
                        logger.warning(
                            f"Сохранённое устройство недоступно, переключаемся на device={device_idx}"
                        )
                        self.device_index = device_idx

                    # Очищаем очередь
                    self._audio_queue.clear()

                    # Запускаем поток захвата
                    self._capture_thread = StoppableThread(
                        target=self._capture_loop,
                        name="AudioCaptureThread"
                    )
                    self._is_capturing = True
                    self._capture_thread.start()

                    logger.info(f"Захват аудио начат (device={device_idx}, rate={self.sample_rate})")
                    return True
                except Exception as e:
                    last_error = e
                    logger.warning(f"Не удалось открыть устройство {device_idx}: {e}")
                    if self._stream:
                        try:
                            self._stream.close()
                        except Exception:
                            pass
                        self._stream = None

            logger.error(f"Ошибка запуска захвата: {last_error}")
            self._is_capturing = False
            return False
    
    def stop_capture(self) -> None:
        """Останавливает захват аудио."""
        with self._lock:
            if not self._is_capturing:
                return
            
            self._is_capturing = False
            
            if self._capture_thread:
                self._capture_thread.stop()
                self._capture_thread.join(timeout=2.0)
                self._capture_thread = None
            
            if self._stream:
                try:
                    self._stream.stop_stream()
                    self._stream.close()
                except Exception as e:
                    logger.warning(f"Ошибка остановки потока: {e}")
                self._stream = None
            
            logger.info("Захват аудио остановлен")
    
    def _capture_loop(self) -> None:
        """Основной цикл захвата аудио."""
        while self._is_capturing and self._capture_thread and not self._capture_thread.stopped():
            try:
                if self._stream and self._stream.is_active():
                    data = self._stream.read(self.chunk_size, exception_on_overflow=False)

                    # Вычисляем уровень громкости со сглаживанием
                    if self._level_callback:
                        audio_array = np.frombuffer(data, dtype=np.int16)
                        raw_level = np.abs(audio_array).mean() / 32768.0
                        raw_level = min(1.0, raw_level * 3)  # Усиливаем для визуализации

                        # Экспоненциальное сглаживание (EMA)
                        self._smoothed_level = (
                            self._smoothing_factor * raw_level +
                            (1 - self._smoothing_factor) * self._smoothed_level
                        )
                        self._level_callback(self._smoothed_level)

                    # Добавляем в очередь
                    try:
                        self._audio_queue.put(data, block=False)
                    except Exception:
                        pass  # Очередь переполнена, пропускаем chunk

            except IOError as e:
                if "Input overflowed" in str(e):
                    logger.debug("Audio buffer overflow, пропускаем")
                else:
                    logger.error(f"Ошибка чтения аудио: {e}")
                    break
            except Exception as e:
                logger.error(f"Неожиданная ошибка в capture loop: {e}")
                break
    
    def get_audio_chunk(self, timeout: float = 0.1) -> Optional[bytes]:
        """Получает chunk аудио из очереди."""
        return self._audio_queue.get(timeout=timeout)
    
    def get_audio_data(self, duration: float) -> Optional[bytes]:
        """
        Собирает аудиоданные за указанную длительность (в секундах).
        """
        chunks_needed = int(duration * self.sample_rate / self.chunk_size)
        chunks = []
        
        for _ in range(chunks_needed):
            chunk = self.get_audio_chunk(timeout=0.5)
            if chunk:
                chunks.append(chunk)
        
        if chunks:
            return b''.join(chunks)
        return None
    
    @property
    def is_capturing(self) -> bool:
        """Проверяет, идёт ли захват."""
        return self._is_capturing
    
    def audio_to_numpy(self, data: bytes) -> np.ndarray:
        """Конвертирует bytes в numpy array для Whisper."""
        audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        return audio_array / 32768.0  # Нормализация [-1, 1]
```

---

## File: `recognition/__init__.py`

```python
"""Recognition package - движки распознавания речи."""

import logging
from typing import Callable, Optional

from .base import BaseRecognizer
from .vosk_engine import VoskRecognizer, VOSK_AVAILABLE
from .whisper_engine import WhisperRecognizer, WHISPER_AVAILABLE, HallucinationFilter
from .faster_whisper_engine import FasterWhisperRecognizer, FASTER_WHISPER_AVAILABLE
from .whispercpp_engine import WhisperCppRecognizer, WHISPER_CPP_AVAILABLE
from utils.config import AppConfig, RecognitionConfig

logger = logging.getLogger("voice_translator.recognition")

def create_recognizer(config: AppConfig, rec_config: RecognitionConfig) -> Optional[BaseRecognizer]:
    """
    Creates and loads the requested recognizer, falling back to CPU engines and Vosk.

    Fallback order after the requested engine fails:
    faster-whisper (CPU) -> openai-whisper (CPU) -> Vosk.
    whisper_cpp uses pywhispercpp when available; otherwise it falls back to CPU.
    """
    attempted: set[str] = set()

    for label, factory in _recognizer_candidates(config, rec_config):
        if label in attempted:
            continue
        attempted.add(label)

        recognizer = _build_recognizer(label, factory)
        if recognizer is None:
            continue

        try:
            if recognizer.load():
                if label != _requested_label(config):
                    logger.warning("Fallback recognizer selected: %s", label)
                return recognizer
            logger.warning("Recognizer failed to load: %s", label)
            recognizer.unload()
        except Exception as e:
            logger.warning("Recognizer %s failed, trying fallback: %s", label, e)
            try:
                recognizer.unload()
            except Exception:
                pass

    logger.error("No recognition engine could be loaded")
    return None


def _recognizer_candidates(
    config: AppConfig,
    rec_config: RecognitionConfig,
) -> list[tuple[str, Callable[[], BaseRecognizer]]]:
    requested = _requested_candidates(config, rec_config)
    fallbacks = [
        _faster_whisper_candidate(config, rec_config),
        _whisper_candidate(config, rec_config),
        _vosk_candidate(config, rec_config),
    ]
    return requested + fallbacks


def _requested_candidates(
    config: AppConfig,
    rec_config: RecognitionConfig,
) -> list[tuple[str, Callable[[], BaseRecognizer]]]:
    if config.engine == "vosk":
        return [_vosk_candidate(config, rec_config)]

    if config.engine != "whisper":
        logger.warning("Unknown recognition engine '%s', using fallback chain", config.engine)
        return []

    if config.whisper_backend == "faster":
        return [_faster_whisper_candidate(config, rec_config)]
    if config.whisper_backend == "openai":
        return [_whisper_candidate(config, rec_config)]
    if config.whisper_backend == "whisper_cpp":
        return [_whisper_cpp_candidate(config, rec_config)]

    logger.warning("Unknown Whisper backend '%s', using fallback chain", config.whisper_backend)
    return []


def _requested_label(config: AppConfig) -> str:
    if config.engine == "vosk":
        return "vosk"
    if config.engine == "whisper":
        if config.whisper_backend == "faster":
            return "faster-whisper (CPU)"
        if config.whisper_backend == "openai":
            return "whisper (CPU)"
        if config.whisper_backend == "whisper_cpp":
            return "whisper.cpp"
    return "unknown"


def _faster_whisper_candidate(
    config: AppConfig,
    rec_config: RecognitionConfig,
) -> tuple[str, Callable[[], BaseRecognizer]]:
    return (
        "faster-whisper (CPU)",
        lambda: FasterWhisperRecognizer(
            rec_config,
            model_name=config.whisper_model,
            cache_dir=config.faster_whisper_cache_dir,
            compute_type=config.whisper_compute_type,
        ),
    )


def _whisper_cpp_candidate(
    config: AppConfig,
    rec_config: RecognitionConfig,
) -> tuple[str, Callable[[], BaseRecognizer]]:
    return (
        "whisper.cpp",
        lambda: WhisperCppRecognizer(
            rec_config,
            model_name=config.whisper_model,
            model_dir=config.whisper_cpp_model_dir,
            use_gpu=config.whisper_cpp_use_gpu,
            language=config.whisper_language,
        ),
    )


def _whisper_candidate(
    config: AppConfig,
    rec_config: RecognitionConfig,
) -> tuple[str, Callable[[], BaseRecognizer]]:
    return (
        "whisper (CPU)",
        lambda: WhisperRecognizer(
            rec_config,
            model_name=config.whisper_model,
            cache_dir=config.whisper_cache_dir,
        ),
    )


def _vosk_candidate(
    config: AppConfig,
    rec_config: RecognitionConfig,
) -> tuple[str, Callable[[], BaseRecognizer]]:
    model_path = config.vosk_large_model_path if config.vosk_model_size == "large" else config.vosk_model_path
    return (
        "vosk",
        lambda: VoskRecognizer(
            rec_config,
            model_path=model_path,
            phrase_timeout=config.vosk_phrase_timeout,
        ),
    )


def _build_recognizer(
    label: str,
    factory: Callable[[], BaseRecognizer],
) -> Optional[BaseRecognizer]:
    if label == "faster-whisper (CPU)" and not FASTER_WHISPER_AVAILABLE:
        logger.warning("faster-whisper is unavailable, trying fallback")
        return None
    if label == "whisper (CPU)" and not WHISPER_AVAILABLE:
        logger.warning("openai-whisper is unavailable, trying fallback")
        return None
    if label == "vosk" and not VOSK_AVAILABLE:
        logger.warning("Vosk is unavailable")
        return None
    if label == "whisper.cpp" and not WHISPER_CPP_AVAILABLE:
        logger.warning("pywhispercpp is unavailable, trying CPU fallback")
        return None

    try:
        return factory()
    except Exception as e:
        logger.warning("Could not create recognizer %s: %s", label, e)
        return None

__all__ = [
    'BaseRecognizer',
    'VoskRecognizer',
    'VOSK_AVAILABLE',
    'WhisperRecognizer',
    'WHISPER_AVAILABLE',
    'FasterWhisperRecognizer',
    'FASTER_WHISPER_AVAILABLE',
    'WhisperCppRecognizer',
    'WHISPER_CPP_AVAILABLE',
    'HallucinationFilter',
    'create_recognizer',
]
```

---

## File: `recognition/base.py`

```python
"""
Базовый интерфейс для движков распознавания речи.
"""

from abc import ABC, abstractmethod
from typing import Optional, Generator
from dataclasses import dataclass
import numpy as np

from utils.threading_utils import RecognitionResult
from utils.config import RecognitionConfig


class BaseRecognizer(ABC):
    """Абстрактный базовый класс для движков распознавания."""
    
    def __init__(self, config: RecognitionConfig):
        self.config = config
        self._is_loaded = False
        self._model_name = "unknown"
    
    @property
    def name(self) -> str:
        """Имя движка."""
        return self.__class__.__name__.replace("Recognizer", "").replace("Engine", "")
    
    @property
    def is_loaded(self) -> bool:
        """Проверяет, загружена ли модель."""
        return self._is_loaded
    
    @abstractmethod
    def load(self) -> bool:
        """
        Загружает модель.
        Должен быть вызван перед использованием.
        Возвращает True при успехе.
        """
        pass
    
    @abstractmethod
    def unload(self) -> None:
        """Выгружает модель и освобождает ресурсы."""
        pass
    
    @abstractmethod
    def recognize(self, audio_data: bytes) -> Optional[RecognitionResult]:
        """
        Распознаёт речь в аудиоданных.
        
        Args:
            audio_data: Аудио в формате PCM16, mono, 16kHz
            
        Returns:
            RecognitionResult или None если нет распознанного текста
        """
        pass
    
    @abstractmethod
    def recognize_stream(self, audio_chunk: bytes) -> Generator[RecognitionResult, None, None]:
        """
        Потоковое распознавание для real-time обработки.
        
        Args:
            audio_chunk: Один chunk аудиоданных
            
        Yields:
            RecognitionResult с partial=True для промежуточных результатов
        """
        pass
    
    def reset(self) -> None:
        """Сбрасывает внутреннее состояние (для потокового распознавания)."""
        pass
    
    def __enter__(self):
        self.load()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unload()
```

---

## File: `recognition/faster_whisper_engine.py`

```python
"""
CPU-only faster-whisper recognizer.
"""

import importlib.util
import logging
from pathlib import Path
from typing import Generator, Optional

import numpy as np

from .base import BaseRecognizer
from .whisper_engine import HallucinationFilter
from utils.threading_utils import RecognitionResult
from utils.config import RecognitionConfig

logger = logging.getLogger("voice_translator.recognition.faster_whisper")

FASTER_WHISPER_AVAILABLE = importlib.util.find_spec("faster_whisper") is not None


class FasterWhisperRecognizer(BaseRecognizer):
    """faster-whisper recognizer forced to CPU int8 by default."""

    def __init__(
        self,
        config: RecognitionConfig,
        model_name: str = "small",
        cache_dir: str = "models/faster-whisper",
        compute_type: str = "int8",
    ):
        super().__init__(config)
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self.compute_type = compute_type
        self._model = None
        self._buffer = bytearray()
        self._filter = HallucinationFilter()
        self._model_name = f"faster-whisper {model_name} CPU"

    def load(self) -> bool:
        """Loads faster-whisper on CPU only."""
        if not FASTER_WHISPER_AVAILABLE:
            logger.error("faster-whisper недоступен. Используйте: pip install faster-whisper")
            return False

        if self._is_loaded:
            logger.debug("faster-whisper модель уже загружена")
            return True

        try:
            from faster_whisper import WhisperModel

            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(
                "Загрузка faster-whisper CPU модели: %s, compute_type=%s",
                self.model_name,
                self.compute_type,
            )
            self._model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type=self.compute_type,
                download_root=str(self.cache_dir),
            )
            self._is_loaded = True
            logger.info("faster-whisper CPU модель загружена успешно")
            return True
        except Exception as e:
            logger.error("Ошибка загрузки faster-whisper CPU: %s", e)
            self._model = None
            self._is_loaded = False
            return False

    def unload(self) -> None:
        """Unloads the model and clears buffered audio."""
        self._model = None
        self._buffer.clear()
        self._is_loaded = False
        logger.info("faster-whisper CPU модель выгружена")

    def recognize(self, audio_data: bytes) -> Optional[RecognitionResult]:
        """Transcribes a PCM16 mono 16 kHz chunk."""
        if not self._is_loaded or self._model is None:
            logger.error("faster-whisper CPU не загружен")
            return None

        audio_f32 = self._pcm16_to_float32(audio_data)
        if audio_f32.size == 0:
            return None

        try:
            segments, _info = self._model.transcribe(
                audio_f32,
                language=self._language,
                vad_filter=True,
            )
            text = self._filter.clean(" ".join(segment.text.strip() for segment in segments))
            if not text:
                return None

            return RecognitionResult(
                text=text,
                is_final=True,
                confidence=0.0,
                engine="faster-whisper (CPU)",
            )
        except Exception as e:
            logger.error("Ошибка распознавания faster-whisper CPU: %s", e)
            return None

    def recognize_stream(self, audio_chunk: bytes) -> Generator[RecognitionResult, None, None]:
        """Buffers live audio and transcribes complete chunk-duration windows."""
        if not self._is_loaded or self._model is None:
            logger.error("faster-whisper CPU не загружен")
            return

        self._buffer.extend(audio_chunk)
        target_bytes = int(self.config.sample_rate * self.config.chunk_duration * 2)
        if len(self._buffer) < target_bytes:
            return

        chunk = bytes(self._buffer[:target_bytes])
        del self._buffer[:target_bytes]

        if self._is_silence(chunk):
            return

        result = self.recognize(chunk)
        if result:
            yield result

    def reset(self) -> None:
        """Clears buffered stream audio."""
        self._buffer.clear()

    @property
    def _language(self) -> str:
        return str(getattr(self.config, "whisper_language", "ru") or "ru")

    def _is_silence(self, audio_data: bytes) -> bool:
        samples = np.frombuffer(audio_data, np.int16).astype(np.int32)
        if samples.size == 0:
            return True
        return float(np.max(np.abs(samples))) < float(self.config.vad_threshold)

    @staticmethod
    def _pcm16_to_float32(audio_data: bytes) -> np.ndarray:
        return np.frombuffer(audio_data, np.int16).astype(np.float32) / 32768.0
```

---

## File: `recognition/vosk_engine.py`

```python
"""
Vosk движок для быстрого real-time распознавания русской речи.
С улучшенным накоплением фраз для предотвращения обрезки предложений.
"""

import json
import logging
import time
from typing import Optional, Generator, List
from pathlib import Path

from .base import BaseRecognizer
from utils.threading_utils import RecognitionResult
from utils.config import RecognitionConfig

logger = logging.getLogger("voice_translator.recognition.vosk")

# Импортируем vosk с обработкой ошибки
try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logger.warning("Vosk не установлен. Используйте: pip install vosk")


class VoskRecognizer(BaseRecognizer):
    """
    Vosk-based распознаватель для быстрого real-time распознавания.
    Низкая латентность, работает офлайн.

    Включает накопление фраз для предотвращения преждевременной обрезки предложений.
    """

    # URL для скачивания моделей
    MODEL_URL_SMALL = "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip"
    MODEL_URL_LARGE = "https://alphacephei.com/vosk/models/vosk-model-ru-0.22.zip"
    MODEL_NAME_SMALL = "vosk-model-ru-0.42"
    MODEL_NAME_LARGE = "vosk-model-ru-0.22"

    # Для обратной совместимости
    MODEL_URL = MODEL_URL_SMALL
    MODEL_NAME = MODEL_NAME_SMALL

    # Параметры накопления фраз
    DEFAULT_PHRASE_TIMEOUT = 1.5  # Секунды тишины до финализации
    MIN_PHRASE_WORDS = 2  # Минимум слов для отдельной фразы

    def __init__(self, config: RecognitionConfig, model_path: str = "models/vosk-model-ru",
                 phrase_timeout: float = DEFAULT_PHRASE_TIMEOUT):
        super().__init__(config)
        self.model_path = Path(model_path)
        self.phrase_timeout = phrase_timeout
        self._model = None
        self._recognizer = None
        self._model_name = "Vosk Russian"

        # Буфер для накопления фраз
        self._phrase_buffer: List[str] = []
        self._last_speech_time: float = 0.0
        self._pending_final: Optional[str] = None

        # Кэш для partial JSON чтобы избежать повторного парсинга
        self._cached_partial_json: Optional[str] = None
        self._cached_partial_text: str = ""
        # Максимальный размер буфера фраз для предотвращения утечки памяти
        self._max_phrase_buffer: int = 50
    
    def load(self) -> bool:
        """Загружает Vosk модель."""
        if not VOSK_AVAILABLE:
            logger.error("Vosk библиотека недоступна")
            return False
        
        if self._is_loaded:
            logger.debug("Vosk модель уже загружена")
            return True
        
        # Отключаем логи Vosk
        SetLogLevel(-1)
        
        # Проверяем наличие модели
        if not self.model_path.exists():
            logger.error(f"Модель Vosk не найдена: {self.model_path}")
            logger.info(f"Скачайте модель: {self.MODEL_URL}")
            logger.info(f"Распакуйте в: {self.model_path}")
            return False
        
        try:
            logger.info(f"Загрузка Vosk модели: {self.model_path}")
            self._model = Model(str(self.model_path))
            self._recognizer = KaldiRecognizer(self._model, self.config.sample_rate)
            self._recognizer.SetWords(True)
            self._is_loaded = True
            logger.info("Vosk модель загружена успешно")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка загрузки Vosk: {e}")
            self._model = None
            self._recognizer = None
            return False
    
    def unload(self) -> None:
        """Выгружает Vosk модель."""
        self._recognizer = None
        self._model = None
        self._is_loaded = False
        logger.info("Vosk модель выгружена")
    
    def recognize(self, audio_data: bytes) -> Optional[RecognitionResult]:
        """
        Распознаёт речь в аудиоданных (batch mode).
        """
        if not self._is_loaded or not self._recognizer:
            logger.error("Vosk не загружен")
            return None
        
        try:
            # Передаём все данные
            self._recognizer.AcceptWaveform(audio_data)
            
            # Получаем финальный результат
            result_json = self._recognizer.FinalResult()
            result = json.loads(result_json)
            
            text = result.get("text", "").strip()
            if text:
                return RecognitionResult(
                    text=text,
                    is_final=True,
                    confidence=self._calculate_confidence(result),
                    engine="vosk"
                )
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга Vosk результата: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка распознавания Vosk: {e}")
            return None
    
    def recognize_stream(self, audio_chunk: bytes) -> Generator[RecognitionResult, None, None]:
        """
        Потоковое распознавание для real-time обработки.
        С накоплением фраз для предотвращения преждевременной обрезки.
        """
        if not self._is_loaded or not self._recognizer:
            logger.error("Vosk не загружен")
            return

        current_time = time.time()

        try:
            if self._recognizer.AcceptWaveform(audio_chunk):
                # Vosk считает фразу законченной
                result_json = self._recognizer.Result()
                result = json.loads(result_json)

                text = result.get("text", "").strip()
                if text:
                    # Добавляем в буфер вместо немедленной отправки
                    self._phrase_buffer.append(text)
                    self._last_speech_time = current_time
                    self._pending_final = result  # Сохраняем для confidence
                    logger.debug(f"Vosk фраза в буфер: '{text}' (всего: {len(self._phrase_buffer)})")

            else:
                # Частичный результат - речь продолжается
                partial_json = self._recognizer.PartialResult()
                # Кэшируем partial JSON чтобы избежать повторного парсинга
                if partial_json == self._cached_partial_json:
                    text = self._cached_partial_text
                else:
                    partial = json.loads(partial_json)
                    text = partial.get("partial", "").strip()
                    self._cached_partial_json = partial_json
                    self._cached_partial_text = text

                if text:
                    self._last_speech_time = current_time
                    # Показываем накопленное + текущее как partial
                    full_partial = self._get_accumulated_text(text)
                    yield RecognitionResult(
                        text=full_partial,
                        is_final=False,
                        confidence=0.0,
                        engine="vosk"
                    )

            # Проверяем timeout для финализации накопленной фразы
            if self._phrase_buffer and self._last_speech_time > 0:
                silence_duration = current_time - self._last_speech_time
                if silence_duration >= self.phrase_timeout:
                    # Достаточно тишины - финализируем накопленную фразу
                    accumulated = self._finalize_accumulated()
                    if accumulated:
                        yield accumulated

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга Vosk: {e}")
        except Exception as e:
            logger.error(f"Ошибка потокового распознавания: {e}")

    def _get_accumulated_text(self, current_partial: str = "") -> str:
        """Возвращает накопленный текст + текущий partial."""
        # Ограничиваем буфер фраз чтобы избежать бесконечного роста
        if len(self._phrase_buffer) > self._max_phrase_buffer:
            # Удаляем старые фразы с запасом
            self._phrase_buffer = self._phrase_buffer[-self._max_phrase_buffer + 10:]
        parts = self._phrase_buffer.copy()
        if current_partial:
            parts.append(current_partial)
        return " ".join(parts)

    def _finalize_accumulated(self) -> Optional[RecognitionResult]:
        """Финализирует накопленную фразу и очищает буфер."""
        if not self._phrase_buffer:
            return None

        accumulated_text = " ".join(self._phrase_buffer)
        self._phrase_buffer.clear()
        self._last_speech_time = 0.0

        # Вычисляем confidence
        confidence = 0.5
        if self._pending_final:
            confidence = self._calculate_confidence(self._pending_final)
        self._pending_final = None

        logger.debug(f"Vosk финализация: '{accumulated_text}'")

        return RecognitionResult(
            text=accumulated_text,
            is_final=True,
            confidence=confidence,
            engine="vosk"
        )
    
    def reset(self) -> None:
        """Сбрасывает состояние recognizer для новой сессии."""
        if self._recognizer and self._model:
            self._recognizer = KaldiRecognizer(self._model, self.config.sample_rate)
            self._recognizer.SetWords(True)

        # Очищаем буфер фраз и кэш partial
        self._phrase_buffer.clear()
        self._last_speech_time = 0.0
        self._pending_final = None
        self._cached_partial_json = None
        self._cached_partial_text = ""
        logger.debug("Vosk recognizer сброшен")
    
    def _calculate_confidence(self, result: dict) -> float:
        """Вычисляет средний confidence из результатов по словам."""
        words = result.get("result", [])
        if not words:
            return 0.5  # Default confidence
        
        confidences = [w.get("conf", 0.5) for w in words]
        return sum(confidences) / len(confidences)
```

---

## File: `recognition/whisper_engine.py`

```python
"""
CPU-only openai-whisper recognizer.
"""

import importlib.util
import logging
import re
from pathlib import Path
from typing import Generator, Optional

import numpy as np

from .base import BaseRecognizer
from utils.threading_utils import RecognitionResult
from utils.config import RecognitionConfig

logger = logging.getLogger("voice_translator.recognition.whisper")

WHISPER_AVAILABLE = importlib.util.find_spec("whisper") is not None


class HallucinationFilter:
    """Lightweight filter for common Whisper filler/hallucination outputs."""

    _KNOWN_PHRASES = {
        "редактор субтитров",
        "субтитры создавал",
        "субтитры сделал",
        "спасибо за просмотр",
        "продолжение следует",
    }
    _FILLER_WORDS = {"а", "ага", "да", "угу", "мм", "м", "эм", "ээ", "ну"}

    def is_hallucination(self, text: str) -> bool:
        normalized = self._normalize(text)
        if not normalized:
            return True

        if normalized in self._KNOWN_PHRASES:
            return True

        words = normalized.split()
        if len(words) >= 5 and len(set(words)) == 1:
            return True

        return bool(words) and all(word in self._FILLER_WORDS for word in words)

    def clean(self, text: str) -> str:
        text = text.strip()
        if self.is_hallucination(text):
            return ""
        return text

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.strip().lower().replace("ё", "е")
        text = re.sub(r"[^\w\s]+", " ", text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", text).strip()


class WhisperRecognizer(BaseRecognizer):
    """openai-whisper recognizer forced to CPU."""

    def __init__(
        self,
        config: RecognitionConfig,
        model_name: str = "small",
        cache_dir: str = "models/whisper",
    ):
        super().__init__(config)
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self._model = None
        self._buffer = bytearray()
        self._filter = HallucinationFilter()
        self._model_name = f"Whisper {model_name} CPU"

    def load(self) -> bool:
        """Loads openai-whisper on CPU only."""
        if not WHISPER_AVAILABLE:
            logger.error("openai-whisper недоступен. Используйте: pip install openai-whisper")
            return False

        if self._is_loaded:
            logger.debug("Whisper модель уже загружена")
            return True

        try:
            import whisper

            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Загрузка Whisper CPU модели: %s", self.model_name)
            self._model = whisper.load_model(
                self.model_name,
                device="cpu",
                download_root=str(self.cache_dir),
            )
            self._is_loaded = True
            logger.info("Whisper CPU модель загружена успешно")
            return True
        except Exception as e:
            logger.error("Ошибка загрузки Whisper CPU: %s", e)
            self._model = None
            self._is_loaded = False
            return False

    def unload(self) -> None:
        """Unloads the model and clears buffered audio."""
        self._model = None
        self._buffer.clear()
        self._is_loaded = False
        logger.info("Whisper CPU модель выгружена")

    def recognize(self, audio_data: bytes) -> Optional[RecognitionResult]:
        """Transcribes a PCM16 mono 16 kHz chunk."""
        if not self._is_loaded or self._model is None:
            logger.error("Whisper CPU не загружен")
            return None

        audio_f32 = self._pcm16_to_float32(audio_data)
        if audio_f32.size == 0:
            return None

        try:
            result = self._model.transcribe(
                audio_f32,
                language=self._language,
                fp16=False,
            )
            text = self._filter.clean(result.get("text", ""))
            if not text:
                return None

            return RecognitionResult(
                text=text,
                is_final=True,
                confidence=0.0,
                engine="whisper (CPU)",
            )
        except Exception as e:
            logger.error("Ошибка распознавания Whisper CPU: %s", e)
            return None

    def recognize_stream(self, audio_chunk: bytes) -> Generator[RecognitionResult, None, None]:
        """Buffers live audio and transcribes complete chunk-duration windows."""
        if not self._is_loaded or self._model is None:
            logger.error("Whisper CPU не загружен")
            return

        self._buffer.extend(audio_chunk)
        target_bytes = int(self.config.sample_rate * self.config.chunk_duration * 2)
        if len(self._buffer) < target_bytes:
            return

        chunk = bytes(self._buffer[:target_bytes])
        del self._buffer[:target_bytes]

        if self._is_silence(chunk):
            return

        result = self.recognize(chunk)
        if result:
            yield result

    def reset(self) -> None:
        """Clears buffered stream audio."""
        self._buffer.clear()

    @property
    def _language(self) -> str:
        return str(getattr(self.config, "whisper_language", "ru") or "ru")

    def _is_silence(self, audio_data: bytes) -> bool:
        samples = np.frombuffer(audio_data, np.int16).astype(np.int32)
        if samples.size == 0:
            return True
        return float(np.max(np.abs(samples))) < float(self.config.vad_threshold)

    @staticmethod
    def _pcm16_to_float32(audio_data: bytes) -> np.ndarray:
        return np.frombuffer(audio_data, np.int16).astype(np.float32) / 32768.0
```

---

## File: `recognition/whispercpp_engine.py`

```python
"""
Optional whisper.cpp recognizer using pywhispercpp.

This is the only planned GPU path for the target Intel macOS + AMD RX 580
machine. GPU use is reported only when runtime initialization output confirms
Metal and the expected AMD device.
"""

import importlib.util
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Generator, Optional

import numpy as np

from .base import BaseRecognizer
from .whisper_engine import HallucinationFilter
from utils.config import RecognitionConfig
from utils.threading_utils import RecognitionResult

logger = logging.getLogger("voice_translator.recognition.whispercpp")

try:
    if importlib.util.find_spec("pywhispercpp") is None:
        raise ImportError("pywhispercpp is not installed")
    from pywhispercpp.model import Model as WhisperCppModel
except Exception as e:
    WhisperCppModel = None
    WHISPER_CPP_AVAILABLE = False
    WHISPER_CPP_IMPORT_ERROR = e
else:
    WHISPER_CPP_AVAILABLE = True
    WHISPER_CPP_IMPORT_ERROR = None


class WhisperCppRecognizer(BaseRecognizer):
    """whisper.cpp recognizer with Metal verification and CPU fallback."""

    METAL_MARKERS = ("ggml_metal", "metal")
    AMD_DEVICE_MARKERS = ("AMD Radeon RX 580", "Radeon RX 580", "RX 580")
    ENGLISH_FILLER_WORDS = {
        "the",
        "you",
        "yeah",
        "yes",
        "no",
        "ok",
        "okay",
        "uh",
        "um",
        "hmm",
        "music",
        "blurgy",
        "blurry",
    }
    ENGLISH_FILLER_PHRASES = {
        "thank you",
        "thanks",
        "thanks for watching",
        "subscribe",
    }
    RUSSIAN_NOISE_PHRASES = {
        "смотрите на видео",
        "спокойная музыка",
        "музыка",
        "смех",
        "смешка",
        "аплодисменты",
        "субтитры",
    }
    NON_RUSSIAN_SCRIPT_RE = re.compile(
        r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]"
    )

    def __init__(
        self,
        config: RecognitionConfig,
        model_name: str = "small",
        model_dir: str = "models/whisper-cpp",
        use_gpu: bool = True,
        language: str = "ru",
    ):
        super().__init__(config)
        self.model_name = model_name
        self.model_dir = Path(model_dir)
        self.use_gpu = bool(use_gpu)
        self.language = language or "ru"
        self.gpu_active = False
        self.init_log = ""
        self._model = None
        self._buffer = bytearray()
        self._filter = HallucinationFilter()
        self._model_name = f"whisper.cpp {model_name}"

    def load(self) -> bool:
        """Loads pywhispercpp and records whether Metal/RX 580 initialized."""
        if not WHISPER_CPP_AVAILABLE:
            logger.error(
                "pywhispercpp недоступен. Соберите/установите pywhispercpp с Metal: %s",
                WHISPER_CPP_IMPORT_ERROR,
            )
            return False

        if self._is_loaded:
            logger.debug("whisper.cpp модель уже загружена")
            return True

        log_path = self._init_log_path()
        try:
            self.model_dir.mkdir(parents=True, exist_ok=True)
            self._model = self._create_model(use_gpu=self.use_gpu, log_path=log_path)

            self.init_log = self._read_init_log(log_path)
            self.gpu_active = self._detect_metal_gpu(self.init_log)
            if self.use_gpu and not self.gpu_active:
                logger.warning(
                    "whisper.cpp loaded, but AMD RX 580 Metal initialization was not verified; using CPU label"
                )
            elif self.gpu_active:
                logger.info("whisper.cpp Metal GPU verified from runtime init output")

            self._is_loaded = True
            return True
        except Exception as e:
            if not self.use_gpu:
                self.init_log = self._read_init_log(log_path)
                logger.error("Ошибка загрузки whisper.cpp CPU: %s", e)
                self._model = None
                self._is_loaded = False
                self.gpu_active = False
                return False

            self.init_log = self._read_init_log(log_path)
            logger.warning("Ошибка загрузки whisper.cpp с GPU, повтор CPU: %s", e)
            return self._load_cpu_fallback()

    def unload(self) -> None:
        """Unloads the model and clears buffered audio."""
        self._model = None
        self._buffer.clear()
        self._is_loaded = False
        self.gpu_active = False
        logger.info("whisper.cpp модель выгружена")

    def recognize(self, audio_data: bytes) -> Optional[RecognitionResult]:
        """Transcribes a PCM16 mono 16 kHz chunk."""
        if not self._is_loaded or self._model is None:
            logger.error("whisper.cpp не загружен")
            return None

        audio_f32 = self._pcm16_to_float32(audio_data)
        if audio_f32.size == 0:
            return None

        try:
            segments = self._model.transcribe(audio_f32, **self._decode_params())
            text = self._clean_text(self._segments_to_text(segments))
            if not text:
                return None

            return RecognitionResult(
                text=text,
                is_final=True,
                confidence=0.0,
                engine="whisper.cpp (Metal)" if self.gpu_active else "whisper.cpp (CPU)",
            )
        except Exception as e:
            logger.error("Ошибка распознавания whisper.cpp: %s", e)
            return None

    def recognize_stream(self, audio_chunk: bytes) -> Generator[RecognitionResult, None, None]:
        """Buffers live audio and transcribes complete chunk-duration windows."""
        if not self._is_loaded or self._model is None:
            logger.error("whisper.cpp не загружен")
            return

        self._buffer.extend(audio_chunk)
        target_bytes = int(self.config.sample_rate * self.config.chunk_duration * 2)
        if len(self._buffer) < target_bytes:
            return

        chunk = bytes(self._buffer[:target_bytes])
        del self._buffer[:target_bytes]

        if self._is_silence(chunk):
            return

        result = self.recognize(chunk)
        if result:
            yield result

    def reset(self) -> None:
        """Clears buffered stream audio."""
        self._buffer.clear()

    def _load_cpu_fallback(self) -> bool:
        log_path = self._init_log_path()
        try:
            self._model = self._create_model(use_gpu=False, log_path=log_path)
            self.init_log = self._read_init_log(log_path)
            self.gpu_active = False
            self._is_loaded = True
            logger.info("whisper.cpp загружен в CPU fallback режиме")
            return True
        except Exception as e:
            self.init_log = self._read_init_log(log_path)
            logger.error("Ошибка CPU fallback whisper.cpp: %s", e)
            self._model = None
            self._is_loaded = False
            self.gpu_active = False
            return False

    def _create_model(self, use_gpu: bool, log_path: str):
        return WhisperCppModel(
            self._model_path(),
            models_dir=str(self.model_dir),
            redirect_whispercpp_logs_to=log_path,
            context_params={"use_gpu": use_gpu},
            n_threads=self._thread_count(),
            **self._decode_params(),
        )

    def _model_path(self) -> str:
        direct = Path(self.model_name).expanduser()
        if direct.is_file():
            return str(direct)

        local_names = [self.model_name]
        if not self.model_name.startswith("ggml-"):
            local_names.insert(0, f"ggml-{self.model_name}.bin")
        elif not self.model_name.endswith(".bin"):
            local_names.insert(0, f"{self.model_name}.bin")

        for name in local_names:
            candidate = self.model_dir / name
            if candidate.is_file():
                return str(candidate)

        from pywhispercpp.utils import resolve_model_path

        return resolve_model_path(self.model_name, str(self.model_dir))

    def _decode_params(self) -> dict[str, object]:
        return {
            "language": self.language,
            "translate": False,
            "no_context": True,
            "no_timestamps": True,
            "single_segment": True,
            "print_progress": False,
            "print_realtime": False,
            "print_timestamps": False,
            "suppress_blank": True,
            "suppress_nst": True,
            "temperature": 0.0,
            "temperature_inc": 0.0,
        }

    @staticmethod
    def _thread_count() -> int:
        for name in ("WHISPER_CPP_THREADS", "OMP_NUM_THREADS"):
            value = os.environ.get(name)
            if not value:
                continue
            try:
                threads = int(value)
            except ValueError:
                continue
            if threads > 0:
                return threads
        return min(4, os.cpu_count() or 1)

    def _clean_text(self, text: str) -> str:
        text = self._filter.clean(text)
        if (
            not text
            or self._is_missing_required_script(text)
            or self._is_english_filler(text)
            or self._is_russian_noise_cue(text)
            or self._is_garbled_mixed_script(text)
        ):
            return ""
        return text

    def _is_missing_required_script(self, text: str) -> bool:
        if self.language.lower() != "ru":
            return False
        return re.search(r"[а-яё]", text, flags=re.IGNORECASE) is None

    @classmethod
    def _is_russian_noise_cue(cls, text: str) -> bool:
        normalized = cls._normalize_words(text)
        return normalized in cls.RUSSIAN_NOISE_PHRASES

    @classmethod
    def _is_garbled_mixed_script(cls, text: str) -> bool:
        if "�" in text:
            return True
        if cls.NON_RUSSIAN_SCRIPT_RE.search(text):
            return True

        cyrillic = len(re.findall(r"[а-яё]", text, flags=re.IGNORECASE))
        latin = len(re.findall(r"[a-z]", text, flags=re.IGNORECASE))
        if cyrillic == 0:
            return False
        return latin >= 8 and latin > cyrillic * 2

    @classmethod
    def _is_english_filler(cls, text: str) -> bool:
        if re.search(r"[а-яё]", text, flags=re.IGNORECASE):
            return False

        normalized = cls._normalize_words(text, alphabet=r"a-zA-Z")
        if not normalized:
            return True

        if normalized in cls.ENGLISH_FILLER_PHRASES:
            return True

        words = normalized.split()
        if words and words[0] in {"blurgy", "blurry"}:
            return True
        if len(words) >= 3 and len(set(words)) == 1:
            return True
        return bool(words) and all(word in cls.ENGLISH_FILLER_WORDS for word in words)

    @staticmethod
    def _normalize_words(text: str, alphabet: str = r"\w") -> str:
        text = text.strip().lower().replace("ё", "е")
        text = re.sub(rf"[^{alphabet}\s]+", " ", text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def _detect_metal_gpu(cls, init_log: str) -> bool:
        normalized = init_log.lower()
        has_metal = any(marker.lower() in normalized for marker in cls.METAL_MARKERS)
        has_amd_rx580 = any(marker.lower() in normalized for marker in cls.AMD_DEVICE_MARKERS)
        return has_metal and has_amd_rx580

    def _is_silence(self, audio_data: bytes) -> bool:
        samples = np.frombuffer(audio_data, np.int16).astype(np.int32)
        if samples.size == 0:
            return True
        return float(np.max(np.abs(samples))) < float(self.config.vad_threshold)

    @staticmethod
    def _pcm16_to_float32(audio_data: bytes) -> np.ndarray:
        return np.frombuffer(audio_data, np.int16).astype(np.float32) / 32768.0

    @staticmethod
    def _segments_to_text(segments) -> str:
        parts = []
        for segment in segments or []:
            text = getattr(segment, "text", segment)
            if text is not None:
                parts.append(str(text).strip())
        return " ".join(part for part in parts if part)

    @staticmethod
    def _init_log_path() -> str:
        handle = tempfile.NamedTemporaryFile(prefix="whispercpp-init-", suffix=".log", delete=False)
        path = handle.name
        handle.close()
        return path

    @staticmethod
    def _read_init_log(path: str) -> str:
        try:
            return Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        finally:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass
```

---

