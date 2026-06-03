---
name: idea-retrospective
description: Use this skill when the user invokes $idea-retrospective, /idea-retrospective, asks to run idea-retrospective, or asks to generate a retrospective for an idea. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# idea-retrospective
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for Research Idea Pipeline.
## Trigger Forms
- $idea-retrospective
- /idea-retrospective
- Natural language requests to generate a retrospective for an idea
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\idea-retrospective.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Preserve Claude Code commands; never delete or overwrite files in {{HOME}}\.claude\commands\.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making the gated writes.
## Command Workflow
You are managing a research idea pipeline for an economics PhD student.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get the vault path (under "Research Idea Pipeline 鈫?Vault").
All file paths below are relative to that vault root.

Perform an **IDEA RETROSPECTIVE** operation for the slug provided in the arguments (e.g., `/idea-retrospective ai-generated-research`).

The goal is to produce a PDF document that a PhD advisor can read to understand the full intellectual journey of the idea: how the research question evolved, where the student's own thinking contributed, what literature was engaged with and why it was insufficient, and what specifically caused the idea to be archived or paused.

---

## Step 1: Read source material

1. Read `ideas/<slug>.md` in full 鈥?this contains all discussion notes, pivots, and accumulated thinking
2. Read `ideas/log.md` 鈥?for timeline context
3. Read `ideas/index.md` 鈥?to understand related ideas

---

## Step 2: Reconstruct the intellectual narrative

From the source material, extract and organize:

**A. Direction changes**
Every time the research question, measurement strategy, or identification approach changed materially, note:
- What the approach was before
- What forced the change (a logical problem, an external paper, a seminar comment)
- What the approach became after

**B. Branching points**
Every time a sub-question split off into its own idea, note:
- What the sub-question was
- Why it needed to be separated
- Which slug it became

**C. The student's own critical contributions**
Identify moments where the student (not a paper) provided the intellectual insight:
- Catching a flaw in the framework
- Distinguishing two concepts that the literature conflates
- Raising a validity concern after reading a paper
These should be highlighted visually in the document.

**D. Literature engagement**
For each paper reviewed, note:
- What it offered toward the research question
- Why it was ultimately insufficient or incomplete
This is not a literature review 鈥?it is a record of what each paper contributed to and failed to solve in the student's specific problem.

**E. The archive/pause decision**
The specific, numbered reasons the idea was set aside. These must be precise: not "measurement is hard" but the exact conceptual or empirical barrier identified.

**F. Revival conditions**
What would need to exist or be resolved for this idea to become viable again.

---

## Step 3: Generate the LaTeX document

Save to `reports/<slug>-retrospective.tex`.

Use the following LaTeX structure and preamble:

```latex
\documentclass[12pt, a4paper]{article}
\usepackage[margin=1.1in]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{microtype}
\usepackage{booktabs}
\usepackage{array}
\usepackage{parskip}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{mdframed}

\definecolor{archivecolor}{RGB}{180, 60, 60}
\definecolor{stagecolor}{RGB}{40, 80, 140}
\definecolor{pivotcolor}{RGB}{160, 100, 0}
\definecolor{insightcolor}{RGB}{30, 120, 60}

\hypersetup{colorlinks=true, linkcolor=stagecolor, urlcolor=stagecolor}
\titleformat{\section}{\large\bfseries\color{stagecolor}}{}{0em}{}[\titlerule]
\titleformat{\subsection}{\normalsize\bfseries}{}{0em}{}
\setlist[itemize]{itemsep=2pt, topsep=4pt}

% Box for the archive/pause decision
\newmdenv[backgroundcolor=gray!8, linecolor=archivecolor, linewidth=1.2pt,
  innerleftmargin=10pt, innerrightmargin=10pt, innertopmargin=8pt, innerbottommargin=8pt]{archivebox}

% Box for key conceptual breakthroughs (student's insight)
\newmdenv[backgroundcolor=insightcolor!6, linecolor=insightcolor, linewidth=1.2pt,
  innerleftmargin=10pt, innerrightmargin=10pt, innertopmargin=8pt, innerbottommargin=8pt]{insightbox}

% Box for direction changes and branching points
\newmdenv[backgroundcolor=pivotcolor!6, linecolor=pivotcolor, linewidth=1.2pt,
  innerleftmargin=10pt, innerrightmargin=10pt, innertopmargin=8pt, innerbottommargin=8pt]{pivotbox}
```

**Document structure 鈥?follow the narrative, not a fixed template:**

The sections should emerge from the actual intellectual journey. Do not use generic section names like "Stage 1, Stage 2." Instead, use descriptive titles that reflect what actually happened in each phase (e.g., "The Measurement Problem," "A Critical Design Fix," "Two Branches Split Off," "The Key Conceptual Breakthrough").

**Required elements:**

- Title block: idea title, student name, institution, date range of discussion, status
- One-paragraph framing note explaining the document's purpose (process documentation, not a research proposal)
- Narrative sections covering the full arc from original question to archive decision
- `\insightbox` for the student's own critical contributions 鈥?label each with `\textbf{Student insight:}`
- `\pivotbox` for direction changes and branching points 鈥?label each with `\textbf{Direction change:}` or `\textbf{Branch:}`
- `\archivebox` for the final archive decision 鈥?list numbered blocking problems with precise language
- A closing paragraph on revival conditions

**Tone:** Write for a PhD advisor who did not participate in the discussions. The document should make the intellectual process legible without assuming prior knowledge of the specific idea. Precise, academic, but not padded.

---

## Step 4: Compile to PDF

Run `pdflatex` twice (for cross-references) in the `reports/` directory:

```bash
cd <vault>/reports && pdflatex -interaction=nonstopmode <slug>-retrospective.tex
cd <vault>/reports && pdflatex -interaction=nonstopmode <slug>-retrospective.tex
```

Check for errors. Clean up auxiliary files (`.aux`, `.log`, `.out`, `.toc`).

---

## Step 5: Finalize

- Append to `ideas/log.md`: `[IDEA-RETROSPECTIVE YYYY-MM-DD] slug: <slug> 鈫?report: reports/<slug>-retrospective.pdf`
- Report to user: PDF page count, file path, and a 2-sentence summary of what the narrative covers.

