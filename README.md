# Darukaa.Earth — AI Biodiversity Intelligence Chatbot

## Why this design

The brief explicitly penalizes "generic LLM-only solutions" and single-variable answers, and
rewards a retrievable knowledge layer plus multi-metric causal reasoning. So instead of
putting facts in a prompt, this system separates three concerns:

1. **A structured, retrievable knowledge base** (`knowledge_base/interventions.json`) — 15
   land/soil/water/biodiversity interventions, each with applicability conditions, a causal
   mechanism, quantified impact ranges, a source, a time horizon and a confidence level.
2. **A retrieval layer** (`src/knowledge_retriever.py`) that ranks knowledge-base entries
   against a query using TF-IDF vector similarity *combined with* structured condition
   matching (soil carbon thresholds, rainfall regime, land use) — so retrieval is grounded
   in the user's actual numbers, not just keyword overlap.
3. **A causal reasoning engine** (`src/reasoning_engine.py`) that encodes explicit
   soil↔biodiversity, water↔species-survival and land-use↔fragmentation relationships as a
   graph, walks outward from each intervention's directly affected metric to surface
   downstream cross-domain effects, and ranks recommendations higher when they touch more
   distinct environmental domains.

A conversational layer (`src/conversation_manager.py`) sits on top: it maintains per-session
memory across turns, asks clarifying questions when required variables (soil organic carbon,
rainfall, land use) are missing, and accepts both free text and structured JSON.

## Architecture

```
                     ┌─────────────────────────┐
   User (text/JSON)  │   ConversationManager    │  ← multi-turn memory, clarifying Qs
   ────────────────► │  (conversation_manager)  │
                      └───────────┬─────────────┘
                                  │ query + structured context
                                  ▼
                      ┌─────────────────────────┐
                      │   KnowledgeRetriever      │  ← TF-IDF vector similarity
                      │  (knowledge_retriever)    │  + structured condition filter
                      └───────────┬─────────────┘
                                  │ ranked RetrievedKnowledge[]
                                  ▼
                      ┌─────────────────────────┐
                      │   Reasoning Engine        │  ← causal graph walk,
                      │   (reasoning_engine)      │    multi-metric domain scoring
                      └───────────┬─────────────┘
                                  │ Recommendation[]
                                  ▼
                      formatted response: what to do / why / metrics / horizon / confidence
```

Two front ends consume the same core (`src/`) so the reasoning logic is never duplicated:
- **CLI** (`src/main.py`) — interactive terminal demo.
- **Web API + minimal chat UI** (`app.py`, `templates/index.html`) — FastAPI backend with a
  single `/chat` endpoint, served with a plain HTML/JS page for the live demo.

## Data / schema

`knowledge_base/interventions.json` — one JSON document, `interventions: [...]`, each record:

| Field | Purpose |
|---|---|
| `applicable_conditions` | thresholds/tags used by the structured filter (soc max, land use, rainfall, human impact) |
| `mechanism` | the scientific "why it works" |
| `quantified_impact` | list of `{metric, change, timeframe, confidence}` |
| `linked_metrics` | seeds for the causal-chain walk |
| `source` | organization/report attribution (FAO, IPCC, CBD, IPBES, USDA NRCS, Project Drawdown) |
| `time_horizon`, `confidence` | surfaced directly in output |

`src/models.py` defines the in-memory contracts (`UserContext`, `RetrievedKnowledge`,
`Recommendation`) that every layer shares — swapping the retrieval backend (see below) only
requires touching `knowledge_retriever.py`.

There is no external database for this prototype; the JSON file *is* the structured dataset
the retriever indexes. This keeps the submission runnable with zero infrastructure while
keeping the retrieval contract identical to what a real vector DB would provide.

## Local setup

Requires Python 3.10+.

