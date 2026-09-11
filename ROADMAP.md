# Russian Voice Translator — Bug-Fix Roadmap

Audit date: 2026-09-11
Scope: current source, available logs, crash report, and existing tests.
This audit did not change application behavior.

## Priority order

### BUG-001 — Global dictation can crash in PyAudio/PortAudio (P0)

Status: confirmed by crash report and logs.

The macOS `pynput`/Quartz event callback calls `AudioCapture.start_capture()` synchronously. That reaches `pyaudio.open()` from inside the event-tap callback. The crash report shows:

`CGEventTap callback → PyAudio_OpenStream → EXC_BAD_ACCESS / SIGSEGV`

Evidence:

- `input_injection/dictation.py:205-215,224-230`
- `audio/capture.py:148-180`
- `report-110926_1411.txt:30,87-119`
- `voice_translator.log:30478-30480`

Planned fix:

- Make hotkey callbacks enqueue start/stop requests only.
- Handle all PortAudio operations on a dedicated audio-control worker.
- Move stop/close operations out of the event callback as well.
- Prefer keeping one stream open while dictation is enabled, or otherwise serialize stream lifecycles.
- Add a stress test for repeated hotkey press/release cycles.

Acceptance criteria: repeated dictation start/stop cycles do not terminate the subprocess; a failed audio open produces a normal error message instead of exit code `-11`.

### BUG-002 — Main-app recording loses the final unfinished phrase (P1)

Status: implemented locally; regression-tested.

GigaAM only emits a result after enough trailing silence or at the maximum utterance length. Stopping the main recording stops the capture and recognition thread but never flushes the recognizer’s pending buffer. Speech immediately before pressing Stop can therefore disappear.

Evidence:

- `recognition/gigaam_engine.py:176-238`
- `app/gui.py:924-946`

Planned fix:

- Add an explicit `flush()`/`finalize()` operation to the recognizer interface.
- Flush pending GigaAM audio before discarding the recognition thread.
- Add tests for stop-during-speech and stop-during-trailing-silence.

Acceptance criteria: speech captured before Stop is emitted once, including when no 1.5-second silence occurred.

### BUG-003 — Recording can remain visually active after a worker failure (P1)

Status: confirmed by control flow.

If `recognize_stream()` raises, `_recognition_loop()` logs the error and exits, but `_is_recording`, the record button, and the status remain active. Similarly, an unexpected audio-thread exit does not reset `_is_capturing`.

Evidence:

- `app/gui.py:1170-1185`
- `audio/capture.py:238-272`

Planned fix:

- Use a single failure path that stops capture, resets UI state, and reports the error.
- Set capture state false in the audio thread’s `finally` block.
- Add fault-injection tests for audio read and recognizer failures.

Acceptance criteria: any worker failure leaves the UI in READY/idle state and allows a new recording without restarting the app.

### BUG-004 — Dictation buffer and recognizer are not fully serialized (P1)

Status: confirmed race risk.

The collector thread appends to `_buffer` without the service lock while `_finish_recording()` copies and clears that same `bytearray`. Also, each completed utterance starts a new transcription thread against the same recognizer. Fast successive utterances can overlap, lose audio, or call a model concurrently when it is not thread-safe.

Evidence:

- `input_injection/dictation.py:239-267`

Planned fix:

- Make buffer ownership single-threaded or protect all accesses with a lock.
- Use one transcription queue/worker to preserve order and serialize model calls.
- Wait for or explicitly cancel pending work during shutdown.

Acceptance criteria: rapid consecutive utterances preserve audio and output order, and shutdown does not leave unfinished transcription work.

### BUG-005 — Clearing the transcript can be undone by delayed callbacks (P1)

Status: implemented locally; regression-tested.

`_clear_transcript()` clears the list and text widget but does not cancel the pending partial timer, clear `_pending_partial_text`, or invalidate translation futures. A delayed partial or translation can reappear after the user has pressed Clear, leaving the UI and `transcript` list inconsistent.

Evidence:

- `app/gui.py:702-753`
- `app/gui.py:794-825`
- `app/gui.py:1326-1330`

Planned fix:

- Cancel the partial timer and clear pending partial state.
- Add a transcript generation/token and ignore callbacks from older generations.
- Remove or invalidate translation marks when clearing.

Implemented fix:

- Clear cancels the partial timer, clears pending partial state, and drains
  queued recognition results.
