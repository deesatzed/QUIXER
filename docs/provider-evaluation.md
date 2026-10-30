# Decision provider research checkpoint

Checked 2026-10-29. These are provider-listed specifications, not measured performance on QUIX tasks; prices and availability can change.

| Candidate | Provider-listed input price per million tokens | Listed context | Notes |
| --- | ---: | ---: | --- |
| [Perplexity Decider V1.2](https://openrouter.ai/perplexity/pplx-decider-v1.2/) | $0.02 | 262,144 | Typed choice, yes/no and score; listed choice limit 255. |
| [TypeSafe Jev 1.14](https://openrouter.ai/typesafe/jev-1.14/) | $0.042 | 262,144 | Typed decision model. |
| JevEdge0 local | Local compute | Environment dependent | Existing next-token scoring and option-order checks; inspect runtime and weights before running. Conditional scores are not calibrated probabilities. |

OpenRouter lists the [alpha Decisions endpoint](https://openrouter.ai/openai/gpt-6-luna-decisions/providers) for structured questions. No model has been selected or invoked for this project. A comparison needs independent labeled decisions, fixed prompts and splits, actual per-call usage and latency, error rates and quality measurements; advertised prices or latency are not project measurements.
