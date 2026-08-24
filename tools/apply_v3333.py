from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, sys, time

VERSION = '3.3.33'
HERE = Path(__file__).resolve().parent.parent

def is_root(p: Path) -> bool:
    try:
        p = p.resolve()
    except Exception:
        return False
    return (p / 'app' / 'static' / 'index.html').is_file() and ((p / 'app' / 'main.py').is_file() or (p / 'requirements.txt').is_file())

def candidates(explicit: str | None):
    seen = set()
    def add(p):
        if not p:
            return
        try:
            q = Path(p).expanduser().resolve()
        except Exception:
            return
        k = str(q).lower()
        if k not in seen:
            seen.add(k)
            yield q
    if explicit:
        yield from add(explicit)
    yield from add(os.environ.get('ZIAD_PROJECT_ROOT'))
    yield from add(Path.cwd())
    yield from add(HERE)
    yield from add(HERE.parent)
    for parent in list(HERE.parents)[:5]:
        yield from add(parent)
    user = Path(os.environ.get('USERPROFILE') or Path.home())
    desktop = user / 'Desktop'
    yield from add(desktop / 'ziad-invoices-v3.3.3')
    yield from add(Path(r'C:\Users\User\Desktop\ziad-invoices-v3.3.3'))
    if desktop.is_dir():
        for p in sorted(desktop.glob('ziad-invoices*')):
            yield from add(p)

def find_root(explicit: str | None) -> Path:
    for p in candidates(explicit):
        if is_root(p):
            return p
    if sys.stdin and sys.stdin.isatty():
        print('\nZiad Invoices project was not found automatically.')
        print('Paste the full project path, for example:')
        print(r'C:\Users\User\Desktop\ziad-invoices-v3.3.3')
        typed = input('Project path: ').strip().strip('"')
        if typed and is_root(Path(typed)):
            return Path(typed).expanduser().resolve()
    raise SystemExit('ERROR: Could not find the Ziad Invoices project folder.')

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def copy_with_backup(src: Path, dst: Path, root: Path, backup_dir: Path, installed: list, created: list):
    if not src.is_file():
        raise SystemExit(f'ERROR: Missing patch file: {src}')
    if dst.exists():
        rel = dst.relative_to(root)
        b = backup_dir / rel
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dst, b)
    else:
        created.append(str(dst.relative_to(root)))
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if sha(src) != sha(dst):
        raise SystemExit(f'ERROR: Copy verification failed: {dst}')
    installed.append(str(dst.relative_to(root)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=None)
    args = ap.parse_args()
    root = find_root(args.root)
    static = root / 'app' / 'static'
    backup_dir = root / 'backups' / f'v{VERSION}-consolidated-{time.strftime("%Y%m%d-%H%M%S")}'
    installed, created = [], []

    print(f'Project: {root}')
    print('Applying one consolidated PR/PV fix...')

    files = [
        (HERE/'app/static/form-templates/payment-request.html', static/'form-templates/payment-request.html'),
        (HERE/'app/static/form-templates/payment-voucher.html', static/'form-templates/payment-voucher.html'),
        (HERE/'app/static/form-templates/request-transfer.html', static/'form-templates/request-transfer.html'),
        (HERE/'app/static/form-templates/car-maintenance.html', static/'form-templates/car-maintenance.html'),
        (HERE/'app/static/ziad-html-template-runtime.js', static/'ziad-html-template-runtime.js'),
        (HERE/'app/static/ziad-html-template-runtime.css', static/'ziad-html-template-runtime.css'),
    ]
    for src, dst in files:
        copy_with_backup(src, dst, root, backup_dir, installed, created)

    cfg_dir = root / 'config'
    cfg_dir.mkdir(parents=True, exist_ok=True)
    for name in ('pr_to_pv_mapping_v3333.json','v3333_template_hashes.json'):
        copy_with_backup(HERE/'config'/name, cfg_dir/name, root, backup_dir, installed, created)

    index = static / 'index.html'
    if not index.is_file():
        raise SystemExit(f'ERROR: index.html not found: {index}')
    rel = index.relative_to(root)
    b = backup_dir / rel
    b.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(index, b)

    text = index.read_text(encoding='utf-8-sig')
    text = re.sub(r'\s*<link[^>]+ziad-html-template-runtime\.css[^>]*>', '', text, flags=re.I)
    text = re.sub(r'\s*<script[^>]+ziad-html-template-runtime\.js[^>]*></script>', '', text, flags=re.I)
    css = f'<link rel="stylesheet" href="/static/ziad-html-template-runtime.css?v={VERSION}" data-ziad-html-template="{VERSION}">'
    js = f'<script defer src="/static/ziad-html-template-runtime.js?v={VERSION}" data-ziad-html-template="{VERSION}"></script>'
    low = text.lower()
    head = low.rfind('</head>')
    if head >= 0:
        text = text[:head] + '  ' + css + '\n' + text[head:]
    else:
        text = css + '\n' + text
    low = text.lower()
    body = low.rfind('</body>')
    if body >= 0:
        text = text[:body] + '  ' + js + '\n' + text[body:]
    else:
        text += '\n' + js + '\n'
    index.write_text(text, encoding='utf-8')
    installed.append(str(rel))

    mapping = json.loads((cfg_dir/'pr_to_pv_mapping_v3333.json').read_text(encoding='utf-8'))
    manifest = {
        'version': VERSION,
        'status': 'installed',
        'project': str(root),
        'backup': str(backup_dir),
        'installed_files': installed,
        'created_files': created,
        'runtime_sha256': sha(static/'ziad-html-template-runtime.js'),
        'payment_request_sha256': sha(static/'form-templates/payment-request.html'),
        'payment_voucher_sha256': sha(static/'form-templates/payment-voucher.html'),
        'mapping': mapping['mapping'],
        'receiver_source': 'prepared_signature only',
        'print_contract': mapping['print_contract'],
    }
    (cfg_dir/'v3333_installed.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    print('\nSUCCESS - v3.3.33 installed.')
    print('LOCKED mapping:')
    print('  Department -> Payment Voucher Pay to')
    print('  PR Pay to -> Payment Voucher Purpose first line')
    print('  PR Description of Purpose -> Purpose following lines')
    print('  Prepared by -> Name of Receiver')
    print('Payment Voucher print text is lifted above printed lines.')
    print(f'Backup: {backup_dir}')

if __name__ == '__main__':
    main()
