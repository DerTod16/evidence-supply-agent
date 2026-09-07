"""编排边界：检索 → 服务端评分裁决 → 可选 LLM 摘要（受约束）→ 引用与审计。

这是全系统唯一可替换的编排点：
- demo（默认，离线）：纯确定性回答，不调用任何外部服务；
- remote：评分/状态/证据仍由服务端裁决，LLM 仅负责受 JSON Schema 约束的摘要；
  LLM 失败自动降级为确定性回答，不影响可用性。
"""

from __future__ import annotations

from collections import Counter

from .llm import LLMError, generate_summary, llm_enabled
from .models import (
    PLATFORM_LABELS,
    AskRequest,
    AskResponse,
    Citation,
    Recommendation,
)
from .retrieval import retrieve_documents
from .scorecard import score_product
from .store import store

WARNING_REAL_DILIGENCE = "上架前务必自行核验：档口主体、真实库存、售后、物流时效与图片版权，勿仅凭站内快照下单。"
WARNING_LEAD = "候选中包含「发现线索」状态的货源：主体、资质、真实库存与动销尚未核验，请勿直接下单铺货。"
WARNING_PENDING = "候选中包含「待人工复核」货源：质检/现场核验未闭环，确认前请先人工复核。"

_DEMO_ANSWER = "已基于演示资料生成候选排序。结果用于研究货源与人工选品，不构成下单或上架批准。"
_DEMO_WARNING = "当前为演示样本数据（合成示例），不代表任何真实商家；请导入自有货源资料后再做真实决策。"


def recommend(request: AskRequest) -> AskResponse:
    products = store.products
    documents = store.documents
    product_by_id = store.product_index()

    retrieved = retrieve_documents(request.question, request.requirement, documents, product_by_id)
    docs_by_product: dict[str, list[Citation]] = {}
    for doc in retrieved:
        citation = Citation(
            document_id=doc.id,
            title=doc.title,
            excerpt=doc.excerpt,
            authority=doc.authority,
            source_type=doc.source_type,
            url=doc.url,
        )
        docs_by_product.setdefault(doc.product_id, []).append(citation)

    candidates: list[Recommendation] = []
    for product in products:
        if request.requirement.platforms and product.platform not in request.requirement.platforms:
            continue
        score, reasons, missing = score_product(product, request.requirement)
        citations = docs_by_product.get(product.id, [])
        if score < 25 and not citations:
            continue
        if not citations:
            missing.append("本次检索未返回可引用的支持资料（评分仅供参考，须人工补证）")
        candidates.append(Recommendation(
            product_id=product.id,
            product_title=product.title,
            supplier=product.supplier,
            platform=PLATFORM_LABELS.get(product.platform, product.platform),
            price_cny=product.price_cny,
            min_order_qty=product.min_order_qty,
            score=score,
            verification_status=product.status,
            why=reasons or ["与当前筛选条件的直接匹配较少"],
            missing_evidence=missing,
            citations=citations,
        ))

    candidates.sort(key=lambda item: (-item.score, item.product_id))
    candidates = candidates[:3]

    warnings = build_warnings(candidates)
    llm_used, llm_error, answer = compose_answer(request, candidates)

    status_counts = Counter(item.verification_status for item in candidates)
    return AskResponse(
        answer=answer,
        recommendations=candidates,
        warnings=warnings,
        audit={
            "retrieval_strategy": "lexical demo retrieval with category/platform metadata boost",
            "retrieved_document_ids": [doc.id for doc in retrieved],
            "scored_product_ids": [item.product_id for item in candidates],
            "verification_status_counts": dict(status_counts),
            "tool_calls": ["sourcing_scorecard", "dataset_lookup"],
            "model_mode": "remote" if llm_used else "deterministic-demo",
            "dataset": "demo-synthetic" if store.is_demo else "imported",
        },
        llm_used=llm_used,
        llm_error=llm_error,
    )


def build_warnings(candidates: list[Recommendation]) -> list[str]:
    warnings: list[str] = []
    if store.is_demo:
        warnings.append(_DEMO_WARNING)
    else:
        warnings.append(WARNING_REAL_DILIGENCE)
    if any(item.verification_status == "lead" for item in candidates):
        warnings.append(WARNING_LEAD)
    if any(item.verification_status == "pending_review" for item in candidates):
        warnings.append(WARNING_PENDING)
    return warnings


def compose_answer(request: AskRequest, candidates: list[Recommendation]) -> tuple[bool, str | None, str]:
    """优先让 LLM 生成受约束摘要；失败或 demo 模式则回落确定性模板。"""
    if llm_enabled():
        try:
            summary = generate_summary(request.requirement, candidates)
            answer = summary.answer
            if summary.market_context:
                answer = f"{answer}\n市场背景：{summary.market_context}"
            return True, None, answer
        except LLMError as exc:
            return False, str(exc), _DEMO_ANSWER
    return False, None, _DEMO_ANSWER
