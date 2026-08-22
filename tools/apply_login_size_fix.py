from __future__ import annotations

from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "app" / "static"
CSS_FILE = STATIC / "ziad-login-size-fix.css"
JS_FILE = STATIC / "ziad-login-size-fix.js"
MARKER = "ziad-login-size-fix-v3.3.22"

CSS = r'''/* ziad-login-size-fix-v3.3.22
   Login page size lock: normal 100% visual scale, full viewport, no app-level zoom-out.
*/
html.ziad-login-size-lock,
html.ziad-login-size-lock body {
  width: 100% !important;
  min-width: 100% !important;
  min-height: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
  zoom: 1 !important;
}

html.ziad-login-size-lock body {
  width: 100vw !important;
  min-height: 100vh !important;
  overflow-x: hidden !important;
}

/* The main two-column login shell must fill the real browser viewport. */
html.ziad-login-size-lock .ziad-login-layout-lock {
  width: 100vw !important;
  max-width: none !important;
  min-width: 100vw !important;
  min-height: 100vh !important;
  height: 100vh !important;
  margin: 0 !important;
  zoom: 1 !important;
  transform: none !important;
  transform-origin: 50% 50% !important;
}

/* Match the supplied desktop reference proportions: about 56.4% visual / 43.6% login. */
@media (min-width: 1000px) {
  html.ziad-login-size-lock .ziad-login-left-lock {
    width: 56.4% !important;
    flex: 0 0 56.4% !important;
    max-width: 56.4% !important;
    min-height: 100vh !important;
    height: 100vh !important;
  }

  html.ziad-login-size-lock .ziad-login-right-lock {
    width: 43.6% !important;
    flex: 0 0 43.6% !important;
    max-width: 43.6% !important;
    min-height: 100vh !important;
    height: 100vh !important;
  }
}

/* Keep the actual login controls large; do not shrink them to fit. */
html.ziad-login-size-lock .ziad-login-form-lock {
  width: min(586px, calc(100% - 72px)) !important;
  max-width: 586px !important;
  min-width: 0 !important;
  zoom: 1 !important;
  transform: none !important;
}

html.ziad-login-size-lock .ziad-login-form-lock input[type="text"],
html.ziad-login-size-lock .ziad-login-form-lock input[type="email"],
html.ziad-login-size-lock .ziad-login-form-lock input[type="password"] {
  min-height: 68px !important;
  height: 68px !important;
  font-size: 18px !important;
  box-sizing: border-box !important;
}

html.ziad-login-size-lock .ziad-login-form-lock button,
html.ziad-login-size-lock .ziad-login-form-lock input[type="submit"] {
  min-height: 68px !important;
  height: 68px !important;
  font-size: 20px !important;
}

/* Do not let a responsive rule make the whole page smaller on common laptop widths. */
@media (min-width: 1000px) and (max-width: 1600px) {
  html.ziad-login-size-lock .ziad-login-form-lock {
    width: min(560px, calc(100% - 56px)) !important;
  }
}

/* Mobile/tablet remains responsive and scrollable. */
@media (max-width: 999px) {
  html.ziad-login-size-lock body {
    overflow-y: auto !important;
  }
  html.ziad-login-size-lock .ziad-login-layout-lock {
    width: 100% !important;
    min-width: 0 !important;
    height: auto !important;
    min-height: 100vh !important;
  }
  html.ziad-login-size-lock .ziad-login-form-lock {
    width: min(586px, calc(100% - 32px)) !important;
  }
}
'''

