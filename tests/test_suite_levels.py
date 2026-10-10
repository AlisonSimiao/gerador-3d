"""Ticket 17: two-level suite + release gate.

Fast level (no bpy): contract, IR and validator tests must collect and pass
in an environment without Blender. Integration level (official env) proves
each pipeline stage separately (see test_pipeline_stages.py). A release
requires the integration level green; broad-Python/no-bpy compat is out of
scope. This file pins the fast-level guarantee and the documented gate.
"""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]
FAST_TEST_MODULES = sorted(
    path
    for path in (REPO / "tests").glob("test_*.py")
    if path.name not in {"test_pipeline.py", "test_reimport_gate.py", "test_atomic_publication.py"}
)
BLENDER_MODULES = ["bpy", "mathutils"]


def _top_level_blender_imports(path: Path) -> list[str]:
    """Top-level `import bpy/mathutils` statements (function-local is fine)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            found.extend(
                alias.name.split(".")[0] for alias in node.names
                if alias.name.split(".")[0] in BLENDER_MODULES
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in BLENDER_MODULES:
                found.append(node.module)
    return found


def test_fast_modules_need_no_bpy_at_import_time() -> None:
    """Every fast test module and every worker module imports without bpy."""
    offenders = {}
    for path in [*FAST_TEST_MODULES, Path(__file__), *sorted((REPO / "blender_worker").glob("*.py"))]:
        bad = _top_level_blender_imports(path)
        if bad:
            offenders[path.name] = bad
    assert offenders == {}, f"modules requiring bpy at import time: {offenders}"


def test_fast_suite_passes_with_bpy_import_blocked(tmp_path: Path) -> None:
    """Mechanical proof: the fast level is green when bpy cannot be imported."""
    if os.environ.get("GERADOR_3D_NO_BPY_GUARD"):
        pytest.skip("already inside the no-bpy proof run")
    (tmp_path / "_no_bpy_blocker.py").write_text(
        "import sys\n"
        "BLOCKED = ('bpy', 'mathutils')\n"
        "class _Blocker:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name.split('.')[0] in BLOCKED:\n"
        "            raise ModuleNotFoundError(\n"
        "                f\"No module named '{name}' (nivel rapido nao usa Blender)\")\n"
        "        return None\n"
        "sys.meta_path.insert(0, _Blocker())\n"
        "for _mod in BLOCKED:\n"
        "    sys.modules.pop(_mod, None)\n",
        encoding="utf-8",
    )
    runner = (
        "import _no_bpy_blocker, sys, pytest\n"
        "sys.argv = ['pytest', '-m', 'not integration', '-q', '-p', 'no:cacheprovider',"
        " '--deselect',"
        " 'tests/test_suite_levels.py::test_fast_suite_passes_with_bpy_import_blocked']\n"
        "raise SystemExit(pytest.main(sys.argv[1:]))\n"
    )
    env = dict(
        os.environ,
        GERADOR_3D_NO_BPY_GUARD="1",
        PYTHONPATH=os.pathsep.join([str(tmp_path), str(REPO)]),
    )
    pre = subprocess.run(
        [sys.executable, "-c", "import _no_bpy_blocker, bpy"],
        capture_output=True, text=True, cwd=str(REPO), env=env,
    )
    assert pre.returncode != 0, "the bpy blocker itself must fail to import bpy"
    proc = subprocess.run(
        [sys.executable, "-c", runner],
        capture_output=True, text=True, cwd=str(REPO), env=env,
    )
    assert proc.returncode == 0, f"fast suite failed without bpy:\n{proc.stdout}\n{proc.stderr}"


def test_ci_runs_both_levels_separately() -> None:
    """The release gate is wired, not just written: CI runs the fast level
    without bpy and the integration level on the official env as its own job."""
    workflow = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "not integration" in workflow
    assert '- run: python -m pytest -m integration -q' in workflow
    assert '"3.13"' in workflow
    assert "needs: fast" in workflow


def test_release_requires_integration_green_is_documented() -> None:
    """The release gate lives in versioned docs, not tribal knowledge."""
    acceptance = (REPO / "acceptance" / "README.md").read_text(encoding="utf-8")
    assert "integra" in acceptance.lower(), "acceptance/README.md must name the integration suite"
    assert "approved" in acceptance, "acceptance/README.md must require approved baselines"
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "integration" in readme.lower()
    assert "release" in readme.lower(), "README.md must state the release gate"


def test_broad_python_no_bpy_compat_is_out_of_scope_in_docs() -> None:
    """No-bpy compat is a fast-feedback aid, not a supported product surface."""
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "fora de escopo" in readme.lower() or "out of scope" in readme.lower(), (
        "README.md must document that broad-Python/no-bpy compat is out of scope"
    )
