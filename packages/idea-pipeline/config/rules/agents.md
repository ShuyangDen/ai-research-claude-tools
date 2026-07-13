# Agent Orchestration

## Default

Use one agent for ordinary paper reading, `/idea-chat`, profile updates, queue sync,
and local knowledge retrieval. A direct conversation should not silently fan out
into parallel research agents.

Prefer deterministic tools for path resolution, bounded retrieval, validation,
and durable run state. The conversational agent owns the synthesis; tools own
repeatable control operations.

## Sub-agents

Do not start S2 or Challenge sub-agents in the current workflow release. Their
interfaces are reserved for a later, explicit single-agent versus multi-agent
A/B evaluation.

For software maintenance, independent bounded subtasks may be delegated when
parallel work materially improves speed or review quality. Give every sub-agent
a narrow file boundary and keep one writer per file.

## Safety

- Never let two agents write the same canonical idea, profile, queue, or index.
- Record actor, scope hash, and output artifact when a delegated task writes state.
- Research claims from any agent still require provenance and locators.
- A sub-agent cannot approve human-only novelty or stage-gate decisions.
