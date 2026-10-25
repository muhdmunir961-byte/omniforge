/* OmniForge / Topology Engine
   Actual WebGL 3D mesh: procedural parametric tubes (trefoil, orbit, coil),
   tangent-space normals, depth, pointer-orbit, live mesh metrics. No Three.js
   dependency or baked illustration. Safe reduced-motion and low-power mode. */
(() => {
  "use strict";
  const TAU = Math.PI * 2;
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const smallScreen = matchMedia("(max-width: 720px)");
  const clamp = (x,a,b) => Math.max(a,Math.min(b,x));
  const vertexSource = [
    "attribute vec3 aPosition;",
    "attribute vec3 aNormal;",
    "uniform float uYaw, uTilt, uTime, uAspect, uZoom, uPointSize;",
    "varying float vLight, vDistance;",
    "void main(){",
    " vec3 p=aPosition*uZoom;",
    " float y=uYaw+uTime*0.11, x=uTilt;",
    " float cy=cos(y),sy=sin(y),cx=cos(x),sx=sin(x);",
    " p=vec3(cy*p.x+sy*p.z,p.y,-sy*p.x+cy*p.z);",
    " p=vec3(p.x,cx*p.y-sx*p.z,sx*p.y+cx*p.z);",
    " vec3 n=aNormal;",
    " n=vec3(cy*n.x+sy*n.z,n.y,-sy*n.x+cy*n.z);",
    " n=vec3(n.x,cx*n.y-sx*n.z,sx*n.y+cx*n.z);",
    " vLight=0.5+0.5*max(0.0,dot(normalize(n),normalize(vec3(-0.43,0.66,0.61))));",
    " float depth=4.5-p.z;",
    " vDistance=clamp((depth-3.0)/3.2,0.0,1.0);",
    " gl_Position=vec4(p.x*2.05/uAspect,p.y*2.05,depth-0.32,depth);",
    " gl_PointSize=uPointSize*(4.5/depth);",
    "}"
  ].join("\n");
  const fragmentSource = [
    "precision mediump float;",
    "uniform vec3 uColor;",
    "uniform float uOpacity, uMode;",
    "varying float vLight,vDistance;",
    "void main(){",
    " float alpha=uOpacity;",
    " if(uMode>1.5){",
    "  float radial=length(gl_PointCoord-vec2(0.5));",
    "  if(radial>0.5) discard;",
    "  alpha*=smoothstep(0.5,0.08,radial);",
    " }",
    " vec3 color=uColor*(0.68+0.40*vLight)*(1.0-0.27*vDistance);",
    " gl_FragColor=vec4(color,alpha);",
    "}"
  ].join("\n");
  function compile(gl,type,source){
    const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)){
      const info=gl.getShaderInfoLog(s);gl.deleteShader(s);throw Error(info||"shader compile failed");
    }
    return s;
  }
  function createProgram(gl){
    const p=gl.createProgram();
    const vert=compile(gl,gl.VERTEX_SHADER,vertexSource);
    const frag=compile(gl,gl.FRAGMENT_SHADER,fragmentSource);
    gl.attachShader(p,vert);gl.attachShader(p,frag);gl.linkProgram(p);
    gl.deleteShader(vert);gl.deleteShader(frag);
    if(!gl.getProgramParameter(p,gl.LINK_STATUS)){
      const info=gl.getProgramInfoLog(p);gl.deleteProgram(p);throw Error(info||"WebGL link error");
    }
    return p;
  }
  const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const normalize=v=>{const length=Math.hypot(...v)||1;return v.map(value=>value/length);};
  function center(t,kind){
    if(kind==="orbital")return [1.02*Math.cos(t),0.6*Math.sin(2*t+0.5),1.03*Math.sin(t)];
    if(kind==="coil"){const r=0.83+0.20*Math.sin(5*t);return [r*Math.cos(2*t),r*Math.sin(2*t),0.59*Math.sin(5*t)];}
    const r=0.78+0.40*Math.cos(3*t);
    return [r*Math.cos(2*t),r*Math.sin(2*t),0.54*Math.sin(3*t)];
  }
  function makeGeometry(kind,quality){
    const along=quality==="low"?108:218,around=quality==="low"?9:14;
    const thickness=kind==="orbital"?0.125:0.107;
    const positions=[],normals=[],triangles=[],edges=[],dots=[];
    for(let i=0;i<=along;i++){
      const t=i/along*TAU,eps=0.001,point=center(t,kind);
      const before=center(t-eps,kind),after=center(t+eps,kind);
      const tangent=normalize(after.map((x,k)=>x-before[k]));
      const reference=Math.abs(dot(tangent,[0,0,1]))<0.94?[0,0,1]:[0,1,0];
      const normal=normalize(cross(tangent,reference));
      const binormal=normalize(cross(tangent,normal));
      for(let j=0;j<=around;j++){
        const a=j/around*TAU;
        const radial=normalize(normal.map((x,k)=>x*Math.cos(a)+binormal[k]*Math.sin(a)));
        positions.push(...point.map((x,k)=>x+thickness*radial[k]));
        normals.push(...radial);
        if(i<along&&j<around){
          const start=i*(around+1)+j;
          const right=start+1,down=start+around+1,diagonal=down+1;
          triangles.push(start,down,right,right,down,diagonal);
          edges.push(start,right,start,down);
        }
      }
      if(i%4===0)dots.push(i*(around+1));
    }
    return {
      positions:new Float32Array(positions),
      normals:new Float32Array(normals),
      triangles:new Uint16Array(triangles),
      edges:new Uint16Array(edges),
      dots:new Uint16Array(dots),
      vertices:(along+1)*(around+1),
      faces:along*around*2,
      segments:along,
      rings:around,
    };
  }
  const preview={};
  function mount(canvas){
    const stage=canvas.closest("[data-mesh-stage]");
    if(!stage)return;
    const status=stage.querySelector("[data-mesh-status]");
    const fallback=stage.querySelector(".mesh-fallback");
    const setStatus=msg=>{if(status)status.textContent=msg;};
    if(!window.WebGLRenderingContext){setStatus("WEBGL UNAVAILABLE");stage.classList.add("mesh-unavailable");return;}
    let gl;
    try{
      gl=canvas.getContext("webgl",{alpha:true,antialias:true,premultipliedAlpha:false,powerPreference:"low-power",depth:true});
    }catch{}
    if(!gl){setStatus("WEBGL NOT SUPPORTED");stage.classList.add("mesh-unavailable");return;}
    stage.classList.add("mesh-ready");
    if(fallback)fallback.hidden=true;
    let p,attrs,locs,geo,bufs,paused=reduceMotion.matches;
    let yaw=0.42,tilt=-0.27,start=performance.now(),elapsed=0,last=0;
    let visible=true,drag=null,frame=0,raf=0,wire=true;
    let quality=smallScreen.matches||((navigator.deviceMemory||4)<3)?"low":"high";
    let model=canvas.dataset.meshModel||"trefoil";
    const palette=canvas.dataset.meshPalette==="soft"?
      {surface:[0.38,0.38,0.35],wire:[0.93,0.72,0.50],points:[0.95,0.92,0.83]}:
      {surface:[0.38,0.55,0.42],wire:[0.96,0.71,0.48],points:[0.98,0.93,0.81]};
    function buffer(target,data){
      const b=gl.createBuffer();gl.bindBuffer(target,b);gl.bufferData(target,data,gl.STATIC_DRAW);return b;
    }
    function loadModel(which){
      if(!["trefoil","orbital","coil"].includes(which))return;
      model=which;
      if(bufs){Object.values(bufs).forEach(b=>gl.deleteBuffer(b));}
      geo=makeGeometry(model,quality);
      bufs={
        positions:buffer(gl.ARRAY_BUFFER,geo.positions),
        normals:buffer(gl.ARRAY_BUFFER,geo.normals),
        triangles:buffer(gl.ELEMENT_ARRAY_BUFFER,geo.triangles),
        edges:buffer(gl.ELEMENT_ARRAY_BUFFER,geo.edges),
        dots:buffer(gl.ELEMENT_ARRAY_BUFFER,geo.dots),
      };
      stage.querySelectorAll("[data-mesh-model]").forEach(button=>{
        const active=button.dataset.meshModel===model;
        button.classList.toggle("active",active);
        button.setAttribute("aria-pressed",String(active));
      });
      const pairs={vertices:geo.vertices,triangles:geo.faces,segments:geo.segments,rings:geo.rings};
      Object.keys(pairs).forEach(key=>{
        stage.querySelectorAll('[data-metric="'+key+'"]').forEach(el=>el.textContent=pairs[key].toLocaleString("en-US"));
      });
      setStatus("LIVE · GPU GEOMETRY");
      stage.dataset.activeMesh=model;stage.dataset.faceCount=String(geo.faces);
      requestFrame();
    }
    function setAttrib(loc,b){
      gl.bindBuffer(gl.ARRAY_BUFFER,b);
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc,3,gl.FLOAT,false,0,0);
    }
    function setup(){
      p=createProgram(gl);gl.useProgram(p);
      attrs={position:gl.getAttribLocation(p,"aPosition"),normal:gl.getAttribLocation(p,"aNormal")};
      locs=Object.fromEntries(["uYaw","uTilt","uTime","uAspect","uZoom","uPointSize","uColor","uOpacity","uMode"].map(n=>[n,gl.getUniformLocation(p,n)]));
      gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
      gl.disable(gl.CULL_FACE);gl.disable(gl.DEPTH_TEST);
      gl.clearColor(0,0,0,0);
      loadModel(model);
    }
    function draw(at){
      if(!p||!geo)return;
      const rect=canvas.getBoundingClientRect();
      if(!rect.width||!rect.height)return;
      const dpr=Math.min(window.devicePixelRatio||1,smallScreen.matches?1.35:1.7);
      const w=Math.max(1,Math.round(rect.width*dpr)),h=Math.max(1,Math.round(rect.height*dpr));
      if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
      gl.viewport(0,0,w,h);
      gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
      gl.useProgram(p);
      setAttrib(attrs.position,bufs.positions);
      setAttrib(attrs.normal,bufs.normals);
      gl.uniform1f(locs.uYaw,yaw);
      gl.uniform1f(locs.uTilt,tilt);
      gl.uniform1f(locs.uAspect,w/h);
      gl.uniform1f(locs.uZoom,stage.classList.contains("mesh-hero")?1.32:1.65);
      gl.uniform1f(locs.uPointSize,stage.classList.contains("mesh-hero")?3.9:4.8);
      gl.uniform1f(locs.uTime,elapsed);
      gl.uniform1f(locs.uMode,0);
      gl.uniform3fv(locs.uColor,palette.surface);
      gl.uniform1f(locs.uOpacity,0.13);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,bufs.triangles);
      gl.drawElements(gl.TRIANGLES,geo.triangles.length,gl.UNSIGNED_SHORT,0);
      if(wire){
        gl.uniform1f(locs.uMode,1);
        gl.uniform3fv(locs.uColor,palette.wire);
        gl.uniform1f(locs.uOpacity,0.67);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,bufs.edges);
        gl.drawElements(gl.LINES,geo.edges.length,gl.UNSIGNED_SHORT,0);
      }
      gl.uniform1f(locs.uMode,2);
      gl.uniform3fv(locs.uColor,palette.points);
      gl.uniform1f(locs.uOpacity,0.96);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,bufs.dots);
      gl.drawElements(gl.POINTS,geo.dots.length,gl.UNSIGNED_SHORT,0);
      frame++;
      if(stage.dataset.webglState!=="rendered"){stage.dataset.webglState="rendered";}
      if(stage.querySelector("[data-metric='fps']")&&last!==0&&frame%30===0){
        stage.querySelector("[data-metric='fps']").textContent=String(Math.round(1000/Math.max(1,at-last)));
      }
    }
    function animate(at){
      raf=0;
      const targetRate=smallScreen.matches?1000/30:1000/45;
      if(!visible||document.hidden)return;
      if(!last||at-last>=targetRate){
        if(!paused)elapsed+=(last?Math.min(at-last,60):0)/1000;
        draw(at);last=at;
      }
      if(!paused)requestFrame();
    }
    function requestFrame(){if(!raf&&visible&&!document.hidden)raf=requestAnimationFrame(animate);}
    function togglePause(value){
      paused=Boolean(value);
      stage.querySelectorAll("[data-mesh-pause]").forEach(button=>{
        button.textContent=paused?"Resume motion":"Pause motion";
        button.setAttribute("aria-pressed",String(paused));
      });
      requestFrame();
    }
    stage.querySelectorAll("[data-mesh-model]").forEach(button=>button.addEventListener("click",()=>loadModel(button.dataset.meshModel)));
    stage.querySelectorAll("[data-mesh-pause]").forEach(button=>button.addEventListener("click",()=>togglePause(!paused)));
    stage.querySelectorAll("[data-mesh-wire]").forEach(button=>button.addEventListener("click",()=>{
      wire=!wire;button.setAttribute("aria-pressed",String(wire));button.textContent=wire?"Wireframe ON":"Wireframe OFF";requestFrame();
    }));
    stage.querySelectorAll("[data-mesh-reset]").forEach(button=>button.addEventListener("click",()=>{
      yaw=0.42;tilt=-0.27;elapsed=0;requestFrame();
    }));
    canvas.addEventListener("pointerdown",event=>{
      if(event.button!==0||reduceMotion.matches)return;
      drag={x:event.clientX,y:event.clientY,yaw,tilt};canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener("pointermove",event=>{
      if(!drag)return;
      yaw=drag.yaw+(event.clientX-drag.x)*0.008;
      tilt=clamp(drag.tilt+(event.clientY-drag.y)*0.008,-1.5,1.5);
      requestFrame();
    });
    ["pointerup","pointercancel","lostpointercapture"].forEach(kind=>canvas.addEventListener(kind,()=>{drag=null;}));
    canvas.addEventListener("keydown",event=>{
      if(!["ArrowLeft","ArrowRight","ArrowUp","ArrowDown"].includes(event.key))return;
      event.preventDefault();
      if(event.key==="ArrowLeft")yaw-=0.15;
      if(event.key==="ArrowRight")yaw+=0.15;
      if(event.key==="ArrowUp")tilt=clamp(tilt-0.15,-1.5,1.5);
      if(event.key==="ArrowDown")tilt=clamp(tilt+0.15,-1.5,1.5);
      requestFrame();
    });
    const observer=new IntersectionObserver(entries=>{
      visible=entries[0].isIntersecting;
      if(visible)requestFrame();else if(raf){cancelAnimationFrame(raf);raf=0;}
    },{threshold:0.04});
    observer.observe(stage);
    const resize=new ResizeObserver(()=>requestFrame());resize.observe(canvas);
    const vis=()=>{if(!document.hidden)requestFrame();};
    document.addEventListener("visibilitychange",vis);
    const onMotion=()=>togglePause(reduceMotion.matches);
    if(reduceMotion.addEventListener)reduceMotion.addEventListener("change",onMotion);
    canvas.addEventListener("webglcontextlost",event=>{
      event.preventDefault();if(raf)cancelAnimationFrame(raf);raf=0;
      setStatus("GRAPHICS CONTEXT LOST");stage.dataset.webglState="lost";
    });
    canvas.addEventListener("webglcontextrestored",()=>{bufs=null;setup();});
    try{setup();togglePause(reduceMotion.matches);requestFrame();}
    catch(error){
      console.warn("OmniForge Mesh:",error?.message||error);
      stage.classList.remove("mesh-ready");stage.classList.add("mesh-unavailable");
      stage.dataset.webglState="unavailable";if(fallback)fallback.hidden=false;
      setStatus("STATIC FALLBACK");
    }
    preview[canvas.id||"mesh"]=()=>({model,faces:geo?.faces||0,vertices:geo?.vertices||0,rendered:stage.dataset.webglState==="rendered"});
  }
  function start(){document.querySelectorAll("canvas[data-mesh-canvas]").forEach(mount);}
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start,{once:true});
  else start();
  window.OmniForgeMesh={getScene:id=>preview[id]?.()||null};
})();
