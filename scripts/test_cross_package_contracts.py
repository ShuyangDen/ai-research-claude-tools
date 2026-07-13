#!/usr/bin/env python3
"""Cross-package tests for identities shared by discovery, reading, and PKB flows."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "packages" / "research-core" / "src"))

from research_core.identifiers import canonical_paper_id  # noqa: E402


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tracker = load_module(
    "cross_contract_tracker_core",
    REPO_ROOT / "packages" / "paper-tracker" / "tracker_core.py",
)
queue_sync = load_module(
    "cross_contract_queue_sync",
    REPO_ROOT / "packages" / "ai-education" / "papers" / "queue_sync.py",
)


class PaperIdentityContractTests(unittest.TestCase):
    def test_all_three_packages_emit_the_same_canonical_id(self) -> None:
        cases = (
            ("DOI paper", "https://doi.org/10.1234/ABC.9?utm_source=test"),
            ("arXiv paper", "https://arxiv.org/abs/2401.01234v3"),
            ("OpenAlex paper", "https://openalex.org/W123456789"),
            ("NBER paper", "https://www.nber.org/papers/w33941"),
            ("URL paper", "HTTPS://Example.COM:443/a//b/?utm_source=x&b=2&a=1#frag"),
            ("A Study—of AI 人力资本", ""),
        )
        for title, url in cases:
            with self.subTest(title=title):
                core_id = canonical_paper_id({"url": url or None, "title": title})
                tracker_id = tracker.stable_paper_id(title=title, url=url)
                education_id = queue_sync.stable_paper_id(title, url)
                self.assertEqual(tracker_id, core_id)
                self.assertEqual(education_id, core_id)


if __name__ == "__main__":
    unittest.main()
