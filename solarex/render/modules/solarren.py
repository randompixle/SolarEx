from PyQt6 import QtWidgets, QtCore, QtGui
from bs4 import BeautifulSoup
from html import escape
import httpx, os, base64, urllib.parse, re, textwrap

metadata = {
    "id": "solarren",
    "name": "SolarRen Ultra",
    "description": "HTML parser with GET/POST forms, status bar, zoom/reload, favicon, async loader, DOM inspector",
    "version": "4.2.0"
}

def get_settings_schema(core):
    return [
        {"key": "font_size", "type": "spin", "label": "Font size", "min": 8, "max": 48, "step": 1, "default": 14},
        {"key": "wrap", "type": "checkbox", "label": "Word wrap", "default": True},
        {"key": "dark", "type": "checkbox", "label": "Dark theme", "default": True},
    ]

# ---------------- helpers ----------------

def _abs(base, url):
    return urllib.parse.urljoin(base, url) if url else ""

def _ensure_statusbar(win: QtWidgets.QMainWindow|None):
    if isinstance(win, QtWidgets.QMainWindow):
        if not win.statusBar():
            win.setStatusBar(QtWidgets.QStatusBar(win))
        return win.statusBar()
    return None

def _parse_inline_css(style_str: str):
    out = {}
    for part in (style_str or "").split(";"):
        if ":" not in part: continue
        k, v = [s.strip().lower() for s in part.split(":", 1)]
        if k in ("color", "background", "background-color", "font-size"):
            out[k] = v
    return out

def _inject_supported_styles(tag, style_dict):
    existing = tag.get("style", "")
    if "background" in style_dict and "background-color" not in style_dict:
        style_dict["background-color"] = style_dict["background"]
    app = []
    if "color" in style_dict: app.append(f"color:{style_dict['color']}")
    if "background-color" in style_dict: app.append(f"background-color:{style_dict['background-color']}")
    if "font-size" in style_dict: app.append(f"font-size:{style_dict['font-size']}")
    merged = (existing + ";" + ";".join(app)).strip(";")
    if merged: tag["style"] = merged

# ---------------- async fetcher ----------------

DEFAULT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) SolarEx/4.2"


class FetchWorker(QtCore.QThread):
    chunk = QtCore.pyqtSignal(int)          # percent
    done  = QtCore.pyqtSignal(str, str)     # html, url
    error = QtCore.pyqtSignal(str)

    def __init__(self, url, backend, timeout=20.0, user_agent: str | None = None):
        super().__init__()
        self.url = url
        self.backend = backend
        self.timeout = timeout
        self.user_agent = user_agent or DEFAULT_USER_AGENT

    def run(self):
        try:
            # Prefer SolarEx backend (cookies/UA)
            if hasattr(self.backend, "get_text"):
                html = self.backend.get_text(self.url)
                self.done.emit(html, self.url); return
            if hasattr(self.backend, "fetch"):
                resp = self.backend.fetch(self.url)
                html = getattr(resp, "text", None) or resp.content.decode("utf-8", "ignore")
                self.done.emit(html, self.url); return

            client = httpx.Client(
                follow_redirects=True,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
            )
            r = client.stream("GET", self.url)
            total = int(r.headers.get("content-length") or 0)
            buf = bytearray()
            with r as resp:
                for b in resp.iter_bytes():
                    buf.extend(b)
                    if total:
                        self.chunk.emit(min(99, int(len(buf)*100/total)))
            self.done.emit(buf.decode("utf-8", "ignore"), self.url)
        except Exception as e:
            self.error.emit(str(e))

# ---------------- main view ----------------

class HoverEventFilter(QtCore.QObject):
    def __init__(self, parent, status_hook):
        super().__init__(parent)
        self.parent = parent
        self.status_hook = status_hook
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.ToolTip:
            cursor = self.parent.cursorForPosition(event.pos())
            href = cursor.charFormat().anchorHref()
            if href:
                QtWidgets.QToolTip.showText(event.globalPos(), href)
                self.status_hook(href)
        return super().eventFilter(obj, event)

