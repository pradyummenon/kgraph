# python project standards

## version
- python 3.12+ (use latest stable features: type hints, match statements,
  tomllib, etc.)

## project structure
```
project-name/
├── pyproject.toml              # single source of truth for config
├── src/
│   └── project_name/
│       ├── __init__.py
│       ├── domain/             # business logic, entities, value objects
│       │   ├── __init__.py
│       │   ├── models.py
│       │   └── services.py
│       ├── infrastructure/     # external concerns (db, api clients, etc.)
│       │   ├── __init__.py
│       │   ├── repositories.py
│       │   └── clients.py
│       ├── application/        # use cases, orchestration
│       │   ├── __init__.py
│       │   └── use_cases.py
│       └── interfaces/         # entry points (cli, api, etc.)
│           ├── __init__.py
│           └── api.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── .env.example
├── .gitignore
└── Makefile                    # common commands
```

## tooling
- **package manager**: uv (preferred) or poetry
- **formatting**: ruff format
- **linting**: ruff check
- **type checking**: mypy (strict mode)
- **testing**: pytest with pytest-cov
- **pre-commit**: ruff + mypy hooks

## code style
- type hints on all function signatures (no `Any` unless truly necessary)
- dataclasses or pydantic for data structures (no raw dicts for domain objects)
- protocols over abstract base classes for dependency inversion
- context managers for resource management
- f-strings for formatting (no .format() or %)
- pathlib over os.path
- explicit is better than implicit — no clever tricks

## dependency injection pattern
```python
# good — dependencies are injected
class DiagnosticService:
    def __init__(self, graph_repo: GraphRepository, llm_client: LLMClient):
        self._graph = graph_repo
        self._llm = llm_client

# bad — dependencies are created internally
class DiagnosticService:
    def __init__(self):
        self._graph = Neo4jGraphRepository()  # hard coupling
```

## error handling
- custom exception hierarchy rooted in a project-level base exception
- never catch bare `Exception` unless re-raising
- use `logging` module, not print statements
- structured logging with context (use structlog if appropriate)

## Makefile targets (always include)
```makefile
.PHONY: install lint format test run

install:
	uv sync

lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff format src/ tests/

test:
	pytest tests/ -v --cov=src/

run:
	python -m project_name
```
