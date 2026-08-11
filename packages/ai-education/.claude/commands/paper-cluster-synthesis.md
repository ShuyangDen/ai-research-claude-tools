# /paper-cluster-synthesis

Synthesize three to eight papers around one research question, mechanism, or
empirical wedge. This is the default bridge between broad AI reading and one
pivotal human deep read.

## Protocol

1. Read `~/.claude/machine_paths.md` and resolve `<AI_EDUCATION_PATH>`,
   `<IDEA_VAULT>`, and `<WIKI_VAULT>`.
2. Require an explicit cluster ID plus three to eight paper IDs from a confirmed
   batch-triage manifest. Do not silently widen the cluster.
3. Read existing source/notes first. Retrieve external text only for claims not
   already covered locally.
4. Label every claim's coverage as `metadata`, `abstract`, `selected sections`,
   or `full text`, and attach source locators when available.
5. Write `<AI_EDUCATION_PATH>\papers\clusters\<cluster-id>.md` atomically.

## Required output

- Common research object and why it matters economically
- Claim matrix: paper, unit, treatment/exposure, outcome, design, claim, coverage
- Identification comparison
- Contradictions, nulls, and boundary conditions
- Data and institutional-setting opportunities
- Nearest-paper / already-done threat
- Frontier delta: what remains genuinely unresolved
- Relevance to the current primary/backup JMP idea
- Reading decision: one pivotal `deep`, up to two `targeted`, or no human read
- One cheapest empirical falsification or feasibility test

Do not create a new idea automatically. If the cluster reveals a candidate,
stage it for explicit human selection and send it to `/idea-feasibility` before
a Full S2 gate. Do not inflate cluster synthesis into claims that the learner
personally mastered every paper.

If the learner identifies the decisive contradiction, missing mechanism,
measurement replacement, or cheapest falsification, persist that observable
move through `/record-research-reasoning`. The cluster file stores evidence;
reasoning memory stores the learner's reusable transformation rule.
