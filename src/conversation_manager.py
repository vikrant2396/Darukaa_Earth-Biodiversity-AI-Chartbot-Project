"""
Conversational intelligence layer.

Responsibilities (mapped directly to the challenge's "Conversational Intelligence"
requirement):
  1. Parse free text OR structured JSON input into the shared UserContext.
  2. Track state across turns (memory) rather than treating each message independently.
  3. Ask clarifying questions when required environmental variables are missing.
  4. Once enough context exists, call the retriever + reasoning engine and format
     output per the required schema (recommendation, impacted metrics, time horizon,
     confidence).
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from .knowledge_retriever import KnowledgeRetriever
from .models import REQUIRED_FIELDS, Recommendation, UserContext
from .reasoning_engine import generate_recommendations

CLARIFYING_QUESTIONS = {
    "soil_organic_carbon": "What is the soil organic carbon percentage (or a rough estimate: very low / low / moderate / high)?",
    "rainfall": "What is the rainfall pattern in the area (low / semi-arid / medium / high)?",
    "land_use": "What is the current land use or crop pattern (e.g. monoculture wheat, pasture, degraded land)?",
}

# Lightweight text-parsing patterns for the mandatory free-text input channel.
_SOC_PATTERN = re.compile(r"(?:soil organic carbon|soc)\D{0,10}(\d+(?:\.\d+)?)\s*%?", re.IGNORECASE)
_RAINFALL_KEYWORDS = {
    "semi-arid": "semi_arid", "semi arid": "semi_arid", "arid": "semi_arid",
    "low rainfall": "low", "low": "low", "drought": "low",
    "high rainfall": "high", "heavy rain": "high", "high": "high",
    "medium rainfall": "medium", "moderate rainfall": "medium",
}
_LAND_USE_KEYWORDS = [
    "monoculture wheat", "monoculture", "wheat", "pasture", "grassland", "rangeland",
    "degraded land", "degraded wetland", "wetland", "cropland", "arable",
    "forest", "plantation", "fragmented habitat",
]
_HUMAN_IMPACT_KEYWORDS = ["pollution", "deforestation", "pesticide", "overgrazing", "runoff", "drainage", "erosion"]


def parse_free_text(text: str) -> Dict:
    """Best-effort structured extraction from a natural-language message.
    This is intentionally simple/rule-based (transparent and debuggable for a hackathon
    submission); in production this stage is where an LLM function-calling extraction
    step would sit, feeding the same UserContext.update_from_dict() contract."""
    extracted: Dict = {}
    lower = text.lower()

    soc_match = _SOC_PATTERN.search(text)
    if soc_match:
        extracted["soil_organic_carbon"] = float(soc_match.group(1))

    for phrase, value in _RAINFALL_KEYWORDS.items():
        if phrase in lower:
            extracted["rainfall"] = value
            break

    for phrase in _LAND_USE_KEYWORDS:
        if phrase in lower:
            extracted["land_use"] = phrase.replace(" ", "_")
            break

    impacts = [k for k in _HUMAN_IMPACT_KEYWORDS if k in lower]
    if impacts:
        extracted["human_impact"] = impacts

    region_match = re.search(r"region[:\s]+([a-zA-Z\- ]+)", text, re.IGNORECASE)
    if region_match:
        extracted["region"] = region_match.group(1).strip()

    return extracted


class ConversationManager:
    def __init__(self, retriever: Optional[KnowledgeRetriever] = None):
        self.retriever = retriever or KnowledgeRetriever()
        self.sessions: Dict[str, UserContext] = {}

    def get_or_create_session(self, session_id: str) -> UserContext:
        if session_id not in self.sessions:
            self.sessions[session_id] = UserContext()
        return self.sessions[session_id]

    def _next_clarifying_question(self, context: UserContext) -> Optional[str]:
        missing = context.missing_required_fields()
        if not missing:
            return None
        field = missing[0]
        return CLARIFYING_QUESTIONS[field]

    def handle_message(
        self,
        session_id: str,
        text: Optional[str] = None,
        structured: Optional[Dict] = None,
    ) -> Dict:
        """
        Main entry point. Accepts free text and/or a structured JSON payload (both may
        be supplied at once; structured values take precedence on conflict since they
        are unambiguous). Returns a dict describing either a clarifying question or a
        set of recommendations, plus the current known context (transparency into
        what the system believes it knows — useful for debugging/demo).
        """
        context = self.get_or_create_session(session_id)
        context.turn_count += 1

        if text:
            context.history.append({"role": "user", "text": text})
            context.update_from_dict(parse_free_text(text))
        if structured:
            context.update_from_dict(structured)

        if not context.is_ready_for_recommendation():
            question = self._next_clarifying_question(context)
            if question is None:
                question = (
                    "Could you tell me a bit more about the land — e.g. crop type, region, "
                    "or any human impact factors like pollution or deforestation?"
                )
            context.history.append({"role": "assistant", "text": question})
            return {
                "type": "clarifying_question",
                "message": question,
                "known_context": context.as_dict(),
                "turn": context.turn_count,
            }

        recommendations = self._generate(context)
        summary = self._format_response(recommendations)
        context.history.append({"role": "assistant", "text": summary})
        return {
            "type": "recommendations",
            "message": summary,
            "recommendations": [r.__dict__ for r in recommendations],
            "known_context": context.as_dict(),
            "turn": context.turn_count,
        }

    def _generate(self, context: UserContext) -> List[Recommendation]:
        query_parts = [
            context.land_use or "",
            context.region or "",
            context.crop or "",
            " ".join(context.human_impact),
            "biodiversity soil water land use improvement",
        ]
        query = " ".join(p for p in query_parts if p)
        retrieved = self.retriever.retrieve(query=query, context=context.as_dict(), top_k=6)
        return generate_recommendations(context, retrieved, max_recommendations=3)

    @staticmethod
    def _format_response(recommendations: List[Recommendation]) -> str:
        if not recommendations:
            return "No sufficiently relevant, evidence-backed intervention was found for this combination of conditions."
        parts = [r.to_text() for r in recommendations]
        return "\n\n".join(parts)
