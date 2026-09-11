# 🎙️ Voice Translator

_[Русская версия — README.md](README.md)_

A desktop application for **offline Russian speech recognition** with translation
and a **dictation-into-cursor** mode that types into any macOS app — without cloud
speech-recognition or translation services.

> Speech processing runs locally on your computer. Audio is not sent to cloud services.
> Internet access may be needed on first launch to download models and the translation
> language package.

---

## ✨ Features

- **Offline Russian speech recognition** through **GigaAM**.
- **Translation** of the recognized text.
- **Two selectable local translators:** fast `Argos` and the newer
  `TranslateGemma 4B` (the Google model is downloaded locally when selected).
- **🎤 Dictation into cursor** — hold a hotkey, speak, and the text is typed
  wherever your cursor is (browser, editor, messenger, etc.).
- Dictation offers a **Russian** or **Russian + English** profile. The Russian
  profile uses GigaAM; the bilingual profile uses Parakeet through `sherpa-onnx`
  and automatically uses GigaAM for Russian speech.
- **Graphical interface** with microphone, sensitivity, VAD-threshold and model
  selection.
- Configurable hotkey. The dictation mode — hold (`hold`) or toggle (`toggle`) —
  is configured in the settings or through the CLI.

---

## 🧩 Requirements

- **macOS** (tested on macOS Tahoe / macOS 26; also works on earlier versions).
- **Python 3.10+**
- **ffmpeg** (required by GigaAM):
  ```bash
  brew install ffmpeg
  ```
- Python dependencies are listed in [`requirements.txt`](requirements.txt), including:
  - `customtkinter` — graphical interface;
  - `pyaudio` — microphone audio capture;
  - `gigaam` — the Russian speech recognition engine (installed separately by the
    command below; it is only commented in `requirements.txt`);
  - `transformers` and `safetensors` — the local TranslateGemma 4B backend;
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

