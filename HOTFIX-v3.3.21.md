# Ziad Invoices Professional v3.3.21 - Windows Startup Dependency Fix

## Fixed

- Fixes `ModuleNotFoundError: No module named 'bs4'` raised by `app/services/pdf_service.py`.
- Adds `beautifulsoup4>=4.12,<5` to the existing `requirements.txt` without deleting any existing dependency.
- Creates a timestamped backup of `requirements.txt` before changing it.
- Uses `.venv\Scripts\python.exe` explicitly, avoiding accidental launcher use of another Python installation.
- Reinstalls/verifies the full project requirements and the BeautifulSoup dependency.
- Verifies `bs4` and `uvicorn` imports.
- Compiles `start.py` and the `app/` package to catch Python syntax errors before launch.

## Apply

Extract these files directly into the Ziad Invoices project root (the same folder containing `start.py`, `requirements.txt`, and `app`). Then double-click:

`APPLY-WINDOWS-DEPENDENCY-FIX.bat`

After the repair reports success, use:

`START-ZIAD-INVOICES-SAFE.bat`

The safe launcher will automatically re-run the repair if the virtual environment or required imports are missing.

## Scope

This patch does not replace invoice templates, application data, Supabase configuration, UI files, or business logic. It only repairs the Windows Python dependency/startup layer that caused the supplied traceback.
