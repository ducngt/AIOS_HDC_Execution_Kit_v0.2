# AIOS Canonical Meta-Model Invariants

The following distinctions are mandatory:

1. Identity != Role
2. Role != Authority
3. Capability != Authority
4. Evidence != Decision
5. AI Recommendation != Human Decision
6. Domain != Organization Unit
7. Current State != History
8. Registry Configuration != Source-Code Hard-Coding

These invariants are machine represented in
`manifests/canonical/meta-model.json`.

Subsequent AIOS tasks may refine the concepts but must not silently collapse
these distinctions.