# 5. Optional: install the Python packages for English Parakeet dictation
pip install "sherpa-onnx==1.13.8" "sherpa-onnx-bin==1.13.8"
```

Parakeet also requires the local Unified EN model. Download it separately and put
`tokens.txt`, `encoder.int8.onnx`, `decoder.int8.onnx`, and `joiner.int8.onnx` in
the directory specified by `parakeet_model_path`.

On first launch, GigaAM may download the selected model if it is not cached. If the
Argos Translate package is not installed locally, Argos downloads its index and the
`ru→en` language package. When TranslateGemma is selected, the app downloads the
official `google/translategemma-4b-it` model from Hugging Face and then runs locally
on the CPU. You must accept Google's Gemma license on the model page before the
download. TranslateGemma is considerably heavier and slower than Argos on this
computer, so Argos remains the default.

### Testing

Install the test dependencies and run the complete test suite with:

```bash
pip install -r requirements-dev.txt
python -m pytest
```

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
2. In the **"🎤 Dictation into cursor"** panel, choose the language profile and hotkey
   (F7–F12, right ⌥, or right ⌘).
3. Click the dictation button — it turns red ("ON").
4. Place the cursor in the desired window, **hold** the hotkey, speak and release —
   the recognized text is typed wherever the cursor is.

> Dictation runs as a **separate process** for stability on macOS: this isolates the
> native libraries (audio, hotkeys, and recognition) from the GUI's main loop. The
> dictation model may therefore be loaded separately from the model in the main window.

The default mode is `hold`: keep the hotkey pressed while speaking. To use toggle
mode, set `dictation_mode: "toggle"` in `config.json` or run standalone mode with
`--mode toggle`.

---

## 🛠️ Configuration (`config.json`)

Main parameters:

| Parameter | Purpose | Example / range |
|---|---|---|
| `engine` | Main recognition engine; only `gigaam` is currently supported | `"gigaam"` |
| `gigaam_model` | GigaAM model: `v3_e2e_rnnt` or `v3_e2e_ctc` | `"v3_e2e_rnnt"` |
| `gigaam_device` | Device: `auto`, `cpu`, or `cuda` | `"cpu"` |
| `gigaam_language` | GigaAM language | `"ru"` |
| `sensitivity` | Software microphone gain; `1000` means neutral | `850` (100–2000) |
| `vad_threshold` | Speech-detection threshold | `700` (200–1000) |
| `device_index` | Microphone index | `7` |
| `device_name` | Microphone name used to restore the selection | `"fifine Microphone"` |
| `sample_rate` | Sample rate, Hz | `16000` (8000–48000) |
| `chunk_duration` | Audio-window duration, seconds | `3.0` (1.0–10.0) |
| `font_size` | Transcript font size | `14` (10–24) |
| `window_width` / `window_height` | Application window size | `900` / `450` |
| `translation_cache_size` | Translation-cache size | `100` (1–10000) |
| `translation_engine` | Translator: `argos` or `translategemma` | `"argos"` |
| `translategemma_model_id` | Hugging Face model ID or local model directory | `"google/translategemma-4b-it"` |
| `partial_throttle_ms` | Partial-text update interval, ms | `100` (50–300) |
| `dictation_key` | Hotkey: `f7`–`f12`, `alt_r`, or `cmd_r` | `"cmd_r"` |
| `dictation_mode` | Mode: `hold` or `toggle` | `"hold"` |
| `dictation_engine` | Dictation profile: `gigaam` or `parakeet` | `"parakeet"` |
| `parakeet_model_path` | Local Parakeet Unified EN model directory | `"sherpa-onnx-nemo-parakeet-unified-en-0.6b-int8-non-streaming"` |
| `parakeet_num_threads` | Number of Parakeet CPU threads | `2` (1–8) |

The interface changes the recognition model, translator, microphone, sensitivity,
VAD, dictation language profile, and hotkey. These changes are saved automatically. Other parameters are
edited in `config.json`; the standalone CLI additionally accepts the hotkey, mode,
and dictation profile.

---

## 📁 Project structure

```
.
├── app/               # Graphical interface (customtkinter)
├── audio/             # Microphone audio capture
├── recognition/       # Recognition engines GigaAM and Parakeet + VAD
├── translation/       # Text translation
├── input_injection/   # Typing into the cursor and the dictation service
├── utils/             # Configuration, logging, helpers
├── main.py            # Entry point: app with the interface
├── dictation_main.py  # Entry point: dictation-only mode
├── config.json        # Application settings
├── requirements.txt   # Main Python dependencies
├── requirements-dev.txt # Test dependencies
└── LICENSE.md         # Project license
```

---

## ❓ Troubleshooting

- **“Nothing recognized” / silence** — check the “Microphone” permission and the correct
  device index (`device_index`); lower `vad_threshold` if needed.
- **Text is not typed into the cursor / an error beep** — the “Accessibility” and/or
  “Input Monitoring” permissions are not granted to the right Python binary; grant them
  and restart the terminal.
- **Error installing GigaAM** — make sure `ffmpeg` is installed.
- **Parakeet does not load** — install `sherpa-onnx` and `sherpa-onnx-bin`, then
  verify that the four model files are present in `parakeet_model_path`.
- **TranslateGemma does not load** — install the dependencies from `requirements.txt`,
  accept the Gemma license on Hugging Face, and check `translategemma_model_id`.
  If the model is unavailable, the app automatically uses Argos.
- **`error: externally-managed-environment`** — install dependencies inside an
  activated virtual environment (`source venv/bin/activate`).

---

## 📄 License

This project is distributed under the **MIT License** — see the [LICENSE.md](LICENSE.md) file.

### Third-party component licenses
The application uses third-party software under its own licenses:
- **GigaAM** — MIT (© GigaChat Team)
- **Argos Translate** — MIT / CC0
- **pynput** — LGPL-3.0
- **PyTorch**, **customtkinter**, **PyAudio**, etc. — see their repositories

Recognition and translation models are downloaded separately and are subject to the
licenses of their respective authors.
