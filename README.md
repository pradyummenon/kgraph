# kgraph

> CLI tool for building and querying knowledge graphs from documents.

## why this exists

there's no mature, CLI-first tool that does the full pipeline of "ingest any document → extract
entities/relationships via LLM → store in Neo4j → query via natural language" as a single
cohesive experience. kgraph fills that gap with a graphiti-like architecture (smart retrieval,
no LLM at query time) and a graphrag-like CLI UX (`init/ingest/query` commands).

## key concepts

- **hybrid retrieval** — vector search + graph traversal, no LLM at retrieval time ([deep dive](docs/architecture/001-hybrid-retrieval-over-community-summarization.md))
- **structured extraction** — claude tool use for guaranteed-schema entity/relationship extraction
- **graph expansion** — 2-hop neighborhood traversal to capture relational context

## architecture

```
┌─────────────────────────────────────────────┐
│                  kgraph CLI                  │
│              (Typer + Rich)                  │
├──────────┬──────────┬───────────┬───────────┤
│  init    │  ingest  │  query    │  explore  │
└──────────┴────┬─────┴─────┬─────┴───────────┘
                │           │
        ┌───────▼───────┐   │
        │  Extractor    │   │
        │  (Claude API  │   │
        │   structured  │   │
        │   output)     │   │
        └───────┬───────┘   │
                │           │
        ┌───────▼───────────▼─────┐
        │      Neo4j Graph DB     │
        │  - Entity nodes         │
        │  - Relationship edges   │
        │  - Vector index (HNSW)  │
        │  - Full-text index      │
        └─────────────────────────┘
```

see [full architecture docs](docs/architecture/) for ADRs and detailed diagrams.

## getting started

```bash
# clone
git clone https://github.com/pradyummenon/kgraph.git
cd kgraph

# install
make install

# start neo4j (docker)
docker run -d --name kgraph-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/kgraph-password \
  -e NEO4J_PLUGINS='["apoc", "graph-data-science"]' \
  -v kgraph-data:/data \
  neo4j:5-community

# configure
kgraph init

# ingest documents
kgraph ingest ./my-docs/

# query
kgraph query "what is X related to?"

# explore an entity
kgraph explore "Entity Name"
```

## project structure

```
kgraph/
├── pyproject.toml              # dependencies + build config
├── src/kgraph/
│   ├── cli.py                  # typer CLI commands (init, ingest, query, explore, stats)
│   ├── config.py               # config management (~/.kgraph/config.toml)
│   ├── domain/
│   │   ├── models.py           # entity, relationship, chunk domain models
│   │   └── services.py         # deduplication, protocols for DI
│   ├── infrastructure/
│   │   ├── chunker.py          # document reading + text splitting
│   │   ├── extractor.py        # claude-based entity/relationship extraction
│   │   ├── embedder.py         # openai + local embedding generation
│   │   ├── graph.py            # neo4j driver (indexes, ingestion, retrieval)
│   │   └── retriever.py        # hybrid retrieval (vector + graph expansion)
│   └── application/
│       └── use_cases.py        # CLI command orchestration
├── tests/
├── docs/
│   ├── architecture/           # ADRs
│   ├── concepts/               # deep-dives
│   └── diagrams/               # mermaid diagrams
├── .claude/                    # claude code harness
└── .github/                    # PR template
```

## tech stack

| technology | why |
|-----------|-----|
| python 3.12+ | type hints, match statements, tomllib |
| typer + rich | modern CLI with beautiful terminal output |
| anthropic (claude) | structured output for entity extraction + answer generation |
| neo4j | graph DB with vector index (HNSW), full-text index, APOC |
| openai embeddings | text-embedding-3-small, cheap and effective |
| pydantic | strict data models for domain objects |
| uv | fast, modern python package management |

## what i learned

- hybrid retrieval (vector + graph traversal) captures relational context that pure vector search misses entirely
- claude structured output via tool use is the most reliable way to enforce extraction schemas
- neo4j's native vector index means you don't need a separate vector DB
- skipping community summarization (graphrag's biggest cost) makes the pipeline 100x cheaper
- clean architecture with dependency injection makes it trivial to swap embedders (openai ↔ local)

## license

MIT
