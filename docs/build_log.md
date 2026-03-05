# GermanDocAI Build Log

## Week 1 — Project Setup

### Date: 2026-03-05

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

