import json

from src import article_fetcher
from src import llm_interest
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


def test_llm_interest_uses_verified_ssl_by_default(monkeypatch):
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"output_text":"{\\"score\\": 5, \\"reason\\": \\"good\\"}"}'

    calls = {}
    sentinel_context = object()
    llm_interest.set_llm_insecure_ssl(False)

    def fake_build_ssl_context(*, insecure):
        calls["insecure"] = insecure
        return sentinel_context

    def fake_urlopen(request, timeout, context):
        calls["context"] = context
        return _Resp()

    monkeypatch.setattr(llm_interest, "_build_ssl_context", fake_build_ssl_context)
    monkeypatch.setattr(llm_interest, "urlopen", fake_urlopen)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    result = llm_interest.score_title_with_llm("A title")

    assert result.status == "ok"
    assert calls["insecure"] is False
    assert calls["context"] is sentinel_context


def test_llm_interest_uses_unverified_ssl_when_enabled(monkeypatch):
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"output_text":"{\\"score\\": 5, \\"reason\\": \\"good\\"}"}'

    calls = {}
    sentinel_context = object()
    llm_interest.set_llm_insecure_ssl(True)

    def fake_build_ssl_context(*, insecure):
        calls["insecure"] = insecure
        return sentinel_context

    def fake_urlopen(request, timeout, context):
        calls["context"] = context
        return _Resp()

    monkeypatch.setattr(llm_interest, "_build_ssl_context", fake_build_ssl_context)
    monkeypatch.setattr(llm_interest, "urlopen", fake_urlopen)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    result = llm_interest.score_title_with_llm("Another title")

    assert result.status == "ok"
    assert calls["insecure"] is True
    assert calls["context"] is sentinel_context
