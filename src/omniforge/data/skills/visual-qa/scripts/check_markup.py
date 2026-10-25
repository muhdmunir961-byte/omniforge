"""Read-only static HTML audit, no script or browser execution."""
from __future__ import annotations
import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path


class MarkupInspector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.missing_alt = []
        self.remote_scripts = []
        self.has_lang = False
        self.has_viewport = False
        self.line = 0

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        line, _ = self.getpos()
        if data.get("id"):
            self.ids.append((data["id"], line))
        if tag == "html" and data.get("lang"):
            self.has_lang = True
        if tag == "meta" and data.get("name", "").lower() == "viewport":
            self.has_viewport = True
        if tag == "img" and "alt" not in data:
            self.missing_alt.append(line)
        if tag == "script":
            src = (data.get("src") or "").strip().lower()
            if src.startswith(("https://", "http://", "//")):
                self.remote_scripts.append({"line": line, "src": src})


def inspect(path: Path) -> dict:
    if not path.is_file() or path.is_symlink() or path.suffix.lower() != ".html":
        raise ValueError("Expected a normal HTML file")
    if path.stat().st_size > 2_000_000:
        raise ValueError("HTML exceeds 2MB")
    parser = MarkupInspector()
    parser.feed(path.read_text(encoding="utf-8"))
    ids = Counter(item[0] for item in parser.ids)
    issues = []
    if not parser.has_lang:
        issues.append({"rule": "missing-html-lang"})
    if not parser.has_viewport:
        issues.append({"rule": "missing-viewport-meta"})
    for name, count in sorted(ids.items()):
        if count > 1:
            issues.append({"rule": "duplicate-id", "id": name, "count": count})
    for line in parser.missing_alt:
        issues.append({"rule": "image-missing-alt", "line": line})
    return {
        "file": str(path),
        "ok": not issues,
        "issues": issues,
        "remote_scripts": parser.remote_scripts,
        "notice": "Static HTML heuristic only; not a WCAG/JS/browser audit.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read-only HTML UI heuristic audit")
    parser.add_argument("html", type=Path)
    args = parser.parse_args(argv)
    try:
        result = inspect(args.html)
    except (ValueError, OSError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
