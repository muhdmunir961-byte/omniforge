"""Fail-closed packaging verification for a release candidate.

Inspects actual wheel and sdist, not only source tree. Also checks that
mandatory runtime source and bundled skill data are present.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile
import zipfile

PACKAGE_FILES = {
    "omniforge/__init__.py",
    "omniforge/cli.py",
    "omniforge/mcp.py",
    "omniforge/provenance_v2.py",
    "omniforge/provenance_v2_cli.py",
    "omniforge/provenance_v2_policy.py",
    "omniforge/provenance_v2_evm.py",
    "omniforge/data/catalog.json",
}
SKILLS = (
    "api-probe", "browser-snapshot", "dependency-inventory", "esptool-chip",
    "firmware-preflight", "git-diff-review", "kicad-drc", "log-triage",
    "openapi-inventory", "python-symbols", "repo-recon", "secret-hygiene",
    "sqlite-inspector", "trivy-scan",
)
BLOCKED = (".env", ".git/", ".omniforge/", ".of-provenance/")


def validate(wheel: Path, sdist: Path, expected_version: str) -> dict:
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", expected_version):
        raise ValueError("Release version must be semantic MAJOR.MINOR.PATCH")
    if not wheel.name.endswith(f"-{expected_version}-py3-none-any.whl"):
        raise ValueError("Wheel filename/version mismatch or unexpected wheel platform tag")
    if not sdist.name.endswith(f"-{expected_version}.tar.gz"):
        raise ValueError("Source distribution version mismatch")
    with zipfile.ZipFile(wheel) as archive:
        files = set(archive.namelist())
        if not PACKAGE_FILES.issubset(files):
            raise ValueError("Wheel is missing runtime sources: " + repr(PACKAGE_FILES - files))
        for skill in SKILLS:
            name = f"omniforge/data/skills/{skill}/SKILL.md"
            if name not in files:
                raise ValueError(f"Wheel missing packaged skill {name}")
        if any(any(part in name for part in BLOCKED) for name in files):
            raise ValueError("Wheel contains excluded project state / secrets")
        metadata = [name for name in files if name.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise ValueError("Wheel metadata missing or ambiguous")
        body = archive.read(metadata[0]).decode("utf-8")
        if f"Version: {expected_version}" not in body or "License-Expression: MIT" not in body and "License: MIT" not in body:
            raise ValueError("Wheel version or license metadata incorrect")
    with tarfile.open(sdist, "r:gz") as archive:
        names = [entry.name for entry in archive.getmembers()]
        if not any(name.endswith("/LICENSE") for name in names):
            raise ValueError("sdist must include MIT LICENSE")
        if not any(name.endswith("/README.md") for name in names):
            raise ValueError("sdist must include README.md")
        if not any(name.endswith("/src/omniforge/provenance_v2.py") for name in names):
            raise ValueError("sdist missing v2 implementation")
    return {
        "verified_version": expected_version,
        "wheel": wheel.name,
        "sdist": sdist.name,
        "packaged_skills": len(SKILLS),
        "sha256": {
            wheel.name: hashlib.sha256(wheel.read_bytes()).hexdigest(),
            sdist.name: hashlib.sha256(sdist.read_bytes()).hexdigest(),
        },
        "note": "Content/metadata integrity check; not a malware or source reproducibility certification.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=Path("dist/release-manifest.json"))
    args = parser.parse_args()
    wheels = list(args.dist.glob("*.whl"))
    sources = list(args.dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise SystemExit("Expected exactly one wheel and one source archive")
    manifest = validate(wheels[0], sources[0], args.version)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
