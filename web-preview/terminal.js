/* OmniForge actual runtime terminal. Never replay fake CLI results. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const cliInput=$("commandInput"),cliOutput=$("cliOutput"),cliRun=$("runCli");
  const cliStatus=$("cliRuntimeStatus"),pyOutput=$("pythonOutput"),pyInput=$("pythonInput");
  const pyRun=$("runPython"),pyStatus=$("pyVersion"),MAX_VISIBLE=24000;
  const batchParser=globalThis.OmniForgeBatch;
  const stopCli=$("stopCli");
  let currentCliController=null, cancelCliRequested=false;
  let apiReady=false,requestRunning=false,worker=null,pythonBusy=false,pythonLoading=false;
  let workerGeneration=0,pyStart=0,pyTimer=null,workerLoadTimer=null,pythonOutputBytes=0;
  const cliHistory=[];let historyPosition=-1;
  const examples={
    hash:["import hashlib","","source = b\"print('OmniForge')\"",
      "digest = hashlib.sha256(source).hexdigest()","",
      "print('Python executes for real.')","print('SHA-256:', digest)",""].join("\n"),
    ast:["import ast","","source = '''","import json","class Repository:",
      "    def inspect(self, path):","        return {'path':path}",
      "async def analyze(project):","    return project","'''",
      "tree = ast.parse(source)",
      "print('Imports:', [n.names[0].name for n in tree.body if isinstance(n, ast.Import)])",
      "print('Classes:', [n.name for n in tree.body if isinstance(n, ast.ClassDef)])",
      "print('Functions:', [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))])",""].join("\n"),
    json:["import json","from collections import Counter","",
      "events = [{'level':'ERROR','module':'api'}, {'level':'WARN','module':'db'}, {'level':'ERROR','module':'api'}]",
      "report = {'total':len(events), 'severities':dict(Counter(e['level'] for e in events)), 'modules':dict(Counter(e['module'] for e in events))}",
      "print(json.dumps(report, indent=2))",""].join("\n"),
    stats:["import statistics","","latencies_ms=[28,31,35,42,29,97,32,38]",
      "print('Samples:',len(latencies_ms))","print('Mean:',round(statistics.mean(latencies_ms),2),'ms')",
      "print('Median:',statistics.median(latencies_ms),'ms')",""].join("\n"),
    hello:["import sys","print('Hello from actual Python.')","print('Runtime:',sys.version.split()[0])",
      "for n in range(1,6):","    print(f'{n}² = {n**2}')",""].join("\n"),
  };

  function setLabel(id,value,bad=false) {
    const el=$(id);el.textContent=value;el.classList.toggle("danger",bad);
  }
  function setEngine(el,value,online=false,failed=false) {
    el.textContent=value;el.classList.toggle("online",online);el.classList.toggle("failed",failed);
  }
  function pretty(text) {
    const str=String(text??"");
    return str.length>MAX_VISIBLE?str.slice(0,MAX_VISIBLE)+"\n… [truncated]":str;
  }
  function showTab(tab) {
    const cli=tab==="cli";
    $("cliPanel").hidden=!cli;$("pythonPanel").hidden=cli;
    $("cliTab").classList.toggle("selected",cli);$("pythonTab").classList.toggle("selected",!cli);
    $("cliTab").setAttribute("aria-selected",String(cli));
    $("pythonTab").setAttribute("aria-selected",String(!cli));
    try{history.replaceState({},"",location.pathname+location.search+(cli?"#cli":"#python"))}catch{}
  }
  $("cliTab").addEventListener("click",()=>showTab("cli"));
  $("pythonTab").addEventListener("click",()=>showTab("python"));
  if(location.hash==="#python")showTab("python");
  const preset=new URLSearchParams(location.search).get("cmd");
  if(preset&&preset.length<=240&&!/[\r\n]/.test(preset))cliInput.value=preset;
  function setCommand(command){
    cliInput.value=command;cliInput.focus();
    cliInput.setSelectionRange(command.length,command.length);
    updateBatchHint();
  }
  const FULL_DEMO=[
    "omniforge doctor",
    'omniforge search "API errors"',
    "ofprov snapshot",
    "ofprov tamper-demo",
  ];
  function updateBatchHint(){
    const status=$("batchHint");
    try{
      const list=batchParser.parse(cliInput.value);
      status.textContent=list.length+" command"+(list.length===1?"":"s")+" ready · "+(
        list.length>1?"Each runs in a fresh temporary project · ":"")+"Ctrl / ⌘ + Enter to execute";
      status.classList.remove("invalid");
    }catch(error){
      status.textContent=String(error.message);
      status.classList.add("invalid");
    }
  }
  $("loadFullDemo").addEventListener("click",()=>{
    setCommand(FULL_DEMO.join("\n"));
    $("batchHint").textContent="4-command demo loaded · press Run commands once to execute all four";
  });
  cliInput.addEventListener("input",updateBatchHint);
  document.querySelectorAll("[data-command]").forEach(el=>
    el.addEventListener("click",()=>setCommand(el.dataset.command||"omniforge doctor")));
  cliInput.addEventListener("keydown",event=>{
    // Enter inserts a NEW LINE like a terminal script editor. Keyboard shortcuts
    // for running are handled once by the existing global Ctrl/Cmd+Enter hook.
    if(event.altKey&&event.key==="ArrowUp"&&cliHistory.length){
      event.preventDefault();
      historyPosition=Math.min(cliHistory.length-1,historyPosition+1);
      cliInput.value=cliHistory[cliHistory.length-1-historyPosition];
      updateBatchHint();
    }else if(event.altKey&&event.key==="ArrowDown"&&cliHistory.length){
      event.preventDefault();
      historyPosition=Math.max(-1,historyPosition-1);
      cliInput.value=historyPosition<0?"":cliHistory[cliHistory.length-1-historyPosition];
      updateBatchHint();
    }
  });
  function renderTrace(steps){
    const box=$("cliTrace"),list=$("traceSteps");
    box.hidden=!(steps&&steps.length);list.replaceChildren();
    for(const step of steps||[]){
      const row=document.createElement("div");row.className="trace-row";
      const title=document.createElement("code");
      title.textContent="$ "+(step.command||"step");
      const note=document.createElement("small");
      note.textContent="exit "+step.exit_code+" · "+(step.duration_ms??0)+" ms";
      row.append(title,note);
      if(step.stdout||step.stderr){
        const pre=document.createElement("pre");
        pre.textContent=pretty(step.stdout||step.stderr).slice(0,1200);row.append(pre);
      }
      list.append(row);
    }
  }
  async function checkServer(){
    const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),12000);
    try{
      const response=await fetch("/api/terminal",{cache:"no-store",signal:ctl.signal});
      if(!response.ok)throw Error("HTTP "+response.status);
      const data=await response.json();
      if(!data.ok||!String(data.engine).includes("real Python"))throw Error("Unexpected response");
      apiReady=true;setEngine(cliStatus,"READY · Python "+data.runtime,true);
      setLabel("cliTabStatus","LIVE PYTHON");setLabel("cliExecutionLabel","SERVER READY");
    }catch(err){
      apiReady=false;setEngine(cliStatus,"UNAVAILABLE",false,true);
      setLabel("cliTabStatus","OFFLINE",true);setLabel("cliExecutionLabel","API NOT READY",true);
      cliOutput.textContent="Python API not reachable: "+err.message+
        "\nWe do NOT substitute simulated output. Try again after deployment or switch to browser Python.";
    }finally{clearTimeout(timer)}
  }
  async function runCli(){
    if(requestRunning)return;
    let commands;
    try{
      if(!batchParser)throw Error("Command parser failed to load. Refresh the page.");
      commands=batchParser.parse(cliInput.value);
    }catch(error){
      cliOutput.textContent="[INPUT ERROR]\n"+error.message+
        "\n\nPaste one OmniForge command per line or press Load 4-step demo.";
      setLabel("cliExecutionLabel","INPUT FORMAT ERROR",true);
      setLabel("cliDuration","—");updateBatchHint();return;
    }
    if(!apiReady){await checkServer();if(!apiReady)return}
    requestRunning=true;cancelCliRequested=false;
    cliRun.disabled=true;cliRun.textContent="Executing…";
    stopCli.hidden=false;
    cliHistory.push(cliInput.value);
    if(cliHistory.length>25)cliHistory.shift();historyPosition=-1;
    const total=commands.length;
    const startTime=performance.now();
    const outputLines=[
      "# OMNIFORGE / LIVE PYTHON",
      "# "+total+" command"+(total===1?"":"s")+" queued",
      "# Each command has a NEW disposable project; state is not shared.",
      "",
    ];
    let executed=0,verified=0,tamperDetections=0,stoppedByError=false;
    const traceRows=[];
    const renderOutput=()=>{
      cliOutput.textContent=pretty(outputLines.join("\n"));
      cliOutput.scrollTop=cliOutput.scrollHeight;
      renderTrace(traceRows);
    };
    setLabel("cliExecutionLabel","STARTING "+total+" COMMAND"+(total===1?"":"S"));
    setLabel("cliDuration","0 / "+total);
    renderTrace([]);
    renderOutput();
    for(let index=0;index<total;index++){
      if(cancelCliRequested)break;
      const command=commands[index];
      outputLines.push("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      outputLines.push("["+String(index+1)+"/"+total+"] $ "+command);
      outputLines.push("");
      setLabel("cliExecutionLabel","RUNNING "+(index+1)+"/"+total+" · REAL PYTHON");
      setLabel("cliDuration",Math.round(performance.now()-startTime)+" ms");
      outputLines.push("Running real Python subprocess…");
      renderOutput();
      outputLines.pop();
      const controller=new AbortController();
      currentCliController=controller;
      const timeout=setTimeout(()=>controller.abort(),22000);
      try{
        const response=await fetch("/api/terminal",{
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({command}),
          cache:"no-store",
          signal:controller.signal,
        });
        const data=await response.json();
        if(!response.ok){
          outputLines.push("[REJECTED / HTTP "+response.status+"]");
          outputLines.push(data.error||"The CLI server rejected this command.");
          outputLines.push("");
          if(data.usage)outputLines.push(data.usage);
          setLabel("cliExecutionLabel","REJECTED · ALLOWLIST",true);
          stoppedByError=true;
          renderOutput();
          break;
        }
        executed++;
        const expectedTamper=command==="ofprov tamper-demo" &&
          data.exit_code===1 && data.steps?.some(step=>step.status==="fixture-change");
        if(data.exit_code===0 || expectedTamper)verified++;
        if(expectedTamper)tamperDetections++;
        outputLines.push(expectedTamper?
          "[✓ TAMPERING DETECTED · EXPECTED EXIT 1]":
          data.exit_code===0?"[✓ SUCCESS · EXIT 0]":"[ERROR · EXIT "+data.exit_code+"]");
        outputLines.push(data.stdout||"(No stdout)");
        if(data.stderr)outputLines.push("[stderr]\n"+data.stderr);
        if(expectedTamper){
          outputLines.push("# Modified bytes were detected by real provenance verification.");
          outputLines.push("# Exit code 1 is expected when verification detects changed files.");
        }
        if(Array.isArray(data.steps)&&data.steps.length){
          outputLines.push("# See underlying Python subprocess steps below.");
          for(const step of data.steps){
            traceRows.push({ ...step,command:"["+String(index+1)+"/"+total+"] "+step.command });
          }
        }
        outputLines.push("");
        if(data.exit_code!==0&&!expectedTamper){
          stoppedByError=true;
          setLabel("cliExecutionLabel","STOPPED · COMMAND ERROR",true);
          renderOutput();
          break;
        }
        renderOutput();
      }catch(error){
        if(cancelCliRequested){
          outputLines.push("[QUEUE STOPPED BY USER]");
          setLabel("cliExecutionLabel","QUEUE STOPPED");
        }else{
          outputLines.push("[NETWORK OR PYTHON ERROR] "+error.message);
          outputLines.push("# No fake output was substituted.");
          setLabel("cliExecutionLabel","NETWORK OR RUNTIME ERROR",true);
          stoppedByError=true;
        }
        renderOutput();
        break;
      }finally{
        clearTimeout(timeout);
        currentCliController=null;
      }
    }
    const elapsed=Math.round(performance.now()-startTime);
    if(cancelCliRequested){
      setLabel("cliExecutionLabel","QUEUE STOPPED · "+executed+"/"+total);
    }else if(!stoppedByError){
      if(total===1 && tamperDetections===1)setLabel("cliExecutionLabel","TAMPER DETECTED · EXPECTED");
      else if(total===1)setLabel("cliExecutionLabel","EXECUTED · REAL PYTHON");
      else setLabel("cliExecutionLabel",verified+"/"+total+" EXECUTED"+
        (tamperDetections?" · "+tamperDetections+" TAMPER DETECTED":""));
    }
    outputLines.push("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    outputLines.push("# "+executed+"/"+total+" commands returned · "+
      verified+" expected result"+(verified===1?"":"s")+
      " · "+elapsed+" ms total");
    outputLines.push("# Each command had its own temporary project. No data persists.");
    renderOutput();
    setLabel("cliDuration",elapsed+" ms");
    stopCli.hidden=true;requestRunning=false;cancelCliRequested=false;
    cliRun.disabled=false;cliRun.textContent="▶ Run commands";
  }
  stopCli.addEventListener("click",()=>{
    if(!requestRunning)return;
    cancelCliRequested=true;
    if(currentCliController)currentCliController.abort();
    stopCli.disabled=true;stopCli.textContent="Stopping…";
    // Abort stops the browser queue. Vercel may finish the current short
    // bounded subprocess server-side; no API cancellation is claimed.
    setTimeout(()=>{stopCli.disabled=false;stopCli.textContent="Stop queue";},500);
  });
  cliRun.addEventListener("click",runCli);
  $("clearCli").addEventListener("click",()=>{
    cliOutput.textContent="# Output cleared.\n# Type commands on separate lines, or load the 4-step demo.";
    renderTrace([]);setLabel("cliExecutionLabel","READY TO EXECUTE");setLabel("cliDuration","—");
  });

  function appendPython(message){
    const str=String(message??"");
    if(pythonOutputBytes>=MAX_VISIBLE)return;
    const allowed=str.slice(0,MAX_VISIBLE-pythonOutputBytes);
    pyOutput.textContent+=allowed+"\n";pythonOutputBytes+=allowed.length;
    pyOutput.scrollTop=pyOutput.scrollHeight;
  }
  function stopTimers(){
    clearTimeout(pyTimer);clearTimeout(workerLoadTimer);pyTimer=null;workerLoadTimer=null;
  }
  function resetPython(silent=false){
    workerGeneration++;stopTimers();if(worker)worker.terminate();worker=null;
    pythonBusy=false;pythonLoading=false;pyRun.disabled=false;
    setEngine(pyStatus,"ENGINE IDLE");
    if(!silent){
      setLabel("pyExecutionLabel","STOPPED / RESET");setLabel("pyDuration","—");
      appendPython("[Python worker terminated; next Run starts a clean interpreter.]");
    }
  }
  function bootWorker(){
    const generation=++workerGeneration;
    worker=new Worker("/py-worker.js",{name:"omniforge-pyodide"});
    worker.onmessage=event=>{
      if(generation!==workerGeneration)return;
      const msg=event.data||{};
      if(msg.type==="loading"){
        pythonLoading=true;setEngine(pyStatus,"DOWNLOADING PYTHON");
        setLabel("pyExecutionLabel","STARTING WEBASSEMBLY");
      }else if(msg.type==="ready"){
        pythonLoading=false;clearTimeout(workerLoadTimer);
        setEngine(pyStatus,"PYTHON "+msg.version,true);
        setLabel("pyExecutionLabel","RUNNING IN YOUR BROWSER");
        pyTimer=setTimeout(()=>{
          appendPython("[Execution exceeded 10 seconds; worker stopped.]");
          resetPython(true);setLabel("pyExecutionLabel","TIME LIMIT REACHED",true);
        },10000);
      }else if(msg.type==="stdout")appendPython(msg.text);
      else if(msg.type==="stderr")appendPython("[stderr] "+msg.text);
      else if(msg.type==="result"){
        if(msg.value!=null&&msg.value!=="")appendPython("=> "+msg.value);
      }else if(msg.type==="done"){
        clearTimeout(pyTimer);pythonBusy=false;pyRun.disabled=false;
        setLabel("pyExecutionLabel",msg.ok?"COMPLETED · REAL PYTHON":"PYTHON EXCEPTION",!msg.ok);
        setLabel("pyDuration",Math.round(performance.now()-pyStart)+" ms (incl. start)");
        if(msg.error)appendPython(msg.error);
      }else if(msg.type==="fatal"){
        appendPython("Python WebAssembly failed: "+(msg.error||"unknown"));
        resetPython(true);setLabel("pyExecutionLabel","ENGINE ERROR",true);
      }
    };
    worker.onerror=()=>{
      if(generation!==workerGeneration)return;
      appendPython("Python WebAssembly worker error. Check jsDelivr network access.");
      resetPython(true);setLabel("pyExecutionLabel","ENGINE ERROR",true);
    };
    workerLoadTimer=setTimeout(()=>{
      appendPython("[Python engine download timed out. Check internet access.]");
      resetPython(true);setLabel("pyExecutionLabel","ENGINE DOWNLOAD TIMEOUT",true);
    },60000);
  }
  function runPython(){
    if(pythonBusy)return;
    const code=pyInput.value;
    if(!code.trim()){pyOutput.textContent="Write Python code first.";return}
    if(code.length>8000){pyOutput.textContent="Maximum 8,000 characters.";return}
    pythonBusy=true;pythonOutputBytes=0;pyOutput.textContent="";pyRun.disabled=true;
    setLabel("pyExecutionLabel","QUEUED · BROWSER RUNTIME");
    setLabel("pyDuration","…");pyStart=performance.now();
    if(!worker)bootWorker();
    worker.postMessage({type:"run",code});
  }
  pyRun.addEventListener("click",runPython);
  $("stopPython").addEventListener("click",()=>resetPython());
  $("clearPython").addEventListener("click",()=>{pyOutput.textContent="";pythonOutputBytes=0});
  document.querySelectorAll("[data-python]").forEach(button=>{
    button.addEventListener("click",()=>{
      const key=button.dataset.python;
      if(!examples[key])return;
      pyInput.value=examples[key];
      document.querySelectorAll("[data-python]").forEach(item=>item.classList.toggle("selected",item===button));
      pyInput.focus();
    });
  });
  pyInput.addEventListener("keydown",event=>{
    if(event.key==="Tab"){
      event.preventDefault();
      pyInput.setRangeText("    ",pyInput.selectionStart,pyInput.selectionEnd,"end");
    }
  });
  document.addEventListener("keydown",event=>{
    if((event.ctrlKey||event.metaKey)&&event.key==="Enter"){
      event.preventDefault();
      if(!$("cliPanel").hidden)runCli();else runPython();
    }
  });
  $("menuToggle").addEventListener("click",()=>{
    const nav=document.querySelector(".site-head nav");
    const open=nav.classList.toggle("open");
    $("menuToggle").setAttribute("aria-expanded",String(open));
  });
  document.querySelectorAll(".site-head nav a").forEach(anchor=>
    anchor.addEventListener("click",()=>{
      document.querySelector(".site-head nav").classList.remove("open");
      $("menuToggle").setAttribute("aria-expanded","false");
    }));
  updateBatchHint();
  checkServer();
})();
