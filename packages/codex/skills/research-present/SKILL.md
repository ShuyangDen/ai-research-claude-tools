---
name: research-present
description: Use this skill when the user invokes $research-present, /research-present, asks to run research-present, or asks to design or build research presentation materials. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# research-present
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for Research Presentation.
## Trigger Forms
- $research-present
- /research-present
- Natural language requests to design or build research presentation materials
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\research-present.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Preserve Claude Code commands; never delete or overwrite files in {{HOME}}\.claude\commands\.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making the gated writes.
## Command Workflow
You are helping the user design a research presentation 鈥?either an interactive HTML visualization or LaTeX Beamer slides 鈥?using the Socratic method. Work through the phases below in order. Ask one or two questions at a time. **Do not write any code until Phase 5 is confirmed.**

---

## Phase 1 鈥?Understand the context

Ask these questions, one at a time:

1. "What research are you presenting? Give me a one-paragraph description 鈥?model setup, key mechanism, main results."
2. "Who is the audience? (e.g., advisor / committee meeting / conference / job talk / self-exploration)"
3. "What format? Interactive HTML (can be opened in any browser, animations on scroll/hover) or LaTeX Beamer slides (compiled PDF, for projector)?"

---

## Phase 2 鈥?Map the content

4. "What are the core results you want the audience to walk away with? List them 鈥?one line each."
5. "What setup does the audience need first 鈥?assumptions, notation, a model? How many distinct steps?"
6. "Is there a concrete example or analogy (like a taxi driver or a researcher) that makes the mechanism intuitive? If yes, describe it."

---

## Phase 3 鈥?Design the narrative spine

Based on the answers, propose a section-by-section structure:
- Motivation (why this question matters, what existing papers miss)
- Setup / Assumptions (N sections, one per assumption)
- Results (M sections, one per result)
- Optional: derivation appendix or click-through modals

Ask: "Does this order feel right? Should anything come earlier or later?"

Then ask about each non-obvious transition:
7. "Between [assumption X] and [result Y] 鈥?what is the 'aha' step? What does the audience realize at that moment?"

---

## Phase 4 鈥?Design each section's visual, one at a time

For each section, ask both questions before moving on:

**A.** "What does the viewer *see* in this section 鈥?describe the diagram, axis, objects, labels. Be as concrete as possible."

**B.** "What *changes* as the viewer reads 鈥?what is the dynamic element that reveals the insight? (e.g., a bar grows, a threshold line appears, a region fades to gray)"

Work through sections in order. Don't advance to the next section until the current one is fully specified.

If the user is vague ("make it look nice"), ask for a concrete reference: "Can you describe what's on the whiteboard, or what the key comparison is?"

---

## Phase 5 鈥?Write and confirm the spec

Produce a complete spec in this format:

```
## Presentation Spec

Format: [HTML / Beamer]
Audience: [...]
Sections: [list with one-line description each]

---

### [Section name]
Text panel: [what the left column says 鈥?key equation, box callouts]
Visual: [what is drawn 鈥?axis range, objects, labels, colors]
Animation: [what changes and when 鈥?timing, trigger (auto / hover / scroll)]

### [Next section]
...
```

Show the full spec and ask: "Does this capture what you want? Any section to revise before I start building?"

**Do not begin implementation until the user explicitly confirms the spec.**

---

## Phase 6 鈥?Build

Once the spec is confirmed, implement in order. After each section is complete, show what was built and ask: "This section is done 鈥?does it look right? Should I continue to [next section]?"

### HTML implementation rules
- Vanilla JS only 鈥?no CDN, no external libraries. Self-contained single file.
- All diagrams drawn programmatically with SVG (`document.createElementNS`)
- Navigation: scroll-snap CSS + keyboard arrows + prev/next buttons + dot indicators
- Animations: `requestAnimationFrame` for continuous motion; CSS `transition` for discrete fades; `setTimeout` chain for sequential reveals
- Derivation modals: open on button click, close on Escape or overlay click
- Helper functions to define once and reuse: `axis()`, `seg()`, `vline()`, `txt()`, `chi()` (or equivalent for the model's learning function)

### Beamer implementation rules
- `aspectratio=169`, `11pt`
- TikZ for all diagrams
- All derivations in appendix frames with `[shrink=N]`
- Test compile after every 3 frames; fix all `Overfull \vbox` and `\hbox` warnings before proceeding

---

## Rules

- Always ask before assuming. Never decide the visual for the user.
- The Socratic questions are not optional 鈥?skip them only if the user explicitly provides the answer unprompted.
- If the user says "same as the previous section but X changes," confirm what X is before continuing.
- After building, remind the user: open in browser (HTML) or run `pdflatex` twice (Beamer).

