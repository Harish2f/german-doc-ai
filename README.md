# GermanDocAI

Production RAG system for German regulatory document intelligence.

Answers questions about BaFin publications, EU AI Act, and DSGVO
using hybrid search and an agentic reasoning layer — built with
DSGVO-compliant architecture and deployed on Azure.

## What This Will Do

- Ingest and parse German regulatory PDFs (BaFin, EU AI Act, DSGVO, Bundesbank)
- Hybrid search combining BM25 keyword and semantic similarity
- LangGraph agent with guardrail, document grading, query rewriting
- DSGVO compliance layer with audit logging and right-to-erasure
- Deployed on Azure Container Apps (West Europe region)

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| API | FastAPI |
| Document Parsing | Docling |
| Search | OpenSearch (hybrid BM25 + semantic) |
| Agent | LangGraph |
| Observability | Langfuse |
| Evaluation | RAGAS |
| Deployment | Azure Container Apps |

## API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | /health | No | Service health check |
| POST | /documents/ | Yes | Store a document |
| GET | /documents/{doc_id} | Yes | Retrieve a document |
| POST | /ingest/ | Yes | Ingest PDF from URL |
| POST | /ask/ | Yes | Hybrid search query |

All protected endpoints require `X-Api-Key` header.

## Development Setup
```bash
git clone https://github.com/harish2f/german-doc-ai
cd german-doc-ai
uv sync
uv run pytest tests/ -v
```

## Quick Start

Start the databases:
```bash
docker-compose up -d
```

Start the API:
```bash
uv run uvicorn src.main:app --reload
```

Run tests:
```bash
uv run pytest tests/ -v
```

Ingest a document:
```bash
curl -X POST http://localhost:8000/ingest/ \
  -H "x-api-key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://arxiv.org/pdf/2303.08774", "title": "GPT-4 Report", "doc_type": "other"}'
```

Ask a question:
```bash
curl -X POST http://localhost:8000/ask/ \
  -H "x-api-key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the safety evaluations?", "doc_types": [], "top_k": 5}'
```


## Build Log

Weekly progress tracked in [docs/build_log.md](docs/build_log.md)