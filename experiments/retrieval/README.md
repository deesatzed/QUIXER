# Prospective retrieval comparison

`manifest.json` freezes 16 unlabeled tasks, eight development and eight held out, across three project documents and explicitly synthetic fixtures. The sources share documents across splits and the project has already been explored; the split is not independent by construction. The fixtures include invented conflicting, stale and unsupported agent findings. They are not observations of a live swarm.

The common candidate scope is current sections and agent records; generated-index passages are excluded. All variants use a 2,000-token `cl100k_base` serialized context-packet budget, but switch consumes additional model input and calls, so the complete model budgets are not matched. Exact-ID matches do not establish that a truncated packet contains the answer. The prepared catalog has no role annotations, so this study cannot measure role-score benefit.

With Python dependencies, Node and the switch experiment dependencies installed, run from the repository root:

```sh
PYTHONPATH=src python experiments/retrieval/prepare.py .local/my-study
PYTHONPATH=src python experiments/retrieval/run.py .local/my-study .local/my-fixture-run --mode fixture
PYTHONPATH=src python experiments/retrieval/run.py .local/my-study .local/my-live-run --mode openrouter --env-file /Volumes/WS4TB/QUIX/.env --model-slot 2
```

Each output directory must be new. Runs use a catalog copy and leave the review packet and prepared catalog intact. Fixture mode exercises the wiring with a deterministic fake selector, not a model. Live mode incurs OpenRouter calls; results, receipts and source text remain in the ignored output directory. Missing usage is unknown. The runner checks source revisions, frozen tasks and candidate material before executing.

For relevance evaluation, an independent reviewer should inspect `blind-review-packet.json` and its source candidates without seeing rankings, fill `reviewer`, and set each task's `reviewed`, `labels`, and, when the corpus cannot answer a task, `missing_reason`. A null label means unreviewed; an empty list with a reason means reviewed and unanswerable. Keep the packet with its prepared catalog. Run again into a new output directory with `--reviewed PATH`. The reviewer identity and independence are self-reported, not authenticated; labels must be exhaustive for exact-ID precision and recall to be meaningful. Do not select thresholds using held-out tasks or retrofit role annotations after preparing the packet: a new catalog requires a new packet and review.
