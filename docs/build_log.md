# GermanDocAI Build Log

## Project Setup

### What I built
- Project structure: src/, tests/, docs/, scripts/
- pyproject.toml with uv dependency management
- Document Pydantic model with DocumentType enum
- 7 passing tests covering all Document methods

### What broke and how I fixed it
- ModuleNotFoundError: src not found by pytest
  Fix: added pythonpath = ["."] to pyproject.toml
- PydanticUserError: missing type annotation on doc_type
  Fix: changed `doc_type = DocumentType` to `doc_type: DocumentType`

### What I learned
- Enum prevents silent string comparison bugs by failing loudly
- Pydantic requires colon syntax for field definitions, not equals
- default_factory vs default: use default_factory for anything that should be called fresh each time

## Pydantic Settings, Structured Logging, Async/Await


### What I built
- src/config.py — Pydantic Settings with environment variable management
- src/logger.py — structlog structured logging with dev/production renderers
- Async/await tested from first principles with timing demonstration
- 18 tests passing

### What I learned
- Pydantic Settings reads .env files automatically and validates types
- get_settings() as factory function enables caching and test overrides
- Nested class vs model_config — always use modern SettingsConfigDict in Pydantic v2
- structlog processor chain — each log event passes through processors in order
- async/await: concurrent queries took 2.25s vs 4.5s sequential — 50% faster
- asyncio.gather() runs multiple coroutines simultaneously
- await only works inside async def — SyntaxError otherwise

### What broke and how I fixed it
- Hit PydanticUserError on missing type annotation — error message pointed exactly to the line, fixed by adding : str annotation. Because Pydantic requires colon syntax not equals for field definitions.
- caught format_exc_info() with parentheses — passing return value instead of function reference, silent bug that would have broken exception logging in production
- Caught the typo in opeansearch_port through testing and fixed it.

### What I would do differently
- I would test each function in the Python shell immediately after writing it instead of writing everything and running pytest at the end  would have caught the annotation errors faster.

## FastAPI Endpoints with Auth, logging and tests

### What I built
- Custom API endpoints for document module and health module.
- Refactored existing tests to mimic the source code's structure and developed tests for the API endpoints.
- Created dependencies module to read environment file only once at the startup and generate unique request id for each API request.
- 28 tests passing.

### What I learnt
- Adding @lru_cache helps redundant disk reads by caching Settings in memory after the first load.
- came across datetime.utcnow() function deprication and fixed it to lambda: datetime.now(timezone.utc)
- How APIRouter organises endpoints into separate files and why that matters as the project grows.
- The difference between prefix="/documents" on the router vs defining full paths in each endpoint.
- How TestClient works — tests the full request/response cycle without starting a real server.
- Why conftest.py fixtures are better than imports — pytest manages lifecycle, enables overrides in Week 4.
- The lifespan pattern in FastAPI — replaces deprecated on_event handlers, code before yield runs on startup, after yield on shutdown.

### What broke and how I fixed it
- x_api_key vs x-api-key in conftest.py — underscore instead of hyphen meant auth headers were never sent, all protected endpoint tests returned 401.
- status_code=200 vs status_code=201 — POST endpoint returns 201 Created not 200 OK, test was asserting the wrong code.

### What I would do differently
- Realized i wrote json definitions manually for each tests, I would use pytest fixtures to define test documents once and reuse them. 

## DB, OpenSearch & Docker compose

### What I built
- Built docker file with Postgres and OpenSearch services with healthchecks.
- Defined volumes for persistent storage outside containers.
- Established postgreSQL and OpenSearch connection and tested async request handling in Swagger and added as services in the github workflows.
- Refactored existing codebase with db instance from in memory dictionary.
- Isolated tests to run on SQLite in in-memory instead of running in Postgres. Same 28 tests now also testing db connection and Opensearch. 

### What I learnt
- Got better understanding on container volumes and persistent memory management.
-  PostgreSQL Docker image on Apple Silicon has a known bug where POSTGRES_USER is ignored when it is not 'postgres'. Debugged by inspecting container logs and checking actual roles with psql.
- In SQLAlchemy, DATETIME function should have timezone=True to enable timezone parsing.

