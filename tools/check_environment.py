"""Report research environment readiness. Does not install or modify drivers."""
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
report = {}
try:
    report['gpu'] = subprocess.check_output(['nvidia-smi', '--query-gpu=name,memory.total,driver_version',
                                            '--format=csv,noheader'], text=True).strip()
except (OSError, subprocess.CalledProcessError):
    report['gpu'] = None
report['torch_installed'] = importlib.util.find_spec('torch') is not None
if report['torch_installed']:
    import torch
    report['torch'] = torch.__version__
    report['cuda_available'] = torch.cuda.is_available()
    if report['cuda_available']:
        try:
            sample = torch.ones((32, 32), device='cuda')
            report['gpu_compute_passed'] = (sample @ sample)[0, 0].item() == 32
        except Exception as exc:
            report['gpu_error'] = str(exc)
report['checkpoints'] = {s: (ROOT / f'models/SignSparK/{s}/ema_0.9999_200000.pt').is_file()
                         for s in ('body', 'hand', 'face')}
print(json.dumps(report, ensure_ascii=False, indent=2))
