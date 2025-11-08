import importlib.util
import json
import sys
import traceback
from pathlib import Path

class Plugin:
    def __init__(self, path: Path, manifest: dict):
        self.path = path
        self.manifest = manifest
        self.name = manifest.get("name", path.name)
        self.entry = manifest.get("entry", "main.py")
        self.module = None

class PluginManager:
    def __init__(self, core_root: Path):
        self.core_root = Path(core_root)
        self.user_root = Path.home() / ".config" / "SolarEx" / "plugins"
        self.plugins = []

    def discover(self):
        for d in [self.core_root / "Plugins", self.user_root]:
            if not d.exists(): continue
            for p in d.glob("*/plugin.json"):
                try:
                    manifest = json.loads(p.read_text(encoding="utf-8"))
                    self.plugins.append(Plugin(p.parent, manifest))
                except Exception as e:
                    print("[SolarEx][plugin] read error:", e)

    def load_all(self, core):
        for pl in self.plugins:
            main_py = pl.path / pl.entry
            try:
                spec = importlib.util.spec_from_file_location(pl.name, main_py)
                if not spec or not spec.loader:
                    raise ImportError(f"Unable to load spec from {main_py}")
                mod = importlib.util.module_from_spec(spec)
                sys.modules[pl.name] = mod
                spec.loader.exec_module(mod)
                init_fn = getattr(mod, "init", None)
                if callable(init_fn):
                    init_fn(core)
                pl.module = mod
                print(f"[SolarEx][plugin] Loaded {pl.name}")
            except Exception as e:
                print(f"[SolarEx][plugin] Failed {pl.name}: {e}")
                traceback.print_exc()
