# ORBIT v0.6.1 — offline-first portable assistant

ORBIT is a local dashboard and modular task runner for bounded workspace operations, optional local-model planning, browser interaction and user-approved desktop controls. The model-free development mode runs with no model weights, no cloud service, and no host Python installation. All required ORBIT state (configuration, SQLite memory, workspace, logs and backups) resides under the extracted ORBIT directory.

**This build is not a generally autonomous computer agent.** A desktop action is recorded as sent, then a fresh task-bound screenshot is captured for user review. An optional local language model may provide an advisory outcome assessment; it cannot mark a task verified or authorize another action. It may also propose a registry-validated revised plan after failure/unexpected state, but proposals are displayed only and do not execute. The user must personally confirm visible success; no uncertain action is automatically retried. Class A autonomy remains bounded to eligible registered workspace operations. No Windows run or 4 GB device benchmark has been performed.

## Start

1. Extract the full `ORBIT` folder to a writable USB drive. Keep its internal layout intact.
2. On Windows x64, run `run_windows.bat`. On Linux x86_64 GNU, run `./run_linux.sh`. These use the included CPython 3.12.15 runtimes; they do not invoke host Python or install software globally.
3. Open the printed loopback URL, normally `http://127.0.0.1:8765`. ORBIT binds to loopback only. Stop with Ctrl+C and let in-flight requests finish before safely ejecting the drive.

The USB must be writable and have free space. The Linux runtime needs a compatible glibc/system loader. Windows, ARM, macOS and Linux musl were not tested/supported by these bundled runtimes. See [`USB_PORTABILITY.md`](DOCUMENTATION/USB_PORTABILITY.md).

## Capabilities

- SQLite task/memory with restart recovery, integrity checks, backup/restore and explicit approval for retained preferences/knowledge.
- A validated action registry for bounded workspace operations; exact task-step dependencies, verification, A/B/C risk metadata and parameter-bound expiring approvals; no shell-command action.
- Optional OpenAI-compatible loopback language/vision endpoints. Model plans are proposals validated against the live action catalogue; model weights are not supplied.
- Optional Playwright Chromium automation: user-enabled navigation, page reading, semantic click/fill, tab, scroll, screenshot and form-submit actions, safe dialog dismissal, and an isolated ORBIT browser profile. Password/file-input fields are denied; downloads are disabled. Page content is untrusted.
- Optional desktop adapter: real X11 screenshot/window/mouse/keyboard/clipboard functions when the interactive display and host tools permit them; PyAutoGUI/Pillow support is vendored for Windows but is untested there. Wayland restrictions are not bypassed. A user-maintained application ID → exact executable/shortcut allowlist gates application launch.
- Resource and USB storage status where measurable; bounded autonomous Class A workflow with action/time limits, pause/cancel and an emergency-stop latch.
- Task-bound desktop observation persistence, explicit user result confirmation, advisory-only model outcome assessment, and model-proposed adaptive replanning that stays non-executable until the user creates a separate task and grants any required approvals.

Desktop input, Browser automation, local inference, and autonomous mode default to disabled. Review the controls before enabling them. External website actions and Class B/C steps require fresh interactive confirmation. Do not expose this development server on a network; it has no login/authentication or encrypted local storage.

## Source checkout and portable package

A source-only Git checkout may omit the large prebuilt `RUNTIME/` and `VENDOR/` binaries to avoid oversized Git objects. Use the complete `ORBIT-v0.6-PORTABLE.zip` release asset for the turnkey USB package; it includes both platform runtimes and vendored dependencies. Chromium browser binaries and model weights are still not included.

## Browser setup

ORBIT bundles the pinned Playwright Python client and platform-specific dependencies in `VENDOR/`. It does **not** bundle Chromium. Optionally install the Playwright-selected browser build into the USB runtime directory using `setup_browser_linux.sh` or `setup_browser_windows.bat`; this requires Internet at setup time and is user-triggered, without administrator installation. Alternatively configure a compatible existing Chromium/Edge executable. Browser and browser-binary licensing/runtime requirements are documented in [`VENDOR/README.md`](VENDOR/README.md) and [`V0.5_TECHNICAL_RESEARCH.md`](DOCUMENTATION/V0.5_TECHNICAL_RESEARCH.md).

## Local model setup

ORBIT does not download weights. To use local inference, separately obtain a model and compatible runtime, verify the model's license and architecture, put GGUF model/projector files under `MODELS/`, configure the language/vision roles, and start an OpenAI-compatible loopback server. An optional manager can start/stop a user-supplied `llama-server` process for user-supplied GGUF files; it downloads nothing. A successful fake-server lifecycle test does **not** count as model inference. No real model weights or genuine inference were available in this build. See [`MODELS/README.md`](MODELS/README.md).

The target of 4 GB RAM is a design constraint, not a compatibility claim. Real OS/app/model memory can be substantially larger than weight files. Resource values are reported only when measurable; null means unavailable. Test the exact weights, quantization, context, browser and device.

## Tests and limits

Run the automated suite with the bundled runtime:

```sh
RUNTIME/LINUX/python/bin/python3.12 -m unittest discover -s tests -v
```

Optional real-environment scripts:

```sh
RUNTIME/LINUX/python/bin/python3.12 tests/integration_v05_browser.py
RUNTIME/LINUX/python/bin/python3.12 tests/integration_v05_desktop.py
RUNTIME/LINUX/python/bin/python3.12 tests/integration_v05_http.py
RUNTIME/LINUX/python/bin/python3.12 tests/integration_v05_llama_manager.py
RUNTIME/LINUX/python/bin/python3.12 tests/integration_v06_observation.py
```

The live tests use the sandbox's X11 session and a disposable localhost browser fixture. The v0.6 HTTP test demonstrates a four-pixel pointer move, fresh task-bound screenshot, no-resend guard, user confirmation and persistence after restart; the browser test demonstrates real Playwright operations against a localhost fixture. They do **not** demonstrate the requested text-editor end-to-end task, external-web research, genuine model inference, automatic vision recovery, Windows behavior, physical USB removal, or 4 GB hardware. See [`PROJECT_STATUS.md`](DOCUMENTATION/PROJECT_STATUS.md) and [`HANDOFF_TO_NEXT_AGENT.md`](DOCUMENTATION/HANDOFF_TO_NEXT_AGENT.md) for exact outcomes and remaining work.
