from app.models import AskRequest, Requirement
from app.service import recommend, retrieve_documents


def test_plant_protein_requirement_prefers_verified_match():
    result = recommend(AskRequest(
        question="Need FSSC certified plant protein with fast lead time",
        requirement=Requirement(category="plant-protein", max_lead_time_days=20, required_certifications=["FSSC 22000"]),
    ))
    assert result.recommendations[0].supplier_id == "harbor-nutrition"
    assert result.recommendations[0].verification_status == "verified"
    assert result.recommendations[0].citations


def test_lead_is_explicitly_flagged():
    result = recommend(AskRequest(question="plant protein", requirement=Requirement(category="plant-protein")))
    lead = next(item for item in result.recommendations if item.supplier_id == "evergreen-trade")
    assert any("仅为发现线索" in item for item in lead.missing_evidence)


def test_retrieval_returns_relevant_quote():
    documents = retrieve_documents("pea protein quote", Requirement(category="plant-protein"))
    assert any(document.source_type == "quote" for document in documents)
