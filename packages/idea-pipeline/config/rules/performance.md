# Performance and Context Discipline

## Research conversations

- Read the target paper or idea before broad retrieval.
- Retrieve at most the evidence budget declared by the active workflow.
- Prefer claim cards and compact state over repeatedly loading full source files.
- Answer the user's question first; omit protocol narration and repeated recap.
- Load full paper text only when a requested detail is absent from the notes.

## Tool execution

- Parallelize independent read-only checks when it materially reduces latency.
- Use deterministic scripts for IDs, hashes, manifests, queue state, and schema
  validation.
- Cache only derived data; retain source hashes so stale caches are detectable.
- Keep runtime state and personal content outside the distributable tools package.

## Model choice

Choose a model according to the task's reasoning and tool-use needs rather than
hard-coding version-specific names in this package. Record the model only in eval
or run metadata when reproducibility requires it.
