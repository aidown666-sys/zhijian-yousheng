"""Audit tracked files/history without printing credential values. Stdlib only."""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {'app_id', 'appid', 'app_secret', 'appsecret', 'consumer_token',
          'producer_token', 'admin_token', 'api_key', 'apikey', 'access_token', 'password'}
ASSIGNMENT = re.compile(
    rb'''["']?(app_?id|app_?secret|consumer_token|producer_token|admin_token|api_?key|access_token|password)["']?\s*(?:=>|[:=])\s*(["'])([^"'\r\n]{4,})\2''', re.I)
TOKEN = re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16})\b')
PRIVATE_KEY = re.compile(rb'-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----')
REFERENCE_FILES = ['integrations/polyv/server/private/config.php',
                   'integrations/polyv/local-bridge.json']
IGNORE_PROBES = REFERENCE_FILES + ['integrations/polyv/watch-config.json',
    'integrations/polyv/package.zip', 'runtime/polyv-bridge-status.json', '.env',
    '.env.production', 'backup.zip', 'credentials.json', 'secrets.json', 'tls.key']


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def protected(path):
    name = path.replace('\\', '/').lower()
    base = name.rsplit('/', 1)[-1]
    return (name.startswith(('runtime/', 'outputs/')) or '/private/' in '/' + name
            or base in {'local-bridge.json', 'watch-config.json'}
            or (base.startswith('.env') and not base.endswith('.example'))
            or base.endswith(('.zip', '.7z', '.pfx', '.p12', '.key', '.pem'))
            or bool(re.fullmatch(r'(?:credentials|secrets)(?:[.-].*)?\.json', base)))


def references():
    """Read ignored local configuration as comparison input, never expose it."""
    values = {}
    for name in REFERENCE_FILES:
        file = ROOT / name
        if not file.is_file():
            continue
        raw = file.read_text(encoding='utf-8-sig')
        if file.suffix == '.php':
            match = re.search(r"json_decode\('(.+?)',\s*true\)", raw, re.S)
            if not match:
                raise ValueError('Unsupported local PHP configuration format')
            obj = json.loads(match[1])
        else:
            obj = json.loads(raw)
        for key, value in obj.items():
            if key.lower() in FIELDS and isinstance(value, str) and len(value) >= 8:
                values[key] = value.encode()
    return values


def findings(data, path, known):
    issues = []
    for key, value in known.items():
        if value in data:
            issues.append('known-local-credential:' + key)
    if TOKEN.search(data):
        issues.append('credential-token-pattern')
    if PRIVATE_KEY.search(data):
        issues.append('private-key')
    # Explicit unit-test fixtures are harmless; real known values are checked above.
    if not path.startswith('tests/'):
        for match in ASSIGNMENT.finditer(data):
            value = match[3].lower()
            placeholder = (value.startswith((b'your_', b'replace_', b'example', b'test-', b'unit-test'))
                           or value in {b'none', b'null'} or b'${' in value)
            if not placeholder:
                issues.append('hardcoded-field:' + match[1].decode('ascii').lower())
    return sorted(set(issues))


def contains_known(file, known):
    """Read large LFS working files in chunks, including matches across boundaries."""
    matches = set()
    overlap = max((len(v) for v in known.values()), default=1) - 1
    previous = b''
    with file.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            data = previous + block
            matches.update('known-local-credential:' + key for key, value in known.items() if value in data)
            previous = data[-overlap:] if overlap else b''
    return sorted(matches)


def object_blobs(objects):
    process = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for oid, name in objects:
            process.stdin.write((oid + '\n').encode())
            process.stdin.flush()
            header = process.stdout.readline().decode().split()
            data = process.stdout.read(int(header[2]))
            process.stdout.read(1)
            if header[1] == 'blob':
                yield oid, name, data
    finally:
        process.stdin.close()
        process.stdout.close()
        process.wait()


def history_blobs():
    objects = []
    for line in git('rev-list', '--objects', '--all').decode('utf-8').splitlines():
        oid, _, name = line.partition(' ')
        objects.append((oid, name))
    yield from object_blobs(objects)


def index_blobs():
    objects = []
    for entry in git('ls-files', '--stage', '-z').decode('utf-8').split('\0'):
        if not entry:
            continue
        metadata, name = entry.split('\t', 1)
        _, oid, stage = metadata.split()
        if stage != '0':
            raise ValueError('Resolve Git index conflicts before auditing')
        objects.append((oid, name))
    yield from object_blobs(objects)


def audit(include_history=False):
    known = references()
    result = {'head': git('rev-parse', 'HEAD').decode().strip(),
              'reference_field_names': sorted(known), 'tracked_files_checked': 0,
              'index_blobs_checked': 0, 'history_blobs_checked': 0,
              'findings': [], 'ignore_failures': []}
    for name in git('ls-files', '-z').decode('utf-8').split('\0'):
        if not name:
            continue
        file = ROOT / name
        issues = ['protected-path'] if protected(name) else []
        if file.stat().st_size > 4 * 1024 * 1024:
            issues += contains_known(file, known)
        else:
            issues += findings(file.read_bytes(), name, known)
        result['tracked_files_checked'] += 1
        if issues:
            result['findings'].append({'path': name, 'issues': issues})
    # A clean working copy must not conceal a previously staged credential.
    for oid, name, data in index_blobs():
        result['index_blobs_checked'] += 1
        issues = findings(data, name, known)
        if protected(name):
            issues.append('protected-path-in-index')
        if issues:
            result['findings'].append({'path': name, 'object': oid, 'scope': 'index', 'issues': issues})
    if include_history:
        for oid, name, data in history_blobs():
            result['history_blobs_checked'] += 1
            issues = findings(data, name, known)
            if protected(name):
                issues.append('protected-path-in-history')
            if issues:
                result['findings'].append({'path': name, 'object': oid, 'issues': issues})
    for name in IGNORE_PROBES:
        check = subprocess.run(['git', 'check-ignore', '--no-index', '-q', name], cwd=ROOT)
        if check.returncode:
            result['ignore_failures'].append(name)
    result['passed'] = not result['findings'] and not result['ignore_failures']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = audit(args.history)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
