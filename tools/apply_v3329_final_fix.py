from __future__ import annotations

from pathlib import Path
import hashlib
import json
import re
import shutil
import sqlite3
import sys
import time

PATCH_VERSION = "3.3.29"
MARKER = "ziad-pr-pv-final-v3.3.29"
HERE = Path(__file__).resolve().parent.parent

# FINAL, USER-APPROVED PAYMENT REQUEST -> PAYMENT VOUCHER CONTRACT.
# Never change this mapping unless the user explicitly replaces it.
FINAL_MAPPING = {
    "department": "pay_to",
    "pay_to": "purpose:first_line",
    "purpose": "purpose:remaining_lines",
    "amount": "amount",
    "currency": "currency",
    "written_amount": "written_amount",
    "approval": "approval",
    "prepared_by": "receiver_name",
}

# Text-overlay coordinates only. Original voucher HTML/PDF/DOCX artwork is protected.
# These coordinates place text immediately ABOVE the ruled lines when PDF is generated.
PV_TARGET_Y = {
    "pay_to": 44.44,
    "purpose": 52.21,
    "written_amount": 71.94,
    "receiver_name": 88.55,
    "accountant": 88.55,
    "approval": 88.55,
}
PV_PURPOSE_LINES = [52.21, 54.54, 56.88]
PV_WRITTEN_LINES = [71.94, 74.48, 77.03]
PV_KNOWN_Y = {
    "pay_to": (45.27, 44.98, 44.44),
    "purpose": (53.02, 52.60, 52.21),
    "written_amount": (73.30, 72.86, 71.94),
    "receiver_name": (90.60, 90.35, 88.55),
    "accountant": (90.60, 90.35, 88.55),
    "approval": (90.60, 90.35, 88.55),
}

