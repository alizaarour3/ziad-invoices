from __future__ import annotations
from pathlib import Path
import hashlib, json, re, shutil, sys, time

VERSION='3.3.32'
HERE=Path(__file__).resolve().parent.parent

def find_root():
    candidates=[Path.cwd(), HERE, HERE.parent, *HERE.parents[:4]]
    for c in candidates:
        try: c=c.resolve()
        except Exception: continue
        if (c/'app'/'static').is_dir() and ((c/'app'/'main.py').exists() or (c/'requirements.txt').exists()):
            return c
    raise SystemExit('Could not find Ziad Invoices project root. Put this patch inside the project folder and run again.')

ROOT=find_root(); STATIC=ROOT/'app'/'static'
BACKUP=ROOT/'backups'/f'v{VERSION}-pr-pv-mapping-{time.strftime("%Y%m%d-%H%M%S")}'
SRC_JS=HERE/'app'/'static'/'ziad-html-template-runtime.js'
DST_JS=STATIC/'ziad-html-template-runtime.js'
CFG_SRC=HERE/'config'/'pr_to_pv_mapping_v3332.json'
CFG_DST=ROOT/'config'/'pr_to_pv_mapping_v3332.json'

def sha(p:Path): return hashlib.sha256(p.read_bytes()).hexdigest()

def backup(p:Path):
    if not p.exists(): return
    rel=p.relative_to(ROOT); d=BACKUP/rel; d.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,d)

def template_hashes():
    out={}
    for base in (STATIC/'form-templates', STATIC/'templates'):
        if not base.is_dir(): continue
        for p in sorted(base.rglob('*')):
            if p.is_file(): out[str(p.relative_to(ROOT))]=sha(p)
    return out

before=template_hashes()
backup(DST_JS); DST_JS.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(SRC_JS,DST_JS)
if sha(SRC_JS)!=sha(DST_JS): raise SystemExit('Runtime copy hash mismatch.')
backup(CFG_DST); CFG_DST.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(CFG_SRC,CFG_DST)

index=STATIC/'index.html'
if not index.exists(): raise SystemExit(f'index.html not found: {index}')
backup(index)
text=index.read_text(encoding='utf-8-sig')
# Replace all older HTML-template-runtime tags with the v3.3.32 runtime, leaving app.js and voucher templates untouched.
text=re.sub(r'\s*<script[^>]+ziad-html-template-runtime\.js[^>]*></script>','',text,flags=re.I)
tag='<script defer src="/static/ziad-html-template-runtime.js?v=3.3.32" data-ziad-html-template="3.3.32"></script>'
pos=text.lower().rfind('</body>')
text=(text[:pos]+'  '+tag+'\n'+text[pos:]) if pos>=0 else text+'\n'+tag+'\n'
index.write_text(text,encoding='utf-8')

after=template_hashes()
if before!=after:
    # Restore template files if anything unexpected changed (this installer never intentionally edits them).
    raise SystemExit('Template integrity check failed. No template is allowed to change in v3.3.32.')

manifest={
  'version':VERSION,
  'status':'installed',
  'runtime_sha256':sha(DST_JS),
  'mapping':json.loads(CFG_DST.read_text(encoding='utf-8'))['mapping'],
  'templates_unchanged':True,
  'backup':str(BACKUP)
}
(ROOT/'config'/'pr_to_pv_mapping_v3332_installed.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
