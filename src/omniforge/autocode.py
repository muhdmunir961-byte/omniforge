"""Optional BYOK OpenAI-compatible patch proposals with human-reviewed application.

Model output is never treated as a shell command. Only explicitly listed local
files may be edited, and every edit is protected by an original SHA-256 lease.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from .core import secure_project_path

MAX_FILES = 5
MAX_FILE_BYTES = 32_000
SYSTEM = ("You are a code-change assistant. Return ONLY a JSON object with an 'edits' array. "
          "Each edit must contain 'path', 'sha256' (the provided original checksum), and "
          "'content' (the COMPLETE replacement file). Modify only provided files. "
          "Do not request shell commands, secrets, or unrelated paths. If uncertain, return edits: [].")


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _get_files(project: Path, paths: list[str]) -> list[dict]:
    if not 1 <= len(paths) <= MAX_FILES or len(set(paths)) != len(paths):
        raise ValueError('Specify 1..5 distinct files')
    result = []
    for name in paths:
        if not isinstance(name, str) or name.startswith('.') or '\x00' in name:
            raise ValueError('Hidden files and invalid paths are not supported')
        p = secure_project_path(project, name)
        if not p.is_relative_to(project) or not p.is_file() or p.is_symlink():
            raise ValueError(f'File must exist inside project: {name}')
        if p.stat().st_size > MAX_FILE_BYTES or p.suffix.lower() not in {'.py','.js','.ts','.tsx','.jsx','.json','.md','.css','.html','.go','.rs'}:
            raise ValueError('Unsupported or excessively large source file')
        data = p.read_bytes()
        content = data.decode('utf-8')
        result.append({'path':str(p.relative_to(project)), 'sha256':_hash(data), 'content':content})
    return result


def request_edits(task: str, project: Path, paths: list[str], *, endpoint: str, model: str,
                  api_key: str | None = None, allow_remote: bool = False,
                  timeout: int = 45) -> dict:
    root = project.expanduser().resolve()
    if not root.is_dir():
        raise ValueError('Invalid project directory')
    if not task.strip() or len(task) > 4000 or not model.strip():
        raise ValueError('A short task and model are required')
    parsed = urlparse(endpoint)
    if parsed.scheme not in {'https', 'http'} or not parsed.hostname or parsed.username:
        raise ValueError('Invalid OpenAI-compatible endpoint')
    local = parsed.hostname in {'localhost', '127.0.0.1', '::1'}
    if parsed.scheme != 'https' and not local:
        raise ValueError('Remote model endpoint must use HTTPS')
    if not local and not allow_remote:
        raise ValueError('Remote code sharing requires --allow-remote')
    if not 1 <= timeout <= 120:
        raise ValueError('Invalid timeout')
    files = _get_files(root, paths)
    # Explicit file list, never recursively upload a repository or credentials.
    prompt = json.dumps({'task':task, 'files':files}, ensure_ascii=False)
    body = json.dumps({'model':model, 'messages':[{'role':'system','content':SYSTEM},
                              {'role':'user','content':prompt}], 'temperature':0}).encode()
    key = api_key if api_key is not None else os.environ.get('OMNIFORGE_API_KEY','')
    headers = {'Content-Type':'application/json'}
    if key:
        headers['Authorization'] = f'Bearer {key}'
    req = Request(endpoint, data=body, headers=headers, method='POST')
    with urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError(f'Provider returned HTTP {response.status}')
        response_data = json.loads(response.read(512_000).decode('utf-8'))
    try:
        raw = response_data['choices'][0]['message']['content']
        proposal = json.loads(raw)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Provider did not return the required JSON edits payload') from exc
    return validate_proposal(proposal, files)


def validate_proposal(proposal: object, originals: list[dict]) -> dict:
    if not isinstance(proposal, dict) or not isinstance(proposal.get('edits'), list):
        raise ValueError('Expected {"edits": [...]}')
    original_map = {f['path']:f for f in originals}
    validated = []
    used = set()
    for edit in proposal['edits']:
        if not isinstance(edit, dict):
            raise ValueError('Malformed edit')
        name = edit.get('path')
        if name not in original_map or name in used:
            raise ValueError('Model attempted an unapproved or duplicate file edit')
        orig = original_map[name]
        content = edit.get('content')
        if edit.get('sha256') != orig['sha256'] or not isinstance(content, str) or '\x00' in content or len(content.encode('utf-8')) > 128_000:
            raise ValueError('Malformed content or original SHA-256 mismatch')
        diff = ''.join(difflib.unified_diff(orig['content'].splitlines(keepends=True),
                                            content.splitlines(keepends=True),
                                            fromfile=f'a/{name}', tofile=f'b/{name}'))
        validated.append({'path':name, 'sha256':orig['sha256'], 'new_content':content,
                          'diff':diff[:20_000], 'diff_truncated':len(diff)>20_000})
        used.add(name)
    return {'status':'proposal', 'edits':validated, 'files_submitted':len(originals),
            'note':'Review diffs before --apply; remote providers receive the selected file contents.'}


def apply_proposal(proposal: dict, project: Path, *, approve: bool = False) -> dict:
    if not approve:
        return {'status':'preview-only','diffs':[{'path':e['path'],'diff':e['diff']} for e in proposal['edits']]}
    root = project.expanduser().resolve()
    edits = proposal['edits']
    # Validate ALL hashes before mutating anything.
    targets = []
    for edit in edits:
        target = secure_project_path(root, edit['path'])
        if not target.is_relative_to(root) or not target.is_file() or target.is_symlink() or _hash(target.read_bytes()) != edit['sha256']:
            raise ValueError(f'Original file changed: {edit["path"]}')
        targets.append(target)
    backup_root = secure_project_path(root, '.omniforge', 'backups', datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    backup_root.mkdir(parents=True, exist_ok=False)
    try:
        for target in targets:
            backup = backup_root / target.relative_to(root)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
        for edit, target in zip(edits, targets):
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=target.parent,delete=False) as out:
                out.write(edit['new_content'])
                temp_path = Path(out.name)
            try:
                os.chmod(temp_path, target.stat().st_mode)
                os.replace(temp_path, target)
            finally:
                temp_path.unlink(missing_ok=True)
    except Exception:
        for target in targets:
            backup = backup_root / target.relative_to(root)
            if backup.exists():
                shutil.copy2(backup, target)
        raise
    return {'status':'applied','files':[e['path'] for e in edits], 'backup':str(backup_root)}
