# Roadmap — Whisper + AMD GPU (Metal) for Russian Voice Translator

This roadmap sequences the subtasks in `tasks/`. Execute phases in order; within a phase, follow the task order. Each phase ends with a verifiable milestone.

## Guiding principles

- **Never break Vosk.** It is the known-good baseline and the ultimate fallback.
- **Prove the CPU pipeline before chasing the GPU.** Getting Whisper working on CPU first de-risks everything downstream.
- **The GPU path is the highest-risk item.** Isolate it (T04) so a Metal failure never blocks shipping a working CPU build.
- **Every task is reversible** and guarded by `ImportError`/feature flags so a missing dependency never prevents app startup.

## Dependency graph

```
T01 config
 └── T02 CPU engines (openai + faster-whisper)
       └── T03 factory + fallback
             ├── T04 GPU engine (whisper.cpp + Metal)   <- highest risk, isolated
             └── T05 GUI wiring
T06 deps/build/models  (supports T02 & T04; author early, needed to run them)
T07 verification + acceptance  (gate; depends on all)
```

## Phases & milestones

### Phase 0 — Prep & guardrails
- Create a working branch. Confirm the app builds and Vosk records/transcribes today (baseline).
- Read `00_context_and_constraints.md`.
- **Milestone M0:** Baseline reproduced; Vosk works; constraints understood.

### Phase 1 — Config foundation (T01)
- Extend `AppConfig` with engine/backend/device/model fields; keep backward compatibility.
- **Milestone M1:** New config fields load from old and new `config.json` without errors; defaults sane.

### Phase 2 — CPU Whisper engines (T02, supported by T06)
- Recreate `whisper_engine.py` (openai-whisper, CPU) and `faster_whisper_engine.py` (faster-whisper, CPU int8).
- **Milestone M2:** Both CPU engines transcribe Russian from mic via the existing pipeline; Vosk still works.

### Phase 3 — Selection & resilience (T03)
- Add `create_recognizer(...)` factory and the fallback chain (requested → CPU Whisper → Vosk).
- **Milestone M3:** Switching engines via config selects the right engine; forced failures fall back cleanly.

### Phase 4 — GPU acceleration (T04, supported by T06) — highest risk
- Add `whispercpp_engine.py` using `pywhispercpp` built with Metal; verify AMD RX 580 offload; CPU fallback.
- **Milestone M4:** whisper.cpp transcribes Russian AND logs confirm the AMD Metal device is used; if Metal is unavailable, it falls back to CPU without crashing.

### Phase 5 — User-facing controls (T05)
- Engine/backend/model selectors; status bar shows the real active engine + device; background reload.
- **Milestone M5:** User can switch engine/backend/model at runtime; status bar reflects reality.

### Phase 6 — Packaging (T06)
- Finalize `requirements.txt` extras, document macOS build of pywhispercpp with Metal, model download.
- **Milestone M6:** Clean environment can be set up from docs; models download; optional deps are truly optional.

### Phase 7 — Verification & acceptance (T07)
- Run the full acceptance matrix (engines × devices), confirm no Vosk regression, capture GPU-usage evidence.
- **Milestone M7 (ship gate):** All acceptance criteria pass; GPU usage evidenced or CPU fallback documented.

## Is it worth splitting? (short rationale)

Yes. The refactor spans configuration, three recognition engines, a fragile GPU/Metal path, GUI, and native build steps. Splitting gives: (1) isolation of the risky Metal work so it can't block a working CPU build, (2) per-step acceptance gates that catch regressions early, (3) smaller diffs an AI agent can reason about reliably, and (4) a clear "good enough to ship" line (M2/M3) independent of GPU success (M4).

## Effort / risk snapshot

| Phase | Task | Risk | Note |
|------|------|------|------|
| 1 | T01 | Low | Pure config; backward compat is the only trap. |
| 2 | T02 | Low–Med | Standard Whisper on CPU; audio format conversion is the main gotcha. |
| 3 | T03 | Low | Wiring + fallbacks. |
| 4 | T04 | **High** | Metal on Intel+AMD is under-tested; needs runtime verification + fallback. |
| 5 | T05 | Med | UI threading; don't block the Tk main loop on model load. |
| 6 | T06 | Med | Native build of pywhispercpp with Metal; model downloads. |
| 7 | T07 | Low | Verification only, but it is the ship gate. |
