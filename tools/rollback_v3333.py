from __future__ import annotations
from pathlib import Path
import argparse, json, os, shutil, sys


def is_root(p: Path) -> bool:
    return (p/'app/static/index.html').is_file()

def find_root(explicit=None):
    c=[]
    if explicit:c.append(Path(explicit))
    c += [Path.cwd(), Path(os.environ.get('USERPROFILE') or Path.home())/'Desktop'/'ziad-invoices-v3.3.3', Path(r'C:\Users\User\Desktop\ziad-invoices-v3.3.3')]
    desktop=Path(os.environ.get('USERPROFILE') or Path.home())/'Desktop'
    if desktop.is_dir():c += list(desktop.glob('ziad-invoices*'))
    for p in c:
        try:p=p.expanduser().resolve()
        except Exception:continue
        if is_root(p):return p
    if sys.stdin.isatty():
        typed=input('Project path: ').strip().strip('"')
        if typed and is_root(Path(typed)):return Path(typed).resolve()
    raise SystemExit('Project not found.')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root');args=ap.parse_args()
    root=find_root(args.root)
    manifest_path=root/'config/v3333_installed.json'
    if not manifest_path.is_file():raise SystemExit('v3.3.33 install manifest not found.')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    backup=Path(manifest['backup'])
    if not backup.is_dir():raise SystemExit(f'Backup not found: {backup}')
    for src in backup.rglob('*'):
        if src.is_file():
            rel=src.relative_to(backup); dst=root/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
    for rel in manifest.get('created_files',[]):
        p=root/rel
        if p.exists() and not (backup/rel).exists():
            try:p.unlink()
            except Exception:pass
    print('Rollback completed from:',backup)
if __name__=='__main__':main()
