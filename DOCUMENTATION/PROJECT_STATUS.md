# ORBIT v0.6.1 — project status

**Snapshot:** 2026-11-01. **Source branch:** `audit/v0.6-stability-fixes`. **Status:** v0.6.1 stability-audit source; core task storage, registered actions, human-gated desktop observation and portable launchers are integrated. This is not yet a generally autonomous or fully portable production computer-use agent.

## What v0.6 adds

A desktop action is no longer treated as verified merely because the input API returned. The engine records it as sent, places the task in an observation boundary and refuses a repeat. The app captures a fresh task-associated screenshot, saves a structured observation and moves the task to user review. Completion is recorded as verified only after the user explicitly confirms the visible outcome. Unverified results stay failed or awaiting review; there is no automatic retry of uncertain external actions.

When a compatible local language model is explicitly configured, ORBIT can produce a bounded, JSON-validated assessment of the visible evidence. The dashboard labels it advisory and explicitly not verification. An adaptive replan endpoint can ask that local model for a revised plan when a task is failed, paused or awaiting review. Each proposed operation must pass the existing action registry. The proposal is persisted for review but cannot execute, transfer approval, or change the original task. The user must review it and create a separate task. With no language model configured, the endpoint returns an unavailable response without making a fallback plan.

This is a **human-confirmed closed loop**, not an autonomous vision-driven loop that observes, chooses, acts and continues without a person. There is no actual inference in this build environment. Vision inference, thresholding, automatic recovery and unattended continuation remain unproven and are deliberately not claimed.

## Verification performed

- **63 unit tests passed** in GitHub Actions on Ubuntu using Python 3.12 (`python -m unittest discover -s tests -v`); Python compile, dashboard JavaScript syntax, Linux launcher syntax and config JSON checks also passed. This CI run tests the source checkout, not the separate bundled portable runtimes.
- Python compilation, `node --check orbit/static/app.js`, Linux shell syntax and JSON parsing passed.
- `tests/integration_v06_observation.py` passed against the bundled launcher and live sandbox X11/HTTP server. It moved the pointer four pixels and restored it; no click or typing was sent. It verified Class B approval, sent/not-verified state, duplicate-action no-resend refusal, task-bound screenshot persistence, fail-closed adaptive proposal when no model is configured, explicit user confirmation, and verified state surviving app restart without input replay.
- `tests/integration_v05_http.py` passed after updating its version assertion to v0.6.1. It launched the bundled Linux runtime, checked live status/resources/storage and desktop gates, executed the bounded three-step Class A workspace demo, exercised the emergency stop, and used an isolated Chromium session with a localhost-only fixture. Its cleanup restored config and removed its preflighted disposable task files.
- `tests/integration_v05_browser.py` passed with real Playwright/Chromium against a temporary localhost fixture. It exercised navigation, reading, safe fill, password denial, visible state-changing click, dialog dismissal, screenshot and tab control. It did not contact a real research source.
- `tests/integration_v05_desktop.py` passed with real sandbox X11: screenshot, window metadata, pointer move/restore, stale-observation denial and emergency-stop denial. No click or text was sent.
- The launcher audit found both runtime binaries at their expected paths and no host-Python invocation in `.sh`/`.bat` launchers. Windows executable behavior was not run on Windows.

## Remaining acceptance gaps

1. **Desktop task:** no editor was launched and no text was typed or saved. The only v0.6 real task-level operation was the four-pixel pointer movement. Do not describe the requested text-editor workflow as complete.
2. **Browser research:** only local test fixtures were used. No external-web research task, sources or research synthesis were completed.
3. **Real model behavior:** no user-supplied GGUF or running local LLM/VLM was available. Advisory scoring and successful adaptive proposal generation were not tested against genuine inference. Only the missing-model failure path was exercised.
4. **Autonomy/adaptation:** a model may propose a replacement plan, but it is not automatically adopted, approved or run. No visual dialog classification, confidence threshold, autonomous replan loop, automatic continuation or retry is claimed.
5. **Portability/hardware:** no clean Windows execution, clean-host no-Python test, physical USB detach/recovery test, 4 GB RAM benchmark or supported-Linux distro matrix was performed. Linux still relies on compatible system libraries, X11, and optional host tools such as `xdotool`.
6. **Security/privacy:** the dashboard has no authentication or encryption and must remain loopback-only. Browser host filtering is not a DNS-rebinding/network sandbox. Local DB, screenshots and browser profile may contain private data.

## Build artifact

