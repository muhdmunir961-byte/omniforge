"""Generate *real* OBJ triangular meshes with positions, UVs and normals.

Offline, standard-library only. Writes a new OBJ with exclusive create.
Does not import models, execute input files or contact networks.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def generate(shape: str, rings: int, segments: int, radius: float,
             major_radius: float, minor_radius: float) -> tuple[list, list, list, list]:
    if shape not in ("torus", "uv-sphere"):
        raise ValueError("Choose torus or uv-sphere")
    if not 3 <= rings <= 256 or not 3 <= segments <= 256:
        raise ValueError("rings and segments must each be 3-256")
    if not all(math.isfinite(v) and 0.001 <= v <= 1000 for v in
               (radius, major_radius, minor_radius)):
        raise ValueError("radii must be finite, between 0.001 and 1000")
    if shape == "torus" and minor_radius >= major_radius:
        raise ValueError("minor-radius must be smaller than major-radius for a non-self-intersecting torus")
    positions, texcoords, normals, faces = [], [], [], []
    for ring in range(rings + 1):
        u = ring / rings
        a = 2 * math.pi * u
        cos_a, sin_a = math.cos(a), math.sin(a)
        for segment in range(segments + 1):
            v = segment / segments
            b = 2 * math.pi * v
            cos_b, sin_b = math.cos(b), math.sin(b)
            if shape == "torus":
                outer = major_radius + minor_radius * cos_b
                point = (outer * cos_a, outer * sin_a, minor_radius * sin_b)
                normal = (cos_a * cos_b, sin_a * cos_b, sin_b)
            else:
                theta = math.pi * v
                point = (radius * math.sin(theta) * cos_a,
                         radius * math.sin(theta) * sin_a,
                         radius * math.cos(theta))
                normal = (math.sin(theta) * cos_a,
                          math.sin(theta) * sin_a,
                          math.cos(theta))
            positions.append(point)
            texcoords.append((u, v))
            normals.append(normal)
    stride = segments + 1
    for ring in range(rings):
        for seg in range(segments):
            i = ring * stride + seg + 1
            j = i + stride
            # Parametrization: d/du x d/dv points toward outside for torus;
            # reversed winding for latitude sphere due to theta increasing.
            if shape == "torus":
                faces.append((i, j, i + 1))
                faces.append((i + 1, j, j + 1))
            else:
                if seg != 0 and ring == -1:
                    raise AssertionError("Unreachable")
                if seg == -1:
                    raise AssertionError("Unreachable")
                # Avoid spherical cap degeneracy with triangle selection.
                if seg > 0:
                    faces.append((i, i + 1, j))
                    faces.append((i + 1, j + 1, j))
    if shape == "uv-sphere":
        # A full UV sphere spans longitude around rings and latitude over segments.
        # The above seg > 0 prevents the upper pole strip degeneracy, but
        # the lower pole strip also needs one triangle per cell.
        faces.clear()
        for ring in range(rings):
            for seg in range(segments):
                i = ring * stride + seg + 1
                j = i + stride
                if seg != 0:
                    faces.append((i, j, i + 1))
                if seg != segments - 1:
                    faces.append((i + 1, j, j + 1))
    return positions, texcoords, normals, faces


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write offline torus/sphere 3D Wavefront OBJ mesh")
    parser.add_argument("--shape", choices=("torus", "uv-sphere"), default="torus")
    parser.add_argument("--rings", type=int, default=48)
    parser.add_argument("--segments", type=int, default=16)
    parser.add_argument("--radius", type=float, default=1.0)
    parser.add_argument("--major-radius", type=float, default=1.15)
    parser.add_argument("--minor-radius", type=float, default=0.32)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        vertices, uv, normals, triangles = generate(
            args.shape, args.rings, args.segments, args.radius,
            args.major_radius, args.minor_radius,
        )
    except ValueError as exc:
        parser.error(str(exc))
    target = args.out.expanduser()
    if target.suffix.lower() != ".obj" or target.is_symlink() or target.exists():
        parser.error("Output must be a NEW .obj file (never overwrite/symlink)")
    if not target.parent.is_dir() or target.parent.is_symlink():
        parser.error("Output parent directory must already exist and not be a symlink")
    lines = ["# OmniForge generated real triangular Wavefront OBJ",
             "o " + args.shape.replace("-", "_")]
    lines.extend("v {:.8f} {:.8f} {:.8f}".format(*pos) for pos in vertices)
    lines.extend("vt {:.8f} {:.8f}".format(*tex) for tex in uv)
    lines.extend("vn {:.8f} {:.8f} {:.8f}".format(*n) for n in normals)
    lines.append("s 1")
    lines.extend("f {0}/{0}/{0} {1}/{1}/{1} {2}/{2}/{2}".format(*face) for face in triangles)
    with target.open("x", encoding="utf-8", newline="\n") as file:
        file.write("\n".join(lines) + "\n")
    print(json.dumps({"shape": args.shape, "path": str(target),
                      "vertices": len(vertices), "triangles": len(triangles),
                      "has_normals": True, "has_uv": True}, indent=2))


if __name__ == "__main__":
    main()
