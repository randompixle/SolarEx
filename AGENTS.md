
SolarEx is a custom modular browser and framework built with PyQt6. It includes:
- `solarx.py`: main entrypoint that bootstraps SolarEx (profiles, modules, plugins).
- `solarex/core/`: framework internals.
- `solarex/render/`: renderer manager and modules (e.g. qtweb, solarren, minimal).
- `solarex/ui/`: UI systems (classic, pov, etc.)
- `solarex/Plugins/`: built-in and user plugins (DarkMode, Logger, RendererSettings, etc.)

Goal: make SolarEx **stable, modular, and runnable with `python solarx.py`**.

### Your tasks:
1. Fix all broken imports and AttributeErrors.
2. Ensure PyQt6 initialization is correct:
   - Always call `QtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)` before `QApplication`.
3. Maintain `qtweb` as the default renderer, but keep `solarren` working for basic fallback rendering.
4. Don’t break any working modules — no overwriting functional code.
5. Ensure all plugins are loaded via `core.plugin_manager.load_all(core)` and print as `[SolarEx][plugin] Loaded <name>`.
6. Add graceful fallback if a renderer or UI module fails to load.
7. Add cleanup to remove `__pycache__` and `.pyc` files on shutdown.
8. Don’t add unnecessary dependencies — stick to PyQt6, httpx, and BeautifulSoup.
9. Make sure window creation and plugin hooks (`core.emit_window_created(win)`) all succeed without crashing.
10. Make solarRen render google properly

### Expected output behavior:
When running:

python solarx.py

The terminal should print:

[SolarEx] Booting modular web system…
[SolarEx] Renderer set to 'qtweb'
[SolarEx][plugin] Loaded Logger
[SolarEx][plugin] Loaded DarkMode
[SolarEx][plugin] Loaded HelloEx
[SolarEx] Window initialized successfully.


If something fails (like a plugin import), it should **print a warning** instead of crashing.

---

DO NOT rewrite or delete files that already work.  
Only fix crashes, imports, Qt init errors, and runtime instability.
