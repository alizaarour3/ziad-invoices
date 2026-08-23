from __future__ import annotations
from pathlib import Path
import hashlib
import json
import shutil
import sys
import time

VERSION='3.3.30'
HERE=Path(__file__).resolve().parent.parent

def root():
    candidates=[HERE,HERE.parent,Path.cwd(),*HERE.parents[:3]]
    for c in candidates:
        try:c=c.resolve()
        except Exception:continue
        if (c/'app'/'static').is_dir() and ((c/'app'/'main.py').exists() or (c/'requirements.txt').exists()): return c
    return HERE

ROOT=root(); SRC=HERE/'app'/'static'; DST=ROOT/'app'/'static'
BACKUP=ROOT/'backups'/f'v{VERSION}-html-template-{time.strftime("%Y%m%d-%H%M%S")}'
FILES=[
 ('form-templates/payment-request.html','form-templates/payment-request.html'),
 ('form-templates/payment-voucher.html','form-templates/payment-voucher.html'),
 ('form-templates/request-transfer.html','form-templates/request-transfer.html'),
 ('form-templates/car-maintenance.html','form-templates/car-maintenance.html'),
 ('ziad-html-template-runtime.js','ziad-html-template-runtime.js'),
 ('ziad-html-template-runtime.css','ziad-html-template-runtime.css'),
]

def sha(p:Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def backup_file(p:Path):
    if p.exists():
        rel=p.relative_to(ROOT)
        target=BACKUP/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,target)

def install_file(src_rel,dst_rel):
    src=SRC/src_rel; dst=DST/dst_rel
    if not src.exists(): raise SystemExit(f'Missing patch file: {src}')
    if src.resolve() == dst.resolve():
        return
    backup_file(dst)
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)
    if sha(src)!=sha(dst): raise SystemExit(f'Hash mismatch after copy: {dst}')

for a,b in FILES: install_file(a,b)

cfg_src=HERE/'config'/'html_templates.json'; cfg_dst=ROOT/'config'/'html_templates.json'
if cfg_src.resolve() != cfg_dst.resolve():
    backup_file(cfg_dst); cfg_dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(cfg_src,cfg_dst)

index=DST/'index.html'
if not index.exists(): raise SystemExit(f'index.html not found: {index}')
backup_file(index)
text=index.read_text(encoding='utf-8')
css='<link rel="stylesheet" href="/static/ziad-html-template-runtime.css?v=3.3.30" data-ziad-html-template="3.3.30">'
js='<script defer src="/static/ziad-html-template-runtime.js?v=3.3.30" data-ziad-html-template="3.3.30"></script>'
# Remove any older copy of our own runtime only; do not touch app.js or any other hotfix.
import re
text=re.sub(r'\s*<link[^>]+ziad-html-template-runtime\.css[^>]*>','',text,flags=re.I)
text=re.sub(r'\s*<script[^>]+ziad-html-template-runtime\.js[^>]*></script>','',text,flags=re.I)
if '</head>' in text.lower():
    pos=text.lower().rfind('</head>'); text=text[:pos]+'  '+css+'\n'+text[pos:]
else: text=css+'\n'+text
if '</body>' in text.lower():
    pos=text.lower().rfind('</body>'); text=text[:pos]+'  '+js+'\n'+text[pos:]
else: text=text+'\n'+js+'\n'
index.write_text(text,encoding='utf-8')

# Report exact source hashes so the user-supplied templates are auditable.
manifest={
 'version':VERSION,
 'mode':'HTML_TEMPLATE_FIRST',
 'installed':{dst_rel:sha(DST/dst_rel) for _,dst_rel in FILES},
 'index':sha(index),
 'backup':str(BACKUP),
}
manifest_path=ROOT/'config'/'html_templates_installed.json'
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
