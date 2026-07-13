# Paper Tracker — Setup Guide

The paper tracker runs as a GitHub Actions workflow that emails you a weekly digest of relevant economics papers. No server needed.

## Prerequisites

- A GitHub account (free)
- A Google account (for Gmail sending and Gemini API)
- Python 3.10+ for local testing (optional; the workflow uses 3.11)

## Step 1 — Fork or clone to your GitHub

Either:
- Fork this repo to your GitHub account, OR
- Create a new private repo and push this folder's contents to it

```bash
git init
git add .
git commit -m "feat: initial paper tracker setup"
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

## Step 2 — Get your API keys

**Google Gemini API key** (required — the LLM that filters papers):
1. Go to aistudio.google.com
2. Click "Get API Key" → "Create API key"
3. Copy the key

**Gmail App Password** (required — for sending the digest email):
1. Enable 2-Factor Authentication on your Google account
2. Go to myaccount.google.com → Security → App Passwords
3. Create an app password for "Mail"
4. Copy the 16-character password

## Step 3 — Configure GitHub Secrets

In your GitHub repo: Settings → Secrets and variables → Actions → New repository secret

Add these 4 secrets:

| Secret name | Value |
|-------------|-------|
| `GOOGLE_API_KEY` | Your Gemini API key |
| `SENDER_EMAIL` | Your Gmail address |
| `SENDER_PASSWORD` | Your Gmail App Password |
| `RECIPIENT_EMAIL` | Email(s) to send digest to (comma-separated for multiple) |

## Step 4 — Customize researcher_profile.md

Edit `researcher_profile.md` in this repo. The LLM uses this file to score paper relevance — good customization dramatically improves paper quality.

Key sections to fill in:
- **Core Research Focus**: what topics you care about
- **Retrieval Terms**: short terms that expand OpenAlex/arXiv recall before ranking
- **Methodology Requirements**: what methods you require (RCTs, IV, etc.)
- **Active Research Directions**: auto-synced from idea pipeline via `/update-researcher-profile`
- **What This Researcher Does NOT Care About**: topics to exclude

## Step 5 — Push and verify

```bash
git add researcher_profile.md
git commit -m "docs: customize researcher profile"
git push
```

The workflow runs every Monday at 8 AM New York time. To test immediately:
- GitHub → Actions tab → "Weekly Paper Digest" → "Run workflow"

Warning: `workflow_dispatch` is an end-to-end run and sends real email to every
configured recipient. Do not use it as a harmless CI-only test.

## Step 6 — Sync with idea pipeline (optional but recommended)

If you're using the idea pipeline, run `/update-researcher-profile` in Claude Code after setting up. It will:
1. Distill your active research ideas into Active Research Directions
2. Update the local tracker profile
3. Ask you to explicitly review and push that private profile; ordinary idea commands never push silently

## Customizing the digest

Use GitHub Actions variables or environment variables; no code edit is needed:

```text
PAPER_TRACKER_DAYS_BACK=7
PAPER_TRACKER_WEEKLY_MAX=15
PAPER_TRACKER_EVALUATION_MAX=180
PAPER_TRACKER_LANE_MIX=exploit:0.55,adjacent:0.20,contradiction:0.15,methodology:0.10
PAPER_TRACKER_SOURCE_FAILURE_THRESHOLD=2
PAPER_TRACKER_RETRIEVAL_TERMS=optional,extra,terms
```

`queue_state.jsonl` is the canonical queue. `reading_queue.md` is regenerated as
a legacy-compatible view for AI Education. Every run also emits
`source_health.json`; HTTP 400/configuration errors fail immediately, while
transient core-source failures mark a run degraded and fail when the configured
threshold is reached.

For local private structured signals, copy `recommendation_profile.example.json`
to `recommendation_profile.json`. The real file is gitignored and takes
precedence over Markdown profile parsing. A GitHub-hosted run cannot see an
ignored local file; keep the private `researcher_profile.md` current, or use an
explicitly reviewed private-repo deployment step for the structured projection.

The pre-model evaluation cap is deterministic and source-stratified. It bounds
Gemini calls, runtime, and cost without allowing one high-volume source to crowd
out every other source.
