# T01 — Configuration foundation

- **Phase:** 1
- **Depends on:** none
- **Risk:** Low (backward compatibility is the only trap)

## Objective

Extend `AppConfig` (`utils/config.py`) so engine, backend, device, and model choices are configurable and persisted, without breaking existing `config.json` files.

## Files to touch

- `utils/config.py`
- `config.json` (add example values; keep it loadable by the old code)

## Steps

1. In `AppConfig`, extend/add fields:
   - Change `whisper_backend` literal to include the new value:
     `whisper_backend: Literal["openai", "faster", "whisper_cpp"] = "whisper_cpp"`
   - `whisper_compute_type: str = "int8"`  (faster-whisper CPU compute type)
   - `whisper_device: Literal["auto", "cpu", "gpu"] = "auto"`
   - `whisper_cpp_model_dir: str = "models/whisper-cpp"`
   - `whisper_cpp_use_gpu: bool = True`
   - `whisper_language: str = "ru"`
2. Keep `AppConfig.load()` tolerant: it already filters unknown keys — verify old configs (without the new fields) still load and get defaults.
3. Add validation in `__post_init__` if useful (e.g. clamp/normalize `whisper_device`).
4. Update `config.json` with the new keys as a documented example. Do NOT remove existing keys.

## Deliverables

- Updated `AppConfig` dataclass with new fields + defaults.
- Example `config.json` including the new keys.

## Acceptance checklist

- [ ] Loading an OLD `config.json` (no new keys) succeeds and applies defaults.
- [ ] Loading a NEW `config.json` (with new keys) round-trips through `save()`/`load()` unchanged.
- [ ] `whisper_backend="whisper_cpp"` is accepted and validated.
- [ ] App still starts and Vosk still works (no behavior change yet).

## Risks & notes

- Do not change field order in a way that breaks positional construction elsewhere; prefer adding fields at the end of the dataclass.

## Stop gate & handoff (MANDATORY)

When this task's Acceptance checklist fully passes:
1. Update `../PROGRESS.md`: mark this task `Done`, set the next task as current, record the branch/commit and date, and append a one-line handoff note.
2. Print a short handoff: what changed, how it was verified, the exact next task, and a ready-to-paste resume prompt.
3. **STOP. Do not start the next task.** Wait for the user to explicitly say to continue (e.g. "continue" / "продолжай").

If the checklist does not fully pass, stay on this task; do not advance and do not mark it Done.
