"""Functional smoke tests of bundled scripts, not just --help flags."""
from __future__ import annotations
import json
import sqlite3
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from omniforge.core import bundled_root


def execute(name: str, *arguments: str) -> dict:
    script = next((bundled_root() / name / 'scripts').glob('*.py'))
    process = subprocess.run([sys.executable, str(script), *map(str, arguments)],
                             capture_output=True, text=True, timeout=15)
    assert process.returncode == 0, f'{name}: {process.stderr}'
    return json.loads(process.stdout)


def test_python_symbols(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('class Dog:\n    def bark(self): return True\nasync def run(): pass\n')
    result = execute('python-symbols', path)
    assert {x['name'] for x in result['symbols']} == {'Dog','bark','run'}


def test_openapi_inventory(tmp_path):
    path = tmp_path / 'openapi.json'
    path.write_text(json.dumps({'openapi':'3.0.3', 'paths':{'/health':{'get':{'responses':{'200':{}}}}}}))
    result = execute('openapi-inventory', path)
    assert result['count'] == 1 and result['endpoints'][0]['method'] == 'GET'


def test_secret_hygiene_never_echoes_value(tmp_path):
    secret = 'testing_secret_password_12345'
    (tmp_path / 'key.py').write_text(f'api_key="{secret}"\n')
    result = execute('secret-hygiene', tmp_path)
    assert result['findings'] and secret not in json.dumps(result)


def test_dependency_inventory(tmp_path):
    (tmp_path / 'requirements.txt').write_text('requests==2.0\n#comment\n')
    result = execute('dependency-inventory', tmp_path)
    assert result['count'] == 1


def test_sqlite_inspector(tmp_path):
    path = tmp_path / 'example.sqlite'
    conn = sqlite3.connect(path)
    conn.execute('create table things(id integer primary key)')
    conn.execute('insert into things values(1)')
    conn.commit();conn.close()
    result = execute('sqlite-inspector', path, '--count')
    assert result['objects'][0]['rows'] == 1


def test_log_triage_redacts(tmp_path):
    path = tmp_path / 'server.log'
    path.write_text('ERROR connection refused token=something-secret\n')
    result = execute('log-triage', path)
    assert result['patterns']['connection'] == 1
    assert 'something-secret' not in json.dumps(result)


def test_firmware_preflight():
    result = execute('firmware-preflight')
    assert 'python' in result and 'pio' in result['executables']


def test_repo_recon(tmp_path):
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    (tmp_path / 'file.py').write_text('print(1)')
    subprocess.run(['git','-C',str(tmp_path),'add','file.py'],check=True)
    result = execute('repo-recon', tmp_path)
    assert result['tracked_files'] == 1


def test_git_diff_review(tmp_path):
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    path = tmp_path / 'file.txt'
    path.write_text('hello\n')
    subprocess.run(['git','-C',str(tmp_path),'add','file.txt'],check=True)
    result = execute('git-diff-review', tmp_path, '--staged')
    assert any(x['path'] == 'file.txt' for x in result['files'])


class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200);self.send_header('Content-Type','text/plain');self.end_headers()
    def log_message(self, *args):
        pass


def test_api_probe_localhost():
    server = HTTPServer(('127.0.0.1',0), Handler)
    runner = threading.Thread(target=server.serve_forever, daemon=True)
    runner.start()
    try:
        result = execute('api-probe', f'http://127.0.0.1:{server.server_port}', '--timeout','3')
        assert result['status'] == 200
    finally:
        server.shutdown();server.server_close();runner.join(timeout=3)
