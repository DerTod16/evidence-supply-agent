"""LLM 网关与降级路径测试：远程模型不可用时系统仍可用（纯确定性）。"""

import pytest

from app.llm import LLMError, generate_summary, llm_enabled
from app.models import AskRequest, LlmSummary, Requirement
from app.service import compose_answer


@pytest.fixture(autouse=True)
def _force_demo_env(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_MODE", "demo")
    yield
    monkeypatch.delenv("LLM_API_KEY", raising=False)


def test_demo_mode_disables_llm():
    assert llm_enabled() is False


def test_remote_requires_api_key(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "remote")
    assert llm_enabled() is False  # 无 API key 时不联网
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    assert llm_enabled() is True


def test_generate_summary_raises_when_disabled():
    with pytest.raises(LLMError):
        generate_summary(Requirement(), [])


def test_llm_summary_rejects_unauthorized_fact_fields():
    """模型输出即使夹带 score/status，也会被 schema 丢弃（extra fields ignored）。"""
    summary = LlmSummary.model_validate({
        "answer": "值得关注 A 与 B",
        "score": 100,
        "verification_status": "verified",
        "price_cny": 1.0,
        "market_context": None,
        "candidate_notes": {"a": "低价但起批量大"},
    })
    assert summary.answer == "值得关注 A 与 B"
    assert summary.market_context is None
    assert not hasattr(summary, "score")
    assert not hasattr(summary, "verification_status")


def _request() -> AskRequest:
    return AskRequest(question="找手机支架货源", requirement=Requirement(category="手机支架"))


def test_compose_falls_back_on_llm_error(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "remote")
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    # compose_answer 位于 service，patch 其直接绑定名
    monkeypatch.setattr("app.service.generate_summary", lambda requirement, recs: (_ for _ in ()).throw(LLMError("boom")))
    used, error, answer = compose_answer(_request(), [])
    assert used is False
    assert error == "boom"
    assert "演示" in answer  # 确定性模板兜底


def test_compose_uses_llm_answer_when_available(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "remote")
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setattr(
        "app.service.generate_summary",
        lambda requirement, recs: LlmSummary(answer="A 低价可作引流款", market_context="该类目夏季为旺季"),
    )
    used, error, answer = compose_answer(_request(), [])
    assert used is True
    assert error is None
    assert "A 低价可作引流款" in answer
    assert "夏季为旺季" in answer
