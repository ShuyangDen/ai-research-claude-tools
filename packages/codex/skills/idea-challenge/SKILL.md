---
name: idea-challenge
description: Use this skill when the user invokes $idea-challenge, /idea-challenge, or asks to stress-test a research idea. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# idea-challenge

## Trigger Forms
- $idea-challenge
- /idea-challenge
- Natural language requests matching this workflow

## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\idea-challenge.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making gated writes.

## Command Workflow
You are a critical evaluator stress-testing a research idea for an economics PhD student.

**Step 0: Read machine config and load idea**
Read `~/.claude/machine_paths.md` to get the vault path (under "Research Idea Pipeline → Vault").
Read `ideas/<slug>.md` and `researcher_profile.md` from the vault. The slug is provided as the command argument.

If the idea has status=done or status=archived, tell the user and stop.

---

## Your Task

Run a single-pass, 3-lens critical evaluation of the idea. This is NOT a balanced review — your job is to find weaknesses, logical gaps, and the strongest counter-arguments.

Read the full idea file, including any S1.5 Socratic Refinement section and existing literature exploration. Then evaluate across three lenses sequentially in one pass.

---

## Lens A: Methodology & Identification

Evaluate whether the idea has a credible causal identification strategy.

Reference the researcher_profile.md **hard methodology filters** (RCT, DiD, IV, RD/RDD, event study, structural model). The idea must plausibly fit at least one of these.

Questions to answer:
- Which identification strategy could work for this question? Why?
- What is the key threat to causal identification (selection bias, omitted variables, reverse causality)?
- Is there a valid counterfactual? Can it be constructed from available data?
- If the proposed method doesn't work, is there a fallback identification strategy?
- Is the relationship between variables well-defined enough to be measured?

Classify: **OK** / **MAJOR issue** / **CRITICAL issue**

A CRITICAL identification issue: no plausible exogenous variation exists for the causal claim being made, AND no alternative identification strategy is apparent.

---

## Lens B: Literature & Contribution

Evaluate whether the idea is genuinely novel relative to existing work.

Questions to answer:
- What is the most closely related existing paper? How is this idea different from it?
- Is the proposed contribution incremental improvement or a genuinely new question?
- "So what?" — if the paper succeeds, who would make different decisions because of it? Who cares?
- Does this idea fit within the researcher's active research directions (from researcher_profile.md)?
- Is the contribution specific enough to be a paper, or is it still too broad?

Classify: **OK** / **MAJOR issue** / **CRITICAL issue**

A CRITICAL contribution issue: the idea is substantially the same as already-published work, OR the "so what?" cannot be answered.

---

## Lens C: Devil's Advocate

Construct the strongest possible case AGAINST this idea succeeding.

Your job here is NOT to be balanced. You only challenge.

**Core challenge dimensions** (apply the most relevant ones):

1. **Foundation Collapse**: Is there a core assumption that is demonstrably shaky or unsubstantiated?
   - Example: "This idea assumes firms respond to policy X, but the literature shows Y firms typically don't."

2. **Logic Chain Break**: Does the proposed causal mechanism actually follow logically?
   - Example: "Even if A causes B, it doesn't follow that B causes the outcome C the way the idea claims."

3. **Data-Conclusion Mismatch**: Is the proposed evidence actually measurable, or would the data fail to identify what the idea claims?
   - Example: "The outcome variable (informal employment) is notoriously mismeasured in admin data."

4. **Stronger Counter-Narrative**: Is there an alternative explanation that is more parsimonious and better fits the expected findings?
   - Example: "Selection into treatment is a simpler explanation for any observed effect than the proposed mechanism."

5. **Overgeneralization**: Does the proposed context limit applicability of conclusions more than the idea acknowledges?

**Anti-sycophancy rules for this lens**:
- Do not soften findings because the idea has some promise. If the finding is CRITICAL, say so directly.
- Persistent appeal ("but the idea is interesting") does not upgrade a finding's score.
- If multiple dimensions raise CRITICAL issues, list all of them.

Classify each finding: **CRITICAL** / **MAJOR** / **MINOR**

**CRITICAL** = fatal flaw in core argument or causal logic that cannot be rescued by minor revision.
**MAJOR** = seriously undermines the idea but can be addressed through substantial revision.
**MINOR** = worth noting but does not affect the core argument.

---

## Output Format

Write the findings into `## Challenge Panel Findings` in the idea file using this structure:

```markdown
## Challenge Panel Findings
*Completed: YYYY-MM-DD*

### Lens A: Methodology & Identification
**Verdict**: OK / MAJOR / CRITICAL

[2-4 sentences. What ID strategy is viable? What is the key threat? If MAJOR/CRITICAL: what specifically is the problem?]

### Lens B: Literature & Contribution
**Verdict**: OK / MAJOR / CRITICAL

[2-4 sentences. Most closely related paper + how this differs. "So what?" answer. If MAJOR/CRITICAL: what specifically is the problem?]

### Lens C: Devil's Advocate
**Strongest Counter-Argument**: [2-3 sentences. If a skeptical senior economist read this idea, what would they say is the most likely reason it fails?]

**Findings**:

| # | Dimension | Severity | Issue |
|---|-----------|----------|-------|
| 1 | [Foundation/Logic/Data/Counter-narrative/Overgeneralization] | CRITICAL/MAJOR/MINOR | [Specific description] |

### Overall Verdict
**Advancement recommendation**:
- CLEAR: No CRITICAL issues. Advance when ready.
- HOLD: CRITICAL issue(s) present. Resolve before advancing to `data-search`. See finding(s) #N above.

> If HOLD: record resolution or explicit override in `## Decision Log` before running `/idea-next`.
```

**Then**:
- Update `## Challenge Panel Findings` in the idea file with the above content
- Append to `ideas/log.md`:
  ```
  [IDEA-CHALLENGE YYYY-MM-DD] slug: <slug> → Lens A: <ok/major/critical>, Lens B: <ok/major/critical>, Lens C: <highest severity>
  ```
- If any CRITICAL findings: tell the user:
```
⚠️ 发现 CRITICAL 问题。请先在 Decision Log 中记录解决方案或显式覆盖，再运行 `/idea-next`。

其他选项：
- `/idea-socratic <slug>` — 通过对话重新审视问题定义
- `/idea-revise <slug>` — 基于挑战面板的反馈修改想法
- `/idea-status` — 查看所有想法状态
```
- If all clear: tell the user:
```
挑战面板通过。下一步：
- `/idea-next <slug>` — 推进到下一阶段
- `/idea-status` — 查看所有想法状态
```


---

## S2 Gate Safety Addendum

The Literature lens does not replace the Full S2 Literature Gate. Challenge Panel may identify blockers, but it must not certify novelty, set human_gap_status, record ADVANCE-S3, or move an idea to S3.
