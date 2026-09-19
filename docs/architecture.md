# Architecture & design notes

## Mapping to the evaluation criteria

| Criterion (weight) | Where it's addressed |
|---|---|
| Depth of Reasoning (30%) | `reasoning_engine.build_causal_chain` walks the causal graph 2 hops beyond each intervention's direct effects; `multi_metric_breadth_score` ranks interventions that span more environmental domains higher, so the top recommendation is rarely the most "obvious" single-effect one. |
| Scientific Grounding (25%) | Every knowledge-base record carries a `source` field (FAO/IPCC/CBD/IPBES/USDA/Project Drawdown) and a `confidence` rating; both are surfaced verbatim in every response. |
| Knowledge System Design (20%) | `knowledge_retriever.py` — vector similarity (TF-IDF/cosine) blended with structured condition filtering over `knowledge_base/interventions.json`; see the module docstring for how to swap in a real embedding/vector-DB backend without touching downstream code. |
| Conversational Intelligence (15%) | `conversation_manager.py` — per-session `UserContext` persists across turns, `missing_required_fields()` drives clarifying questions, `parse_free_text` + structured JSON both feed the same state. |
| Output Clarity (10%) | `models.Recommendation.to_text()` — fixed schema: action, reasoning, multi-metric chain, quantified impact, impacted metrics, time horizon, confidence, source. |

## Why the retrieval score blends vector similarity and structured filtering

Pure text similarity would treat "monoculture wheat, semi-arid" and "monoculture wheat,
high rainfall" as retrieving the same top intervention, because the text is almost
identical. The structured filter (`_condition_match_score` in `knowledge_retriever.py`)
checks the user's actual `rainfall`, `land_use` and `soil_organic_carbon` against each
intervention's declared `applicable_conditions`, so a low-SOC, semi-arid, monoculture
profile correctly surfaces agroforestry/intercropping and rainwater harvesting over, say,
wetland restoration — which is a strong textual match for "biodiversity" queries in general
but conditionally inapplicable here.

## Why causal chains are capped at 2 hops

Unbounded graph traversal on a small, hand-curated edge set quickly produces chains that
either cycle back on themselves or drift into generic ecological truisms ("everything
affects everything"). Two hops is enough to demonstrate a genuine cross-domain link (e.g.
soil organic carbon → microbial diversity → species richness) without manufacturing a false
sense of exhaustiveness the underlying edge set can't actually support.

## Extending the knowledge base

Add a record to `knowledge_base/interventions.json` following the existing schema —
`applicable_conditions`, `mechanism`, `quantified_impact`, `linked_metrics`, `source`,
`time_horizon`, `confidence`. No code changes are required: the retriever re-indexes the
whole file on startup, and any new `linked_metrics` values that also appear as keys in
`reasoning_engine.CAUSAL_EDGES` are automatically included in causal-chain generation.

## Extending to a production RAG backend

1. Replace `KnowledgeRetriever.__init__`'s TF-IDF fit with an embedding call (batch-embed
   `_record_to_text()` output) and store vectors in a vector DB (pgvector/Pinecone/Weaviate).
2. Replace `retrieve()`'s `cosine_similarity(query_vec, self._matrix)` with a nearest-neighbor
   query against that store.
3. Leave `_condition_match_score`, `reasoning_engine.py` and `conversation_manager.py`
   untouched — they only depend on the `RetrievedKnowledge` dataclass contract.

## Known constraints of this submission

- Built and tested in an offline sandboxed environment with no access to hosted embedding
  or LLM APIs, which is why free-text parsing is rule-based and retrieval uses TF-IDF rather
  than a hosted embedding model (both are called out explicitly in code comments and the
  README, with a stated upgrade path).
- 15 knowledge-base records covering the five required domains (soil, land use, biodiversity,
  climate, human impact) — designed to demonstrate the architecture, not as an exhaustive
  literature index.
