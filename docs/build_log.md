# GermanDocAI Build Log

## Week 1 — Project Setup

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

## Week 2 — Pydantic Settings, Structured Logging, Async/Await


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