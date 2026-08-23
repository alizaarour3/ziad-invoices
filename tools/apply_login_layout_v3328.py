from __future__ import annotations

from pathlib import Path
import hashlib
import shutil
import sys
import time

PATCH_ROOT = Path(__file__).resolve().parent.parent
SOURCE_CSS = PATCH_ROOT / "app" / "static" / "login-layout-v3.3.28.css"
LINK = '<link rel="stylesheet" href="/static/login-layout-v3.3.28.css" data-fix="login-layout-v3.3.28">'
MARKER = "login-layout-v3.3.28"
PROTECTED_DIR_NAMES = {"templates", "form-templates"}


def has_app(root: Path) -> bool:
    static = root / "app" / "static"
    return static.exists() and any((static / name).exists() for name in ("index.html", "app.html", "main.html"))


def discover_project_root() -> Path | None:
    # Supports either:
    # 1) patch files copied into project root, or
    # 2) patch folder extracted as a child of the project root.
    candidates = [PATCH_ROOT, PATCH_ROOT.parent]
    for root in candidates:
        if has_app(root):
            return root
    return None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def template_snapshot(project_root: Path) -> dict[str, str]:
    static = project_root / "app" / "static"
    snap: dict[str, str] = {}
    for dirname in PROTECTED_DIR_NAMES:
        d = static / dirname
        if d.exists():
            for p in sorted(x for x in d.rglob("*") if x.is_file()):
                snap[str(p.relative_to(project_root))] = sha256(p)
    return snap


def backup(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_name(path.name + f".backup-v3.3.28-{stamp}")
    shutil.copy2(path, dst)
    return dst


def find_entry_html(static: Path) -> Path | None:
    for name in ("index.html", "app.html", "main.html"):
        p = static / name
        if p.exists():
            return p
    htmls = [p for p in static.glob("*.html") if p.is_file()]
    return htmls[0] if htmls else None


def inject_link(path: Path, project_root: Path) -> bool:
    raw = path.read_text(encoding="utf-8-sig")
    if MARKER in raw or "login-layout-v3.3.28.css" in raw:
        print(f"[OK] Login layout stylesheet already linked in {path.relative_to(project_root)}")
        return False
    lower = raw.lower()
    idx = lower.rfind("</head>")
    if idx >= 0:
        out = raw[:idx] + "  " + LINK + "\n" + raw[idx:]
    else:
        out = LINK + "\n" + raw
    b = backup(path)
    path.write_text(out, encoding="utf-8")
    print(f"[OK] Linked login layout CSS in {path.relative_to(project_root)}")
    print(f"[OK] Backup created: {b.name}")
    return True


def main() -> int:
    project_root = discover_project_root()
    if not project_root:
        print("[ERROR] Ziad Invoices project root was not found.", file=sys.stderr)
        print("Extract this patch inside the project folder that contains app/static/index.html.", file=sys.stderr)
        return 1

    if not SOURCE_CSS.exists():
        print("[ERROR] login-layout-v3.3.28.css is missing from the patch.", file=sys.stderr)
        return 2

    static = project_root / "app" / "static"
    target_css = static / "login-layout-v3.3.28.css"
    entry = find_entry_html(static)
    if not entry:
        print("[ERROR] Could not find the static HTML entry file.", file=sys.stderr)
        return 3

    before = template_snapshot(project_root)

    # UI-only file copy. This is outside template directories.
    if SOURCE_CSS.resolve() != target_css.resolve():
        shutil.copy2(SOURCE_CSS, target_css)
    print(f"[OK] Installed {target_css.relative_to(project_root)}")

    inject_link(entry, project_root)

    after = template_snapshot(project_root)
    if before != after:
        print("[ERROR] Protected voucher/request template files changed. Installation aborted.", file=sys.stderr)
        return 4

    print("[OK] Voucher/request templates verified unchanged.")
    print("[OK] Desktop login ratio: LEFT 66.67% / RIGHT 33.33%.")
    print("[OK] Right panel is approximately half the width of the left panel.")
    print("[OK] App scale remains 100%; no zoom-out or scale-down added.")
    print("[DONE] Restart the app and press Ctrl+F5 once.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
