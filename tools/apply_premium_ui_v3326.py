from __future__ import annotations

from pathlib import Path
import hashlib
import re
import shutil
import sys
import time

PATCH_ROOT = Path(__file__).resolve().parent.parent
ASSET = PATCH_ROOT / "app" / "static" / "premium-system-v3.3.26.css"
MARKER = "premium-system-v3.3.26.css"
LINK = '<link rel="stylesheet" href="/static/premium-system-v3.3.26.css?v=3.3.26" data-ziad-premium-ui="3.3.26">'


def find_project_root() -> Path:
    seen: set[Path] = set()
    for start in (PATCH_ROOT, Path.cwd()):
        for candidate in (start, *start.parents):
            try:
                candidate = candidate.resolve()
            except Exception:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            if (candidate / "app" / "static" / "index.html").exists():
                return candidate
    raise FileNotFoundError(
        "Could not find the Ziad Invoices root. Extract this patch into the project folder that contains app\\static\\index.html."
    )


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def protected_template_files(root: Path) -> list[Path]:
    paths: set[Path] = set()
    for folder in (
        root / "templates",
        root / "app" / "templates",
        root / "app" / "static" / "templates",
        root / "app" / "static" / "form-templates",
    ):
        if folder.exists():
            paths.update(p for p in folder.rglob("*") if p.is_file())

    static = root / "app" / "static"
    if static.exists():
        # In this project, standalone static HTML files are document/form pages.
        # index.html is the only application shell HTML allowed to change.
        paths.update(
            p for p in static.glob("*.html")
            if p.is_file() and p.name.lower() != "index.html"
        )
    return sorted(paths)


def fingerprint(paths: list[Path], root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in paths:
        if path.exists():
            out[str(path.relative_to(root)).replace("\\", "/")] = sha256(path)
    return out


def backup(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(f"{path.name}.backup-v3.3.26-{stamp}")
    shutil.copy2(path, dest)
    return dest


def install(root: Path) -> None:
    static = root / "app" / "static"
    index = static / "index.html"
    target = static / MARKER

    protected = protected_template_files(root)
    before = fingerprint(protected, root)

    if not ASSET.exists():
        raise FileNotFoundError(f"Patch stylesheet is missing: {ASSET}")

    index_backup = backup(index)

    if ASSET.resolve() != target.resolve():
        shutil.copy2(ASSET, target)

    html = index.read_text(encoding="utf-8")

    # Supersede the previous premium UI and keep this operation idempotent.
    html = re.sub(
        r'\s*<link\b[^>]*premium-system-v3\.3\.(?:25|26)\.css[^>]*>\s*',
        "\n",
        html,
        flags=re.IGNORECASE,
    )

    lower = html.lower()
    pos = lower.rfind("</head>")
    if pos < 0:
        raise RuntimeError("index.html has no </head> tag. Installation stopped safely.")

    html = html[:pos] + "  " + LINK + "\n" + html[pos:]
    index.write_text(html, encoding="utf-8", newline="\n")

    after = fingerprint(protected, root)
    if before != after:
        shutil.copy2(index_backup, index)
        raise RuntimeError(
            "TEMPLATE PROTECTION FAILED: a voucher/request template changed. index.html was rolled back automatically."
        )

    css = target.read_text(encoding="utf-8")
    # The CSS may mention protected classes only as exclusions/comments. It may
    # never define a rule whose target starts at a protected template selector.
    forbidden = [
        r'(^|[}\n]\s*)\.template-page\s*\{',
        r'(^|[}\n]\s*)\.template-bg\s*\{',
        r'(^|[}\n]\s*)\.template-field\s*\{',
        r'(^|[}\n]\s*)\.template-line-field\s*\{',
        r'(^|[}\n]\s*)\.template-checkbox\s*\{',
    ]
    for pattern in forbidden:
        if re.search(pattern, css, re.IGNORECASE | re.MULTILINE):
            shutil.copy2(index_backup, index)
            raise RuntimeError(
                "TEMPLATE PROTECTION FAILED: premium CSS directly targets a protected template class. Rolled back."
            )

    print("Ziad Invoices v3.3.26 premium UI installed successfully.")
    print(f"Project: {root}")
    print(f"UI stylesheet: {target.relative_to(root)}")
    print(f"index.html backup: {index_backup.relative_to(root)}")
    print(f"Protected template files verified unchanged: {len(before)}")
    print("Voucher/request templates: UNCHANGED")
    print("Application scale: 100% (no zoom-out / no scale-down)")


def main() -> int:
    try:
        install(find_project_root())
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
