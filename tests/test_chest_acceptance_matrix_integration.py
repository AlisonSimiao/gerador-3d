"""Ticket 20 (integration): regenerate the whole chest matrix via the official path.

Compares OBJECTIVE properties only — tri budget, validators green, 1024px
preview present, same-seed byte-identical GLB. Aesthetic judgment stays
human; no pixel assertions here.
"""

from pathlib import Path

import pytest

from tests._matrix_helpers import (
    assert_matrix_regenerates,
    assert_same_seed_regenerates_identical_glb,
)

pytestmark = pytest.mark.integration

CHEST_DIR = Path("acceptance/chest")


def test_matrix_regenerates_with_objective_properties_green(
    tmp_path: Path,
) -> None:
    assert_matrix_regenerates("chest", CHEST_DIR, tmp_path)


def test_matrix_same_seed_regenerates_identical_glb(tmp_path: Path) -> None:
    assert_same_seed_regenerates_identical_glb(CHEST_DIR, tmp_path)
