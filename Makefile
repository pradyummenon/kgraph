.PHONY: install lint format test run neo4j

install:
	uv sync

install-local:
	uv sync --extra local

install-dev:
	uv sync --extra dev

lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff format src/ tests/

test:
	pytest tests/ -v --cov=src/

run:
	kgraph --help

neo4j:
	docker run -d --name kgraph-neo4j \
		-p 7474:7474 -p 7687:7687 \
		-e NEO4J_AUTH=neo4j/kgraph-password \
		-e NEO4J_PLUGINS='["apoc", "graph-data-science"]' \
		-v kgraph-data:/data \
		neo4j:5-community

neo4j-stop:
	docker stop kgraph-neo4j && docker rm kgraph-neo4j
