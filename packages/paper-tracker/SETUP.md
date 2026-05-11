# Paper Tracker — Setup Guide

The paper tracker runs as a GitHub Actions workflow that emails you a weekly digest of relevant economics papers. No server needed.

## Prerequisites

- A GitHub account (free)
- A Google account (for Gmail sending and Gemini API)
- Python 3.9+ for local testing (optional)

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

## Step 6 — Sync with idea pipeline (optional but recommended)

If you're using the idea pipeline, run `/update-researcher-profile` in Claude Code after setting up. It will:
1. Distill your active research ideas into Active Research Directions
2. Push the updated researcher_profile.md to this repo automatically

## Customizing the digest

Edit the `Config` class in `paperextract.py` and `paperextract_cn.py`:

```python
class Config:
    days_back: int = 7          # search window (days)
    final_max_papers: int = 15  # max papers in digest
```

The `ai_keywords` and `topic_keywords` lists control the initial paper search.
