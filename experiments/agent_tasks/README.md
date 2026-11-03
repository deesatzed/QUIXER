# Isolated paired agent-study fixture

This is an orchestration fixture, not an agent evaluation. It schedules the same tasks in four seeded, shuffled conditions, passes no condition name or other output to the agent, enforces a serialized-request character cap, and retains failures and unknown costs. Both context and output in `run.py` are synthetic; no QUIX retrieval, HITMCockpit agent, external service or MindStore is involved.

From the repository root: `PYTHONPATH=src python experiments/agent_tasks/run.py .local/agent-fixture.json`. The destination must not exist. The character cap is not a token budget and the callable injection layer does not itself enforce process timeouts, prevent a malicious callable from sharing state, verify source citations, or connect the real Swift adapter. Do not interpret fixture outputs as actual agent performance.

An actual comparison still needs a source-validated context adapter for each condition, isolated real-agent invocations with enforced timeout and equivalent full request budgets, captured provider usage and failure results, an output-blind review packet, and independent outcome review. The existing HITMCockpit `PlannerAgent` accepts an intent, not a separate QUIX packet, so an adapter must be designed and validated before claiming that path was exercised. Live swarm and MindStore integration remain outside the approved slice.