### What broke and how I fixed it
- I was passing DATETIME function in SQLAlchemy without timezone and comparing with created_at timestamp and fixed it later by setting timezone=True.
- Had problem establishing ROLE in Postgres with SQLAlchemy because of having a different user_name, it's a known bug in Apple Silicon and fixed it with the username: postgres.
- After establishing db, tests failed because of duplicate id's in the database, so I isolated tests to run on SQLite instead of Postgres db in production and established async SQLite session in conftest.

### What I would do differently
- Not technical, but forgot to document and build logs. Next time, i will make sure i also build the logs before I push the code.

## Docling Parser and Hybrid search with OpenSearch

### What I built
- Built ingestion pipelines for docling parser, embedder and chunker with sliding window overlap.
- Built endpoints for data ingestion and ask query. 
- Build hybrid search with BM25 and Knn semantic search combined with Reciprocal Rank Fusion to reward the chunks with low semantic differences.
- Built mockers for tests to avoid real API calls or Db compute.
- 34 tests passing.

### What I learnt
- learnt mocking is defined on where the functions are used, not where they are defined. This helps to mock the entire function we want to mock.
- Reciprocal Rank Fusion rewards chunks that appear high in both BM25 keyword search and KNN semantic search — consensus between both methods produces the highest combined score.
- Though, Docling is good at handling and parsing PDF's, it by defaults rejects PDF's during ingestion directly from the URL and the file format has to be defined individually.

### What broke and How I fixed it
- Made a typo in reciprocal rank fusion function, defined it as 'rrf_score' but calling it as 'rff_score', understood the issue from error message and fixed it.
- Defined ingestion endpoints with '/ingestion' and tried calling it as '/ingest', throwing error and fixed it by referencing '/ingestion'
- Docling detects file format from URL extension - URLs without .pdf extension are rejected by default. Fixed by explicitly configuring InputFormat.PDF and PdfFormatOption in the converter.

### What I would do differently
- may be maintain a list of variables created to maintain and reference easily without dwelling through whole codebase.
- Try to write the result of Each API request to a custom table for better auditability.

## RAG Generator, Rate Limiter, Circuit Breaker

### What I built
- Azure OpenAI integration with GPT-4o, system prompt for regulatory compliance, temperature=0.0 for deterministic answers, token usage tracking
- sliding window rate limiter using deque, 60 requests per minute, queues excess requests instead of rejecting
- Three state machine (CLOSED/OPEN/HALF_OPEN), opens after 5 failures, recovers after 60 seconds
- Now returns real answers from GPT-4o with sources and token counts
- Tests for all three RAG components — 44 tests passing.

### What I learnt
- temperature=0.0 ensures deterministic outputs, critical for regulatory compliance
- Token counting is required for both cost monitoring and rate limit management
- Circuit breaker states — CLOSED normal, OPEN fail fast, HALF_OPEN probes recovery
	•	deque vs list — popleft() is O(1) vs O(n), critical for rate limiter performance
- RAG vs raw LLM — enables use of proprietary data, provides citations, improves cost control
- Patch where used not where defined — mock src.rag.generator.get_azure_openai_client, not openai client directly

### What broke and how I fixed it
- DeploymentNotFound — Azure OpenAI deployment takes 5–10 minutes to provision after creation, fixed by waiting for deployment readiness
- failure_content typo in circuit breaker init — should be failure_count, fixed incorrect attribute name
- doc_types is False bug in ask endpoint — empty list is not False, fixed with if request.doc_types
- rl.acquire without parentheses in rate limiter test — function was referenced instead of called, fixed by adding ()
- mocker was trying to call real Azure OpenAI API, fixed by adding a fixture of generate answer and added the fixture function as a parameter for the tests.

### What I would do differently

- Add token usage thresholds and alerts to proactively control cost spikes
- Log circuit breaker state transitions for better observability in production
- Standardize request/response logging for full traceability of RAG pipeline

## LangGraph Agent layer

### What I built
- Implemented a LangGraph-based RAG agent with a StateGraph controlling retrieval, grading, rewriting, and generation steps.
- Designed a shared agent state (TypedDict) to pass query, retrieved chunks, rewrite count, and generation results across nodes.
- Implemented agent nodes for retrieval (hybrid_search), document grading (LLM), query rewriting (LLM), and answer generation.
- Built conditional routing logic (grade_query, should_rewrite) to control out-of-scope detection and retrieval retry loops.
- Created an agent execution wrapper (run_agent) to initialise state and run the graph asynchronously.
- Added a FastAPI /agent endpoint integrating circuit breaker, rate limiting, and OpenSearch dependency injection.

