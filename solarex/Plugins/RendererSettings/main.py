from PyQt6 import QtWidgets
def init(core):
    print("[RendererSettings] Ready")
    def on_win(win):
        menubar = win.menuBar() if hasattr(win, "menuBar") else None
        if menubar is None: return
        settings_menu = menubar.addMenu("Settings")
        renderer_menu = settings_menu.addMenu("Renderer")
        act_qt = renderer_menu.addAction("QtWebEngine (full)")
        act_solar = renderer_menu.addAction("SolarRen (Python text renderer)")
        act_min = renderer_menu.addAction("Minimal (no JS)")
        def set_qt():
            core.render.set_active("qtweb")
            if hasattr(win, "swap_current_view"): win.swap_current_view("qtweb")
        def set_solar():
            core.render.set_active("solarren")
            if hasattr(win, "swap_current_view"): win.swap_current_view("solarren")

        def set_min():
            core.render.set_active("minimal")
            if hasattr(win, "swap_current_view"): win.swap_current_view("minimal")
        act_qt.triggered.connect(set_qt)
        act_solar.triggered.connect(set_solar)
        act_min.triggered.connect(set_min)
    core.on_window_created(on_win)
