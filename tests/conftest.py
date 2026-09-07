import pytest

from app.store import store


@pytest.fixture(autouse=True)
def _isolated_demo_store(monkeypatch):
    """每个测试从干净演示数据集开始；测试期间强制 demo 模式避免意外联网。"""
    monkeypatch.setenv("LLM_MODE", "demo")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    store.reset_demo()
    yield
    store.reset_demo()
