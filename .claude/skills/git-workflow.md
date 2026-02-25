# git workflow standards

## branching model
- `main` — always deployable, always clean
- `feat/<name>` — new features
- `fix/<name>` — bug fixes
- `refactor/<name>` — structural improvements
- `docs/<name>` — documentation only
- `chore/<name>` — tooling, config, dependencies

## commit message format

```
<type>(<scope>): <subject>

<body — optional, wrap at 72 chars>

<footer — optional, references>
```

### types
feat, fix, refactor, docs, test, chore, perf, style, ci

### rules
- all lowercase
- no period at end of subject
- imperative mood: "add" not "adds" or "added"
- subject max 72 characters
- body explains WHY, not WHAT (the diff shows what)
- reference issue numbers in footer if applicable

### examples
```
feat(diagnostics): add multi-hop graph traversal for differential diagnosis

implement breadth-first traversal with weighted edges to rank
candidate diagnoses by symptom match score. uses cypher path
expansion with APOC for performance.

relates-to: #42
```

```
refactor(api): extract http client into injectable service

reduces coupling between use cases and transport layer.
enables testing without network calls.
```

## PR standards

### title
same format as commit message subject line.

### description template
```
## what
brief description of the change.

## why
what problem does this solve? link to ADR if relevant.

## how
high-level approach. mention any patterns or trade-offs.

## testing
how was this verified?

## files changed
quick summary of what changed where (helps reviewers navigate).
```

### size limits
- target: 5-10 files
- max: 15 files
- if more needed: split into stacked PRs with clear dependency order

## .gitignore essentials
```
.env
*.pyc
__pycache__/
.mypy_cache/
.pytest_cache/
.ruff_cache/
build/
dist/
*.egg-info/
.idea/
.vscode/
*.iml
target/
.gradle/
node_modules/
```
