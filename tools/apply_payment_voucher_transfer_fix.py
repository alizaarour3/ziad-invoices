from __future__ import annotations

from pathlib import Path
import json
import re
import shutil
import sqlite3
import sys
import time

PATCH_VERSION = "3.3.24"
MARKER = "ziad-pv-pr-fix-v3.3.24"
HERE = Path(__file__).resolve().parent.parent


def locate_root() -> Path:
    candidates = [HERE, HERE.parent, Path.cwd()]
    candidates += list(HERE.parents[:3])
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            candidate = candidate.resolve()
        except Exception:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "app").is_dir():
            return candidate
    return HERE


ROOT = locate_root()
STATIC = ROOT / "app" / "static"
CSS_FILE = STATIC / "ziad-payment-voucher-fix.css"
JS_FILE = STATIC / "ziad-payment-voucher-fix.js"

# The offsets below are taken from the exact A4 Payment Voucher version where
# typed text sits above the printed ruled lines. Values are percentages of the
# 297 mm A4 page height.
FIELD_TARGET_Y = {
    "pay_to": 44.98,        # -0.85 mm
    "purpose": 52.60,       # -1.25 mm
    "written_amount": 72.86,# -1.30 mm
    "receiver_name": 90.35, # -0.75 mm
    "accountant": 90.35,    # -0.75 mm
    "approval": 90.35,      # -0.75 mm
}
FIELD_CANONICAL_Y = {
    "pay_to": 45.27,
    "purpose": 53.02,
    "written_amount": 73.30,
    "receiver_name": 90.60,
    "accountant": 90.60,
    "approval": 90.60,
}

CSS = r'''/* ziad-pv-pr-fix-v3.3.24
   Payment Voucher: exact above-line typing + footer sentence removal.
*/

/* Legacy/standalone Payment Voucher templates that use the historical IDs/classes. */
html.ziad-pv-active #payto,
html.ziad-pv-active .pay-line {
  transform: translateY(-0.85mm) !important;
}

html.ziad-pv-active #purpose,
html.ziad-pv-active .purpose-input,
html.ziad-pv-active textarea.purpose {
  transform: translateY(-1.25mm) !important;
}

html.ziad-pv-active #written,
html.ziad-pv-active .written-input,
html.ziad-pv-active textarea.written {
  transform: translateY(-1.30mm) !important;
}

html.ziad-pv-active .sig-input,
html.ziad-pv-active .signature.field {
  transform: translateY(-0.75mm) !important;
}

/* Runtime fallback classes are added only when an element is still at the old Y position. */
html.ziad-pv-active .ziad-pv-shift-payto { transform: translateY(-0.85mm) !important; }
html.ziad-pv-active .ziad-pv-shift-purpose { transform: translateY(-1.25mm) !important; }
html.ziad-pv-active .ziad-pv-shift-written { transform: translateY(-1.30mm) !important; }
html.ziad-pv-active .ziad-pv-shift-signature { transform: translateY(-0.75mm) !important; }

/* The requested footer sentence is baked into some older voucher backgrounds.
   This narrow mask removes the sentence but intentionally leaves the round seal/icon on the far right visible. */
.ziad-pv-page-container > .ziad-pv-footer-mask {
  position: absolute !important;
  left: 58.2% !important;
  right: 5.35% !important;
  bottom: 1.00% !important;
  height: 1.55% !important;
  z-index: 3 !important;
  display: block !important;
  background: #fff !important;
  border: 0 !important;
  box-shadow: none !important;
  pointer-events: none !important;
  user-select: none !important;
  -webkit-print-color-adjust: exact !important;
  print-color-adjust: exact !important;
}

@media print {
  .ziad-pv-page-container > .ziad-pv-footer-mask {
    display: block !important;
    background: #fff !important;
  }
}
'''