- Recognition results carry the transcript generation from the producer;
  results from before Clear are ignored.
- Delayed translation callbacks verify both generation and entry membership
  before changing the UI.

Acceptance criteria: after Clear, no old partial or translation is inserted into the widget.

### BUG-006 — Microphone sensitivity control has no effect (P1)

Status: implemented locally; regression-tested.

The sensitivity slider updates and saves `config.sensitivity`, but the value is never read by audio capture, VAD, or recognition logic. The control appears functional while changing no behavior.

Evidence:

- `app/gui.py:267-274,1210-1215`
- `utils/config.py:31-34`
- No consumers found outside the setting handlers.

Planned fix:

- Define whether sensitivity is an input gain/display scaling/VAD parameter.
- Implement that behavior or remove the control and setting.
- Add a test proving the selected value affects the intended processing path.

Implemented fix:

- Sensitivity now controls bounded software gain on captured PCM16 audio
  (`1000` is neutral); values are clipped safely before reaching recognition.
- The main app and cursor dictation pass the setting into `AudioCapture`, and
  changing the slider updates an active capture.

Acceptance criteria: changing sensitivity has a documented, observable effect, or the misleading control is removed.

### BUG-007 — Inactive audio streams can cause a busy loop and stale state (P2)

Status: implemented locally; regression-tested.

`_capture_loop()` has no sleep or state transition when `_stream` exists but `is_active()` returns false. It can spin at high CPU usage. On read failure it exits without setting `_is_capturing` false, so callers may believe recording is still active.

Evidence:

- `audio/capture.py:238-272`

Planned fix:

- Treat an inactive stream as a terminal capture failure or wait briefly before retrying.
- Reset state in `finally` and notify the owner.
- Add tests for inactive streams and read failures.

Implemented fix:

- Inactive streams and unrecoverable read errors stop capture immediately and
  invoke an owner callback once.
- The main app routes that callback to its existing recording-failure reset
  path.

Acceptance criteria: no busy spin, and `is_capturing` becomes false after an unrecoverable stream failure.

### BUG-008 — Recognizer reload has lifecycle races and can destroy the working engine (P2)

Status: implemented locally; regression-tested.

The old recognizer is unloaded before the replacement has successfully loaded. A load failure leaves the application without the previously working recognizer. Reload completion also calls `root.after()` from a background thread without checking whether the window is still alive. The `EngineManager` switching flag is checked outside its lock, allowing two reload requests to pass the check concurrently.

Evidence:

- `app/gui.py:1261-1294`
- `utils/threading_utils.py:142-162`

Planned fix:

- Load and validate the replacement first, then atomically swap it in.
- Serialize reload requests under one lock or coalesce them.
- Guard UI callbacks during shutdown.

Implemented fix:

- A replacement recognizer is loaded before the current one is unloaded; a
  failed replacement leaves the working recognizer active.
- `EngineManager` checks and sets its switching flag under the same lock.
- Reload completion skips UI scheduling during shutdown and tolerates a window
  closing while the worker is finishing.

Acceptance criteria: a failed reload preserves the previous recognizer; closing during reload produces no background traceback or stale UI update.

### BUG-009 — Translator executor cannot be reused after unload (P2)

Status: implemented locally; regression-tested.

`Translator.unload()` shuts down the executor permanently. Reusing the instance after a context-manager exit or unload causes `translate_async()` to raise `RuntimeError: cannot schedule new futures after shutdown`.

Evidence:

- `translation/translator.py:107-113,213-219,259-264`

Planned fix:

- Either make `Translator` single-use and enforce that contract, or recreate the executor on the next `load()`.
- Make unload wait/cancel policy explicit.

Implemented fix:

- Unload cancels pending work and releases the executor.
- The next load or asynchronous translation lazily creates a fresh executor.

Acceptance criteria: reload/reuse behavior is deterministic and covered by tests.

### BUG-010 — Configuration accepts unsafe audio/cache values (P2)

Status: implemented locally; regression-tested.

`sample_rate`, `device_index`, `translation_cache_size`, and window dimensions are not validated. Invalid values can reach PortAudio or create a zero-sized translation cache, whose first insertion can fail. Numeric device indices are also inherently unstable across macOS device changes.

Evidence:

- `utils/config.py:31-57,59-112`
- `audio/capture.py:173-179`
- `translation/translator.py:51-62`

