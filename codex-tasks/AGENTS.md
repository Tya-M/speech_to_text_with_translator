# AGENTS.md — How Codex must work with the `codex-tasks/` folder

This file is authoritative for agent behavior in this folder. Follow it exactly.

## Golden rules

1. **Read `00_context_and_constraints.md` first.** Its HARD constraints are non-negotiable — especially: `faster-whisper` and `openai-whisper` stay CPU-only on this machine; the ONLY real GPU path is `whisper.cpp` built with Metal for the AMD RX 580.
2. **Read `ROADMAP.md`** for phase order (M0→M7), the dependency graph, and where the high-risk work is (T04, GPU/Metal).
3. **Execute tasks in `tasks/` strictly in numeric order (T01 → T07).** Each task lists its own `Depends on`; never start a task before its dependencies are done.
4. **Work exactly ONE task per run.** One dedicated branch per task (e.g. `feat/T01-config`), small scoped commits, no drive-by refactors.
5. **Run the task's Acceptance checklist before doing anything else.** Advance only when every box passes.
6. **Never break Vosk.** It is the known-good baseline and final fallback. The app must always start even if optional Whisper deps are missing (guard imports with feature flags).
7. **For T04, do not claim GPU acceleration without runtime evidence** (a `ggml_metal_init` log line naming the AMD RX 580 + visible GPU activity). If Metal doesn't offload, fall back to CPU and record it (see `tasks/T07_verification_acceptance.md`).
8. **When a task is ambiguous, prefer existing interfaces** (`BaseRecognizer`, `RecognitionResult`, `AppConfig`) and mirror `recognition/vosk_engine.py` instead of inventing patterns.

## STOP GATE after every task (MANDATORY)

Codex must PAUSE between subtasks so the user stays in control (and so work can continue in a fresh chat if this one fills up).

When a task's Acceptance checklist fully passes:
1. **Update `PROGRESS.md`**: mark the task `Done`, set the next task as current, and record the branch/commit and date.
2. **Print a short handoff**: what changed, how it was verified, the exact next task, and a ready-to-paste resume prompt.
3. **STOP. Do NOT start the next task.** Wait for the user to explicitly tell you to continue (e.g. "continue" / "продолжай" / "go T0X").

If the checklist does NOT fully pass, stay on the current task and keep fixing it — do not advance and do not mark it Done.

## Resuming in a NEW chat (when the current chat overflows)

Do these steps in order before touching code:
1. **Read `PROGRESS.md` FIRST** — it is the single source of truth for what is done and what is next.
2. Read `AGENTS.md` (this file) and `00_context_and_constraints.md`.
3. Read the next task file named in `PROGRESS.md` (e.g. `tasks/T03_factory_fallback.md`).
4. Check out / confirm the branch noted in `PROGRESS.md`, and verify the repo state matches (run the previous task's acceptance checks if in doubt).
5. Do ONLY that one task, then apply the STOP GATE again.

Never assume progress from memory or chat history — always trust `PROGRESS.md`.