JS = r'''/* ziad-pr-pv-final-v3.3.29
   FINAL user-approved Payment Request -> Payment Voucher mapping.
   This file never changes voucher artwork. It only transfers values.
*/
(() => {
  "use strict";

  const STORAGE_KEY = "ziad-pr-to-pv-final-v3.3.29";
  const FALLBACK_KEY = "ziad-pr-to-pv-final-v3.3.29-fallback";
  const LEGACY_KEYS = [
    "ziad-pr-to-pv-v3.3.27",
    "ziad-pr-to-pv-v3.3.24",
    "ziad-pr-to-pv-v3.3.23"
  ];
  const MAX_AGE_MS = 30 * 60 * 1000;

  const aliases = {
    department: ["department", "dept", "القسم"],
    pay_to: ["pay_to", "payto", "pay-to", "الدفع_إلى", "الدفع_ل", "يدفع_إلى"],
    purpose: ["purpose", "description_of_purpose", "description", "الغرض", "وذلك_عن"],
    amount: ["amount", "المبلغ"],
    currency: ["currency", "currancy", "العملة"],
    written_amount: ["written_amount", "written", "amount_in_words", "المبلغ_كتابة"],
    prepared_by: ["prepared_by", "prepared", "prepared_signature", "requester_name", "اسم_مقدم_الصرف"],
    approval: ["approval", "approval_signature", "الموافقة"],
    receiver_name: ["receiver_name", "receiver", "name_of_receiver", "اسم_المستلم"],
    accountant: ["accountant", "accounts", "المحاسب"]
  };

  const normalizedAlias = new Map();
  function norm(v) {
    return String(v || "").trim().toLowerCase()
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
      for (const [alias, canonical] of normalizedAlias.entries()) {
        if (alias.length >= 4 && (n === alias || n.endsWith("_" + alias) || n.startsWith(alias + "_"))) return canonical;
      }
    }
    return null;
  }
  function allFields() {
    return [...document.querySelectorAll('input, textarea, select, [contenteditable="true"], [data-field-key], [data-key], [data-save], [data-field]')];
  }
  function fieldFor(canonical) { return allFields().find(el => canonicalKey(el) === canonical) || null; }
  function readValue(el) {
    if (!el) return "";
    if (el.type === "checkbox" || el.type === "radio") return !!el.checked;
    if (el.isContentEditable) return ((el.innerText || el.textContent) || "").trim();
    if ("value" in el) return String(el.value ?? "").trim();
    return textOf(el);
  }
  function isBlank(v) { return v === null || v === undefined || v === "" || (typeof v === "string" && !v.trim()); }
  function setNativeValue(el, value) {
    if (!el) return false;
    const str = value == null ? "" : String(value);
    if (el.isContentEditable) {
      if (((el.innerText || el.textContent) || "").trim() === str.trim()) return false;
      el.textContent = str;
    } else if ("value" in el) {
      if (String(el.value ?? "") === str) return false;
      let proto = HTMLInputElement.prototype;
      if (el.tagName === "TEXTAREA") proto = HTMLTextAreaElement.prototype;
      else if (el.tagName === "SELECT") proto = HTMLSelectElement.prototype;
      const desc = Object.getOwnPropertyDescriptor(proto, "value");
      if (desc && desc.set) desc.set.call(el, str); else el.value = str;
    } else return false;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }
  function hasKey(k) { return !!fieldFor(k); }
  function isPaymentRequestPage() {
    const body = textOf(document.body);
    const fields = hasKey("department") && hasKey("pay_to") && hasKey("purpose") && hasKey("amount") && hasKey("prepared_by") && hasKey("approval");
    return fields || ((body.includes("Payment Request") || body.includes("طلب صرف")) && !body.includes("Payment Voucher"));
  }
  function isPaymentVoucherPage() {
    const body = textOf(document.body);
    const fields = hasKey("pay_to") && hasKey("purpose") && hasKey("receiver_name") && hasKey("approval");
    return fields || body.includes("Payment Voucher") || body.includes("مستند الدفع") || body.includes("سند الدفع");
  }

  function collectPR() {
    const keys = ["department", "pay_to", "purpose", "amount", "currency", "written_amount", "prepared_by", "approval"];
    const values = {};
    keys.forEach(k => { const el = fieldFor(k); if (el) values[k] = readValue(el); });
    if (!Object.keys(values).length) return null;
    return { version: "3.3.29", captured_at: Date.now(), values };
  }
  function persistSnapshot(payload) {
    const raw = JSON.stringify(payload);
    try { sessionStorage.setItem(STORAGE_KEY, raw); } catch (_) {}
    try { localStorage.setItem(FALLBACK_KEY, raw); } catch (_) {}
  }
  function savePRSnapshot() {
    if (!isPaymentRequestPage()) return;
    const payload = collectPR();
    if (payload) persistSnapshot(payload);
  }
  function validPayload(raw) {
    if (!raw) return null;
    try {
      const payload = JSON.parse(raw);
      if (!payload || !payload.values || !payload.captured_at) return null;
      if (Date.now() - Number(payload.captured_at) > MAX_AGE_MS) return null;
      return payload;
    } catch (_) { return null; }
  }
  function loadPRSnapshot() {
    let payload = null;
    try { payload = validPayload(sessionStorage.getItem(STORAGE_KEY)); } catch (_) {}
    if (!payload) { try { payload = validPayload(localStorage.getItem(FALLBACK_KEY)); } catch (_) {} }
    if (!payload) {
      for (const key of LEGACY_KEYS) {
        try { payload = validPayload(sessionStorage.getItem(key)); } catch (_) {}
        if (payload) break;
      }
    }
    return payload;
  }
  function clearSnapshot() {
    try { sessionStorage.removeItem(STORAGE_KEY); LEGACY_KEYS.forEach(k => sessionStorage.removeItem(k)); } catch (_) {}
    try { localStorage.removeItem(FALLBACK_KEY); } catch (_) {}
  }

  function composePurpose(src) {
    // FINAL RULE: PR Pay to occupies the first ruled line of PV الغرض/Purpose.
    // PR Description of purpose follows on the remaining ruled lines.
    const payTo = String(src.pay_to || "").trim();
    const description = String(src.purpose || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
    if (payTo && description && description !== payTo) return `${payTo}\n${description}`;
    return payTo || description;
  }

  function applyPRToPV() {
    if (!isPaymentVoucherPage()) return false;
    const payload = loadPRSnapshot();
    if (!payload) return false;
    const src = payload.values || {};
    let changed = false;

    // FINAL MAPPING - DO NOT ADD OR REMOVE FIELDS:
    // PR القسم                   -> PV Pay to
    // PR Pay to                  -> PV الغرض/Purpose first line
    // PR Description of purpose  -> PV الغرض/Purpose remaining lines
    // PR Amount                  -> PV Amount
    // PR Currency                -> PV Currency
    // PR Written Amount          -> PV Written Amount
    // PR Approval                -> PV Approval
    // PR اسم مقدم الصرف          -> PV اسم المستلم
    const directMap = [
      ["department", "pay_to"],
      ["amount", "amount"],
      ["currency", "currency"],
      ["written_amount", "written_amount"],
      ["approval", "approval"],
      ["prepared_by", "receiver_name"]
    ];
    for (const [from, to] of directMap) {
      if (isBlank(src[from])) continue;
      changed = setNativeValue(fieldFor(to), src[from]) || changed;
    }
    const purpose = composePurpose(src);
    if (purpose) changed = setNativeValue(fieldFor("purpose"), purpose) || changed;

    if (changed) {
      clearSnapshot();
      document.documentElement.dataset.ziadPrToPv = "final-v3.3.29-applied";
    }
    return changed;
  }

  const pdfTargetY = { pay_to:44.44, purpose:52.21, written_amount:71.94, receiver_name:88.55, accountant:88.55, approval:88.55 };
  const knownOldY = {
    pay_to:[45.27,44.98], purpose:[53.02,52.60], written_amount:[73.30,72.86],
    receiver_name:[90.60,90.35], accountant:[90.60,90.35], approval:[90.60,90.35]
  };
  function candidatePageContainer() {
    const anchor = fieldFor("pay_to") || fieldFor("purpose") || document.querySelector("#voucherPage");
    if (!anchor) return document.querySelector("#voucherPage,.document-page,.template-page,.page");
    let cur = anchor.parentElement, candidates = [];
    while (cur && cur !== document.body) {
      const r = cur.getBoundingClientRect();
      if (r.width >= 300 && r.height >= 420) candidates.push({el:cur, score:Math.abs((r.width/r.height)-0.7071)});
      cur = cur.parentElement;
    }
    return candidates.sort((a,b)=>a.score-b.score)[0]?.el || document.querySelector("#voucherPage,.document-page,.template-page,.page");
  }
  function topPercent(el,page) {
    const raw = (el.style && el.style.top) || "";
    if (raw.endsWith("%")) { const n=parseFloat(raw); if(Number.isFinite(n)) return n; }
    if (!page) return null;
    const er=el.getBoundingClientRect(), pr=page.getBoundingClientRect();
    return pr.height ? ((er.top-pr.top)/pr.height)*100 : null;
  }
  function alignVoucherOverlay() {
    if (!isPaymentVoucherPage()) return;
    const page = candidatePageContainer(); if (!page) return;
    document.documentElement.classList.add("ziad-pv-final-line-align");
    for (const [key,target] of Object.entries(pdfTargetY)) {
      const el=fieldFor(key); if(!el) continue;
      const current=topPercent(el,page); if(current==null || Math.abs(current-target)<=0.18) continue;
      const known=knownOldY[key] || [];
      if(!known.some(v=>Math.abs(current-v)<=0.55)) continue;
      const deltaPx=((target-current)/100)*page.getBoundingClientRect().height;
      el.style.setProperty("--ziad-pv-delta-y", `${deltaPx}px`);
      el.classList.add("ziad-pv-runtime-align");
    }
  }
  function apply() {
    if (!document.body) return;
    if (isPaymentRequestPage()) savePRSnapshot();
    if (isPaymentVoucherPage()) { alignVoucherOverlay(); applyPRToPV(); }
  }
  function boot() {
    document.addEventListener("input", () => { if (isPaymentRequestPage()) savePRSnapshot(); }, true);
    document.addEventListener("change", () => { if (isPaymentRequestPage()) savePRSnapshot(); }, true);
    document.addEventListener("click", e => {
      if (!isPaymentRequestPage()) return;
      const el=e.target && e.target.closest && e.target.closest("button,a,[role=button]"); if(!el) return;
      const t=textOf(el)+" "+(el.getAttribute("href")||"");
      if (/سند\s*دفع|مستند\s*دفع|payment\s*voucher|\bPV\b|تحويل/i.test(t)) savePRSnapshot();
    }, true);
    apply();
    let queued=false;
    const observer=new MutationObserver(()=>{ if(queued)return; queued=true; requestAnimationFrame(()=>{queued=false;apply();}); });
    observer.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:["value","class","style"]});
    window.addEventListener("popstate",apply); window.addEventListener("hashchange",apply);
    window.addEventListener("beforeprint",alignVoucherOverlay);
  }
  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",boot,{once:true}); else boot();
})();
'''

