from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


VerificationStatus = Literal["verified", "lead", "pending_review"]


class Supplier(BaseModel):
    id: str
    name: str
    region: str
    categories: list[str]
    certifications: list[str]
    min_order_quantity: int
    unit_price_usd: float
    lead_time_days: int
    status: VerificationStatus
    source_document_ids: list[str]


class SourceDocument(BaseModel):
    id: str
    title: str
    source_type: Literal["certificate", "catalog", "quote", "assessment"]
    supplier_id: str
    excerpt: str
    authority: Literal["primary", "supplier_provided", "internal"]
    updated_at: str


class Requirement(BaseModel):
    category: str | None = None
    max_unit_price_usd: float | None = Field(default=None, gt=0)
    max_lead_time_days: int | None = Field(default=None, gt=0)
    required_certifications: list[str] = Field(default_factory=list)
    region: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1_000)
    requirement: Requirement = Field(default_factory=Requirement)


class Citation(BaseModel):
    document_id: str
    title: str
    excerpt: str
    authority: str


class Recommendation(BaseModel):
    supplier_id: str
    supplier_name: str
    score: int
    verification_status: VerificationStatus
    why: list[str]
    missing_evidence: list[str]
    citations: list[Citation]


class AskResponse(BaseModel):
    answer: str
    recommendations: list[Recommendation]
    warnings: list[str]
    audit: dict[str, object]
