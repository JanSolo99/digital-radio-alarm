"""Shared helpers and bought-component models for the alternative designs.

Components are built in a local frame and then placed, so the same speaker,
display and encoder can sit upright in one design and tilted or facing
down in another. Dimensions match V1 (cad/build_radio.py) and the
manufacturer data listed there.

Local frames
------------
driver:  origin on the mounting face, axis +Y points into the cabinet,
         sound leaves toward -Y.
display: origin at the centre of the active area on the panel's front
         face (the surface it's mounted into), viewer toward -Y.
encoder: origin on the front face at the shaft axis, viewer toward -Y.
"""

import math

import FreeCAD as App
import Part
from FreeCAD import Vector as V

# Dayton Audio PC83-4
FS, QTS, VAS_L = 80.1, 0.54, 1.98
DRIVER_FRAME_R, DRIVER_CUTOUT_R, DRIVER_DEPTH = 41.5, 38.5, 50.0
WADDING_FACTOR = 1.15

# Waveshare 1.54" e-Paper module
ACTIVE = 27.6
GLASS = (37.32, 31.8, 1.05)
GLASS_MARGIN_NEAR = 2.2
MODULE = (48.0, 33.0, 1.6)

# EC11 encoder
ENC_BODY = (12.0, 12.0, 6.5)
ENC_BUSHING, ENC_SHAFT = 7.0, 20.0

# Colours shared across designs
MATTE_BLACK = (0.08, 0.08, 0.08)
PRINT_BLACK = (0.13, 0.13, 0.14)
ALUMINIUM = (0.74, 0.75, 0.77)
BRASS = (0.80, 0.63, 0.30)
EPAPER = (0.86, 0.86, 0.82)
PCB_GREEN = (0.10, 0.40, 0.18)
PCB_BLUE = (0.12, 0.25, 0.55)
PCB_BLACK = (0.10, 0.10, 0.12)
FOAM = (0.30, 0.30, 0.32)
WARM_LED = (1.0, 0.78, 0.45)


def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def ycyl(r, y0, y1, x, z):
    return Part.makeCylinder(r, y1 - y0, V(x, y0, z), V(0, 1, 0))


def zcyl(r, z0, z1, x, y):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0), V(0, 0, 1))


def xcyl(r, x0, x1, y, z):
    return Part.makeCylinder(r, x1 - x0, V(x0, y, z), V(1, 0, 0))


def fuse_all(shapes):
    result = shapes[0]
    for s in shapes[1:]:
        result = result.fuse(s)
    return result.removeSplitter()


def placed(shape, placement):
    s = shape.copy()
    s.transformShape(placement.toMatrix())
    return s


def sealed_box_alignment(vb_litres):
    k = math.sqrt(1 + VAS_L / vb_litres)
    return QTS * k, FS * k


class Builder:
    """Creates a fresh document and adds coloured Part features to groups."""

    def __init__(self, name):
        if name in App.listDocuments():
            App.closeDocument(name)
        self.doc = App.newDocument(name)
        self.gui = App.GuiUp
        self.groups = {}

    def group(self, name):
        if name not in self.groups:
            self.groups[name] = self.doc.addObject("App::DocumentObjectGroup", name)
        return self.groups[name]

    def add(self, name, shape, color, grp, transparency=0, emissive=None):
        obj = self.doc.addObject("Part::Feature", name)
        obj.Label = name
        obj.Shape = shape
        self.group(grp).addObject(obj)
        if self.gui:
            vo = obj.ViewObject
            vo.ShapeColor = color
            vo.Transparency = transparency
            if emissive is not None:
                mat = vo.ShapeAppearance[0]
                mat.EmissiveColor = emissive
                mat.DiffuseColor = color
                vo.ShapeAppearance = (mat,)
        return obj

    def clashes(self, allow=()):
        parts = [o for o in self.doc.Objects if o.TypeId == "Part::Feature" and o.Shape.Volume > 0.05]
        found = []
        for i, a in enumerate(parts):
            for b in parts[i + 1:]:
                if (a.Label, b.Label) in allow or (b.Label, a.Label) in allow:
                    continue
                if a.Shape.BoundBox.intersect(b.Shape.BoundBox):
                    v = a.Shape.common(b.Shape).Volume
                    if v > 0.05:
                        found.append((a.Label, b.Label, round(v, 2)))
        invalid = [o.Label for o in parts if not o.Shape.isValid()]
        return found, invalid


