# ORBIT v0.5 Hardware and Platform Compatibility

## What was tested

- The bundled CPython 3.12.15 Linux x86_64 GNU runtime launched the application and ran all 49 automated unit tests reported in `TEST_REPORT.md`.
- In the Ubuntu sandbox, the optional Linux X11/Pillow adapter captured an actual 1280×1029 screenshot, found the visible window and active-window metadata, and moved/restored the pointer; stale observations and emergency-stop state blocked input. No click or text entry was sent to a real application.
- Bundled Playwright 1.64.1 controlled an isolated Chromium session and a disposable localhost fixture. It read page content, filled a non-password field without submitting, denied a password field, verified a visible state-changing click, safely dismissed a JavaScript dialog, captured a screenshot and opened/switched tabs.
- The bundled launcher passed an end-to-end HTTP workflow: real status/storage/resource reporting; opt-in bounded three-step local workspace task; screenshots/window API; desktop-off and emergency-stop denials; browser APIs against only a local fixture.
- The manager spawned and stopped a fake loopback API server in a test, validated a fixture GGUF path and model alias. **No GGUF weights or inference were used.**

These are sandbox integration tests, not physical hardware tests. No task was performed in a real editor and no external website was researched.

## Platform and dependency limits

The project bundles standalone CPython 3.12.15 for Windows x86_64 MSVC and Linux x86_64 GNU. The source-package structure also vendors Playwright/Pillow for Linux and Windows; Windows vendor imports, PyAutoGUI, pywin32, browser launch, USB paths and batch behavior were not run on Windows. Browser binaries are **not** bundled; the user-triggered installer downloads a Playwright-matched build into the USB folder. Distribution terms/system libraries for those binaries remain the user's responsibility (see `VENDOR/README.md`).

The Linux test used a sandbox-provided X11 display, `xdotool`, `xclip`, Chromium and system libraries. On another Linux system, desktop capture/control may be unavailable without a permitted interactive X11 session and required host tools. Wayland global desktop control may be denied; ORBIT does not bypass compositor policy. Multi-monitor support is not claimed. Windows desktop functionality, active-window lookup, app shortcuts and native input need clean Windows verification.

## Resource measurements and 4 GB target

The new status API samples actual host-reported available RAM, ORBIT process RSS, managed-model-process RSS (only when it knows the PID), and CPU where available. Null values are not fabricated. The sandbox values describe the sandbox only and cannot be transferred to a 4 GB computer. There was no constrained/physical 4 GB environment, no idle/peak-memory benchmark, and no model weights available. No model-free device-performance target or 4 GB model compatibility has been certified. Browser Chromium, Python, OS, vision images, model buffers, context/KV cache and other user applications consume additional memory. Never assume language and vision models can share 4 GB or run simultaneously.

## USB/removable storage

The app resolves source, config, SQLite, workspace, logs, screenshots, backups, browser profile and model references relative to the extracted project. Launchers do not use system Python. Storage writability/free-space probes precede writes/actions/screenshots, but physical ejection, power loss, flash-controller faults and filesystem failures can still interrupt SQLite or application operations. Test only on a spare drive and wait for in-flight requests before ejecting.

## Verdict

**Demonstrated in this sandbox:** Linux bundled-runtime launch, real X11 screenshot/window observation, safe pointer movement, local Playwright/Chromium interaction, local mock-server HTTP lifecycle, model-free task persistence/autonomy limits.

**Not verified:** clean Windows 10/11 launch/GUI/browser; physical USB insertion/removal; other Linux distributions; Wayland; real local-model inference; 4 GB performance; full editor workflow; external-site research; vision-driven closed-loop recovery or adaptive replanning. This release is not a certified general-purpose autonomous desktop agent.
