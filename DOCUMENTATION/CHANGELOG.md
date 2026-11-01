# Changelog

## v0.6.1 CI and portable-build validation — 2026-11-01

- Supersedes the earlier intermediate notes below that described Windows CI as pending and the v0.6.1 portable package as not yet rebuilt.
- GitHub Actions source CI run [41279727228](https://github.com/joelinthechat-max/ORBIT/actions/runs/41279727228) passed all 63 tests and static checks on both Ubuntu and Windows.
- Portable build and Windows smoke run [41279727221](https://github.com/joelinthechat-max/ORBIT/actions/runs/41279727221) passed: the audited source was overlaid onto the checksum-verified v0.6.0 base package, the bundled Linux runtime test suite and static checks passed, the v0.6.1 portable ZIP integrity check passed, all bundled Windows Python tests passed, and `run_windows.bat` launched a healthy v0.6.1 server.
- The rebuilt `ORBIT-v0.6.1-PORTABLE.zip` is available in the GitHub Actions artifact `ORBIT-v0.6.1-PORTABLE` for 14 days from 2026-11-01. This is a build artifact, not a published GitHub release.
- These CI results do not establish physical USB reliability, 4 GB hardware compatibility, genuine local-model inference, external-web research, editor end-to-end operation, or fully autonomous vision-driven behavior.

# Changelog

## Windows CI follow-up — 2026-11-01

- The first Windows matrix run exposed two test/runtime issues: the legacy path test compared Windows path strings with a case-sensitive prefix check, and the Windows process-RSS probe lacked pointer-safe Win32 function signatures.
- Corrected the path test to compare resolved `Path` objects and updated the Windows RSS probe to declare pointer-sized handles and API signatures before calling PSAPI.
- The Ubuntu matrix leg passed; Windows rerun is pending.

## 0.6.1 validation follow-up — 2026-11-01

- GitHub Actions run 41279275468 passed all 63 source-checkout unit tests and the Python compile, JavaScript syntax, Linux shell syntax and configuration checks on Ubuntu.
- The workflow was expanded to run the same Python/compile/JavaScript/configuration checks on both Ubuntu and Windows hosted runners. Windows matrix status is pending confirmation.
- Updated the bundled-runtime live HTTP smoke test's expected API version to 0.6.1. The source-only CI does not execute that hardware/GUI integration test.
- No v0.6.1 portable ZIP has been rebuilt or released; the previously published v0.6.0 binary is not the corrected package.

## 0.6.1 — 2026-10-31 (stability audit)

- **Fixed Windows workspace-path validation** (`orbit/app.py`): the previous check rejected valid relative paths such as `DATA/workspace` after `pathlib` normalised separators on Windows. Validation now inspects the original configuration string, accepts both `/` and `\\`, and still rejects absolute, drive-qualified, UNC, and parent-traversal paths. Resolved paths are required to stay inside the ORBIT root.
- **Fixed dashboard status crash** (`orbit/static/app.js`): `refreshStatus()` referenced the undeclared global `CONFIG_COMPUTER_ENABLED` before assignment, producing "Status CONFIG_COMPUTER_ENABLED is not defined" on load/reload. The status response field `c.control_enabled` is now used directly.
- Added regression tests for portable workspace path validation (`tests/test_workspace_path.py`) covering forward/backslash separators, absolute paths, drive-qualified paths, UNC paths, parent traversal, empty values, resolved containment, and symlink escapes.
- Version string updated to 0.6.1.
- No architecture or safety-policy changes. Existing Class A/B/C permissions, approval tokens, emergency stop, and observation boundaries are unchanged.

## 0.6.0 — 2026-10-31

- Added a task-bound desktop Observe → Act → fresh screenshot → user Verify boundary. Action dispatch is kept separate from verified completion; observations and screenshot references persist with task memory, and restart recovery never replays uncertain external input.
- Added an optional local language-model assessment of observed evidence. It is schema-checked, displayed as advisory only, and never counts as verification or permission.
- Added a local-model adaptive-plan proposal path for failed, paused or unverified tasks. Proposed steps must validate against the action registry and are persisted/displayed as non-executable; they do not change approvals or authorize execution.
- Added the dashboard's advisory assessment and revised-plan review surface, SQLite persistence coverage, and a live HTTP/X11 acceptance script for same-session observation, user confirmation, no-resend refusal, and restart persistence.
- Added project status and next-agent handoff documents. The model-free build remains safe but cannot generate assessments or revised plans; a real local model, vision evaluation, external-web research demo, text-editor workflow, Windows run, 4 GB benchmark and physical USB test are not claimed.

## 0.5.0 — 2026-10-31

- Added platform-local vendored Playwright 1.64.1 and Pillow 12.3.0 dependencies; added optional browser setup scripts that download a matching Chromium build only when explicitly run. Browser binaries and model weights are not bundled.
- Added persistent isolated browser automation for navigation, visible-page/links/controls extraction, semantic click/fill, scroll, tabs, screenshot, explicit form submission, safe dialog dismissal and failure detection. Password/file-upload controls are denied, downloads disabled, literal private-host requests are denied by default and local fixture access needs explicit opt-in.
- Added actual Linux X11 screenshot, active-window/window-list, bounded mouse/keyboard/clipboard actions and optional PyAutoGUI/Pillow-backed Windows implementation packaged in `VENDOR/WINDOWS`. Required explicit screen freshness, coordinate bounds and emergency stop remain in force. Added application discovery, exact saved executable/shortcut allowlist and confirmed launch.
- Added best-effort host resource monitoring (null when the OS does not expose a reading), configurable bounded Class A autonomy/cancellation, screenshot and removable-storage preflights, browser/model manager lifecycle cleanup and emergency stop integration.
- Added an explicit user-supplied `llama-server`/GGUF process manager constrained to the USB model folder and loopback. It starts/stops only a user-supplied binary/weight/projector and never downloads assets.
- Added real sandbox X11 and Playwright/Chromium fixture scripts, live HTTP smoke and fake llama-server manager lifecycle test; expanded unit/safety coverage. See `TEST_REPORT.md` for exact outcomes.
- Important limit: external browser/desktop actions stop for user review rather than automatically continuing through a vision-confidence-verified loop. A full adaptive replanner, real-model inference and requested editor/external research demonstrations remain unimplemented or unverified. Windows and 4 GB physical hardware remain untested. Do not describe this as a fully autonomous computer-use agent.

## 0.4.0 — 2026-10-31

- Bundled official standalone CPython 3.12.15 runtimes for Windows x86_64 MSVC and Linux x86_64 GNU. Replaced host-Python launcher commands with self-relative USB launchers.
- Added a schema-validated modular workspace action registry and task engine: bounded file/folder operations, dependencies, Class A/B/C policy, exact expiring approvals and restart recovery.
- Expanded local-model plans to validated registered multi-step actions; retained no-shell execution boundary.
- Added model configuration/status and persistent SQLite migration/backup recovery.
- Added removable-storage write/free-space preflights and conservative handling for interrupted uncertain actions.
- Vision-guided closed-loop execution, application/window controls, browser automation, real model process control and autonomous Class A mode were explicitly out of scope for 0.4.

## 0.2.0 — 2026-10-31

- Added versioned SQLite task memory, recovery, explicit preference/knowledge approval, search, backup/restore, and safe write/verification steps.
- Added structured local-model planning, vision response validation and guarded optional desktop interactions.

## 0.1.0 — initial development build

- Added loopback dashboard, deterministic file workflow, workspace boundaries, adapter skeletons, launchers and base tests.
