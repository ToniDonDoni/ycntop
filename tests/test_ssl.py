import json

from src import article_fetcher
from src.hn_client import HNClient


class _DummyResponse:
    def __init__(self, payload: bytes):
        self._payload = payload
        self.headers = self

    def get_content_charset(self):
        return "utf-8"

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_hn_client_uses_ssl_context_in_urlopen(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout, context):
        captured["context"] = context
        return _DummyResponse(json.dumps([1, 2, 3]).encode("utf-8"))

    client = HNClient()
    sentinel_context = object()
    client.ssl_context = sentinel_context
    monkeypatch.setattr("src.hn_client.urlopen", fake_urlopen)

    data = client._get_json("https://example.com/api.json")

    assert data == [1, 2, 3]
    assert captured["context"] is sentinel_context


def test_article_fetcher_uses_ssl_context_in_urlopen(monkeypatch):
    captured = {}
    sentinel_context = object()

    def fake_build_ssl_context():
        return sentinel_context

    def fake_urlopen(request, timeout, context):
        captured["context"] = context
        return _DummyResponse(b"<html>ok</html>")

    monkeypatch.setattr(article_fetcher, "_build_ssl_context", fake_build_ssl_context)
    monkeypatch.setattr(article_fetcher, "urlopen", fake_urlopen)

    body = article_fetcher.fetch_url("https://example.com")

    assert body == "<html>ok</html>"
    assert captured["context"] is sentinel_context
