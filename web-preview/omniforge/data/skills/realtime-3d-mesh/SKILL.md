---
name: realtime-3d-mesh
description: "Create genuine interactive WebGL 3D mesh experiences using Three.js, React Three Fiber, glTF, procedural vertices normals UVs, PBR lighting and performance-aware mobile fallback."
---
# Real-time 3D Mesh: real geometry, not CSS imitation

## Activate
Use for 3D product showcases, WebGL or WebGPU, react-three-fiber, Three.js, Blender-to-web pipelines, shaders, automotive CAD presentation, interactive mesh and model viewers.

## Real geometry requirements
Show actual three-dimensional vertices, triangles, winding, normals, UVs, material and perspective camera. A CSS perspective transform or SVG is not an interactive 3D model. For automotive models use metric units and physically plausible geometry and axle placements.

## Stack choice
- Plain HTML/JS: Three.js scene, camera, renderer, mesh, OrbitControls; pin a compatible version and test imports.
- React/Next.js: @react-three/fiber and optional @react-three/drei; use client-only components when SSR is present.
- Imported assets: owned or licensed glTF/GLB, validated units/origin, inspect texture permissions and asset size. Prefer KTX2, Meshopt or Draco only with working runtime decoders.
- Materials: start MeshStandardMaterial physically based shading, correct sRGB/tone mapping and measured exposure. Use custom GLSL when justified, not for routine glow.

## Procedure
1. Define subject, physical scale, scene goals and source assets.
2. Design a usable 3D camera: framing, near/far, field of view, target, zoom and reset view. Avoid clipping and small mobile compositions.
3. Build indexed triangle geometry with normal direction, UV seams and material assignments. Check degenerate triangles, bounding box, consistent orientation and vertex count.
4. Light like a product photographer: key, fill, rim, believable reflections and intentionally restrained postprocessing.
5. Interactions: drag/orbit, pinch zoom, click hotspots, keyboard fallback and accessibility description. Provide a true pause and reset.
6. Performance budget: cap mobile device pixel ratio, lazy-load canvas, pause offscreen animation, reduce geometry/texture quality on weaker devices, use instancing and dispose of GPU resources at unmount.
7. Fallback: image/poster and descriptive HTML, with full page utility even when WebGL is unsupported or reduced-data mode is enabled.
8. Verify scene in actual browser on multiple viewport sizes; detect console errors, context loss, loading failures, touch operation and reduced-motion.
9. Show screenshot and working interactive preview only if truly executed. Do not claim that an OBJ file alone is a running WebGL scene.

## Working procedural mesh generator
Included standard-library Python: python scripts/mesh_generator.py --shape torus --major-radius 1.15 --minor-radius 0.32 --rings 48 --segments 16 --out demo.obj

Or sphere: python scripts/mesh_generator.py --shape uv-sphere --radius 1 --rings 24 --segments 32 --out sphere.obj

The generator writes **real Wavefront OBJ geometry** with vertex positions, vertex normals, texture coordinates and triangulated faces. No Three.js or Blender installation is bundled. Import/export to runtime GLB using an authorized compatible tool.

## Browser implementation checklist
Correct Three.js module imports, ResizeObserver cleanup, sensible camera clipping, capped pixel ratio, render loop disposal, shader uniform updates and an accessible HTML alternative. Test PBR lighting, normals and mesh winding. Never auto-fetch assets or install libraries without approval.