from __future__ import annotations

import threading
import time
import webbrowser

import uvicorn

from app.settings import HOST, PORT


def open_browser() -> None:
    time.sleep(1.2)
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("app.runtime_entry:app", host=HOST, port=PORT, reload=False, log_level="info")
