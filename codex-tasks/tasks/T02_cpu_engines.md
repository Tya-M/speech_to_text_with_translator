# T02 — CPU Whisper engines (openai-whisper + faster-whisper)

- **Phase:** 2
- **Depends on:** T01. Needs T06 dependencies/models available to run.
- **Risk:** Low–Medium (audio format conversion is the main gotcha)

## Objective

Recreate the two CPU Whisper engines as proper `.py` sources (the repo only has stale `.pyc`). Prove the Whisper pipeline works on CPU before attempting GPU (T04).

## Files to touch

- `recognition/whisper_engine.py` (recreate)
- `recognition/faster_whisper_engine.py` (recreate)
- `recognition/__init__.py` (export new classes + availability flags — full factory is T03)

## Interface (mirror `recognition/base.py` and `vosk_engine.py`)

Both subclass `BaseRecognizer` and return `RecognitionResult`. Convert int16 PCM bytes → float32:
```python
import numpy as np
audio_f32 = np.frombuffer(audio_data, np.int16).astype(np.float32) / 32768.0
```

### `whisper_engine.py`
- Class `WhisperRecognizer(config, model_name, cache_dir)` using `openai-whisper`.
- **CPU only**: load with `whisper.load_model(model_name, device="cpu", download_root=cache_dir)`.
- Guard import with `WHISPER_AVAILABLE`.
- `recognize()` → run `model.transcribe(audio_f32, language=config.whisper_language, fp16=False)`, return final `RecognitionResult(engine="whisper (CPU)", is_final=True)`.
- `recognize_stream()` → accumulate `config.chunk_duration` seconds, transcribe per chunk, apply `vad_threshold` silence gating.

### `faster_whisper_engine.py`
- Class `FasterWhisperRecognizer(config, model_name, cache_dir, compute_type="int8")` using `faster-whisper`.
- **CPU only**: `WhisperModel(model_name, device="cpu", compute_type=compute_type, download_root=cache_dir)`.
- Guard import with `FASTER_WHISPER_AVAILABLE`.
- `recognize()`/`recognize_stream()` → iterate `segments`, join text, return `RecognitionResult(engine="faster-whisper (CPU)")`.
- Add a light hallucination guard: drop empty/whitespace-only and known filler-only outputs.

## Deliverables

- Two working CPU engine modules with availability flags.
- Minimal exports in `recognition/__init__.py`.

## Acceptance checklist

- [ ] With deps installed, `WhisperRecognizer` transcribes Russian mic audio (model `small`) on CPU.
- [ ] With deps installed, `FasterWhisperRecognizer` transcribes Russian mic audio (`small`, `int8`) on CPU.
- [ ] With deps NOT installed, importing `recognition` does not crash the app (flags are False).
- [ ] Audio conversion verified (no clipping/garbage: sample a chunk and confirm plausible transcript).
- [ ] Vosk still works.

## Risks & notes

- Respect `main.py` env-var ordering before importing torch/whisper.
- Keep model load on a background thread when wired into the GUI (handled in T05), but the engine `load()` itself should be synchronous and return `bool`.

## Stop gate & handoff (MANDATORY)

When this task's Acceptance checklist fully passes:
1. Update `../PROGRESS.md`: mark this task `Done`, set the next task as current, record the branch/commit and date, and append a one-line handoff note.
2. Print a short handoff: what changed, how it was verified, the exact next task, and a ready-to-paste resume prompt.
3. **STOP. Do not start the next task.** Wait for the user to explicitly say to continue (e.g. "continue" / "продолжай").

If the checklist does not fully pass, stay on this task; do not advance and do not mark it Done.
