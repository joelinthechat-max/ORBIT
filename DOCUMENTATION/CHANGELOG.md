# Changelog

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
