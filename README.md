# QUIX Knowledge — experimental prototype

An early local SQLite catalog for exploring evidence-linked retrieval by software agents. This is a research prototype, not a validated swarm knowledge service.

## Try it

From this checkout, set `PYTHONPATH=src`, then run:

```sh
python -m quix_knowledge --db /tmp/quix-example.db ingest docs/plans/2026-10-29-shared-knowledge-design.md
python -m quix_knowledge --db /tmp/quix-example.db search 'role retrieval'
python -m pytest tests/ -q
```

Markdown headings become line-anchored sections; unheaded text receives a generated fallback section. PDF ingestion requires the optional `pdf` dependency (`pip install -e '.[pdf]'`). Embedded PDF bookmarks define page-granularity sections; without bookmarks, each page becomes a generated fallback section. Pages with no extractable text are reported, and OCR is not performed. Source revisions are retained. Python APIs can add findings, evidence links, topic assignments and role annotations. Search includes current sections and proposed/current agent records, labels unsupported claims, and can apply topic and role adjustments. Decision providers can be passed to the Python search API; returned judgments are recorded and bounded adjustments are experimental. Missing or invalid judgments do not remove results.

The `index` command creates provisional topic links from existing headings. Optionally it assesses structure and a bounded number of topic candidates with a decision model; source text remains searchable when a model is uncertain or unavailable. Model-assessed links are still proposals, and a plain-text fallback is not a generated semantic table of contents. The result's `decision_calls` reports actual attempted calls. For example:

```sh
python -m quix_knowledge --db /tmp/quix-example.db index docs/plans/2026-10-29-shared-knowledge-design.md --env-file /Volumes/WS4TB/QUIX/.env --model-slot 2 --max-decisions 2
```

The optional search `--context-chars` bounds returned body text by characters, not tokens; source metadata and model input are separate from that output budget. Agent findings report `evidence_status` as current, stale or unsupported; linked evidence does not prove the finding is true.

## Current limitations

OpenRouter can be used explicitly for a decision search, using a configured model slot and `.env` file. This sends candidate text to OpenRouter and incurs API charges:

```sh
python -m quix_knowledge --db /tmp/quix-example.db search 'role retrieval' --variant decision --env-file /Volumes/WS4TB/QUIX/.env --model-slot 2
```

Returned model probabilities are recorded but remain provisional: the adapter does not apply unvalidated thresholds. Model failures result in unknown judgments and preserve the original candidates.

There is no OCR, production orchestration integration, semantic or BM25 search, context-token budget, independently labeled benchmark, model calibration, concurrency control or production readiness claim. PDF bookmarks can be incomplete and same-page entries are combined; page anchors do not identify exact passage boundaries. The current evaluator is not the planned complete run-manifest framework. Structure judgments are recorded rather than used to delete source content, and topic links remain proposed pending acceptance. Role annotations and topic links can be added through Python, not the CLI. Do not interpret synthetic tests as a quality evaluation. See [progress](PROGRESS.md), [evaluation](docs/evaluation.md), and the [plan](docs/plans/2026-10-29-shared-knowledge-implementation.md).