class SolarRenView(QtWidgets.QScrollArea):
    def __init__(self, core):
        super().__init__()
        self.core = core
        self.setWidgetResizable(True)

        self.user_agent = getattr(getattr(core, "args", None), "ua", None) or DEFAULT_USER_AGENT

        self.canvas = QtWidgets.QTextBrowser()
        self.setWidget(self.canvas)

        self.client = httpx.Client(
            follow_redirects=True,
            timeout=20.0,
            headers={"User-Agent": self.user_agent},
        )
        self.cache_dir = os.path.join(core.profile.storage_path, "cache", "images")
        os.makedirs(self.cache_dir, exist_ok=True)

        fs = core.settings.get_ns("renderer.solarren", "font_size", 14)
        font = self.canvas.font(); font.setPointSize(fs); self.canvas.setFont(font)
        wrap = core.settings.get_ns("renderer.solarren", "wrap", True)
        self.canvas.setLineWrapMode(
            QtWidgets.QTextEdit.LineWrapMode.WidgetWidth if wrap
            else QtWidgets.QTextEdit.LineWrapMode.NoWrap
        )

        # Events
        self.canvas.anchorClicked.connect(self._on_link_clicked)
        self.hover_filter = HoverEventFilter(self.canvas, self._show_status)
        self.canvas.installEventFilter(self.hover_filter)

        # Shortcuts
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+R"), self.canvas, activated=self.reload)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+="), self.canvas, activated=lambda: self._zoom(1))
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl++"), self.canvas, activated=lambda: self._zoom(1))
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+-"), self.canvas, activated=lambda: self._zoom(-1))
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+0"), self.canvas, activated=self._zoom_reset)
        QtGui.QShortcut(QtGui.QKeySequence("F12"),    self.canvas, activated=self._toggle_dom_inspector)

        self._dom_dock = None
        self._dom_tree = None
        self._last_zoom_delta = 0
        self._last_soup = None
        self.current_url = "about:blank"

    # ---- status bar ----
    def _show_status(self, text: str):
        sb = _ensure_statusbar(self.window())
        if sb: sb.showMessage(text, 3000)

    # ---- favicon ----
    def _set_favicon(self, base_url, soup):
        try:
            link = soup.find("link", rel=re.compile("icon", re.I))
            href = link.get("href") if link else None
            if not href: return
            absu = _abs(base_url, href)
            name = base64.urlsafe_b64encode(absu.encode()).decode()[:48] + ".ico"
            path = os.path.join(self.cache_dir, name)
            if not os.path.exists(path):
                data = self.client.get(absu).content
                with open(path, "wb") as f: f.write(data)
            pix = QtGui.QPixmap(path)
            if not pix.isNull():
                icon = QtGui.QIcon(pix)
                win = self.window()
                if isinstance(win, QtWidgets.QMainWindow): win.setWindowIcon(icon)
        except Exception:
            pass

    # ---- images ----
    def _image_local(self, abs_url):
        try:
            if not abs_url: return ""
            if abs_url.startswith("data:image/"): return abs_url
            name = base64.urlsafe_b64encode(abs_url.encode()).decode()[:48] + ".img"
            path = os.path.join(self.cache_dir, name)
            if not os.path.exists(path):
                r = self.client.get(abs_url)
                r.raise_for_status()
                with open(path, "wb") as f: f.write(r.content)
            return "file://" + path if os.path.getsize(path) else ""
        except Exception as e:
            print("[SolarRen] image fetch failed:", e)
            return ""

    # ---- forms ----
    def _rewrite_forms(self, soup, base_url):
        for form in soup.find_all("form"):
            method = (form.get("method") or "get").lower()
            action = _abs(base_url, form.get("action") or base_url)
            fields = []
            # inputs + textarea basics
            for inp in list(form.find_all("input")) + list(form.find_all("textarea")):
                t = (inp.get("type") or "text").lower()
                name = inp.get("name")
                if not name: continue
                if t in ("text","search","password","email","url","number") or inp.name == "textarea":
                    fields.append(name)
                    marker = soup.new_tag("span"); marker.string = f"[{name}]"; inp.replace_with(marker)
                elif t in ("submit","button"):
                    inp.decompose()
            fld = ",".join(fields)
            link = soup.new_tag(
                "a",
                href=f"solarren://form_submit?method={method}&action={urllib.parse.quote(action)}&fields={urllib.parse.quote(fld)}"
            )
            link.string = "[ Submit ]"
            form.append(link)

    def _handle_form_submit(self, url: str):
        qs = urllib.parse.urlparse(url).query
        args = dict(urllib.parse.parse_qsl(qs))
        action = urllib.parse.unquote(args.get("action", ""))
        method = (args.get("method", "get")).lower()
        fields = [f for f in (urllib.parse.unquote(args.get("fields", "")).split(",")) if f]

        data = {}
        for name in fields:
            text, ok = QtWidgets.QInputDialog.getText(self, "Form field", f"{name}:")
            if not ok: return
            data[name] = text

        try:
            if method == "get":
                q = urllib.parse.urlencode(data, doseq=True)
                joiner = "&" if urllib.parse.urlparse(action).query else "?"
                self.load(action + (joiner + q if q else ""))
            else:
                r = self.client.post(action, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
                self._render(action, r.text)
        except Exception as e:
            self.canvas.setPlainText(f"[SolarRen] form error: {e}")

    # ---- DOM inspector ----
    def _toggle_dom_inspector(self):
        win = self.window()
        if not isinstance(win, QtWidgets.QMainWindow): return
        if self._dom_dock and self._dom_dock.isVisible():
            self._dom_dock.hide(); return
        if not self._dom_dock:
            self._dom_dock = QtWidgets.QDockWidget("DOM Inspector", win)
            self._dom_tree = QtWidgets.QTreeWidget()
            self._dom_tree.setHeaderLabels(["Node", "Attrs"])
            self._dom_dock.setWidget(self._dom_tree)
            win.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self._dom_dock)
        self._dom_dock.show()
        if self._last_soup: self._populate_dom_tree(self._last_soup)

    def _populate_dom_tree(self, soup):
        self._dom_tree.clear()
        def add_node(parent, tag):
            if isinstance(tag, str):
                if tag.strip(): QtWidgets.QTreeWidgetItem(parent, ["#text", tag.strip()[:80]]); return
            label = getattr(tag, "name", "#")
            attrs = " ".join([f'{k}="{v}"' for k,v in getattr(tag, "attrs", {}).items()])
            item = QtWidgets.QTreeWidgetItem(parent, [label, attrs])
            for ch in getattr(tag, "children", []): add_node(item, ch)
        root = self._dom_tree.invisibleRootItem()
        add_node(root, (soup.body or soup))
        self._dom_tree.expandToDepth(2)

    # ---- zoom/reload ----
    def _zoom(self, delta):
        if delta > 0: self.canvas.zoomIn(1)
        else: self.canvas.zoomOut(1)
        self._last_zoom_delta += delta
    def _zoom_reset(self):
        if self._last_zoom_delta > 0:
            for _ in range(self._last_zoom_delta): self.canvas.zoomOut(1)
        elif self._last_zoom_delta < 0:
            for _ in range(-self._last_zoom_delta): self.canvas.zoomIn(1)
        self._last_zoom_delta = 0
    def reload(self): self.load(self.current_url)

    # ---- events ----
    def _on_link_clicked(self, qurl: QtCore.QUrl):
        url = qurl.toString()
        if url.startswith("solarren://form_submit"):
            self._handle_form_submit(url); return
        if url.startswith("solarren://google_search"):
            self._handle_google_search(url); return
        self.load(url)

    # ---- public ----
    def load(self, qurl):
        url = qurl.toString() if hasattr(qurl, "toString") else str(qurl)
        self.current_url = url
        self.canvas.setPlainText(f"[SolarRen] Loading {url} …")
        self._show_status(f"Loading {url}")

        backend = getattr(self.core, "net", None) or self.core.require("net")
        self._worker = FetchWorker(url, backend, user_agent=self.user_agent)
        self._worker.chunk.connect(lambda p: self._show_status(f"Downloading… {p}%"))
        self._worker.done.connect(lambda html, u: self._render(u, html))
        self._worker.error.connect(lambda msg: self.canvas.setPlainText(f"[SolarRen] fetch failed: {msg}"))
        self._worker.start()

    # ---- render ----
    def _render(self, base_url, html):
        soup = BeautifulSoup(html, "html.parser")
        # Keep inline styles; drop scripts & <noscript>
        for s in soup(["script","noscript"]): s.decompose()

        # Title + favicon
        title_tag = soup.find("title")
        title = title_tag.text.strip() if title_tag else base_url
        win = self.window()
        if isinstance(win, QtWidgets.QMainWindow): win.setWindowTitle(f"SolarEx - {title}")
        self._set_favicon(base_url, soup)

        if self._render_google_if_applicable(base_url, soup, title):
            return

        # Inline styles pass-through (subset)
        for tag in soup.find_all(True):
            sty = _parse_inline_css(tag.get("style", ""))
            if sty: _inject_supported_styles(tag, sty)

        # Forms and images
        self._rewrite_forms(soup, base_url)
        for img in soup.find_all("img"):
            src = img.get("src")
            absu = _abs(base_url, src) if src else ""
            img["src"] = self._image_local(absu) if absu else ""

        # Iframes -> placeholders
        for iframe in soup.find_all("iframe"):
            src = iframe.get("src")
            iframe.replace_with(soup.new_tag("div", string=f"[iframe: {_abs(base_url, src)}]" if src else "[iframe]"))

        # Basic structural pretties
        self._enhance_blocks(soup)

        # Theme
        dark = self.core.settings.get_ns("renderer.solarren", "dark", True)
        bg = "#0f111a" if dark else "#f5f6fa"
        fg = "#d5d9e2" if dark else "#1f2530"
        accent = "#4fa3ff" if dark else "#0a59c9"
        muted = "#5a6074" if dark else "#6f778b"

        stylesheet = textwrap.dedent(
            f"""
            :root {{ color-scheme: {'dark' if dark else 'light'}; }}
            body {{
                margin: 0;
                padding: 32px;
                background: radial-gradient(circle at top, {bg} 0%, {bg} 45%, {('#05060a' if dark else '#e4e7ef')} 100%);
                color: {fg};
                font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
                display: flex;
                justify-content: center;
            }}
            a {{ color: {accent}; }}
            a:hover {{ color: {accent}; text-decoration: underline; }}
            .solarren-wrapper {{ width: 100%; max-width: 960px; }}
            .solarren-toolbar {{
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px 16px;
                border-radius: 12px;
                background: {('#161a2b' if dark else '#ffffff')};
                border: 1px solid {muted};
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.18);
                margin-bottom: 20px;
            }}
            .solarren-location {{
                flex: 1;
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
                font-size: 12px;
                display: flex;
                gap: 4px;
                overflow: hidden;
                white-space: nowrap;
                text-overflow: ellipsis;
            }}
            .solarren-location span {{ overflow: hidden; text-overflow: ellipsis; }}
            .solarren-location-protocol {{ opacity: 0.6; }}
            .solarren-location-host {{ font-weight: 600; }}
            .solarren-location-path {{ opacity: 0.7; }}
            .solarren-open {{
                padding: 8px 14px;
                border-radius: 8px;
                border: 1px solid {accent};
                text-decoration: none;
                color: {accent};
            }}
            .solarren-open:hover {{ background: {accent}; color: {bg}; }}
            .solarren-surface {{
                background: {('#161a2b' if dark else '#ffffff')};
                border-radius: 16px;
                border: 1px solid {muted};
                box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
                padding: 28px;
            }}
            .solarren-header h1 {{ margin: 0 0 6px 0; font-size: 22px; }}
            .solarren-url {{ font-size: 12px; color: {muted}; }}
            .solarren-content {{ margin-top: 20px; }}
            .solarren-document {{
                line-height: 1.65;
                font-size: 14px;
            }}
            .solarren-document pre {{
                background: {('#0f1220' if dark else '#f1f3f8')};
                border-radius: 8px;
                padding: 12px;
                overflow-x: auto;
            }}
            .solarren-document img {{ max-width: 100%; height: auto; }}
            .solarren-document table {{
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
            }}
            .solarren-document th,
            .solarren-document td {{
                border: 1px solid {muted};
                padding: 6px 8px;
            }}
            .solarren-control {{
                margin: 12px 0;
                padding: 12px;
                border-radius: 8px;
                border: 1px dashed {muted};
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
            }}
            """
        ).strip()

        parsed = urllib.parse.urlparse(base_url)
        protocol_display = f"{parsed.scheme}://" if parsed.scheme else ""
        host_display = parsed.hostname or parsed.netloc or base_url
        path_parts = parsed.path or ""
        if parsed.params:
            path_parts += f";{parsed.params}"
        if parsed.query:
            path_parts += f"?{parsed.query}"
        if parsed.fragment:
            path_parts += f"#{parsed.fragment}"

        safe_protocol = escape(protocol_display)
        safe_host = escape(host_display)
        safe_path = escape(path_parts)
        safe_url = escape(base_url)
        safe_title = escape(title)

        location_html = (
            "<div class=\"solarren-location\">"
            f"<span class=\"solarren-location-protocol\">{safe_protocol}</span>"
            f"<span class=\"solarren-location-host\">{safe_host}</span>"
            f"<span class=\"solarren-location-path\">{safe_path}</span>"
            "</div>"
        )
        toolbar_html = (
            "<div class=\"solarren-toolbar\">"
            f"{location_html}"
            f"<a class=\"solarren-open\" href=\"{safe_url}\" target=\"_blank\">Open original</a>"
            "</div>"
        )

        header_html = (
            "<div class=\"solarren-header\">"
            f"<h1>{safe_title}</h1>"
            f"<div class=\"solarren-url\">{safe_url}</div>"
            "</div>"
        )

        body_node = soup.body or soup
        if getattr(body_node, "name", "").lower() == "body":
            body_fragment = "".join(str(child) for child in body_node.children)
        else:
            body_fragment = str(body_node)

        document_html = f'<div class="solarren-document">{body_fragment}</div>'

        html_output = (
            "<html><head><meta charset=\"utf-8\"/>"
            f"<style>{stylesheet}</style>"
            "</head><body>"
            "<div class=\"solarren-wrapper\">"
            f"{toolbar_html}<div class=\"solarren-surface\">{header_html}<div class=\"solarren-content\">{document_html}</div></div>"
            "</div>"
            "</body></html>"
        )

        self.canvas.setHtml(html_output)
        self.canvas.document().setBaseUrl(QtCore.QUrl(base_url))
        self._last_soup = soup
        self._show_status("Done")

    def _enhance_blocks(self, soup):
        for hr in soup.find_all("hr"):
            hr.replace_with(soup.new_tag("div", style="border-top:1px solid #444;margin:8px 0;"))
        for bq in soup.find_all("blockquote"):
            bq["style"] = (bq.get("style","")+";border-left:4px solid #555;padding-left:10px;color:#aaa;margin:6px 0;").strip(";")
        for code in soup.find_all("code"):
            code["style"] = (code.get("style","")+";background:#222;padding:2px 4px;border-radius:4px;color:#6f6;").strip(";")
        for pre in soup.find_all("pre"):
            pre["style"] = (pre.get("style","")+";background:#111;border:1px solid #333;padding:4px;font-family:monospace;color:#9f9;overflow:auto;").strip(";")
        for tbl in soup.find_all("table"):
            tbl["style"] = (tbl.get("style","")+";border-collapse:collapse;width:100%;margin:6px 0;").strip(";")
            for td in tbl.find_all(["td","th"]):
                td["style"] = (td.get("style","")+";border:1px solid #444;padding:4px;").strip(";")
        for ul in soup.find_all("ul"):
            ul["style"] = (ul.get("style","")+";margin-left:20px;list-style-type:disc;").strip(";")
        for ol in soup.find_all("ol"):
            ol["style"] = (ol.get("style","")+";margin-left:20px;list-style-type:decimal;").strip(";")
        for i in range(1,7):
            for h in soup.find_all(f"h{i}"):
                h["style"] = (h.get("style","")+f";color:#fff;margin:6px 0;font-size:{24 - i*2}px;").strip(";")

    def _render_google_if_applicable(self, base_url, soup, title):
        parsed = urllib.parse.urlparse(base_url)
        host = (parsed.hostname or parsed.netloc or "").lower()
        if not host.startswith("www.google."):
            return False

        search_form = soup.find("form")
        query_input = search_form.find("input", attrs={"name": "q"}) if search_form else None
        query_value = query_input.get("value", "") if query_input else ""
        action = _abs(base_url, search_form.get("action") if search_form else "https://www.google.com/search")

        results = []
        for res in soup.select("div#search div.g"):
            link = res.find("a", href=True)
            title_tag = res.find("h3")
            if not link or not title_tag:
                continue
            href = self._google_clean_link(_abs(base_url, link["href"]))
            snippet = ""
            snippet_tag = res.select_one("div.IsZvec") or res.select_one("div.VwiC3b") or res.select_one("span.aCOpRe")
            if snippet_tag:
                snippet = snippet_tag.get_text(" ", strip=True)
            else:
                snippet = res.get_text(" ", strip=True)
            results.append({
                "title": title_tag.get_text(" ", strip=True),
                "href": href,
                "display": urllib.parse.urlparse(href).netloc or href,
                "snippet": snippet,
            })

        cards = []
        for card in results:
            safe_title = escape(card["title"])
            safe_href = escape(card["href"])
            safe_display = escape(card["display"])
            safe_snippet = escape(card["snippet"])
            cards.append(
                "<div class=\"solarren-result\">"
                f"<a class=\"solarren-result-title\" href=\"{safe_href}\">{safe_title}</a>"
                f"<div class=\"solarren-result-link\">{safe_display}</div>"
                f"<div class=\"solarren-result-snippet\">{safe_snippet}</div>"
                "</div>"
            )

        safe_query = escape(query_value)
        safe_title = escape(title)
        safe_url = escape(base_url)
        action_encoded = urllib.parse.quote(action, safe="")
        query_encoded = urllib.parse.quote(query_value, safe="")

        stylesheet = self._build_stylesheet(self.core.settings.get_ns("renderer.solarren", "dark", True))
        display_query = safe_query or "—"
        results_html = ''.join(cards) if cards else '<div class="solarren-empty">No results.</div>'
        search_link = f"solarren://google_search?action={action_encoded}&q={query_encoded}"
        html_output = (
            "<html><head><meta charset=\"utf-8\"/>"
            f"<style>{stylesheet}</style>"
            "</head><body>"
            "<div class=\"solarren-wrapper\">"
            "<div class=\"solarren-toolbar\">"
            f"<div class=\"solarren-location\"><span class=\"solarren-location-host\">Google</span></div>"
            f"<a class=\"solarren-open\" href=\"{safe_url}\" target=\"_blank\">Open original</a>"
            "</div>"
            "<div class=\"solarren-surface\">"
            f"<div class=\"solarren-header\"><h1>{safe_title}</h1></div>"
            "<div class=\"solarren-google-search\">"
            f"<div class=\"solarren-google-query\">Query: {display_query}</div>"
            f"<a class=\"solarren-google-button\" href=\"{search_link}\">New search…</a>"
            "</div>"
            f"<div class=\"solarren-google-results\">{results_html}</div>"
            "</div>"
            "</div>"
            "</body></html>"
        )

        self.canvas.setHtml(html_output)
        self.canvas.document().setBaseUrl(QtCore.QUrl(base_url))
        self._last_soup = soup
        self._show_status("Google results ready")
        return True

    def _build_stylesheet(self, dark: bool) -> str:
        bg = "#0f111a" if dark else "#f5f6fa"
        fg = "#d5d9e2" if dark else "#1f2530"
        accent = "#4fa3ff" if dark else "#0a59c9"
        muted = "#5a6074" if dark else "#6f778b"
        surface = "#161a2b" if dark else "#ffffff"
        secondary_surface = "#1d2237" if dark else "#f0f3fb"
        code_bg = "#0f1220" if dark else "#f1f3f8"
        gradient_end = "#05060a" if dark else "#e4e7ef"

        return textwrap.dedent(
            f"""
            :root {{ color-scheme: {'dark' if dark else 'light'}; }}
            body {{
                margin: 0;
                padding: 32px;
                background: radial-gradient(circle at top, {bg} 0%, {bg} 45%, {gradient_end} 100%);
                color: {fg};
                font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
                display: flex;
                justify-content: center;
            }}
            a {{ color: {accent}; }}
            a:hover {{ color: {accent}; text-decoration: underline; }}
            .solarren-wrapper {{ width: 100%; max-width: 960px; }}
            .solarren-toolbar {{
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px 16px;
                border-radius: 12px;
                background: {surface};
                border: 1px solid {muted};
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.18);
                margin-bottom: 20px;
            }}
            .solarren-location {{
                flex: 1;
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
                font-size: 12px;
                display: flex;
                gap: 4px;
                overflow: hidden;
                white-space: nowrap;
                text-overflow: ellipsis;
            }}
            .solarren-location span {{ overflow: hidden; text-overflow: ellipsis; }}
            .solarren-location-protocol {{ opacity: 0.6; }}
            .solarren-location-host {{ font-weight: 600; }}
            .solarren-location-path {{ opacity: 0.7; }}
            .solarren-open {{
                padding: 8px 14px;
                border-radius: 8px;
                border: 1px solid {accent};
                text-decoration: none;
                color: {accent};
            }}
            .solarren-open:hover {{ background: {accent}; color: {bg}; }}
            .solarren-surface {{
                background: {surface};
                border-radius: 16px;
                border: 1px solid {muted};
                box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
                padding: 28px;
            }}
            .solarren-header h1 {{ margin: 0 0 6px 0; font-size: 22px; }}
            .solarren-url {{ font-size: 12px; color: {muted}; }}
            .solarren-content {{ margin-top: 20px; }}
            .solarren-document {{
                line-height: 1.65;
                font-size: 14px;
            }}
            .solarren-document pre {{
                background: {code_bg};
                border-radius: 8px;
                padding: 12px;
                overflow-x: auto;
            }}
            .solarren-document img {{ max-width: 100%; height: auto; }}
            .solarren-document table {{
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
            }}
            .solarren-document th,
            .solarren-document td {{
                border: 1px solid {muted};
                padding: 6px 8px;
            }}
            .solarren-control {{
                margin: 12px 0;
                padding: 12px;
                border-radius: 8px;
                border: 1px dashed {muted};
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
            }}
            .solarren-google-search {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
                padding: 12px 16px;
                border-radius: 12px;
                background: {secondary_surface};
                margin-bottom: 20px;
            }}
            .solarren-google-query {{ font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px; }}
            .solarren-google-button {{
                padding: 8px 16px;
                border-radius: 8px;
                border: 1px solid {accent};
                text-decoration: none;
                color: {accent};
                font-weight: 600;
            }}
            .solarren-google-button:hover {{ background: {accent}; color: {bg}; }}
            .solarren-google-results {{ display: flex; flex-direction: column; gap: 18px; }}
            .solarren-result {{
                padding: 16px;
                border-radius: 12px;
                background: {surface};
                border: 1px solid {muted};
                box-shadow: 0 4px 18px rgba(0, 0, 0, 0.18);
            }}
            .solarren-result-title {{ font-size: 18px; font-weight: 600; }}
            .solarren-result-link {{ font-size: 12px; color: {muted}; margin-top: 4px; }}
            .solarren-result-snippet {{ margin-top: 10px; line-height: 1.55; font-size: 13px; }}
            .solarren-empty {{ font-style: italic; color: {muted}; }}
            """
        ).strip()

    def _google_clean_link(self, href: str) -> str:
        try:
            parsed = urllib.parse.urlparse(href)
            if parsed.path == "/url" and parsed.query:
                params = urllib.parse.parse_qs(parsed.query)
                if "q" in params:
                    return params["q"][0]
                if "url" in params:
                    return params["url"][0]
            return href
        except Exception:
            return href

    def _handle_google_search(self, url: str):
        parsed = urllib.parse.urlparse(url)
        qs = dict(urllib.parse.parse_qsl(parsed.query))
        action = urllib.parse.unquote(qs.get("action", "https://www.google.com/search"))
        preset = urllib.parse.unquote(qs.get("q", ""))

        text, ok = QtWidgets.QInputDialog.getText(self, "Google search", "Query:", text=preset)
        if not ok:
            return
        query = text.strip()
        if not query:
            return
        sep = "&" if urllib.parse.urlparse(action).query else "?"
        self.load(f"{action}{sep}q={urllib.parse.quote(query)}")

def new_view(core, *a, **kw):
    return SolarRenView(core)
