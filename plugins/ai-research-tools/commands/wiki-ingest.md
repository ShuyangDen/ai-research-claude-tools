# /wiki-ingest

Project canonical source claims into the personal concept wiki with content-hash idempotency.

## Usage

- `/wiki-ingest` — process every new or changed source
- `/wiki-ingest <source-file>` — process one source only

Read `~/.claude/machine_paths.md` as UTF-8 and resolve the Personal Knowledge Wiki vault and AI Research Tools source root. Read the vault `CLAUDE.md` before writing.

## Detect work

Compute SHA-256 for each candidate `sources/*.md`, excluding `_template.md`. Parse `wiki/log.md` by `(source path, sha256)`.

- Skip only when the same source hash has a successful ingest record.
- Re-ingest a changed source even when its filename was previously processed.
- Validate source schema, paper identity, claim types, and locators first.
- A malformed source is reported as blocked and left unchanged; do not fabricate wiki assertions from it.

## Projection rules

For each changed source:

1. Read its claim table, identification/data sections, learner reflections, open questions, and Idea Relationships.
2. Resolve concept aliases before creating a page; prefer updating an existing canonical concept over near-duplicate names.
3. Create/update assertions that retain `assertion_id`, `claim_id`, relationship, source path, locator, and status.
4. Keep contradictory claims separate and explain population/design/version boundaries.
5. Mark assertions from replaced claims `superseded`; do not erase provenance.
6. Preserve `## Human Notes` verbatim.
7. Atomically update concept pages and `wiki/index.md` through one writer.
8. Rebuild the compact retrieval catalog/index from the resulting assertions.

The wiki is a derived view. Never modify `sources/`, idea files, profile files, or S2 human fields during ingest.

## Commit ingest state

Append one UTF-8 log event only after all staged pages validate:

```text
[INGEST YYYY-MM-DD] source: <file> | sha256: <hash> | created: <pages or none> | updated: <pages or none> | superseded: <count>
```

If an active S2 gate may change, report a dirty-gate proposal containing the source/claim IDs. The paper completion orchestrator, not wiki ingest, owns the actual gate-state write.

Report processed/skipped/blocked sources, assertions created/updated/superseded, alias decisions, and validation errors. Keep the summary compact.
