from dataclasses import dataclass
from typing import Callable, Dict, Optional

import re
import threading
import urllib.error
import urllib.request
from html import unescape

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
        try:
            from PyQt6.QtWebEngineCore import (
                QWebEnginePage,
                QWebEngineProfile,
                QWebEngineScript,
            )
        except ImportError:
            # Older PyQt6 releases shipped these APIs from QtWebEngineWidgets
            from PyQt6.QtWebEngineWidgets import (  # type: ignore
                QWebEnginePage,
                QWebEngineProfile,
                QWebEngineScript,
            )

        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
        except ImportError:
            # Newer distributions keep the view class in QtWebEngineCore
            from PyQt6.QtWebEngineCore import QWebEngineView  # type: ignore

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

class SolarRenBackend:
    def __init__(self):
        self._default_agent = "SolarRen/1.0"

    def new_view(self, core, user_agent: str = None):
        from PyQt6 import QtCore, QtWidgets

        default_agent = self._default_agent

        class TextExtractor:
            def __init__(self):
                from html.parser import HTMLParser

                class _Parser(HTMLParser):
                    def __init__(self, outer):
                        super().__init__()
                        self.outer = outer
                        self._ignore_stack: list[str] = []

                    def handle_starttag(self, tag, attrs):
                        tag = tag.lower()
                        if tag in ("script", "style"):
                            self._ignore_stack.append(tag)
                        elif not self._ignore_stack and tag in ("br", "p", "div", "li", "section", "article", "tr", "h1", "h2", "h3", "h4", "h5", "h6"):
                            self.outer._chunks.append("\n")

                    def handle_endtag(self, tag):
                        tag = tag.lower()
                        if self._ignore_stack and self._ignore_stack[-1] == tag:
                            self._ignore_stack.pop()
                        elif not self._ignore_stack and tag in ("p", "div", "li", "section", "article", "tr"):
                            self.outer._chunks.append("\n")

                    def handle_data(self, data):
                        if self._ignore_stack:
                            return
                        text = unescape(data)
                        if text.strip():
                            self.outer._chunks.append(text.strip())

                self._chunks: list[str] = []
                self._parser = _Parser(self)

            def feed(self, html: str):
                self._parser.feed(html)

            def get_text(self) -> str:
                body = " ".join(self._chunks)
                body = re.sub(r"\s+\n", "\n", body)
                body = re.sub(r"\n\s+", "\n", body)
                body = re.sub(r"\n{3,}", "\n\n", body)
                body = re.sub(r"\s{2,}", " ", body)
                return body.strip()

        class SolarRenView(QtWidgets.QWidget):
            titleChanged = QtCore.pyqtSignal(str)
            loadFinished = QtCore.pyqtSignal(bool)
            _contentReady = QtCore.pyqtSignal(str, str, str, bool)

            def __init__(self, core, agent: str):
                super().__init__()
                self.core = core
                self._agent = agent or getattr(getattr(core, "args", None), "ua", None) or default_agent
                self._url = QtCore.QUrl("about:blank")
                self._thread: Optional[threading.Thread] = None

                layout = QtWidgets.QVBoxLayout(self)
                layout.setContentsMargins(6, 6, 6, 6)
                self._status = QtWidgets.QLabel("SolarRen ready.")
                self._status.setObjectName("solarren-status")
                self._viewer = QtWidgets.QPlainTextEdit()
                self._viewer.setReadOnly(True)
                self._viewer.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.WidgetWidth)
                layout.addWidget(self._status)
                layout.addWidget(self._viewer, 1)

                self._contentReady.connect(self._apply_content)
                self.setSource = self.load  # compatibility with minimal backend usage

            def sizeHint(self):  # pragma: no cover - simple Qt size hint
                return QtCore.QSize(800, 600)

            def url(self):
                return QtCore.QUrl(self._url)

            @QtCore.pyqtSlot(str, str, str, bool)
            def _apply_content(self, url_str: str, title: str, text: str, success: bool):
                self._url = QtCore.QUrl(url_str)
                self._status.setText(f"SolarRen → {url_str}")
                self._viewer.setPlainText(text)
                self.titleChanged.emit(title)
                self.loadFinished.emit(success)

            def load(self, url):
                if isinstance(url, QtCore.QUrl):
                    qurl = QtCore.QUrl(url)
                else:
                    qurl = QtCore.QUrl(str(url))
                if not qurl.scheme():
                    qurl.setScheme("https")

                if qurl.scheme() == "about" and qurl.path().lower() in ("", "blank"):
                    self._contentReady.emit(qurl.toString(), "about:blank", "SolarRen ready.", True)
                    return

                self._status.setText(f"Loading {qurl.toString()} …")
                self._viewer.setPlainText("")
                self.loadFinished.emit(False)

                def worker(target_url: QtCore.QUrl):
                    url_str = target_url.toString()
                    try:
                        if target_url.scheme() not in ("http", "https"):
                            raise ValueError(f"Unsupported scheme '{target_url.scheme()}'")
                        request = urllib.request.Request(url_str, headers={"User-Agent": self._agent})
                        with urllib.request.urlopen(request, timeout=15) as response:
                            charset = response.headers.get_content_charset() or "utf-8"
                            payload = response.read()
                        try:
                            html_text = payload.decode(charset, errors="replace")
                        except LookupError:
                            html_text = payload.decode("utf-8", errors="replace")

                        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
                        page_title = unescape(title_match.group(1).strip()) if title_match else url_str

                        extractor = TextExtractor()
                        extractor.feed(html_text)
                        body = extractor.get_text() or "[No textual content rendered]"

                        header = page_title + "\n" + ("=" * len(page_title)) + "\n\n"
                        display_text = header + body
                        self._contentReady.emit(url_str, page_title, display_text, True)
                    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
                        self._contentReady.emit(
                            url_str,
                            url_str,
                            f"SolarRen failed to load {url_str}:\n{exc}",
                            False,
                        )
                    except Exception as exc:
                        self._contentReady.emit(
                            url_str,
                            url_str,
                            f"SolarRen failed to load {url_str}:\n{exc}",
                            False,
                        )

                self._thread = threading.Thread(target=worker, args=(qurl,), daemon=True)
                self._thread.start()

        return SolarRenView(core, user_agent or self._default_agent)

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
    mgr.register("solarren", lambda: SolarRenBackend())
    mgr.register("minimal", lambda: MinimalBackend())
    core.render = mgr
