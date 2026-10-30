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
