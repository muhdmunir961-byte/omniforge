# OmniForge release engineering

Release assets are not published simply because someone edits the version string.
GitHub Release publishing is gated by an explicit `vMAJOR.MINOR.PATCH` Git tag.
Manual and ordinary main-branch runs create **release candidates only**.

## Evidence before tagging

1. Review successful **CI**, **Cross-platform**, **Real Integrations E2E**,
   **Packaged CLI Preview**, and **Security and dependencies** workflows.
2. Ensure version fields match in `pyproject.toml`, `src/omniforge/__init__.py`
   and `vscode-extension/package.json`.
3. Inspect the latest coverage report and security findings; don't conceal known
   security vulnerabilities to make a dashboard appear green.
4. Run the **Verified release candidate** workflow; it checks test results,
   builds an sdist and wheel, validates the 14 packaged skills, builds a VSIX,
   generates a build-environment SBOM, SHA-256 checksums and a manifest.

## Publishing a tagged release

Only a repository maintainer should create the reviewed version tag. For example:

```bash
git fetch origin
git checkout main
git pull --ff-only
git tag -a v1.3.1 -m "OmniForge 1.3.0 verified release"
git push origin v1.3.1
```

The tag triggers `.github/workflows/release.yml`. That workflow runs its own
Linux/macOS/Windows regression gate, verifies release contents, creates a GitHub
artifact attestation for the binary artifacts and publishes a GitHub Release
**only if the tag matches the package version**.

Do not create a tag for a version if a GitHub Release already exists.
Do not publish to PyPI or the VS Code Marketplace without separate package
owner enrollment, access review and trusted-publishing configuration.

## Verify provenance and integrity

Download the artifacts from the release page, inspect `SHA256SUMS.txt` and
compare with `sha256sum` (or a platform equivalent). For a tagged release
that has successfully generated an attestation, GitHub CLI can inspect it:

```bash
gh attestation verify ./omniforge-*.whl --repo muhdmunir961-byte/omniforge
```

Checksums detect accidental changes. GitHub attestations link an artifact digest
to a GitHub Actions build identity, not the absence of malware or an independent
review. The local OF-Provenance hash-chain is a separate optional feature.

## Incident and rollback

Do not rewrite or delete historic tags, ledger hashes, or release checksums.
Publish a patched semantic version with a documented fix and deprecate the
affected version. If a security issue is exploitable, use private vulnerability
reporting before a coordinated public advisory.

Current limitation: no published PyPI package or Marketplace listing is
implied by the existence of this release workflow.
