from __future__ import annotations

from src.enricher import GroqEnricher


def test_fallback_enrichment_extracts_skills():
    enricher = GroqEnricher(api_key="")

    skills, confidence = enricher.enrich_listing(
        "We need a Python engineer with Docker, Kubernetes and FastAPI experience."
    )

    assert "Python" in skills
    assert "Docker" in skills
    assert confidence >= 0.75


def test_fallback_answer_uses_context():
    enricher = GroqEnricher(api_key="")

    answer = enricher.answer_question(
        "What skills matter?",
        "- AI Engineer at Acme (Python, FastAPI)\n- Platform Engineer at Beta (Docker, Kubernetes)",
    )

    assert "Acme" in answer