CSS = r'''/* ziad-pr-pv-final-v3.3.29 - overlay only; template artwork remains untouched */
html.ziad-pv-final-line-align .ziad-pv-runtime-align {
  transform: translateY(var(--ziad-pv-delta-y, 0px)) !important;
}
@media print {
  html.ziad-pv-final-line-align input,
  html.ziad-pv-final-line-align textarea,
  html.ziad-pv-final-line-align [contenteditable="true"] {
    color:#000 !important;
    background:transparent !important;
    box-shadow:none !important;
  }
  html.ziad-pv-final-line-align .ziad-pv-runtime-align {
    transform:translateY(var(--ziad-pv-delta-y,0px)) !important;
  }
}
'''


def log(msg: str) -> None:
    print(f"[Ziad Invoices v{PATCH_VERSION}] {msg}", flush=True)


def locate_root() -> Path:
    candidates = [HERE, HERE.parent, Path.cwd(), *list(HERE.parents[:4])]
    seen: set[Path] = set()
    for candidate in candidates:
        try: candidate = candidate.resolve()
        except Exception: continue
        if candidate in seen: continue
        seen.add(candidate)
        if (candidate / "app").is_dir(): return candidate
    return HERE

ROOT = locate_root()
STATIC = ROOT / "app" / "static"
JS_FILE = STATIC / "ziad-payment-voucher-fix.js"
CSS_FILE = STATIC / "ziad-payment-voucher-fix.css"
CONTRACT_FILE = ROOT / "config" / "pr_to_pv_mapping.json"


