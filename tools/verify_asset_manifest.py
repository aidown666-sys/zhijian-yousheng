"""Verify binary assets without unpickling motion data."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'assets/MANIFEST.json').read_text(encoding='utf-8'))
    failures = []
    for item in manifest['files']:
        path = ROOT / item['path']
        if not path.is_file() or path.stat().st_size != item['bytes']:
            failures.append(item['path'])
            continue
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != item['sha256']:
            failures.append(item['path'])
    if failures:
        raise SystemExit('Missing, modified or unpulled assets: ' + ', '.join(failures))
    print('Asset checks passed:', len(manifest['files']))


if __name__ == '__main__':
    main()