```bash
git clone <this-repo-url>
cd darukaa-biodiversity-ai
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt

# Run the automated tests (includes the exact example from the challenge PDF)
python tests/test_system.py

# Option A: interactive CLI
python -m src.main

# Option B: web app (chat UI at http://localhost:8000)
uvicorn app:app --reload --port 8000
```

### Example (matches the PDF's worked example)

```
json:{"soil_organic_carbon": 0.3, "rainfall": "low", "land_use": "monoculture_wheat", "region": "semi-arid"}
```
→ top recommendation: **Agroforestry / intercropping**, with quantified soil-carbon and
biodiversity impact, an explicit multi-metric causal chain, and FAO/IPCC sourcing — see
`examples/example_run.md` for a full transcript.

## API

`POST /chat`
```json
{ "session_id": "optional-uuid", "text": "free text turn", "structured": {"soil_organic_carbon": 0.3}, "latitude": 19.07, "longitude": 72.87 }
```
Returns `{ type: "clarifying_question" | "recommendations", message, known_context, recommendations, turn }`.

`GET /health` — liveness check for deployment platforms.

## CI/CD

`.github/workflows/ci.yml` runs `pip install -r requirements.txt` and `python
tests/test_system.py` on every push/PR to `main`, so a broken retriever or reasoning change
fails the build before merge. There is no separate CD/deploy step wired up in this repo —
deployment is a one-command `uvicorn` start on any Python host (Render/Railway/Fly.io/HF
Spaces); see "Deploying the live demo" below.

## Deploying the live demo

The app has no external services or secrets, so any platform that runs a Python web process
works:
- **Render / Railway**: connect the repo, build command `pip install -r requirements.txt`,
  start command `uvicorn app:app --host 0.0.0.0 --port $PORT`.
- **Hugging Face Spaces (Docker SDK)**: add a `Dockerfile` (`FROM python:3.11-slim`, copy repo,
  `pip install -r requirements.txt`, `CMD ["uvicorn","app:app","--host","0.0.0.0","--port","7860"]`).

## Design decisions & honest limitations

- **Retrieval uses TF-IDF, not a hosted embedding model.** The engine this was built in has
  no network access to embedding APIs. TF-IDF + cosine similarity implements the same
  retrieval *contract* (query → ranked structured records) as a dense embedding index, and
  `knowledge_retriever.py` is written so a real embedding model or vector DB (Pinecone,
  Weaviate, pgvector, sentence-transformers) drops in without touching the reasoning or
  conversation layers.
- **Free-text extraction is rule-based** (`conversation_manager.parse_free_text`), not an LLM
  call — deliberately, so the pipeline is transparent and fully offline/testable. In
  production this stage is the natural place for an LLM function-calling extraction step,
  feeding the same `UserContext.update_from_dict()` contract, with no changes needed
  downstream.
- **Knowledge base figures are illustrative ranges** drawn from widely-cited FAO/IPCC/CBD/
  IPBES literature, not measurements from a specific site. `knowledge_base/interventions.json`
  documents this in its `metadata.note_on_sources` field; before real deployment, each figure
  should be checked against its primary study.
- **15 curated interventions**, not an ingested corpus of full papers — sufficient to
  demonstrate the retrieval + multi-metric reasoning architecture end-to-end; scaling to a
  full literature corpus is a matter of adding records (or documents to embed) with the same
  schema, not redesigning the pipeline.

## Repository layout

```
knowledge_base/interventions.json   structured, sourced knowledge base
src/models.py                       shared data contracts
src/knowledge_retriever.py          RAG-style retrieval (TF-IDF + structured filtering)
src/reasoning_engine.py             causal graph, multi-metric scoring, recommendation generation
src/conversation_manager.py         multi-turn memory, clarifying questions, text/JSON parsing
src/main.py                         CLI demo
app.py                              FastAPI web app
templates/index.html                minimal chat UI
tests/test_system.py                automated tests incl. the PDF's worked example
examples/example_run.md             full annotated transcript
docs/architecture.md                extended design notes
.github/workflows/ci.yml            CI: install + test on push/PR
```
