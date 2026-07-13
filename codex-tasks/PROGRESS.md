# PROGRESS — single source of truth for resuming

> **Codex: update this file after finishing each task, BEFORE stopping.**
> **When resuming (especially in a NEW chat), READ THIS FILE FIRST.**

## Current status

- **Phase:** 6 — deps, Metal build, models
- **Last completed task:** `T05_gui_wiring`
- **NEXT TASK:** `T06_deps_build_models`
- **Active branch:** `feat/T05-gui-wiring`
- **Last updated:** 2026-07-13

## Task checklist

| Task | Description | Status | Branch | Verified? |
|------|-------------|--------|--------|-----------|
| T01  | Config foundation | Done | n/a | Config yes; Vosk model present |
| T02  | CPU engines (openai + faster-whisper) | Done | n/a | Yes |
| T03  | Factory + fallback chain | Done | `feat/T03-factory-fallback` | Yes (`5393932`) |
| T04  | GPU engine: whisper.cpp + Metal (AMD RX 580) | code complete — on-device Metal/GPU verification DEFERRED to T06/T07 | `feat/T04-whispercpp-metal` | Offline checks only; Metal not verified |
| T05  | GUI wiring: selectors + real status bar | Done | `feat/T05-gui-wiring` | Offline GUI/fallback smoke checks (`3e72596`) |
| T06  | Deps, macOS Metal build, models | Not started | | |
| T07  | Verification & acceptance (ship gate) | Not started | | |

Status values: `Not started` → `In progress` → `Done`.

## Handoff notes (most recent last)

_(Codex appends one short entry per completed task: what changed, how verified, commit hash.)_

- 2026-07-13: T01 added Whisper backend/device/model config fields and example config values; verified config compatibility/round-trip, GUI import, py_compile, and Vosk model presence (no commit: workspace is not a git repo).
- 2026-07-13: T02 added CPU-only openai-whisper and faster-whisper recognizers with guarded imports; verified both plus Vosk on the bundled Russian sample (no commit: workspace is not a git repo).
- 2026-07-13: Git initialized; source-only baseline committed on `main` as `8320976` (`baseline before codex-tasks`); next task branch is `feat/T03-factory-fallback`.
- 2026-07-13: T03 added `create_recognizer(...)` with requested-engine selection and CPU/Vosk fallback chain; verified fake failure paths and real cached engine smoke checks (`5393932`).
- 2026-07-13: T04 added optional `WhisperCppRecognizer` and factory wiring (`2750bf0`); pywhispercpp built with `GGML_METAL=ON` after forcing Python 3.11 and adding local rpath, but ggml model download from Hugging Face CDN returns 502 so real Metal/RX 580 verification is still blocked.
- 2026-07-13: T04 is code complete offline on `feat/T04-whispercpp-metal`; on the AMD RX 580 later verify exactly: `ggml_metal_init` picks the RX 580, GPU activity appears in Activity Monitor, and the Russian sample transcribes successfully.
- 2026-07-13: T05 wired GUI engine/backend/model selectors through the recognizer factory, added background reload + fallback warning/status labels, and verified py_compile, GUI import, selector helper, and fake fallback reload smoke checks (`3e72596`).

## How to resume in a NEW chat (paste this prompt)

```
You are continuing the "Russian Voice Translator" refactor described in the codex-tasks/ folder.
Before writing any code:
1. Read codex-tasks/PROGRESS.md to find the NEXT TASK.
2. Read codex-tasks/AGENTS.md and codex-tasks/00_context_and_constraints.md.
3. Read the next task file under codex-tasks/tasks/.
4. Confirm the branch/repo state noted in PROGRESS.md.
Then do ONLY that one task, run its Acceptance checklist, update PROGRESS.md,
print a handoff, and STOP for my confirmation before the next task.
The next task per PROGRESS.md is: T06_deps_build_models.
```
