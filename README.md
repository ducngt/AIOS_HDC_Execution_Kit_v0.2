# AIOS HDC Execution Kit v0.2

AIOS HDC Execution Kit is the execution and governance framework for
Human-Directed Coding (HDC) in AIOS.

## Core principle

AI performs software engineering under Human authority and acceptance.

The Human owns:

- purpose;
- institutional meaning;
- standards;
- authority;
- responsibility;
- acceptance.

AI may perform:

- repository discovery;
- modelling;
- architecture preparation;
- contract preparation;
- implementation;
- testing;
- verification;
- replay;
- evidence preparation;
- operational tooling.

AI does not acquire institutional authority by performing technical work.

## Execution sequence

UNDERSTAND
-> DISCOVER
-> MODEL
-> CONTRACT
-> ARCHITECT
-> HUMAN GATE
-> IMPLEMENT
-> TEST
-> VERIFY
-> REPLAY
-> EVIDENCE
-> HUMAN ACCEPTANCE

## Repository model

- `governance/` - authority and acceptance rules
- `contracts/` - machine-verifiable execution contracts
- `hdc/` - HDC runtime
- `tasks/` - ordered implementation tasks
- `change-packages/` - proposed engineering changes
- `engineering-evidence/` - verification evidence
- `acceptance-packages/` - material for Human acceptance
- `manifests/` - domain, capability, agent and workspace declarations
- `docs/` - architecture and protocol documentation
- `.github/workflows/` - automated repository enforcement

## Version

Current baseline: `0.2.0`

## Bootstrap status

This repository initially contains the architecture required to build the HDC
execution system.

The HDC Guard itself is implemented through Task T00 and is not assumed to be
trusted before T00 verification and Human acceptance.
