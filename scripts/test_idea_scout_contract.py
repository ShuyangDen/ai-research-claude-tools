from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IdeaScoutContractTests(unittest.TestCase):
    def test_trigger_eval_set_has_twenty_balanced_edge_cases(self) -> None:
        path = ROOT / "packages" / "idea-pipeline" / "evals" / "idea-scout" / "trigger-evals.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 20)
        self.assertEqual(sum(bool(row["should_trigger"]) for row in rows), 10)
        self.assertEqual(sum(not bool(row["should_trigger"]) for row in rows), 10)

    def test_canonical_skill_contains_safety_and_quality_contracts(self) -> None:
        text = (ROOT / "packages" / "idea-pipeline" / "commands" / "idea-scout.md").read_text(encoding="utf-8")
        required = (
            "at least 3 recent eligible papers",
            "source/venue breadth of at least 2",
            "At least half must be non-AI topics",
            "Do not create or edit `ideas/<slug>.md`",
            "idea_origin: ai_generated",
            "at most 5 papers",
            "at most 3 candidate openings",
            "profile prose stay local",
            "separate `Why now` and `Overlap` entries",
            "contributes zero researcher-profile interest/retrieval signal",
            "authoritative S2 sidecar records the human outcome `ADVANCE-S3`",
            "roughly 80%",
            "at least 70%",
            "at least 50%",
            "OpenAlex is a discovery/metadata index only",
            "labor economics and economics of education",
            "Tianjin University Ma Yinchu and SUFE",
            "actual recent abstract",
            "tier/evidence-weighted attention",
            "Do not equate attention with attractiveness",
            "crowding risk",
            "35% labor",
        )
        for phrase in required:
            self.assertIn(phrase, text)
        self.assertNotRegex(text.casefold(), r"verified (gap|novelty)")

    def test_ranked_journal_registry_has_access_and_opportunity_guards(self) -> None:
        import yaml

        path = ROOT / "packages" / "idea-pipeline" / "obsidian" / "JMP Idea" / "system" / "economics_journal_catalogs.yml"
        registry = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertIn("tju_msoe_2017", registry["catalogs"])
        self.assertIn("sufe_economics_public", registry["catalogs"])
        self.assertEqual(registry["ranking_policy"]["role"], "retrieval_and_attention_prior_not_paper_quality_or_novelty")
        self.assertIn("crowding", registry["ranking_policy"]["opportunity_rule"].casefold())
        enabled = [item for item in registry["journals"] if item.get("enabled_by_default")]
        self.assertTrue(enabled)
        self.assertTrue(all(item["abstract_access"]["status"].startswith("verified_") for item in enabled))

    def test_adapter_description_covers_positive_intent_without_single_idea_review(self) -> None:
        manifest = json.loads((ROOT / "packages" / "codex" / "workflow-adapters.json").read_text(encoding="utf-8"))
        adapter = next(row for row in manifest["adapters"] if row["name"] == "idea-scout")
        description = adapter["description"].casefold()
        for phrase in ("recent top-5", "hotspots", "personalized research ideas", "waits for confirmation"):
            self.assertIn(phrase, description)
        self.assertNotIn("existing idea literature review", description)


if __name__ == "__main__":
    unittest.main()
