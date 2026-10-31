# ORBIT v0.5 — implementation and acceptance report

> **v0.6 update (2026-10-31):** This file preserves the v0.5 baseline report below. For current v0.6 results, read [`PROJECT_STATUS.md`](PROJECT_STATUS.md) and [`HANDOFF_TO_NEXT_AGENT.md`](HANDOFF_TO_NEXT_AGENT.md). The current suite passes 52 unit tests. `tests/integration_v06_observation.py` additionally passes against the bundled Linux launcher and sandbox X11, exercising action-sent/not-verified state, no-resend protection, task-bound screenshot persistence, the fail-closed no-model adaptive-replan path, explicit user confirmation, and persistence through restart. The v0.6 assessment/replan success paths with genuine local inference, external browser research, text-editor workflow, Windows runtime, 4 GB hardware and physical USB behavior remain unverified. The existing v0.5 counts and statements in this historical report are not v0.6 measurements.

**Release:** 0.5.0 · **Build environment:** Ubuntu sandbox, Linux x86_64 GNU, X11 · **Status:** substantial integration, not a completed general-purpose autonomous agent.

## Executive summary

The v0.4 architecture has been extended with real optional Playwright browser automation, Linux X11 desktop capture/control, a packaged-but-unverified Windows PyAutoGUI stack, application discovery/allowlist, resource reporting, bounded Class A workspace autonomy, and explicit user-supplied llama.cpp process management. All prior SQLite, registered-action, dependency, approval, restart and USB-runtime constraints were retained. **The central vision-driven adaptive loop is not complete:** external browser/desktop interaction pauses for user observation/review instead of automatically capturing, confidence-checking, replanning and safely continuing. No genuine language or vision model inference, target Windows run, 4 GB system or physical USB removal was available.

## Scope and implementation matrix

| Brief area | Implemented and tested here | Incomplete, unverified or deliberately deferred |
|---|---|---|
| 1–2. Identity, offline mode, audit/preservation | Existing v0.4 project extended in place; model-free server, workspace actions, local SQLite, restart recovery, action dependencies, A/B/C and USB-relative data paths retained. | ORBIT remains a bounded development assistant rather than a general-purpose autonomous agent. |
| 3. Desktop engine | Real Linux X11 screenshot, active/window listing and safe pointer movement through `xdotool`/Pillow; click, double/right-click, scroll, drag, keyboard, clipboard and window controls are registered behind safety gates; screen bounds/freshness/resize checks and stop latch retained. Windows dependency set is staged. | No click/text was sent to a real application in the live demonstration; the requested text-editor creation/save workflow was not run. Windows GUI stack is untested. Multiple monitors are not claimed. |
| 4. Visual intelligence | Real screenshot input pipeline; resize/pixel/file limits, validated schema, confidence and coordinate bounds; fixed crop-origin/resized-pixel to desktop-coordinate mapping, active window title metadata and bounded potential-error list. | No actual vision model/weights were available. Vision observations do not yet drive a confidence threshold, automatic recapture/crop, screen action or adaptive recovery. No mock is presented as vision. |
| 5. Browser | Persistent isolated Playwright worker; navigation, page text/links/controls, semantic click/fill, scroll/tabs, screenshot, explicit form submission, page failure handling and safe dialog dismissal. Password/file inputs denied, downloads off, local file/browser schemes denied; literal local/private IPs denied by default. | Real test used only a localhost fixture, not external web research. Private-host protection is not a DNS-rebinding/network sandbox. Browser binary is not bundled; user-triggered browser setup requires Internet. |
| 6. Discovery/window/app permission | Linux `.desktop` and Windows shortcut discovery adapters; exact user-maintained app ID/path allowlist, explicit launch confirmation, OS window listing/activation/close controls. App launch uses only the saved path without model-controlled command/arguments. | Windows discovery/shortcut launching untested. Wayland may deny global automation; no bypass. |
| 7. Model inference/backend | Loopback-only OpenAI-compatible client and plan validator; user-supplied `llama-server`/GGUF process manager with USB containment, CPU-only flags, bounded context/thread/health checks, alias verification and stop. | **No real model inference.** Process manager integration used fake weights/path and a fake OpenAI-compatible server only. Streaming, genuine cancellation, real weight compatibility, model discovery and memory-aware load forecasting are not demonstrated. |
| 8. Execution/recovery | Bounded action count, timeout, cancellation, Class A gate, storage preflight, task pause/recovery and no-replay policies. External UI actions create a review boundary. | No full `plan → act → screenshot/vision → verify → memory → continue/replan` loop; automatic vision-triggered replan/retry is deliberately withheld. Restart recovery was verified for registered file/model-plan tasks, not a live GUI state. |
| 9. Safety/autonomy | Default-deny registry/schema, workspace/path bounds, exact expiring B/C approvals, local application permission, browser/task confirmation, emergency stop, loopback-only server, untrusted page boundary, no model shell. Class A autonomy defaults off and is bounded. | No auth or encrypted local data; not suitable for exposure, unattended high-consequence work or hostile local-machine threat models. Browser domain filtering is not network isolation. |
| 10. Resources/4 GB | Best-effort actual available RAM, app RSS, known managed process RSS and CPU where supported; null when unavailable. Screenshot/context/action limits and only one ORBIT-managed model process. | No constrained/physical 4 GB benchmark; no 4 GB compatibility claim. External process RSS and vision-specific peak RAM may be unknown; no simultaneous two-model claim. |
| 11. USB | Bundled CPython runtimes, relative paths, local config/database/log/workspace/backups/screenshots/browser profile, storage preflight. Optional packages are vendored by OS; browser binaries are user-installed to USB only. | Clean Windows and physical USB detach/recovery not tested; Linux USB filesystem transition not exercised. |
| 12. Dashboard | Hybrid dashboard shows tasks/steps/outputs, model/vision/browser/computer/storage/resource status, approvals, memory, application allowlist, pause/resume/stop and desktop controls. | External action state is visible but not automatically classified/replanned from vision; no fake model progress is shown. |
| 13. End-to-end demonstrations | See the six test-by-test results below; real Browser/X11 APIs and a local workspace task were exercised. | Requested editor workflow, three-source external research task, unexpected visual dialog recovery and genuine model inference were not demonstrated. |
| 14. Physical hardware | No physical/target hardware evidence. | Windows 10/11, clean Windows without Python, Linux distro matrix, Wayland, actual 4 GB hardware and physical USB verification remain open. |
| 15. Development order | The received sections were implemented as far as the available environment permitted; the existing project was retained. | The uploaded brief ends mid-sentence in section 15. Per user direction, no unseen phases or requirements were assumed. |