[`ORBIT-v0.6-PORTABLE.zip`](../ORBIT-v0.6-PORTABLE.zip) is built at the project root (about 199 MB; 8,964 entries in the verified build). `unzip -t`, inventory checks and adjacent SHA-256 verification passed. It contains both bundled CPython 3.12.15 runtimes, both platform-specific vendor trees, source, tests and documentation. Generated SQLite data, model weights, browser profiles/cache, screenshots, bytecode caches and logs are excluded; `.gitkeep` directories remain. That historical v0.6.0 archive verification does not verify a rebuilt v0.6.1 release or substitute for running its Windows launcher on Windows. Verify the adjacent [`checksum file`](../ORBIT-v0.6-PORTABLE.zip.sha256) after rebuilding or transferring it.

For operational setup and system limits, see [`README.md`](../README.md), [`USB_PORTABILITY.md`](USB_PORTABILITY.md), [`HARDWARE_COMPATIBILITY.md`](HARDWARE_COMPATIBILITY.md) and [`TEST_REPORT.md`](TEST_REPORT.md). For the next-agent task list, see [`HANDOFF_TO_NEXT_AGENT.md`](HANDOFF_TO_NEXT_AGENT.md).


## v0.6.1 stability-audit update (2026-11-01)

- Corrected Windows workspace-path validation and dashboard status refresh, and aligned both runtime and package version strings to 0.6.1.
- GitHub Actions run 41279275468 passed all 63 unit tests and static checks on Ubuntu. The workflow was subsequently expanded to a Windows/Linux matrix; the new Windows result is pending confirmation.
- The live HTTP integration smoke now checks the 0.6.1 status version. It requires the full bundled Linux runtime and a disposable Linux/X11 environment, so it is not run by source-checkout CI.
- The 0.6.0 release ZIP has not been rebuilt from this branch. No v0.6.1 portable package is ready to distribute. Windows portable-runtime execution, physical USB behavior, 4 GB hardware and genuine model inference remain unverified.

## Windows CI follow-up (2026-11-01)

The first hosted Windows matrix leg exposed two issues. The legacy `safe_path` test used a case-sensitive string-prefix comparison, which is not portable to Windows path casing; it now compares resolved `Path` values. The Windows resident-memory sampler returned null because its ctypes Win32 handles/function signatures were not declared with pointer-sized types; the implementation now sets explicit `argtypes`/`restype` for Kernel32 and PSAPI. The Linux leg passed. These fixes are committed, but the rerun must pass before treating cross-platform source CI as green. This still does not test the bundled Windows runtime or batch launcher.

## Cross-platform source CI result (2026-11-01)

GitHub Actions run [41279467484](https://github.com/joelinthechat-max/ORBIT/actions/runs/41279467484) passed on both `ubuntu-latest` and `windows-latest`. Each runner passed all 63 unit tests, Python compilation, dashboard JavaScript syntax and config JSON validation; the Linux-only shell syntax step passed on Ubuntu and was correctly skipped on Windows. This verifies the source checkout under hosted Python 3.12 on both operating systems. It does **not** execute the bundled CPython runtimes, `run_windows.bat`, or the full portable ZIP.


## Superseding validation update — 2026-11-01

The earlier validation notes above contain intermediate statements that are now superseded by the completed GitHub Actions runs below.

- Source CI run [41279727228](https://github.com/joelinthechat-max/ORBIT/actions/runs/41279727228) completed successfully on both Ubuntu and Windows. Each platform passed all 63 unit tests, Python compilation, dashboard JavaScript syntax and configuration JSON checks; the Linux shell syntax check also passed.
- Portable build and Windows smoke run [41279727221](https://github.com/joelinthechat-max/ORBIT/actions/runs/41279727221) completed successfully. The workflow verified the published v0.6.0 base ZIP against its checksum, overlaid the audited source, ran the bundled Linux Python test suite and static checks, rebuilt the v0.6.1 ZIP, checked ZIP integrity, then extracted the rebuilt package on Windows and passed all bundled-Windows-Python tests and the actual `run_windows.bat` launcher/API-status smoke test.
- GitHub Actions artifact **ORBIT-v0.6.1-PORTABLE** was created for run 41279727221. Its artifact digest is `sha256:ddd6854a9e1f36e16f2a5bcc75421823503e790734f47d9809f34af01ff900be`; it is approximately 196 MB and expires 2026-11-15. This digest identifies the uploaded Actions artifact archive, not the inner portable ZIP's own SHA-256.
- The candidate is a CI-validated portable build, not a published release and not a physical USB acceptance result. The PR remains a draft and `main` is unchanged.
- These runs do not close the separately listed gaps: physical USB removal/recovery, a 4 GB device benchmark, real GGUF/VLM inference, external-web research, editor typing/saving, and unattended vision-driven autonomy.

The portable package is therefore available as a short-lived workflow artifact for review/testing. Do not claim the remaining hardware, real-model or full-autonomy acceptance items are complete.
