"""HTTP 层契约测试：健康检查、查询响应结构、资料导入/重置闭环。"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ask_returns_full_card_contract():
    response = client.post("/api/ask", json={
        "question": "找桌面收纳货源",
        "requirement": {"category": "桌面收纳"},
    })
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["answer"], str)
    assert isinstance(body["recommendations"], list)
    assert 0 < len(body["recommendations"]) <= 3
    card = body["recommendations"][0]
    for key in ("product_id", "product_title", "supplier", "platform", "price_cny",
                "score", "verification_status", "why", "missing_evidence", "citations"):
        assert key in card
    assert "sourcing_scorecard" in body["audit"]["tool_calls"]
    assert body["llm_used"] is False


def test_ask_rejects_short_question():
    response = client.post("/api/ask", json={"question": "ab"})
    assert response.status_code == 422


def test_dataset_import_and_reset_roundtrip():
    sample = json.load(open(ROOT / "examples" / "dataset.example.json", encoding="utf-8"))
    response = client.post("/api/dataset/import", json=sample)
    assert response.status_code == 200
    data = response.json()
    assert data["is_demo"] is False
    assert data["imported_products"] > 0

    # 导入后 ask 的审计应标记 imported，且 warning 不再声称是演示样本
    ask = client.post("/api/ask", json={"question": "测试导入货源", "requirement": {}}).json()
    assert ask["audit"]["dataset"] == "imported"
    assert not any("演示" in w for w in ask["warnings"])

    reset = client.post("/api/dataset/reset")
    assert reset.json()["is_demo"] is True
    assert client.get("/api/health").json()["mode"] == "deterministic-demo"


def test_dataset_import_validates_references():
    response = client.post("/api/dataset/import", json={
        "products": [{
            "id": "p1",
            "platform": "1688",
            "title": "测试商品",
            "category": "测试类目",
            "supplier": "测试档口",
            "region": "测试地区",
            "price_cny": 1.0,
            "market_ref_price_cny": 2.0,
            "min_order_qty": 1,
            "status": "verified",
            "source_document_ids": ["missing-doc"],
        }],
    })
    assert response.status_code == 422
