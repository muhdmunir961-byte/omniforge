/* OmniForge product walkthrough. Evidence taken from an actual CLI Actions artifact.
   UI remains static: no remote shell, no wallet, no secrets, no server-side code. */
const $ = id => document.getElementById(id);
const BASE='https://github.com/muhdmunir961-byte/omniforge';
const E2E=`${BASE}/blob/main/tests/test_live_integrations.py`;
const EVM=`${BASE}/blob/main/tests/test_blockchain_evm.py`;
const clip = text => String(text??'');
function safe(value){return clip(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function trunc(value,limit=2400){const text=clip(value).trim();return text.length<=limit?text:text.slice(0,limit)+'\n… [output clipped; inspect CI trace for the full recording]' }
const STORIES=[
  {id:'search',number:'01',cat:'discover',tag:'DISCOVERY / RECORDED CLI',title:'Find the right debugging skill',short:'Find → rank → load',problem:'A Python API returns errors. Which of the 14 tools should your coding assistant load instead of stuffing every skill into its context?',outcome:'Local search ranked log-triage first (score 8.32972), then lazy loading let the user inspect only that skill. CI budget estimated 709 vs 3,034 tokens.',before:'14 skills available; no selected skill.',after:'log-triage ranked #1; selective loading.',source:'ci',url:'https://github.com/muhdmunir961-byte/omniforge/actions/runs/40131838901',steps:[
    {title:'Describe the problem',stage:'INPUT',desc:'Ask the local ranking engine for tools relevant to the error. No remote model request is needed.',command:'omniforge search "API errors"',trace:'Hybrid search',note:'RANKED RESULTS',before:'Undirected search',after:'log-triage returned first'},
    {title:'Measure context overhead',stage:'PROCESS',desc:'Compare loading one SKILL.md on demand versus all bundled instructions at once. Numbers are heuristic estimates, not measured token bills.',command:'omniforge budget --selected log-triage',trace:'Token estimate',note:'APPROXIMATE BUDGET',before:'All skills in context',after:'3,034 vs 709 estimated tokens'},
    {title:'Inspect the skill',stage:'CONTROL',desc:'Load the exact SKILL.md instructions. Reading the skill never executes its scripts.',command:'omniforge load log-triage',trace:'Lazy load SKILL.md',note:'SKILL DOCUMENT',before:'Only skill metadata',after:'Full instructions available'},
    {title:'Use the result in your agent',stage:'RESULT',desc:'Now you know which skill to install or manually approve. The workflow remains human-controlled; discovery is not automatic execution.',command:'omniforge install log-triage --agent codex --project .',trace:null,display:'Expected destination after explicit CLI invocation:\n.agents/skills/log-triage/SKILL.md\n\nThe exact installation is tested in scenario 02.',note:'NEXT ACTION',before:'No log-triage instructions in agent',after:'Ready for reviewed installation'}
  ]},
  {id:'install',number:'02',cat:'discover',tag:'AGENT SETUP / RECORDED CLI',title:'Install a skill into a coding assistant',short:'Inspect → install → configure',problem:'You want a reusable AI-agent skill in Codex and a working local VS Code bridge without manually copying configuration across directories.',outcome:'CI created .agents/skills/log-triage/SKILL.md, .vscode/mcp.json, and GitHub instruction files in a temporary project.',before:'app.py + pyproject.toml, no agent skill.',after:'.agents/skills/log-triage + VS Code MCP.',source:'ci',url:'https://github.com/muhdmunir961-byte/omniforge/actions/runs/40131838901',steps:[
    {title:'Inspect current project',stage:'INPUT',desc:'Detect Python and check top-level files before changing anything.',command:'omniforge inspect .',trace:'Project detection',note:'PROJECT DETECTION',before:'Unknown project type',after:'Python detected'},
    {title:'Install a reviewed skill',stage:'PROCESS',desc:'Copy only the requested bundled skill to the chosen agent folder; refuse overwriting without force.',command:'omniforge install log-triage --agent codex --project .',trace:'Install skill',note:'FILE CREATED',before:'No Codex log-triage skill',after:'.agents/skills/log-triage'},
    {title:'Prepare VS Code integration',stage:'PROCESS',desc:'Generate the local MCP configuration and assistant instructions. No cloud login is required.',command:'omniforge setup-vscode --project .',trace:'VS Code setup',note:'CONFIG WRITTEN',before:'MCP not set up in VS Code',after:'.vscode/mcp.json'},
    {title:'Inspect the resulting files',stage:'RESULT',desc:'The result is normal files that you can read, edit, commit or remove. The extension is not a remotely hosted agent.',command:'find .agents .vscode .github/instructions -type f',display:'.agents/skills/log-triage/SKILL.md\n.vscode/mcp.json\n.github/instructions/omniforge.instructions.md\n\nThe first three steps are captured from an actual temporary CI project.',note:'FILE TREE / DERIVED FROM TEST',before:'No local agent configuration',after:'Two instruction/config locations'}
  ]},
  {id:'workflow',number:'03',cat:'automate',tag:'ORCHESTRATION / CI + E2E',title:'Coordinate dependent developer tasks',short:'Plan → preview → approve',problem:'You need one task to inspect a Python file, then a second task to use its completion as a prerequisite—without silent execution.',outcome:'A real Docker E2E test verifies both tasks complete in dependency order when manually approved. By default, the CLI only previews them.',before:'Two unrelated actions, no ordering.',after:'inspect → confirm; both completed in Docker E2E.',source:'mixed',url:E2E,steps:[
    {title:'Request a reviewed plan',stage:'INPUT',desc:'Search for likely skills and return a deterministic, human-reviewable plan. It is not a free-running autonomous coding agent.',command:'omniforge plan "debug ESP32 firmware"',trace:'Workflow plan',note:'DRY-RUN PLAN',before:'No structured plan',after:'Ordered skill suggestions'},
    {title:'Define the dependency graph',stage:'PROCESS',desc:'Tasks are validated for duplicates, missing dependencies, and cycles before the CLI attempts execution.',command:'cat workflow.json',display:'{"tasks": [\n  {"id":"inspect","kind":"skill","skill":"python-symbols","args":["sample.py"]},\n  {"id":"confirm","kind":"skill","skill":"python-symbols","args":["sample.py"],"depends_on":["inspect"]}\n]}',note:'E2E TEST FIXTURE',before:'Unordered list',after:'One explicit dependency'},
    {title:'Preview before approval',stage:'CONTROL',desc:'No --approve means preview-only. The recorded CI workflow confirms this with two preview-only tasks.',command:'omniforge orchestrate workflow.json --project .',trace:'DAG orchestration preview',note:'PREVIEW-ONLY',before:'Unknown actions',after:'Visible Docker commands; no execution'},
    {title:'Execute only if authorized',stage:'RESULT',desc:'E2E: execute_workflow(..., approve=True) runs the two Python AST tasks in restricted Docker containers. Test asserts both return completed and stdout contains ready.',command:'omniforge orchestrate workflow.json --project . --approve',display:'E2E assertions (test_live_docker_dependency_workflow):\nresult["success"] is True\n[t["id"] for t in result["tasks"]] == ["inspect", "confirm"]\nall(t["status"] == "completed" for t in result["tasks"])\nall("ready" in t["stdout"] for t in result["tasks"])',note:'ACTUAL E2E ASSERTIONS',before:'Preview-only status',after:'2 tasks completed after explicit approval'}
  ]},
  {id:'integrity',number:'04',cat:'protect',tag:'PROVENANCE / RECORDED CLI',title:'Catch source tampering before release',short:'Snapshot → edit → detect → restore',problem:'Someone edits app.py after you create a release checkpoint. Can you prove the current files no longer match the recorded snapshot?',outcome:'CI detected app.py in files.modified, exited nonzero, recorded a new snapshot seq=1 and returned to a clean verify.',before:'Recorded app.py: answer = 42',after:'Modified app.py flagged; new snapshot verified.',source:'ci',url:'https://github.com/muhdmunir961-byte/omniforge/actions/runs/40131838901',steps:[
    {title:'Record a baseline',stage:'INPUT',desc:'Initialize the strict v2 local ledger, then hash selected project files. Each record stores an immutable snapshot and scan policy.',command:'ofprov init --project .\nofprov snapshot --project .',trace:'Create snapshot',note:'INITIAL SNAPSHOT',before:'No ledger',after:'seq 0 + SHA-256 entry hash'},
    {title:'Verify the baseline',stage:'PROCESS',desc:'Compare source files and a separate, externally trusted seq/head if you have one.',command:'ofprov verify --project . --check-files --expected-head HEAD --expected-seq 0',trace:'Verify snapshot and trusted checkpoint',note:'VERIFIED CLEAN',before:'Unverified project',after:'ok: true, modified: []'},
    {title:'Make a malicious or accidental edit',stage:'DETECTION',desc:'Change app.py from answer=42 to answer=43, then verify again. CI intentionally expects a nonzero exit code.',command:'ofprov verify --project . --check-files',trace:'Detect modified file',note:'MISMATCH DETECTED',before:'Baseline hash matches',after:'ok: false, modified: ["app.py"]'},
    {title:'Accept the reviewed change',stage:'RESULT',desc:'After reviewing the edit, append another record instead of rewriting old hashes, and verify the latest project state.',command:'ofprov snapshot --project . --expected-head OLD_HEAD\nofprov verify --project . --check-files',trace:'Append new snapshot',note:'NEW IMMUTABLE RECORD',before:'Current file differs from seq 0',after:'seq 1 created; latest verify is clean'}
  ]},
  {id:'mcp',number:'05',cat:'discover',tag:'MCP / RECORDED STDIO',title:'Let an AI assistant inspect tools safely',short:'Handshake → discover → verify',problem:'A coding assistant should be able to find skills and verify project integrity, but must not silently start Docker or approve browser navigation.',outcome:'The CLI CI preview launched the actual MCP subprocess, exchanged JSON-RPC frames, discovered 10 tools and got a valid read-only provenance verification.',before:'No machine-readable agent tool contract.',after:'10 discoverable MCP tools; read-only proof.',source:'ci',url:'https://github.com/muhdmunir961-byte/omniforge/actions/runs/40131838901',steps:[
    {title:'Connect by stdio',stage:'INPUT',desc:'The coding client starts a local Python process and sends a protocol initialize request; no API server is needed.',command:'omniforge mcp',trace:'Real MCP stdio session',note:'MCP JSON-RPC FRAMES',before:'No connected MCP process',after:'initialize returns protocolVersion 2025-06-18'},
    {title:'Inspect registered tools',stage:'PROCESS',desc:'tools/list advertises schemas for ten tool names, including search, load, preview-only run/browser and v2 provenance verify.',command:'{"jsonrpc":"2.0","id":2,"method":"tools/list"}',display:'Discovered: omniforge_search, omniforge_load, omniforge_run,\nomniforge_browser, omniforge_chain_verify, omniforge_chain_proof,\nomniforge_provenance_verify, omniforge_provenance_proof,\nomniforge_provenance_audit, omniforge_budget.\n\nEnumeration comes from src/omniforge/mcp.py.',note:'ACTUAL REGISTERED TOOL NAMES',before:'Unstructured abilities',after:'Ten JSON input schemas'},
    {title:'Run read-only verification',stage:'CONTROL',desc:'The MCP caller requests the same local ledger check that the CLI supports, but without writing or authorizing execution.',command:'{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"omniforge_provenance_verify","arguments":{"project":".","check_files":true}}}',display:'Captured end-to-end test: call result parses as JSON and\nreport["ok"] is True. Tool returned through real MCP stdio.',note:'CI ASSERTION',before:'Integrity unknown',after:'Validated read-only result'},
    {title:'Require local approval for side effects',stage:'RESULT',desc:'MCP run/browser endpoints return previews only. To execute an action, the human must use the locally installed CLI approval path.',command:'omniforge run python-symbols --project . --approve -- sample.py',display:'MCP run/browser: preview-only by design.\nLocal CLI with --approve: can execute, using Docker by default.\nThis site never executes the command.',note:'TRUST BOUNDARY',before:'AI could request an action',after:'Human controls approval in local CLI'}
  ]},
  {id:'patch',number:'06',cat:'automate',tag:'AI PATCHING / ACTUAL E2E FIXTURE',title:'Approve an AI code edit without blind overwrite',short:'Select → propose → review → backup',problem:'You want a model to change app.py but not read secret.env, edit unrelated files or overwrite a file that changed since the proposal.',outcome:'The real local-HTTP E2E test changed answer = 1 to answer = 2 only after explicit approval, preserved the previous app.py in a backup, and did not transmit the secret.env fixture.',before:'app.py → answer = 1',after:'app.py → answer = 2; backup retains answer = 1.',source:'e2e',url:E2E,steps:[
    {title:'Choose only allowed source',stage:'INPUT',desc:'Explicitly select app.py; never scan/upload the whole repository or hidden secrets. For a remote model host, --allow-remote is required.',command:'omniforge code --task "set answer to 2" --file app.py --endpoint http://127.0.0.1:8000/v1/chat/completions --model local-test',display:'E2E fixture inputs:\napp.py      → answer = 1\nsecret.env  → VERY_PRIVATE_TEST_VALUE\n\nOnly ["app.py"] is sent to the local HTTP test provider.',note:'E2E TEST INPUT',before:'Original app.py present',after:'Only app.py selected'},
    {title:'Receive a constrained proposal',stage:'PROCESS',desc:'The model HTTP fixture responds with a JSON edit containing the exact selected path and original SHA-256 lease.',command:'request_edits("set answer to 2", project, ["app.py"], endpoint=local_fixture, model="mock-e2e")',display:'assert proposal["status"] == "proposal"\nassert len(MockModel.received) == 1\nassert "VERY_PRIVATE_TEST_VALUE" not in json.dumps(MockModel.received)',note:'E2E ASSERTIONS',before:'No proposed diff',after:'One validated app.py edit'},
    {title:'Inspect the proposed change',stage:'CONTROL',desc:'Without approval, apply_proposal returns a preview; it does not modify app.py.',command:'apply_proposal(proposal, project)',display:'Preview asserts:\npreview["status"] == "preview-only"\nfile.read_text() == "answer = 1\\n"\n\nPotential diff:\n- answer = 1\n+ answer = 2',note:'E2E PREVIEW',before:'app.py = answer = 1',after:'Still unchanged'},
    {title:'Approve and keep a backup',stage:'RESULT',desc:'After explicit approve=True, the file changes. Original bytes are preserved in a timestamped backup folder.',command:'apply_proposal(proposal, project, approve=True)',display:'E2E asserts:\napplied["status"] == "applied"\nfile.read_text() == "answer = 2\\n"\n(Path(applied["backup"]) / "app.py").read_text() == "answer = 1\\n"',note:'E2E VERIFIED RESULT',before:'Old code, no backup',after:'Updated code plus recoverable previous version'}
  ]},
  {id:'docker',number:'07',cat:'automate',tag:'DOCKER / ACTUAL E2E FIXTURE',title:'Run a code inspector with restricted permissions',short:'Inspect → sandbox → output',problem:'You want to inspect Python classes/functions but should not hand an unknown script broad host access.',outcome:'The actual E2E test ran python-symbols inside Docker with network=none and an owner-mapped read-only mount, returned the Example class and left source content unchanged.',before:'sample.py contains class Example',after:'Parsed symbol Example; sample.py unchanged.',source:'e2e',url:E2E,steps:[
    {title:'Review source and chosen skill',stage:'INPUT',desc:'Target a specific Python file. The bundled skill parses AST rather than executing the target code.',command:'omniforge load python-symbols',display:'Fixture file: sample.py\nclass Example:\n    pass\n\nNo user code is executed by the AST scanner.',note:'TEST INPUT',before:'Unknown file symbols',after:'Ready to inspect'},
    {title:'Generate a Docker plan',stage:'PROCESS',desc:'Run defaults to Docker; image must already be available. The command includes resource limits, readonly mounts and no network.',command:'omniforge run python-symbols --project . -- sample.py',display:'E2E plan asserts:\nplan["mode"] == "docker-isolated"\n--network none\n--user <host UID:GID>\n--read-only\n--cap-drop ALL\nproject mount readonly',note:'ACTUAL E2E GUARDS',before:'Potentially untrusted tool',after:'Restricted container configuration'},
    {title:'Approve local execution',stage:'CONTROL',desc:'The test calls execute_run(plan, approve=True). The public Vercel preview cannot reach Docker and never runs arbitrary code.',command:'omniforge run python-symbols --project . --approve -- sample.py',display:'E2E test: response["status"] == "completed"\nparsed = json.loads(response["stdout"])',note:'E2E RUN STATUS',before:'Preview-only',after:'Completed only with approval'},
    {title:'Observe read-only output',stage:'RESULT',desc:'The inspector returns the class declaration while the input file remains byte-for-byte unchanged.',command:'python -m pytest -q tests/test_live_integrations.py -k docker',display:'E2E asserts:\nany(symbol["name"] == "Example" for symbol in parsed["symbols"])\nassert sample.py == "class Example:\\n    pass\\n"\n\nDocker is a mitigation, not perfect kernel isolation.',note:'E2E VERIFIED RESULT',before:'No parsed symbol list',after:'Example class found; source intact'}
  ]},
  {id:'anchor',number:'08',cat:'protect',tag:'EVM / CLI + LOCAL-CHAIN E2E',title:'Anchor a source hash without giving away wallet keys',short:'Snapshot → unsigned tx → external approval',problem:'You need an optional public timestamp signal for a code snapshot. You do not want private keys in the AI tool, or any automatic crypto transactions.',outcome:'CLI returned an unsigned zero-value self-transaction containing the snapshot hash. A separate E2E test used disposable Anvil accounts to verify calldata and receipts; mainnet is not involved.',before:'Only local SHA-256 ledger state',after:'Unsigned payload; real wallet still owns approval.',source:'mixed',url:EVM,steps:[
    {title:'Capture the source hash',stage:'INPUT',desc:'Compute an immutable entry_hash from the selected project snapshot and policy. The external wallet never needs the source code.',command:'ofprov snapshot --project .',trace:'Create snapshot',note:'LOCAL RECORD',before:'No public anchor',after:'Immutable ledger entry hash'},
    {title:'Acknowledge public data',stage:'CONTROL',desc:'Without explicit --ack-public-data the CLI refuses to prepare the EVM calldata.',command:'ofprov anchor --project . --wallet 0x1111111111111111111111111111111111111111 --chain-id 1337 --prepare',trace:'Anchor consent enforced',note:'FAIL-CLOSED PRIVACY CHECK',before:'No privacy consent',after:'CLI exits with error; no transaction'},
    {title:'Generate an unsigned transaction',stage:'PROCESS',desc:'The CLI produces from/to, value=0 and calldata=entry_hash. It never signs or sends it. Test-chain gas is simulated.',command:'ofprov anchor --project . --wallet 0x1111111111111111111111111111111111111111 --chain-id 1337 --prepare --ack-public-data',trace:'Unsigned EVM anchor preview',note:'UNSIGNED CALDATA',before:'Nothing prepared',after:'wallet-approval-required'},
    {title:'Verify an external tx if you choose',stage:'RESULT',desc:'Anvil E2E explicitly broadcasts a test transaction outside OmniForge and confirms the matching hash and receipt. Real public networks require an external wallet and may cost gas.',command:'ofprov anchor --project . --wallet PUBLIC_ADDRESS --chain-id CHAIN_ID --verify-tx TX_HASH --rpc-url https://TRUSTED-RPC --confirmations 3',display:'Local Anvil E2E asserts:\nreceipt["status"] == "0x1"\nverified["ok"] is True\nverified["entry_hash"] == entry["entry_hash"]\nverified["confirmations"] >= 1\n\nApp never requests keys, signs or broadcasts.',note:'E2E ASSERTIONS (ANVIL)',before:'Unanchored local record',after:'Read-only tx verification available'}
  ]},
  {id:'browser',number:'09',cat:'automate',tag:'PLAYWRIGHT / ACTUAL E2E FIXTURE',title:'Check a website with controlled browser actions',short:'Authorize → fill → click → screenshot',problem:'A developer needs repeatable checks on a known site, not an uncontrolled browsing agent that silently accesses arbitrary hosts.',outcome:'A real Chromium E2E test visited a temporary local page, filled a form, clicked submit, observed text and saved a screenshot larger than 1 KB.',before:'Status is Initial',after:'Status shows end-to-end confirmed; screenshot saved.',source:'e2e',url:E2E,steps:[
    {title:'Authorize the target',stage:'INPUT',desc:'The E2E creates a disposable local web server with a text input, button and status element. Public browsing has separate restrictions.',command:'omniforge browser --url https://example.org --project .',display:'Test fixture page:\n<input id="entry">\n<button id="go">Submit</button>\n<div id="status">Initial</div>\n\nThis is a local test server, not a public page.',note:'ACTUAL TEST FIXTURE',before:'Status = Initial',after:'Authorized local target'},
    {title:'Build deterministic steps',stage:'PROCESS',desc:'The E2E uses explicit selectors and text values rather than having a model improvise browser actions.',command:'[{"action":"fill","selector":"#entry","value":"end-to-end confirmed"},{"action":"click","selector":"#go"},{"action":"screenshot"}]',display:'E2E actions:\nfill #entry → "end-to-end confirmed"\nclick #go\nwait 80 ms\nscreenshot → artifacts/browser.png',note:'TEST ACTIONS',before:'Input empty',after:'Field filled and submitted'},
    {title:'Require approval before opening a browser',stage:'CONTROL',desc:'The local CLI needs --approve. MCP offers only a preview; this Vercel website cannot request live navigation.',command:'omniforge browser --url https://example.org --project . --approve',display:'E2E uses:\nbrowser_session(base, steps=steps, project=tmp_path,\n                screenshot="artifacts/browser.png",\n                allow_local=True, approve=True)',note:'E2E INVOCATION',before:'No browser launched',after:'Approved Chromium session'},
    {title:'Capture visible evidence',stage:'RESULT',desc:'The real test inspects DOM text and confirms the screenshot exists, without claiming a production screenshot has been shared here.',command:'python -m pytest -q tests/test_live_integrations.py -k browser',display:'E2E asserts:\nresult["status"] == "completed"\nresult["title"] == "OmniForge Local E2E"\n"end-to-end confirmed" in result["text"]\nscreenshot.is_file() and screenshot.stat().st_size > 1000',note:'E2E VERIFIED RESULT',before:'Status = Initial',after:'Confirmed text + PNG file'}
  ]}
];
let evidence={captures:[]};let selectedId='search',selectedStep=0,filter='all',caseQuery='';
const visibleStories=()=>STORIES.filter(story=>{
  if(filter!=='all'&&story.cat!==filter)return false;
  if(!caseQuery)return true;
  const haystack=[story.title,story.short,story.problem,story.outcome,story.tag,
    ...story.steps.map(step=>[step.title,step.command,step.desc].join(' '))].join(' ').toLowerCase();
  return haystack.includes(caseQuery);
});
const initialCase=new URLSearchParams(location.search).get('demo');
if(STORIES.some(story=>story.id===initialCase))selectedId=initialCase;
const CAPTURES=()=>new Map((evidence.captures||[]).map(e=>[e.label,e]));
const evidenceBadge=story=>story.source==='ci'?'CAPTURED FROM CI':story.source==='e2e'?'ASSERTED BY E2E TEST':'CI RECORDING + E2E TEST';
const indicator=story=>story.source==='ci'?'capture':'test';
const caseList=$('caseList'),caseWorkspace=$('caseWorkspace');
let timer;
function toast(message){const e=$('toast');e.textContent=message;e.classList.add('show');clearTimeout(timer);timer=setTimeout(()=>e.classList.remove('show'),2500)}
async function copyCommand(data){try{await navigator.clipboard.writeText(data);toast('Command copied — run locally after reviewing permissions.')}catch{const input=document.createElement('textarea');input.value=data;document.body.append(input);input.select();document.execCommand('copy');input.remove();toast('Copied to clipboard')}}
function renderMenu(){
  const selection=visibleStories();
  $('caseCount').textContent=`${selection.length} OF ${STORIES.length} EXAMPLES`;
  if(!selection.some(story=>story.id===selectedId)){
    selectedId=selection[0]?.id??null;selectedStep=0;
  }
  caseList.replaceChildren(...selection.map(story=>{
    const button=document.createElement('button');
    button.className='case-item'+(story.id===selectedId?' active':'');
    button.type='button';button.setAttribute('role','option');
    button.setAttribute('aria-selected',String(story.id===selectedId));
    button.dataset.id=story.id;
    button.innerHTML=`<span class="index">${story.number}</span><span><strong>${safe(story.title)}</strong><small>${safe(story.short)}</small></span>`;
    return button;
  }));
  if(!selection.length){
    caseWorkspace.innerHTML=`<div class="no-results"><div class="empty-symbol" aria-hidden="true">⌕</div><h3>No matching examples</h3><p>Try a broader search, switch the category to All examples, or clear the search field.</p><button type="button" class="action-main" id="clearCaseSearch">Clear search</button></div>`;
    $('clearCaseSearch').addEventListener('click',()=>{
      caseQuery='';$('caseSearch').value='';filter='all';
      $('storyFilters').querySelectorAll('button').forEach(button=>button.classList.toggle('active',button.dataset.filter==='all'));
      renderMenu();renderStory();$('caseSearch').focus();
    });
  }
}
function renderStory(){if(!visibleStories().length)return;const s=STORIES.find(s=>s.id===selectedId)||visibleStories()[0],step=s.steps[selectedStep],capture=step.trace?CAPTURES().get(step.trace):null;const isCaptured=!!capture;let output=step.display??(capture?capture.stdout||capture.stderr:'');if(capture&&capture.stderr&&!capture.stdout)output=capture.stderr;
if(capture&&capture.label==='Real MCP stdio session')output=clip(capture.stdout).split('\n').filter(Boolean).slice(0,2).join('\n');
const marker=isCaptured?'ACTUAL CLI STDOUT · v1.3.0':s.source==='e2e'||s.source==='mixed'?'TEST FIXTURE / CODE ASSERTIONS':'EXPLANATORY EXAMPLE';
caseWorkspace.innerHTML=`<div class="case-labels"><span class="pill ${indicator(s)}">${safe(evidenceBadge(s))}</span><span class="pill">${safe(s.tag)}</span></div>
 <h3 class="case-title">${safe(s.title)}</h3><p class="case-problem">${safe(s.problem)}</p>
 <div class="case-outcome"><span class="outcome-mark">✓</span><div><strong>What you actually get</strong><br>${safe(s.outcome)}</div></div>
 <div class="step-meter" aria-label="Walkthrough progress"><span class="meter-copy">STEP ${selectedStep+1} OF ${s.steps.length}</span><span class="meter-track"><span class="meter-fill" style="width:${100*(selectedStep+1)/s.steps.length}%"></span></span></div>
 <div class="stepper" role="group" aria-label="Process steps">${s.steps.map((x,i)=>`<button type="button" data-step="${i}" class="${selectedStep===i?'active':''}" aria-pressed="${selectedStep===i}"><span class="step-num">0${i+1} / 0${s.steps.length}</span><strong>${safe(x.title)}</strong></button>`).join('')}</div>
 <div class="step-content"><div class="step-main"><div class="step-topic">${safe(step.stage)} / STEP 0${selectedStep+1}</div><h3>${safe(step.title)}</h3><p class="step-copy">${safe(step.desc)}</p>
 <div class="terminal-frame ${isCaptured?'':'has-fixture'}"><div class="terminal-header"><span class="dots"><i></i><i></i><i></i></span><span>${safe(step.note)}</span></div><div class="terminal-command"><code>$ ${safe(step.command)}</code><button type="button" class="copy" data-copy="command" aria-label="Copy this OmniForge command">COPY</button></div><pre class="terminal-output">${safe(trunc(output,2400))}</pre><div class="terminal-footer"><span>${safe(marker)}</span><span class="${isCaptured?'':'fixture'}">${isCaptured?'CAPTURED ✓':'NOT A LIVE CLI SESSION'}</span></div></div></div>
 <aside class="step-aside"><span>BEFORE / AFTER</span><h4>What changes at this step?</h4><p>${safe(step.desc)}</p><div class="stage-before-after"><div class="change-block"><span>BEFORE</span><code>${safe(step.before||s.before)}</code></div><div class="change-block"><span>AFTER</span><code>${safe(step.after||s.after)}</code></div></div><a href="${safe(s.url)}" target="_blank" rel="noreferrer">Inspect original evidence ↗</a></aside></div>
 <div class="step-controls"><span>STEP ${selectedStep+1} OF ${s.steps.length} · ${safe(s.tag)}</span><div><button type="button" class="action-outline" id="prevStep" ${selectedStep===0?'disabled':''}>← Previous</button><button type="button" class="action-main" id="nextStep">${selectedStep===s.steps.length-1?'Next case':'Next step'} ↗</button></div></div>
 <div class="case-source-line">${isCaptured?'This output was captured by the actual installed Python CLI in CI.':'This step uses explanatory/test-fixture content—not a fabricated live CLI output.'} <a href="${safe(s.url)}" target="_blank" rel="noreferrer">Verify source ↗</a>. Public temporary paths were anonymized.</div>`;
caseWorkspace.querySelectorAll('[data-step]').forEach(button=>button.addEventListener('click',()=>{selectedStep=Number(button.dataset.step);renderStory()}));
caseWorkspace.querySelector('[data-copy]').addEventListener('click',()=>copyCommand(step.command));
  try{history.replaceState({},'',location.pathname+'?demo='+encodeURIComponent(s.id)+location.hash)}catch{}
$('prevStep').addEventListener('click',()=>{selectedStep=Math.max(0,selectedStep-1);renderStory()});
$('nextStep').addEventListener('click',()=>{if(selectedStep<s.steps.length-1)selectedStep++;else{const visible=visibleStories();selectedId=visible[(visible.findIndex(z=>z.id===s.id)+1)%visible.length].id;selectedStep=0;renderMenu()}renderStory()});}
caseList.addEventListener('click',e=>{const btn=e.target.closest('button[data-id]');if(btn){selectedId=btn.dataset.id;selectedStep=0;renderMenu();renderStory()}});
$('storyFilters').addEventListener('click',e=>{const b=e.target.closest('button[data-filter]');if(!b)return;filter=b.dataset.filter;$('storyFilters').querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));renderMenu();renderStory()});
const caseSearch=$('caseSearch');
caseSearch.addEventListener('input',()=>{
  caseQuery=caseSearch.value.trim().toLocaleLowerCase();
  renderMenu();renderStory();
});
document.addEventListener('keydown',event=>{
  const inField=event.target?.matches('input,textarea,[contenteditable="true"]');
  if(event.key==='/'&&!inField&&!event.ctrlKey&&!event.metaKey&&!event.altKey){
    event.preventDefault();caseSearch.focus();caseSearch.select();
  }
  if(event.key==='Escape'&&document.activeElement===caseSearch){
    caseSearch.value='';caseQuery='';renderMenu();renderStory();caseSearch.blur();
  }
});
caseList.addEventListener('keydown',event=>{
  if(!['ArrowRight','ArrowLeft','ArrowUp','ArrowDown'].includes(event.key))return;
  const buttons=[...caseList.querySelectorAll('button[data-id]')];
  const current=buttons.findIndex(button=>button===document.activeElement);
  if(current<0)return;
  event.preventDefault();
  const offset=['ArrowRight','ArrowDown'].includes(event.key)?1:-1;
  const next=buttons[(current+offset+buttons.length)%buttons.length];
  next?.focus();next?.click();
});
document.querySelectorAll('[data-open-case]').forEach(anchor=>anchor.addEventListener('click',()=>{
  const target=anchor.dataset.openCase;
  if(!STORIES.some(story=>story.id===target))return;
  selectedId=target;selectedStep=0;caseQuery='';caseSearch.value='';filter='all';
  $('storyFilters').querySelectorAll('button').forEach(button=>button.classList.toggle('active',button.dataset.filter==='all'));
  renderMenu();renderStory();
}));
const pageProgress=$('pageProgress');
let progressScheduled=false;
window.addEventListener('scroll',()=>{
  if(progressScheduled)return;
  progressScheduled=true;
  requestAnimationFrame(()=>{
    const available=document.documentElement.scrollHeight-innerHeight;
    pageProgress.style.transform='scaleX('+(available>0?Math.min(1,Math.max(0,scrollY/available)):0)+')';
    progressScheduled=false;
  });
},{passive:true});
let digestBaseline=null,digestCurrent=null,baselineContent=null;
const initialSource=$('hashInput').value;const encoder=new TextEncoder();
// The HTTPS deployment uses Web Crypto. Portable SHA-256 fallback keeps the
// educational lab functional in file previews and restrictive test sandboxes.
function sha256Fallback(bytes){
  const primes=[
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  const rotate=(x,n)=>(x>>>n)|(x<<(32-n));
  const size=Math.ceil((bytes.length+9)/64)*64,buf=new Uint8Array(size);
  buf.set(bytes);buf[bytes.length]=128;
  const view=new DataView(buf.buffer), bits=bytes.length*8;
  view.setUint32(size-8,Math.floor(bits/4294967296));view.setUint32(size-4,bits>>>0);
  const h=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
  for(let off=0;off<size;off+=64){
    const w=new Array(64);for(let i=0;i<16;i++)w[i]=view.getUint32(off+i*4);
    for(let i=16;i<64;i++){
      const a=w[i-15],b=w[i-2];const s0=rotate(a,7)^rotate(a,18)^(a>>>3);
      const s1=rotate(b,17)^rotate(b,19)^(b>>>10);
      w[i]=(w[i-16]+s0+w[i-7]+s1)>>>0;
    }
    let [a,b,c,d,e,f,g,j]=h;
    for(let i=0;i<64;i++){
      const s1=rotate(e,6)^rotate(e,11)^rotate(e,25),ch=(e&f)^(~e&g);
      const t1=(j+s1+ch+primes[i]+w[i])>>>0;
      const s0=rotate(a,2)^rotate(a,13)^rotate(a,22),maj=(a&b)^(a&c)^(b&c);
      const t2=(s0+maj)>>>0;
      j=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;
    }
    const v=[a,b,c,d,e,f,g,j];for(let i=0;i<8;i++)h[i]=(h[i]+v[i])>>>0;
  }
  return h.map(x=>x.toString(16).padStart(8,'0')).join('');
}
async function sha256(value){
  const bytes=encoder.encode(value);
  if(globalThis.crypto?.subtle){const hash=await crypto.subtle.digest('SHA-256',bytes);return Array.from(new Uint8Array(hash)).map(b=>b.toString(16).padStart(2,'0')).join('')}
  return sha256Fallback(bytes);
}
async function updateLab(){try{digestCurrent=await sha256($('hashInput').value);$('currentHash').textContent=digestCurrent;if(digestBaseline===null){$('labStatus').textContent='AWAITING SNAPSHOT';$('labResult').textContent='No baseline recorded';$('labDetail').textContent='Press Record baseline to begin.';$('labIndicator').parentElement.className='lab-state';return}const same=digestCurrent===digestBaseline;$('labStatus').textContent=same?'MATCH':'MODIFIED';$('labResult').textContent=same?'Integrity verified':'Change detected';$('labDetail').textContent=same?'Current file hash matches the stored baseline.':'Bytes differ from the recorded baseline; the SHA-256 no longer matches.';$('labIndicator').parentElement.className='lab-state '+(same?'match':'mismatch');$('labExplainer').textContent=same?'Your source is identical to the baseline. Edit even one character to see a mismatch.':'This illustrates how content hashing detects changed bytes. Revert text to restore a match.'}catch(err){$('labResult').textContent='Web Crypto unavailable';$('labDetail').textContent=err.message}}
$('takeBaseline').addEventListener('click',async()=>{baselineContent=$('hashInput').value;digestBaseline=await sha256($('hashInput').value);$('baselineHash').textContent=digestBaseline;await updateLab();toast('Baseline recorded in this browser session.')});
$('verifySample').addEventListener('click',updateLab);
$('resetSample').addEventListener('click',async()=>{
  $('hashInput').value=baselineContent??initialSource;
  await updateLab();toast(baselineContent===null?'Sample reset to initial source.':'Sample restored to your recorded baseline.');
});
$('editSample').addEventListener('click',async()=>{const original=$('hashInput').value;const value=original.includes('42')?original.replace('42','43'):original+'\n# changed by demo\n';$('hashInput').value=value;await updateLab();toast('Source changed. Current SHA-256 recalculated.')});
let hashTimer;$('hashInput').addEventListener('input',()=>{clearTimeout(hashTimer);hashTimer=setTimeout(updateLab,100)});
$('menuToggle').addEventListener('click',()=>{const n=document.querySelector('.site-head nav');n.classList.toggle('open');$('menuToggle').setAttribute('aria-expanded',String(n.classList.contains('open')))});
document.querySelectorAll('.site-head nav a').forEach(a=>a.addEventListener('click',()=>{document.querySelector('.site-head nav').classList.remove('open');$('menuToggle').setAttribute('aria-expanded','false')}));
async function initialize(){try{const embedded=document.getElementById('evidence-data');if(embedded){evidence=JSON.parse(embedded.textContent)}else{const response=await fetch('/evidence.json',{cache:'no-store'});if(!response.ok)throw Error('Evidence download failed');evidence=await response.json()}if(!Array.isArray(evidence.captures)||evidence.captures.length<30)throw Error('Missing CI capture data')}catch(error){evidence={captures:[]};toast('CI archive unavailable; test fixture walkthrough remains accessible.')}renderMenu();renderStory();await updateLab()}
initialize();
