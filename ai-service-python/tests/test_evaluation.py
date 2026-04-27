"""
Unit tests for the evaluation and guardrails module.
Run with: pytest tests/test_evaluation.py -v
"""

import pytest
from app.evaluation import (
    RAGEvaluator,
    check_query_safety,
    check_answer_safety,
    compute_faithfulness,
    compute_answer_relevance,
    compute_context_precision,
    compute_hallucination_risk,
    EvalResult,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_DOCS = [
    {
        "publication_title": "Deep Learning for Natural Language Processing",
        "author": "Jane Smith",
        "affiliation": "MIT",
        "interests": "machine learning neural networks NLP",
        "cluster": "Machine Learning & AI",
        "year": 2023,
        "citations": 150,
        "score": 0.92,
    },
    {
        "publication_title": "Cryptographic Protocols for Secure Communication",
        "author": "John Doe",
        "affiliation": "Stanford",
        "interests": "cryptography security privacy",
        "cluster": "Cryptography & Security",
        "year": 2022,
        "citations": 80,
        "score": 0.85,
    },
]

# ── Query safety guardrail tests ──────────────────────────────────────────────

class TestQuerySafety:
    def test_normal_query_allowed(self):
        result = check_query_safety("Who are the top researchers in deep learning?")
        assert result.allowed is True
        assert result.reason is None

    def test_too_short_blocked(self):
        result = check_query_safety("ai")
        assert result.allowed is False
        assert "short" in result.reason.lower()

    def test_too_long_blocked(self):
        result = check_query_safety("a" * 1001)
        assert result.allowed is False
        assert "long" in result.reason.lower()

    def test_harmful_keyword_blocked(self):
        result = check_query_safety("how to hack a database")
        assert result.allowed is False

    def test_edge_case_exactly_3_chars(self):
        result = check_query_safety("NLP")
        assert result.allowed is True


# ── Faithfulness tests ────────────────────────────────────────────────────────

class TestFaithfulness:
    def test_highly_faithful_answer(self):
        answer = "Jane Smith from MIT published work on deep learning and NLP neural networks."
        score = compute_faithfulness(answer, SAMPLE_DOCS)
        assert score > 0.5, f"Expected >0.5, got {score}"

    def test_no_context_returns_one(self):
        score = compute_faithfulness("any answer", [])
        assert score == 1.0

    def test_empty_answer_returns_one(self):
        score = compute_faithfulness("", SAMPLE_DOCS)
        assert score == 1.0

    def test_unrelated_answer_lower_score(self):
        answer = "The stock market crashed yesterday causing economic turmoil globally."
        grounded = "Jane Smith MIT deep learning NLP machine learning neural networks."
        score_unrelated = compute_faithfulness(answer, SAMPLE_DOCS)
        score_grounded = compute_faithfulness(grounded, SAMPLE_DOCS)
        assert score_grounded > score_unrelated


# ── Answer relevance tests ────────────────────────────────────────────────────

class TestAnswerRelevance:
    def test_relevant_answer(self):
        query = "deep learning NLP researchers"
        answer = "The top researchers in deep learning for NLP include experts at major universities."
        score = compute_answer_relevance(query, answer)
        assert score > 0.2

    def test_empty_inputs(self):
        score = compute_answer_relevance("", "")
        assert score == 0.5   # default for empty

    def test_irrelevant_answer_low_score(self):
        query = "cryptography researchers"
        answer = "The weather today is sunny and warm."
        score = compute_answer_relevance(query, answer)
        assert score < 0.3


# ── Context precision tests ───────────────────────────────────────────────────

class TestContextPrecision:
    def test_relevant_docs_high_precision(self):
        query = "deep learning neural networks"
        score = compute_context_precision(query, SAMPLE_DOCS)
        # At least one doc mentions deep learning
        assert score > 0.0

    def test_empty_docs_zero_precision(self):
        score = compute_context_precision("any query", [])
        assert score == 0.0

    def test_empty_query(self):
        score = compute_context_precision("", SAMPLE_DOCS)
        assert score == 0.5   # default


# ── Hallucination risk tests ──────────────────────────────────────────────────

class TestHallucinationRisk:
    def test_grounded_answer_low_risk(self):
        answer = "Jane Smith published deep learning research at MIT."
        risk = compute_hallucination_risk(answer, SAMPLE_DOCS)
        assert risk < 0.5

    def test_unknown_names_raise_risk(self):
        answer = "Professor Xyz Abc from Unknown University pioneered this field."
        risk_with_context = compute_hallucination_risk(answer, SAMPLE_DOCS)
        risk_no_context = compute_hallucination_risk(answer, [])
        assert risk_with_context > 0.0

    def test_overconfident_language_raises_risk(self):
        answer = "This is definitely certainly always the best approach without doubt."
        risk = compute_hallucination_risk(answer, SAMPLE_DOCS)
        assert risk > 0.2


# ── End-to-end evaluator tests ────────────────────────────────────────────────

class TestRAGEvaluator:
    def setup_method(self):
        self.evaluator = RAGEvaluator()

    def test_eval_returns_eval_result(self):
        result = self.evaluator.evaluate(
            query="deep learning researchers",
            answer="Jane Smith from MIT works on deep learning and neural networks.",
            context_docs=SAMPLE_DOCS,
            latency_ms=250.0,
        )
        assert isinstance(result, EvalResult)
        assert 0.0 <= result.faithfulness <= 1.0
        assert 0.0 <= result.answer_relevance <= 1.0
        assert 0.0 <= result.context_precision <= 1.0
        assert 0.0 <= result.hallucination_risk <= 1.0
        assert 0.0 <= result.overall_score <= 1.0

    def test_to_dict_has_all_keys(self):
        result = self.evaluator.evaluate("test query", "test answer", SAMPLE_DOCS)
        d = result.to_dict()
        for key in ("faithfulness", "answer_relevance", "context_precision",
                    "hallucination_risk", "overall_score", "latency_ms",
                    "flags", "passed_guardrails"):
            assert key in d, f"Missing key: {key}"

    def test_high_latency_flagged(self):
        result = self.evaluator.evaluate("q", "a", SAMPLE_DOCS, latency_ms=6000)
        flags = result.to_dict()["flags"]
        assert any("LATENCY" in f for f in flags)

    def test_retrieval_only_eval(self):
        result = self.evaluator.evaluate_retrieval_only("deep learning", SAMPLE_DOCS)
        assert "context_precision" in result
        assert "docs_retrieved" in result
        assert result["docs_retrieved"] == 2

    def test_answer_safety_blocks_low_faithfulness(self):
        bad_result = EvalResult(faithfulness=0.1, hallucination_risk=0.2)
        guard = check_answer_safety("some answer", bad_result)
        assert guard.allowed is False

    def test_answer_safety_passes_good_result(self):
        good_result = EvalResult(faithfulness=0.8, hallucination_risk=0.1)
        guard = check_answer_safety("good grounded answer", good_result)
        assert guard.allowed is True
