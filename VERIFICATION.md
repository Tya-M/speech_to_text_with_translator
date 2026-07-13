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
| whisper.cpp `small` | Metal / CPU fallback | n/a | n/a | n/a | BLOCKED: `ggml-small.bin` download returns proxy 502 |

Transcript quality:

- Vosk: `родион потапыч высчитывал каждый новый вершок углубления и давно определил про себя`
- faster-whisper: `Родион Потапыч высчитывал каждый новый вершок углубления и давно определил про себя`
- openai-whisper: `Родион Потапыч высчитывал каждый новый вершок углубления и давно определил про себя`

## whisper.cpp / Metal Status

`pywhispercpp` is importable and linked against Metal, but the model is missing:

- `models/whisper-cpp` is empty.
- `pywhispercpp.resolve_model_path("small", "models/whisper-cpp")` failed via Hugging Face/Xet with `502 Bad Gateway`.
- `curl https://ggml.ggerganov.com/ggml-model-whisper-small.bin` failed with `502`.
- `hf download ggerganov/whisper.cpp ggml-small.bin` with `HF_HUB_DISABLE_XET=1` failed with `502 Bad Gateway`.

Because no ggml model is available, whisper.cpp transcription did not run and no `ggml_metal_init` / system-info lines were produced. Metal device picked: **not verified**.

## Fallback / Compatibility

- Real factory fallback passed: requesting `whisper_cpp` failed on model download, then loaded `FasterWhisperRecognizer`.
- Current `config.json` loads.
- Old minimal config loads and fills new defaults.
- Config persistence round-trip passed.
- GUI import with Whisper deps hidden passed; optional flags became `False`.

## Manual Confirmation Still Required

- AMD RX 580 GPU activity in Activity Monitor during whisper.cpp recognition.
- Live transcription quality in the app window.
