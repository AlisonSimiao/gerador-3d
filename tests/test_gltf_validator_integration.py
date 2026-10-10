"""ADR 0015 (integration): matrix GLBs pass the Khronos glTF Validator.

The canonical GLB of each Marco 1 type is regenerated via the official
path and validated with the Khronos `gltf_validator` binary: zero
conformity errors. The binary is optional infrastructure, never vendored:
when it is absent (no `GLTF_VALIDATOR` env var, no `gltf_validator` on
PATH) the test skips gracefully with the install procedure. See
`acceptance/README.md` for the release-gate command.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from blender_worker.export import generate_from_spec_file

pytestmark = pytest.mark.integration

VALIDATOR_ENV = "GLTF_VALIDATOR"
CANONICAL_SPECS = [
    ("house", "acceptance/house/canonical.json"),
    ("sword", "acceptance/sword/canonical.json"),
    ("tree", "acceptance/tree/canonical.json"),
    ("chest", "acceptance/chest/canonical.json"),
]
SKIP_REASON = (
    "Khronos glTF Validator ausente: defina GLTF_VALIDATOR com o caminho "
    "do binário ou instale-o (ver acceptance/README.md); sem ele, este "
    "gate não pode rodar e a release não pode ser aprovada."
)


def _find_validator() -> str:
    override = os.environ.get(VALIDATOR_ENV)
    if override:
        if Path(override).is_file():
            return override
        pytest.skip(f"{VALIDATOR_ENV}={override!r} não é um arquivo. {SKIP_REASON}")
    found = shutil.which("gltf_validator")
    if found is None:
        pytest.skip(SKIP_REASON)
    return found


def _validate(validator: str, glb: Path) -> dict:
    completed = subprocess.run(
        [validator, "-o", str(glb)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        pytest.fail(
            f"{glb.name}: saída do validador não é JSON: "
            f"{completed.stdout[:500]!r} / {completed.stderr[:500]!r}"
        )
    issues = report.get("issues", {})
    errors = issues.get("numErrors", 1)
    warnings = issues.get("numWarnings", 0)
    assert errors == 0, (
        f"{glb.name}: {errors} erro(s), {warnings} aviso(s) de conformidade: "
        f"{json.dumps(issues.get('messages', [])[:5], ensure_ascii=False)}"
    )
    return report


def test_canonical_glbs_pass_khronos_validator(tmp_path: Path) -> None:
    validator = _find_validator()
    for asset_type, spec in CANONICAL_SPECS:
        out = tmp_path / asset_type
        report = generate_from_spec_file(spec, str(out))
        assert report["ok"] is True, f"{spec}: {report.get('error')}"
        _validate(validator, out / "model.glb")
