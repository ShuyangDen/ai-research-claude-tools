from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from research_core.cli import main
from research_core.contracts import available_schemas, validate_contract
from research_core.doctor import check_install_manifest, run_doctor
from research_core.identifiers import (
    canonical_paper_id,
    normalize_arxiv,
    normalize_doi,
    normalize_url,
)
from research_core.idea_context import _latest_session
from research_core.machine_paths import parse_machine_paths
from research_core.profile import project_profile
from research_core.sessions import init_session, load_session, update_session
from research_core.state import RunStore
from research_core.util import sha256_file


FIXTURES = Path(__file__).parent / "fixtures"


def test_machine_paths_parser_resolves_all_known_fields() -> None:
    source = FIXTURES / "machine_paths.md"
    result = parse_machine_paths(source)
    assert result.tools_root == source.parent / "tools"
    assert result.personal_knowledge_vault == source.parent / "pkb"
    assert result.idea_vault == source.parent / "ideas"
    assert result.paper_tracker_profile == source.parent / "tracker" / "researcher_profile.md"
    assert result.paper_tracker_repo == "owner/repository"
    assert result.workflow_state_root == source.parent / "state"
    assert result.to_dict()["source"] == str(source)


def test_identifier_normalization_and_precedence() -> None:
    assert normalize_doi("https://doi.org/10.1000/ABC.") == "10.1000/abc"
    assert normalize_arxiv("https://arxiv.org/pdf/2401.12345v3.pdf") == "2401.12345"
    assert normalize_url("HTTPS://Example.COM:443/a//b/?utm_source=x&b=2&a=1#frag") == "https://example.com/a/b?a=1&b=2"
    assert canonical_paper_id({"doi": "doi:10.1000/X", "openalex": "W1234"}) == "doi:10.1000/x"
    assert canonical_paper_id({"title": "  A Study—of AI  "}).startswith("title-sha256:")
    with pytest.raises(ValueError):
        canonical_paper_id({})


def test_run_store_is_durable_resumable_and_contract_valid(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "state")
    started = store.start("paper-done", run_id="run-1", actor="tutor", scope_hash="scope-a")
    assert validate_contract("run-manifest", started) == []
    store.fail_step("run-1", "ingest", error="temporary")
    store.resume("run-1")
    failed_again = store.fail_step("run-1", "ingest", error="temporary-2")
    assert failed_again["steps"][0]["attempt"] == 2
    store.resume("run-1")
    store.complete_step("run-1", "ingest", output={"paper_id": "doi:10.1000/x"})
    completed = store.complete_run("run-1")
    events_path = tmp_path / "state" / "events" / "events.jsonl"
    before = events_path.read_text(encoding="utf-8").splitlines()
    assert store.complete_run("run-1") == completed
    assert events_path.read_text(encoding="utf-8").splitlines() == before
    assert completed["steps"][0]["attempt"] == 3
    assert validate_contract("run-manifest", completed) == []
    assert not store.manifest_path("run-1").read_bytes().startswith(b"\xef\xbb\xbf")
    events = [json.loads(line) for line in before]
    assert all(not validate_contract("event", event) for event in events)


def test_run_store_persists_human_wait_and_resumes(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "state")
    planned = store.start(
        "paper-done",
        run_id="run-human",
        actor="tutor",
        steps=["validate_note", "propose_idea_delta"],
    )
    assert [step["status"] for step in planned["steps"]] == ["pending", "pending"]
    assert validate_contract("run-manifest", planned) == []
    store.complete_step("run-human", "validate_note", output={"valid": True})
    store.start_step("run-human", "propose_idea_delta")
    waiting = store.wait_step(
        "run-human",
        "propose_idea_delta",
        reason="confirm candidate actions",
        details={"candidate_ids": ["doi:10.1/x#c001"]},
    )
    assert waiting["status"] == "waiting_human"
    proposal = next(step for step in waiting["steps"] if step["name"] == "propose_idea_delta")
    assert proposal["status"] == "waiting_human"
    assert validate_contract("run-manifest", waiting) == []
    with pytest.raises(RuntimeError, match="resume it first"):
        store.start_step("run-human", "apply_confirmed_delta")
    with pytest.raises(RuntimeError):
        store.complete_run("run-human")
    resumed = store.resume("run-human")
    assert resumed["status"] == "running"
    with pytest.raises(RuntimeError, match="Resolve waiting step"):
        store.start_step("run-human", "apply_confirmed_delta")
    store.complete_step("run-human", "propose_idea_delta", output={"accepted": []})
    assert store.complete_run("run-human")["status"] == "completed"


