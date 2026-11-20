import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ai import service  # noqa: E402


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    """Caché temporal, sin red real y modo LLM con clave falsa por defecto."""
    monkeypatch.setattr(service, "CACHE_DIR", tmp_path / "cache")
    service.clear_memory_cache()
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("LLM_API_KEY", "test-key-not-real")

    def _no_network(*a, **k):
        raise AssertionError("llamada HTTP no simulada")

    monkeypatch.setattr("app.ai.llm.httpx.post", _no_network)
    yield
    service.clear_memory_cache()


class FakeResp:
    def __init__(self, content, status=200):
        self.content_text = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError("err", request=None, response=None)

    def json(self):
        return {"choices": [{"message": {"content": self.content_text}}]}


@pytest.fixture
def fake_llm(monkeypatch):
    """Devuelve un objeto con .answers (lista o callable) y .calls."""

    class Fake:
        def __init__(self):
            self.calls = []
            self.answers = []

        def __call__(self, url, **kwargs):
            self.calls.append(kwargs)
            a = self.answers(kwargs) if callable(self.answers) else self.answers.pop(0)
            return a if isinstance(a, FakeResp) else FakeResp(a)

    fake = Fake()
    monkeypatch.setattr("app.ai.llm.httpx.post", fake)
    return fake
