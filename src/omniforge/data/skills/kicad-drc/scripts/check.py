"""KiCad PCB DRC adapter. Writes a DRC report only when explicitly requested."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description='KiCad PCB design-rule checker')
p.add_argument('--check', action='store_true')
p.add_argument('--run', action='store_true')
p.add_argument('--board')
p.add_argument('--report')
a = p.parse_args()
binary = shutil.which('kicad-cli')
if not a.run:
    print(json.dumps({'tool':'kicad-cli','available':bool(binary)}))
elif not binary:
    p.error('kicad-cli not installed')
else:
    if not a.board:
        p.error('--board required')
    board = Path(a.board).resolve()
    if not board.is_file() or board.suffix.lower() != '.kicad_pcb':
        p.error('Board must be an existing .kicad_pcb file')
    report = Path(a.report).resolve() if a.report else board.with_suffix('.drc.txt')
    if report == board or not report.parent.is_dir():
        p.error('Invalid report path')
    result = subprocess.run([binary, 'pcb', 'drc', '--output', str(report), str(board)],
                            capture_output=True, text=True, timeout=120, check=False)
    print(json.dumps({'tool':'kicad-cli','exit_code':result.returncode,'report':str(report),
                      'stdout':result.stdout[:5000],'stderr':result.stderr[:5000]}))
    raise SystemExit(result.returncode)
