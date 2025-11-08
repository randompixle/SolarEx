#!/usr/bin/env python3
import argparse
import atexit
import shutil
import sys
from pathlib import Path

from PyQt6 import QtCore

# Must be set BEFORE QApplication is created or any QtWebEngine import occurs
QtCore.QCoreApplication.setAttribute(
    QtCore.Qt.ApplicationAttribute.AA_ShareOpenGLContexts,
    True,
)

from PyQt6 import QtWidgets

# ✅ Preload QtWebEngine so QtWebEngineCore is initialized globally
try:
    from PyQt6 import QtWebEngineCore, QtWebEngineWidgets
    QtWebEngineCore.QWebEngine.initialize() if hasattr(QtWebEngineCore, "QWebEngine") else None
except Exception:
    # Fallback — will still work if QtWebEngine is lazy-loaded later
    pass

from solarex.core.modules import SolarCore


PROJECT_ROOT = Path(__file__).resolve().parent


def _cleanup_pycache(root: Path) -> None:
    for pycache in root.rglob("__pycache__"):
        shutil.rmtree(pycache, ignore_errors=True)
    for pyc in root.rglob("*.pyc"):
        try:
            pyc.unlink()
        except FileNotFoundError:
            pass


def _load_ui(core: SolarCore, preferred: str, fallback: str) -> None:
    try:
        core.load(preferred, as_name="ui")
    except Exception as exc:
        if fallback and fallback != preferred:
            print(f"[SolarEx][ui] Failed to load '{preferred}': {exc}. Trying '{fallback}'…")
            core.load(fallback, as_name="ui")
        else:
            raise


def main():
    ap = argparse.ArgumentParser(prog="SolarEx")
    ap.add_argument("--mode", choices=["classic", "pov"], default="classic")
    ap.add_argument("--home", default="https://www.google.com/")
    ap.add_argument("--ua", help="Custom User-Agent")
    ap.add_argument("--profile", default="Default", help="Profile name (ignored if --incognito)")
    ap.add_argument("--incognito", action="store_true", help="Incognito (no disk cache/cookies)")
    ap.add_argument(
        "--renderer",
        choices=["qtweb", "solarren", "minimal"],
        default="qtweb",
        help="Choose renderer backend",
    )
    args = ap.parse_args()

    # === Core boot ===
    core = SolarCore()
    core.args = args
    core.boot()
    core.set_profile(name=args.profile, incognito=args.incognito)
    atexit.register(core.shutdown)

    # === Load core modules ===
    core.load("solarex.net")
    core.load("solarex.net.httpx_backend", as_name="net")
    if hasattr(core, "net") and hasattr(core.net, "close"):
        core.add_shutdown_hook(core.net.close)
    core.load("solarex.render.manager", as_name="render")
    core.render.set_active(args.renderer)

    # === Load UI ===
    core.load("solarex.ui", as_name="ui")
    if args.mode == "classic":
        _load_ui(core, "solarex.ui.classic", "solarex.ui.pov")
    else:
        _load_ui(core, "solarex.ui.pov", "solarex.ui.classic")

    # === Load plugins ===
    core.plugin_manager.load_all(core)

    # === Register cleanup ===
    atexit.register(_cleanup_pycache, PROJECT_ROOT)

    # === Create QApplication ===
    app = QtWidgets.QApplication(sys.argv)
    if hasattr(QtCore.Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        app.setAttribute(QtCore.Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    # === Launch UI window ===
    win_cls = core.ui
    try:
        win = win_cls(core, start_url=args.home)
    except TypeError:
        win = win_cls(core, args.home)

    win.show()
    core.emit_window_created(win)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
