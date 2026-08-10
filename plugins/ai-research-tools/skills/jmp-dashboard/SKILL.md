---
name: jmp-dashboard
description: "Use this skill when the user invokes $jmp-dashboard, /jmp-dashboard, asks to organize research around a job market paper, choose one primary and one backup idea, allocate weekly research attention, or inspect JMP portfolio violations and next artifacts."
---
# jmp-dashboard

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/jmp-dashboard.md","source_sha256":"7f356ba4f46f2c59726d3c378f0305298fef963e1b09910dbf27282cf807c8f4","workflow_version":"3.3.0"} -->

## Trigger Forms

- $jmp-dashboard
- /jmp-dashboard
- Natural language requests to build or refresh a job-market-paper research portfolio dashboard

## Codex Execution Rules

- Do **not** read `~/.claude/commands/jmp-dashboard.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /jmp-dashboard

Build or refresh a JMP-centered research portfolio dashboard. The workflow is
report-only unless the researcher explicitly approves portfolio-role changes.

## Inputs

Read `~/.claude/machine_paths.md` and resolve `<TOOLS_ROOT>`, `<IDEA_VAULT>`, and
`<PROJECTS_VAULT>`. Run:

```powershell
python "<TOOLS_ROOT>\scripts\research_core.py" jmp-dashboard-data `
  --idea-vault "<IDEA_VAULT>" `
  --projects-vault "<PROJECTS_VAULT>"
```

Read the generated snapshot plus the primary/backup feasibility sidecars and
active project index. Do not use modification time as substantive progress.

## Portfolio contract

- exactly one idea has `portfolio_role: primary`;
- at most one idea has `portfolio_role: backup`;
- primary and backup are not paused and both have feasibility gates;
- primary and backup have a human `continue` decision and a valid
  `project_slug` link to the tracked execution-project index;
- all other ideas are `parked` or unassigned;
- the dashboard names one next observable artifact, not a generic activity;
- weekly target is 70% primary execution, 20% targeted literature/feasibility,
  and 10% broad search/methods/taste calibration.

Render `<IDEA_VAULT>\reports\jmp-dashboard.md` from
`reports\_jmp_dashboard_template.md`. Include primary, backup, execution
project, sprint deadlines, last real result, next artifact, advisor blockers,
and deterministic portfolio violations.

If roles are missing or invalid, propose the smallest patch and ask for one
explicit confirmation. Role selection is a human portfolio decision. Never
auto-promote an AI-generated candidate or treat capture/Quick Scan approval as
JMP adoption. After confirmation, update only `portfolio_role`, `updated`, and
the append-only idea log; then regenerate the dashboard.
