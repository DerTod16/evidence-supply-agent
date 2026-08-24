from __future__ import annotations

import re
from collections import Counter

from .data import DOCUMENTS, SUPPLIERS
from .models import AskRequest, AskResponse, Citation, Recommendation, Requirement, SourceDocument, Supplier


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def retrieve_documents(question: str, requirement: Requirement, limit: int = 6) -> list[SourceDocument]:
    query = _terms(question + " " + (requirement.category or "") + " " + " ".join(requirement.required_certifications))
    ranked: list[tuple[int, SourceDocument]] = []
    for document in DOCUMENTS:
        score = len(query.intersection(_terms(document.title + " " + document.excerpt)))
        if requirement.category and requirement.category in next(s for s in SUPPLIERS if s.id == document.supplier_id).categories:
            score += 3
        ranked.append((score, document))
    return [document for score, document in sorted(ranked, key=lambda item: (-item[0], item[1].id))[:limit] if score > 0]


def _score_supplier(supplier: Supplier, requirement: Requirement) -> tuple[int, list[str], list[str]]:
    score = 40
    reasons: list[str] = []
    missing: list[str] = []
    if requirement.category:
        if requirement.category in supplier.categories:
            score += 20
            reasons.append(f"产品类别匹配：{requirement.category}")
        else:
            score -= 35
            missing.append(f"目录中未证明供应 {requirement.category}")
    if requirement.region:
        if requirement.region.lower() == supplier.region.lower():
            score += 10
            reasons.append(f"区域匹配：{supplier.region}")
        else:
            score -= 4
    if requirement.max_unit_price_usd:
        if supplier.unit_price_usd <= requirement.max_unit_price_usd:
            score += 12
            reasons.append(f"演示报价 ${supplier.unit_price_usd:.2f}/kg 在预算内")
        else:
            score -= 12
            missing.append(f"演示报价 ${supplier.unit_price_usd:.2f}/kg 高于预算")
    if requirement.max_lead_time_days:
        if supplier.lead_time_days <= requirement.max_lead_time_days:
            score += 10
            reasons.append(f"标示交期 {supplier.lead_time_days} 天符合要求")
        else:
            score -= 10
            missing.append(f"标示交期 {supplier.lead_time_days} 天超出要求")
    required = {item.lower() for item in requirement.required_certifications}
    actual = {item.lower() for item in supplier.certifications}
    unsupported = sorted(required - actual)
    if unsupported:
        score -= 20
        missing.append("缺少认证证据：" + ", ".join(unsupported))
    elif required:
        score += 12
        reasons.append("所需认证已在演示资料中出现")
    if supplier.status == "verified":
        score += 12
        reasons.append("资料状态为已验证")
    elif supplier.status == "lead":
        score -= 18
        missing.append("仅为发现线索，尚未完成实体、合规和库存核验")
    else:
        score -= 6
        missing.append("仍需人工质量复核")
    return max(0, min(100, score)), reasons, missing


def recommend(request: AskRequest) -> AskResponse:
    retrieved = retrieve_documents(request.question, request.requirement)
    docs_by_supplier: dict[str, list[SourceDocument]] = {}
    for document in retrieved:
        docs_by_supplier.setdefault(document.supplier_id, []).append(document)

    candidates: list[Recommendation] = []
    for supplier in SUPPLIERS:
        score, reasons, missing = _score_supplier(supplier, request.requirement)
        supplier_docs = docs_by_supplier.get(supplier.id, [])
        if score < 25 and not supplier_docs:
            continue
        citations = [Citation(document_id=doc.id, title=doc.title, excerpt=doc.excerpt, authority=doc.authority) for doc in supplier_docs]
        if not citations:
            missing.append("本次检索未返回可引用的支持材料")
        candidates.append(Recommendation(
            supplier_id=supplier.id,
            supplier_name=supplier.name,
            score=score,
            verification_status=supplier.status,
            why=reasons or ["与当前筛选条件的直接匹配较少"],
            missing_evidence=missing,
            citations=citations,
        ))
    candidates.sort(key=lambda item: (-item.score, item.supplier_name))
    candidates = candidates[:3]
    status_counts = Counter(item.verification_status for item in candidates)
    answer = "已基于演示资料生成候选排序。结果用于研究与人工尽调，不构成采购批准。"
    warnings = [
        "本仓库仅含合成演示资料；不得将其视作真实供应商推荐。",
        "任何采购决定前应核验实体、证书有效性、报价、库存、物流与合规。",
    ]
    if status_counts.get("lead"):
        warnings.append("候选中包含发现线索（lead），应在进入比价前完成供应商尽调。")
    return AskResponse(
        answer=answer,
        recommendations=candidates,
        warnings=warnings,
        audit={
            "retrieval_strategy": "lexical demo retrieval with category metadata boost",
            "retrieved_document_ids": [doc.id for doc in retrieved],
            "tool_calls": ["supplier_scorecard"],
            "model_mode": "deterministic-demo",
        },
    )
