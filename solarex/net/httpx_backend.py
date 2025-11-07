import httpx
from types import SimpleNamespace


def init(core):
    core.net = HTTPXBackend()


class HTTPXBackend:
    def __init__(self):
        self._client = httpx.Client(follow_redirects=True, timeout=20)
    def fetch(self, url: str):
        r = self._client.get(url)
        return SimpleNamespace(
            url=str(r.url),
            status=r.status_code,
            headers=dict(r.headers),
            content=r.content,
            mime=r.headers.get("content-type", "application/octet-stream"),
        )
    def close(self):
        self._client.close()