def test_idea_session_explicit_updates_and_scope_staleness(tmp_path: Path) -> None:
    vault = tmp_path / "idea-vault"
    idea = vault / "ideas" / "demo.md"
    idea.parent.mkdir(parents=True)
    idea.write_text("# Canonical idea\n", encoding="utf-8")
    original = idea.read_bytes()
    session = init_session(vault, "demo", mode="literature", objective="Clarify novelty", scope_hash="scope-a")
    assert validate_contract("idea-session", session) == []
    changed = update_session(vault, "demo", {"scope_hash": "scope-b", "agreed": ["A", "A", "B"]})
    assert changed["stale"] is True
    assert changed["previous_scope_hash"] == "scope-a"
    assert changed["agreed"] == ["A", "B"]
    assert idea.read_bytes() == original
    assert load_session(vault, "demo")["scope_hash"] == "scope-b"
    with pytest.raises(ValueError):
        update_session(vault, "demo", {"automatic_summary": "forbidden"})


def test_idea_context_never_reads_a_prefix_neighbor_session(tmp_path: Path) -> None:
    sessions = tmp_path / "ideas" / "sessions"
    sessions.mkdir(parents=True)
    neighbor = sessions / "ai-teachers-session.json"
    neighbor.write_text("{}", encoding="utf-8")
    assert _latest_session(sessions, "ai") is None
    exact = sessions / "ai-session.json"
    exact.write_text("{}", encoding="utf-8")
    assert _latest_session(sessions, "ai") == exact


def test_profile_projection_keeps_signal_lanes_separate() -> None:
    now = datetime(2026, 7, 13, tzinfo=timezone.utc)
    common = {
        "schema_version": "1.0",
        "status": "active",
        "title": "Signal",
        "mechanism": "Mechanism",
        "retrieval_terms": ["term"],
        "source_refs": [{"type": "test", "id": "fixture"}],
        "confidence": 1.0,
        "priority": "high",
        "observed_at": "2026-04-14T00:00:00Z",
        "updated_at": "2026-04-14T00:00:00Z",
    }
    signals = [
        {**common, "signal_id": "declared-ok", "signal_type": "declared", "human_approved": True},
        {**common, "signal_id": "declared-no", "signal_type": "declared", "human_approved": False},
        {**common, "signal_id": "portfolio-ok", "signal_type": "portfolio", "human_approved": True},
        {**common, "signal_id": "portfolio-no", "signal_type": "portfolio", "human_approved": False},
        {**common, "signal_id": "inferred", "signal_type": "inferred", "human_approved": False},
        {**common, "signal_id": "spec", "signal_type": "speculative", "human_approved": False},
        {**common, "signal_id": "negative", "signal_type": "negative", "human_approved": False},
    ]
    projection = project_profile(signals, now=now, half_life_days=90)
    assert projection["tier_1_signal_ids"] == ["declared-ok", "portfolio-ok"]
    assert projection["lanes"]["portfolio"][0]["tier_1_eligible"] is True
    assert projection["lanes"]["speculative"][0]["projection_score"] <= 0.25
    assert projection["lanes"]["negative"][0]["projection_score"] < 0
    assert all(
        not validate_contract("profile-signal", signal)
        for lane in projection["lanes"].values()
        for signal in lane
    )


