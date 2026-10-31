# ORBIT v0.5 Developer Notes

## Architecture

- `orbit/app.py`: loopback-only HTTP server, local SQLite store, action/task/model/browser/desktop/resource/status APIs, storage preflight and static dashboard. Core Python code uses the bundled standard library.
- `orbit/actions.py`: schema-validated allowlisted workspace, browser and desktop actions, risk metadata, parameter validation, path bounds and handlers. There is no unrestricted shell/process action. Application launch is a separate exact-ID local config allowlist.
- `orbit/engine.py`: deterministic/local-model plan creation, dependencies, Class A/B/C permissions, parameter-bound expiring approvals, pause/resume/cancel and bounded sequential Class A execution. Uncertain actions are not replayed.
- `orbit/memory.py`: SQLite task history, approval/preferences/knowledge, integrity checks, backup/restore, version migration, crash recovery and locking.
- `orbit/adapters/models.py`: loopback OpenAI-compatible language and vision clients, structured-plan checks and bounded image processing. Model plan JSON is untrusted and revalidated against the current catalogue before storage/execution.
- `orbit/adapters/llama_server.py`: explicit manager for a user-supplied llama.cpp server executable and USB-contained GGUF path, loopback binding, bounded process/health checks, alias verification and stop. No runtime/model download. A fake HTTP server test is not inference evidence.
- `orbit/adapters/browser.py`: one worker thread owns Playwright synchronous objects; isolated persistent profile below `DATA/browser`; fixed DOM queries; deny-default literal private-host routing; local-host exception is explicit; password/file inputs refused; downloads disabled; dialogs dismissed; browser setting changes stop the current worker.
- `orbit/adapters/computer.py`: optional PyAutoGUI, or Linux X11/Pillow + fixed-argument `xdotool` fallback; timestamp/bounds/screen-size checks, guarded keyboard/mouse, clipboard, window discovery, screenshot and exact allowlisted app launch. Windows shortcuts use OS association only after explicit user allowlisting. Wayland restrictions are not bypassed.
- `orbit/resources.py`: best-effort OS measurements; null means unavailable. Only a managed model process PID permits a server-RSS estimate.
- `orbit/static/`: hybrid dashboard for tasks, approvals, outputs, resources, browser/model settings, application allowlist and desktop controls.

## Security / risk boundaries

Unknown action identifiers and unknown input fields fail closed. Plans are limited to registered schemas, workspace file paths are contained, external destinations are validated, no model-controlled shell exists, and completed action states persist. B/C approvals bind the task/step/parameters/expected result and expire. Computer-control and browser configuration default off. External browser and desktop actions do not continue into a second autonomous action without user observation/review. Stop signals cancellation and sets the computer emergency latch; explicitly Resume only after inspection.

Local app allowlist paths are inherently powerful and are user-managed; a shortcut can encode its own arguments/target. Review the exact path before saving it. Desktop/browser libraries operate with the logged-in user's OS privileges. The dashboard has no auth; do not bind it off-loopback or expose the port.

The browser private-host filter checks literal private IPs and a small localhost set; it is not a DNS-rebinding or network-isolation boundary. Use only trusted destinations and do not treat it as a sandbox. Web content is untrusted context. The current code does not implement a reliable visual-confidence gate or automatic action re-planning.

## Storage and runtime

`ROOT` derives from `orbit/app.py`; workspace/model paths reject traversal and remain under the USB project. SQLite, WAL, config, backups, logs, screenshots and browser profile are on the USB. Storage preflights run before task/execution and screenshots; synchronous OS calls cannot be safely cancelled in the middle. No code can guarantee integrity after physical drive removal or power loss. Browser downloads are disabled.

The project bundles CPython 3.12.15 standalone runtimes for Windows x86_64 MSVC and Linux x86_64 GNU. `VENDOR/README.md` lists optional third-party packages, versions and license-retention structure. The browser binaries are not included; setup scripts download the Playwright-selected build to a USB cache only when the user runs them. Windows runtime/vendor/desktop behavior was not executed on a Windows host. Linux needs a compatible glibc/loader; X11 control also needs interactive `DISPLAY` and host `xdotool`. No Wayland security bypass is attempted.

## Testing

```sh
export PYTHONHOME="$PWD/RUNTIME/LINUX/python" PYTHONPATH="$PWD" PYTHONNOUSERSITE=1
RUNTIME/LINUX/python/bin/python3.12 -m unittest discover -s tests -v
RUNTIME/LINUX/python/bin/python3.12 -m compileall -q orbit tests
node --check orbit/static/app.js
sh -n run_linux.sh setup_browser_linux.sh
python3 -m json.tool CONFIG/orbit.json >/dev/null
```

Real-environment scripts (optional compatible Chromium, X11 or Playwright browser required): `tests/integration_v05_browser.py`, `integration_v05_desktop.py`, `integration_v05_http.py`, `integration_v05_llama_manager.py`. The HTTP integration refuses pre-existing disposable targets, and tests only a local fixture. The llama-manager integration uses a fake server and no weights. See `TEST_REPORT.md` for exact results and gaps.

## Important deferred goal

The v0.5 master goal's complete loop `plan → action → screenshot/vision → confidence-aware verification → memory update → continue/replan` is **not finished**. The current engine pauses after external browser/desktop I/O rather than trusting a click or generated vision observation. It lacks a complete adaptive re-planner, confidence threshold/retry/crop policy, browser/desktop observation-memory loop and the requested text-editor/external-research end-to-end demonstrations. This is a deliberate safety limitation, not an implemented capability.
