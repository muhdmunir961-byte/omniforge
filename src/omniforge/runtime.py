"""Permission-gated skill execution; Docker is required for the isolated mode.

This module deliberately does not claim the host subprocess is a sandbox.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from .core import bundled_names, bundled_root

NETWORK_SKILLS = frozenset({'api-probe', 'browser-snapshot', 'trivy-scan'})


def get_skill_script(name: str) -> Path:
    if name not in bundled_names():
        raise ValueError('Unknown bundled skill')
    scripts = sorted((bundled_root() / name / 'scripts').glob('*.py'))
    if len(scripts) != 1 or scripts[0].is_symlink():
        raise ValueError('Skill must have exactly one safe Python script')
    return scripts[0].resolve()


def prepare_run(name: str, args: list[str], project: Path, *, docker: bool = True,
                allow_network: bool = False, timeout: int = 30) -> dict:
    if not 1 <= timeout <= 300:
        raise ValueError('timeout must be between 1 and 300 seconds')
    if any('\x00' in arg or '\n' in arg or len(arg) > 2048 for arg in args) or len(args) > 30:
        raise ValueError('Malformed script arguments')
    script = get_skill_script(name)
    root = project.expanduser().resolve()
    if not root.is_dir():
        raise ValueError('Project must be an existing directory')
    if name in NETWORK_SKILLS and not allow_network:
        raise ValueError(f'{name} requires --allow-network; network access is opt-in')
    if docker:
        # The project and skill script are mounted read-only. No secrets or host
        # home directory are forwarded. Rootfs is read-only with a tmpfs /tmp.
        mapped_args = []
        for arg in args:
            mapped_args.append('/workspace/' + str(Path(arg).relative_to(root))
                               if Path(arg).is_absolute() and Path(arg).is_relative_to(root)
                               else arg)
        # Run as the invoking user's UID/GID, not root. With all capabilities
        # dropped, container root cannot read user-owned 0700 project directories.
        # Matching the host owner preserves access without restoring root bypass.
        identity = ['--user', f'{os.getuid()}:{os.getgid()}'] if hasattr(os, 'getuid') else []
        command = [shutil.which('docker') or 'docker', 'run', '--rm', '--pull=never', '--init', '--read-only', '--cap-drop=ALL',
                   '--security-opt=no-new-privileges', *identity, '--pids-limit=64',
                   '--memory=256m', '--cpus=1', '--tmpfs', '/tmp:rw,noexec,nosuid,size=32m',
                   '--network', 'bridge' if allow_network else 'none',
                   '--mount', f'type=bind,src={root},dst=/workspace,readonly',
                   '--mount', f'type=bind,src={script},dst=/opt/skill.py,readonly',
                   '--workdir', '/workspace', 'python:3.13-alpine', 'python', '/opt/skill.py',
                   *mapped_args]
    else:
        command = [sys.executable, str(script), *args]
    return {'skill': name, 'mode': 'docker-isolated' if docker else 'host-unisolated',
            'network': allow_network, 'project': str(root), 'timeout': timeout,
            'command': command, 'approved': False}


def execute_run(plan: dict, *, approve: bool = False) -> dict:
    if not approve:
        return dict(plan, status='preview-only', note='No command executed; pass --approve to run')
    if not isinstance(plan.get('command'), list):
        raise ValueError('Malformed execution plan')
    if plan['mode'] == 'docker-isolated' and not shutil.which('docker'):
        raise ValueError('Docker must be installed for isolated execution')
    try:
        result = subprocess.run(plan['command'], cwd=plan['project'],
                                capture_output=True, text=True, timeout=plan['timeout'],
                                check=False, env=_minimal_environment(plan['mode']),
                                stdin=subprocess.DEVNULL)
        return {'skill': plan['skill'], 'mode': plan['mode'], 'exit_code': result.returncode,
                'stdout': result.stdout[:30000], 'stderr': result.stderr[:15000],
                'status': 'completed' if result.returncode == 0 else 'failed'}
    except subprocess.TimeoutExpired:
        return {'skill': plan['skill'], 'status': 'timeout', 'timeout': plan['timeout']}


def _minimal_environment(mode: str) -> dict[str, str]:
    env = {'PATH': os.pathsep.join(['/usr/local/bin', '/usr/bin', '/bin']), 'PYTHONIOENCODING': 'utf-8'}
    if mode == 'docker-isolated':
        for key in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'HOME', 'XDG_RUNTIME_DIR'):
            if key in os.environ:
                env[key] = os.environ[key]
    return env
