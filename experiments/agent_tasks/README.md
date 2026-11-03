# Isolated paired agent-study fixture

This is an orchestration fixture, not an agent evaluation. It schedules the same tasks in four seeded, shuffled conditions, passes no condition name or other output to the agent, enforces a serialized-request character cap, and retains failures and unknown costs. Both context and output in `run.py` are synthetic; no QUIX retrieval, HITMCockpit agent, external service or MindStore is involved.

From the repository root: `PYTHONPATH=src python experiments/agent_tasks/run.py .local/agent-fixture.json`. The destination must not exist. The character cap is not a token budget and the callable injection layer does not itself enforce process timeouts, prevent a malicious callable from sharing state, verify source citations, or connect the real Swift adapter. Do not interpret fixture outputs as actual agent performance.

An exploratory real-agent path is available with the separate, isolated HITMCockpit worktree at `quix-read-adapter`: build its `QuixPlannerStudyCLI`, then run:

```sh
PYTHONPATH=src python experiments/agent_tasks/run_live.py .local/retrieval-study-v1 .local/new-agent-run --planner /private/tmp/hitm-quix-swift-build/out/Products/Debug/QuixPlannerStudyCLI --model openai/gpt-4o-mini
```

The destination must be new. This makes OpenRouter calls for switch navigation and the text planner using the authorized `.env`, and saves raw source packets, retrieval traces, outputs and receipts locally. The text model is an explicit experimental choice; the `.env` configures decision models, not an agent model. The Swift bridge requires exact task and role matching, rechecks source hashes before use, preserves source anchors, and rejects an intent above the planner's 2,000-Unicode-scalar limit. The experiment takes one result and caps its body at 300 characters; this is not full-prompt token matching. Each planner invocation is a separate process with a 60-second parent timeout, no tools, and no previous output. Returned costs can be unknown. On timeout, calls may already have occurred and their cost is unknown. Role annotations in the prepared study are absent, so the role condition cannot measure the effect of role scores. Switch may fall back to baseline; inspect the recorded retrieval report. This is an isolated planning comparison, not live swarm or MindStore integration.

An output-blind review packet and an actual independent outcome review remain necessary to judge correctness, source support, missing evidence and task completion. Even a reviewed five-task exploratory run cannot establish a swarm benefit.
