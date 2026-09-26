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

## AIOS Integrated Prototype v0.1

The repository now includes a Human-testable integrated prototype in `ui/`.

Demo accounts (password `demo`):
- `human@aios.demo` — Human workspace
- `leader@aios.demo` — Leadership workspace
- `admin@aios.demo` — Administration workspace

Run with the optional AI provider proxy:

```bash
python -m hdc.prototype_server
```

For a real OpenAI-compatible AI provider, set server-side environment variables
`AIOS_AI_API_KEY`, `AIOS_AI_BASE_URL`, and `AIOS_AI_MODEL`. The API key is never
placed in browser code. Without provider configuration, the prototype falls back
to a deterministic local assistant so the UX remains testable.

Prototype data is synthetic/local-browser data and must not be treated as
authoritative institutional data.

## Foundation Identity & People import

The Administration workspace now supports direct import of NUTE XLSX foundation datasets (organization, positions, personnel, student cohorts, major cohorts, administrative classes and student profiles). Imported people become a shared canonical Identity foundation for RIS/LIS/SIS/PIS rather than being copied into each domain.

Run the full prototype server (required for XLSX import, account administration and real AI provider calls):

```bash
pip install -e .
python -m hdc.prototype_server
```

Then open `http://127.0.0.1:8000` and log in with the demo Admin account. Real accounts created in Administration authenticate through the server API. Uploaded source XLSX files are not stored by the app; normalized prototype data is written to the ignored `runtime/` SQLite database.
