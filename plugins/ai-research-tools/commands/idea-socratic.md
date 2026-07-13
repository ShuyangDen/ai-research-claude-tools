# /idea-socratic

Optional Socratic mode for `/idea-chat`; use it when the user wants to discover or sharpen their own reasoning, not as the default way to answer every idea question.

## Usage

`/idea-socratic <slug>`

Run `/idea-chat <slug> clarify` with these additions:

- Start from the target idea, authoritative S2 sidecar, and current session; do not start from the whole profile.
- Ask at most one question per turn and keep the response under 180 Chinese characters unless the user asks for an explanation.
- Answer direct questions directly. A concise answer may be followed by one diagnostic question.
- Tag a genuinely new, specific statement as `[INSIGHT: ...]`; do not tag paraphrases or generic preferences.
- Choose the next useful dimension from problem, mechanism, falsification, identification, evidence/data, and contribution. Do not force all dimensions or a minimum number of exchanges.
- Do not push causal methods before the estimand and mechanism are clear.
- Do not hint at literature from memory. Use retrieved claim cards or label the point `UNVERIFIED`.
- End when the user asks, a concrete decision is reached, or further questioning has low information value.

At a natural stopping point, stage a compact candidate delta in the idea session:

```markdown
### Socratic delta
- Question or estimand clarified:
- Mechanism clarified:
- Evidence that would change the belief:
- Main unresolved issue:
```

Merge it into `## S1.5: Socratic Refinement` only after explicit confirmation. If it changes an approved S2 scope axis, mark the gate dirty; never change a human gate decision.