# ── Components (local frames, see module docstring) ─────────────────────
def driver_local():
    gasket = ycyl(DRIVER_FRAME_R, 0, 1, 0, 0).cut(ycyl(DRIVER_CUTOUT_R, -1, 2, 0, 0))
    frame = ycyl(DRIVER_FRAME_R, 1, 4, 0, 0).cut(ycyl(35, 0, 5, 0, 0))
    basket = Part.makeCone(35, 27, 27, V(0, 4, 0), V(0, 1, 0)).cut(
        Part.makeCone(33.5, 25.5, 27.2, V(0, 3.9, 0), V(0, 1, 0)))
    magnet = ycyl(27, 31, 1 + DRIVER_DEPTH, 0, 0)
    cone = Part.makeCone(34.5, 12, 14, V(0, -0.5, 0), V(0, 1, 0)).cut(
        Part.makeCone(33.5, 11, 14.2, V(0, -1.3, 0), V(0, 1, 0)))
    dustcap = Part.makeSphere(9, V(0, 9, 0)).common(ycyl(10, -1, 9, 0, 0))
    return {"gasket": gasket, "body": fuse_all([frame, basket, magnet]), "cone": cone.fuse(dustcap)}


def display_local(panel_t, window_margin=0.4, bezel=None, recess=3.0):
    """E-ink glass, module and the cuts it needs in a panel of thickness panel_t.

    Returns shapes: glass, module, cut (to subtract from the panel), window
    (a centred square the size of the active area plus margin, for bezels).
    """
    gx0 = -ACTIVE / 2 - GLASS_MARGIN_NEAR
    gx1 = gx0 + GLASS[0]
    gz0, gz1 = -GLASS[1] / 2, GLASS[1] / 2
    g_y0 = recess
    g_y1 = g_y0 + GLASS[2]
    mcx = (gx0 + gx1) / 2
    mx0, mx1 = mcx - MODULE[0] / 2, mcx + MODULE[0] / 2
    mz0, mz1 = -MODULE[1] / 2, MODULE[1] / 2
    m_y0, m_y1 = g_y1, g_y1 + MODULE[2]
    cut = box(gx0 - 0.3, -1, gz0 - 0.3, gx1 + 0.3, m_y0 + 0.1, gz1 + 0.3).fuse(
        box(mx0 - 0.4, m_y0 - 0.1, mz0 - 0.4, mx1 + 0.4, max(panel_t, m_y1) + 1, mz1 + 0.4))
    w = ACTIVE / 2 + window_margin
    return {
        "glass": box(gx0, g_y0, gz0, gx1, g_y1, gz1),
        "module": box(mx0, m_y0, mz0, mx1, m_y1, mz1),
        "module_bounds": (mx0, mx1, mz0, mz1, m_y1),
        "cut": cut,
        "window": box(-w, -10, -w, w, 10, w),
    }


def encoder_local(panel_t, skin=4.0):
    """EC11 through a panel: counterbore from behind leaves `skin` for the bushing."""
    face = skin
    body = box(-ENC_BODY[0] / 2, face, -ENC_BODY[1] / 2, ENC_BODY[0] / 2, face + ENC_BODY[2], ENC_BODY[1] / 2)
    bushing = ycyl(3.5, face - ENC_BUSHING, face, 0, 0)
    shaft = ycyl(3.0, face - ENC_SHAFT, face - ENC_BUSHING, 0, 0).cut(box(1.5, -30, -4, 4, 10, 4))
    cut = ycyl(3.75, -1, panel_t + 1, 0, 0).fuse(box(-7, face, -7, 7, panel_t + 1, 7))
    nut = ycyl(5.0, -2.0, 0, 0, 0).cut(ycyl(3.5, -5, 5, 0, 0))
    return {"encoder": fuse_all([body, bushing, shaft]), "nut": nut, "cut": cut,
            "shaft_tip_y": face - ENC_SHAFT}


