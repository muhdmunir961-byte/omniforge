export const META = Object.freeze({
  repo: 'https://github.com/muhdmunir961-byte/omniforge',
  api: 'https://api.github.com/repos/muhdmunir961-byte/omniforge',
  version: '1.3.1',
  sourceCommit: '6de32a84c6331b14bb1eadd5bf28ef267c649a5f',
  verifiedAt: '2026-10-25',
  python: '3.11+',
  nativeSkills: 14,
  adapters: 4,
  researchCandidates: 112
});

export const SKILLS = [
  {name:'api-probe',type:'builtin',category:'Networking',description:'Probe a URL explicitly authorized by the user, reporting response status, headers and timing without leaking credentials.',need:'Python standard library',example:'omniforge load api-probe'},
  {name:'browser-snapshot',type:'adapter',category:'Browser',description:'Capture a browser snapshot or interact with approved pages using optional local Playwright.',need:'Playwright + local Chromium',example:'omniforge load browser-snapshot'},
  {name:'dependency-inventory',type:'builtin',category:'Repository',description:'Inventory declared Python and Node.js dependencies in a local project without installing or executing packages.',need:'Python standard library',example:'omniforge load dependency-inventory'},
  {name:'esptool-chip',type:'adapter',category:'Hardware',description:'Read chip identification from an explicitly selected ESP32 serial port using installed esptool.',need:'esptool + selected serial port',example:'omniforge load esptool-chip'},
  {name:'firmware-preflight',type:'builtin',category:'Hardware',description:'Check local ESP32 firmware tooling availability and device-port enumeration without flashing or changing hardware.',need:'Python standard library',example:'omniforge load firmware-preflight'},
  {name:'git-diff-review',type:'builtin',category:'Git',description:'Review local Git diff statistics and changed files without modifying the repository or showing secret contents.',need:'Git available locally',example:'omniforge load git-diff-review'},
  {name:'interface-craft',type:'builtin',category:'Design',description:'Plan premium responsive UI/UX with art direction, accessibility, working product states and reviewable source changes.',need:'Coding client for actual implementation',example:'omniforge load interface-craft'},
  {name:'motion-interaction',type:'builtin',category:'Design',description:'Plan meaningful interface animation and Three.js camera movement with reduced-motion and performance considerations.',need:'Frontend runtime for implementation',example:'omniforge load motion-interaction'},
  {name:'realtime-3d-mesh',type:'builtin',category:'3D',description:'Guide genuine Three.js or React Three Fiber meshes, glTF assets, lighting and mobile performance, not fabricated 3D renders.',need:'Three.js / React Three Fiber application',example:'omniforge load realtime-3d-mesh'},
  {name:'visual-qa',type:'builtin',category:'Quality',description:'Audit layouts and 3D browser experiences for broken assets, interactions, accessibility and WebGL runtime errors.',need:'Real browser test runner for full QA',example:'omniforge load visual-qa'},
  {name:'kicad-drc',type:'adapter',category:'Hardware',description:'Check PCB design-rule violations using the installed KiCad kicad-cli command.',need:'Installed KiCad CLI',example:'omniforge load kicad-drc'},
  {name:'log-triage',type:'builtin',category:'Observability',description:'Triage application logs offline, redact basic secrets and identify recurring error signatures and severity patterns.',need:'Python standard library',example:'omniforge load log-triage'},
  {name:'openapi-inventory',type:'builtin',category:'Networking',description:'Summarize endpoints, request methods, and response codes in an existing local OpenAPI JSON file without network calls.',need:'Python standard library',example:'omniforge load openapi-inventory'},
  {name:'python-symbols',type:'builtin',category:'Analysis',description:'Inspect Python source file classes, functions, imports, and asynchronous definitions using safe AST parsing.',need:'Python standard library',example:'omniforge load python-symbols'},
  {name:'repo-recon',type:'builtin',category:'Repository',description:'Inspect a local Git repository to summarize status, branches, recent commits and project languages without modifying files.',need:'Local Git repository',example:'omniforge load repo-recon'},
  {name:'secret-hygiene',type:'builtin',category:'Security',description:'Flag likely credentials in local source trees and report only file names, line numbers, and pattern types without exposing values.',need:'Python standard library',example:'omniforge load secret-hygiene'},
  {name:'sqlite-inspector',type:'builtin',category:'Database',description:'Inspect SQLite schemas and table row-count estimates using read-only queries without altering local databases.',need:'SQLite standard library',example:'omniforge load sqlite-inspector'},
  {name:'trivy-scan',type:'adapter',category:'Security',description:'Scan a local project for vulnerabilities or secrets using installed Trivy; requires opt-in for database downloads.',need:'Installed Trivy + optional DB download',example:'omniforge load trivy-scan'}
];

