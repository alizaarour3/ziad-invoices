from __future__ import annotations
import threading, time, webbrowser
import uvicorn
from app.settings import HOST, PORT

def run_server():
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False, log_level="warning")

if __name__ == "__main__":
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start(); time.sleep(1.2)
    url=f"http://{HOST}:{PORT}"
    try:
        import webview
        webview.create_window("Ziad Invoices Professional", url, width=1440, height=900, min_size=(1100,700))
        webview.start()
    except Exception:
        webbrowser.open(url)
        try:
            while thread.is_alive(): time.sleep(1)
        except KeyboardInterrupt:
            pass
