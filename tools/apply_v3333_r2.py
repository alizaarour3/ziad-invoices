from __future__ import annotations
from pathlib import Path
import argparse, ctypes, hashlib, json, os, re, shutil, sys, time

VERSION = '3.3.33-R2'
HERE = Path(__file__).resolve().parent.parent

# Windows Restart Manager helpers: used only to identify which app is locking a file.
if os.name == 'nt':
    from ctypes import wintypes
    ERROR_MORE_DATA = 234
    CCH_RM_SESSION_KEY = 32
    CCH_RM_MAX_APP_NAME = 255
    CCH_RM_MAX_SVC_NAME = 63

    class RM_UNIQUE_PROCESS(ctypes.Structure):
        _fields_ = [('dwProcessId', wintypes.DWORD), ('ProcessStartTime', wintypes.FILETIME)]

    class RM_PROCESS_INFO(ctypes.Structure):
        _fields_ = [
            ('Process', RM_UNIQUE_PROCESS),
            ('strAppName', wintypes.WCHAR * (CCH_RM_MAX_APP_NAME + 1)),
            ('strServiceShortName', wintypes.WCHAR * (CCH_RM_MAX_SVC_NAME + 1)),
            ('ApplicationType', wintypes.DWORD),
            ('AppStatus', wintypes.ULONG),
            ('TSSessionId', wintypes.DWORD),
            ('bRestartable', wintypes.BOOL),
        ]


def locking_processes(path: Path):
    if os.name != 'nt':
        return []
    try:
        rstrtmgr = ctypes.WinDLL('Rstrtmgr.dll')
        handle = wintypes.DWORD()
        key = ctypes.create_unicode_buffer(CCH_RM_SESSION_KEY + 1)
        if rstrtmgr.RmStartSession(ctypes.byref(handle), 0, key) != 0:
            return []
        try:
            resources = (wintypes.LPCWSTR * 1)(str(path))
            if rstrtmgr.RmRegisterResources(handle, 1, resources, 0, None, 0, None) != 0:
                return []
            needed = wintypes.UINT(0)
            count = wintypes.UINT(0)
            reason = wintypes.DWORD(0)
            rc = rstrtmgr.RmGetList(handle, ctypes.byref(needed), ctypes.byref(count), None, ctypes.byref(reason))
            if rc not in (0, ERROR_MORE_DATA) or needed.value == 0:
                return []
            arr = (RM_PROCESS_INFO * needed.value)()
            count = wintypes.UINT(needed.value)
            rc = rstrtmgr.RmGetList(handle, ctypes.byref(needed), ctypes.byref(count), arr, ctypes.byref(reason))
            if rc != 0:
                return []
            out = []
            for i in range(count.value):
                out.append((arr[i].Process.dwProcessId, arr[i].strAppName or 'Unknown process'))
            return out
        finally:
            rstrtmgr.RmEndSession(handle)
    except Exception:
        return []


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
        typed = input('Paste project path: ').strip().strip('"')
        if typed and is_root(Path(typed)):
            return Path(typed).expanduser().resolve()
    raise SystemExit('ERROR: Could not find the Ziad Invoices project folder.')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retry_file_op(label, path: Path, fn, retries=4):
    last = None
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except PermissionError as exc:
            last = exc
            print(f'\nLOCKED FILE: {path}')
            procs = locking_processes(path)
            if procs:
                print('Windows reports this file is being used by:')
                for pid, name in procs:
                    print(f'  PID {pid}: {name}')
            else:
                print('Windows says another process is using this file.')
            if attempt < retries:
                print(f'Retry {attempt}/{retries - 1}: close Ziad Invoices completely, then press ENTER.')
                try:
                    input()
                except EOFError:
                    time.sleep(2)
            else:
                break
    raise PermissionError(
        f'Cannot update locked file: {path}\n'
        'Close Ziad Invoices, its server/terminal window, and any editor that has this file open, then run the installer again.'
    ) from last


def safe_copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    def op():
        shutil.copy2(src, dst)
    retry_file_op('copy', dst, op)


