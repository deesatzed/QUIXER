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

It prints a JSON report; redirect it to a suitable local file if desired. The corpus fingerprint currently includes local source paths, so it identifies the actual catalog snapshot rather than being portable across checkouts. `labels: null` means not reviewed. A `labels: []` means explicitly unanswerable; do not use it for missing labels. Precision and recall assume provided labels are exhaustive, which must be established by independent review. Generated-index IDs and parent section IDs are distinct: exact-ID scoring does not treat a hit on an arbitrary paragraph as a hit for its parent, so reviewers must label units at the evaluated granularity. The runner supports a named tokenizer budget for returned body text; it excludes metadata, prompts and model input and may use a different encoding from the eventual agent.

The runner reports metrics separately for `train`, `development`, `held_out` and `unassigned` task splits, but it cannot prove that the partitions were created before tuning. It flags tasks whose labeled IDs are absent from the current catalog as `missing_source` and excludes those tasks from recall and precision; it does not misclassify them as retrieval failures. These metrics are exact record-ID candidate metrics: an ID match does not verify that a truncated body contains the evidence or that the agent used it.

For a matched **context-packet** budget instead of a body-only budget, use `--packet-tokens N --tokenizer NAME`. The packet includes task, role, fingerprint, result metadata and body text in the counted JSON representation, and records selected results omitted to fit. It does not include any downstream chat or tool wrapper, and the named encoding may not be the receiving model's encoding. Explicit experimental `--thresholds LOW HIGH` are recorded in the manifest; they are not calibrated merely because a run uses them. Do not tune thresholds on held-out labels.

The offline `calibrate SPEC.json` command replays explicitly supplied binary labels and candidate `(low, high)` thresholds without making model calls. Each row requires a unique case ID, `development` or `held_out` split, probability (or null), label (true, false or null), and identical model, prompt version and question identifiers. The spec must name label provenance, selection error limit, minimum development actions and the threshold grid. The selector uses only development results; it then reports held-out errors, unknowns, abstentions and coverage. Unstable option-order results are withheld; rows that require stability but lack it are unknown. Unique IDs do not establish that related examples are independent across splits. A provenance string does not establish independence, and a small sample's empirical error is not a confidence guarantee. This software has synthetic tests only; no validated policy is selected until independently reviewed cases and a suitable held-out study exist.

`index` reports elapsed time, receipt IDs, reported cost and input tokens when supplied by every decision response; missing usage stays unknown. Pass the receipt IDs as a JSON array through `experiment --indexing-receipts FILE` to include separately measured indexing calls in the manifest. Receipts must point to current sources in the same catalog. This does not measure local compute or unrecorded prior indexing activity. Prompt versioning, full missing-source accounting, and independently reviewed labels remain open.

The [unlabeled project smoke run](../reports/2026-10-30-unlabeled-project-smoke.json) exercises five draft tasks on two project documents. The report omits source text, local paths and request IDs. Its topic links were provisional and no role annotations were present, so topic and role variants do not test those features. All labels were absent; recall and precision are not measured. Its timings and costs are observations from this one run, not performance benchmarks.

An [unlabeled BM25 smoke](../reports/2026-10-30-bm25-unlabeled-smoke.json) runs the same five draft tasks and 400-token context-packet budget using both overlap and BM25 rankers. One baseline top result changed; without reviewed labels this is a difference in ordering, not evidence that either ranker is better. Candidate-ID metrics cannot by themselves establish that a truncated packet contains the needed passage.

The optional `hybrid` ranker uses the local JevEdge0 embedding implementation with an explicitly supplied local model, combined with BM25 by reciprocal-rank fusion. [One unlabeled local integration check](../reports/2026-10-30-hybrid-local-smoke.json) confirms the encoder/search path with a real checkpoint; it does not measure quality. Compare it against BM25 on the same independently reviewed tasks and packet budget before making a relative-quality claim. Encoder tokenizer truncation, model load time, repeated embedding computation and local hardware costs must be recorded separately.

A [five-task unlabeled comparison](../reports/2026-10-30-hybrid-unlabeled-comparison.json) uses the actual local encoder and the same 400-token packet budget for BM25 and hybrid. All five baseline top IDs changed; the record contains no relevance labels and does not establish which ordering is better. It does not measure local hardware energy or cost.

If running agents on these tasks, preserve their actual outputs and have an independent reviewer assess the outcomes separately from retrieval. Do not call synthetic tests or model responses evidence of improved swarm performance.
