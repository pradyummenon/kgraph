# CLAUDE.md

## identity

you are working on a project authored by pradyum.
all code, commits, and documentation are attributed to pradyum.
never mention claude, ai, llm, or any ai tool as author or contributor.
derive git author identity from the git config of this repository.

## core philosophy

this codebase prioritizes:
1. clean architecture over speed — every abstraction must earn its place
2. small, reviewable changes — never touch more than 10-15 files per commit
3. learning-first — every feature should teach something worth writing about
4. production-grade patterns — even for learning projects, write code you'd ship

## design principles (always enforced)

follow these in every file, every function, every class:
- SOLID principles (single responsibility is non-negotiable)
- GRASP patterns (information expert, creator, controller, low coupling, high cohesion)
- dependency injection over hard-coded dependencies
- composition over inheritance
- program to interfaces, not implementations
- fail fast, fail loud — no silent swallowing of exceptions
- guard clauses over nested conditionals
- meaningful names that reveal intent — no abbreviations unless universally understood

refer to `.claude/skills/design-principles.md` for detailed examples.

## git discipline

### commits
- format: `<type>(<scope>): <description>`
- types: feat, fix, refactor, docs, test, chore, perf
- all lowercase, no period at end
- max 72 chars for subject line
- present tense, imperative mood: "add feature" not "added feature"
- examples:
  - `feat(auth): add jwt token refresh mechanism`
  - `refactor(graph): extract traversal logic into strategy pattern`
  - `docs(concepts): add knowledge graph query optimization notes`

### branches
- format: `<type>/<short-description>`
- examples: `feat/jwt-refresh`, `refactor/graph-traversal`, `docs/core-concepts`
- always branch from main, always PR back to main

### pull requests
- title matches commit convention
- description explains WHY not just WHAT
- max 10-15 files changed
- if a feature needs more files, split into stacked PRs
- link to relevant ADR if architectural decision was made

### secrets & config
- never commit secrets, tokens, api keys, passwords
- use environment variables or .env files (always in .gitignore)
- provide .env.example with placeholder values
- abstract all external service configs behind a config module

## documentation requirements

every project must have:
1. `README.md` — what it is, why it exists, how to run it
2. `docs/architecture/` — at least one ADR explaining the core design
3. `docs/concepts/` — deep-dive on the hardest concept in this project
4. `docs/diagrams/` — at least one high-level architecture diagram (mermaid)

## language-specific rules

- python projects → follow `.claude/skills/python.md`
- java projects → follow `.claude/skills/java.md`

## workflow

when starting a new feature:
1. create a feature branch
2. implement in small commits (each commit should compile/pass tests)
3. run the architect-reviewer agent before creating PR
4. generate/update documentation
5. generate architecture diagram if design changed
6. update learning journal

## sub-agents (invoke as needed)

- **architect review**: `.claude/agents/architect-reviewer.md` — run before any PR
- **documentation**: `.claude/agents/doc-writer.md` — generate docs after feature complete
- **diagrams**: `.claude/agents/diagram-gen.md` — create/update architecture visuals
- **content**: `.claude/agents/content-creator.md` — convert learnings to twitter content
