"""可解释检索：词法匹配 + 类目/平台元数据加权。

与上游一致：demo 阶段使用透明的词法检索，保证每次命中都可解释。
生产可按 service 边界替换为向量/混合检索，但评分与证据检查仍在服务端。
"""

from __future__ import annotations

import re

from .models import EvidenceDocument, Requirement, SourceProduct

_TOKEN_RE = re.compile(r"[a-z0-9\u4e00-\u9fff]+")


def _terms(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def retrieve_documents(
    question: str,
    requirement: Requirement,
    documents: list[EvidenceDocument],
    product_by_id: dict[str, SourceProduct],
    limit: int = 8,
) -> list[EvidenceDocument]:
    """按相关性返回资料摘录：词法命中 + 需求类目加权 + 目标平台加权。"""
    category = (requirement.category or "").strip()
    platforms = set(requirement.platforms or [])
    query_terms = _terms(f"{question} {category}")

    ranked: list[tuple[int, int, EvidenceDocument]] = []
    for idx, doc in enumerate(documents):
        score = len(query_terms.intersection(_terms(f"{doc.title} {doc.excerpt}")))
        haystack = f"{doc.title} {doc.excerpt}"
        if category and category.lower() in haystack.lower():
            score += 3
        product = product_by_id.get(doc.product_id)
        if product is not None and platforms and product.platform in platforms:
            score += 2
        ranked.append((score, idx, doc))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [doc for score, _, doc in ranked[:limit] if score > 0]
