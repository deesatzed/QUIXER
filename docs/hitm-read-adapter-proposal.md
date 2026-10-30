# Proposed read-only HITMCockpit adapter

Status: **draft for separate review; not approved or implemented**. This document makes the integration decision concrete. It does not change either repository's existing policy or authorize a live swarm connection.

## Intended first slice

For a single non-sensitive project, let an orchestrator request a focused QUIX catalog result for an implementation or review task and show the agent source locations, record status and evidence references. Keep the existing HITMCockpit `MindStore` as the sole owner of its own entries and approvals. QUIX owns its catalog and derived index. This first slice has no write-back, no automatic promotion of findings into shared mind, and no new authority to execute agent actions.

## Current interfaces and important differences

HITMCockpit's `MindStore.slices(role:kinds:tags:budgetCharacters:destination:)` filters accepted entries, checks the log and content hashes, and applies its destination and sensitivity rules. Its `MindSlice` presently contains id, kind, title, body and tags, but not evidence links or the index revision. Its `AgentAdapter` currently exposes a planning proposal method; it is not a general shared-context transport. QUIX currently has a Python library and CLI, not a versioned agent-service protocol. Therefore direct file reads of `.hitm` or assuming either interface already supplies a complete evidence trail would bypass or invent semantics.

## Proposed boundary

1. A single HITMCockpit-owned process continues to call `MindStore.slices` using its existing destination and profile policy. Any export into QUIX must be an explicit future interface owned by that process, carrying only fields actually returned or separately verified by the store. For this first slice, avoid indexing HITMCockpit memory entirely; use QUIX to retrieve project documents and agent-produced records already in the QUIX catalog.
2. A future local request includes protocol version, task text, role and role-definition revision, result count and a named token or character budget. The response carries an immutable catalog fingerprint, source path/revision and section/page or span anchor, record lifecycle, evidence links, provisional/accepted index status, and any fallback or truncation reason. It must not turn a model's option score into a claim of truth or an authorization.
3. If QUIX is unavailable, returns malformed data, detects a changed source or lacks usable evidence, the orchestrator records that fact and proceeds according to its existing fallback and gate policy. It must not silently present stale or unverified material as current. The source paths and document revisions must be revalidated before use; a returned anchor is not evidence the source still matches the indexed bytes.
4. QUIX's returned-body token budget excludes protocol framing, titles, evidence metadata and agent prompt overhead. The caller must budget the complete agent request using its own tokenizer. A `cl100k_base` count is not proof of a different model's token count.

## Ownership and lifecycle

The single-writer QUIX catalog remains separate from HITMCockpit's single-process `MindStore`; neither SQLite nor `.hitm` gains multi-process writer safety through this proposal. Explicitly re-ingest changed source files before retrieval. Future indexing of MindStore content would require a separate design for allowed statuses, verification receipts, provenance, sensitivity/destination filtering, and revocation when an entry is corrected or expired. HITMCockpit's existing profile and destination restrictions remain in force even though the QUIX pilot corpus is non-sensitive.

## Verification before any integration claim

- Contract tests covering role/version and budgets, exact anchors, truncated data, stale source revisions, unknown model judgments, malformed responses and service unavailability.
- HITMCockpit tests showing its existing policy, evidence and approval paths remain authoritative and that no write is made to shared mind by retrieval.
- A real, independently labeled implementation/review retrieval comparison at matched context budgets before measuring the adapter's effect on agents.
- A controlled agent-task comparison with independent outcome review before claiming improved swarm performance. Report adapter failures, latency and cost separately.

Open decisions for the separate review: transport and process ownership, source-revision validation method, whether and how to expose verified MindStore slices, schema/versioning and explicit human approval for the integration scope. No live service, file watcher, memory write-back or agent dispatch is authorized by this draft.
