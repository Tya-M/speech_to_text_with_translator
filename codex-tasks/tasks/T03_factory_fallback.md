# T03 — Engine factory + graceful fallback chain

- **Phase:** 3
- **Depends on:** T01, T02
- **Risk:** Low

## Objective

Centralize engine selection in a factory and add a resilient fallback chain so a failed engine load never leaves the app without recognition.

## Files to touch

- `recognition/__init__.py`

## Steps

1. Export all engine classes and availability flags:
   `VoskRecognizer/VOSK_AVAILABLE`, `WhisperRecognizer/WHISPER_AVAILABLE`, `FasterWhisperRecognizer/FASTER_WHISPER_AVAILABLE`, and (after T04) `WhisperCppRecognizer/WHISPER_CPP_AVAILABLE`.
2. Implement:
   ```python
   def create_recognizer(config: AppConfig, rec_config: RecognitionConfig) -> Optional[BaseRecognizer]: ...
   ```
   Selection:
   - `config.engine == "vosk"` → `VoskRecognizer`.
   - `config.engine == "whisper"` → by `config.whisper_backend`:
     - `"whisper_cpp"` → `WhisperCppRecognizer` (GPU/Metal path; added in T04).
     - `"faster"` → `FasterWhisperRecognizer` (CPU int8).
     - `"openai"` → `WhisperRecognizer` (CPU).
3. Fallback chain (log every downgrade): requested engine load fails → try `faster-whisper` CPU → try `WhisperRecognizer` CPU → try Vosk. If everything fails, return `None` and surface a clear error to the GUI.
4. Before T04 is done, treat `whisper_cpp` as unavailable and fall back to faster-whisper CPU (do not crash).

## Deliverables

- `create_recognizer(...)` with documented selection + fallback semantics.

## Acceptance checklist

- [ ] Each `engine`/`whisper_backend` combo selects the intended class.
- [ ] Forcing a load failure (e.g. temporarily bad model path) triggers the documented fallback and logs it.
- [ ] `whisper_cpp` selected while unavailable → falls back to CPU engine, no crash.
- [ ] Returns `None` only when literally nothing can load; GUI handles it.

## Risks & notes

- Keep the factory pure (no GUI imports) to avoid circular imports.

## Stop gate & handoff (MANDATORY)

When this task's Acceptance checklist fully passes:
1. Update `../PROGRESS.md`: mark this task `Done`, set the next task as current, record the branch/commit and date, and append a one-line handoff note.
2. Print a short handoff: what changed, how it was verified, the exact next task, and a ready-to-paste resume prompt.
3. **STOP. Do not start the next task.** Wait for the user to explicitly say to continue (e.g. "continue" / "продолжай").

If the checklist does not fully pass, stay on this task; do not advance and do not mark it Done.
