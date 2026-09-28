"""Render review images of the alternative designs from their mesh dumps.

In FreeCAD, after building a design:
    exec(open("cad/render_views.py").read(), ns)
    ns["export_mesh"]("cad/alternatives/<name>_mesh.npz", doc_name="<Name>")
Then: python3 cad/alternatives/render_alternatives.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from render_views import render  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "docs", "img") + os.sep

VIEWS = {
    "sunrise": [
        ("front-three-quarter", (0.55, 1.0, -0.42), {}),
        ("front", (0.0, 1.0, 0.0), {}),
        ("rear-three-quarter", (-0.6, -1.0, -0.45), {}),
        ("cutaway", (-0.45, -0.8, -0.7),
         {"hide": ("Carcass_Arch", "Rear_Panel", "Rear_Gasket", "Button_Menu", "Button_Dismiss")}),
    ],
    "pebble": [
        ("front-three-quarter", (0.55, 1.0, -0.42), {}),
        ("front", (0.0, 1.0, 0.0), {}),
        ("underside", (0.35, 0.65, 0.68), {}),
        ("cutaway", (-0.45, -0.8, -0.7), {"hide": ("Shell", "Bottom_Grille", "Feet")}),
    ],
}

if __name__ == "__main__":
    for name, views in VIEWS.items():
        path = os.path.join(HERE, f"{name}_mesh.npz")
        if not os.path.exists(path):
            print(f"skip {name}: no mesh dump")
            continue
        mesh = np.load(path)
        for view, direction, kw in views:
            render(mesh, direction, f"{OUT}alt-{name}-{view}.png", **kw)
        print(f"rendered {name}")