def test_profile_hash_ignores_render_timestamp_when_semantics_do_not_change() -> None:
    signal = {
        "signal_id": "declared:stable",
        "signal_type": "declared",
        "status": "active",
        "title": "Stable interest",
        "mechanism": "same mechanism",
        "source_refs": [],
        "human_approved": True,
        "confidence": 1.0,
        "priority": "high",
        "observed_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-01T00:00:00Z",
    }
    first = project_profile([signal], now=datetime(2026, 7, 13, 10, tzinfo=timezone.utc))
    second = project_profile([signal], now=datetime(2026, 7, 13, 11, tzinfo=timezone.utc))
    assert first["generated_at"] != second["generated_at"]
    assert first["projection_hash"] == second["projection_hash"]


def test_doctor_finds_encoding_placeholder_paths_and_hash_drift(tmp_path: Path) -> None:
    scan = tmp_path / "scan"
    scan.mkdir()
    unresolved = "{{" + "TOOLS_ROOT" + "}}"
    (scan / "bom.md").write_bytes(b"\xef\xbb\xbfplaceholder " + unresolved.encode("utf-8") + b"\n")
    (scan / "broken.md").write_bytes(b"\xff\xfe")
    (scan / "mojibake.md").write_text("bad \ufffd text", encoding="utf-8")
    suspicious = scan / "mojibake-patterns.md"
    question_marks = "?" * 3
    bad_cjk = "\u93b4\u6223"
    suspicious.write_text(f"lost {question_marks} text\nprivate \ue123 character\n{bad_cjk} corrupted\n", encoding="utf-8")
    source = tmp_path / "source.md"
    installed = tmp_path / "installed.md"
    source.write_text("same", encoding="utf-8")
    installed.write_text("same", encoding="utf-8")
    manifest = tmp_path / "install.json"
    payload = {
        "schema_version": "1.0",
        "generated_at": "2026-07-13T00:00:00Z",
        "files": [{
            "source": str(source),
            "installed": str(installed),
            "source_sha256": sha256_file(source),
            "installed_sha256": "0" * 64,
        }],
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    report = run_doctor(scan_roots=[scan], install_manifest=manifest)
    codes = {item["code"] for item in report["findings"]}
    assert {"encoding.bom", "encoding.invalid_utf8", "encoding.mojibake", "placeholder.unresolved", "install.target_drift"} <= codes
    assert report["ok"] is False
    suspicious_lines = {
        item["line"]
        for item in report["findings"]
        if item["code"] == "encoding.mojibake" and item["path"] == str(suspicious.resolve())
    }
    assert suspicious_lines == {1, 2, 3}
    pua = next(
        item for item in report["findings"]
        if item["code"] == "encoding.mojibake"
        and item["path"] == str(suspicious.resolve())
        and item["line"] == 2
    )
    assert pua["severity"] == "warning"


def test_doctor_accepts_local_sync_and_repository_artifact_manifests(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "source.md"
    source.write_text("source", encoding="utf-8")
    destination = tmp_path / "installed.md"
    destination.write_text("installed", encoding="utf-8")
    local_state = tmp_path / "local-state.json"
    local_state.write_text(json.dumps({
        "schema_version": 1,
        "source_repository": str(repo),
        "artifacts": [{
            "source": "source.md",
            "destination": str(destination),
            "source_sha256": sha256_file(source),
            "installed_sha256": sha256_file(destination),
        }],
    }), encoding="utf-8")
    assert check_install_manifest(local_state) == []
    assert validate_contract("install-manifest", json.loads(local_state.read_text(encoding="utf-8"))) == []

    manifest_dir = repo / "packages" / "codex"
    manifest_dir.mkdir(parents=True)
    anchor = manifest_dir / "workflow-adapters.json"
    anchor.write_text("anchor", encoding="utf-8")
    artifact = repo / "VERSION"
    artifact.write_text("generated", encoding="utf-8")
    decoy = manifest_dir / "VERSION"
    decoy.write_text("wrong nearby file", encoding="utf-8")
    repo_manifest = repo / "packages" / "codex" / "install-manifest.json"
    repo_manifest.write_text(json.dumps({
        "schema_version": 1,
        "source_manifest": {"path": "packages/codex/workflow-adapters.json", "sha256": sha256_file(anchor)},
        "artifacts": [{"path": "VERSION", "sha256": sha256_file(artifact)}],
    }), encoding="utf-8")
    assert check_install_manifest(repo_manifest) == []
    assert validate_contract("install-manifest", json.loads(repo_manifest.read_text(encoding="utf-8"))) == []
    artifact.write_text("drift", encoding="utf-8")
    assert {item.code for item in check_install_manifest(repo_manifest)} == {"install.artifact_drift"}


def test_doctor_refuses_ambiguous_repository_roots(tmp_path: Path) -> None:
    outer = tmp_path / "outer"
    nested = outer / "nested"
    nested.mkdir(parents=True)
    for anchor in (outer / "anchor.json", nested / "anchor.json"):
        anchor.write_text("same anchor", encoding="utf-8")
    artifact = outer / "VERSION"
    artifact.write_text("version", encoding="utf-8")
    manifest = nested / "install-manifest.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "source_manifest": {"path": "anchor.json", "sha256": sha256_file(outer / "anchor.json")},
        "artifacts": [{"path": "VERSION", "sha256": sha256_file(artifact)}],
    }), encoding="utf-8")
    findings = check_install_manifest(manifest)
    assert {item.code for item in findings} == {"install_manifest.repo_root_ambiguous"}