export const AGENT_PATHS = {
  codex:'.agents/skills',claude:'.claude/skills',cursor:'.cursor/skills',
  opencode:'.opencode/skills',copilot:'.github/skills',gemini:'.gemini/skills',universal:'.agents/skills'
};

export const MCP_TOOLS = [
  {name:'omniforge_search',type:'read-only',description:'Search local agent skills with hybrid local text ranking. Returns metadata only.',args:{query:'ESP32 hardware',limit:5},required:['query']},
  {name:'omniforge_load',type:'read-only',description:'Load the full SKILL.md for one explicitly selected bundled skill.',args:{name:'log-triage'},required:['name']},
  {name:'omniforge_run',type:'preview-only',description:'Preview a bundled skill execution. MCP cannot approve or perform actual execution.',args:{name:'firmware-preflight',project:'/sample-project',args:[]},required:['name','project']},
  {name:'omniforge_browser',type:'preview-only',description:'Preview browser navigation. MCP cannot authorize opening web pages.',args:{url:'https://example.org',project:'/sample-project'},required:['url','project']},
  {name:'omniforge_chain_verify',type:'read-only',description:'Verify local v1 chain links and optionally check the current project snapshot.',args:{project:'/sample-project',check_current:true},required:['project']},
  {name:'omniforge_chain_proof',type:'read-only',description:'Access one previously recorded v1 block hash. Never initiates wallet actions.',args:{project:'/sample-project',height:0},required:['project']},
  {name:'omniforge_provenance_verify',type:'read-only',description:'Verify the strict v2 ledger and optionally match source files or an independently trusted checkpoint.',args:{project:'/sample-project',check_files:true},required:['project']},
  {name:'omniforge_provenance_proof',type:'read-only',description:'Read a validated v2 ledger snapshot. No wallet signing or network calls.',args:{project:'/sample-project',seq:0},required:['project']},
  {name:'omniforge_provenance_audit',type:'read-only',description:'Audit v2 hash chain, files, policy history and privacy warnings.',args:{project:'/sample-project'},required:['project']},
  {name:'omniforge_budget',type:'read-only',description:'Estimate the approximate token context overhead of lazy skill loading.',args:{selected:'log-triage'},required:[]}
];

export const CAPABILITIES = [
  {page:'skills',id:'01',title:'Skill discovery',description:'Hybrid local search, metadata indexing and lazy skill loading.',icon:'◇'},
  {page:'terminal',id:'02',title:'Local-first CLI',description:'Explore exact commands, flags and sample JSON output.',icon:'⌘'},
  {page:'mcp',id:'03',title:'MCP tool bridge',description:'Inspect stdio schemas and read-only tool contracts.',icon:'⇄'},
  {page:'workflow',id:'04',title:'Task orchestration',description:'Validated dependencies, explicit approval, DAG execution.',icon:'⬡'},
  {page:'provenance',id:'05',title:'Integrity ledger',description:'Try SHA-256 snapshots, verification and unsigned EVM calldata.',icon:'⛓'},
  {page:'runtime',id:'06',title:'Permission control',description:'Understand Docker isolation, AI patches and browser guardrails.',icon:'⌁'},
  {page:'architecture',id:'07',title:'Source architecture',description:'Inspect modules, boundaries and external dependencies.',icon:'⊞'},
  {page:'verification',id:'08',title:'Test evidence',description:'View verified CI history and refresh public GitHub status.',icon:'✓'}
];

export const MODULES = [
  {file:'src/omniforge/cli.py',name:'CLI dispatcher',description:'argparse commands and user approval flags'},
  {file:'src/omniforge/core.py',name:'Skill core',description:'Catalog, skill installation and heuristic audit'},
  {file:'src/omniforge/semantic.py',name:'Search ranking',description:'Hybrid search and optional local embeddings'},
  {file:'src/omniforge/router.py',name:'Skill router',description:'Index, metadata search and lazy instructions'},
  {file:'src/omniforge/planner.py',name:'Offline planner',description:'Related skills and deterministic task suggestions'},
  {file:'src/omniforge/agents.py',name:'Workflow DAG',description:'Dependency graph and controlled external commands'},
  {file:'src/omniforge/runtime.py',name:'Execution runtime',description:'Docker restrictions and explicit local execution'},
  {file:'src/omniforge/mcp.py',name:'MCP server',description:'JSON-RPC tool discovery and read-only previews'},
  {file:'src/omniforge/autocode.py',name:'Model patching',description:'BYOK model proposals and checked source edit application'},
  {file:'src/omniforge/browser.py',name:'Browser actions',description:'Opt-in Playwright session and hostname controls'},
  {file:'src/omniforge/provenance_v2.py',name:'Ledger engine',description:'v2 snapshots, verify, migration and backup'},
  {file:'src/omniforge/provenance_v2_policy.py',name:'Snapshot policy',description:'Safe project hashing, exclusions and canonical JSON'},
  {file:'src/omniforge/provenance_v2_evm.py',name:'EVM verifier',description:'Unsigned anchor and read-only receipt inspection'},
  {file:'vscode-extension/extension.js',name:'VS Code integration',description:'Local CLI commands in the editor'},
  {file:'scripts/preview_check.py',name:'Packaged CLI preview',description:'32 CLI scenarios with real subprocess JSON traces'},
  {file:'.github/workflows/portability.yml',name:'Platform CI',description:'Windows/macOS/Linux on Python 3.11 and 3.13'}
];

