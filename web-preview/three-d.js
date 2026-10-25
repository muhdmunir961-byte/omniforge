/* Native WebGL2 interactive 3D, real vertices and triangles, no fake CSS mesh. */
(()=>{"use strict";
const $=id=>document.getElementById(id),canvas=$("gl");
const gl=canvas.getContext("webgl2",{antialias:true,alpha:false});
let shape="torus",wire=false,ax=.3,ay=-.6,distance=4.4,paused=false,drag=false,last=null,mesh=null,program=null,vao=null,buffer=null,count=0,edges=0,old=0;
const norm=p=>{let d=Math.hypot(...p)||1;return p.map(n=>n/d)};
function generate(s){
  const positions=[],normals=[],faces=[];
  const tri=(a,b,c,an,bn,cn)=>{const i=positions.length/3;positions.push(...a,...b,...c);normals.push(...an,...bn,...cn);faces.push(i,i+1,i+2)};
  if(s==="cube"){
    const v=[[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]];
    const panels=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[3,7,6,2],[0,4,7,3],[1,2,6,5]];
    panels.forEach(q=>{const a=v[q[0]],b=v[q[1]],c=v[q[2]],d=v[q[3]];
      const x=b.map((t,i)=>t-a[i]),y=c.map((t,i)=>t-a[i]),n=norm([x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0]]);
      tri(a,b,c,n,n,n);tri(a,c,d,n,n,n)});
  }else{
    const rings=48,segs=32;
    const pos=(i,j)=>{
      const u=i*2*Math.PI/rings,v=j*(s==="torus"?2*Math.PI:Math.PI)/segs;
      if(s==="sphere")return [Math.sin(v)*Math.cos(u),Math.sin(v)*Math.sin(u),Math.cos(v)];
      const r=1.1+.34*Math.cos(v);return [r*Math.cos(u),r*Math.sin(u),.34*Math.sin(v)];
    };
    const n=p=>s==="sphere"?norm(p):norm([(Math.hypot(p[0],p[1])-1.1)*p[0]/Math.hypot(p[0],p[1]),(Math.hypot(p[0],p[1])-1.1)*p[1]/Math.hypot(p[0],p[1]),p[2]]);
    for(let i=0;i<rings;i++)for(let j=0;j<segs;j++){
      const a=pos(i,j),b=pos(i+1,j),c=pos(i+1,j+1),d=pos(i,j+1);
      if(j!==0||s==="torus")tri(a,b,d,n(a),n(b),n(d));
      if(j!==segs-1||s==="torus")tri(b,c,d,n(b),n(c),n(d));
    }
  }
  const lines=[];for(let i=0;i<faces.length;i+=3){const [a,b,c]=faces.slice(i,i+3);lines.push(a,b,b,c,c,a)}
  return {positions,normals,faces,lines};
}
function shader(kind,code){
 const h=gl.createShader(kind);gl.shaderSource(h,code);gl.compileShader(h);
 if(!gl.getShaderParameter(h,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(h));return h;
}
function start(){
 const vs=shader(gl.VERTEX_SHADER,[
 "#version 300 es","in vec3 aPosition;in vec3 aNormal;","uniform mat4 uProjection;uniform mat4 uModel;","out vec3 vNormal;",
 "void main(){gl_Position=uProjection*uModel*vec4(aPosition,1.0);vNormal=mat3(uModel)*aNormal;}"
 ].join("\n"));
 const fs=shader(gl.FRAGMENT_SHADER,[
 "#version 300 es","precision highp float;","in vec3 vNormal;uniform bool uWire;out vec4 outColor;",
 "void main(){vec3 n=normalize(vNormal);float l=max(dot(n,normalize(vec3(-.5,.8,1.5))),0.0);vec3 c=uWire?vec3(.95,.77,.5):vec3(.72,.44,.26);outColor=vec4(c*(.28+.72*l),1.0);}"
 ].join("\n"));
 program=gl.createProgram();gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);
 if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
 gl.deleteShader(vs);gl.deleteShader(fs);gl.enable(gl.DEPTH_TEST);gl.clearColor(.12,.17,.14,1);
 upload();
 requestAnimationFrame(render);
}
function upload(){
 mesh=generate(shape);
 $("verts").textContent=(mesh.positions.length/3).toLocaleString();
 $("tris").textContent=(mesh.faces.length/3).toLocaleString();
 $("sceneLabel").textContent=shape.toUpperCase()+" · PARAMETRIC";
 $("zoom").textContent=distance.toFixed(1)+"×";
 if(!gl||!program)return;
 if(vao)gl.deleteVertexArray(vao);if(buffer)gl.deleteBuffer(buffer);
 vao=gl.createVertexArray();gl.bindVertexArray(vao);
 const d=new Float32Array(mesh.positions.length*2);
 for(let i=0,j=0;i<mesh.positions.length;i+=3,j+=6)for(let k=0;k<3;k++){d[j+k]=mesh.positions[i+k];d[j+k+3]=mesh.normals[i+k]}
 buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,d,gl.STATIC_DRAW);
 for(const [attr,offset] of [["aPosition",0],["aNormal",12]]){const loc=gl.getAttribLocation(program,attr);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,24,offset)}
 const ids=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ids);
 gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint32Array([...mesh.faces,...mesh.lines]),gl.STATIC_DRAW);
 count=mesh.faces.length;edges=mesh.lines.length;gl.bindVertexArray(null);
}
function render(t){
 if(!paused&&!drag)ay+=Math.min(40,t-old||16)*.00025;old=t;
 const ratio=Math.min(devicePixelRatio||1,1.8),w=Math.round(canvas.clientWidth*ratio),h=Math.round(canvas.clientHeight*ratio);
 if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h}
 gl.viewport(0,0,w,h);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
 const aspect=w/Math.max(h,1),f=1/Math.tan(Math.PI/5),near=.1,far=100;
 const projection=new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,(far+near)/(near-far),-1,0,0,2*far*near/(near-far),0]);
 const cx=Math.cos(ax),sx=Math.sin(ax),cy=Math.cos(ay),sy=Math.sin(ay);
 const model=new Float32Array([cy,cx*sy,sx*sy,0,-sy,cx*cy,sx*cy,0,0,-sx,cx,0,0,0,-distance,1]);
 gl.useProgram(program);gl.uniformMatrix4fv(gl.getUniformLocation(program,"uProjection"),false,projection);
 gl.uniformMatrix4fv(gl.getUniformLocation(program,"uModel"),false,model);
 gl.uniform1i(gl.getUniformLocation(program,"uWire"),wire?1:0);
 gl.bindVertexArray(vao);gl.disable(gl.CULL_FACE);
 gl.drawElements(wire?gl.LINES:gl.TRIANGLES,wire?edges:count,gl.UNSIGNED_INT,wire?count*4:0);
 requestAnimationFrame(render);
}
for(const type of ["torus","sphere","cube"])$(type).onclick=()=>{
 shape=type;for(const x of ["torus","sphere","cube"])$(x).classList.toggle("active",x===type);upload();
};
for(const type of ["solid","wire"])$(type).onclick=()=>{
 wire=type==="wire";$("solid").classList.toggle("active",!wire);$("wire").classList.toggle("active",wire);
};
$("pause").onclick=()=>{paused=!paused;$("pause").textContent=paused?"Resume animation":"Pause animation"};
$("reset").onclick=()=>{ax=.3;ay=-.6;distance=4.4;$("zoom").textContent=distance.toFixed(1)+"×"};
canvas.onpointerdown=e=>{drag=true;last=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId)};
canvas.onpointermove=e=>{if(!drag)return;ay+=(e.clientX-last[0])*.008;ax=Math.max(-1.5,Math.min(1.5,ax+(e.clientY-last[1])*.008));last=[e.clientX,e.clientY]};
for(const evt of ["pointerup","pointercancel","lostpointercapture"])canvas.addEventListener(evt,()=>{drag=false;last=null});
canvas.addEventListener("wheel",e=>{e.preventDefault();distance=Math.max(2.2,Math.min(8,distance+e.deltaY*.005));$("zoom").textContent=distance.toFixed(1)+"×"},{passive:false});
canvas.addEventListener("keydown",e=>{if(e.key.startsWith("Arrow")){e.preventDefault();ay+=e.key==="ArrowRight"?.11:e.key==="ArrowLeft"?-.11:0;ax+=e.key==="ArrowDown"?.11:e.key==="ArrowUp"?-.11:0}});
$("download").onclick=()=>{
 if(!mesh)return;
 const data=["# OmniForge real 3D geometry","o "+shape];
 for(let i=0;i<mesh.positions.length;i+=3)data.push("v "+mesh.positions.slice(i,i+3).map(v=>v.toFixed(6)).join(" "));
 for(let i=0;i<mesh.normals.length;i+=3)data.push("vn "+mesh.normals.slice(i,i+3).map(v=>v.toFixed(6)).join(" "));
 for(let i=0;i<mesh.faces.length;i+=3)data.push("f "+mesh.faces.slice(i,i+3).map(n=>(n+1)+"//"+(n+1)).join(" "));
 const url=URL.createObjectURL(new Blob([data.join("\n")+"\n"],{type:"text/plain"}));
 const a=document.createElement("a");a.href=url;a.download="omniforge-"+shape+".obj";a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
};
if(!gl){$("fallback").style.display="flex";$("fps").textContent="NO WEBGL2";upload();}
else{try{start()}catch(e){$("fallback").textContent="WebGL2 error: "+e.message;$("fallback").style.display="flex";upload()}}
})();