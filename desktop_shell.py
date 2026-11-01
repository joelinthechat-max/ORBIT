"""ORBIT Windows desktop host.

The UI is rendered inside an application-owned WebView2 window. It does not
open a separate Chrome/Edge browser tab. Persistent data remains beside ORBIT.exe.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path


def configure_paths() -> Path:
    if getattr(sys, "frozen", False):
        root = Path(sys.executable).resolve().parent
        bundle = Path(getattr(sys, "_MEIPASS", root)).resolve()
        os.environ["ORBIT_ROOT"] = str(root)
        os.environ["ORBIT_STATIC_DIR"] = str(bundle / "orbit" / "static")
    else:
        root = Path(__file__).resolve().parent
        os.environ.setdefault("ORBIT_ROOT", str(root))
        os.environ.setdefault("ORBIT_STATIC_DIR", str(root / "orbit" / "static"))
    return root


def show_error(message: str) -> None:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "ORBIT could not start", 0x10)
    except Exception:
        pass


def start_server():
    from orbit import app

    server, host, port = app.create_server()
    worker = threading.Thread(target=server.serve_forever, name="orbit-http", daemon=True)
    worker.start()
    return app, server, worker, host, port


def stop_server(app, server, worker) -> None:
    try:
        server.shutdown()
    finally:
        server.server_close()
        worker.join(timeout=5)
        app.shutdown()


def self_test() -> int:
    app = server = worker = None
    try:
        # Ensure the packaged desktop-window backend is importable, not just the HTTP server.
        import webview
        if os.name == "nt":
            import webview.platforms.edgechromium
        app, server, worker, host, port = start_server()
        url = f"http://{host}:{port}/api/status"
        last_error = None
        for _ in range(30):
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if payload.get("version") != "0.6.1":
                    raise RuntimeError("Unexpected ORBIT version in /api/status")
                if not payload.get("storage", {}).get("writable"):
                    raise RuntimeError("ORBIT storage is not writable")
                return 0
            except Exception as exc:
                last_error = exc
                time.sleep(0.25)
        raise RuntimeError(f"ORBIT health check failed: {last_error}")
    except Exception as exc:
        show_error(f"ORBIT desktop self-test failed:\n{exc}")
        return 1
    finally:
        if app is not None and server is not None and worker is not None:
            stop_server(app, server, worker)


def main() -> int:
    root = configure_paths()
    if "--self-test" in sys.argv:
        return self_test()

    app = server = worker = None
    try:
        config_path = root / "CONFIG" / "orbit.json"
        if not config_path.is_file():
            raise FileNotFoundError(f"Missing configuration: {config_path}")
        app, server, worker, host, port = start_server()

        import webview

        window = webview.create_window(
            "ORBIT",
            f"http://{host}:{port}",
            width=1440,
            height=920,
            min_size=(1024, 680),
            background_color="#0b1220",
        )
        if os.name == "nt":
            webview.start(gui="edgechromium", debug=False)
        else:
            webview.start(debug=False)
        return 0
    except Exception as exc:
        show_error(
            "ORBIT could not open its desktop window.\n\n"
            f"{exc}\n\n"
            "On Windows, install the Microsoft Edge WebView2 Runtime, then try again."
        )
        return 1
    finally:
        if app is not None and server is not None and worker is not None:
            stop_server(app, server, worker)


if __name__ == "__main__":
    raise SystemExit(main())