## Automated checks

- **49 unit tests passed** under the bundled CPython 3.12.15 Linux runtime (`python -m unittest discover -s tests -v`). Coverage includes prior action/memory/model tests and v0.5 browser/desktop schema and policy, browser worker disable behavior, class gating, bounded autonomy, model-manager validation, resource null handling, application allowlist, vision coordinate scaling/crop origins and potential-error schema.
- Python compile check: `compileall -q orbit tests` passed.
- `node --check orbit/static/app.js` passed.
- `sh -n run_linux.sh setup_browser_linux.sh` and JSON parsing of `CONFIG/orbit.json` passed.
- Windows `.bat` syntax and Windows binaries/import paths were not executable or tested in the Linux environment.

## Live integration results

| Script | Result | Exact boundary |
|---|---|---|
| `tests/integration_v05_browser.py` | **PASS**, actual Playwright + sandbox Chromium | Isolated persistent test profile; localhost fixture; visible page/title/read; non-password field filled without submit; password field denied; visible click verified; alert dismissed by safe default; screenshot; blank tab and switch. No external website or existing user profile. |
| `tests/integration_v05_desktop.py` | **PASS**, actual sandbox X11 desktop | Screenshot 1280×1029; one visible window and active-window metadata; pointer move and restore; stale timestamp and emergency-stop denial. No click, keystroke or text sent to an application. |
| `tests/integration_v05_http.py` | **PASS**, actual bundled Linux launcher/HTTP/Chromium/X11 | Status/resource/storage, screenshot/window API, desktop disabled gate, 3-step Class A workspace task with file, verified outputs, exact stop/reject path, real local fixture browser navigation/read/fill/password denial/click/screenshot/close. Test restored config and deleted only pre-checked disposable data. |
| `tests/integration_v05_llama_manager.py` | **PASS**, fake local process | Verified USB-contained executable/model-path validation, loopback spawn, exact served alias and clean stop. It deliberately used no model weights and proves no inference capability. |
| `tests/integration_portable_smoke.py` | **PASS**, inherited mock-model workflow | Mock endpoint returned a 2-step plan; registry/dependency checks, Class B approval, copy verification, cross-origin denial, restart persistence and no replay passed. **Mock inference only.** |

## Required demonstrations, explicitly scored

1. **Text editor task:** not demonstrated. The live desktop test captured the real screen/window and moved/restored the cursor only; it did not open an editor, type text or save a document.
2. **External browser research:** not demonstrated. Browser operations were exercised against a controlled local fixture only; no sources or factual comparison were gathered.
3. **Visual recovery:** not demonstrated. Dialog dismissal was tested in the isolated browser fixture, but no unexpected desktop state was detected/reassessed by the ORBIT execution engine.
4. **Restart recovery:** partial pass. Existing/mock-model task persistence and no-repeat after app restart were verified. GUI reassessment after restart was not implemented or tested.
5. **Safety:** passed for tested action schemas/approval, Class A opt-in/bounds, password/unsafe protocol denial, local desktop config/freshness, emergency stop and loopback/cross-origin checks. Not an audit/certification of the full OS threat surface.
6. **Real local model inference:** not done. No user-supplied weights/server existed. The fake server test is process/API-contract validation only.

## Hardware and privacy caveats

This is an Ubuntu sandbox result, not a Windows test, physical USB test or 4 GB benchmark. The Linux test also relied on sandbox-provided X11, `xdotool`, `xclip`, system libraries and Chromium. Model weights are not bundled. A model file's size is not its memory requirement. Resource values reflect only the build environment; null indicates no measurement. Task prompts, screenshots, browser profile and local DB may contain private information. The server has no authentication or encryption, binds only to loopback and must not be exposed to a network.

See `HARDWARE_COMPATIBILITY.md`, `USB_PORTABILITY.md`, `V0.5_TECHNICAL_RESEARCH.md` and `VENDOR/README.md` for detailed limitations and setup provenance.
