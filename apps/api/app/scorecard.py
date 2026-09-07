"""确定性评分工具（服务端裁决，不依赖 LLM）。

设计原则（沿用上游 evidence-first 理念）：评分、核验状态与缺失证据由
本模块的确定性规则产生，LLM 永远无权改写这些事实。LLM 的输出即使声称
"某候选已验证"也会被上层丢弃，避免模型把猜测伪装成采购/上架结论。
"""

from __future__ import annotations

from .models import Requirement, SourceProduct


def score_product(product: SourceProduct, requirement: Requirement) -> tuple[int, list[str], list[str]]:
    """返回 (score 0-100, reasons 匹配依据, missing 待核验/缺失证据)。"""
    score = 40
    reasons: list[str] = []
    missing: list[str] = []

    category = (requirement.category or "").strip().lower()
    if category:
        if product.category.lower() == category:
            score += 20
            reasons.append(f"类目匹配：{product.category}")
        else:
            score -= 35
            missing.append(f"目录中未证明属于目标类目「{requirement.category}」")

    if requirement.max_price_cny is not None:
        if product.price_cny <= requirement.max_price_cny:
            score += 14
            reasons.append(f"拿货价 ¥{product.price_cny:.2f}/件 在预算内")
        else:
            score -= 12
            missing.append(f"拿货价 ¥{product.price_cny:.2f}/件 高于预算上限")

    if requirement.min_est_profit_cny is not None:
        if product.market_ref_price_cny is None:
            missing.append("缺少市场参考售价，实际毛利空间无法核实（仅按拿货价估算）")
        elif product.market_ref_price_cny - product.price_cny >= requirement.min_est_profit_cny:
            score += 12
            reasons.append(f"参考毛利 ¥{product.market_ref_price_cny - product.price_cny:.2f}/件 满足预期")
        else:
            score -= 12
            missing.append(f"参考毛利仅 ¥{product.market_ref_price_cny - product.price_cny:.2f}/件，低于预期空间")

    if requirement.max_min_order_qty is not None:
        if product.min_order_qty <= requirement.max_min_order_qty:
            score += 8
            reasons.append(f"起批量 {product.min_order_qty} 件可接受")
        else:
            score -= 8
            missing.append(f"起批量 {product.min_order_qty} 件超过可接受上限")

    if requirement.drop_ship_required:
        if product.drop_ship_supported:
            score += 8
            reasons.append("支持一件代发，符合零库存起步策略")
        else:
            score -= 8
            missing.append("不支持一件代发，需自行备货")

    if product.est_monthly_sales is None:
        missing.append("缺少近期动销数据，无法判断该货源的热度")
    elif product.est_monthly_sales >= 500:
        score += 8
        reasons.append(f"近期动销线索 {product.est_monthly_sales}+ 件/月")
    elif product.est_monthly_sales > 0:
        score += 3
        reasons.append(f"近期动销线索 {product.est_monthly_sales} 件/月（偏低）")

    # 核验状态裁决：优先级低于一切业务分，但 lead / pending 强制进入缺失证据
    if product.status == "verified":
        score += 12
        reasons.append("资料状态为已验证（offer 快照/报价/质检在档）")
    elif product.status == "lead":
        score -= 16
        missing.append("仅为发现线索：档口主体、资质、真实库存与动销均未完成核验")
    else:  # pending_review
        score -= 5
        missing.append("仍有待人工复核项（质检/现场核验未闭环），请勿直接上架")

    if product.image_count == 0:
        missing.append("无可用商品图素材")
    elif product.image_count < 5:
        missing.append(f"商品图素材偏少（{product.image_count} 张），上架主图/详情可能不足")

    return max(0, min(100, score)), reasons, missing
