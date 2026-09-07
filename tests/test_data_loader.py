"""资料导入装配与一致性校验测试。"""

import pytest

from app.data_loader import load_dataset_payload, load_dataset_file
from app.store import DatasetStore

VALID_PRODUCT = {
    "id": "p-ok-1",
    "platform": "1688",
    "title": "测试货源",
    "category": "测试类目",
    "supplier": "测试档口",
    "region": "测试地",
    "price_cny": 1.0,
    "market_ref_price_cny": 3.0,
    "min_order_qty": 1,
    "status": "verified",
    "source_document_ids": [],
}

VALID_DOC = {
    "id": "doc-ok-1",
    "product_id": "p-ok-1",
    "source_type": "offer",
    "title": "测试 offer",
    "excerpt": "测试摘录",
    "authority": "platform",
    "url": "https://example.invalid/offer/1",
    "updated_at": "2026-09-01",
}


def test_valid_payload_roundtrip():
    products, docs = load_dataset_payload({"products": [VALID_PRODUCT], "documents": [VALID_DOC]})
    assert products[0].id == "p-ok-1"
    assert docs[0].product_id == "p-ok-1"


def test_empty_products_rejected():
    with pytest.raises(ValueError):
        load_dataset_payload({"products": []})


def test_orphan_document_rejected():
    bad = {**VALID_DOC, "id": "doc-orphan", "product_id": "no-such-product"}
    with pytest.raises(ValueError, match="不存在的 product"):
        load_dataset_payload({"products": [VALID_PRODUCT], "documents": [bad]})


def test_dangling_reference_rejected():
    bad_product = {**VALID_PRODUCT, "id": "p-ref", "source_document_ids": ["ghost-doc"]}
    with pytest.raises(ValueError, match="不存在的 document"):
        load_dataset_payload({"products": [bad_product]})


def test_duplicate_document_id_rejected():
    with pytest.raises(ValueError, match="重复 id"):
        load_dataset_payload({"products": [VALID_PRODUCT], "documents": [VALID_DOC, VALID_DOC]})


def test_import_sets_is_demo_false():
    products, docs = load_dataset_payload({"products": [VALID_PRODUCT], "documents": [VALID_DOC]})
    store = DatasetStore()
    store.replace(products, docs)
    assert store.is_demo is False


def test_load_dataset_file(tmp_path):
    import json

    path = tmp_path / "dataset.json"
    path.write_text(json.dumps({"products": [VALID_PRODUCT], "documents": []}), encoding="utf-8")
    products, docs = load_dataset_file(path)
    assert products[0].title == "测试货源"
    assert docs == []
