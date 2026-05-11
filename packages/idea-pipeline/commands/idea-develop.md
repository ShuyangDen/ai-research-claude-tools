Develop a research idea with targeted context drawn from the three-system knowledge base. Reads only lean indexes first, scores relevance, then loads only the relevant full files — not everything.

## Usage

`/idea-develop <slug>`

Where `<slug>` is an idea file name without `.md` (e.g. `ai-human-capital`, `ai-selective-reporting`).

---

## Step 0 — Read machine paths

Read `~/.claude/machine_paths.md` to get:
- AI Education path (under "AI Education Project → Project root")
- Idea vault path (under "Research Idea Pipeline → Vault")

---

## Step 1 — Load Layer 0 (indexes only)

Read these three files in parallel. Total size < 12 KB.

- `{{AI_EDUCATION_PATH}}\papers\index.md` — all studied papers with topics and one-liners
- `{{OBSIDIAN_ROOT}}\JMP Idea\ideas\index.md` — all research ideas with status
- `{{OBSIDIAN_ROOT}}\JMP Idea\researcher_profile.md` — active research directions and methodology standards

*(Replace `{{AI_EDUCATION_PATH}}` and `{{OBSIDIAN_ROOT}}` with the paths read from machine_paths.md)*

If `{{OBSIDIAN_ROOT}}\JMP Idea\ideas\<slug>.md` does not exist, stop and tell the user: "No idea file found at ideas/<slug>.md."

---

## Step 2 — Score relevance

From the indexes, score each item for relevance to the target idea `<slug>`. Do this in one pass, not as separate API calls.

**Score each studied paper** (from papers/index.md) on:
- Topic overlap with the idea's research direction
- Methodological relevance (does it use methods the idea requires?)
- Whether it provides evidence for, against, or context for the idea's mechanism

**Score each other idea** (from ideas/index.md, excluding the target slug) on:
- Whether it shares the same underlying mechanism or data requirement
- Whether it has a complementary or conflicting research question

Load everything that scores "relevant" — no hard cap on count. Typically 3–6 papers and 0–2 related ideas. If a paper is clearly unrelated (e.g., sovereign debt paper for an AI-education idea), skip it.

---

## Step 3 — Load Layer 2

Load the files identified in Step 2:

- `{{OBSIDIAN_ROOT}}\JMP Idea\ideas\<slug>.md` — the target idea (always load this)
- `{{AI_EDUCATION_PATH}}\papers\notes\<paper-slug>.md` — for each relevant paper
- `{{OBSIDIAN_ROOT}}\JMP Idea\ideas\<related-slug>.md` — for each related idea (if any)

Do NOT load full-text paper markdowns from `papers/text/` — notes files are sufficient.

---

## Step 4 — Report context loaded

Tell the user (in Chinese):
- Which idea is being developed
- Which papers were loaded (by title) and why each is relevant
- Which related ideas were loaded (if any)
- Total approximate context size

Then ask: "你想从哪个角度切入？（机制设计、数据策略、文献综述、还是批判性反思？）"

---

## Step 5 — Develop the idea

Work through whatever the user chooses. Draw explicitly on the loaded paper notes and researcher_profile when making connections. When you identify a new critique or research question, note it explicitly for the user to save to the idea file.

At the end of the session, remind the user to run `/idea-revise <slug>` to save any updates to the idea file.
