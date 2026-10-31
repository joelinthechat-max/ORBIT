# Local model setup (v0.5; weights are not included)

The default mode is offline and model-free. ORBIT ships no checkpoint/projector weights and downloads none. The language and vision roles are independently configured loopback OpenAI-compatible `/v1` services. Read `DOCUMENTATION/V0.5_TECHNICAL_RESEARCH.md` for backend/format references and `DOCUMENTATION/HARDWARE_COMPATIBILITY.md` for measured versus untested facts.

## External local service

Obtain the model and runtime from sources you trust. Verify the exact model license, architecture, tokenizer/template, quantization, processor/projector needs, context and CPU requirements. Store models under this folder and configure the exact served ID, base URL, backend, format, quantization and context in the Models panel. Endpoints must be loopback (`127.0.0.1`, `localhost` or `::1`). ORBIT probes `/models` and reports endpoint reachability separately from an exact ID match. An endpoint response is not proof of image capability or successful inference.

## Optional managed llama.cpp process

For a supported user-supplied `llama-server`, configure the server executable in the matching USB runtime tree (or use its explicit USB-relative path), a `GGUF` model file under `MODELS/`, a supported alias, context/thread bounds and a loopback `/v1` base URL. Vision may require a user-supplied, compatible `mmproj` file. Start/stop is explicit in the dashboard. ORBIT invokes the executable without a shell, downloads no binary/weights, rejects paths outside the project, sets CPU-only default flags, binds to loopback and checks the served alias. The adapter supports a narrow llama.cpp command/API contract; other architectures/backend-specific flags may not work. Do not infer support for all GGUF files or vision projectors.

The automated process-manager smoke test used a fake API server and a placeholder GGUF path only. It validated process control/health/alias checks, not parsing weights, inference quality, cancellation of an in-flight generation, model memory or compatibility. No actual model was available during this build.

## Planning, vision and safety

An enabled language model can propose a multi-step JSON plan drawn only from `/api/actions`. The application validates action IDs, schemas, paths, dependencies, expected outcomes and Class A/B/C rules before saving it. Model text never bypasses approvals or invokes a shell. On network/inference failure, the engine records the error and uses only its limited deterministic fallback; malformed/unsafe JSON is rejected.

The vision adapter accepts bounded screenshots, resizes before encoding and validates structured labels/coordinates/confidence. Its observations currently feed the dashboard/recent context only. A confidence threshold, automatic recapture/cropping, OCR/accessibility fallback, autonomous visual verification and closed-loop adaptive replanning are not implemented. Do not treat vision output as proof that an external UI action succeeded.

## Hardware

The 4 GB target remains unverified. Model weight-file size is not peak RAM. Include Python, SQLite, OS, browser, runtime, context/KV cache, model buffers and images. Only one managed inference process is started by ORBIT at a time, but externally managed servers may still occupy memory. Resource status is best effort and null where the host provides no usable measure. Benchmark the exact model/backend/context on the intended hardware; do not promise simultaneous language+vision operation or a token/s speed.
