"""领域模型：电商货源选品域（evidence-first）。

状态与证据模型沿用上游 evidence-supply-agent 的核心理念：
- 候选货源状态三态：verified / lead / pending_review，禁止把"线索"伪装成"已验证"；
- 每个候选携带可回溯的资料引用（citations）与缺失证据声明（missing_evidence）；
- 评分与状态由服务端确定性工具裁决，LLM 只负责摘要与解读，输出受 JSON Schema 约束。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# 目标货源平台（电商新手卖家货源场景）
PlatformCode = Literal["1688", "yiwugo", "pdd-wholesale"]

PLATFORM_LABELS: dict[str, str] = {
    "1688": "1688",
    "yiwugo": "义乌购",
    "pdd-wholesale": "拼多多批发",
}

VerificationStatus = Literal["verified", "lead", "pending_review"]

STATUS_LABELS: dict[str, str] = {
    "verified": "已验证",
    "lead": "发现线索",
    "pending_review": "待人工复核",
}


class SourceProduct(BaseModel):
    """货源候选商品：来自货源站 offer 或目录资料的可核验条目。"""

    id: str
    platform: PlatformCode
    title: str
    category: str
    supplier: str  # 档口 / 供应商名称
    region: str  # 发货地（城市）
    price_cny: float  # 单件拿货价 / 代发价（元）
    market_ref_price_cny: float | None = None  # 市场参考售价（元/件，来自同款在售样本）
    min_order_qty: int  # 起批量（件）
    est_monthly_sales: int | None = None  # 近期动销线索（件/月），无则视为缺失证据
    drop_ship_supported: bool = False  # 是否支持一件代发
    image_count: int = 0  # 可用商品图数量（素材完整性线索）
    status: VerificationStatus
    source_document_ids: list[str] = Field(default_factory=list)


class EvidenceDocument(BaseModel):
    """支撑某候选货源的可追溯资料：offer 页快照 / 报价 / 质检与资质 / 评估记录。"""

    id: str
    product_id: str
    source_type: Literal["offer", "quote", "certificate", "assessment"]
    title: str
    excerpt: str
    authority: Literal["primary", "platform", "supplier_provided", "internal"]
    url: str = ""  # 平台来源地址（demo 数据使用 *.invalid 占位，真实部署填入实际 offer 链接）
    updated_at: str


class Requirement(BaseModel):
    """选品需求（新手卖家视角，全部可选、由前端表单填充）。"""

    category: str | None = None  # 目标类目，如 "桌面收纳"
    max_price_cny: float | None = Field(default=None, gt=0)  # 最高拿货单价（元）
    max_min_order_qty: int | None = Field(default=None, gt=0)  # 可接受最大起批量
    min_est_profit_cny: float | None = Field(default=None, gt=0)  # 期望单件毛利空间（元）
    drop_ship_required: bool = False  # 是否必须支持一件代发
    platforms: list[str] | None = None  # 目标平台子集，空则不限制


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1_000)
    requirement: Requirement = Field(default_factory=Requirement)


class Citation(BaseModel):
    document_id: str
    title: str
    excerpt: str
    authority: str
    source_type: str
    url: str = ""


class Recommendation(BaseModel):
    """候选货源卡片：评分 + 核验状态 + 依据 + 缺失证据 + 引用。"""

    product_id: str
    product_title: str
    supplier: str
    platform: str  # 展示名，如 1688 / 义乌购 / 拼多多批发
    price_cny: float
    min_order_qty: int
    score: int
    verification_status: VerificationStatus
    why: list[str]
    missing_evidence: list[str]
    citations: list[Citation]


class LlmSummary(BaseModel):
    """LLM 唯一允许输出的结构化摘要（受 JSON Schema 约束并由服务端强校验）。

    刻意不包含 score / verification_status / price —— 这些事实由服务端裁决，
    模型输出即使出现也会被丢弃，防止模型把猜测伪装成结论。
    """

    answer: str
    market_context: str | None = None
    candidate_notes: dict[str, str] = Field(default_factory=dict)


class AskResponse(BaseModel):
    answer: str
    recommendations: list[Recommendation]
    warnings: list[str]
    audit: dict[str, object]
    llm_used: bool = False
    llm_error: str | None = None
