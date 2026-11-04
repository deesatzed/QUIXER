# Decision provider research checkpoint

Checked 2026-10-29. These are provider-listed specifications, not measured performance on QUIX tasks; prices and availability can change.

| Candidate | Provider-listed input price per million tokens | Listed context | Notes |
| --- | ---: | ---: | --- |
| [Perplexity Decider V1.2](https://openrouter.ai/perplexity/pplx-decider-v1.2/) | $0.02 | 262,144 | Typed choice, yes/no and score; listed choice limit 255. |
| [TypeSafe Jev 1.14](https://openrouter.ai/typesafe/jev-1.14/) | $0.042 | 262,144 | Typed decision model. |
| JevEdge0 local | Local compute | Environment dependent | Existing next-token scoring and option-order checks; inspect runtime and weights before running. Conditional scores are not calibrated probabilities. |

OpenRouter lists the [alpha Decisions endpoint](https://openrouter.ai/openai/gpt-6-luna-decisions/providers) for structured questions. Joey-1 has been invoked in small integration smoke runs, but no model has been selected for operational use. A comparison needs independent labeled decisions, fixed prompts and splits, actual per-call usage and latency, error rates and quality measurements; advertised prices or latency are not project measurements.

## Local JevEdge0 adapter

The loopback-only adapter sends a typed two-option decision to JevEdge0's `/v1/decisions` endpoint and can request option-order stability trials. It preserves the conditional option score, legal mass and stability metadata in receipts. These values are not calibrated probabilities of correctness and must not be compared as though they have the same calibration as hosted model outputs. By default every result remains unclear; explicitly supplied experimental thresholds can be applied only if requested stability checks report stable results.

As checked on 2026-10-30, the default local health endpoint was unavailable and no model directory was present in the sibling JevEdge0 checkout. The adapter was tested with a local HTTP fixture, not actual Edge0 weights. No local-vs-hosted inference or quality comparison has yet been measured. To use it, separately start a JevEdge0 workbench with the needed model, then supply `--jev-url http://127.0.0.1:8090 --stability-trials 2` to `index`, `search`, `assess-role`, or `experiment`. This does not launch or download a model.

## Hosted adapter smoke observations

The [role-scoring smoke record](../reports/2026-10-30-provider-role-smoke.json) contains one call each to Joey-1, d1.1 and Decider V1.2 on the same design-document section and reviewer role. It records resolved models, returned scores, elapsed times and provider usage. The example is unlabeled: differences in scores do not establish accuracy, calibration, ranking quality or a preferred model. One request per model is not a latency or cost benchmark. All judgments remained provisional because no operating thresholds were supplied.

## 2026-11-04: selected research model roles

The user selected [`tencent/hy4`](https://openrouter.ai/tencent/hy4) as the **preferred escalation model** for the next research integration, informed by other reviews the user has seen. Those reviews have not been supplied or independently assessed here. Hy4 is a text-generation and tool-capable model, distinct from the typed decision endpoint. The current code does not yet automatically route to Hy4; the selection is a design decision for implementation and evaluation, not a claim of deployment or measured superiority.

The intended research cascade is:

1. Preserve source revisions, original sections and explicit unsupported or stale evidence labels.
2. Use BM25 and, when adapters are tested, optional Cohere Embed 5 Pro and Rerank 5 Pro to retrieve and order source candidates. Role scores remain provisional ranking metadata, never proof or a reason to discard evidence.
3. Evaluate Morph Reflex for bounded typed decisions and switch navigation. Timeout, unstable results, absent evidence and unsupported output stay explicit, with deterministic baseline fallback. Do not infer operational thresholds from model scores alone.
4. Escalate a bounded, source-linked task to **Hy4** when a stronger generative agent is needed: for example, to synthesize conflicting evidence, make a source-backed plan, or review unresolved ambiguity. Supply the agent's role and purpose, task, evidence IDs/revisions/anchors, explicit uncertainty and a request/token budget. Record configured and resolved model, prompt version, sources, usage, cost, latency and failures. Output is a proposal with citations, not verified truth or authority to mutate the catalog.
5. Use Clairic's separate extraction API as an optional ingestion candidate for typed metadata. Preserve nulls and the source span; a guess or confidence is not a verified field.

The 2026-11-04 synthetic Hy4 smoke returned a valid short JSON answer with a matching source excerpt. This is a contract observation from one simple request, not a quality comparison. A bounded role-aware task pilot with frozen inputs should compare Hy4 with the existing planner and separate AI reviewer, report unsupported citations, uncertainty, latency and actual cost, and preserve all failures. Reusing the same model to generate and review its own output is not independent review. Any live swarm or MindStore integration remains outside the approved isolated slice.