### What I Learned
- How LangGraph StateGraph works: nodes perform operations while edges define control flow.
- The difference between graph nodes (operations) and conditional edges (decision routing).
- Using functools.partial() for dependency injection when graph nodes require external services (OpenSearch).
- Benefits of TypedDict for agent state management and predictable state merging across nodes.
- Implementing simple query classification using keyword matching (grade_query).
- Preventing infinite loops in agent workflows using a maximum rewrite limit (should_rewrite)

### What broke and how I fixed it
- Homebrew PostgreSQL conflict caused port/service issues → resolved by stopping the system instance and restarting the Homebrew-managed service.
- Incorrect test patching target (src.agent.nodes.generate_answer) - fixed by patching the correct import path src.rag.generator.generate_answer.
- Incorrect test patching target (src.agent.nodes.grade_documents) - fixed by directly mocking Azure client inside grade documents mocker

### What I would do differently
- 	Improve document grading output to include confidence scores and reasoning instead of a binary flag.
- Add observability and tracing (LangSmith or structured metrics) for node execution and token usage.
- add Cache query rewrites to reduce repeated LLM calls for similar queries.
- Persist agent run metadata (query, rewrites, retrieved chunks, answer) for evaluation and debugging

## DSGVO Compliance layer

### What I built
- Built a DSGVO compliance module split into audit logging, chat history management, and full user data erasure across systems.
- Implemented async repositories + services for PostgreSQL entities (AuditLog, ChatSession, ChatMessage, DocumentRecord).
- Added end-to-end erasure workflow coordinating OpenSearch deletion first, then relational DB cleanup with verification checks.
- Designed chat persistence layer supporting sessions, message turns, and LLM-ready history formatting.
- Added structured logging and async pytest coverage for all compliance flows including edge cases and failure scenarios.

### What I Learned
- How to structure compliance systems cleanly using repository-service separation for maintainability and auditability.
- Why deletion order matters in distributed systems (OpenSearch vs PostgreSQL consistency risks).
- How to safely design “right-to-erasure” flows with verification steps before final commit.
- Practical async SQLAlchemy behavior in real workflows (flush vs commit, delete semantics).
- How to design chat history formats that are directly compatible with LLM APIs without transformation overhead.

### What broke and how I fixed it
- Async pytest fixtures were not recognized by default → fixed by switching to pytest_asyncio.fixture and enabling async mode.
- Delete operations in tests initially appeared inconsistent due to missing commits → fixed by explicitly committing/rolling back in test flow.
- OpenSearch dependency in erasure service made unit testing fragile → solved by mocking async client with AsyncMock.
- Ordering issues in chat message retrieval → ensured explicit ORDER BY created_at for deterministic tests.
- Session handling edge cases (missing/invalid session_id) → handled via fallback logic in get_or_create_session.

### What I would do differently
- Introduce transaction boundary abstraction so tests don’t need manual commit/rollback handling.
- Add stronger integration tests with a real OpenSearch test container instead of full mocking.
- Centralize test fixtures for DB state builders to reduce repetitive setup across compliance tests.
- Add structured schemas (Pydantic) for service inputs to avoid implicit dict contracts.
- Extend erasure flow with observability hooks (metrics + tracing) to verify DSGVO compliance in production runs.

## Langfuse and Azure Deployment

### What I built

- Containerized the RAG application using Docker and deployed it to Azure Container Apps through Azure Container Registry (ACR).
- Integrated Neon PostgreSQL for relational persistence, AWS OpenSearch Serverless for vector retrieval, and Langfuse for observability/tracing with user and session tracking.
- Added Langfuse instrumentation across retrieval, generation, and compliance workflows to capture traces, spans, latency, token usage, and session-level debugging.
- Built GitHub Actions CI/CD pipeline for automated Docker build, image push to ACR, and Azure deployment.
- Implemented startup resilience and optional dependency handling so the API can boot even when observability or external services are temporarily unavailable.

### What I Learned

- The difference between ARM and AMD64 container builds and why Azure Container Apps commonly require explicit AMD64-compatible images.
- How AWS IAM-based authentication works for OpenSearch Serverless compared to standard username/password OpenSearch clusters.
- Tradeoffs between Neon and Supabase free tiers, especially around cold starts, connection limits, and operational simplicity.
- How to design graceful startup behavior for optional infrastructure dependencies like Langfuse or OpenSearch.
- Differences in secrets management between GitHub Actions secrets and Azure Container Apps environment variable configuration.

