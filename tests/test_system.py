"""
Automated checks, including a reproduction of the exact example use case in the
challenge PDF: SOC 0.3%, low rainfall, monoculture wheat, semi-arid region ->
system should surface agroforestry/intercropping with quantified soil-carbon and
biodiversity impacts and credible sourcing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.conversation_manager import ConversationManager, parse_free_text
from src.models import UserContext
from src.reasoning_engine import build_causal_chain, multi_metric_breadth_score


def test_free_text_parsing_extracts_key_variables():
    text = "Soil organic carbon is 0.3%, rainfall is low, monoculture wheat, semi-arid region."
    parsed = parse_free_text(text)
    assert parsed["soil_organic_carbon"] == 0.3
    assert parsed["rainfall"] in ("low", "semi_arid")
    assert "wheat" in parsed["land_use"] or "monoculture" in parsed["land_use"]


def test_missing_fields_triggers_clarifying_question():
    manager = ConversationManager()
    result = manager.handle_message("test-session-1", text="Biodiversity is declining on my land")
    assert result["type"] == "clarifying_question"
    assert "soil" in result["message"].lower() or "carbon" in result["message"].lower() \
        or "rainfall" in result["message"].lower() or "land use" in result["message"].lower()


def test_pdf_example_use_case_generates_grounded_recommendation():
    manager = ConversationManager()
    session_id = "test-session-pdf-example"

    r1 = manager.handle_message(
        session_id,
        structured={
            "soil_organic_carbon": 0.3,
            "rainfall": "semi_arid",
            "land_use": "monoculture_wheat",
            "region": "semi-arid",
        },
    )
    assert r1["type"] == "recommendations"

    combined_text = r1["message"].lower()
    # Expected output per PDF: agroforestry/intercropping, soil carbon + biodiversity impact,
    # credible source reference (FAO / IPCC).
    assert "agroforestry" in combined_text or "intercrop" in combined_text
    assert "soil_organic_carbon" in combined_text or "soil organic carbon" in combined_text
    assert "fao" in combined_text or "ipcc" in combined_text

    recs = r1["recommendations"]
    assert len(recs) >= 1
    top = recs[0]
    assert set(["action", "reasoning", "impacted_metrics", "time_horizon", "confidence", "source"]) <= set(top.keys())
    assert len(top["impacted_metrics"]) >= 2  # multi-metric, not single-variable


def test_multi_turn_memory_persists_context():
    manager = ConversationManager()
    session_id = "test-session-memory"
    manager.handle_message(session_id, text="Soil organic carbon is 0.3%")
    r2 = manager.handle_message(session_id, text="rainfall is low")
    r3 = manager.handle_message(session_id, text="it's monoculture wheat land, semi-arid region")
    assert r3["known_context"]["soil_organic_carbon"] == 0.3
    # Later turns may sharpen "low" to "semi_arid" as more context arrives — memory persists,
    # it doesn't just keep the first value.
    assert r3["known_context"]["rainfall"] in ("low", "semi_arid")
    assert r3["known_context"]["land_use"] is not None
    assert r3["type"] in ("recommendations", "clarifying_question")


def test_causal_chain_is_multi_metric():
    chain = build_causal_chain(["soil_organic_carbon"])
    assert any("microbial_diversity" in step for step in chain)
    breadth = multi_metric_breadth_score(["soil_organic_carbon", "species_richness", "water_retention"])
    assert breadth >= 2


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
            passed += 1
        except Exception:
            print(f"FAIL: {t.__name__}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
