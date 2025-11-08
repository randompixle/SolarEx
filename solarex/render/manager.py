import importlib
import pkgutil
from dataclasses import dataclass
from types import ModuleType
from typing import Callable, Dict, Optional

@dataclass
class BackendEntry:
    id: str
    name: str
    desc: str
    module: ModuleType
    settings_schema: Callable[[object], list]

    def create_view(self, core, *args, **kwargs):
        return self.module.new_view(core, *args, **kwargs)

class RenderManager:
    def __init__(self, core):
        self.core = core
        self.backends: Dict[str, BackendEntry] = {}
        self.active_id: Optional[str] = None
        self._discover()
    def _discover(self):
        import solarex.render.modules as mods
        for m in pkgutil.iter_modules(mods.__path__):
            try:
                mod = importlib.import_module(f"solarex.render.modules.{m.name}")
            except Exception as exc:
                print(f"[SolarEx][render] Failed to import renderer module '{m.name}': {exc}")
                continue
            meta = getattr(mod, "metadata", None)
            factory = getattr(mod, "new_view", None)
            if not meta or not callable(factory):
                continue
            entry = BackendEntry(
                id=meta.get("id", m.name),
                name=meta.get("name", m.name),
                desc=meta.get("description", ""),
                module=mod,
                settings_schema=getattr(mod, "get_settings_schema", lambda core: [])
            )
            self.backends[entry.id] = entry

    def _preferred(self, *candidates: str) -> Optional[BackendEntry]:
        for candidate in candidates:
            entry = self.backends.get(candidate)
            if entry:
                return entry
        return next(iter(self.backends.values()), None)
    def list_backends(self): return list(self.backends.values())
    def set_active(self, backend_id: str):
        entry = self.backends.get(backend_id)
        if not entry:
            entry = self._preferred("qtweb", "solarren")
            if not entry:
                raise RuntimeError("No renderer backends are available")
            print(f"[SolarEx][render] Unknown backend '{backend_id}', falling back to '{entry.id}'")
        self.active_id = entry.id
        print(f"[SolarEx] Renderer set to '{self.active_id}'")
    def new_view(self, *a, **kw):
        if not self.active_id:
            default_entry = self._preferred("qtweb", "solarren")
            if not default_entry:
                raise RuntimeError("No renderer backends are registered")
            self.active_id = default_entry.id
            print(f"[SolarEx][render] No renderer selected, defaulting to '{self.active_id}'")

        entry = self.backends.get(self.active_id)
        if not entry:
            raise RuntimeError(f"Renderer '{self.active_id}' is not registered")

        try:
            return entry.create_view(self.core, *a, **kw)
        except Exception as exc:
            print(f"[SolarEx][render] Failed to create view for '{entry.id}': {exc}")
            fallback = self._preferred("solarren")
            if fallback and fallback.id != entry.id:
                print(f"[SolarEx][render] Falling back to '{fallback.id}' renderer")
                self.active_id = fallback.id
                return fallback.create_view(self.core, *a, **kw)
            raise

def init(core): core.render = RenderManager(core)
