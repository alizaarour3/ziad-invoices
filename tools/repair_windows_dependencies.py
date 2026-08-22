from __future__ import annotations

import compileall
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
REQ = ROOT / "requirements.txt"
HOTFIX_REQ = ROOT / "requirements-hotfix.txt"
START = ROOT / "start.py"
APP = ROOT / "app"
PDF_SERVICE = APP / "services" / "pdf_service.py"


def log(message: str) -> None:
    print(f"[Ziad Invoices] {message}", flush=True)


def fail(message: str, code: int = 1) -> int:
    print(f"[ERROR] {message}", file=sys.stderr, flush=True)
    return code


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    log("Running: " + " ".join(args))
    return subprocess.run(args, cwd=ROOT, text=True, check=check)


def normalize_package_line(line: str) -> str:
    line = line.strip().lower()
    if not line or line.startswith("#"):
        return ""
    for token in ("==", ">=", "<=", "~=", "!=", ">", "<", "[", ";", " @ "):
        if token in line:
            line = line.split(token, 1)[0]
    return line.strip().replace("_", "-")


def ensure_requirements_entry() -> None:
    dep = "beautifulsoup4>=4.12,<5"
    if not REQ.exists():
        log("requirements.txt was not found; creating it without touching application code.")
        REQ.write_text(dep + "\n", encoding="utf-8")
        return

    text = REQ.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    packages = {normalize_package_line(line) for line in lines}
    if "beautifulsoup4" in packages:
        log("beautifulsoup4 is already declared in requirements.txt.")
        return

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = REQ.with_name(f"requirements.txt.backup-{stamp}")
    backup.write_text(text, encoding="utf-8")
    suffix = "" if text.endswith("\n") or not text else "\n"
    REQ.write_text(text + suffix + "\n# PDF HTML parsing / Arabic print bundle\n" + dep + "\n", encoding="utf-8")
    log(f"Added {dep} to requirements.txt. Backup: {backup.name}")


def validate_layout() -> None:
    missing = [str(p.relative_to(ROOT)) for p in (START, APP, PDF_SERVICE) if not p.exists()]
    if missing:
        raise RuntimeError(
            "This hotfix must be extracted into the Ziad Invoices project root. Missing: "
            + ", ".join(missing)
        )


def install_dependencies() -> None:
    # Install only the dependency responsible for the supplied traceback.
    # Reinstalling the whole requirements file here could disturb already-working
    # Windows packages (for example PDF/native-library integrations).
    run([sys.executable, "-m", "pip", "install", "-r", str(HOTFIX_REQ)])


def verify_runtime() -> None:
    check = (
        "from bs4 import BeautifulSoup; "
        "import bs4, uvicorn; "
        "print('BeautifulSoup OK:', getattr(bs4, '__version__', 'installed')); "
        "print('Uvicorn OK:', getattr(uvicorn, '__version__', 'installed'))"
    )
    run([sys.executable, "-c", check])

    if not compileall.compile_file(str(START), quiet=1):
        raise RuntimeError("start.py failed Python compilation")
    if not compileall.compile_dir(str(APP), quiet=1):
        raise RuntimeError("one or more files under app/ failed Python compilation")
    log("Python syntax verification passed for start.py and app/.")


def main() -> int:
    try:
        os.chdir(ROOT)
        validate_layout()
        ensure_requirements_entry()
        install_dependencies()
        verify_runtime()
    except subprocess.CalledProcessError as exc:
        return fail(f"A dependency command failed with exit code {exc.returncode}.")
    except Exception as exc:
        return fail(str(exc))

    log("Dependency repair completed successfully.")
    log("You can now run START-ZIAD-INVOICES-SAFE.bat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