def safe_backup(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    def op():
        shutil.copy2(src, dst)
    retry_file_op('backup', src, op)


def write_text_retry(path: Path, text: str):
    def op():
        path.write_text(text, encoding='utf-8')
    retry_file_op('write', path, op)


def rollback(changed, created):
    print('\nRolling back changes from this failed attempt...')
    errors = []
    for dst, backup in reversed(changed):
        try:
            if backup and backup.exists():
                safe_copy(backup, dst)
        except Exception as exc:
            errors.append(f'{dst}: {exc}')
    for dst in reversed(created):
        try:
            if dst.exists():
                dst.unlink()
        except Exception as exc:
            errors.append(f'{dst}: {exc}')
    if errors:
        print('Rollback warnings:')
        for e in errors:
            print('  ' + e)
    else:
        print('Rollback complete.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=None)
    args = ap.parse_args()
    root = find_root(args.root)
    static = root / 'app' / 'static'
    stamp = time.strftime('%Y%m%d-%H%M%S')
    backup_dir = root / 'backups' / f'v{VERSION}-consolidated-{stamp}'
    changed = []
    created = []
    installed = []

    print(f'Project: {root}')
    print('IMPORTANT: Ziad Invoices must be CLOSED while this update is applied.')
    print('Applying one consolidated PR/PV fix with locked-file protection...')

    files = [
        (HERE/'app/static/form-templates/payment-request.html', static/'form-templates/payment-request.html'),
        (HERE/'app/static/form-templates/payment-voucher.html', static/'form-templates/payment-voucher.html'),
        (HERE/'app/static/form-templates/request-transfer.html', static/'form-templates/request-transfer.html'),
        (HERE/'app/static/form-templates/car-maintenance.html', static/'form-templates/car-maintenance.html'),
        (HERE/'app/static/ziad-html-template-runtime.js', static/'ziad-html-template-runtime.js'),
        (HERE/'app/static/ziad-html-template-runtime.css', static/'ziad-html-template-runtime.css'),
    ]

    try:
        for src, dst in files:
            if not src.is_file():
                raise RuntimeError(f'Missing patch file: {src}')
            backup = None
            if dst.exists():
                rel = dst.relative_to(root)
                backup = backup_dir / rel
                safe_backup(dst, backup)
            else:
                created.append(dst)
            safe_copy(src, dst)
            if sha(src) != sha(dst):
                raise RuntimeError(f'Copy verification failed: {dst}')
            changed.append((dst, backup))
            installed.append(str(dst.relative_to(root)))

        cfg_dir = root / 'config'
        cfg_dir.mkdir(parents=True, exist_ok=True)
        for name in ('pr_to_pv_mapping_v3333.json', 'v3333_template_hashes.json'):
            src = HERE/'config'/name
            dst = cfg_dir/name
            backup = None
            if dst.exists():
                backup = backup_dir / dst.relative_to(root)
                safe_backup(dst, backup)
            else:
                created.append(dst)
            safe_copy(src, dst)
            changed.append((dst, backup))
            installed.append(str(dst.relative_to(root)))

        index = static / 'index.html'
        if not index.is_file():
            raise RuntimeError(f'index.html not found: {index}')
        index_backup = backup_dir / index.relative_to(root)
        safe_backup(index, index_backup)
        text = index.read_text(encoding='utf-8-sig')
        text = re.sub(r'\s*<link[^>]+ziad-html-template-runtime\.css[^>]*>', '', text, flags=re.I)
        text = re.sub(r'\s*<script[^>]+ziad-html-template-runtime\.js[^>]*></script>', '', text, flags=re.I)
        css = '<link rel="stylesheet" href="/static/ziad-html-template-runtime.css?v=3.3.33" data-ziad-html-template="3.3.33">'
        js = '<script defer src="/static/ziad-html-template-runtime.js?v=3.3.33" data-ziad-html-template="3.3.33"></script>'
        low = text.lower()
        head = low.rfind('</head>')
        text = text[:head] + '  ' + css + '\n' + text[head:] if head >= 0 else css + '\n' + text
        low = text.lower()
        body = low.rfind('</body>')
        text = text[:body] + '  ' + js + '\n' + text[body:] if body >= 0 else text + '\n' + js + '\n'
        write_text_retry(index, text)
        changed.append((index, index_backup))
        installed.append(str(index.relative_to(root)))

        mapping = json.loads((cfg_dir/'pr_to_pv_mapping_v3333.json').read_text(encoding='utf-8'))
        manifest = {
            'version': VERSION,
            'status': 'installed',
            'project': str(root),
            'backup': str(backup_dir),
            'installed_files': installed,
            'runtime_sha256': sha(static/'ziad-html-template-runtime.js'),
            'payment_request_sha256': sha(static/'form-templates/payment-request.html'),
            'payment_voucher_sha256': sha(static/'form-templates/payment-voucher.html'),
            'mapping': mapping['mapping'],
            'receiver_source': 'prepared_signature only',
            'print_contract': mapping['print_contract'],
        }
        manifest_path = cfg_dir/'v3333_installed.json'
        manifest_backup = None
        if manifest_path.exists():
            manifest_backup = backup_dir / manifest_path.relative_to(root)
            safe_backup(manifest_path, manifest_backup)
        else:
            created.append(manifest_path)
        write_text_retry(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        changed.append((manifest_path, manifest_backup))

    except Exception as exc:
        print(f'\nERROR: {exc}')
        rollback(changed, created)
        raise SystemExit(1)

    print('\nSUCCESS - v3.3.33-R2 installed.')
    print('Department -> Payment Voucher Pay to')
    print('PR Pay to -> Payment Voucher Purpose first line')
    print('PR Description -> Purpose following lines')
    print('Prepared by -> Name of Receiver')
    print('Payment Voucher print text remains above printed lines.')
    print(f'Backup: {backup_dir}')


if __name__ == '__main__':
    main()
