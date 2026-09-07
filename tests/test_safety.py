"""安全行为测试：锁定两条核心规则（沿用上游 evidence-first 安全行为并适配电商选品）。

1. verified（已核实货源）优先于 lead（线索）进入候选头部；
2. lead / pending_review 候选必须显式携带"未核验/待复核"声明，禁止伪装成已验证。
"""

from app.models import AskRequest, Requirement
from app.service import recommend


def test_sourcing_prefers_verified_over_lead():
    result = recommend(AskRequest(
        question="找手机支架货源，能一件代发",
        requirement=Requirement(
            category="手机支架",
            max_price_cny=3.5,
            max_min_order_qty=60,
            drop_ship_required=True,
        ),
    ))
    # 头名必须是已核实货源
    assert result.recommendations[0].verification_status == "verified"
    # lead 若出现，必须排在所有 verified 之后
    lead_positions = [i for i, r in enumerate(result.recommendations) if r.verification_status == "lead"]
    if lead_positions:
        verified_positions = [i for i, r in enumerate(result.recommendations) if r.verification_status == "verified"]
        assert max(verified_positions) < min(lead_positions)
    # lead 货源被显式标注
    lead = next((r for r in result.recommendations if r.verification_status == "lead"), None)
    if lead is not None:
        assert any("仅为发现线索" in item for item in lead.missing_evidence)
        assert any("未完成核验" in item for item in lead.missing_evidence)


def test_lead_is_explicitly_flagged_when_only_lead_available():
    result = recommend(AskRequest(
        question="宠物磨牙玩具",
        requirement=Requirement(category="宠物玩具"),
    ))
    lead = next(r for r in result.recommendations if r.verification_status == "lead")
    assert any("仅为发现线索" in item for item in lead.missing_evidence)


def test_pending_review_is_never_silently_verified():
    result = recommend(AskRequest(
        question="桌面收纳架",
        requirement=Requirement(category="桌面收纳"),
    ))
    pending = next(r for r in result.recommendations if r.verification_status == "pending_review")
    assert pending.verification_status != "verified"
    assert any("待人工复核" in item for item in pending.missing_evidence)


def test_every_candidate_carries_verification_status_and_missing_evidence_field():
    result = recommend(AskRequest(question="桌面收纳盒", requirement=Requirement(category="桌面收纳")))
    for rec in result.recommendations:
        assert rec.verification_status in {"verified", "lead", "pending_review"}
        assert isinstance(rec.missing_evidence, list)
        assert isinstance(rec.why, list)
