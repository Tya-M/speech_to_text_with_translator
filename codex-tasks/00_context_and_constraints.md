# Shared context & hard constraints (read before every task)

## Project

"Russian Voice Translator" — a macOS desktop GUI app (`customtkinter`/`tkinter`). Offline Russian speech-to-text with RU→EN translation (Argos). Entry point: `main.py` → `app.gui.VoiceTranslatorApp`. Today only **Vosk** is wired up and used, even though the config already references Whisper.

## Target machine (do not assume otherwise)

- **macOS on a Hackintosh, x86_64 (Intel-class CPU).**
- **GPU: AMD Radeon RX 580 8 GB.**
- **No NVIDIA, no CUDA. No Apple Neural Engine.**
- Because it is a Hackintosh, "About This Mac" identifiers (CPU model, board) may be spoofed via SMBIOS — do not derive hardware assumptions from them beyond the GPU stated here.

## HARD constraints — non-negotiable

1. **faster-whisper / CTranslate2 cannot use the AMD GPU.** It supports **CPU and NVIDIA CUDA only** — no Metal backend; ROCm builds are Linux-only. On this machine it must run on **CPU** with `compute_type="int8"`. Never try to make it use the RX 580.
2. **openai-whisper (PyTorch) has no GPU on Intel macOS.** PyTorch `mps` is Apple-Silicon-only; there is no CUDA. Keep it **CPU-only**.
3. **The only real GPU path is `whisper.cpp` built with the Metal backend (`GGML_METAL`)**, which can target the AMD Radeon via Metal. This is the primary GPU engine (T04). Metal in whisper.cpp is mainly tuned for Apple Silicon and is less proven on Intel+AMD, so you MUST verify real GPU offload at runtime and fall back to CPU cleanly if it fails. A `GGML_VULKAN` (MoltenVK) build is an OPTIONAL secondary fallback — only if Metal fails.
4. **Do not break the existing Vosk path** or the shared engine interface.
5. In `main.py`, the env-var setup (`KMP_DUPLICATE_LIB_OK`, `OMP_NUM_THREADS`, `MKL_NUM_THREADS`) MUST stay **before** any `torch`/`whisper` import. New torch-importing code must not run before those are set.
6. Every new dependency import must be guarded (`try/except ImportError` + a feature flag) so the app still starts if a dependency is missing.

## Existing architecture you must conform to

Open and mirror these before writing code:

- `recognition/base.py` — abstract `BaseRecognizer(config: RecognitionConfig)`. Engines implement (confirm exact signatures in the file):
  - `load(self) -> bool`
  - `recognize(self, audio_data: bytes) -> Optional[RecognitionResult]`
  - `recognize_stream(self, audio_chunk: bytes) -> Generator[RecognitionResult, None, None]`
  - `reset(self)` / `unload(self)`
- `recognition/vosk_engine.py` — the **reference implementation** to mirror. Constructor: `VoskRecognizer(config, model_path=..., phrase_timeout=...)`; availability flag `VOSK_AVAILABLE` guarded by `ImportError`.
- `utils/threading_utils.py` — `RecognitionResult(text: str, is_final: bool, confidence: float = 0.0, engine: str = "", timestamp: float = 0.0)`. Return this from every engine; set `engine` to a human label (e.g. `"whisper.cpp (Metal)"`, `"faster-whisper (CPU)"`, `"whisper (CPU)"`).
- `utils/config.py` — `AppConfig` (dataclass, JSON-backed, `load()` filters unknown keys) and `RecognitionConfig.from_app_config(...)` (`vad_threshold`, `chunk_duration=3.0`, `sample_rate=16000`, `channels`, `buffer_size`).
- `audio/capture.py` — produces **PCM int16, mono, 16 kHz** frames. Whisper needs float32 in [-1, 1]:
  ```python
  import numpy as np
  audio_f32 = np.frombuffer(audio_data, np.int16).astype(np.float32) / 32768.0
  ```
- `app/gui.py` — `VoiceTranslatorApp` with `EngineManager`/`EngineState`; `_init_recognizers` (~lines 476–535) currently loads only Vosk and hardcodes the status-bar engine name to "Vosk".

## Known existing config fields (utils/config.py `AppConfig`)

`engine: Literal["vosk","whisper"]`, `whisper_model: Literal["tiny","base","small","medium","large-v2","large-v3"]`, `whisper_backend: Literal["openai","faster"]`, `vosk_model_size`, `sample_rate=16000`, `chunk_duration=3.0`, and cache dirs `whisper_cache_dir="models/whisper"`, `faster_whisper_cache_dir="models/faster-whisper"`.

## Definition of done (applies to all tasks)

- App still launches with only Vosk deps installed.
- New code paths are guarded and logged.
- The task's own Acceptance checklist passes.
- No regression to Vosk real-time recognition.
