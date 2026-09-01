from __future__ import annotations

from research_workbench.abstract_resolver import AbstractResolver, openalex_abstract, repair_mojibake, title_matches
from research_workbench.models import PaperRecord


def test_openalex_abstract_reconstructs_positions_and_rejects_wrong_title() -> None:
    assert openalex_abstract({"second": [1], "first": [0], "last": [2]}) == "first second last"
    assert title_matches("AI and Education: Evidence from Schools", "AI and Education Evidence from Schools")
    assert not title_matches("AI and Education", "Health Insurance and Employment")
    assert repair_mojibake("Bachelorâ€™s Degrees") == "Bachelor’s Degrees"


def test_resolver_uses_complete_matching_openalex_metadata() -> None:
    words = ("This study estimates causal effects using a randomized school rollout and reports student outcomes " * 8).split()
    index: dict[str, list[int]] = {}
    for position, word in enumerate(words):
        index.setdefault(word, []).append(position)

    def fake_json(url: str):
        assert "api.openalex.org" in url
        return {"results": [{
            "id": "https://openalex.org/W123",
            "doi": "https://doi.org/10.1234/example",
            "display_name": "AI and Education: Evidence from Schools",
            "abstract_inverted_index": index,
        }]}

    paper = PaperRecord(paper_id="paper:1", title="AI and Education: Evidence from Schools")
    result = AbstractResolver(fetch_json=fake_json).resolve(paper)
    assert result is not None
    assert result.source == "OpenAlex"
    assert len(result.abstract.split()) == len(words)


def test_resolver_normalizes_canonical_openalex_url_before_lookup() -> None:
    words = ("A complete abstract grounded in the paper metadata and long enough for the recommendation gate " * 8).split()
    index: dict[str, list[int]] = {}
    for position, word in enumerate(words):
        index.setdefault(word, []).append(position)

    def fake_json(url: str):
        assert url == "https://api.openalex.org/works/W123"
        return {
            "id": "https://openalex.org/W123",
            "display_name": "Energy Transition and Wages",
            "abstract_inverted_index": index,
        }

    paper = PaperRecord(
        paper_id="paper:2",
        title="Energy Transition and Wages",
        identifiers={"openalex_id": "https://openalex.org/W123"},
    )
    result = AbstractResolver(fetch_json=fake_json).resolve(paper)
    assert result is not None
    assert result.source == "OpenAlex"
