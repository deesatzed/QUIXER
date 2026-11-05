# Isolated model-cascade experiment

This research path compares source-checked baseline, Reflex, Cohere rerank and combined context selection. It may escalate a combined task to `tencent/hy4` when navigation or reranking is unavailable or a task explicitly requests synthesis. It returns proposals and receipts and does not dispatch agents or write MindStore. A decision score is not an operating threshold, and failed/unsupported results remain explicit.

From the project root, with the existing prepared isolated study, the separate HITMCockpit `QuixPlannerStudyCLI` built and the authorized `.env` in place:

```sh
PYTHONPATH=src python experiments/cascade/run_pilot.py .local/retrieval-study-isolated-v1 .local/NEW-CASCADE-RUN --planner /private/tmp/hitm-quix-swift-build/out/Products/Debug/QuixPlannerStudyCLI
PYTHONPATH=src python experiments/cascade/review_pilot.py .local/NEW-CASCADE-RUN .local/retrieval-study-isolated-v1 .local/NEW-CASCADE-RUN/ai-review
PYTHONPATH=src python experiments/cascade/analyze_pilot.py .local/NEW-CASCADE-RUN .local/retrieval-study-isolated-v1 .local/NEW-CASCADE-RUN/ai-review .local/NEW-CASCADE-RUN/analysis.json
```

Every destination must be new. Calls cost money; the four-task manifest schedules 16 planner attempts, four rerank requests, bounded Reflex calls and a separate AI review. Raw data, source excerpts, local paths, outputs and receipts stay under `.local`. On incomplete/uncertain AI reviews, use a new output directory with `review_pilot.py ... --retry PREVIOUS_REVIEW`, then pass `--retry RETRY_DIRECTORY` to `analyze_pilot.py`. Original failed attempts and their costs remain separate. The reviewer sees no condition mapping; the contents of answers may still disclose clues.

`probe_ingestion_search.py` separately sends a small fixture to Clairic and compares Cohere query/document embeddings with BM25 on the same four questions. It uses a fixed local destination and does not cache document embeddings. It tests an adapter and exploratory ordering, not production quality or cost. Its text inputs and model outputs are non-sensitive research copies.

The November 4 v2 pilot used a five-step switch budget, source packet limit three, and 100 characters per body. It ran before the latest study-request and stage/packet/schedule hashes were added; those fields are not retroactively claimed. Two attempts were rejected for stale or unsupported selected evidence; AI review remained unknown for one completed plan. The user-selected Hy4 model needed `reasoning.enabled=false` to return a bounded proposal; the isolated HITMCockpit CLI applies that setting only to the exact `tencent/hy4` slug. The initial failed and subsequent adjusted runs used different binaries and are not pooled. The full source corpus had already been explored, and AI labels do not establish independent accuracy. See `reports/2026-11-05-cascade-pilot.json` for costs and results.
