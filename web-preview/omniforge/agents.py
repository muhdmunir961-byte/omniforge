"""Local DAG task coordination for bundled skills and explicitly approved agent CLIs.

No model is bundled. External agent commands require user-specified executable
allowlisting, a consent flag, and a locally installed compatible CLI.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from .runtime import prepare_run, execute_run

MAX_TASKS = 24


def read_workflow(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding='utf-8'))
    tasks = data.get('tasks')
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= MAX_TASKS:
        raise ValueError('Workflow requires 1..24 tasks')
    ids = set()
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get('id'), str) or not task['id'].replace('-', '').replace('_', '').isalnum():
            raise ValueError('Each task needs a simple id')
        if task['id'] in ids:
            raise ValueError('Duplicate task id')
        ids.add(task['id'])
        if task.get('kind', 'skill') not in ('skill', 'agent'):
            raise ValueError('Task kind must be skill or agent')
        if not isinstance(task.get('args', []), list) or not all(isinstance(x, str) for x in task.get('args', [])):
            raise ValueError('Task args must be strings')
        if not isinstance(task.get('depends_on', []), list):
            raise ValueError('depends_on must be a list')
    for task in tasks:
        if any(d not in ids or d == task['id'] for d in task.get('depends_on', [])):
            raise ValueError('Unknown or self-referential dependency')
    pending = {task['id']: set(task.get('depends_on', [])) for task in tasks}
    completed = set()
    while pending:
        ready = {key for key, deps in pending.items() if deps <= completed}
        if not ready:
            raise ValueError('Workflow contains a dependency cycle')
        completed |= ready
        pending = {k: v for k, v in pending.items() if k not in ready}
    return tasks


def agent_command(task: dict, *, allow_commands: set[str]) -> list[str]:
    executable = task.get('executable')
    if not isinstance(executable, str) or executable not in allow_commands:
        raise ValueError('Agent executable must be explicitly allowlisted')
    if os.path.basename(executable) != executable or not executable.replace('-', '').replace('_', '').isalnum():
        raise ValueError('Agent executable must be a simple filename')
    if not shutil.which(executable):
        raise ValueError(f'Agent executable unavailable: {executable}')
    args = task.get('args', [])
    if len(args) > 32 or any(len(arg) > 3000 or '\x00' in arg for arg in args):
        raise ValueError('Invalid agent arguments')
    return [shutil.which(executable) or executable, *args]


def execute_workflow(path: Path, project: Path, *, approve: bool = False,
                     unsafe_local: bool = False, allow_network: bool = False,
                     allow_commands: set[str] | None = None, workers: int = 2,
                     timeout: int = 60) -> dict:
    if not 1 <= workers <= 4 or not 1 <= timeout <= 300:
        raise ValueError('workers must be 1..4 and timeout 1..300')
    tasks = read_workflow(path)
    project = project.resolve()
    allow_commands = allow_commands or set()
    def perform(task: dict) -> dict:
        if task.get('kind', 'skill') == 'skill':
            plan = prepare_run(task['skill'], task.get('args', []), project,
                               docker=not unsafe_local, allow_network=allow_network, timeout=timeout)
            result = execute_run(plan, approve=approve)
        else:
            command = agent_command(task, allow_commands=allow_commands)
            if not approve:
                result = {'status': 'preview-only', 'command': command}
            else:
                try:
                    finished = subprocess.run(command, cwd=project, timeout=timeout,
                                              capture_output=True, text=True, stdin=subprocess.DEVNULL,
                                              env={'PATH': os.defpath, 'PYTHONIOENCODING':'utf-8'})
                    result = {'status': 'completed' if finished.returncode == 0 else 'failed',
                              'exit_code': finished.returncode,
                              'stdout': finished.stdout[:20000], 'stderr': finished.stderr[:10000]}
                except subprocess.TimeoutExpired:
                    result = {'status': 'timeout'}
        return {'id': task['id'], **result}
    outstanding = {task['id']: task for task in tasks}
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        while outstanding:
            ready = [task for task in outstanding.values() if all(d in results for d in task.get('depends_on', []))]
            if not ready:
                raise ValueError('Unresolvable dependency graph')
            futures = {}
            for task in ready:
                dependencies = task.get('depends_on', [])
                if any(results[d]['status'] not in {'completed', 'preview-only'} for d in dependencies):
                    results[task['id']] = {'id': task['id'], 'status':'skipped', 'reason':'dependency failed'}
                else:
                    futures[pool.submit(perform, task)] = task['id']
            for future in as_completed(futures):
                ident = futures[future]
                try:
                    results[ident] = future.result()
                except (OSError, ValueError) as exc:
                    results[ident] = {'id': ident, 'status': 'failed', 'error':str(exc)}
            for task in ready:
                outstanding.pop(task['id'])
    return {'workflow': str(path), 'approved': approve, 'tasks': list(results.values()),
            'success': all(x['status'] in ('completed', 'preview-only') for x in results.values())}
