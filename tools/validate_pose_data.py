"""Validate public CSL pose arrays without SMPL-X meshes or licensed body files."""
import hashlib
import io
import json
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime/pose_packages'))
from urllib.request import Request, urlopen


def request(url, headers=None):
    return urlopen(Request(url, headers={'User-Agent': 'SignHuman-research/1.0', **(headers or {})}), timeout=60)
import lmdb
import numpy as np


def main():
    repo = 'LionelLow/SignSparK_data'
    name = 'dev/CSL-Daily_reopt_dev.lmdb/data.mdb'
    expected_size = 200536064
    expected_hash = 'c01bded1a737ba0405d7deedd13de3c6d8173584daadc47682b83449b93bd6d5'
    dest = ROOT / 'data/lmdb' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix('.mdb.part')
    with request(f'https://huggingface.co/api/datasets/{repo}') as response:
        revision = json.load(response)['sha']
    while not dest.is_file() and (partial.stat().st_size if partial.exists() else 0) < expected_size:
        offset = partial.stat().st_size if partial.exists() else 0
        end = min(offset + 32 * 1024 * 1024 - 1, expected_size - 1)
        url = f'https://huggingface.co/datasets/{repo}/resolve/{revision}/{name}?download=true&offset={offset}'
        with request(url, {'Range': f'bytes={offset}-{end}'}) as response, partial.open('ab') as output:
            if response.status != 206 or not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                raise RuntimeError('Unexpected range response')
            count = 0
            while count < end - offset + 1:
                block = response.read(min(1024 * 1024, end - offset + 1 - count))
                if not block:
                    break
                output.write(block)
                count += len(block)
            if not count:
                raise RuntimeError('Empty download')
        print(f'CSL dev data: {partial.stat().st_size / 2**20:.0f} / {expected_size / 2**20:.0f} MiB', flush=True)
    check = dest if dest.exists() else partial
    digest = hashlib.sha256(check.read_bytes()).hexdigest()
    if digest != expected_hash:
        raise RuntimeError('Dataset hash mismatch; refusing to decode unverified records')
    if not dest.exists():
        partial.replace(dest)
    report = {'dataset': repo, 'revision': revision, 'sha256_verified': True,
              'smplx_model_used': False, 'inference_executed': False,
              'scope': 'Official dataset pose-array validation only; not text generation or photoreal avatar output.',
              'clips_checked': 0, 'invalid': [], 'samples': []}
    out = ROOT / 'outputs/pose-validation'
    out.mkdir(parents=True, exist_ok=True)
    with lmdb.open(str(dest.parent), readonly=True, lock=False, readahead=False) as env:
        with env.begin() as txn:
            metadata = pickle.loads(txn.get(b'__meta__'))
            ids = metadata['clip_ids']
            report['clips_total'] = len(ids)
            for index, clip_id in enumerate(ids):
                raw = txn.get(clip_id.encode('utf-8'))
                with np.load(io.BytesIO(raw), allow_pickle=True) as data:
                    frames = len(data['segment'])
                    problems = []
                    for field, minimum in [('left_features', 90), ('right_features', 90), ('body_features', 126), ('face_features', 56)]:
                        arr = data[field]
                        if arr.ndim != 2 or arr.shape[0] != frames or arr.shape[1] < minimum:
                            problems.append(f'{field}:unexpected_shape:{arr.shape}')
                        if not np.isfinite(arr).all():
                            problems.append(f'{field}:nonfinite')
                    if not np.isin(data['segment'], [0, 1, 2]).all():
                        problems.append('invalid_segment_labels')
                    if problems:
                        report['invalid'].append({'id': clip_id, 'errors': problems})
                    report['clips_checked'] += 1
                    if index < 5:
                        report['samples'].append({'id': clip_id, 'text': str(data['translation'][0]),
                            'gloss': str(data['gloss'][0]), 'frames': frames,
                            'shape': {f: list(data[f].shape) for f in ['left_features', 'right_features', 'body_features', 'face_features']}})
                    if index == 0:
                        np.savez_compressed(out / 'first-real-sample.npz', **{k: data[k] for k in data.files})
    report['passed'] = not report['invalid'] and report['clips_checked'] > 0
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