def is_protected_template_path(path: Path) -> bool:
    try: rel = path.relative_to(ROOT)
    except Exception: return False
    parts = [p.lower() for p in rel.parts]
    return (
        (len(parts)>=3 and parts[0]=="app" and parts[1]=="static" and parts[2] in {"form-templates","templates"})
        or (parts and parts[0]=="templates")
    )


def protected_hashes() -> dict[str,str]:
    out={}
    for base in (STATIC/"form-templates", STATIC/"templates", ROOT/"templates"):
        if not base.exists(): continue
        for p in base.rglob("*"):
            if p.is_file():
                try: out[str(p.relative_to(ROOT)).replace("\\","/")] = hashlib.sha256(p.read_bytes()).hexdigest()
                except Exception: pass
    return out


def skip_path(path: Path) -> bool:
    if is_protected_template_path(path): return True
    parts={p.lower() for p in path.parts}
    return bool(parts & {".git",".venv","venv","node_modules","__pycache__","dist","build"}) or ".backup-" in path.name


def backup(path: Path) -> Path:
    stamp=time.strftime("%Y%m%d-%H%M%S")
    dst=path.with_name(path.name+f".backup-v{PATCH_VERSION}-{stamp}")
    shutil.copy2(path,dst); return dst


def close_to_known(key: str, value: float) -> bool:
    return any(abs(value-known)<=0.75 for known in PV_KNOWN_Y.get(key,()))


def patch_pv_config_obj(obj: object) -> int:
    changed=0
    if isinstance(obj,dict):
        if str(obj.get("code","")).upper()=="PV" and isinstance(obj.get("fields"),list):
            for field in obj["fields"]:
                if not isinstance(field,dict): continue
                key=str(field.get("key",""))
                if key not in PV_TARGET_Y: continue
                try: old_y=float(field.get("y"))
                except (TypeError,ValueError): continue
                target=PV_TARGET_Y[key]
                if abs(old_y-target)>0.005:
                    if not close_to_known(key,old_y):
                        log(f"Skipped unknown/custom PV coordinate for {key}: {old_y}")
                        continue
                    field["y"]=round(target,2); changed+=1
                if key=="purpose":
                    if field.get("line_positions") != PV_PURPOSE_LINES:
                        field["line_positions"]=PV_PURPOSE_LINES.copy(); changed+=1
                    if isinstance(field.get("line_boxes"),list) and len(field["line_boxes"])>=3:
                        for i,y in enumerate(PV_PURPOSE_LINES[:len(field["line_boxes"])]):
                            if isinstance(field["line_boxes"][i],dict): field["line_boxes"][i]["y"]=y
                elif key=="written_amount":
                    if field.get("line_positions") != PV_WRITTEN_LINES:
                        field["line_positions"]=PV_WRITTEN_LINES.copy(); changed+=1
                    if isinstance(field.get("line_boxes"),list) and len(field["line_boxes"])>=3:
                        for i,y in enumerate(PV_WRITTEN_LINES[:len(field["line_boxes"])]):
                            if isinstance(field["line_boxes"][i],dict): field["line_boxes"][i]["y"]=y
        for v in obj.values(): changed += patch_pv_config_obj(v)
    elif isinstance(obj,list):
        for v in obj: changed += patch_pv_config_obj(v)
    return changed


