# 🎙️ Voice Translator

_[Русская версия — README.md](README.md)_

A desktop application for **offline Russian speech recognition** with translation
and a **dictation-into-cursor** mode that types into any macOS app — with no cloud
services or third-party APIs.

> All speech processing runs locally on your computer. Audio is never sent anywhere.

---

## ✨ Features

- **Offline speech recognition** with a choice of two engines:
  - **GigaAM** — high-quality Russian recognition (recommended);
  - **Vosk** — lightweight and fast option.
- **Translation** of the recognized text.
- **🎤 Dictation into cursor** — hold a hotkey, speak, and the text is typed
  wherever your cursor is (browser, editor, messenger, etc.).
- Dictation can use **GigaAM (Russian)** or **Parakeet Unified EN (English)**;
  Parakeet runs locally through `sherpa-onnx`.
- **Graphical interface** with microphone, sensitivity and VAD-threshold settings,
  plus engine and model selection.
- Configurable hotkey and dictation mode (hold / toggle).

---

## 🧩 Requirements

- **macOS** (tested on macOS Tahoe / macOS 26; also works on earlier versions).
- **Python 3.11+**
- **ffmpeg** (required by GigaAM):
  ```bash
  brew install ffmpeg
  ```
- Python dependencies are listed in [`requirements.txt`](requirements.txt), including:
  - `customtkinter` — graphical interface;
  - `pyaudio` — microphone audio capture;
  - `vosk` — the Vosk engine;
  - `pynput`, `pyobjc-framework-Quartz`, `pyobjc-framework-Cocoa` — typing into the
    cursor and handling global hotkeys on macOS.

---

## ⚙️ Installation

```bash
# 1. Clone the repository
git clone https://github.com/Tya-M/speech_to_text_with_translator.git
cd speech_to_text_with_translator

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install the GigaAM engine (for the best quality)
pip install "gigaam @ git+https://github.com/salute-developers/GigaAM.git"

# 5. Optional: install the English Parakeet engine
pip install "sherpa-onnx==1.13.8" "sherpa-onnx-bin==1.13.8"
```

> On first launch, the selected recognition model is downloaded automatically.

---

## 🔐 macOS permissions

So that dictation can type into the cursor and hear the microphone, grant
permissions **to the exact Python executable you launch the app from** (usually
your terminal or the Python binary inside `venv`).

**System Settings → Privacy & Security →**
- **Accessibility** — required (synthetic text input);
- **Input Monitoring** — required (global hotkey capture);
- **Microphone** — required (speech capture).

Find the exact path to the Python binary:
```bash
python -c "import sys, os; print(os.path.realpath(sys.executable))"
```
Add exactly that file to the lists above and **restart your terminal** after granting
the permissions.

---

## 🚀 Running

**Full application with the graphical interface:**
```bash
source venv/bin/activate
python main.py
```

**Dictation-only mode (no window, from the terminal):**
```bash
python dictation_main.py
```

---

## 🎤 How to use dictation into the cursor

1. Launch the app and wait for the recognition engine to load.
2. In the **"🎤 Dictation into cursor"** panel, choose the language and engine.
3. Choose a hotkey (F7–F12, right ⌥, or right ⌘), then click the button — it turns red ("ON").
4. Place the cursor in the desired window, **hold** the hotkey, speak and release —
   the recognized text is typed wherever the cursor is.

> Dictation runs as a **separate process** for stability on macOS: this isolates the
> native libraries (audio, hotkeys, the recognition model) from the GUI's main loop.

---

## 🛠️ Configuration (`config.json`)

Main parameters:

| Parameter          | Purpose                                                 | Example         |
|--------------------|---------------------------------------------------------|-----------------|
| `engine`           | Recognition engine: `gigaam` or `vosk`                  | `"gigaam"`      |
| `gigaam_model`     | GigaAM model                                            | `"v3_e2e_rnnt"` |
| `vad_threshold`    | Speech-detection threshold (silence/voice)              | `700`           |
| `sample_rate`      | Sample rate, Hz                                         | `16000`         |
| `device_index`     | Microphone index                                        | `7`             |
| `dictation_key`    | Dictation hotkey                                        | `"f9"`          |
| `dictation_mode`   | Mode: `hold` or `toggle`                                | `"hold"`        |
| `dictation_engine` | Dictation engine: `gigaam` or `parakeet`               | `"gigaam"`      |
| `parakeet_model_path` | Parakeet Unified EN model directory                  | `"sherpa-onnx-nemo-parakeet-unified-en-0.6b-int8-non-streaming"` |
| `parakeet_num_threads` | Number of Parakeet CPU threads                       | `2`              |

Settings can also be changed directly in the interface — they are saved automatically.

---

## 📁 Project structure

```
.
├── app/               # Graphical interface (customtkinter)
├── audio/             # Microphone audio capture
├── recognition/       # Recognition engines (GigaAM, Vosk) + VAD
├── translation/       # Text translation
├── input_injection/   # Typing into the cursor and the dictation service
├── utils/             # Configuration, logging, helpers
├── main.py            # Entry point: app with the interface
├── dictation_main.py  # Entry point: dictation-only mode
├── config.json        # Application settings
└── requirements.txt   # Python dependencies
```

---

## ❓ Troubleshooting

- **“Nothing recognized” / silence** — check the “Microphone” permission and the correct
  device index (`device_index`); lower `vad_threshold` if needed.
- **Text is not typed into the cursor / an error beep** — the “Accessibility” and/or
  “Input Monitoring” permissions are not granted to the right Python binary; grant them
  and restart the terminal.
- **Error installing GigaAM** — make sure `ffmpeg` is installed.
- **`error: externally-managed-environment`** — install dependencies inside an
  activated virtual environment (`source venv/bin/activate`).

---

## 📄 License

This project is distributed under the **MIT License** — see the [LICENSE](LICENSE) file.

### Third-party component licenses
The application uses third-party software under its own licenses:
- **GigaAM** — MIT (© GigaChat Team)
- **Vosk** — Apache License 2.0
- **Argos Translate** — MIT / CC0
- **pynput** — LGPL-3.0
- **PyTorch**, **customtkinter**, **PyAudio**, etc. — see their repositories

Recognition and translation models are downloaded separately and are subject to the
licenses of their respective authors.
