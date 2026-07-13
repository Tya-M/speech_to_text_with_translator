# Russian Voice Translator — Codex task package

**Цель пакета (RU):** превратить один большой рефактор (добавление движков Whisper + GPU‑ускорение на AMD RX 580 через Metal + GUI + сборка) в набор изолированных подзадач с дорожной картой. Codex выполняет по одной подзадаче и останавливается, ожидая команды пользователя. Прогресс фиксируется в `PROGRESS.md`, поэтому работу можно продолжить в новом чате, если текущий переполнится.

**Package goal (EN):** break the large refactor into small, independently verifiable subtasks driven by a roadmap. The agent does ONE task at a time and pauses for user confirmation; progress is tracked in `PROGRESS.md` so work can resume in a fresh chat.

## Read order for the agent

1. `AGENTS.md` — how to work here (rules + STOP GATE + how to resume in a new chat).
2. `PROGRESS.md` — what is done and what the NEXT task is. **On resume, read this first.**
3. `00_context_and_constraints.md` — shared context + HARD constraints.
4. `ROADMAP.md` — phases, milestones, dependency graph, risks.
5. `tasks/T0X_*.md` — the current subtask.

## Working loop (per subtask)

1. Pick the NEXT task from `PROGRESS.md`.
2. Read that task file; do only that task on its own branch.
3. Run the task's Acceptance checklist.
4. Update `PROGRESS.md` (mark Done, set next task, note branch/commit) and print a handoff.
5. **STOP and wait** for the user's "continue" command before the next task.

## Resuming in a new chat

If this chat fills up, open a new one and paste the resume prompt at the bottom of `PROGRESS.md`. The agent will read `PROGRESS.md`, `AGENTS.md`, `00_context_and_constraints.md`, and the next task file, then continue from exactly where you left off.

## Recommended git hygiene

- One branch per task, e.g. `feat/T01-config`, merged only after its acceptance checklist passes.
- Small commits scoped to the task. No drive-by refactors.
- Tag a milestone commit at the end of each phase (see `ROADMAP.md`).

## File map

```
codex-tasks/
  README.md                     <- this file
  AGENTS.md                     <- agent behavior rules + STOP GATE + resume procedure
  PROGRESS.md                   <- live state: done / next task / resume prompt (READ FIRST on resume)
  ROADMAP.md                    <- phases, milestones, dependency graph, risks
  00_context_and_constraints.md <- shared context + HARD constraints
  tasks/
    T01_config.md               <- config schema for engine/backend/device/models
    T02_cpu_engines.md          <- openai-whisper (CPU) + faster-whisper (CPU int8)
    T03_factory_fallback.md     <- engine factory + graceful fallback chain
    T04_gpu_whispercpp_metal.md <- whisper.cpp + Metal (the AMD RX 580 GPU path)
    T05_gui_wiring.md           <- engine/backend/model selectors + real status bar
    T06_deps_build_models.md    <- requirements, macOS build of pywhispercpp, models
    T07_verification_acceptance.md <- end-to-end verification + acceptance gate
```

## One-paragraph summary of the technical reality

The target machine is macOS on a Hackintosh (x86_64) with an **AMD Radeon RX 580** and **no NVIDIA/CUDA**. `faster-whisper`/CTranslate2 is CPU-or-CUDA only, so it **cannot** use the AMD GPU and must stay on CPU. `openai-whisper` (PyTorch) has no GPU on Intel macOS. The **only** real GPU-acceleration path is **`whisper.cpp` built with the Metal backend**, which can target the AMD GPU — with the caveat that Metal is primarily tuned for Apple Silicon, so runtime GPU-offload verification and a clean CPU fallback are mandatory.
