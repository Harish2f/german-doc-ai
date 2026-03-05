# GermanDocAI

Production RAG system for German regulatory document intelligence.

Answers questions about BaFin publications, EU AI Act, and DSGVO
using hybrid search and an agentic reasoning layer — built with
DSGVO-compliant architecture and deployed on Azure.

## Status

🚧 Under active development

## What This Will Do

- Ingest and parse German regulatory PDFs (BaFin, EU AI Act, DSGVO)
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

## Development Setup
```bash
git clone https://github.com/harish2f/german-doc-ai
cd german-doc-ai
uv sync
uv run pytest tests/ -v
```

## Build Log

Weekly progress tracked in [docs/build_log.md](docs/build_log.md)