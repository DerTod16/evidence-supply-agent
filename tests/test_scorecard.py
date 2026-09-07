"""评分工具与检索回归测试（确定性，不依赖网络）。"""

import pytest

from app.models import AskRequest, Requirement
from app.retrieval import retrieve_documents
from app.scorecard import score_product
from app.service import recommend
from app.store import store


def _product(pid: str):
    return next(p for p in store.products if p.id == pid)


def test_over_budget_is_flagged_and_docked():
    product = _product("phone-stand-1688-qiangda")
    # 仅预算约束（不叠加类目分），3.2 > 2.0 应显著降分
    score, reasons, missing = score_product(product, Requirement(max_price_cny=2.0))
    assert any("高于预算上限" in item for item in missing)
    assert score < 60
    # 同条件下不设预算应明显更高
    score_without_budget, _, _ = score_product(product, Requirement())
    assert score_without_budget > score


def test_no_market_price_yields_profit_uncertainty():
    product = _product("phone-stand-1688-xinyi")  # market_ref_price_cny=None
    score, reasons, missing = score_product(
        product, Requirement(category="手机支架", min_est_profit_cny=5.0)
    )
    assert any("缺少市场参考售价" in item for item in missing)


def test_drop_ship_requirement_docks_unsupported_product():
    product = _product("desk-organizer-1688-yueshi")  # drop_ship_supported=False
    score, reasons, missing = score_product(
        product, Requirement(category="桌面收纳", drop_ship_required=True)
    )
    assert any("不支持一件代发" in item for item in missing)


def test_platform_filter_only_returns_matching_platform():
    result = recommend(AskRequest(
        question="手机支架",
        requirement=Requirement(category="手机支架", platforms=["1688"]),
    ))
    assert result.recommendations
    assert all(rec.platform == "1688" for rec in result.recommendations)


def test_retrieval_returns_relevant_quote():
    product_by_id = store.product_index()
    docs = retrieve_documents(
        "手机支架 报价",
        Requirement(category="手机支架"),
        store.documents,
        product_by_id,
    )
    assert docs
    assert any(doc.source_type == "offer" for doc in docs)


def test_audit_trace_records_tool_calls():
    result = recommend(AskRequest(question="桌面收纳盒", requirement=Requirement(category="桌面收纳")))
    assert "sourcing_scorecard" in result.audit["tool_calls"]
    assert result.audit["model_mode"] == "deterministic-demo"
    assert isinstance(result.audit["retrieved_document_ids"], list)


def test_answer_warns_demo_dataset():
    result = recommend(AskRequest(question="桌面收纳盒", requirement=Requirement(category="桌面收纳")))
    assert any("演示" in warning for warning in result.warnings)


def test_demo_score_sanity_ranges():
    for product in store.products:
        score, reasons, missing = score_product(product, Requirement(category=product.category))
        assert 0 <= score <= 100
        assert isinstance(reasons, list) and isinstance(missing, list)
