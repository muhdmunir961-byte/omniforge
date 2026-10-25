"""Read-only esptool chip information; chip may reset after connection."""
import argparse
import json
import shutil
import subprocess

p = argparse.ArgumentParser(description='ESP32 chip information via esptool')
p.add_argument('--check',action='store_true')
p.add_argument('--run',action='store_true')
p.add_argument('--port')
a = p.parse_args()
binary = shutil.which('esptool')
if not a.run:
    print(json.dumps({'tool':'esptool','available':bool(binary),'note':'Serial access may reset the device'}))
elif not binary:
    p.error('esptool (v5+) not found')
elif not a.port or not (a.port.startswith('/dev/') or a.port.upper().startswith('COM')):
    p.error('--port must name a serial device (/dev/* or COM*)')
else:
    result = subprocess.run([binary, '--port', a.port, 'chip-id'],
                            capture_output=True,text=True,timeout=40,check=False)
    print(json.dumps({'tool':'esptool','exit_code':result.returncode,
                      'stdout':result.stdout[:8000],'stderr':result.stderr[:4000]}))
    raise SystemExit(result.returncode)
