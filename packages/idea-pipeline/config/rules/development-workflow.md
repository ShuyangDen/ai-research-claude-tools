# Development Workflow

1. Inspect the current worktree and preserve unrelated user changes.
2. Define the smallest file boundary and behavioral contract for the change.
3. Add or update focused tests for risky behavior and state transitions.
4. Implement incrementally; keep generated artifacts derived from one canonical
   source and verify generation drift.
5. Run proportionate tests, encoding checks, and a dry-run before local sync.
6. Back up every existing destination before applying machine-local updates.
7. Never commit, push, or overwrite personal research data without explicit user
   authorization.

Parallel implementation is optional, not a default requirement. When used, keep
one writer per file and integrate centrally.