def test_contract_catalog_and_cli_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    expected = {
        "paper-record", "queue-item", "reading-feedback", "claim-card", "event",
        "run-manifest", "profile-signal", "idea-session", "context-manifest", "install-manifest",
    }
    assert set(available_schemas()) == expected
    assert validate_contract("install-manifest", {"schema_version": 1})
    assert main(["paper-id", "--doi", "10.1000/XYZ"]) == 0
    assert json.loads(capsys.readouterr().out)["paper_id"] == "doi:10.1000/xyz"
    assert main(["contract", "validate", "paper-record", "{}"]) == 1


def test_reading_feedback_contract_matches_terminal_event_shape() -> None:
    feedback = {
        "schema_version": "1.0",
        "feedback_id": "feedback:0123456789abcdef0123",
        "paper_id": "doi:10.1234/example",
        "date": "2026-07-13",
        "slug": "example",
        "queue_item_id": None,
        "recorded_at": "2026-07-13T10:00:00Z",
        "rating": "high-value",
        "read_depth": "full",
        "outcome": "completed",
        "usefulness": "credible counterevidence",
        "surprise": "null result",
        "belief_changed": "narrower domain",
        "idea_affected": ["idea-one"],
        "reason": "",
        "actor": "human",
        "provenance": {"source": "paper-reading-tutor", "run_id": "paper-done-abc"},
    }
    assert validate_contract("reading-feedback", feedback) == []


def test_queue_item_contract_matches_tracker_state_shape() -> None:
    item = {
        "schema_version": "1.0",
        "paper_id": "doi:10.1234/example",
        "candidate_slug": "example",
        "title": "Example paper",
        "tier": 1,
        "lane": "exploit",
        "matched_signal": "portfolio:one",
        "authors": "A. Author",
        "venue": "Journal",
        "url": "https://doi.org/10.1234/example",
        "published": "2026-07-01",
        "added": "2026-07-13",
        "last_seen": "2026-07-13",
        "status": "queued",
        "score": 0.9,
        "source": "openalex",
        "identifiers": {"doi": "10.1234/example"},
    }
    assert validate_contract("queue-item", item) == []
