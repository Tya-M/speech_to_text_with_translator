# PROGRESS — single source of truth for resuming

> **Codex: update this file after finishing each task, BEFORE stopping.**
> **When resuming (especially in a NEW chat), READ THIS FILE FIRST.**

## Current status

- **Phase:** 2 — CPU Whisper engines complete
- **Last completed task:** `T02_cpu_engines`
- **NEXT TASK:** `T03_factory_fallback`
- **Active branch:** `feat/T03-factory-fallback`
- **Last updated:** 2026-07-13

## Task checklist

| Task | Description | Status | Branch | Verified? |
|------|-------------|--------|--------|-----------|
| T01  | Config foundation | Done | n/a | Config yes; Vosk model present |
| T02  | CPU engines (openai + faster-whisper) | Done | n/a | Yes |
| T03  | Factory + fallback chain | Not started | | |
| T04  | GPU engine: whisper.cpp + Metal (AMD RX 580) | Not started | | |
| T05  | GUI wiring: selectors + real status bar | Not started | | |
| T06  | Deps, macOS Metal build, models | Not started | | |
| T07  | Verification & acceptance (ship gate) | Not started | | |

Status values: `Not started` → `In progress` → `Done`.

## Handoff notes (most recent last)

_(Codex appends one short entry per completed task: what changed, how verified, commit hash.)_

- 2026-07-13: T01 added Whisper backend/device/model config fields and example config values; verified config compatibility/round-trip, GUI import, py_compile, and Vosk model presence (no commit: workspace is not a git repo).
- 2026-07-13: T02 added CPU-only openai-whisper and faster-whisper recognizers with guarded imports; verified both plus Vosk on the bundled Russian sample (no commit: workspace is not a git repo).
- 2026-07-13: Git initialized; source-only baseline committed on `main` as `8320976` (`baseline before codex-tasks`); next task branch is `feat/T03-factory-fallback`.

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
The next task per PROGRESS.md is: T03_factory_fallback.
```