### What broke and how I fixed it

- Docker image failed on Azure due to ARM/AMD64 mismatch from local Mac build → fixed using explicit --platform linux/amd64 builds.
- Azure PostgreSQL deployment initially failed because the PostgreSQL resource namespace was not registered -> resolved by manually registering the provider in Azure subscription settings.
- Neon PostgreSQL intermittently returned connection refused during cold starts -> fixed with retry logic and startup connection backoff.
- OpenSearch Serverless authentication failed due to incorrect AWS credential/signature configuration -> fixed by switching to SigV4-compatible IAM authentication flow.
- SQLAlchemy async setup failed in Linux container because greenlet wheel dependency was missing -> fixed by explicitly adding greenlet to requirements.

### What I would do differently

- Move all infrastructure provisioning to Terraform or Bicep instead of manual Azure setup steps.
- Add centralized secret management using Azure Key Vault instead of relying only on environment variables.
- Use managed identity or workload identity federation instead of long-lived AWS access keys inside Azure deployments.
- Add distributed tracing correlation between Langfuse traces, application logs, and infrastructure metrics.
- Introduce staged deployment environments (dev/staging/prod) with automated rollback support in CI/CD.

## pgvector Migration & Sentence Aware chunking

### What I built

- Migrated the retrieval layer from AWS OpenSearch Serverless to pgvector on Neon PostgreSQL with hybrid BM25 + semantic retrieval using tsvector, pgvector embeddings, HNSW indexing, and Reciprocal Rank Fusion (RRF).
- Integrated Docling into production Docker deployment including required Linux system libraries and startup warmup to reduce first-request latency.
- Reworked chunking pipeline from fixed sliding windows to sentence-aware chunking using NLTK (300-word chunks with 2-sentence overlap) for better semantic continuity.
- Integrated Cohere reranker encoder model to rank chunks before LLM generation, improving overall RAGAS score from 0.604 in baseline to 0.772 
- Added asynchronous PDF ingestion using FastAPI BackgroundTasks and built a multipart upload endpoint (POST /ingestion/upload) to avoid request timeouts on large documents.
- Built a lightweight Gradio UI with ingestion, query, and audit-trail tabs and expanded automated coverage to 84 passing tests.

### What I Learned

- AWS OpenSearch Serverless pricing can become unexpectedly expensive because compute units stay active even during low traffic or idle periods.
- pgvector on Neon is operationally simpler and architecturally cleaner for DSGVO-focused systems since both relational and vector data stay inside one EU-hosted database.
- Sentence-aware chunking performs better for retrieval quality than naive fixed-size sliding windows, especially for regulatory PDFs with long contextual sections.
- FastAPI BackgroundTasks is useful for lightweight async ingestion workflows, but it is still process-bound and not a true distributed job queue.
- RAG evaluation metrics can regress after infrastructure migration even when architecture becomes cleaner, making systematic benchmarking essential.

### What broke and how I fixed it

- AWS OpenSearch Serverless SEARCH collections did not support KNN vector search → migrated to VectorSearch collections, then fully replaced the stack with pgvector after free-tier cost exhaustion.
- Background ingestion initially failed with foreign key violations → fixed by ensuring document metadata records are inserted before chunk persistence.
- CI pipeline failed with asyncio event loop issues → replaced asyncio.get_event_loop() usage with asyncio.run() for compatibility in isolated test environments.
- NLTK punkt_tab downloads failed on macOS because of SSL certificate validation → fixed using certifi certificate configuration.
- Azure Container Apps timed out during Docling cold ingestion → solved through startup warmup and asynchronous background ingestion execution.

### What I would do differently

- Start with pgvector from the beginning instead of introducing OpenSearch Serverless complexity and cost overhead.
- Design ingestion as a proper async job architecture early using Redis/Celery or Azure Service Bus instead of relying on in-process background tasks.
- Add ingestion status tracking endpoints and persistent job metadata for frontend polling and operational visibility.
- Benchmark retrieval quality continuously during infrastructure migrations instead of evaluating only after major architectural changes.
- Add automated retrieval quality regression tests alongside unit and integration tests to catch semantic search degradation earlier.