Planned fix:

- Validate and normalize numeric ranges/types.
- Resolve the selected microphone by stable name/identity, then refresh its current index.
- Define behavior for cache size zero.

Implemented fix:

- Numeric audio, device, window, cache, and timing values are normalized to
  safe ranges with deterministic defaults for malformed input.
- `AudioCapture` validates its native-facing sample rate, chunk size, and
  device index as a second defensive boundary.
- `TranslationCache` clamps zero or invalid capacity to one.

Acceptance criteria: malformed configuration falls back predictably and never reaches native audio APIs with invalid parameters.

### BUG-011 — Transcript UI trimming is inconsistent with export/copy data (P2)

Status: implemented locally; regression-tested.

The text widget is trimmed to approximately 500 lines, but `self.transcript` retains every entry. The visible transcript, copied text, JSON export, TXT export, and memory usage therefore diverge during long sessions.

Evidence:

- `app/gui.py:716,777-793`
- `app/gui.py:1340-1356,1358-1377,1380-1402`

Planned fix: choose one policy—retain all data and make the UI explicitly a viewport, or prune the model and document that exports contain only the retained window.

Implemented fix: retain the complete transcript in both the model and the
scrollable text widget; the old automatic text trimming is now disabled, so
copy and export scope matches what remains visible in the session.

Acceptance criteria: visible, copied, and exported transcript scope is predictable and tested after more than 500 lines.

### BUG-012 — SRT export uses fabricated fixed three-second timings (P3)

Status: implemented locally; regression-tested.

Every subtitle starts at the recognition timestamp and ends exactly three seconds later, regardless of actual speech duration or neighboring entries. Dense speech produces overlapping/inaccurate subtitles.

Evidence:

- `app/gui.py:1403-1426`

Planned fix: retain segment duration/timing metadata from capture, or label the export as approximate and derive non-overlapping timings from adjacent entries.

Implemented fix: SRT export now uses relative approximate timings derived from
neighboring recognition timestamps, enforces minimum subtitle durations, and
prevents overlaps when entries arrive close together.

Acceptance criteria: exported SRT timings do not overlap for normal sequential recordings and are clearly marked approximate if exact timings are unavailable.

### BUG-013 — Parakeet cursor dictation recognizes only English (P1)

Status: implemented locally; requires real-device verification.

The Parakeet Unified EN model has an English-only vocabulary, and cursor
dictation previously sent each utterance only to the selected Parakeet model.
Russian speech therefore could not be typed under the cursor when Parakeet was
selected, even though the main dictation workflow could use Russian recognition
separately.

Implemented fix:

- When Parakeet is selected for cursor dictation, load GigaAM alongside it.
- Run both recognizers for each completed utterance.
- Prefer the GigaAM result when it contains Cyrillic; otherwise use Parakeet's
  English result.
- Fall back to English-only Parakeet operation if GigaAM is unavailable.
- Label the option and command-line help as Russian + English.

Acceptance criteria: separate Russian and English utterances made with the
Parakeet option are recognized and typed into the cursor without changing the
selected option. Mixed-language phrases within one utterance remain dependent
on the two models' whole-utterance output and are not guaranteed to be split.

## Verification debt

- `venv/bin/python -m unittest tests.test_audio_capture -v`: passes.
- `venv/bin/python -m compileall ...`: passes.
- `git diff --check`: passes.
- The complete test command is `python -m pytest` after installing `requirements-dev.txt`.
- The current virtual environment does not yet contain the newly declared `pytest` dependency, so the complete suite still needs one dependency installation.
- Existing tests still do not cover full dictation lifecycle, recognizer reload
  fault injection, or exact real-audio SRT timing.

## Suggested implementation sequence

1. BUG-001 and BUG-004: make dictation audio/model lifecycle safe.
2. BUG-002 and BUG-003: make main recording lossless and self-healing.
3. BUG-013: verify bilingual cursor dictation on the target Mac and microphone.
4. BUG-005 and BUG-008: eliminate stale asynchronous UI updates and reload races.
5. BUG-006 and BUG-010: make settings real and validate native-facing values.
6. BUG-007, BUG-009, BUG-011, and BUG-012: harden long-running sessions and exports.
7. Add regression tests for every fixed item and make the virtual-environment test command reproducible — documented via `requirements-dev.txt` and `pytest.ini`.
