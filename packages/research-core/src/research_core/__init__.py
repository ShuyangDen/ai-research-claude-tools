"""Deterministic primitives for the personal AI research workflow."""

from .identifiers import IdentifierSet, canonical_paper_id, normalize_identifier
from .idea_provenance import (
    IDEA_ORIGINS,
    LEGACY_ORIGIN,
    assert_origin_unchanged,
    idea_profile_eligible,
    normalize_idea_origin,
)
from .machine_paths import MachinePaths, parse_machine_paths, parse_machine_paths_text
from .state import RunStore

__all__ = [
    "IdentifierSet",
    "IDEA_ORIGINS",
    "LEGACY_ORIGIN",
    "MachinePaths",
    "RunStore",
    "canonical_paper_id",
    "assert_origin_unchanged",
    "idea_profile_eligible",
    "normalize_idea_origin",
    "normalize_identifier",
    "parse_machine_paths",
    "parse_machine_paths_text",
]

__version__ = "0.1.0"
