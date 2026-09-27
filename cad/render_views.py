"""Renders review images of the radio from a mesh dump, outside FreeCAD.

FreeCAD's own screenshot/offscreen paths return blank or scrambled images on
some Wayland/GL setups, so this is a small numpy z-buffer rasteriser instead.

Usage:
  1. In FreeCAD (with DigitalRadioAlarm open), run export_mesh() from this file,
     or: exec(open("cad/render_views.py").read()); export_mesh("cad/mesh.npz")
  2. python3 cad/render_views.py cad/mesh.npz docs/img/
"""

import sys

import numpy as np


def export_mesh(path, tolerance=0.2):
    """Run inside FreeCAD: dump triangles, colours and labels to an .npz."""
    import FreeCAD as App
    import Part

    doc = App.getDocument("DigitalRadioAlarm")
    pts_all, tris, cols, names = [], [], [], []
    for o in doc.Objects:
        if o.TypeId == "App::DocumentObjectGroup" or not hasattr(o, "Shape") or o.Shape.isNull():
            continue
        shp = o.Shape
        if not shp.Faces and shp.Wires:
            shp = Part.Face(shp.Wires)              # ShapeString outlines -> fillable face
        pts, fac = shp.tessellate(tolerance)
        if not fac:
            continue
        off = len(pts_all)
        pts_all += [(p.x, p.y, p.z) for p in pts]
        tris += [(a + off, b + off, c + off) for a, b, c in fac]
        col = o.ViewObject.ShapeColor[:3] if o.ViewObject else (0.5, 0.5, 0.5)
        cols += [col] * len(fac)
        names += [o.Label] * len(fac)
    np.savez(path, P=np.array(pts_all), T=np.array(tris), C=np.array(cols), N=np.array(names))


BACKGROUND = np.array([0.957, 0.949, 0.933])


def render(mesh, view_dir, out, width=1400, height=1050, hide=(), up=(0, 0, 1), margin=0.06):
    import matplotlib.pyplot as plt

    P, T, C, N = mesh["P"], mesh["T"], mesh["C"], mesh["N"]
    keep = np.array([not any(str(n).startswith(h) for h in hide) for n in N])
    tri, col, names = P[T[keep]], C[keep], N[keep].astype(str)

    v = np.asarray(view_dir, float)
    v /= np.linalg.norm(v)
    right = np.cross(v, np.asarray(up, float))
    right /= np.linalg.norm(right)
    upv = np.cross(right, v)

    sx, sy, sz = tri @ right, tri @ upv, tri @ v
    lo = np.array([sx.min(), sy.min()])
    hi = np.array([sx.max(), sy.max()])
    scale = min(width, height) * (1 - 2 * margin) / max(hi - lo)
    cx = (sx - (lo[0] + hi[0]) / 2) * scale + width / 2
    cy = height / 2 - (sy - (lo[1] + hi[1]) / 2) * scale

    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    n[(n @ v) > 0] *= -1
    key = -v + 0.7 * upv - 0.5 * right
    key /= np.linalg.norm(key)
    shade = 0.35 + 0.55 * np.clip(n @ key, 0, 1) + 0.10 * np.clip(n @ upv, 0, 1)
    rgb = np.clip(col * shade[:, None], 0, 1)
    glow = np.char.startswith(names, "LED")
    rgb[glow] = col[glow]

    img = np.tile(BACKGROUND, (height, width, 1))
    zbuf = np.full((height, width), np.inf)
    for i in range(len(tri)):
        x, y, z = cx[i], cy[i], sz[i]
        x0, x1 = int(max(np.floor(x.min()), 0)), int(min(np.ceil(x.max()), width - 1))
        y0, y1 = int(max(np.floor(y.min()), 0)), int(min(np.ceil(y.max()), height - 1))
        if x0 > x1 or y0 > y1:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if abs(d) < 1e-9:
            continue
        w0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / d
        w1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / d
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue
        depth = w0 * z[0] + w1 * z[1] + w2 * z[2] - 0.02   # tiny bias so decals win ties
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        win = inside & (depth < sub)
        sub[win] = depth[win]
        img[y0:y1 + 1, x0:x1 + 1][win] = rgb[i]
    plt.imsave(out, img)


if __name__ == "__main__":
    mesh = np.load(sys.argv[1])
    out = sys.argv[2]
    render(mesh, (0.55, 1.0, -0.42), out + "radio-front-three-quarter.png")
    render(mesh, (0.0, 1.0, 0.0), out + "radio-front.png")
    render(mesh, (-0.6, -1.0, -0.45), out + "radio-rear-three-quarter.png")
    render(mesh, (-0.45, -0.8, -0.85), out + "radio-cutaway.png",
           hide=("Carcass_Top", "Rear_Panel", "Rear_Screws", "Button_", "Cable_Grommet", "Rear_Cleats"))