JS = r'''/* ziad-pv-pr-fix-v3.3.24 */
(() => {
  "use strict";

  const STORAGE_KEY = "ziad-pr-to-pv-v3.3.24";
  const MAX_AGE_MS = 30 * 60 * 1000;
  const FOOTER_RE = /طباعة\s*وتصميم\s*مكتبة\s*النبأ\s*العظيم|07828731227/i;

  const aliases = {
    document_number: ["document_number", "pr_number", "no_pr", "no-pr", "prnumber"],
    date: ["date", "document_date"],
    reference: ["reference", "ref"],
    requester_name: ["requester_name", "requester", "name_of_requester"],
    department: ["department", "dept"],
    pay_to: ["pay_to", "payto", "pay-to"],
    purpose: ["purpose", "description_of_purpose", "description"],
    payment_cash: ["payment_cash", "cash"],
    payment_bank: ["payment_bank", "bank"],
    payment_transfer: ["payment_transfer", "transfer"],
    amount: ["amount"],
    currency: ["currency", "currancy"],
    written_amount: ["written_amount", "written", "amount_in_words"],
    prepared_by: ["prepared_by", "prepared_signature", "prepared"],
    verified_by: ["verified_by", "manager_signature", "verified", "line_manager"],
    approval: ["approval", "approval_signature"],
    payment_request: ["payment_request", "request", "payment-request"],
    receiver_name: ["receiver_name", "receiver", "name_of_receiver"],
    accountant: ["accountant", "accounts"]
  };

  const normalizedAlias = new Map();
  function norm(v) {
    return String(v || "")
      .trim()
      .toLowerCase()
      .replace(/[\s./\\:-]+/g, "_")
      .replace(/[^\w\u0600-\u06ff]+/g, "_")
      .replace(/^_+|_+$/g, "");
  }
  Object.entries(aliases).forEach(([canonical, vals]) => {
    vals.concat([canonical]).forEach(v => normalizedAlias.set(norm(v), canonical));
  });

  function textOf(el) {
    return ((el && (el.innerText || el.textContent)) || "").replace(/\s+/g, " ").trim();
  }

  function keyCandidates(el) {
    if (!el) return [];
    return [
      el.dataset && el.dataset.fieldKey,
      el.dataset && el.dataset.key,
      el.dataset && el.dataset.save,
      el.dataset && el.dataset.field,
      el.getAttribute && el.getAttribute("name"),
      el.getAttribute && el.getAttribute("id"),
      el.getAttribute && el.getAttribute("aria-label"),
      el.getAttribute && el.getAttribute("title")
    ].filter(Boolean);
  }

  function canonicalKey(el) {
    for (const raw of keyCandidates(el)) {
      const n = norm(raw);
      if (normalizedAlias.has(n)) return normalizedAlias.get(n);
      // Allow keys such as field-purpose or document_purpose.
      for (const [alias, canonical] of normalizedAlias.entries()) {
        if (alias.length >= 4 && (n === alias || n.endsWith("_" + alias) || n.startsWith(alias + "_"))) {
          return canonical;
        }
      }
    }
    return null;
  }

  function allFields() {
    return [...document.querySelectorAll(
      'input, textarea, select, [contenteditable="true"], [data-field-key], [data-key], [data-save], [data-field]'
    )];
  }

  function fieldFor(canonical) {
    const fields = allFields();
    return fields.find(el => canonicalKey(el) === canonical) || null;
  }

  function readValue(el) {
    if (!el) return "";
    if (el.type === "checkbox" || el.type === "radio") return !!el.checked;
    if (el.isContentEditable) return textOf(el);
    if ("value" in el) return String(el.value ?? "").trim();
    return textOf(el);
  }

  function isBlank(v) {
    return v === null || v === undefined || v === "" || (typeof v === "string" && !v.trim());
  }

  function setNativeValue(el, value) {
    if (!el) return false;
    if (el.type === "checkbox" || el.type === "radio") {
      const checked = !!value;
      if (el.checked === checked) return false;
      el.checked = checked;
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }

    const str = value == null ? "" : String(value);
    if (el.isContentEditable) {
      if (textOf(el) === str.trim()) return false;
      el.textContent = str;
    } else if ("value" in el) {
      if (String(el.value ?? "") === str) return false;
      const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype :
                    el.tagName === "SELECT" ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
      const desc = Object.getOwnPropertyDescriptor(proto, "value");
      if (desc && desc.set) desc.set.call(el, str);
      else el.value = str;
    } else {
      return false;
    }

    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    try { el.dispatchEvent(new Event("blur", { bubbles: false })); } catch (_) {}
    return true;
  }

  function hasKey(k) { return !!fieldFor(k); }

  function isPaymentRequestPage() {
    const body = textOf(document.body);
    const byFields = hasKey("pay_to") && hasKey("purpose") &&
      (hasKey("requester_name") || hasKey("department")) &&
      (hasKey("payment_cash") || hasKey("payment_bank") || hasKey("payment_transfer"));
    return byFields || ((body.includes("Payment Request") || body.includes("طلب صرف")) && !body.includes("Payment Voucher"));
  }

  function isPaymentVoucherPage() {
    const body = textOf(document.body);
    const byFields = hasKey("payment_request") && hasKey("pay_to") && hasKey("purpose") &&
      (hasKey("receiver_name") || hasKey("accountant"));
    return byFields || body.includes("Payment Voucher") || body.includes("مستند الدفع") || body.includes("سند الدفع");
  }

  function collectPR() {
    const keys = [
      "document_number", "date", "reference", "requester_name", "department", "pay_to", "purpose",
      "payment_cash", "payment_bank", "payment_transfer", "amount", "currency", "written_amount",
      "prepared_by", "verified_by", "approval"
    ];
    const values = {};
    keys.forEach(k => {
      const el = fieldFor(k);
      if (el) values[k] = readValue(el);
    });
    if (!Object.keys(values).length) return null;
    return { version: "3.3.24", captured_at: Date.now(), values };
  }

  function savePRSnapshot() {
    if (!isPaymentRequestPage()) return;
    const payload = collectPR();
    if (!payload) return;
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload)); } catch (_) {}
  }

  function loadPRSnapshot() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const payload = JSON.parse(raw);
      if (!payload || !payload.values || !payload.captured_at) return null;
      if (Date.now() - Number(payload.captured_at) > MAX_AGE_MS) {
        sessionStorage.removeItem(STORAGE_KEY);
        return null;
      }
      return payload;
    } catch (_) {
      return null;
    }
  }

  function applyPRToPV() {
    if (!isPaymentVoucherPage()) return false;
    const payload = loadPRSnapshot();
    if (!payload) return false;
    const src = payload.values || {};
    const prNo = String(src.document_number || "").trim();
    const requestEl = fieldFor("payment_request");
    const existingRequest = String(readValue(requestEl) || "").trim();

    // Prevent an old PR snapshot from touching an unrelated existing voucher.
    if (existingRequest && prNo && existingRequest !== prNo) return false;

    // Exact PR -> Payment Voucher transfer requested for Ziad Invoices v3.3.24.
    // Only these six fields are copied. No date, reference, PR number, requester,
    // department, payment method, prepared-by, verified-by, or other field is moved.
    const map = [
      ["pay_to", "pay_to"],
      ["purpose", "purpose"],
      ["amount", "amount"],
      ["currency", "currency"],
      ["written_amount", "written_amount"],
      ["approval", "approval"]
    ];

    let changed = false;
    for (const [from, to] of map) {
      const value = src[from];
      if (isBlank(value) || value === false) continue;
      const target = fieldFor(to);
      if (!target) continue;
      // For an actual PR -> PV conversion, the PR is the source of truth for
      // these six mapped fields. Replace stale/default PV values with the PR value.
      changed = setNativeValue(target, value) || changed;
    }

    if (changed || (requestEl && (readValue(requestEl) === prNo))) {
      try { sessionStorage.removeItem(STORAGE_KEY); } catch (_) {}
      document.documentElement.dataset.ziadPrToPv = "applied";
    }
    return changed;
  }

  function candidatePageContainer() {
    const anchor = fieldFor("pay_to") || fieldFor("purpose") || document.querySelector("#voucherPage");
    if (!anchor) return document.querySelector("#voucherPage, .document-page, .template-page, .page");
    const candidates = [];
    let cur = anchor.parentElement;
    while (cur && cur !== document.body) {
      const r = cur.getBoundingClientRect();
      if (r.width >= 300 && r.height >= 420) {
        const ratio = r.width / r.height;
        const score = Math.abs(ratio - 0.7071) + Math.abs(r.height - innerHeight * 0.85) / Math.max(r.height, 1) * 0.02;
        candidates.push({ el: cur, score });
      }
      cur = cur.parentElement;
    }
    if (candidates.length) return candidates.sort((a, b) => a.score - b.score)[0].el;
    return document.querySelector("#voucherPage, .document-page, .template-page, .page");
  }

  function removeFooterSentence() {
    if (!isPaymentVoucherPage()) return;

    // Remove it directly when it is an HTML text layer.
    document.querySelectorAll("body *").forEach(el => {
      if (el.children.length) return;
      const t = textOf(el);
      if (t && FOOTER_RE.test(t) && t.length < 140) {
        el.style.setProperty("visibility", "hidden", "important");
      }
    });

    // Older official templates contain the sentence in the background itself.
    const page = candidatePageContainer();
    if (!page) return;
    page.classList.add("ziad-pv-page-container");
    const cs = getComputedStyle(page);
    if (cs.position === "static") page.style.position = "relative";
    if (!page.querySelector(":scope > .ziad-pv-footer-mask")) {
      const mask = document.createElement("div");
      mask.className = "ziad-pv-footer-mask";
      mask.setAttribute("aria-hidden", "true");
      page.appendChild(mask);
    }
  }

  const expectedOld = {
    pay_to: 45.27,
    purpose: 53.02,
    written_amount: 73.30,
    receiver_name: 90.60,
    accountant: 90.60,
    approval: 90.60
  };
  const expectedTarget = {
    pay_to: 44.98,
    purpose: 52.60,
    written_amount: 72.86,
    receiver_name: 90.35,
    accountant: 90.35,
    approval: 90.35
  };

  function topPercent(el, page) {
    const raw = (el.style && el.style.top) || "";
    if (raw.endsWith("%")) {
      const n = parseFloat(raw);
      if (Number.isFinite(n)) return n;
    }
    if (!page) return null;
    const er = el.getBoundingClientRect();
    const pr = page.getBoundingClientRect();
    if (!pr.height) return null;
    return ((er.top - pr.top) / pr.height) * 100;
  }

  function runtimeAlignmentFallback() {
    if (!isPaymentVoucherPage()) return;
    document.documentElement.classList.add("ziad-pv-active");
    const page = candidatePageContainer();
    const spec = [
      ["pay_to", "ziad-pv-shift-payto"],
      ["purpose", "ziad-pv-shift-purpose"],
      ["written_amount", "ziad-pv-shift-written"],
      ["receiver_name", "ziad-pv-shift-signature"],
      ["accountant", "ziad-pv-shift-signature"],
      ["approval", "ziad-pv-shift-signature"]
    ];
    for (const [key, cls] of spec) {
      const el = fieldFor(key);
      if (!el || el.id === "payto" || el.id === "purpose" || el.id === "written") continue;
      const y = topPercent(el, page);
      if (y == null) continue;
      const oldY = expectedOld[key], targetY = expectedTarget[key];
      // Only shift a still-unpatched legacy/dynamic field; never double-shift the patched config position.
      if (Math.abs(y - targetY) <= 0.13) el.classList.remove(cls);
      else if (Math.abs(y - oldY) <= 0.16) el.classList.add(cls);
    }
  }

  function apply() {
    if (!document.body) return;
    if (isPaymentRequestPage()) savePRSnapshot();
    if (isPaymentVoucherPage()) {
      document.documentElement.classList.add("ziad-pv-active");
      runtimeAlignmentFallback();
      removeFooterSentence();
      applyPRToPV();
    } else {
      document.documentElement.classList.remove("ziad-pv-active");
    }
  }

  function boot() {
    // Capture PR changes continuously so conversion buttons/routes cannot lose the latest values.
    document.addEventListener("input", () => { if (isPaymentRequestPage()) savePRSnapshot(); }, true);
    document.addEventListener("change", () => { if (isPaymentRequestPage()) savePRSnapshot(); }, true);
    document.addEventListener("click", (e) => {
      if (!isPaymentRequestPage()) return;
      const el = e.target && e.target.closest && e.target.closest("button, a, [role=button]");
      if (!el) return;
      const t = textOf(el) + " " + (el.getAttribute("href") || "");
      if (/سند\s*دفع|مستند\s*دفع|payment\s*voucher|\bPV\b|تحويل/i.test(t)) savePRSnapshot();
    }, true);

    apply();
    let queued = false;
    const observer = new MutationObserver(() => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => { queued = false; apply(); });
    });
    observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["value", "class", "style"] });
    window.addEventListener("popstate", apply);
    window.addEventListener("hashchange", apply);
    window.addEventListener("beforeprint", apply);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
'''

