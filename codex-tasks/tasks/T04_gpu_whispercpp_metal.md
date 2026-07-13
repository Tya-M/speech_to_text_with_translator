# T04 — GPU engine: whisper.cpp + Metal (AMD RX 580)

- **Phase:** 4 (highest risk — isolated on purpose)
- **Depends on:** T01, T02, T03. Needs T06 build steps (pywhispercpp with Metal) to run.
- **Risk:** HIGH (Metal on Intel+AMD is under-tested)

## Objective

Add a whisper.cpp-based engine that actually uses the AMD Radeon RX 580 via the Metal backend, with mandatory runtime verification and a clean CPU fallback.

## Why this design (do not substitute faster-whisper here)

faster-whisper/CTranslate2 is CPU/CUDA-only and cannot use AMD on macOS. whisper.cpp's Metal backend can target the AMD GPU. See `00_context_and_constraints.md`.

## Files to touch

- `recognition/whispercpp_engine.py` (new)
- `recognition/__init__.py` (register in factory — coordinate with T03)

## Steps

1. New class `WhisperCppRecognizer(config, model_name, model_dir, use_gpu=True)` subclassing `BaseRecognizer`; guard import with `WHISPER_CPP_AVAILABLE`.
2. Use `pywhispercpp`:
   ```python
   from pywhispercpp.model import Model
   self._model = Model(model_name, models_dir=model_dir, n_threads=os.cpu_count())
   ```
   pywhispercpp auto-downloads the ggml model if missing (see T06 for building it WITH Metal).
3. **GPU verification (mandatory):** after load, inspect the whisper.cpp init logs / system-info for a Metal device line (expect something like `ggml_metal_init: picking default device: AMD Radeon RX 580`). Set `self.gpu_active = True/False` accordingly. If `use_gpu` is requested but Metal did not initialize on the GPU, log a clear WARNING and continue on CPU.
4. `recognize()`: convert int16 → float32, call `self._model.transcribe(audio_f32, language=config.whisper_language)`, join segment texts, return `RecognitionResult(engine="whisper.cpp (Metal)" if self.gpu_active else "whisper.cpp (CPU)", is_final=True)`.
5. `recognize_stream()`: accumulate `config.chunk_duration` (whisper.cpp is not truly streaming), transcribe per chunk, apply `vad_threshold` gating + hallucination guard (drop empty/filler-only).
6. Implement `unload()`/`reset()`.
7. **Optional secondary fallback (only if Metal fails):** a `WhisperCppCliRecognizer` that shells out to a whisper.cpp CLI binary built with Metal (`whisper-cli -m <ggml-model> -l ru -f <wav>`) and parses stdout. Keep it behind the same interface. Build flags in T06.

## Deliverables

- `whispercpp_engine.py` with GPU verification + CPU fallback.
- Factory registration so `whisper_backend="whisper_cpp"` reaches this engine.

## Acceptance checklist

- [ ] With pywhispercpp built with Metal, transcribes Russian mic audio (model `small`).
- [ ] Logs confirm the **AMD RX 580 Metal device** is initialized; `gpu_active` is True.
- [ ] GPU activity is visible in macOS Activity Monitor's GPU history during recognition.
- [ ] If Metal is unavailable, engine loads on CPU (or factory falls back), no crash; status reflects CPU.
- [ ] `RecognitionResult.engine` label matches the actual device used.

## Risks & notes

- Metal in whisper.cpp is primarily optimized for Apple Silicon; on Intel+AMD it may underperform or silently fall back to CPU. The verification step is what makes this honest — do not claim GPU use without the log/Activity-Monitor evidence.
- If Metal underperforms, the acceptable shipped outcome is CPU `small` int8 (fast enough) — that is a T07 decision, not a reason to fake GPU support.
- Keep this engine fully optional so its failure never blocks M2/M3 builds.

## Stop gate & handoff (MANDATORY)

When this task's Acceptance checklist fully passes:
1. Update `../PROGRESS.md`: mark this task `Done`, set the next task as current, record the branch/commit and date, and append a one-line handoff note.
2. Print a short handoff: what changed, how it was verified, the exact next task, and a ready-to-paste resume prompt.
3. **STOP. Do not start the next task.** Wait for the user to explicitly say to continue (e.g. "continue" / "продолжай").

If the checklist does not fully pass, stay on this task; do not advance and do not mark it Done.
