"""Step 5: thin wrapper around the Claude API for structured clause assessment.

The LLM is given two versions of what the deterministic layer already matched as
the SAME clause, and asked to explain the change and flag risk. It returns a
schema-validated `ClauseAssessment` via `messages.parse()` — no free-form text to
parse, no hallucinated fields. The model is told to ground every judgement in the
provided text and to flag uncertainty rather than guess.
"""

from __future__ import annotations

from ..config import get_config
from ..schemas import ClauseAssessment, RiskLevel

SYSTEM_PROMPT = """\
You are a legal document comparison assistant supporting a human legal reviewer.
You are given two versions of what has already been matched as the SAME clause:
version A (original) and version B (revised). Explain what changed and flag
potential risk FOR THE REVIEWER. You do not give legal advice and you do not make
decisions — you surface information so a human can decide.

Rules:
- Base everything ONLY on the provided clause text. Never assume facts not present.
- summary: plainly state what changed (altered terms, numbers, dates, parties,
  obligations, added or removed language). If nothing of substance changed, say so.
- risk_level: none | low | medium | high — how much the change could matter to a
  reviewer (e.g. shifts liability, weakens a protection, changes a deadline or
  amount, adds an obligation). Purely stylistic edits are "none".
- risk_rationale: one or two sentences justifying risk_level, grounded in the text.
- evidence_a / evidence_b: short EXACT quotes from each version showing the change.
  Use an empty string for a side with nothing relevant.
- uncertain: true if the clause is ambiguous, the change is hard to interpret, or
  you lack context to judge risk. It is better to flag uncertainty than to guess.
"""


class LLMClient:
    """Wraps the Anthropic client; returns a validated ClauseAssessment per pair."""

    def __init__(self) -> None:
        import anthropic  # imported here so the package loads without the dep present

        cfg = get_config()
        api_key = cfg["secrets"]["anthropic_api_key"]
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = cfg["comparison"]["model"]
        self._max_tokens = cfg["comparison"]["max_tokens"]

    def assess_clause(self, text_a: str, text_b: str) -> ClauseAssessment:
        """Ask the model to compare two matched clause versions; return validated JSON."""
        user = (
            f'Version A (original):\n"""\n{text_a}\n"""\n\n'
            f'Version B (revised):\n"""\n{text_b}\n"""\n\n'
            "Compare version A to version B."
        )
        response = self._client.messages.parse(
            model=self._model,
            max_tokens=self._max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user}],
            output_format=ClauseAssessment,
        )
        result = response.parsed_output
        if result is None:
            # Refusal or unparseable output — fail safe: flag as uncertain, don't crash.
            return ClauseAssessment(
                summary="The model did not return a structured assessment for this pair.",
                risk_level=RiskLevel.NONE,
                risk_rationale="",
                evidence_a="",
                evidence_b="",
                uncertain=True,
            )
        return result
