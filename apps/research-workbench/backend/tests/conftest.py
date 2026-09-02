from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_workbench.codex_app_server import FakeCodexAppServer
from research_workbench.config import WorkbenchSettings
from research_workbench.models import current_iso_week


@pytest.fixture
def workbench_fixture(tmp_path: Path) -> tuple[WorkbenchSettings, FakeCodexAppServer]:
    repo = tmp_path / "repo"
    tracker = tmp_path / "tracker"
    ideas = tmp_path / "ideas"
    ai = tmp_path / "ai-education"
    knowledge = tmp_path / "personal-knowledge"
    projects = tmp_path / "projects"
    state = tmp_path / "state"
    for path in (repo, tracker, ideas / "ideas", ai, knowledge, projects / "welfare", state):
        path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "machine_paths.md").write_text(f"AI_EDUCATION_PATH={ai}\n", encoding="utf-8")
    (ai / "CLAUDE.md").write_text("# Test Trevor bootloader\n", encoding="utf-8")
    (ai / "tutor").mkdir()
    (ai / "tutor" / "context_snapshot.md").write_text(
        "# Session Snapshot\nresponse_mode: default\n\n## Current State\n"
        "**New math gaps:** None.\n\n## Learner Profile (compressed)\n"
        "Economics researcher. Prefers intuition before formalism.\n",
        encoding="utf-8",
    )
    (ai / "tutor" / "system.md").write_text("# Test Trevor system\n", encoding="utf-8")
    (ai / "tutor" / "trevor.md").write_text("# Trevor\nSpeak Chinese and ask one question.\n", encoding="utf-8")
    week = current_iso_week()
    archive = tracker / "archives" / week / "run-123"
    archive.mkdir(parents=True)
    papers = [
        {
            "paper_id": f"paper:{index}",
            "title": f"Paper {index}: AI and Education",
            "abstract": (
                f"Paper {index} studies how access to an AI-supported education program changes "
                "student achievement and teacher practice. The authors use a randomized rollout "
                "across schools, measure outcomes before and after implementation, and report "
                "treatment effects on learning, engagement, and instructional time. The abstract "
                "also describes the sample, research design, main estimates, and limits on how far "
                "the results can be generalized to other school systems."
            ),
            "authors": "A. Researcher",
            "venue": "Working Paper",
            "url": f"https://example.test/{index}",
            "published": "2026-08-24",
            "source": "openalex",
            "methodology": "RCT" if index % 2 else "Difference-in-differences",
            "tier": 1 if index <= 3 else 2,
            "lane": "exploit" if index <= 4 else "adjacent",
            "score": 100 - index,
            "priority_rank": index,
            "provenance": [{"source": "openalex", "source_id": str(index), "fetched_at": "2026-08-24T12:00:00Z", "url": f"https://example.test/{index}"}],
        }
        for index in range(1, 8)
    ]
    pool = {
        "schema": "ai-research-workbench.candidate-pool",
        "schema_version": 1,
        "week": week,
        "github_run_id": "run-123",
        "generated_at": "2026-08-24T12:00:00Z",
        "source_health": {"status": "ok", "sources": {"openalex": {"status": "ok", "count": 7}}},
        "papers": papers,
        "content_hash": "fixture-hash",
    }
    (archive / "candidate_pool.json").write_text(json.dumps(pool), encoding="utf-8")
    (archive / "source_health.json").write_text(json.dumps(pool["source_health"]), encoding="utf-8")
    (archive / "manifest.json").write_text(json.dumps({
        "github_run_id": "run-123", "week": week, "status": "succeeded", "generated_at": "2026-08-24T12:00:00Z", "artifacts": []
    }), encoding="utf-8")
    queue = [
        {
            "paper_id": paper["paper_id"], "candidate_slug": f"paper-{index}", "title": paper["title"],
            "tier": paper["tier"], "lane": paper["lane"], "matched_signal": "", "authors": paper["authors"],
            "venue": paper["venue"], "url": paper["url"], "published": paper["published"], "added": "2026-08-24",
            "last_seen": "2026-08-24", "status": "queued", "score": paper["score"], "source": paper["source"],
            "identifiers": {}, "schema_version": "1.0",
        }
        for index, paper in enumerate(papers, 1)
    ]
    (tracker / "queue_state.jsonl").write_text("".join(json.dumps(item) + "\n" for item in queue), encoding="utf-8")
    (ideas / "ideas" / "teacher-ai.md").write_text(
        "---\ntitle: Teacher-AI Complementarity\nstage: s1\nstatus: active\nrole: primary\n---\n# Teacher-AI Complementarity\n",
        encoding="utf-8",
    )
    (projects / "index.md").write_text(
        "# Projects Index\n\n| slug | title | path | status | open-issues | last-sync |\n"
        "|------|-------|------|--------|-------------|-----------|\n"
        f"| welfare | Welfare | {repo} | active | 2 | 2026-08-24 |\n",
        encoding="utf-8",
    )
    (projects / "welfare" / "index.md").write_text(
        "---\nslug: welfare\ntitle: Welfare\n"
        f"project-path: {repo}\nstatus: active\nstage: draft\ncurrent-focus: health channel\n"
        "last-sync: 2026-08-24\nzotero-collection: pending\n---\n\nDraft welfare paper.\n\n"
        "Open Issues: 2 items\nRecent change: health channel\n",
        encoding="utf-8",
    )
    settings = WorkbenchSettings(
        repo_root=repo,
        machine_paths_file=tmp_path / "machine_paths.md",
        state_root=state,
        tracker_root=tracker,
        idea_vault=ideas,
        ai_education_root=ai,
        personal_knowledge_vault=knowledge,
        projects_vault=projects,
        project_paths={},
        skill_roots=(repo / "skills",),
    )
    return settings, FakeCodexAppServer(cwd=repo)
