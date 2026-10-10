"""Ticket 19 (integration): regenerate the whole tree matrix via the official path.

Compares OBJECTIVE properties only — determinism (same seed regenerates
byte-identical GLB), tri budget, validators green, 1024px preview present.
Aesthetic judgment stays human; no pixel assertions here.
"""

from pathlib import Path

import pytest

from tests._matrix_helpers import (
    assert_matrix_regenerates,
    assert_same_seed_regenerates_identical_glb,
)

pytestmark = pytest.mark.integration

TREE_DIR = Path("acceptance/tree")


def test_matrix_regenerates_with_objective_properties_green(
    tmp_path: Path,
) -> None:
    assert_matrix_regenerates("tree", TREE_DIR, tmp_path)


def test_matrix_same_seed_regenerates_identical_glb(tmp_path: Path) -> None:
    assert_same_seed_regenerates_identical_glb(TREE_DIR, tmp_path)
