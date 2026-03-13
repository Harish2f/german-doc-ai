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