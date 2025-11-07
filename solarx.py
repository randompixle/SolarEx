#!/usr/bin/env python3
from PyQt6 import QtCore
# Must be set BEFORE QApplication is created or any QtWebEngine import occurs
QtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

import argparse
import sys
from PyQt6 import QtWidgets
from solarex.core.modules import SolarCore


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

    core = SolarCore()
    core.args = args
    core.boot()
    core.set_profile(name=args.profile, incognito=args.incognito)

    # Load core modules
    core.load("solarex.net")
    core.load("solarex.net.httpx_backend", as_name="net")
    core.load("solarex.render.manager", as_name="render")
    core.render.set_active(args.renderer)

    # Choose UI mode
    if args.mode == "classic":
        core.load("solarex.ui", as_name="ui")
        core.load("solarex.ui.classic", as_name="ui")
    else:
        core.load("solarex.ui", as_name="ui")
        core.load("solarex.ui.pov", as_name="ui")

    # Load built-in and user plugins after core is ready
    core.plugin_manager.load_all(core)

    # Create app AFTER loading QtWebEngine-compatible modules
    app = QtWidgets.QApplication(sys.argv)
    if hasattr(QtCore.Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        app.setAttribute(QtCore.Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    # Launch the window
    win_cls = core.ui
    try:
        win = win_cls(core, start_url=args.home)
    except TypeError:
        win = win_cls(core, args.home)

    win.show()

    # Notify plugins the window is ready
    core.emit_window_created(win)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