def patch_json(path: Path) -> int:
    try: data=json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception: return 0
    count=patch_pv_config_obj(data)
    if not count: return 0
    b=backup(path); path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    log(f"Locked PDF overlay coordinates in {path.relative_to(ROOT)} ({count} updates; backup {b.name})")
    return count


def patch_sql(path: Path) -> int:
    try: raw=path.read_text(encoding="utf-8-sig")
    except Exception: return 0
    if "$cfg_PV$" not in raw: return 0
    total=0
    def repl(m: re.Match[str]) -> str:
        nonlocal total
        try: data=json.loads(m.group(1))
        except Exception: return m.group(0)
        count=patch_pv_config_obj(data)
        if not count: return m.group(0)
        total += count
        return "$cfg_PV$"+json.dumps(data,ensure_ascii=False,separators=(",",":"))+"$cfg_PV$"
    out=re.sub(r"\$cfg_PV\$(\{.*?\})\$cfg_PV\$",repl,raw,flags=re.DOTALL)
    if not total or out==raw: return 0
    b=backup(path); path.write_text(out,encoding="utf-8")
    log(f"Locked PV coordinates in SQL seed {path.relative_to(ROOT)} ({total} updates; backup {b.name})")
    return total


def sqlite_backup(conn: sqlite3.Connection,path: Path) -> Path:
    stamp=time.strftime("%Y%m%d-%H%M%S"); dst=path.with_name(path.name+f".backup-v{PATCH_VERSION}-{stamp}")
    bconn=sqlite3.connect(dst)
    try: conn.backup(bconn)
    finally: bconn.close()
    return dst


def patch_sqlite(path: Path) -> int:
    try: conn=sqlite3.connect(path,timeout=2.0)
    except Exception: return 0
    try:
        if not conn.execute("select name from sqlite_master where type='table' and name='document_types'").fetchone(): return 0
        row=conn.execute("select id,config_json from document_types where upper(code)='PV' limit 1").fetchone()
        if not row: return 0
        doc_id,raw=row; data=json.loads(raw); count=patch_pv_config_obj(data)
        if not count: return 0
        b=sqlite_backup(conn,path)
        conn.execute("update document_types set config_json=? where id=?",(json.dumps(data,ensure_ascii=False,separators=(",",":")),doc_id)); conn.commit()
        log(f"Locked live SQLite PV print coordinates in {path.relative_to(ROOT)} ({count} updates; backup {b.name})")
        return count
    except Exception as exc:
        log(f"SQLite skipped for {path.relative_to(ROOT)}: {exc}"); return 0
    finally: conn.close()


def inject_shell(path: Path) -> bool:
    try: raw=path.read_text(encoding="utf-8-sig")
    except Exception: return False
    out=raw
    if "ziad-payment-voucher-fix.css" not in out:
        tag=f'<link rel="stylesheet" href="/static/ziad-payment-voucher-fix.css" data-fix="{MARKER}">'
        idx=out.lower().rfind("</head>"); out=(out[:idx]+"  "+tag+"\n"+out[idx:]) if idx>=0 else tag+"\n"+out
    if "ziad-payment-voucher-fix.js" not in out:
        tag=f'<script defer src="/static/ziad-payment-voucher-fix.js" data-fix="{MARKER}"></script>'
        idx=out.lower().rfind("</body>"); out=(out[:idx]+"  "+tag+"\n"+out[idx:]) if idx>=0 else out+"\n"+tag+"\n"
    if out==raw: return False
    b=backup(path); path.write_text(out,encoding="utf-8")
    log(f"Injected final mapping runtime into {path.relative_to(ROOT)} (backup {b.name})"); return True


