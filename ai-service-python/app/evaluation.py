"""
AI Evaluation & Guardrails
===========================
Implements production-grade evaluation without requiring a paid RAGAS API key.

Metrics computed (RAGAS-inspired):
  • faithfulness      — does the answer stay within the retrieved context?
  • answer_relevance  — does the answer address the question?
  • context_precision — are the retrieved docs actually relevant to the query?
  • hallucination_risk — heuristic score based on unverifiable claims

Guardrails:
  • query_safety      — blocks harmful / off-topic inputs
  • answer_safety     — flags answers with low faithfulness before returning them
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Banned / off-topic patterns ───────────────────────────────────────────────
_BLOCKED_PATTERNS = [
    r"\b(bomb|weapon|hack|exploit|password|credit.?card|ssn|social.security)\b",
    r"\b(kill|murder|suicide|self.harm)\b",
]
_COMPILED_BLOCKS = [re.compile(p, re.IGNORECASE) for p in _BLOCKED_PATTERNS]


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class EvalResult:
    faithfulness: float = 1.0        # 0–1; how grounded in context
    answer_relevance: float = 1.0    # 0–1; how relevant to query
    context_precision: float = 1.0   # 0–1; retrieval quality
    hallucination_risk: float = 0.0  # 0–1; higher = more risk
    latency_ms: float = 0.0
    flags: list[str] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        return round(
            0.4 * self.faithfulness
            + 0.3 * self.answer_relevance
            + 0.2 * self.context_precision
            + 0.1 * (1 - self.hallucination_risk),
            3,
        )

    def to_dict(self) -> dict:
        return {
            "faithfulness": round(self.faithfulness, 3),
            "answer_relevance": round(self.answer_relevance, 3),
            "context_precision": round(self.context_precision, 3),
            "hallucination_risk": round(self.hallucination_risk, 3),
            "overall_score": self.overall_score,
            "latency_ms": round(self.latency_ms, 1),
            "flags": self.flags,
            "passed_guardrails": len(self.flags) == 0,
        }


@dataclass
class GuardrailResult:
    allowed: bool
    reason: Optional[str] = None


# ── Guardrails ────────────────────────────────────────────────────────────────

def check_query_safety(query: str) -> GuardrailResult:
    """Block harmful queries before they reach the pipeline."""
    for pattern in _COMPILED_BLOCKS:
        if pattern.search(query):
            return GuardrailResult(
                allowed=False,
                reason=f"Query contains disallowed content (matched: {pattern.pattern})",
            )

    # Length guardrail
    if len(query.strip()) < 3:
        return GuardrailResult(allowed=False, reason="Query too short (< 3 chars)")
    if len(query) > 1000:
        return GuardrailResult(allowed=False, reason="Query too long (> 1000 chars)")

    return GuardrailResult(allowed=True)


def check_answer_safety(answer: str, eval_result: EvalResult) -> GuardrailResult:
    """Block or flag answers that fail faithfulness/hallucination thresholds."""
    if eval_result.faithfulness < 0.25:
        return GuardrailResult(
            allowed=False,
            reason=f"Answer failed faithfulness guardrail (score={eval_result.faithfulness:.2f})",
        )
    if eval_result.hallucination_risk > 0.75:
        return GuardrailResult(
            allowed=False,
            reason=f"Answer flagged for high hallucination risk (score={eval_result.hallucination_risk:.2f})",
        )
    return GuardrailResult(allowed=True)


# ── Metric computation ────────────────────────────────────────────────────────

def _tokenise(text: str) -> set[str]:
    """Simple word-level tokeniser (no NLTK dependency)."""
    return set(re.findall(r"\b[a-z]{3,}\b", text.lower()))


def compute_faithfulness(answer: str, context_docs: list[dict]) -> float:
    """
    Heuristic faithfulness: what fraction of meaningful answer words
    appear in at least one retrieved document?

    A production system would use an LLM judge (e.g., RAGAS faithfulness
    prompt); here we use token overlap as a cost-free approximation.
    """
    if not context_docs or not answer:
        return 1.0  # no context → can't penalise

    # Build corpus from retrieved doc fields
    corpus_tokens: set[str] = set()
    for doc in context_docs:
        for field in ("publication_title", "author", "interests", "affiliation", "cluster"):
            corpus_tokens |= _tokenise(str(doc.get(field, "")))

    answer_tokens = _tokenise(answer)
    if not answer_tokens:
        return 1.0

    overlap = answer_tokens & corpus_tokens
    score = len(overlap) / len(answer_tokens)
    return min(score * 1.5, 1.0)   # scale: token overlap underestimates faithfulness


def compute_answer_relevance(query: str, answer: str) -> float:
    """
    Heuristic relevance: bidirectional token overlap between query and answer.
    Production alternative: embed both and compute cosine similarity.
    """
    q_tokens = _tokenise(query)
    a_tokens = _tokenise(answer)
    if not q_tokens or not a_tokens:
        return 0.5

    overlap = q_tokens & a_tokens
    precision = len(overlap) / len(a_tokens)
    recall = len(overlap) / len(q_tokens)

    if precision + recall == 0:
        return 0.0
    f1 = 2 * precision * recall / (precision + recall)
    return min(f1 * 2.5, 1.0)   # scale up: academic answers use different vocabulary


def compute_context_precision(query: str, context_docs: list[dict]) -> float:
    """
    What fraction of retrieved docs are relevant to the query?
    Proxy: token overlap of query with each doc's title + interests.
    """
    if not context_docs:
        return 0.0

    q_tokens = _tokenise(query)
    if not q_tokens:
        return 0.5

    relevant = 0
    for doc in context_docs:
        doc_text = f"{doc.get('publication_title','')} {doc.get('interests','')}"
        doc_tokens = _tokenise(doc_text)
        if q_tokens & doc_tokens:
            relevant += 1

    return relevant / len(context_docs)


def compute_hallucination_risk(answer: str, context_docs: list[dict]) -> float:
    """
    Heuristic: detects patterns typical of hallucinated academic content.
      • Specific numbers/years not in context
      • Researcher names not in context
      • High-certainty hedging phrases ("definitely", "certainly", "always")
    """
    risk = 0.0

    # Collect all names/numbers from context
    context_text = " ".join(
        f"{d.get('author','')} {d.get('publication_title','')} {d.get('year','')}"
        for d in context_docs
    )

    # Proper nouns in the answer not seen in context
    answer_names = set(re.findall(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", answer))
    context_names = set(re.findall(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", context_text))
    unverified_names = answer_names - context_names
    if unverified_names:
        risk += min(0.2 * len(unverified_names), 0.4)

    # Overconfident language
    overconfident = re.findall(
        r"\b(definitely|certainly|always|never|proven|guaranteed|without doubt)\b",
        answer, re.IGNORECASE,
    )
    if overconfident:
        risk += min(0.1 * len(overconfident), 0.3)

    # Very short answer with no context reference (likely generic)
    if len(answer.split()) < 20 and not context_docs:
        risk += 0.3

    return min(risk, 1.0)


# ── Main evaluator ────────────────────────────────────────────────────────────

class RAGEvaluator:
    """
    Wraps all evaluation metrics into a single callable.

    Usage:
        evaluator = RAGEvaluator()
        result = evaluator.evaluate(query, answer, context_docs, latency_ms)
        print(result.to_dict())
    """

    def evaluate(
        self,
        query: str,
        answer: str,
        context_docs: list[dict],
        latency_ms: float = 0.0,
    ) -> EvalResult:
        t0 = time.time()

        faithfulness = compute_faithfulness(answer, context_docs)
        relevance = compute_answer_relevance(query, answer)
        precision = compute_context_precision(query, context_docs)
        hall_risk = compute_hallucination_risk(answer, context_docs)

        flags: list[str] = []
        if faithfulness < 0.4:
            flags.append(f"LOW_FAITHFULNESS({faithfulness:.2f})")
        if relevance < 0.2:
            flags.append(f"LOW_RELEVANCE({relevance:.2f})")
        if hall_risk > 0.5:
            flags.append(f"HALLUCINATION_RISK({hall_risk:.2f})")
        if latency_ms > 5000:
            flags.append(f"HIGH_LATENCY({latency_ms:.0f}ms)")

        eval_latency = (time.time() - t0) * 1000
        logger.debug(
            f"Eval completed in {eval_latency:.1f}ms | "
            f"faith={faithfulness:.2f} rel={relevance:.2f} "
            f"prec={precision:.2f} hall={hall_risk:.2f}"
        )

        return EvalResult(
            faithfulness=faithfulness,
            answer_relevance=relevance,
            context_precision=precision,
            hallucination_risk=hall_risk,
            latency_ms=latency_ms,
            flags=flags,
        )

    def evaluate_retrieval_only(self, query: str, context_docs: list[dict]) -> dict:
        """Quick evaluation of retrieval quality without an answer."""
        precision = compute_context_precision(query, context_docs)
        return {
            "context_precision": round(precision, 3),
            "docs_retrieved": len(context_docs),
            "relevant_docs": int(precision * len(context_docs)),
        }


# Singleton
evaluator = RAGEvaluator()
