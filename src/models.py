"""
Core data structures shared across the retrieval, reasoning and conversation layers.

Kept deliberately framework-agnostic (plain dataclasses) so the same objects can be
reused whether the system is driven from the CLI (src/main.py) or the web API (app.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Fields the reasoning engine needs before it can generate a grounded recommendation.
REQUIRED_FIELDS = ["soil_organic_carbon", "rainfall", "land_use"]

# Fields that sharpen recommendations but are not strictly required.
OPTIONAL_FIELDS = [
    "region",
    "crop",
    "temperature",
    "human_impact",
    "species_richness",
    "habitat_diversity",
    "latitude",
    "longitude",
]

ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS


@dataclass
class UserContext:
    """
    Accumulated, multi-turn memory for a single conversation session.
    Values are progressively filled in as the user supplies more information
    (text or structured JSON) across turns.
    """
    soil_organic_carbon: Optional[float] = None      # percent, e.g. 0.3
    rainfall: Optional[str] = None                   # "low" | "medium" | "high" | "semi_arid"
    land_use: Optional[str] = None                   # e.g. "monoculture_wheat"
    region: Optional[str] = None                      # free text, e.g. "semi-arid"
    crop: Optional[str] = None
    temperature: Optional[float] = None
    human_impact: List[str] = field(default_factory=list)   # e.g. ["pollution", "deforestation"]
    species_richness: Optional[str] = None            # qualitative or quantitative note
    habitat_diversity: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    turn_count: int = 0
    history: List[Dict[str, str]] = field(default_factory=list)  # [{"role": "user"/"assistant", "text": ...}]

    def missing_required_fields(self) -> List[str]:
        missing = []
        for f in REQUIRED_FIELDS:
            if getattr(self, f) in (None, "", []):
                missing.append(f)
        return missing

    def is_ready_for_recommendation(self) -> bool:
        # We can reason once at least 2 of 3 required fields plus land_use are present,
        # per the challenge's "at least 3 environmental variables together" constraint.
        filled_required = [f for f in REQUIRED_FIELDS if getattr(self, f) not in (None, "", [])]
        filled_optional = [f for f in OPTIONAL_FIELDS if getattr(self, f) not in (None, "", [])]
        return (len(filled_required) + len(filled_optional)) >= 3 and self.land_use is not None

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        for key, value in data.items():
            if key == "human_impact" and value:
                if isinstance(value, str):
                    value = [v.strip() for v in value.split(",")]
                existing = set(self.human_impact)
                for v in value:
                    if v not in existing:
                        self.human_impact.append(v)
            elif key in ALL_FIELDS and value not in (None, ""):
                setattr(self, key, value)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "soil_organic_carbon": self.soil_organic_carbon,
            "rainfall": self.rainfall,
            "land_use": self.land_use,
            "region": self.region,
            "crop": self.crop,
            "temperature": self.temperature,
            "human_impact": self.human_impact,
            "species_richness": self.species_richness,
            "habitat_diversity": self.habitat_diversity,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


@dataclass
class RetrievedKnowledge:
    intervention_id: str
    title: str
    mechanism: str
    quantified_impact: List[Dict[str, str]]
    linked_metrics: List[str]
    source: str
    time_horizon: str
    confidence: str
    relevance_score: float


@dataclass
class Recommendation:
    action: str                       # "What to do"
    reasoning: str                    # "Why it works" (mechanism + causal chain)
    impacted_metrics: List[str]
    time_horizon: str
    confidence: str
    source: str
    quantified_impact: List[Dict[str, str]]
    linked_reasoning_chain: List[str] = field(default_factory=list)  # multi-metric causal chain

    def to_text(self) -> str:
        lines = [f"• Recommendation: {self.action}"]
        lines.append(f"  Why it works: {self.reasoning}")
        if self.linked_reasoning_chain:
            lines.append("  Multi-metric chain: " + " → ".join(self.linked_reasoning_chain))
        impacts = "; ".join(
            f"{i['metric']}: {i['change']} ({i['timeframe']})" for i in self.quantified_impact
        )
        lines.append(f"  Expected impact: {impacts}")
        lines.append(f"  Impacted metrics: {', '.join(self.impacted_metrics)}")
        lines.append(f"  Time horizon: {self.time_horizon}")
        lines.append(f"  Confidence: {self.confidence}")
        lines.append(f"  Source: {self.source}")
        return "\n".join(lines)