JS = r'''/* ziad-login-size-fix-v3.3.22 */
(() => {
  "use strict";

  const LOGIN_WORDS = ["تسجيل الدخول", "اسم المستخدم", "كلمة المرور"];

  function textOf(el) {
    return ((el && el.innerText) || "").replace(/\s+/g, " ").trim();
  }

  function isLoginScreen() {
    const t = textOf(document.body);
    return LOGIN_WORDS.every((word) => t.includes(word));
  }

  function parseScale(transform) {
    if (!transform || transform === "none") return 1;
    try {
      const m = new DOMMatrixReadOnly(transform);
      const sx = Math.hypot(m.a, m.b);
      const sy = Math.hypot(m.c, m.d);
      return Math.min(sx || 1, sy || 1);
    } catch (_) {
      return 1;
    }
  }

  function removeShrink(el) {
    if (!el) return;
    const cs = getComputedStyle(el);
    const zoom = parseFloat(cs.zoom || "1") || 1;
    if (zoom > 0 && zoom < 0.98) {
      el.style.setProperty("zoom", "1", "important");
    }
    const scale = parseScale(cs.transform);
    if (scale > 0 && scale < 0.98) {
      el.style.setProperty("transform", "none", "important");
      el.style.setProperty("transform-origin", "50% 50%", "important");
    }
  }

  function directChildContaining(parent, node) {
    if (!parent || !node) return null;
    let cur = node;
    while (cur && cur.parentElement && cur.parentElement !== parent) {
      cur = cur.parentElement;
    }
    return cur && cur.parentElement === parent ? cur : null;
  }

  function commonTwoPaneLayout(form) {
    const candidates = [];
    let el = form;
    while (el && el !== document.body) {
      const parent = el.parentElement;
      if (!parent) break;
      const children = [...parent.children].filter((c) => {
        const r = c.getBoundingClientRect();
        return r.width > 100 && r.height > innerHeight * 0.45;
      });
      if (children.length >= 2) {
        const formChild = directChildContaining(parent, form);
        if (formChild) {
          const sibling = children.find((c) => c !== formChild);
          if (sibling) candidates.push({ parent, right: formChild, left: sibling });
        }
      }
      el = parent;
    }
    if (!candidates.length) return null;
    return candidates.sort((a, b) => {
      const ar = a.parent.getBoundingClientRect();
      const br = b.parent.getBoundingClientRect();
      const as = Math.abs(ar.width - innerWidth) + Math.abs(ar.height - innerHeight);
      const bs = Math.abs(br.width - innerWidth) + Math.abs(br.height - innerHeight);
      return as - bs;
    })[0];
  }

  function findLoginForm() {
    const password = document.querySelector('input[type="password"]');
    if (!password) return null;
    const form = password.closest("form");
    if (form) return form;

    let el = password.parentElement;
    while (el && el !== document.body) {
      const t = textOf(el);
      if (t.includes("تسجيل الدخول") && el.querySelector("button, input[type=submit]")) return el;
      el = el.parentElement;
    }
    return password.parentElement;
  }

  function apply() {
    if (!document.body || !isLoginScreen()) return;

    document.documentElement.classList.add("ziad-login-size-lock");
    document.documentElement.style.setProperty("zoom", "1", "important");
    document.body.style.setProperty("zoom", "1", "important");

    const form = findLoginForm();
    if (!form) return;
    form.classList.add("ziad-login-form-lock");

    // Remove only detected shrinking transforms/zoom from the login ancestors.
    let cur = form;
    while (cur && cur !== document.documentElement) {
      removeShrink(cur);
      cur = cur.parentElement;
    }

    const layout = commonTwoPaneLayout(form);
    if (layout) {
      layout.parent.classList.add("ziad-login-layout-lock");
      layout.right.classList.add("ziad-login-right-lock");
      layout.left.classList.add("ziad-login-left-lock");
      removeShrink(layout.parent);
      removeShrink(layout.left);
      removeShrink(layout.right);
    }
  }

  function boot() {
    apply();
    // SPA/login DOM can be rendered after page load; re-apply on DOM changes.
    const observer = new MutationObserver(() => apply());
    observer.observe(document.documentElement, { childList: true, subtree: true });
    window.addEventListener("resize", apply, { passive: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
'''

LINK = '<link rel="stylesheet" href="/static/ziad-login-size-fix.css" data-fix="ziad-login-size-fix-v3.3.22">'
SCRIPT = '<script defer src="/static/ziad-login-size-fix.js" data-fix="ziad-login-size-fix-v3.3.22"></script>'


def log(msg: str) -> None:
    print(f"[Ziad Invoices] {msg}", flush=True)


def backup(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_name(path.name + f".backup-{stamp}")
    shutil.copy2(path, dst)
    return dst


def inject_html(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8-sig")
    if MARKER in raw or "ziad-login-size-fix.css" in raw:
        return False

    out = raw
    if "</head>" in out.lower():
        idx = out.lower().rfind("</head>")
        out = out[:idx] + "  " + LINK + "\n" + out[idx:]
    else:
        out = LINK + "\n" + out

    if "</body>" in out.lower():
        idx = out.lower().rfind("</body>")
        out = out[:idx] + "  " + SCRIPT + "\n" + out[idx:]
    else:
        out += "\n" + SCRIPT + "\n"

    b = backup(path)
    path.write_text(out, encoding="utf-8")
    log(f"Patched {path.relative_to(ROOT)} (backup: {b.name})")
    return True


def main() -> int:
    if not STATIC.exists():
        print("[ERROR] app/static was not found. Extract this patch into the Ziad Invoices project root.", file=sys.stderr)
        return 1

    STATIC.mkdir(parents=True, exist_ok=True)
    CSS_FILE.write_text(CSS, encoding="utf-8")
    JS_FILE.write_text(JS, encoding="utf-8")
    log("Installed app/static/ziad-login-size-fix.css")
    log("Installed app/static/ziad-login-size-fix.js")

    html_files = sorted(STATIC.rglob("*.html"))
    if not html_files:
        print("[ERROR] No HTML entry file was found under app/static.", file=sys.stderr)
        return 2

    # Prefer pages that contain login wording; if the app is an SPA, patch its likely entry page.
    preferred = []
    for p in html_files:
        try:
            s = p.read_text(encoding="utf-8-sig")
        except Exception:
            continue
        if any(word in s for word in ("تسجيل الدخول", "اسم المستخدم", "login", "password")):
            preferred.append(p)

    targets = preferred or [p for p in html_files if p.name.lower() in {"index.html", "app.html", "main.html"}]
    if not targets:
        targets = html_files

    changed = 0
    for p in targets:
        try:
            changed += 1 if inject_html(p) else 0
        except UnicodeDecodeError:
            log(f"Skipped non-UTF8 HTML: {p.relative_to(ROOT)}")

    log(f"Login-size fix ready. HTML files changed: {changed}")
    log("Restart the application and keep the browser at 100% zoom (Ctrl+0).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