def write_contract() -> None:
    CONTRACT_FILE.parent.mkdir(parents=True,exist_ok=True)
    data={
        "version": PATCH_VERSION,
        "status": "LOCKED_USER_APPROVED",
        "rule": "Do not change unless user explicitly replaces this mapping.",
        "mapping": FINAL_MAPPING,
        "payment_voucher_print": {
            "requirement": "Text must print immediately above ruled lines, never below them.",
            "overlay_y_percent": PV_TARGET_Y,
            "purpose_line_positions": PV_PURPOSE_LINES,
            "written_amount_line_positions": PV_WRITTEN_LINES,
        },
        "template_policy": "Do not modify voucher/request template artwork, HTML, PDF or DOCX. Only data transfer and text overlay positions may change."
    }
    CONTRACT_FILE.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    log(f"Wrote permanent mapping contract: {CONTRACT_FILE.relative_to(ROOT)}")


def verify_contract() -> None:
    data=json.loads(CONTRACT_FILE.read_text(encoding="utf-8"))
    if data.get("mapping") != FINAL_MAPPING: raise RuntimeError("Final PR->PV mapping contract verification failed")
    if data.get("payment_voucher_print",{}).get("overlay_y_percent") != PV_TARGET_Y: raise RuntimeError("PV print coordinate contract verification failed")


def main() -> int:
    log(f"Project root: {ROOT}")
    if not (ROOT/"app").is_dir():
        print("[ERROR] Extract this update inside the Ziad Invoices project root containing app/.",file=sys.stderr); return 1

    before=protected_hashes()
    STATIC.mkdir(parents=True,exist_ok=True)
    JS_FILE.write_text(JS,encoding="utf-8"); CSS_FILE.write_text(CSS,encoding="utf-8")
    write_contract(); verify_contract()

    json_count=sum(patch_json(p) for p in ROOT.rglob("templates.json") if not skip_path(p))
    sql_count=sum(patch_sql(p) for p in ROOT.rglob("*.sql") if not skip_path(p))
    dbs=[]
    for pattern in ("*.db","*.sqlite","*.sqlite3"): dbs.extend(ROOT.rglob(pattern))
    db_count=sum(patch_sqlite(p) for p in sorted(set(dbs)) if p.is_file() and not skip_path(p) and p.stat().st_size<500*1024*1024)
    injected=0
    for name in ("index.html","app.html","main.html"):
        p=STATIC/name
        if p.exists(): injected += 1 if inject_shell(p) else 0

    after=protected_hashes()
    if before != after:
        print("[ERROR] Protected voucher/request template files changed unexpectedly. Aborting.",file=sys.stderr)
        changed=sorted(set(before)|set(after))
        for k in changed:
            if before.get(k)!=after.get(k): print("  changed:",k,file=sys.stderr)
        return 2

    # Static self-test of exact mapping semantics.
    js=JS_FILE.read_text(encoding="utf-8")
    required=[
        '["department", "pay_to"]', '["amount", "amount"]', '["currency", "currency"]',
        '["written_amount", "written_amount"]', '["approval", "approval"]', '["prepared_by", "receiver_name"]',
        'return `${payTo}\\n${description}`'
    ]
    missing=[x for x in required if x not in js]
    if missing: raise RuntimeError("Runtime mapping self-test failed: "+", ".join(missing))

    log("------------------------------------------------------------")
    log("FINAL MAPPING LOCKED:")
    log("  PR department -> PV pay_to")
    log("  PR pay_to -> PV purpose / first ruled line")
    log("  PR description_of_purpose -> PV purpose / remaining ruled lines")
    log("  PR amount -> PV amount")
    log("  PR currency -> PV currency")
    log("  PR written_amount -> PV written_amount")
    log("  PR approval -> PV approval")
    log("  PR prepared_by -> PV receiver_name")
    log(f"JSON coordinate updates: {json_count}; SQL: {sql_count}; SQLite: {db_count}; shell injections: {injected}")
    log("Protected voucher/request template artwork hashes: UNCHANGED")
    log("PDF text-overlay positions: LOCKED ABOVE RULED LINES")
    log("FINAL FIX COMPLETE")
    return 0

if __name__ == "__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}",file=sys.stderr)
        raise SystemExit(1)
