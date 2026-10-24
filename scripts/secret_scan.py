"""Best-effort high-confidence secret scanner for tracked repo files.

This does NOT replace GitHub secret scanning or detect all credentials.
It intentionally avoids printing secret values to CI logs.
"""
from pathlib import Path
import re
import subprocess
import sys

PATTERNS = {
    "private-key PEM": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub classic PAT": re.compile(r"ghp_[A-Za-z0-9]{36}\b"),
    "GitHub fine-grained PAT": re.compile(r"github_pat_[A-Za-z0-9_]{50,}\b"),
    "AWS access key ID": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
}
SKIP_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip", ".whl", ".wasm"}
MAX_BYTES = 2_000_000


def main() -> int:
    result = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True)
    found = []
    for entry in result.stdout.split(b"\x00"):
        if not entry:
            continue
        path = Path(entry.decode("utf-8", "surrogateescape"))
        if path.suffix.lower() in SKIP_SUFFIX or not path.is_file():
            continue
        if path.stat().st_size > MAX_BYTES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                # Avoid treating regex fixtures as credential leaks. We still
                # report the path and line, never raw matched credentials.
                context = text[max(0, match.start() - 30):match.start()]
                if path.name == "secret_scan.py" and ("re.compile" in context or "PATTERNS" in context):
                    continue
                found.append((path.as_posix(), label, text.count("\n", 0, match.start()) + 1))
    for path, label, line in found:
        print(f"Potential {label} in {path} at line {line} (value redacted)", file=sys.stderr)
    print(f"Scanned tracked source: {len(found)} high-confidence finding(s)")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
