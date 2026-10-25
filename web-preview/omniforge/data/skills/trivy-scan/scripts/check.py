"""Trivy adapter. Explicit execution only; network DB download may be required."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description='Trivy filesystem scan adapter')
p.add_argument('--check', action='store_true')
p.add_argument('--run', action='store_true')
p.add_argument('--target', default='.')
p.add_argument('--allow-network', action='store_true')
a = p.parse_args()
binary = shutil.which('trivy')
if not a.run:
    print(json.dumps({'tool':'trivy','available':bool(binary),'network_required_for_database_updates':True}))
elif not binary:
    p.error('Trivy is not installed')
elif not a.allow_network:
    p.error('Explicit --allow-network required; Trivy may download vulnerability DB')
else:
    target = Path(a.target).resolve()
    if not target.is_dir():
        p.error('Target must be a directory')
    command = [binary, 'fs', '--scanners', 'vuln,secret', '--format', 'json', str(target)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
    print(json.dumps({'tool':'trivy','exit_code':result.returncode,'report':result.stdout[:200000],
                      'stderr':result.stderr[:3000]}))
    raise SystemExit(result.returncode)
