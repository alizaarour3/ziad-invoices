from __future__ import annotations
from pathlib import Path
import re
import sys

MARKER = "premium-system-v3.3.25.css"


def find_project_root() -> Path:
    here = Path(__file__).resolve().parent.parent
    for start in (here, Path.cwd()):
        for candidate in (start, *start.parents):
            if (candidate / "app" / "static" / "index.html").exists():
                return candidate.resolve()
    raise FileNotFoundError("Could not find project root.")


def main() -> int:
    try:
        root = find_project_root()
        index = root / "app" / "static" / "index.html"
        css = root / "app" / "static" / MARKER
        html = index.read_text(encoding="utf-8")
        html = re.sub(r'\s*<link\b[^>]*premium-system-v3\.3\.25\.css[^>]*>\s*', "\n", html, flags=re.IGNORECASE)
        index.write_text(html, encoding="utf-8", newline="\n")
        if css.exists():
            css.unlink()
        print("Premium UI v3.3.25 removed. Voucher/request templates were not touched.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
