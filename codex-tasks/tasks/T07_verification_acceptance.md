# T07 — Verification & acceptance (ship gate)

- **Phase:** 7
- **Depends on:** T01–T06
- **Risk:** Low (verification only, but it is the gate)

## Objective

Run the full acceptance matrix, prove no Vosk regression, and capture evidence of GPU usage (or document the CPU-fallback decision honestly).

## Acceptance matrix (engine × device)

| Engine / backend | Device | Expected |
|---|---|---|
| Vosk | CPU | Unchanged real-time RU recognition |
| Whisper / openai | CPU | RU transcript, `small` |
| Whisper / faster | CPU int8 | RU transcript, `small`, lower memory |
| Whisper / whisper_cpp | Metal (AMD RX 580) | RU transcript + logged Metal device + GPU activity |
| Whisper / whisper_cpp | CPU fallback | RU transcript when Metal unavailable, no crash |

## Steps

1. Execute every row of the matrix; record transcript quality and rough speed (xRT) per row.
2. For the GPU row, capture evidence: the `ggml_metal_init` log line naming the AMD RX 580 AND a screenshot/observation of Activity Monitor GPU history rising during recognition.
3. Force failure cases: bad model path, missing dependency, `use_gpu=True` with Metal disabled — confirm the T03 fallback chain and GUI messaging.
4. Confirm config persistence across restarts and that old configs still load (T01).
5. Confirm the app starts with only Vosk deps installed (extras removed).

## Ship decision

- **M7 pass (ideal):** GPU row shows verified Metal offload on the RX 580.
- **M7 conditional pass (acceptable):** if Metal underperforms/does not offload on this Intel+AMD box, ship with `faster-whisper` CPU `int8` `small` as default and document the finding. Do NOT label output as GPU-accelerated unless verified.

## Acceptance checklist

- [ ] All matrix rows pass (or are documented as conditional).
- [ ] GPU usage evidenced OR CPU-fallback decision documented with data.
- [ ] Fallback chain verified for all forced-failure cases.
- [ ] No Vosk regression.
- [ ] Old and new `config.json` both load.
- [ ] App starts with only Vosk deps present.

## Deliverables

- A short `VERIFICATION.md` (or PR description) with per-row results, speed numbers, and GPU evidence or the documented CPU decision.

## Stop gate & handoff (MANDATORY)

This is the final task. When its Acceptance checklist fully passes:
1. Update `../PROGRESS.md`: mark T07 `Done` and mark the project complete (all milestones through M7), record the final branch/commit and date.
2. Print a final handoff: the acceptance matrix results, GPU-usage evidence (or the documented CPU-fallback decision), and any follow-ups.
3. **STOP.** Do not start unrelated work. Wait for the user.

If the checklist does not fully pass, stay on this task; do not mark it Done.
