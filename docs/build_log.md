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