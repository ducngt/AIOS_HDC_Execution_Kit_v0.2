# T00 Acceptance Criteria

T00 may be accepted only when all of the following are demonstrated.

1. HDC contracts are machine-verifiable.
2. Invalid task state causes deterministic validation failure.
3. Implementation cannot be represented as accepted without Human acceptance evidence.
4. Change packages are linked to a task.
5. Engineering evidence is linked to the corresponding change.
6. Regression tests execute automatically.
7. CI executes the HDC Guard.
8. Guard failures produce actionable diagnostics.
9. Existing repository invariants remain valid.
10. Verification results can be replayed from a clean checkout.
11. No runtime state or secrets are committed.
12. Human acceptance remains an explicit authority boundary.

Acceptance of T00 must be performed by a Human and recorded separately from AI-generated engineering evidence.