export const WORKFLOW_TEMPLATES = {
  review:{tasks:[
    {id:'inspect',kind:'skill',skill:'repo-recon'},
    {id:'dependency-check',kind:'skill',skill:'dependency-inventory',depends_on:['inspect']},
    {id:'diff-review',kind:'skill',skill:'git-diff-review',depends_on:['inspect']},
    {id:'secrets',kind:'skill',skill:'secret-hygiene',depends_on:['dependency-check','diff-review']}
  ]},
  firmware:{tasks:[
    {id:'tooling',kind:'skill',skill:'firmware-preflight'},
    {id:'code-scan',kind:'skill',skill:'python-symbols',args:['main.py'],depends_on:['tooling']},
    {id:'report',kind:'skill',skill:'repo-recon',depends_on:['code-scan']}
  ]},
  analysis:{tasks:[
    {id:'recon',kind:'skill',skill:'repo-recon'},
    {id:'api-map',kind:'skill',skill:'openapi-inventory',depends_on:['recon']},
    {id:'deps',kind:'skill',skill:'dependency-inventory',depends_on:['recon']},
    {id:'review',kind:'skill',skill:'git-diff-review',depends_on:['api-map','deps']}
  ]}
};

export const PRINCIPLES = [
  ['No silent command execution','Execution and browser MCP calls always return previews; human CLI approval is separate.'],
  ['Read-only by default','Browsing a skill or checking a ledger should not mutate a project.'],
  ['Docker, not invincibility','Default Docker isolation drops privileges, limits resources and disables network; host/container attacks still exist.'],
  ['Explicit BYOK sharing','Only user-selected files are sent to a configured model endpoint; review any outgoing source.'],
  ['Check files before patching','Approved patch application compares original SHA-256 and keeps local backups.'],
  ['Local ledger ≠ decentralization','A local history can be rewritten; an externally trusted checkpoint matters.'],
  ['Optional EVM anchoring','Unsigned calldata only: never store seeds, sign transactions or auto-broadcast.'],
  ['Heuristics have blind spots','Skill audit, secret scanners and CodeQL do not prove code is malware-free.']
];

export const VERIFIED_RUNS = [
  {name:'Linux Python CI',subtitle:'3.11 / 3.12 / 3.13; unit tests and branch coverage',url:'https://github.com/muhdmunir961-byte/omniforge/actions/runs/40133944866',state:'SUCCESS'},
  {name:'Cross-platform portability',subtitle:'Windows, macOS, Linux (six Python/OS combinations)',url:'https://github.com/muhdmunir961-byte/omniforge/actions/runs/40133857430',state:'SUCCESS'},
  {name:'Real integrations E2E',subtitle:'Docker, Playwright, local model, Foundry Anvil and VS Code',url:'https://github.com/muhdmunir961-byte/omniforge/actions/runs/40133857450',state:'SUCCESS'},
  {name:'Packaged CLI preview',subtitle:'Clean .whl install; 32 scenarios and HTML/JSON artifact',url:'https://github.com/muhdmunir961-byte/omniforge/actions/runs/40133857435',state:'SUCCESS'},
  {name:'Release-candidate verification',subtitle:'Wheel, sdist, VSIX, checksum and build environment SBOM',url:'https://github.com/muhdmunir961-byte/omniforge/actions/runs/40133857439',state:'SUCCESS'},
  {name:'Security automation',subtitle:'CodeQL, dependency audit and secret-pattern scan',url:'https://github.com/muhdmunir961-byte/omniforge/actions/runs/40133231711',state:'SUCCESS'}
];

export const CLI_EXAMPLES = [
  ['System diagnostics','omniforge doctor'],
  ['Find ESP32 skills','omniforge search "ESP32 hardware"'],
  ['List bundled skills','omniforge list'],
  ['Load one skill','omniforge load log-triage'],
  ['Token budget','omniforge budget --selected log-triage'],
  ['Workflow plan','omniforge plan "debug python errors"'],
  ['Read-only execution preview','omniforge run firmware-preflight'],
  ['Initialize local ledger','ofprov init --project .'],
  ['Append SHA-256 snapshot','ofprov snapshot --project .'],
  ['Verify current source','ofprov verify --project . --check-files'],
  ['Deliberately change demo file','demo edit'],
  ['Audit changed files','ofprov audit --project .']
];