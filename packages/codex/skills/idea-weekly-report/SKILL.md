---
name: idea-weekly-report
description: "Use this skill when the user invokes $idea-weekly-report, /idea-weekly-report, asks for a weekly advisor update on research ideas, or wants a summary of ideas discussed during a date range. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# idea-weekly-report

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-weekly-report.md","source_sha256":"515f93d2edeaffcd70f8b76ec032e248360276f837abe73e2e5a4ab00c683330","workflow_version":"3.2.0"} -->

## Trigger Forms

- $idea-weekly-report
- /idea-weekly-report
- Natural language requests to summarize this week's discussed research ideas for an advisor or meeting

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-weekly-report.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /idea-weekly-report

Generate a concise advisor-facing report from research ideas substantively discussed during a selected week. This is a reporting workflow, not a pipeline transition or literature review.

## Usage

`/idea-weekly-report [this-week|last-week|YYYY-MM-DD..YYYY-MM-DD] [brief|email]`

Defaults:

- interval: Monday 00:00 through the current time in the machine's local timezone;
- format: `brief`;
- destination: return Markdown in the conversation only.

If the user gives an explicit date range, use a half-open interval from the start date at 00:00 through the day after the end date at 00:00. State the resolved dates and timezone at the top of the report.

## Step 0 - Resolve paths

Read `~/.claude/machine_paths.md` as UTF-8 and resolve:

- `<TOOLS_ROOT>` from `AI Research Tools -> Source root`;
- `<IDEA_VAULT>` from `Research Idea Pipeline -> Vault`.

Never guess a personal path.

## Step 1 - Find ideas discussed in the interval

Use the append-only discussion registry, not filesystem modification times:

```powershell
python "<TOOLS_ROOT>\scripts\research_core.py" idea-session discussed --idea-vault "<IDEA_VAULT>" --since <UTC-ISO-start> --until <UTC-ISO-end>
```

Deduplicate by slug while retaining every event in the interval. If the log is missing or empty, fall back to `updated_at` in `ideas/sessions/*-session.json`, label the result `timestamp fallback`, and do not infer discussion dates from idea-page frontmatter or file mtimes.

If no ideas qualify, say so plainly and stop. Do not include ideas merely because they are high priority or recently created.

## Step 2 - Load bounded context for each qualifying idea

For each slug, read only:

1. the discussion events within the selected interval;
2. `ideas/sessions/<slug>-session.json`;
3. the idea page's title, frontmatter, Current Brief or Original Idea, and latest relevant Decision Log entry;
4. the authoritative S2 sidecar Gate Brief only when needed to avoid misstating current status.

Do not run external search, generate new literature claims, inspect candidate datasets, or reopen a paused feasibility investigation. Summarize what the researcher actually considered that week. If the session and idea page conflict, report the conflict rather than resolving it silently.

## Step 3 - Write for an advisor

Assume the ideas are preliminary. Preserve uncertainty and distinguish:

- what the researcher currently thinks;
- what evidence or design was considered;
- what remains unverified;
- what feedback is requested from the advisor.

Use this compact structure:

```markdown
# Weekly Idea Update

**Period:** YYYY-MM-DD to YYYY-MM-DD (timezone)
**Note:** These are early-stage ideas discussed this week, not settled proposals.

## 1. [Idea title] (`slug`)

**One-sentence idea.** ...

**What I thought through this week**
- At most 3 concise bullets.

**Current direction.** 1-3 sentences on the most plausible mechanism, design, or data route.

**Main uncertainty.** The most decision-relevant blocker or identification concern.

**Questions for advisor**
- 1-2 concrete questions that the advisor can answer.

**Current disposition.** Continue / tentative / pause pending advisor discussion / parked, using only the researcher's recorded decision.

## Across the ideas

- The shared theme or tradeoff, if one genuinely exists.
- Which decision would most help allocate next week's research time.
```

Do not force a ranking unless the researcher has stated one. Do not call a gap novel, a design causal, or a dataset obtainable when the records mark it unverified.

For `email`, add a short subject line and greeting, then use the same substantive content in a more natural email voice. Draft only; never send email without a separate explicit instruction and confirmation.

## Step 4 - Output and persistence

Return the report in the conversation by default. Do not save it to the vault merely because it was generated.

Only when the user explicitly asks to save or export, write to:

`<IDEA_VAULT>\ideas\reports\weekly\weekly-idea-report-<end-date>.md`

Saving a report does not modify idea pages, sessions, index, `ideas/log.md`, S2 state, checkpoints, or human-only fields.
