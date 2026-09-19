"""
Knowledge retrieval layer.

Design note (why TF-IDF and not a hosted embedding API):
This hackathon environment has no outbound access to model-hosting APIs, so retrieval
here uses scikit-learn's TF-IDF vectorizer + cosine similarity as a transparent,
dependency-light stand-in for a dense embedding index. The retrieval CONTRACT is what
matters for the architecture (query -> vector similarity -> ranked structured records
-> filtered by explicit conditions), and this module is written so `_vectorize()` and
`retrieve()` can be swapped for a real embedding model (e.g. sentence-transformers,
OpenAI/Voyage embeddings, or a hosted vector DB such as Pinecone/Weaviate/pgvector)
by changing only this file — nothing in reasoning_engine.py or conversation_manager.py
needs to change, since they only depend on the RetrievedKnowledge contract in models.py.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import RetrievedKnowledge

KB_PATH = Path(__file__).resolve().parent.parent / "knowledge_base" / "interventions.json"


class KnowledgeRetriever:
    def __init__(self, kb_path: Path = KB_PATH):
        with open(kb_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self.interventions: List[Dict] = raw["interventions"]
        self._corpus = [self._record_to_text(rec) for rec in self.interventions]
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform(self._corpus)

    @staticmethod
    def _record_to_text(rec: Dict) -> str:
        parts = [
            rec["title"],
            " ".join(rec.get("categories", [])),
            rec.get("mechanism", ""),
            " ".join(rec.get("linked_metrics", [])),
        ]
        return " ".join(parts)

    def _condition_match_score(self, rec: Dict, context: Dict) -> float:
        """
        Structured filter layer, applied on top of vector similarity.
        Rewards interventions whose declared applicable_conditions match the
        user's actual land_use / rainfall / soil state, so retrieval is grounded
        in the structured dataset, not text similarity alone.
        """
        cond = rec.get("applicable_conditions", {})
        score = 0.0

        land_use = (context.get("land_use") or "").lower().replace(" ", "_")
        if land_use and cond.get("land_use"):
            if any(lu in land_use or land_use in lu for lu in cond["land_use"]):
                score += 1.0

        rainfall = (context.get("rainfall") or "").lower().replace(" ", "_")
        if rainfall and cond.get("rainfall"):
            if rainfall in [r.lower() for r in cond["rainfall"]]:
                score += 1.0
            elif "semi_arid" in rainfall and "low" in [r.lower() for r in cond["rainfall"]]:
                score += 0.5

        soc = context.get("soil_organic_carbon")
        if soc is not None and "soil_organic_carbon_max" in cond:
            if float(soc) <= float(cond["soil_organic_carbon_max"]):
                score += 1.0

        human_impact = context.get("human_impact") or []
        if human_impact and cond.get("human_impact"):
            overlap = set(h.lower() for h in human_impact) & set(h.lower() for h in cond["human_impact"])
            if overlap:
                score += 0.5 * len(overlap)

        return score

    def retrieve(
        self,
        query: str,
        context: Optional[Dict] = None,
        top_k: int = 4,
    ) -> List[RetrievedKnowledge]:
        context = context or {}
        query_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self._matrix).flatten()

        scored = []
        for idx, rec in enumerate(self.interventions):
            vector_score = float(sims[idx])
            condition_score = self._condition_match_score(rec, context)
            # Weighted blend: structured condition match dominates (this is what makes
            # the system "know" agroforestry fits semi-arid monoculture, not just that
            # the words are similar), vector similarity breaks ties / covers free text.
            combined = 0.4 * vector_score + 0.6 * (condition_score / 3.5)
            scored.append((combined, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, rec in scored[:top_k]:
            results.append(
                RetrievedKnowledge(
                    intervention_id=rec["id"],
                    title=rec["title"],
                    mechanism=rec["mechanism"],
                    quantified_impact=rec["quantified_impact"],
                    linked_metrics=rec["linked_metrics"],
                    source=rec["source"],
                    time_horizon=rec["time_horizon"],
                    confidence=rec["confidence"],
                    relevance_score=round(score, 4),
                )
            )
        return results
