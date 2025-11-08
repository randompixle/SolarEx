from importlib import import_module
from pathlib import Path
import traceback

from .registry import ModuleRegistry
from .profiles import ProfileManager
from .plugins import PluginManager
from .uiapi import UIAPI
from .settings import Settings

class SolarCore:
    def __init__(self):
        self.registry = ModuleRegistry()
        self.args = None
        self.profile = None
        self.plugin_manager = None
        self.ui_api = UIAPI(self)
        self.settings = Settings()
        self._window_created_listeners = []
        self._shutdown_hooks = []

    def boot(self):
        print("[SolarEx] Booting modular web system…")
        core_root = Path(__file__).resolve().parent.parent
        self.plugin_manager = PluginManager(core_root)
        self.plugin_manager.discover()
        self.profile = ProfileManager(profile_name="Default", incognito=False)

    def set_profile(self, name="Default", incognito=False):
        self.profile = ProfileManager(profile_name=name, incognito=incognito)
        print(f"[SolarEx] Using profile: {self.profile}")

    def load(self, dotted, as_name=None):
        try:
            mod = import_module(dotted)
        except Exception as exc:
            print(f"[SolarEx][modules] Failed to import '{dotted}': {exc}")
            raise

        init_fn = getattr(mod, "init", None)
        if callable(init_fn):
            try:
                init_fn(self)
            except Exception as exc:
                print(f"[SolarEx][modules] init() failed for '{dotted}': {exc}")
                traceback.print_exc()
                raise

        name = as_name or dotted.split('.')[-1]
        self.registry.register(name, mod)
        print(f"[SolarEx] Loaded module '{name}' from '{dotted}'")
        return mod

    def require(self, name):
        return self.registry.require(name)

    def on_window_created(self, fn):
        self._window_created_listeners.append(fn)

    def emit_window_created(self, win):
        for fn in list(self._window_created_listeners):
            try:
                fn(win)
            except Exception as exc:
                print("[SolarEx][event] window_created error:", exc)

    def add_shutdown_hook(self, fn):
        if callable(fn):
            self._shutdown_hooks.append(fn)

    def shutdown(self):
        while self._shutdown_hooks:
            hook = self._shutdown_hooks.pop()
            try:
                hook()
            except Exception as exc:
                print("[SolarEx][shutdown] hook error:", exc)
