# /weekly-research-loop

Run one capacity-bounded weekly cycle from paper discovery to personalized idea
candidates. The loop uses the researcher's observable reasoning memory and
stops before any candidate becomes a formal idea.

## Inputs and boundaries

Read `~/.claude/machine_paths.md` and the applicable project instructions.
Use, when available:

- the current Gmail weekly digest or its saved English/Chinese reports;
- Paper Tracker candidate cards and current reading queue;
- this week's triage, reading feedback, and completed/rough-read notes;
- paper-cluster syntheses;
- `ideas/memory/reasoning-events.jsonl` and `idea-feedback.jsonl`;
- attributed external idea-pattern exemplars that the researcher explicitly
  endorsed during paper reading;
- the approved Researcher Pattern Card and current recommendation-profile hash.

Do not send email. Do not rerun the external tracker when the user says the
weekly tracker already ran. Do not create idea pages or advance stages without
explicit selection.

## Weekly cycle

1. **Reconcile inputs.** Identify the digest date, queue snapshot, completed
   readings, unresolved targeted reads, and source gaps. Gmail is an input
   source when the weekly reports were delivered there; do not ask the user to
   paste material that is already accessible.
2. **Allocate attention.** Run `/paper-batch-triage`. Default weekly human
   budget is one deep read, up to two targeted reads, and cluster-only handling
   for the rest. Preserve explicit user overrides.
3. **Close reading feedback.** Every full, selective, rough, or skipped paper
   receives terminal reading feedback. Record any explicit reasoning events,
   especially critiques, belief changes, idea connections, and stopping logic.
4. **Synthesize clusters.** Use `/paper-cluster-synthesis` for related papers.
   Produce claim, mechanism, identification, data, and contradiction matrices;
   do not force one-paper-at-a-time deep reading.
5. **Refresh memory.** Run the research-memory summary. Refresh the Pattern
   Card/profile only when new direct human evidence changes a durable rule.
   Advisor outcomes remain a separate feasibility/JMP signal.
6. **Generate weekly candidates.** Run `/idea-scout weekly`. Use this week's
   paper clusters as the seed and current frontier papers as nearest-neighbor
   checks. Generate 3-4 candidates, not the broad six-candidate default.
7. **Explain observable fit.** For each candidate show the triggering evidence,
   named reasoning moves, matched pattern IDs, mechanism, falsifiable contrast,
   data/identification path, time to first signal, salvage value, nearest
   papers, largest risk, and kill test. Do not expose hidden chain-of-thought.
   When fit comes from an endorsed external exemplar, name the source and show
   which abstract question-forming move was transferred. Do not copy the source
   topic or imply that the researcher originated the exemplar.
8. **Freeze and review.** Save the AI ranking and profile/style hashes before
   showing candidates. Ask the researcher to keep, modify, hold, or reject each
   candidate and record separate idea-feedback axes.
9. **Stop at the checkpoint.** Only selected candidates may enter `/idea-new`.
   A promising JMP candidate should normally enter `/idea-feasibility` before
   a costly literature or data build.

## Weekly output

Return:

- reading-budget execution and unfinished items;
- a compact cluster frontier map;
- newly recorded reasoning signals and unresolved unknowns;
- 3-4 ranked candidate cards;
- the exact user decision required for each candidate;
- no email, no remote push, and no automatic idea creation.

## Calibration

Once a month, reserve one weekly candidate set as held out. Freeze the AI idea
ranking before human review and run `/taste-calibration ideas`. Report idea
top-3 precision and pairwise agreement separately from paper-ranking metrics.
