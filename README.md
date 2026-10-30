# QUIX Knowledge — experimental prototype

An early local SQLite catalog for exploring evidence-linked retrieval by software agents. This is a research prototype, not a validated swarm knowledge service.

## Try it

From this checkout, set `PYTHONPATH=src`, then run:

```sh
python -m quix_knowledge --db /tmp/quix-example.db ingest docs/plans/2026-10-29-shared-knowledge-design.md
python -m quix_knowledge --db /tmp/quix-example.db search 'role retrieval'
python -m pytest tests/ -q
```

Markdown headings become line-anchored sections; unheaded text receives a generated fallback section. Source revisions are retained. Python APIs can add findings, evidence links, topic assignments and role annotations. Search includes current sections and proposed/current agent records, labels unsupported claims, and can apply topic and role adjustments. Decision providers can be passed to the Python search API; returned judgments are recorded and bounded adjustments are experimental. Missing or invalid judgments do not remove results.

## Current limitations

OpenRouter can be used explicitly for a decision search, using a configured model slot and `.env` file. This sends candidate text to OpenRouter and incurs API charges:

```sh
python -m quix_knowledge --db /tmp/quix-example.db search 'role retrieval' --variant decision --env-file /Volumes/WS4TB/QUIX/.env --model-slot 2
```

Returned model probabilities are recorded but remain provisional: the adapter does not apply unvalidated thresholds. Model failures result in unknown judgments and preserve the original candidates.

There is no PDF adapter, production orchestration integration, semantic or BM25 search, context-token budget, independently labeled benchmark, model calibration, concurrency control or production readiness claim. The current evaluator is not the planned complete run-manifest framework. Decision calls can assess a proposed topic link, but do not control ingestion; supported links remain proposed pending acceptance. Role annotations and topic links can be added through Python, not the CLI. Do not interpret synthetic tests as a quality evaluation. See [progress](PROGRESS.md), [evaluation](docs/evaluation.md), and the [plan](docs/plans/2026-10-29-shared-knowledge-implementation.md).
