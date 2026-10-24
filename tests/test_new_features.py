"""v1.1 feature behavior and safety contract tests: no external services required."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from omniforge.semantic import hybrid_search, embedding_search
from omniforge.runtime import prepare_run, execute_run
from omniforge.agents import read_workflow, execute_workflow, agent_command
from omniforge.browser import validate_url, load_actions, browser_session
from omniforge.autocode import validate_proposal, apply_proposal, request_edits, _hash
from omniforge.provenance import build_manifest, check_manifest
from omniforge.mcp import dispatch
from omniforge.cli import main
from omniforge.core import bundled_names


def test_hybrid_search_relevance():
    assert hybrid_search('database tables schema')[0]['name'] == 'sqlite-inspector'
    assert hybrid_search('ESP32 hardware')[0]['name'] in {'firmware-preflight','esptool-chip'}
    assert len(hybrid_search('trivy security scan')) >= 1
    assert hybrid_search('')
    with pytest.raises(ValueError):
        hybrid_search('log', limit=0)


def test_neural_model_is_explicit_and_offline():
    with pytest.raises(ValueError, match='Local embedding model'):
        embedding_search('database', model_path='/missing/omniforge-model')


def test_execution_preview_requires_approval(tmp_path):
    plan = prepare_run('python-symbols', [], tmp_path, docker=True)
    assert plan['mode'] == 'docker-isolated'
    assert '--network' in plan['command']
    assert plan['command'][plan['command'].index('--network')+1] == 'none'
    result = execute_run(plan)
    assert result['status'] == 'preview-only'


def test_execution_restricts_network_and_timeout(tmp_path):
    with pytest.raises(ValueError, match='allow-network'):
        prepare_run('api-probe', [], tmp_path)
    with pytest.raises(ValueError, match='timeout'):
        prepare_run('log-triage', [], tmp_path, timeout=10000)
    with pytest.raises(ValueError):
        prepare_run('../../outside', [], tmp_path)


def test_execution_host_optin_smoke(tmp_path):
    plan = prepare_run('firmware-preflight', [], tmp_path, docker=False)
    response = execute_run(plan, approve=True)
    assert response['status'] == 'completed'
    assert 'executables' in response['stdout']


def test_workflow_cycle_is_rejected(tmp_path):
    workflow = tmp_path / 'cycle.json'
    workflow.write_text(json.dumps({'tasks':[{'id':'a','skill':'repo-recon','depends_on':['b']},
                                             {'id':'b','skill':'repo-recon','depends_on':['a']}]}))
    with pytest.raises(ValueError, match='cycle'):
        read_workflow(workflow)


def test_workflow_preview_and_local_execution(tmp_path):
    workflow = tmp_path / 'workflow.json'
    workflow.write_text(json.dumps({'tasks':[{'id':'one','kind':'skill','skill':'firmware-preflight'},
                                             {'id':'two','kind':'skill','skill':'firmware-preflight','depends_on':['one']}]}))
    preview = execute_workflow(workflow, tmp_path)
    assert preview['success'] and all(x['status']=='preview-only' for x in preview['tasks'])
    actual = execute_workflow(workflow, tmp_path, approve=True, unsafe_local=True)
    assert actual['success'] and all(x['status']=='completed' for x in actual['tasks'])


def test_agent_commands_must_be_allowlisted():
    with pytest.raises(ValueError, match='allowlisted'):
        agent_command({'executable':'python','args':['--version']}, allow_commands=set())
    assert agent_command({'executable':'python','args':['--version']}, allow_commands={'python'})[0]
    with pytest.raises(ValueError):
        agent_command({'executable':'../../python','args':[]}, allow_commands={'../../python'})


def test_browser_urls_private_blocked():
    for url in ['file:///tmp/a','http://example.com','https://127.0.0.1/',
                'https://localhost:443','https://u:p@example.com/', 'https://10.0.0.1/']:
        with pytest.raises(ValueError):
            validate_url(url)
    assert validate_url('https://example.org/foo') == 'example.org'
    assert validate_url('http://127.0.0.1:8080/', allow_local=True) == '127.0.0.1'
    with pytest.raises(ValueError):
        validate_url('https://example.net/',allowed_host='example.org')


def test_browser_preview_and_action_validation(tmp_path):
    response = browser_session('https://example.org',project=tmp_path)
    assert response['status']=='preview-only'
    actions=tmp_path/'steps.json'
    actions.write_text(json.dumps([{'action':'fill','selector':'#search','value':'hello'}]))
    assert load_actions(actions)[0]['action']=='fill'
    actions.write_text(json.dumps([{'action':'evaluate','script':'fetch()'}]))
    with pytest.raises(ValueError):
        load_actions(actions)
    with pytest.raises(ValueError):
        browser_session('https://example.org',project=tmp_path,screenshot='../escape.png')


def test_code_patch_validation_and_backups(tmp_path):
    file=tmp_path/'hello.py'
    file.write_text('answer = 1\n')
    original=file.read_bytes()
    data=[{'path':'hello.py','content':original.decode(),'sha256':_hash(original)}]
    proposal=validate_proposal({'edits':[{'path':'hello.py','sha256':data[0]['sha256'],'content':'answer = 2\n'}]},data)
    assert 'answer = 2' in proposal['edits'][0]['diff']
    preview=apply_proposal(proposal,tmp_path)
    assert preview['status']=='preview-only' and file.read_bytes()==original
    applied=apply_proposal(proposal,tmp_path,approve=True)
    assert file.read_text() == 'answer = 2\n'
    assert (Path(applied['backup'])/'hello.py').read_bytes()==original
    with pytest.raises(ValueError):
        apply_proposal(proposal,tmp_path,approve=True)


def test_code_patch_unapproved_file_rejected():
    with pytest.raises(ValueError,match='unapproved'):
        validate_proposal({'edits':[{'path':'secrets.env','sha256':'sha','content':'hi'}]},
                          [{'path':'hello.py','sha256':'sha','content':'hi'}])


def test_code_requires_optin_remote(tmp_path):
    (tmp_path/'main.py').write_text('x=1')
    with pytest.raises(ValueError,match='allow-remote'):
        request_edits('fix a bug',tmp_path,['main.py'],endpoint='https://api.example.org/v1/chat/completions',model='test')


def test_manifest_detects_changed_files(tmp_path):
    (tmp_path/'main.py').write_text('x=1')
    obj=build_manifest(tmp_path)
    m=tmp_path/'manifest.json'
    m.write_text(json.dumps(obj))
    assert check_manifest(tmp_path,m)['ok']
    (tmp_path/'main.py').write_text('x=2')
    report=check_manifest(tmp_path,m)
    assert not report['ok'] and report['changed']==['main.py']


def test_mcp_execution_preview_not_enabled(tmp_path):
    payload={'jsonrpc':'2.0','id':9,'method':'tools/call', 'params':{
        'name':'omniforge_run','arguments':{'name':'firmware-preflight','project':str(tmp_path),'approve':True}}}
    with patch.dict('os.environ',{'OMNIFORGE_MCP_EXECUTION':''}):
        result=dispatch(payload)
    assert 'preview-only' in result['result']['content'][0]['text']
    browser={'jsonrpc':'2.0','id':10,'method':'tools/call','params':{
        'name':'omniforge_browser','arguments':{'url':'https://example.org','project':str(tmp_path),'approve':True}}}
    with patch.dict('os.environ',{'OMNIFORGE_MCP_BROWSER':''}):
        response=dispatch(browser)
    assert 'preview-only' in response['result']['content'][0]['text']


def test_optional_tool_adapters_are_packaged(tmp_path):
    assert {'trivy-scan','kicad-drc','esptool-chip','browser-snapshot'} <= set(bundled_names())
    from omniforge.core import bundled_root
    for name in ('trivy-scan','kicad-drc','esptool-chip','browser-snapshot'):
        assert (bundled_root()/name/'scripts'/'check.py').is_file()


def test_local_model_response_produces_validated_patch(monkeypatch,tmp_path):
    import io
    from omniforge import autocode
    (tmp_path/'main.py').write_text('result = 1\n')
    sha = _hash((tmp_path/'main.py').read_bytes())
    payload={'choices':[{'message':{'content':json.dumps({'edits':[
        {'path':'main.py','sha256':sha,'content':'result = 2\n'}]})}}]}
    class FakeResponse:
        status=200
        def read(self,n): return json.dumps(payload).encode()
        def __enter__(self): return self
        def __exit__(self,*args): pass
    def fake_urlopen(req,timeout):
        body=json.loads(req.data)
        assert body['messages'][1]['content'].find('main.py') >= 0
        assert body['messages'][1]['content'].find('secret.env') == -1
        return FakeResponse()
    monkeypatch.setattr(autocode,'urlopen',fake_urlopen)
    proposal=request_edits('fix a test',tmp_path,['main.py'],
                           endpoint='http://127.0.0.1:2000/v1/chat/completions',model='fake')
    assert len(proposal['edits'])==1
    assert (tmp_path/'main.py').read_text()=='result = 1\n'


def test_manifest_bad_traversal_rejected(tmp_path):
    manifest=tmp_path/'manifest.json'
    manifest.write_text(json.dumps({'format':'omniforge-sha256-v1',
                                    'files':{'../etc/passwd':'0'*64}}))
    with pytest.raises(ValueError,match='unsafe'):
        check_manifest(tmp_path,manifest)


def test_adapter_checks_do_not_require_upstream_binaries():
    import subprocess
    from omniforge.core import bundled_root
    for name in ('trivy-scan','kicad-drc','esptool-chip','browser-snapshot'):
        script=bundled_root()/name/'scripts'/'check.py'
        cp=subprocess.run([sys.executable,str(script),'--check'],text=True,
                          capture_output=True,timeout=10)
        assert cp.returncode==0,cp.stderr
        obj=json.loads(cp.stdout)
        assert 'available' in obj


def test_model_provider_redirect_never_follows_or_leaks_auth(tmp_path):
    """Real local HTTP 302 must not forward a source file or bearer token."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Redirect(BaseHTTPRequestHandler):
        forwarded = False

        def do_POST(self):
            self.send_response(302)
            self.send_header("Location", "/unexpected-destination")
            self.end_headers()

        def do_GET(self):
            self.__class__.forwarded = True
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"unexpected")

        def log_message(self, *args):
            pass

    source = tmp_path / "module.py"
    source.write_text("secret_test_only = 'PRIVATE'\n")
    server = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(ValueError, match="redirects are disabled"):
            request_edits("format this file", tmp_path, ["module.py"],
                          endpoint=f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
                          model="fixture", api_key="test-token")
        assert Redirect.forwarded is False
        assert source.read_text() == "secret_test_only = 'PRIVATE'\n"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_model_endpoint_rejects_embedded_credentials_and_fragments(tmp_path):
    (tmp_path / "main.py").write_text("valid = True")
    for endpoint in ("https://user:password@api.example.org/v1/chat/completions",
                     "https://api.example.org/v1/chat/completions#secret"):
        with pytest.raises(ValueError, match="endpoint"):
            request_edits("refactor", tmp_path, ["main.py"],
                          endpoint=endpoint, model="fixture", allow_remote=True)
