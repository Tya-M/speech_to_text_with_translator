# T06 — Dependencies, macOS build (Metal), and models

- **Phase:** 6 (author early; T02 & T04 need it to run)
- **Depends on:** none to author; pairs with T02/T04
- **Risk:** Medium (native build + downloads)

## Objective

Make the optional Whisper dependencies installable, build `pywhispercpp` with Metal on macOS, and set up model download — without making the base app hard-depend on any of them.

## Files to touch

- `requirements.txt` (optional extras; keep base deps working without them)
- `README.md` (build/setup docs)
- optionally a `scripts/setup_whisper.sh` helper

## Steps

1. Add optional extras (documented as optional, guarded in code):
   - `openai-whisper`
   - `faster-whisper`
   - `pywhispercpp`
   - `numpy` (if not already present)
2. macOS prerequisites (document in README):
   - Xcode Command Line Tools.
   - `brew install cmake ninja ffmpeg`.
3. **Build pywhispercpp WITH Metal** (Metal is enabled by default when building whisper.cpp on Apple platforms, so build from source rather than using a CPU-only wheel):
   ```bash
   pip install --no-binary :all: pywhispercpp
   # or, from git:
   pip install git+https://github.com/absadiki/pywhispercpp
   ```
   Verify at import/load time that a Metal device initializes (see T04).
4. **Fallback build — whisper.cpp CLI with Metal** (used by the optional CLI engine in T04):
   ```bash
   git clone https://github.com/ggml-org/whisper.cpp
   cmake -B build -DGGML_METAL=1 whisper.cpp
   cmake --build build -j --config Release
   ```
   (Vulkan alternative, only if Metal fails: `-DGGML_VULKAN=1` with MoltenVK.)
5. **Models:**
   - whisper.cpp ggml models → `whisper_cpp_model_dir` (pywhispercpp auto-downloads by name, or `whisper.cpp/models/download-ggml-model.sh small`). Default `small`; allow `medium`; offer `q5_0` quantized variants to cut memory.
   - openai-whisper / faster-whisper models download to their configured cache dirs.
   - Leave Vosk model paths untouched.

## Deliverables

- `requirements.txt` with optional extras.
- README section: prerequisites, Metal build, model download, verification.
- optional `scripts/setup_whisper.sh`.

## Acceptance checklist

- [ ] Base app installs and runs with ONLY Vosk deps (extras absent).
- [ ] Following the README on a clean macOS setup installs deps and downloads models.
- [ ] pywhispercpp import succeeds and (on the target machine) reports a Metal device.
- [ ] Documented commands are copy-paste correct.

## Risks & notes

- Network access may be required for model download; document offline placement of ggml files as an alternative.
- Do not pin versions so tightly that the build breaks; document the versions actually validated.

## Stop gate & handoff (MANDATORY)

When this task's Acceptance checklist fully passes:
1. Update `../PROGRESS.md`: mark this task `Done`, set the next task as current, record the branch/commit and date, and append a one-line handoff note.
2. Print a short handoff: what changed, how it was verified, the exact next task, and a ready-to-paste resume prompt.
3. **STOP. Do not start the next task.** Wait for the user to explicitly say to continue (e.g. "continue" / "продолжай").

If the checklist does not fully pass, stay on this task; do not advance and do not mark it Done.
