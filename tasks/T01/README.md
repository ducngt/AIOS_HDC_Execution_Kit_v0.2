# T01 — Canonical Meta-Model

## Purpose

Establish the machine-verifiable canonical meta-model used as the shared
structural language for subsequent AIOS kernels, domains, capabilities,
agents, workspaces, evidence, decisions, and changes.

T01 defines canonical concepts, references, lifecycle semantics, and
cross-object invariants.

T01 does not implement business-domain runtime.

## Canonical concept families

- Identity
- Organization
- Role
- Context
- Authority
- Delegation
- Policy
- Semantic
- Capability
- Contract
- Domain
- Work
- Decision
- Evidence
- Event
- Agent
- Change

## Core invariants

- Identity != Role
- Role != Authority
- Capability != Authority
- Evidence != Decision
- AI Recommendation != Human Decision
- Domain != Organization Unit
- Current State != History
- Registry configuration != source-code hard-coding
- Canonical references must be explicit and machine-verifiable
- Canonical objects must be versionable

## Out of scope

- authentication/login runtime
- user database
- authorization engine
- organization administration UI
- semantic registry runtime
- agent runtime
- domain applications
- RIS/LIS implementation
- production database
- workflow engine
