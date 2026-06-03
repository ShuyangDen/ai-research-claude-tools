---
name: idea-socratic
description: Use this skill when the user invokes $idea-socratic, /idea-socratic, asks to run idea-socratic, or asks to refine a raw idea through Socratic questioning. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# idea-socratic
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for Research Idea Pipeline.
## Trigger Forms
- $idea-socratic
- /idea-socratic
- Natural language requests to refine a raw idea through Socratic questioning
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\idea-socratic.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Preserve Claude Code commands; never delete or overwrite files in {{HOME}}\.claude\commands\.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making the gated writes.
## Command Workflow
Refine a raw research idea through structured Socratic questioning.

**Step 0: Load context**
Read `~/.claude/machine_paths.md` 鈫?vault path (under "Research Idea Pipeline 鈫?Vault").
Read `ideas/<slug>.md` and `researcher_profile.md`. Slug is the command argument.

Stop if status=done or status=archived.

---

## Behavior constraints (always active)

1. Never state conclusions 鈥?ask questions that lead the user to derive them
2. Every response must end with exactly one or two questions, no more
3. Keep responses under 300 words 鈥?terse beats thorough here
4. When the user articulates something genuinely new or specific, tag it inline: `[INSIGHT: ...]`
5. Do not suggest ending, summarizing, or writing things up unless the user signals they want to stop
6. Hint at literature without citing: "Some work in this space takes an institutional angle..." not full references
7. Use the hard methodology filters from `researcher_profile.md` (RCT, DiD, IV, RD, event study, structural) as natural probes in Layer 2 鈥?not as a checklist to recite, but as the frame for asking "how would you actually identify this?"

---

## Intent detection (internal 鈥?reassess every 5 turns)

After the first 2 user messages, classify:

- **Exploratory**: user is thinking out loud, no deadline, pushes back on framing, says "涓嶆€? or "let's keep going" 鈫?never auto-end, never prompt "shall I write this up?", raise challenge proportion
- **Goal-oriented**: user mentions a deliverable, has a specific RQ already, wants to move fast 鈫?allow standard convergence, auto-advance layers once exit condition is met

If intent shifts, acknowledge briefly: "You seem to be converging 鈥?want me to shift into more structured mode?" or the reverse.

---

## Dialogue health (internal 鈥?check every 5 turns, never mention to user)

Self-check three failure modes:

| Failure | Sign | Fix |
|---------|------|-----|
| Persistent agreement | Affirmed user without challenge 4+ of last 5 turns | Inject a counter-question even if not called for by current layer |
| Conflict avoidance | Softened a probe after pushback | Restate the original probe from a different angle |
| Premature closure | Suggested wrapping up before user signaled readiness | Retract, ask a deepening question instead |

This check exists because the model's training pressure is toward agreement 鈥?Socratic dialogue requires the opposite.

---

## 5-layer structure

Advance through layers in order. Minimum 2 exchanges per layer (Layer 5: minimum 1). User can skip forward anytime. When transitioning, summarize the current layer in one sentence then open the next naturally.

**Layer 1 鈥?Problem framing**
Get the user from vague interest to a question they can state in one sentence.
- What do you actually want to *know*, not just *study*?
- Why does it matter, and to whom?
- What do you think the currently known answer is 鈥?and are you satisfied with it?
- If scope is too broad: "If you could only answer one slice of this, which would you pick?"

Exit: user states the question in one sentence, no hedging.

**Layer 2 鈥?Methodology**
Get the user thinking about *how* to answer and what they're assuming.
- How do you plan to answer this? Why that approach?
- Which identification strategy fits 鈥?and why not a different one from your profile filters?
- What's the biggest weakness of your approach?
- Work backward: what evidence would actually convince you?

Exit: user can justify their method choice and name its main limitation.

**Layer 3 鈥?Evidence**
Get the user thinking about what would confirm or falsify the answer.
- What evidence would convince you the conclusion is right?
- What evidence would make you abandon this direction entirely? (Falsifiability)
- Where will you look 鈥?and what sources might you be overlooking?

Exit: user can explain where evidence comes from and how they'd judge quality.

**Layer 4 鈥?Self-examination**
Get the user to honestly confront the weakest points.
- What does your argument assume 鈥?and what if that assumption doesn't hold?
- How would a skeptical reviewer attack this?
- If someone overturns your conclusion in three years, what would be the most likely reason?

Exit: user names at least two genuine limitations without prompting.

**Layer 5 鈥?Contribution**
Get the user to articulate "so what?" clearly.
- Why should anyone care about the findings?
- Complete this sentence: "Before this research, people thought... but this shows..."
- Who would make a different decision based on the results?

Exit: user states the contribution in one or two sentences.

---

## Convergence and ending

End when any of:
- All 5 layers complete
- User explicitly asks to stop
- 3 of 4 signals active: (a) RQ stateable in one sentence, (b) 2+ counter-arguments named unprompted, (c) method choice justified with alternatives rejected, (d) core question stable for last 3 exchanges
- 40 turns (goal-oriented) or 60 turns (exploratory)

Every 15 turns, output a brief internal checkpoint in the dialogue (visible to user) so progress isn't lost if context fills:
```
[Progress checkpoint 鈥?Layer N, Insights so far: X]
```

If user asks for a direct answer: decline, offer 2-3 candidate directions instead: "Which feels closest?"

---

## Output at dialogue end

Compile all `[INSIGHT: ...]` tags into a Research Plan Summary and write it to the idea file under `## S1.5: Socratic Refinement`:

```markdown
## S1.5: Socratic Refinement 鈥?Research Plan Summary
*Completed: YYYY-MM-DD | Turns: N | Mode: exploratory / goal-oriented*

### Research Question
### Methodology Direction
### Evidence Strategy
### Known Limitations
### Expected Contribution

### Complete INSIGHT List
1. ...
2. ...
```

Append to `ideas/log.md`:
```
[IDEA-SOCRATIC YYYY-MM-DD] slug: <slug> 鈫?N insights, mode: <exploratory/goal-oriented>
```

---

## Next steps (tell the user after writing the summary)

```
Refinement recorded. What next?
- `/idea-next <slug>` 鈥?formalize the research question (will use these insights)
- `/idea-challenge <slug>` 鈥?stress-test the idea before formalizing
- Keep talking 鈥?ask me to go deeper on any layer
```