def knurled_knob(r, y_front, y_back, shaft_tip_y, grooves=40, skirt=True):
    """Knob in the local encoder frame (axis along Y), with D-bore and nut recess."""
    knob = ycyl(r, y_front, y_back - (1.5 if skirt else 0), 0, 0)
    if skirt:
        knob = knob.fuse(Part.makeCone(r, r + 1.5, 1.5, V(0, y_back - 1.5, 0), V(0, 1, 0)))
    cuts = []
    for i in range(grooves):
        g = box(-0.6, y_front + 1, r - 0.8, 0.6, y_back + 1, r + 2)
        g.rotate(V(0, 0, 0), V(0, 1, 0), 360.0 * i / grooves)
        cuts.append(g)
    knob = knob.cut(Part.makeCompound(cuts))
    knob = knob.cut(ycyl(6.5, y_back - 3.0, y_back + 1, 0, 0))
    knob = knob.cut(ycyl(3.1, shaft_tip_y - 0.3, y_back, 0, 0).cut(box(1.65, -30, -4, 4, 10, 4)))
    return knob.cut(ycyl(1.2, y_front - 1, y_front + 0.8, 0, r - 4))


def pi_zero(x0, y0, z0):
    """Pi Zero 2 W on a printed tray. Long axis along Y. Returns (tray, board, header)."""
    holes = [(x0 + 3.5, y0 + 3.5), (x0 + 26.5, y0 + 3.5), (x0 + 3.5, y0 + 61.5), (x0 + 26.5, y0 + 61.5)]
    tray = box(x0 - 3, y0 - 3, z0, x0 + 33, y0 + 68, z0 + 2)
    tray = fuse_all([tray] + [zcyl(2.6, z0 + 2, z0 + 6, x, y) for x, y in holes])
    for x, y in holes:
        tray = tray.cut(zcyl(1.1, z0 + 0.8, z0 + 7, x, y))
    board = box(x0, y0, z0 + 6, x0 + 30, y0 + 65, z0 + 7.6)
    header = box(x0 + 24.9, y0 + 7, z0 + 7.6, x0 + 29.9, y0 + 58, z0 + 16.1)
    return tray, board, header


def tactile_button(cap_r, top_z, deck_under_z, x, y, travel_gap=0.5, flange=1.5):
    """12mm tactile switch + printed cap pressing up through a horizontal deck."""
    cap_bottom = deck_under_z - travel_gap - flange
    sw_z0 = cap_bottom - 7.3
    sw = box(x - 6, y - 6, sw_z0, x + 6, y + 6, sw_z0 + 3.8).fuse(zcyl(1.75, sw_z0 + 3.8, cap_bottom, x, y))
    cap = zcyl(cap_r, cap_bottom, top_z, x, y).fuse(zcyl(cap_r + 2, cap_bottom, cap_bottom + flange, x, y))
    return sw, cap.removeSplitter(), sw_z0


def perforated(shape_plate, centre_xz, radius, pitch, hole_r, y0, y1):
    """Hex-pattern holes (along Y) inside a circle, cut from a plate."""
    holes = []
    cx, cz = centre_xz
    rows = int(radius / (pitch * 0.866)) + 1
    for row in range(-rows, rows + 1):
        dz = row * pitch * 0.866
        off = (pitch / 2) if row % 2 else 0.0
        cols = int(radius / pitch) + 1
        for col in range(-cols, cols + 1):
            dx = col * pitch + off
            if math.hypot(dx, dz) < radius:
                holes.append(ycyl(hole_r, y0, y1, cx + dx, cz + dz))
    return shape_plate.cut(Part.makeCompound(holes))