LINK = f'<link rel="stylesheet" href="/static/ziad-payment-voucher-fix.css" data-fix="{MARKER}">'
SCRIPT = f'<script defer src="/static/ziad-payment-voucher-fix.js" data-fix="{MARKER}"></script>'


def log(msg: str) -> None:
    print(f"[Ziad Invoices] {msg}", flush=True)


def skip_path(path: Path) -> bool:
    parts = {p.lower() for p in path.parts}
    return bool(parts & {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}) or ".backup-" in path.name


def backup(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_name(path.name + f".backup-v{PATCH_VERSION}-{stamp}")
    shutil.copy2(path, dst)
    return dst


def patch_pv_config_obj(obj: object) -> int:
    changed = 0
    if isinstance(obj, dict):
        if str(obj.get("code", "")).upper() == "PV" and isinstance(obj.get("fields"), list):
            for field in obj["fields"]:
                if not isinstance(field, dict):
                    continue
                key = str(field.get("key", ""))
                if key not in FIELD_TARGET_Y:
                    continue
                try:
                    old_y = float(field.get("y"))
                except (TypeError, ValueError):
                    continue
                target = FIELD_TARGET_Y[key]
                canonical = FIELD_CANONICAL_Y[key]
                # Respect a custom placement that is far away from the known official template.
                if abs(old_y - canonical) > 0.90 and abs(old_y - target) > 0.15:
                    continue
                delta = target - old_y
                if abs(delta) <= 0.005:
                    continue
                field["y"] = round(target, 2)
                if isinstance(field.get("line_positions"), list):
                    field["line_positions"] = [round(float(v) + delta, 2) for v in field["line_positions"]]
                if isinstance(field.get("line_boxes"), list):
                    for box in field["line_boxes"]:
                        if isinstance(box, dict) and isinstance(box.get("y"), (int, float)):
                            box["y"] = round(float(box["y"]) + delta, 2)
                changed += 1
        for value in obj.values():
            changed += patch_pv_config_obj(value)
    elif isinstance(obj, list):
        for value in obj:
            changed += patch_pv_config_obj(value)
    return changed


def patch_json_file(path: Path) -> int:
    try:
        raw = path.read_text(encoding="utf-8-sig")
        data = json.loads(raw)
    except Exception:
        return 0
    count = patch_pv_config_obj(data)
    if not count:
        return 0
    b = backup(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"Aligned PV config in {path.relative_to(ROOT)} ({count} fields; backup: {b.name})")
    return count


def patch_sql_file(path: Path) -> int:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except Exception:
        return 0
    if "$cfg_PV$" not in raw:
        return 0
    total = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal total
        blob = match.group(1)
        try:
            data = json.loads(blob)
        except Exception:
            return match.group(0)
        count = patch_pv_config_obj(data)
        if not count:
            return match.group(0)
        total += count
        compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return "$cfg_PV$" + compact + "$cfg_PV$"

    out = re.sub(r"\$cfg_PV\$(\{.*?\})\$cfg_PV\$", repl, raw, flags=re.DOTALL)
    if not total or out == raw:
        return 0
    b = backup(path)
    path.write_text(out, encoding="utf-8")
    log(f"Aligned PV SQL seed in {path.relative_to(ROOT)} ({total} fields; backup: {b.name})")
    return total


def sqlite_backup(conn: sqlite3.Connection, path: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_name(path.name + f".backup-v{PATCH_VERSION}-{stamp}")
    bconn = sqlite3.connect(dst)
    try:
        conn.backup(bconn)
    finally:
        bconn.close()
    return dst


def patch_sqlite_db(path: Path) -> int:
    if skip_path(path):
        return 0
    try:
        conn = sqlite3.connect(path, timeout=2.0)
    except Exception:
        return 0
    try:
        table = conn.execute("select name from sqlite_master where type='table' and name='document_types'").fetchone()
        if not table:
            return 0
        row = conn.execute("select id, config_json from document_types where upper(code)='PV' limit 1").fetchone()
        if not row:
            return 0
        doc_id, config_raw = row
        data = json.loads(config_raw)
        count = patch_pv_config_obj(data)
        if not count:
            return 0
        b = sqlite_backup(conn, path)
        conn.execute("update document_types set config_json=? where id=?", (json.dumps(data, ensure_ascii=False, separators=(",", ":")), doc_id))
        conn.commit()
        log(f"Aligned current SQLite PV config in {path.relative_to(ROOT)} ({count} fields; backup: {b.name})")
        return count
    except Exception as exc:
        log(f"Skipped SQLite database {path.relative_to(ROOT)}: {exc}")
        return 0
    finally:
        conn.close()


def remove_literal_footer_from_html(path: Path) -> int:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except Exception:
        return 0
    if not any(x in raw for x in ("Payment Voucher", "مستند الدفع", "سند الدفع", "payment_voucher", "payment-voucher")):
        return 0
    out = raw
    # Remove only the known printing/design sentence and its phone number when present as a text layer.
    out = re.sub(r"طباعة\s*وتصميم\s*مكتبة\s*النبأ\s*العظيم\s*07828731227", "", out)
    out = re.sub(r"طباعة\s*وتصميم\s*مكتبة\s*النبأ\s*العظيم", "", out)
    if out == raw:
        return 0
    b = backup(path)
    path.write_text(out, encoding="utf-8")
    log(f"Removed literal PV footer sentence from {path.relative_to(ROOT)} (backup: {b.name})")
    return 1


def inject_html(path: Path) -> bool:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except Exception:
        return False
    if MARKER in raw or "ziad-payment-voucher-fix.js" in raw:
        return False
    lower = raw.lower()
    out = raw
    if "</head>" in lower:
        idx = lower.rfind("</head>")
        out = out[:idx] + "  " + LINK + "\n" + out[idx:]
    else:
        out = LINK + "\n" + out
    lower2 = out.lower()
    if "</body>" in lower2:
        idx = lower2.rfind("</body>")
        out = out[:idx] + "  " + SCRIPT + "\n" + out[idx:]
    else:
        out += "\n" + SCRIPT + "\n"
    b = backup(path)
    path.write_text(out, encoding="utf-8")
    log(f"Injected PV/PR runtime fix into {path.relative_to(ROOT)} (backup: {b.name})")
    return True


def main() -> int:
    log(f"Project root: {ROOT}")
    if not (ROOT / "app").exists():
        print("[ERROR] app/ was not found. Extract this patch into the Ziad Invoices project root.", file=sys.stderr)
        return 1

    STATIC.mkdir(parents=True, exist_ok=True)
    CSS_FILE.write_text(CSS, encoding="utf-8")
    JS_FILE.write_text(JS, encoding="utf-8")
    log("Installed app/static/ziad-payment-voucher-fix.css")
    log("Installed app/static/ziad-payment-voucher-fix.js")

    config_fields = 0
    for path in ROOT.rglob("templates.json"):
        if not skip_path(path):
            config_fields += patch_json_file(path)

    sql_fields = 0
    for path in ROOT.rglob("*.sql"):
        if not skip_path(path):
            sql_fields += patch_sql_file(path)

    db_fields = 0
    db_candidates: list[Path] = []
    for pattern in ("*.db", "*.sqlite", "*.sqlite3"):
        db_candidates.extend(ROOT.rglob(pattern))
    for path in sorted(set(db_candidates)):
        if path.is_file() and path.stat().st_size < 500 * 1024 * 1024:
            db_fields += patch_sqlite_db(path)

    html_files = [p for p in STATIC.rglob("*.html") if not skip_path(p)]
    literal_removed = sum(remove_literal_footer_from_html(p) for p in html_files)

    # Inject into the SPA entry file(s) and standalone PR/PV templates.
    targets: list[Path] = []
    for p in html_files:
        try:
            s = p.read_text(encoding="utf-8-sig")
        except Exception:
            continue
        name = p.name.lower()
        if name in {"index.html", "app.html", "main.html"} or any(term in s for term in ("Payment Voucher", "Payment Request", "مستند الدفع", "طلب صرف")):
            targets.append(p)
    if not targets:
        targets = html_files
    injected = 0
    for p in sorted(set(targets)):
        injected += 1 if inject_html(p) else 0

    log("------------------------------------------------------------")
    log(f"PV fields aligned in JSON config: {config_fields}")
    log(f"PV fields aligned in SQL seed: {sql_fields}")
    log(f"PV fields aligned in current SQLite DB: {db_fields}")
    log(f"Literal footer text layers removed: {literal_removed}")
    log(f"HTML files injected: {injected}")
    log("PR -> PV carry-over is restricted to the exact six requested fields: pay_to, purpose, amount, currency, written_amount, approval.")
    log("Done. Restart Ziad Invoices and test one new PR -> PV conversion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
