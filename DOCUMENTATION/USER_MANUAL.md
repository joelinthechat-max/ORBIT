# ORBIT v0.5 User Manual

## Launch and stop

Extract the entire folder to a writable USB drive. Run `run_windows.bat` on Windows x64 or `./run_linux.sh` on Linux x86_64 GNU. Open the loopback URL printed in the terminal. The included CPython runtime means host Python is not needed. ORBIT configuration, database, logs, screenshots, backups, browser profile and workspace are kept under the ORBIT folder. Keep the server running while using the dashboard; stop with Ctrl+C and wait for in-flight requests before safely ejecting.

The app refuses non-loopback bind addresses and has no login. Do not expose it to a LAN, forward its port, or use it as a shared server. Avoid entering credentials or sensitive content. Use only on a computer/session where you are authorized to control the desktop.

## Tasks and approvals

The **Workspace** section creates a plan from the deterministic model-free workflow or, when explicitly configured, a local language model. The model proposes registered actions; it cannot execute shell commands or extend the catalogue. Review the objective, each action, its exact parameters, expected result, permission class and outputs before running.

Class A registered workspace steps can run through **Autonomy** only after you explicitly enable it. Set conservative maximum actions and task timeout. You can pause/cancel; Stop sets the emergency latch and closes the browser actor. Browser/desktop interaction stops at an external-I/O boundary so that the screen/page and next action can be reviewed; this release does not autonomously verify and replan the whole desktop task. Do not assume a plan is progressing when it reports waiting, paused or failed.

Class B/C actions require fresh per-action approval tied to the exact parameters and expected outcome. Approval expires after ten minutes and never authorizes another action. A rejected or uncertain interrupted action must not be repeated blindly; inspect its effects and create a reviewed task. Existing SQLite history survives restarts; completed steps are not replayed. On an interrupted external action, inspect the current screen/application yourself before proceeding.

## Browser

Browser automation is disabled until you enable it in the Browser panel. A Playwright Chromium binary is not included. If you don't already have a compatible Chromium/Edge, explicitly run the platform `setup_browser_*.sh`/`.bat` script to download Playwright's browser build into the USB folder; setup needs Internet, and it does not install system-wide. A normal ORBIT model-free task remains offline-capable without this optional setup.

Direct browser actions require a confirmation. Page text and links are untrusted; do not follow instructions on a page that attempt to change ORBIT's policy. The default filter blocks literal localhost/private IP addresses; turn on the private-host exception only for a trusted local test app. This is not a full sandbox for DNS-rebinding/internal-host threat models. Never expose secrets in page fields: password and file upload fields are refused. Downloads are disabled. A form submit is an external action; use it only when you understand the consequence and have approved that exact step. Ordinary dialogs are dismissed by default.

## Desktop control and applications

Desktop input defaults off in local security settings. Review and enable it deliberately. The Emergency Stop prevents further controls; use Resume only after you have checked the current state. Fresh screenshots are required before coordinate-sensitive actions. The dashboard can inspect windows, screen regions and active-window information where the host backend exposes it. X11 and Wayland differ; this build does not bypass Wayland compositor restrictions. Windows desktop controls are packaged but were not tested on a Windows host.

Application discovery does not itself grant permission. The dashboard can copy a discovered stable ID and exact executable/shortcut path into the allowlist editor. Review the JSON and save the explicit mapping before Launch appears. Each launch requires a visible confirmation and invokes only the saved executable/shortcut; the app passes no model-generated shell or arguments. On Windows, a `.lnk` is opened through the OS association, so inspect the shortcut's target before allowlisting it.

## Models

No model weights are included. The offline workspace workflow works with both model roles disabled. To use local AI, obtain and license-check compatible weights and inference software yourself; place the weights under `MODELS/`, set the exact served model and a loopback-only `/v1` endpoint, then enable the relevant role. The optional process manager starts only a user-supplied `llama-server` and GGUF model/projector; it will not download either. Never point the endpoint at a public or LAN server. Endpoint reachable does not prove the intended model is loaded or that it supports images. A missing/failed language model permits only the visible deterministic fallback; malformed or unsafe model plans are rejected.

No genuine model inference or 4 GB model run was performed for this build. Do not infer RAM from the model file size. Resource fields display null where the OS cannot provide a measurement.

## Memory, backup and storage

Memory holds task history and explicitly approved preferences/knowledge. Inspect it and remove entries you no longer need. Create SQLite backups in **Memory** and keep copies on trusted storage. Restore replaces the current memory store after integrity checks; it does not restore workspace files. Protect backups because task prompts and outputs may include private data.

ORBIT checks that its data volume is writable and has space before writes and screenshots. Physical USB removal, power failure or filesystem/flash-device failure can still corrupt a write. Stop ORBIT and wait for active requests before safely ejecting. Never unplug the USB during task/database writes.

## Current scope

ORBIT v0.5 includes action validation, persistent task/memory, browser and optional desktop adapters, model configuration/management, resource status and bounded workspace autonomy. It is not yet the fully closed-loop autonomous desktop intelligence described in the project goal. Vision observations are structured and displayed, but confidence-aware closed-loop re-planning, end-to-end editor/browser research demos, physical Windows testing and a real-model demonstration remain unverified/deferred. Consult `TEST_REPORT.md` and `HARDWARE_COMPATIBILITY.md`.
