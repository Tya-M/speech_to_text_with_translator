# T07 Verification

Date: 2026-07-13
Branch: `feat/T07-verification`
Sample: `models/vosk-model-ru/decoder-test.wav` (7.08s, 8 kHz mono PCM16; repeated to 16 kHz for app recognizers)

## Environment

- Python venv: 3.11.15
- Optional deps present: `faster-whisper 1.2.1`, `openai-whisper 20250625`, `pywhispercpp 1.5.0`, `vosk 0.3.44`
- `pywhispercpp` rebuilt from source after forcing `DEBUG=0` and CMake Python executable to the venv Python.
- Native `_pywhispercpp.cpython-311-darwin.so` imports successfully after adding site-packages rpath.
- `_pywhispercpp` links `libggml-metal.0.dylib`.

## Matrix Results

| Engine | Device | Load | Transcribe | xRT | Result |
|---|---:|---:|---:|---:|---|
| Vosk | CPU | 89.581s | 2.018s | 0.285 | PASS |
| faster-whisper `small` int8 | CPU | 15.247s | 11.338s | 1.601 | PASS |
| openai-whisper `small` | CPU | 13.912s | 15.655s | 2.211 | PASS |
| whisper.cpp `small` | Metal (AMD Radeon RX 580) | 36.169s | 14.857s | 2.098 | PASS headless; Activity Monitor confirmation pending |

Transcript quality:

- Vosk: `родион потапыч высчитывал каждый новый вершок углубления и давно определил про себя`
- faster-whisper: `Родион Потапыч высчитывал каждый новый вершок углубления и давно определил про себя`
- openai-whisper: `Родион Потапыч высчитывал каждый новый вершок углубления и давно определил про себя`
- whisper.cpp: `Родион Потапыч высчитывал каждый новый вершок углубления и давно определил про себя.`

## whisper.cpp / Metal Status

`pywhispercpp` is importable, linked against Metal, and transcribed the bundled sample after `ggml-small.bin` was placed in `models/whisper-cpp`.

- Model file: `models/whisper-cpp/ggml-small.bin` (~465 MiB on disk).
- Metal selected device: `AMD Radeon RX 580`.
- Headless command used OpenMP guards: `KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1`.

Full init/system log:

```text
whisper_init_from_file_with_params_no_state: loading model from '/Applications/russian_voice_translator/models/whisper-cpp/ggml-small.bin'
whisper_init_with_params_no_state: use gpu    = 1
whisper_init_with_params_no_state: flash attn = 1
whisper_init_with_params_no_state: gpu_device = 0
whisper_init_with_params_no_state: dtw        = 0
ggml_metal_device_init: tensor API disabled for pre-M5 and pre-A19 devices
ggml_metal_library_init: using embedded metal library
ggml_metal_library_init: loaded in 0.041 sec
ggml_metal_rsets_init: creating a residency set collection (keep_alive = 180 s)
ggml_metal_device_init: GPU name:   MTL0
ggml_metal_device_init: GPU family: MTLGPUFamilyCommon3 (3003)
ggml_metal_device_init: simdgroup reduction   = false
ggml_metal_device_init: simdgroup matrix mul. = false
ggml_metal_device_init: has unified memory    = false
ggml_metal_device_init: has bfloat            = false
ggml_metal_device_init: has tensor            = false
ggml_metal_device_init: use residency sets    = true
ggml_metal_device_init: use shared buffers    = false
ggml_metal_device_init: recommendedMaxWorkingSetSize  =  8589.93 MB
whisper_init_with_params_no_state: devices    = 3
whisper_init_with_params_no_state: backends   = 3
whisper_model_load: loading model
whisper_model_load: n_vocab       = 51865
whisper_model_load: n_audio_ctx   = 1500
whisper_model_load: n_audio_state = 768
whisper_model_load: n_audio_head  = 12
whisper_model_load: n_audio_layer = 12
whisper_model_load: n_text_ctx    = 448
whisper_model_load: n_text_state  = 768
whisper_model_load: n_text_head   = 12
whisper_model_load: n_text_layer  = 12
whisper_model_load: n_mels        = 80
whisper_model_load: ftype         = 1
whisper_model_load: qntvr         = 0
whisper_model_load: type          = 3 (small)
whisper_model_load: adding 1608 extra tokens
whisper_model_load: n_langs       = 99
whisper_model_load: MTL0_Private total size =   487.01 MB
whisper_model_load: model size    =  487.01 MB
whisper_backend_init_gpu: device 0: MTL0 (type: 1)
whisper_backend_init_gpu: found GPU device 0: MTL0 (type: 1, cnt: 0)
whisper_backend_init_gpu: using MTL0 backend
ggml_metal_init: allocating
ggml_metal_init: found device: AMD Radeon RX 580
ggml_metal_init: found device: Intel(R) KBL Unknown
ggml_metal_init: picking default device: AMD Radeon RX 580
ggml_metal_init: use fusion         = true
ggml_metal_init: use concurrency    = true
ggml_metal_init: use graph optimize = true
whisper_backend_init: using BLAS backend
whisper_init_state: kv self size  =   18.87 MB
whisper_init_state: kv cross size =   56.62 MB
whisper_init_state: kv pad  size  =    4.72 MB
whisper_init_state: compute buffer (conv)   =   32.78 MB
whisper_init_state: compute buffer (encode) =   57.00 MB
whisper_init_state: compute buffer (cross)  =   16.59 MB
whisper_init_state: compute buffer (decode) =  183.83 MB
```

## Fallback / Compatibility

- Real factory fallback passed: requesting `whisper_cpp` failed on model download, then loaded `FasterWhisperRecognizer`.
- Current `config.json` loads.
- Old minimal config loads and fills new defaults.
- Config persistence round-trip passed.
- GUI import with Whisper deps hidden passed; optional flags became `False`.

## Manual Confirmation Still Required

- AMD RX 580 GPU activity in Activity Monitor during whisper.cpp recognition.
- Live transcription quality in the app window.
