"""真实货源资料导入：校验并装配 JSON 载荷为 (products, documents)。

支持的载荷结构（与 examples/dataset.example.json 一致）：
{
  "products": [ SourceProduct 字段... ],
  "documents": [ EvidenceDocument 字段... ]   # 可选
}
source_document_ids 与 documents.product_id 之间的外键会做一致性校验。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models import EvidenceDocument, SourceProduct


def load_dataset_payload(payload: dict[str, Any]) -> tuple[list[SourceProduct], list[EvidenceDocument]]:
    try:
        raw_products = payload["products"]
        raw_documents = payload.get("documents", [])
        products = [SourceProduct.model_validate(item) for item in raw_products]
        documents = [EvidenceDocument.model_validate(item) for item in raw_documents]
    except (KeyError, TypeError, ValidationError) as exc:
        raise ValueError(f"资料结构不合法：{exc}") from exc

    if not products:
        raise ValueError("products 不能为空")

    product_ids = {p.id for p in products}
    doc_ids: set[str] = set()
    for doc in documents:
        if doc.id in doc_ids:
            raise ValueError(f"documents 出现重复 id：{doc.id}")
        doc_ids.add(doc.id)
        if doc.product_id not in product_ids:
            raise ValueError(f"document {doc.id} 指向不存在的 product：{doc.product_id}")

    for product in products:
        for ref in product.source_document_ids:
            if ref not in doc_ids:
                raise ValueError(f"product {product.id} 引用了不存在的 document：{ref}")

    return products, documents


def load_dataset_file(path: str | Path) -> tuple[list[SourceProduct], list[EvidenceDocument]]:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("数据集文件顶层必须是 JSON 对象")
    return load_dataset_payload(payload)
