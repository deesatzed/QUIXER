# Evaluation and review packet

This is an evaluation plan and an unreviewed draft, not a benchmark result. The first corpus is the design and implementation plan in this repository at a recorded Git commit. Section IDs depend on the absolute source path and source revision; resolve anchors against the actual ingested revision, do not copy IDs between machines.

## Draft tasks

| Task | Role | Candidate evidence to review | Status |
| --- | --- | --- | --- |
| Implement a source-linked fallback when a document has no headings. | Implementer | Design: Ingestion and indexing; plan: Task 2 | Unreviewed |
| Check how an agent finding should identify its supporting source. | Reviewer | Design: Records and metadata; plan: Task 3 | Unreviewed |
| Handle a decision-model timeout without suppressing source evidence. | Implementer | Design: Retrieval and failure handling; plan: Task 5 | Unreviewed |
| Assess whether role usefulness may hide an otherwise relevant section. | Reviewer | Design: Architecture; plan: Task 4 | Unreviewed |
| Determine whether provider scores have already been validated as task accuracy. | Reviewer | Design: Retrieval and failure handling; provider evaluation | Unreviewed |

An independent reviewer should inspect the exact source revision without seeing system rankings, mark all relevant anchors and any missing evidence, and sign off on labels. Divide tasks before choosing thresholds. A task with no verified labels is **unlabeled**, not unanswerable. Explicitly label unanswerable only when the corpus has been inspected and lacks sufficient evidence.

Run baseline, topic, decision and role variants on the same revision, tasks and retrieval budgets. Preserve per-task results and metadata: corpus digest, query and role definition, chosen model and resolved version, prompt version, returned score, failures, token usage, reported cost, elapsed time, and configuration. Report answerable recall, relevance and stale/unsupported material, plus cost and latency. Compare decision model outputs and operational thresholds using held-out labels; a model's own probability does not establish accuracy.

The `experiment` command now runs all four variants against a fingerprinted SQLite catalog with common per-query result and character budgets, recording query results, timings and actual decision receipts. For example, after indexing the corpus, run:

```sh
python -m quix_knowledge --db /tmp/quix-example.db experiment examples/project_tasks_unreviewed.json --context-chars 1500 --limit 3 --env-file /Volumes/WS4TB/QUIX/.env --model-slot 2
```

It prints a JSON report; redirect it to a suitable local file if desired. The corpus fingerprint currently includes local source paths, so it identifies the actual catalog snapshot rather than being portable across checkouts. `labels: null` means not reviewed. A `labels: []` means explicitly unanswerable; do not use it for missing labels. Precision and recall assume provided labels are exhaustive, which must be established by independent review. Token budgeting, prompt versioning, full missing-source and indexing cost accounting, and independently reviewed labels remain open.

The [unlabeled project smoke run](../reports/2026-10-30-unlabeled-project-smoke.json) exercises five draft tasks on two project documents. The report omits source text, local paths and request IDs. Its topic links were provisional and no role annotations were present, so topic and role variants do not test those features. All labels were absent; recall and precision are not measured. Its timings and costs are observations from this one run, not performance benchmarks.

If running agents on these tasks, preserve their actual outputs and have an independent reviewer assess the outcomes separately from retrieval. Do not call synthetic tests or model responses evidence of improved swarm performance.
