from dataclasses import dataclass
from typing import Callable, Dict, Optional

import re
import textwrap
import threading
import urllib.error
import urllib.request
from html import escape, unescape
from urllib.parse import urljoin

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
            def __init__(self, base_url: str):
                from html.parser import HTMLParser

                class _Parser(HTMLParser):
                    BLOCK_BREAK_TAGS = {
                        "address",
                        "article",
                        "aside",
                        "div",
                        "footer",
                        "form",
                        "header",
                        "main",
                        "nav",
                        "section",
                        "table",
                    }

                    DOUBLE_BREAK_TAGS = {
                        "article",
                        "aside",
                        "header",
                        "footer",
                        "main",
                        "section",
                        "h1",
                        "h2",
                        "h3",
                        "h4",
                        "h5",
                        "h6",
                    }

                    LIST_TAGS = {"ul", "ol"}

                    def __init__(self, outer: "TextExtractor"):
                        super().__init__()
                        self.outer = outer
                        self._ignore_stack: list[str] = []

                    def handle_starttag(self, tag, attrs):
                        tag = tag.lower()
                        if tag in ("script", "style"):
                            self._ignore_stack.append(tag)
                            return

                        if self._ignore_stack:
                            return

                        if tag == "br":
                            self.outer._append_break(False)
                            return

                        if tag in self.DOUBLE_BREAK_TAGS:
                            self.outer._append_break(True)
                        elif tag in self.BLOCK_BREAK_TAGS:
                            self.outer._append_break(False)

                        if tag in self.LIST_TAGS:
                            self.outer._list_stack.append({"type": tag, "index": 1})
                            return

                        if tag == "li":
                            self.outer._append_break(False)
                            prefix = "• "
                            if self.outer._list_stack:
                                top = self.outer._list_stack[-1]
                                if top["type"] == "ol":
                                    prefix = f"{top['index']}. "
                                    top["index"] += 1
                            self.outer._pending_prefix = prefix
                            return

                        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                            self.outer._heading_level = tag
                            return

                        if tag == "a":
                            attrs_dict = {k.lower(): v for k, v in attrs}
                            href = attrs_dict.get("href") or ""
                            resolved = urljoin(self.outer.base_url, href) if href else ""
                            self.outer._anchor_stack.append(resolved)
                            return

                    def handle_endtag(self, tag):
                        tag = tag.lower()
                        if self._ignore_stack and self._ignore_stack[-1] == tag:
                            self._ignore_stack.pop()
                            return

                        if self._ignore_stack:
                            return

                        if tag == "li":
                            self.outer._append_break(False)
                            return

                        if tag in ("ul", "ol") and self.outer._list_stack:
                            self.outer._list_stack.pop()
                            self.outer._append_break(True)
                            return

                        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                            self.outer._append_break(True)
                            self.outer._heading_level = None
                            return

                        if tag == "a" and self.outer._anchor_stack:
                            self.outer._anchor_stack.pop()

                    def handle_data(self, data):
                        if self._ignore_stack or not data:
                            return
                        text = unescape(data)
                        if self.outer._heading_level:
                            text = text.upper()
                        if self.outer._anchor_stack:
                            href = self.outer._anchor_stack[-1]
                            self.outer._append_link(text, href)
                        else:
                            self.outer._append_text(text)

                self.base_url = base_url
                self._segments: list[tuple] = []
                self._pending_prefix: Optional[str] = None
                self._heading_level: Optional[str] = None
                self._anchor_stack: list[str] = []
                self._list_stack: list[dict] = []
                self._parser = _Parser(self)

            def _append_break(self, hard: bool):
                self._pending_prefix = None
                if not self._segments:
                    return
                kind, *rest = self._segments[-1]
                if kind == "break":
                    if hard and not rest[0]:
                        self._segments[-1] = ("break", True)
                    return
                self._segments.append(("break", hard))

            def _consume_prefix(self) -> str:
                prefix = self._pending_prefix or ""
                self._pending_prefix = None
                return prefix

            def _append_text(self, text: str):
                cleaned = re.sub(r"\s+", " ", text)
                if not cleaned.strip():
                    return
                prefix = self._consume_prefix()
                self._segments.append(("text", prefix, cleaned.strip()))

            def _append_link(self, text: str, href: str):
                cleaned = re.sub(r"\s+", " ", text)
                if not cleaned.strip():
                    return
                prefix = self._consume_prefix()
                self._segments.append(("link", prefix, cleaned.strip(), href))

            def feed(self, html: str):
                self._parser.feed(html)

            def get_text(self) -> str:
                if not self._segments:
                    return ""
                parts: list[str] = []
                for segment in self._segments:
                    kind = segment[0]
                    if kind == "break":
                        if not parts:
                            continue
                        hard = segment[1]
                        if hard:
                            if parts[-1].endswith("\n"):
                                if not parts[-1].endswith("\n\n"):
                                    parts[-1] = parts[-1] + "\n"
                            else:
                                parts.append("\n\n")
                        else:
                            if not parts[-1].endswith("\n"):
                                parts.append("\n")
                        continue

                    if kind == "text":
                        _, prefix, content = segment
                        chunk = (prefix or "") + content
                    else:
                        _, prefix, content, href = segment
                        if href:
                            chunk = (prefix or "") + f"{content} [{href}]"
                        else:
                            chunk = (prefix or "") + content

                    if not chunk:
                        continue
                    if parts and not parts[-1].endswith(("\n", " ")):
                        parts.append(" ")
                    parts.append(chunk)

                text_output = "".join(parts).strip()
                text_output = re.sub(r"\n{3,}", "\n\n", text_output)
                return text_output

            def get_html(self) -> str:
                if not self._segments:
                    return ""
                parts: list[str] = ["<div class=\"solarren-document\">"]
                last_was_break = True
                for segment in self._segments:
                    kind = segment[0]
                    if kind == "break":
                        if len(parts) == 1:
                            continue
                        hard = segment[1]
                        parts.append("<br/><br/>" if hard else "<br/>")
                        last_was_break = True
                        continue

                    if kind == "text":
                        _, prefix, content = segment
                        chunk = (prefix or "") + content
                        chunk = chunk.strip()
                        if not chunk:
                            continue
                        if not last_was_break:
                            parts.append(" ")
                        parts.append(escape(chunk))
                        last_was_break = False
                    else:
                        _, prefix, content, href = segment
                        chunk = (prefix or "") + content
                        chunk = chunk.strip()
                        if not chunk:
                            continue
                        if not last_was_break:
                            parts.append(" ")
                        if href:
                            safe_href = escape(href, quote=True)
                            parts.append(f'<a href="{safe_href}">{escape(chunk)}</a>')
                        else:
                            parts.append(escape(chunk))
                        last_was_break = False

                parts.append("</div>")
                html_output = "".join(parts)
                html_output = re.sub(r"(<br/>\s*){3,}", "<br/><br/>", html_output)
                return html_output

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
                self._viewer = QtWidgets.QTextBrowser()
                self._viewer.setOpenExternalLinks(False)
                self._viewer.setOpenLinks(False)
                self._viewer.anchorClicked.connect(self.load)
                self._viewer.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
                self._viewer.setAcceptRichText(True)
                layout.addWidget(self._status)
                layout.addWidget(self._viewer, 1)

                self._contentReady.connect(self._apply_content)
                self.setSource = self.load  # compatibility with minimal backend usage

            def sizeHint(self):  # pragma: no cover - simple Qt size hint
                return QtCore.QSize(800, 600)

            def url(self):
                return QtCore.QUrl(self._url)

            @QtCore.pyqtSlot(str, str, str, bool)
            def _apply_content(self, url_str: str, title: str, content_html: str, success: bool):
                self._url = QtCore.QUrl(url_str)
                self._status.setText(f"SolarRen → {url_str}")
                document_html = self._wrap_document(url_str, title, content_html)
                self._viewer.document().setBaseUrl(self._url)
                self._viewer.setHtml(document_html)
                self.titleChanged.emit(title)
                self.loadFinished.emit(success)

            def _wrap_document(self, url_str: str, title: str, body_html: str) -> str:
                palette = self._viewer.palette()
                base = palette.color(palette.ColorRole.Base)
                text = palette.color(palette.ColorRole.Text)
                link = palette.color(palette.ColorRole.Link)
                muted = palette.color(palette.ColorRole.Mid)

                def qcolor_to_css(color: "QtGui.QColor") -> str:
                    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()/255:.3f})"

                stylesheet = textwrap.dedent(
                    f"""
                    body {{
                        background-color: {qcolor_to_css(base)};
                        color: {qcolor_to_css(text)};
                        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                        font-size: 14px;
                        margin: 0;
                        padding: 0;
                    }}

                    a {{
                        color: {qcolor_to_css(link)};
                    }}

                    .solarren-wrapper {{
                        padding: 12px 16px;
                    }}

                    .solarren-header {{
                        margin-bottom: 12px;
                    }}

                    .solarren-header h1 {{
                        font-size: 20px;
                        margin: 0;
                        font-weight: 600;
                    }}

                    .solarren-url {{
                        font-size: 12px;
                        color: {qcolor_to_css(muted)};
                    }}

                    .solarren-document {{
                        white-space: pre-wrap;
                        line-height: 1.55;
                        font-family: "JetBrains Mono", "Fira Code", "Source Code Pro", monospace;
                        font-size: 13px;
                    }}
                    """
                ).strip()

                safe_title = escape(title or url_str)
                safe_url = escape(url_str)
                header_html = (
                    "<div class=\"solarren-header\">"
                    f"<h1>{safe_title}</h1>"
                    f"<div class=\"solarren-url\"><a href=\"{safe_url}\">{safe_url}</a></div>"
                    "</div>"
                )

                body_section = body_html or "<div class=\"solarren-document\">[No textual content rendered]</div>"

                return (
                    "<html><head><meta charset=\"utf-8\"/>"
                    f"<style>{stylesheet}</style>"
                    "</head><body>"
                    "<div class=\"solarren-wrapper\">"
                    f"{header_html}{body_section}"
                    "</div></body></html>"
                )

            def load(self, url):
                if isinstance(url, QtCore.QUrl):
                    qurl = QtCore.QUrl(url)
                else:
                    qurl = QtCore.QUrl(str(url))
                if not qurl.scheme():
                    qurl.setScheme("https")

                if qurl.scheme() == "about" and qurl.path().lower() in ("", "blank"):
                    ready_html = "<div class=\"solarren-document\">SolarRen ready.</div>"
                    self._contentReady.emit(qurl.toString(), "about:blank", ready_html, True)
                    return

                self._status.setText(f"Loading {qurl.toString()} …")
                loading_html = "<div class=\"solarren-document\">Loading…</div>"
                self._viewer.document().setBaseUrl(qurl)
                self._viewer.setHtml(self._wrap_document(qurl.toString(), "Loading…", loading_html))
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

                        extractor = TextExtractor(url_str)
                        extractor.feed(html_text)
                        body_html = extractor.get_html()
                        if not body_html:
                            body_html = "<div class=\"solarren-document\">[No textual content rendered]</div>"
                        self._contentReady.emit(url_str, page_title, body_html, True)
                    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
                        error_html = (
                            "<div class=\"solarren-document\">"
                            f"SolarRen failed to load {escape(url_str)}:\n{escape(str(exc))}"
                            "</div>"
                        )
                        self._contentReady.emit(url_str, url_str, error_html, False)
                    except Exception as exc:
                        error_html = (
                            "<div class=\"solarren-document\">"
                            f"SolarRen failed to load {escape(url_str)}:\n{escape(str(exc))}"
                            "</div>"
                        )
                        self._contentReady.emit(url_str, url_str, error_html, False)

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
