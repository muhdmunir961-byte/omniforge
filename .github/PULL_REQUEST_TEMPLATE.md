# Pull request

## Why
Explain the user-facing bug or capability. Link an issue when one exists.

## Changes and risk
- [ ] Code and documentation are aligned.
- [ ] Security impact reviewed (filesystem, agent consent, network, credentials).
- [ ] Backward compatibility and migration considered.
- [ ] No private tokens or project contents included.

## Verification
- [ ] `python -m pip install -e . -r requirements-dev.txt`
- [ ] `python -m pytest -q`
- [ ] `python -m compileall -q src`
- [ ] Windows/macOS/Linux test results reviewed when platform behavior changes.
- [ ] Real E2E workflow reviewed when Docker, browser, VS Code or EVM behavior changes.
- [ ] Docs and changelog updated for user-visible changes.

## Limitations
Be explicit about functionality that has not been tested. Do not claim that heuristic
scanning is a penetration test, or that a local hash-chain is decentralized.
