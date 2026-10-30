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

The `index` command creates provisional topic links from existing headings. For unheaded fallback sections and sections containing multiple paragraphs or long passages, it also proposes paragraph-level entries with extractive titles, exact offsets into the source section and an explicit provisional status. These are candidate navigation aids, not verified semantic headings. Optionally it assesses structure and a bounded number of topic candidates with a decision model; source text remains searchable when a model is uncertain or unavailable. Model-assessed links remain proposals. The result's `decision_calls` reports actual attempted calls. For example:

```sh
python -m quix_knowledge --db /tmp/quix-example.db index docs/plans/2026-10-29-shared-knowledge-design.md --env-file /Volumes/WS4TB/QUIX/.env --model-slot 2 --max-decisions 2
```

Inspect generated candidates with `list-index` and record an explicit named review with `review-index ENTRY_ID accepted --reviewer NAME` (or `rejected`). Provisional entries can be included experimentally in topic, decision or role searches with `--include-proposed`; accepted entries are available to those variants by default. Source changes mark dependent entries stale.

The optional search `--context-chars` bounds returned body text by characters. Alternatively, install the `tokens` extra and use `--context-tokens N --tokenizer cl100k_base` to bound each returned body's token count with the named `tiktoken` encoding. The sum is for body text only: titles, metadata, message framing and model-input tokens are excluded, and a named encoding may not match the agent's actual tokenizer. Agent findings report `evidence_status` as current, stale or unsupported; linked evidence does not prove the finding is true.

To request a role-usefulness estimate for a section ID returned by search, use `assess-role SECTION_ID --role reviewer --role-version 1 --role-purpose 'Review implementation evidence' --env-file /Volumes/WS4TB/QUIX/.env --model-slot 2`. It records the source revision, role definition and model receipt; the score is a proposed estimate, not calibrated utility. An error records an unknown result and does not invent a score. Increment the role version when its purpose changes.

## Current limitations

OpenRouter can be used explicitly for a decision search, using a configured model slot and `.env` file. This sends candidate text to OpenRouter and incurs API charges:

```sh
python -m quix_knowledge --db /tmp/quix-example.db search 'role retrieval' --variant decision --env-file /Volumes/WS4TB/QUIX/.env --model-slot 2
```

Returned model probabilities are recorded but remain provisional: the adapter does not apply unvalidated thresholds. Model failures result in unknown judgments and preserve the original candidates.

An independently running JevEdge0 workbench can be selected with `--jev-url http://127.0.0.1:8090 --stability-trials 2` instead of the OpenRouter settings. The adapter accepts only loopback HTTP and preserves conditional option scores and permutation-stability information; those scores are not calibrated accuracy. The workbench and model weights are separate prerequisites, and have not been tested live in this checkout.

There is no OCR, production orchestration integration, semantic or BM25 search, complete request token budget, independently labeled benchmark, model calibration, concurrency control or production readiness claim. PDF bookmarks can be incomplete and same-page entries are combined; page anchors do not identify exact passage boundaries. The current evaluator is not the planned complete run-manifest framework. When a decision is uncertain or fails, retrieval falls back to the ungated baseline and identifies the fallback. Structure judgments are recorded rather than used to delete source content, and topic links remain proposed pending acceptance. Ordinary heading topic links can be added through Python, not the CLI. Do not interpret synthetic tests as a quality evaluation. See [progress](PROGRESS.md), [evaluation](docs/evaluation.md), and the [plan](docs/plans/2026-10-29-shared-knowledge-implementation.md).

When exact lexical search yields no results, the retriever also tries a conservative singular/plural normalization and labels that fallback. This is not semantic search and may still miss relevant evidence.
