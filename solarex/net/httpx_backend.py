import httpx
from types import SimpleNamespace


def init(core):
    core.net = HTTPXBackend(core)


class HTTPXBackend:
    def __init__(self, core=None):
        self._core = core
        self._headers = {"User-Agent": self._determine_user_agent()}
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=20,
            headers=self._headers,
        )

    def _determine_user_agent(self) -> str:
        ua = None
        if self._core is not None:
            args = getattr(self._core, "args", None)
            ua = getattr(args, "ua", None)
        return ua or "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) SolarEx/1.0"

    def fetch(self, url: str):
        r = self._client.get(url)
        return SimpleNamespace(
            url=str(r.url),
            status=r.status_code,
            headers=dict(r.headers),
            content=r.content,
            mime=r.headers.get("content-type", "application/octet-stream"),
        )

    def get_text(self, url: str, encoding="utf-8"):
        r = self._client.get(url)
        r.encoding = encoding if encoding else r.encoding
        return r.text

    def close(self):
        self._client.close()
