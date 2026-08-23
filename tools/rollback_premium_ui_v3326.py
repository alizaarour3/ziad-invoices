from __future__ import annotations
from pathlib import Path
import re
import sys


def find_root() -> Path:
    here = Path(__file__).resolve().parent.parent
    for start in (here, Path.cwd()):
        for p in (start, *start.parents):
            if (p / "app" / "static" / "index.html").exists():
                return p.resolve()
    raise FileNotFoundError("Ziad Invoices project root not found.")


def main() -> int:
    try:
        root = find_root()
        index = root / "app" / "static" / "index.html"
        html = index.read_text(encoding="utf-8")
        html = re.sub(
            r'\s*<link\b[^>]*premium-system-v3\.3\.26\.css[^>]*>\s*',
            "\n",
            html,
            flags=re.IGNORECASE,
        )
        index.write_text(html, encoding="utf-8", newline="\n")
        print("v3.3.26 UI link removed. Voucher/request templates were not touched.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
