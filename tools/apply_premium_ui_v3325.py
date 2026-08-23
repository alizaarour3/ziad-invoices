from __future__ import annotations

from pathlib import Path
import hashlib
import re
import shutil
import sys
import time

PATCH_ROOT = Path(__file__).resolve().parent.parent
ASSET = PATCH_ROOT / "app" / "static" / "premium-system-v3.3.25.css"
MARKER = "premium-system-v3.3.25.css"
LINK = '<link rel="stylesheet" href="/static/premium-system-v3.3.25.css?v=3.3.25" data-ziad-premium-ui="3.3.25">'


def find_project_root() -> Path:
    candidates: list[Path] = []
    for start in (PATCH_ROOT, Path.cwd()):
        candidates.extend([start, *start.parents])
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            candidate = candidate.resolve()
        except Exception:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "app" / "static" / "index.html").exists() and (candidate / "app" / "static" / "app.js").exists():
            return candidate
    raise FileNotFoundError(
        "Could not find the Ziad Invoices project root. Extract this patch directly into the project folder that contains app\\static\\index.html."
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
        root / "app" / "static" / "templates",
        root / "app" / "static" / "form-templates",
        root / "templates",
    ):
        if folder.exists():
            for p in folder.rglob("*"):
                if p.is_file():
                    paths.add(p)

    static = root / "app" / "static"
    if static.exists():
        for p in static.glob("*.html"):
            if p.name.lower() != "index.html":
                paths.add(p)
    return sorted(paths)


def fingerprint(paths: list[Path], root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for p in paths:
        try:
            result[str(p.relative_to(root)).replace("\\", "/")] = sha256(p)
        except FileNotFoundError:
            pass
    return result


def backup_file(path: Path, version: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.backup-{version}-{stamp}")
    shutil.copy2(path, backup)
    return backup


def install(root: Path) -> None:
    static = root / "app" / "static"
    index = static / "index.html"
    target_css = static / MARKER

    protected = protected_template_files(root)
    before = fingerprint(protected, root)

    if not ASSET.exists():
        raise FileNotFoundError(f"Missing patch asset: {ASSET}")

    # Back up only files this patch is allowed to change.
    backup = backup_file(index, "v3.3.25")

    # Copy the premium UI asset. This is application chrome CSS only.
    if ASSET.resolve() != target_css.resolve():
        shutil.copy2(ASSET, target_css)

    html = index.read_text(encoding="utf-8")

    # Remove older copies of this specific premium-theme link so the operation is idempotent.
    html = re.sub(
        r'\s*<link\b[^>]*premium-system-v3\.3\.25\.css[^>]*>\s*',
        "\n",
        html,
        flags=re.IGNORECASE,
    )

    if "</head>" not in html.lower():
        raise RuntimeError("index.html has no </head> tag; no changes were applied safely.")

    # Insert last in <head> so it becomes a controlled visual override.
    pos = html.lower().rfind("</head>")
    html = html[:pos] + "  " + LINK + "\n" + html[pos:]
    index.write_text(html, encoding="utf-8", newline="\n")

    after = fingerprint(protected, root)
    if before != after:
        # Emergency rollback of the only existing file modified by this installer.
        shutil.copy2(backup, index)
        raise RuntimeError(
            "Safety check failed: a protected voucher/template file changed. index.html was rolled back."
        )

    # Strong source-level guard: this CSS must not target official template classes.
    css = target_css.read_text(encoding="utf-8")
    forbidden_selector_patterns = [
        r'(^|[\s,>+~])\.template-page\s*\{',
        r'(^|[\s,>+~])#template-page\s*\{',
        r'(^|[\s,>+~])\.template-field\s*\{',
        r'(^|[\s,>+~])\.template-bg\s*\{',
        r'(^|[\s,>+~])\.template-line-field\s*\{',
        r'(^|[\s,>+~])\.template-checkbox\s*\{',
    ]
    for pattern in forbidden_selector_patterns:
        if re.search(pattern, css, flags=re.IGNORECASE | re.MULTILINE):
            shutil.copy2(backup, index)
            raise RuntimeError("Premium CSS attempted to style a protected template selector. Installation aborted and index.html was rolled back.")

    print("Ziad Invoices v3.3.25 premium system UI installed successfully.")
    print(f"Project: {root}")
    print(f"UI stylesheet: {target_css.relative_to(root)}")
    print(f"Backup: {backup.relative_to(root)}")
    print(f"Protected template files verified unchanged: {len(before)}")
    print("Voucher/request templates: UNCHANGED")
    print("App zoom/scale: 100% / no app-level zoom-out")


def main() -> int:
    try:
        root = find_project_root()
        install(root)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
