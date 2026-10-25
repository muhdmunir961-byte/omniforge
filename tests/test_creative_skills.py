"""New creative skill acceptance tests: real mesh geometry, markup audit and discovery."""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest
from omniforge.core import bundled_names, bundled_root, validate_skill, audit_skill
from omniforge.router import load_skill, search_skills, token_report

CREATIVE = ("interface-craft", "realtime-3d-mesh", "motion-interaction", "visual-qa")


def load_script(path: Path):
    spec = importlib.util.spec_from_file_location("skill_script_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_creative_skills_are_discoverable_and_valid():
    for name in CREATIVE:
        assert name in bundled_names()
        assert not validate_skill(bundled_root() / name)
        data = load_skill(name)
        assert data["name"] == name
        assert len(data["content"]) >= 800
        audit = audit_skill(bundled_root() / name)
        assert audit["structural_errors"] == []
        assert not audit["findings"], audit
    assert len(bundled_names()) == 18
    assert token_report()["skill_count"] == 18


@pytest.mark.parametrize(("query", "expected"), [
    ("premium design system UI UX", "interface-craft"),
    ("Three.js mesh 3d geometry shader", "realtime-3d-mesh"),
    ("animation motion transitions", "motion-interaction"),
    ("visual browser QA accessibility screenshots", "visual-qa"),
])
def test_creative_skill_search(query, expected):
    matches = search_skills(query, limit=8)
    assert expected in [item["name"] for item in matches]


@pytest.mark.parametrize(("shape", "rings", "segments"), [
    ("torus", 12, 10),
    ("uv-sphere", 12, 10),
    ("torus", 6, 3),
    ("uv-sphere", 8, 8),
])
def test_mesh_geometry_has_outward_faces_and_nonzero_triangles(shape, rings, segments):
    mod = load_script(bundled_root() / "realtime-3d-mesh" / "scripts" / "mesh_generator.py")
    points, uvs, norms, triangles = mod.generate(shape, rings, segments, 1, 1.15, 0.32)
    assert len(points) == len(uvs) == len(norms) == (rings + 1) * (segments + 1)
    expected = 2 * rings * segments if shape == "torus" else 2 * rings * (segments - 1)
    assert len(triangles) == expected
    for tri in triangles:
        a, b, c = [points[i - 1] for i in tri]
        cross = ((b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1]),
                 (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2]),
                 (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
        magnitude = math.sqrt(sum(x*x for x in cross))
        assert magnitude > 1e-8, (shape, tri)
        smooth = [sum(norms[i-1][axis] for i in tri) for axis in range(3)]
        assert sum(cross[i] * smooth[i] for i in range(3)) > 0, (shape, tri)
    for normal in norms:
        assert math.isclose(sum(x*x for x in normal), 1, abs_tol=1e-9)


@pytest.mark.parametrize("shape", ["torus", "uv-sphere"])
def test_obj_generator_creates_real_mesh_and_never_overwrites(tmp_path, shape):
    script = bundled_root() / "realtime-3d-mesh" / "scripts" / "mesh_generator.py"
    obj = tmp_path / "demo.obj"
    command = [sys.executable, str(script), "--shape", shape, "--rings", "9",
               "--segments", "8", "--out", str(obj)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    metadata = json.loads(result.stdout)
    assert metadata["has_normals"] and metadata["has_uv"]
    content = obj.read_text()
    assert "\nv " in content and "\nvt " in content and "\nvn " in content and "\nf " in content
    assert content.count("\nv ") == metadata["vertices"]
    assert content.count("\nf ") == metadata["triangles"]
    repeated = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert repeated.returncode != 0 and obj.read_text() == content


@pytest.mark.parametrize("shape", ["torus", "uv-sphere"])
def test_mesh_rejects_nonfinite_or_invalid_radii(shape):
    mod = load_script(bundled_root() / "realtime-3d-mesh" / "scripts" / "mesh_generator.py")
    for bad in [0, -1, float("inf"), float("nan")]:
        with pytest.raises(ValueError):
            mod.generate(shape, 8, 8, bad, 1, .3)
    with pytest.raises(ValueError):
        mod.generate("torus", 8, 8, 1, 1, 2)


def test_markup_auditor_reports_real_issues_without_code_execution(tmp_path):
    module = load_script(bundled_root() / "visual-qa" / "scripts" / "check_markup.py")
    doc = tmp_path / "site.html"
    doc.write_text('<html><head></head><body><div id="x"></div><p id="x"></p>'
                   '<img src="a.png"><script src="https://cdn.example/a.js"></script></body></html>')
    result = module.inspect(doc)
    rules = {issue["rule"] for issue in result["issues"]}
    assert {"missing-html-lang", "missing-viewport-meta", "duplicate-id", "image-missing-alt"} <= rules
    assert len(result["remote_scripts"]) == 1
    assert result["ok"] is False
    doc.write_text('<html lang="en"><head><meta name="viewport" content="width=device-width"></head>'
                   '<body><img src="a.png" alt=""></body></html>')
    assert module.inspect(doc)["ok"] is True
