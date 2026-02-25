# ADR-001: Hybrid Retrieval Over Community Summarization

**date:** 2026-02-25
**status:** accepted
**project:** kgraph

## context

building a CLI tool that ingests documents into a knowledge graph and supports
natural language querying. the key architectural question is how to handle
retrieval — the step between "user asks a question" and "LLM generates an answer."

the dominant approaches in the space:
- **microsoft graphrag**: community summarization at ingestion time. expensive
  (610K+ tokens per global query). great for broad "summarize everything" questions.
- **graphiti**: hybrid retrieval with no LLM at query time. fast, efficient,
  67% better relevance than vector-only in benchmarks.
- **pure vector search (RAG)**: simple but misses relational context entirely.

## decision

use **hybrid retrieval**: vector search (HNSW on Neo4j) → graph expansion
(2-hop traversal) → assemble context → LLM for answer generation only.

no community summarization. no LLM at retrieval time. the LLM is used at
**ingestion** (entity extraction) and **answer generation** (final step).

## alternatives considered

### alternative 1: microsoft graphrag-style community summarization
- pros: excellent for global "summarize the whole corpus" queries
- cons: extremely expensive (tokens scale with corpus size), slow ingestion,
  requires periodic re-summarization as graph grows
- why rejected: a CLI tool needs to be fast and cheap. per-query costs of
  600K+ tokens are not viable for a learning project or personal tool.

### alternative 2: pure vector search (standard RAG)
- pros: simple to implement, well-understood, many libraries
- cons: completely misses relational context. "what is X related to?" fails
  because vector similarity doesn't capture graph structure.
- why rejected: the whole point of a knowledge graph is the relationships.
  ignoring them defeats the purpose.

### alternative 3: text2cypher (LLM generates cypher queries)
- pros: very flexible, can answer arbitrary graph questions
- cons: LLM at query time (latency + cost), cypher generation is unreliable,
  requires self-healing retry loops
- why rejected: too fragile for a primary retrieval mode. kept as an
  optional `--mode cypher` flag for power users.

## consequences

### positive
- fast retrieval (no LLM call at query time, just vector search + graph traversal)
- predictable costs (only 2 LLM calls per query: embedding + answer generation)
- captures relational context that pure vector search misses
- simple architecture — easy to understand and debug

### negative
- weaker at "summarize everything" global queries (no pre-computed summaries)
- embedding quality is a bottleneck — if embeddings are bad, vector search is bad
- 2-hop expansion can return noisy context for densely connected entities

### risks
- graph traversal performance may degrade with very large graphs (millions of nodes).
  mitigation: limit expansion to top-scored entities, cap context size.

## learning notes

the key insight from studying graphiti vs graphrag is that most practical questions
are "local" — they're about specific entities and their neighborhoods. you rarely
need a global summary of an entire corpus. by skipping community summarization,
we avoid the biggest cost center in the pipeline while still getting relational
context through graph expansion.
