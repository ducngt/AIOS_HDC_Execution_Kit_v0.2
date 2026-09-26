# AIOS Canonical Meta-Model

## Purpose

The Canonical Meta-Model provides the shared structural language used by
subsequent AIOS kernels, domains, capabilities, agents, workspaces, decisions,
evidence, events, and governed changes.

It is a contract-level model, not a production database schema.

## Canonical layers

1. Canonical Identity
2. Canonical Reference
3. Canonical Lifecycle
4. Canonical Object Envelope
5. Canonical Meta-Model Registry

## Concept families

Identity, Organization, Role, Context, Authority, Delegation, Policy,
Semantic, Capability, Contract, Domain, Work, Decision, Evidence, Event,
Agent, and Change.

## Reference rule

Canonical objects reference other objects through explicit typed references.
A reference does not embed or silently duplicate the target object.

## Lifecycle rule

Current state, lifecycle state, history, effective time, and provenance are
separate concerns.

## Scope boundary

T01 defines canonical structure and machine-verifiable contracts.
It does not implement authentication, authorization runtime, business-domain
applications, production databases, RIS/LIS, or workflow runtime.
