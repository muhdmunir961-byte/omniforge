/* OmniForge actual runtime terminal. Never replay fake CLI results. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const cliInput=$("commandInput"),cliOutput=$("cliOutput"),cliRun=$("runCli");
  const cliStatus=$("cliRuntimeStatus"),pyOutput=$("pythonOutput"),pyInput=$("pythonInput");
  const pyRun=$("runPython"),pyStatus=$("pyVersion"),MAX_VISIBLE=24000;
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
  }
  document.querySelectorAll("[data-command]").forEach(el=>
    el.addEventListener("click",()=>setCommand(el.dataset.command||"omniforge doctor")));
  cliInput.addEventListener("keydown",ev=>{
    if(ev.key==="Enter"){ev.preventDefault();runCli()}
    else if(ev.key==="ArrowUp"&&cliHistory.length){
      ev.preventDefault();historyPosition=Math.min(cliHistory.length-1,historyPosition+1);
      cliInput.value=cliHistory[cliHistory.length-1-historyPosition];
    }else if(ev.key==="ArrowDown"&&cliHistory.length){
      ev.preventDefault();historyPosition=Math.max(-1,historyPosition-1);
      cliInput.value=historyPosition<0?"":cliHistory[cliHistory.length-1-historyPosition];
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
    const command=cliInput.value.trim();
    if(!command||command.length>240){cliOutput.textContent="Enter one command (max 240 characters).";return}
    if(!apiReady){await checkServer();if(!apiReady)return}
    requestRunning=true;cliRun.disabled=true;cliRun.textContent="Running…";
    cliHistory.push(command);if(cliHistory.length>25)cliHistory.shift();historyPosition=-1;
    setLabel("cliExecutionLabel","EXECUTING · SERVER PYTHON");setLabel("cliDuration","…");
    cliOutput.textContent="$ "+command+"\n\nRunning actual Python…";renderTrace([]);
    const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),22000);
    const started=performance.now();
    try{
      const response=await fetch("/api/terminal",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({command}),cache:"no-store",signal:ctl.signal,
      });
      const data=await response.json();
      if(!response.ok){
        cliOutput.textContent="$ "+command+"\n\n[REJECTED / "+response.status+"]\n"+
          pretty(data.error||"Unknown error")+(data.usage?"\n\n"+data.usage:"");
        setLabel("cliExecutionLabel","REJECTED · ALLOWLIST",true);
        setLabel("cliDuration",Math.round(performance.now()-started)+" ms");return;
      }
      const lines=["$ "+command,"",data.stdout||"(No stdout)"];
      if(data.stderr)lines.push("","[stderr]",data.stderr);
      if(data.steps?.length)lines.push("","# See prerequisite Python processes below.");
      if(data.exit_code!==0)lines.push("","# Exit code: "+data.exit_code);
      cliOutput.textContent=pretty(lines.join("\n"));
      setLabel("cliExecutionLabel",data.exit_code===0?"EXECUTED · REAL PYTHON":"RETURNED EXIT "+data.exit_code,data.exit_code!==0);
      setLabel("cliDuration",(data.duration_ms??"?")+" ms");
      renderTrace(data.steps);
    }catch(err){
      cliOutput.textContent="Real API execution failed: "+err.message+
        "\nNo prerecorded output was substituted.";
      setLabel("cliExecutionLabel","NETWORK OR RUNTIME ERROR",true);
      setLabel("cliDuration",Math.round(performance.now()-started)+" ms");
    }finally{clearTimeout(timer);requestRunning=false;cliRun.disabled=false;cliRun.textContent="Run command ↗"}
  }
  cliRun.addEventListener("click",runCli);
  $("clearCli").addEventListener("click",()=>{
    cliOutput.textContent="# Output cleared.\n# Run a supported command.";
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
  checkServer();
})();
