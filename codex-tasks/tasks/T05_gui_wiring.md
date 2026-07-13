# T05 — GUI wiring: selectors + real status bar

- **Phase:** 5
- **Depends on:** T03 (factory). Full value needs T02 and T04 engines.
- **Risk:** Medium (UI threading)

## Objective

Make engine/backend/model selectable at runtime and show the real active engine + device in the status bar. Never block the Tk main loop on model loading.

## Files to touch

- `app/gui.py`
- possibly `app/components.py` / `app/styles.py` for the new controls

## Steps

1. Replace the Vosk-only imports with the factory: `from recognition import create_recognizer, <flags...>`.
2. Rewrite `_init_recognizers` (~lines 476–535) to build the recognizer via `create_recognizer(self.config, RecognitionConfig.from_app_config(self.config))`. Keep Vosk working when `engine=="vosk"`.
3. Add UI controls (reuse existing `CTkOptionMenu` styling):
   - **Engine:** `Vosk` / `Whisper`.
   - When Whisper: **Backend** `whisper.cpp (GPU)` / `faster-whisper (CPU)` / `openai (CPU)`, and **Model** `tiny/base/small/medium/large-v3`.
4. On change: update `AppConfig`, persist with `config.save()`, then reload the recognizer **on a background thread** (mirror the existing threaded init). Show a loading state; never freeze the UI.
5. **Status bar:** drive it from the loaded engine, not a hardcoded string. Show engine + device, e.g. `Whisper · whisper.cpp · Metal (AMD RX 580)` or `… · CPU`. Use the engine's `engine` label / `gpu_active`.
6. On load failure, show a user-visible message and rely on the T03 fallback; reflect the actual engine that ended up active.

## Deliverables

- Runtime engine/backend/model switching with persistence.
- Accurate status bar reflecting the real active engine and device.

## Acceptance checklist

- [ ] Switching engine/backend/model reloads without freezing the UI.
- [ ] Choice persists across restarts (via `config.save()`).
- [ ] Status bar shows the real engine + device (matches logs).
- [ ] Load failure shows a message and falls back; status bar shows the fallback engine.
- [ ] Vosk selectable and unchanged.

## Risks & notes

- All Tk widget updates must happen on the main thread (use `self.root.after(0, ...)` from worker threads), as the existing code already does for device lists.

## Stop gate & handoff (MANDATORY)

When this task's Acceptance checklist fully passes:
1. Update `../PROGRESS.md`: mark this task `Done`, set the next task as current, record the branch/commit and date, and append a one-line handoff note.
2. Print a short handoff: what changed, how it was verified, the exact next task, and a ready-to-paste resume prompt.
3. **STOP. Do not start the next task.** Wait for the user to explicitly say to continue (e.g. "continue" / "продолжай").

If the checklist does not fully pass, stay on this task; do not advance and do not mark it Done.
