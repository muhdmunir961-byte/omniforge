"""Opt-in ephemeral Playwright browser automation with constrained actions.

Playwright and a browser binary are optional, never installed automatically.
"""
from __future__ import annotations

import ipaddress
import json
import socket
from pathlib import Path
from urllib.parse import urlparse
from .core import secure_project_path

MAX_STEPS = 15


def validate_url(url: str, *, allow_local: bool = False, allowed_host: str | None = None) -> str:
    if not isinstance(url, str) or len(url) > 2048:
        raise ValueError('Invalid URL')
    parsed = urlparse(url)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Only HTTP(S) URLs without embedded credentials are supported')
    if parsed.scheme != 'https' and not allow_local:
        raise ValueError('Remote browsing requires HTTPS')
    host = parsed.hostname.lower().rstrip('.')
    if allowed_host and host != allowed_host:
        raise ValueError('Cross-domain navigation blocked')
    if host in {'localhost', 'localhost.localdomain'}:
        if not allow_local:
            raise ValueError('Local addresses are disabled by default')
    else:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global and not allow_local:
            raise ValueError('Private and reserved network addresses are blocked')
        if host.endswith(('.local', '.internal', '.localhost')) and not allow_local:
            raise ValueError('Internal hostnames are blocked')
    return host


def load_actions(path: Path | None) -> list[dict]:
    if path is None:
        return []
    content = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(content, list) or len(content) > MAX_STEPS:
        raise ValueError('Expected a list with at most 15 browser actions')
    for step in content:
        if not isinstance(step, dict) or step.get('action') not in {'click','fill','wait','screenshot','goto'}:
            raise ValueError('Unsupported browser action')
        if step['action'] in {'click','fill'} and (not isinstance(step.get('selector'), str) or len(step['selector']) > 250):
            raise ValueError('Invalid selector')
        if step['action'] == 'fill' and (not isinstance(step.get('value'), str) or len(step['value']) > 2000):
            raise ValueError('Invalid fill content')
        if step['action'] == 'wait' and (type(step.get('milliseconds')) is not int or not 0 <= step['milliseconds'] <= 5000):
            raise ValueError('wait milliseconds must be 0..5000')
        if step['action'] == 'goto' and not isinstance(step.get('url'), str):
            raise ValueError('goto requires url')
    return content


def browser_session(url: str, *, steps: list[dict] | None = None, project: Path,
                    screenshot: str | None = None, approve: bool = False,
                    allow_local: bool = False) -> dict:
    host = validate_url(url, allow_local=allow_local)
    steps = steps or []
    for step in steps:
        if step.get('action') == 'goto':
            validate_url(step['url'], allow_local=allow_local, allowed_host=host)
    root = project.resolve()
    if not root.is_dir():
        raise ValueError('Project must exist')
    shot = None
    if screenshot:
        shot = secure_project_path(root, screenshot)
        if not shot.is_relative_to(root) or shot.suffix.lower() != '.png':
            raise ValueError('Screenshot must be a .png inside the project directory')
    preview = {'url': url, 'actions': len(steps), 'screenshot': str(shot) if shot else None,
               'status': 'preview-only'}
    if not approve:
        return preview
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError as exc:
        raise ValueError('Playwright not installed; run pip install playwright && playwright install chromium') from exc
    # Resolve remote hostname before launching Chromium. This reduces accidental
    # access to private targets, but is not a full DNS-rebinding defense.
    if not allow_local:
        try:
            resolved = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise ValueError('Browser target DNS lookup failed') from exc
        for item in resolved:
            if not ipaddress.ip_address(item[4][0]).is_global:
                raise ValueError('Browser target resolves to a private or reserved address')
    # One fresh browser context per run, no persisted cookies.
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=False, service_workers='block')
        page = context.new_page()
        def restrict(route):
            request_url = route.request.url
            if request_url.startswith(('data:', 'about:', 'blob:')):
                return route.continue_()
            try:
                validate_url(request_url, allow_local=allow_local, allowed_host=host)
                return route.continue_()
            except ValueError:
                return route.abort()
        context.route('**/*', restrict)
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        for step in steps:
            action = step['action']
            if action == 'goto':
                page.goto(step['url'], wait_until='domcontentloaded', timeout=15000)
            elif action == 'click':
                page.locator(step['selector']).first.click(timeout=5000)
            elif action == 'fill':
                page.locator(step['selector']).first.fill(step['value'], timeout=5000)
            elif action == 'wait':
                page.wait_for_timeout(step['milliseconds'])
            elif action == 'screenshot' and shot:
                shot.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(shot), full_page=True)
        if shot and not shot.is_file():
            shot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shot), full_page=True)
        result = {'status':'completed', 'url':page.url, 'title':page.title(),
                  'text':page.locator('body').inner_text(timeout=5000)[:10000],
                  'links':page.locator('a[href]').evaluate_all('(els) => els.slice(0,50).map(a => ({text:a.innerText.slice(0,100), href:a.href}))'),
                  'screenshot':str(shot) if shot else None}
        context.close()
        browser.close()
        return result
