from dataclasses import dataclass
from typing import Callable, Dict, Optional

@dataclass
class BackendEntry:
    name: str
    factory: Callable[[], object]

class RenderManager:
    def __init__(self, core):
        self.core = core
        self.backends: Dict[str, BackendEntry] = {}
        self.active: Optional[str] = None

    def register(self, name: str, factory: Callable[[], object]):
        self.backends[name] = BackendEntry(name, factory)

    def set_active(self, name: str):
        if name not in self.backends:
            raise RuntimeError(f"No such renderer backend: {name}")
        self.active = name
        print(f"[SolarEx] Renderer set to '{name}'")

    def new_view(self, *a, **kw):
        if not self.active:
            raise RuntimeError("No active renderer backend")
        backend = self.backends[self.active].factory()
        return backend.new_view(self.core, *a, **kw)

# ==== Backends ====

class QtWebBackend:
    def __init__(self): pass
    def new_view(self, core, user_agent: str = None):
        from PyQt6.QtWebEngineCore import (
            QWebEnginePage,
            QWebEngineProfile,
            QWebEngineScript,
        )
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineScript
        from PyQt6.QtWebEngineWidgets import QWebEnginePage, QWebEngineView

        if core.profile.incognito:
            profile = QWebEngineProfile()
        else:
            profile = QWebEngineProfile(core.profile.profile_name)
            profile.setCachePath(core.profile.cache_path)
            profile.setPersistentStoragePath(core.profile.storage_path)
            profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)

        page = QWebEnginePage(profile)
        if user_agent:
            profile.setHttpUserAgent(user_agent)
        view = QWebEngineView()
        view.setPage(page)

        # userscripts via extensions
        try:
            from solarex.core.extensions import ExtensionManager
            from pathlib import Path
            em = ExtensionManager(Path(core.profile.root))
            em.discover()
            for ext in em.extensions:
                for rel in ext.userscripts:
                    p = (Path(ext.manifest_path).parent / rel).resolve()
                    if p.exists():
                        with open(p, "r", encoding="utf-8") as f:
                            src = f.read()
                        script = QWebEngineScript()
                        script.setSourceCode(src)
                        script.setName(f"ext::{ext.name}::{p.name}")
                        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
                        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
                        script.setRunsOnSubFrames(True)
                        profile.scripts().insert(script)
        except Exception as e:
            print("[SolarEx][ext] injection error:", e)
        return view

class MinimalBackend:
    def __init__(self): pass
    def new_view(self, core, user_agent: str = None):
        from PyQt6 import QtWidgets, QtCore
        view = QtWidgets.QTextBrowser()
        view.setOpenExternalLinks(True)
        def load_url(url):
            if hasattr(url, "toString"):
                url = url.toString()
            view.setSource(QtCore.QUrl(url))
        view.load = load_url
        view.titleChanged = DummySignal()
        view.url = lambda: view.source()
        view.loadFinished = DummySignal()
        return view

class DummySignal:
    def connect(self, *a, **kw): pass

def init(core):
    mgr = RenderManager(core)
    mgr.register("qtweb", lambda: QtWebBackend())
    mgr.register("minimal", lambda: MinimalBackend())
    core.render = mgr
