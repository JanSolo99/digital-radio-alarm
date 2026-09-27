"""Builds the Digital Radio Alarm design model in FreeCAD.

Run inside FreeCAD (Macro > Execute, or exec() from the Python console).
Creates a fresh document "DigitalRadioAlarm" and saves it next to this file.

Axes: X = width (180), Y = depth (100, front face at Y=0, looking toward +Y),
Z = height (120). All dimensions in mm. Matches the spec on the project site:
180w x 120h x 100d mitred 12mm hardwood carcass, 3" ported driver, 1.54"
square e-ink in a recessed dial-window bezel with a top-down light hood,
encoder on the front, three buttons on the top deck.
"""

import math
import os

import FreeCAD as App
import Part
from FreeCAD import Vector as V

# ── Key dimensions ──────────────────────────────────────────────────────
W, D, H = 180.0, 100.0, 120.0
WALL = 12.0
BAFFLE_T = 9.0
BAFFLE_RECESS = 2.0          # shadow line: baffle sits 2mm behind the carcass edge
REAR_T = 6.0
REAR_RECESS = 2.0

DRIVER_C = (58.0, 60.0)      # x, z of the driver axis
DRIVER_CUTOUT_R = 34.0       # ~68mm hole-saw cutout
DRIVER_FRAME_R = 40.0        # ~80mm frame
GRILLE_R = 44.0              # 88mm brass grille

DISPLAY_C = (140.0, 82.0)
ACTIVE = 27.6                # 1.54" panel active area
BEZEL = 46.0

KNOB_C = (140.0, 36.0)
KNOB_R = 16.0

PORT_C = (45.0, 40.0)        # rear-panel bass port

WALNUT = (0.36, 0.22, 0.13)
DARK_WOOD = (0.22, 0.14, 0.09)
BRASS = (0.80, 0.63, 0.30)
MATTE_BLACK = (0.08, 0.08, 0.08)
ALUMINIUM = (0.74, 0.75, 0.77)
EPAPER = (0.86, 0.86, 0.82)
PCB_GREEN = (0.10, 0.40, 0.18)
PCB_BLUE = (0.12, 0.25, 0.55)
PLY = (0.78, 0.66, 0.48)
WARM_LED = (1.0, 0.78, 0.45)

FONT_CANDIDATES = [
    "/usr/share/fonts/TTF/DejaVuSansCondensed-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
]

DOC_NAME = "DigitalRadioAlarm"


# ── Helpers ─────────────────────────────────────────────────────────────
def xz_prism(pts, y0, depth):
    """Polygon in the XZ plane at y=y0, extruded along +Y."""
    wire = Part.makePolygon([V(x, y0, z) for x, z in pts] + [V(pts[0][0], y0, pts[0][1])])
    return Part.Face(wire).extrude(V(0, depth, 0))


def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def ycyl(r, y0, y1, x, z):
    return Part.makeCylinder(r, y1 - y0, V(x, y0, z), V(0, 1, 0))


def zcyl(r, z0, z1, x, y):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0), V(0, 0, 1))


def fuse_all(shapes):
    result = shapes[0]
    for s in shapes[1:]:
        result = result.fuse(s)
    return result.removeSplitter()


def main():
    if DOC_NAME in App.listDocuments():
        App.closeDocument(DOC_NAME)
    doc = App.newDocument(DOC_NAME)
    gui = App.GuiUp

    def group(name):
        return doc.addObject("App::DocumentObjectGroup", name)

    def add(name, shape, color, grp, transparency=0, emissive=None):
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = shape
        grp.addObject(obj)
        if gui:
            vo = obj.ViewObject
            vo.ShapeColor = color
            vo.Transparency = transparency
            if emissive is not None:
                mat = vo.ShapeAppearance[0]
                mat.EmissiveColor = emissive
                mat.DiffuseColor = color
                vo.ShapeAppearance = (mat,)
        return obj

    g_cab = group("Cabinet")
    g_front = group("Front")
    g_ctrl = group("Controls")
    g_int = group("Internals")

    # ── Carcass: four mitred 12mm boards ───────────────────────────────
    top = xz_prism([(0, H), (W, H), (W - WALL, H - WALL), (WALL, H - WALL)], 0, D)
    bottom = xz_prism([(0, 0), (W, 0), (W - WALL, WALL), (WALL, WALL)], 0, D)
    left = xz_prism([(0, 0), (WALL, WALL), (WALL, H - WALL), (0, H)], 0, D)
    right = xz_prism([(W, 0), (W - WALL, WALL), (W - WALL, H - WALL), (W, H)], 0, D)

    # Button holes through the top deck (menu, snooze, dismiss)
    buttons = [("Menu", 45.0, 6.0, MATTE_BLACK), ("Snooze", 90.0, 10.0, BRASS), ("Dismiss", 135.0, 6.0, MATTE_BLACK)]
    for _, bx, br, _ in buttons:
        top = top.cut(zcyl(br + 0.5, H - WALL - 1, H + 1, bx, 50.0))

    add("Carcass_Top", top, WALNUT, g_cab)
    add("Carcass_Bottom", bottom, WALNUT, g_cab)
    add("Carcass_Left", left, WALNUT, g_cab)
    add("Carcass_Right", right, WALNUT, g_cab)

    # Corner cleats the rear panel screws into
    cleats = []
    for cx, cz in [(WALL, WALL), (W - WALL - 10, WALL), (WALL, H - WALL - 10), (W - WALL - 10, H - WALL - 10)]:
        cleats.append(box(cx, 60, cz, cx + 10, D - REAR_RECESS - REAR_T, cz + 10))
    add("Rear_Cleats", fuse_all(cleats), DARK_WOOD, g_cab)

    # ── Front baffle ────────────────────────────────────────────────────
    by0 = BAFFLE_RECESS
    by1 = BAFFLE_RECESS + BAFFLE_T
    baffle = box(WALL, by0, WALL, W - WALL, by1, H - WALL)
    baffle = baffle.cut(ycyl(DRIVER_CUTOUT_R, by0 - 1, by1 + 1, *DRIVER_C))
    baffle = baffle.cut(box(DISPLAY_C[0] - 16.5, by0 - 1, DISPLAY_C[1] - 16.5,
                            DISPLAY_C[0] + 16.5, by1 + 1, DISPLAY_C[1] + 16.5))
    # Encoder: 7mm shaft hole, plus a counterbore from behind so the short
    # EC11 bushing reaches through (the thickness issue in the build plan).
    baffle = baffle.cut(ycyl(3.6, by0 - 1, by1 + 1, *KNOB_C))
    baffle = baffle.cut(ycyl(12.0, by0 + 4, by1 + 1, *KNOB_C))
    add("Front_Baffle", baffle, DARK_WOOD, g_front)

    # ── Brass speaker grille ────────────────────────────────────────────
    grille = ycyl(GRILLE_R, by0 - 1.0, by0, *DRIVER_C)
    holes = []
    pitch = 4.5
    rows = int(GRILLE_R / (pitch * 0.866)) + 1
    for row in range(-rows, rows + 1):
        dz = row * pitch * 0.866
        offset = (pitch / 2) if row % 2 else 0.0
        cols = int(GRILLE_R / pitch) + 1
        for col in range(-cols, cols + 1):
            dx = col * pitch + offset
            if math.hypot(dx, dz) < GRILLE_R - 5:
                holes.append(ycyl(1.25, by0 - 2, by0 + 1, DRIVER_C[0] + dx, DRIVER_C[1] + dz))
    grille = grille.cut(Part.makeCompound(holes))
    add("Speaker_Grille", grille, BRASS, g_front)

    # ── 3" driver behind the baffle ─────────────────────────────────────
    dx, dz = DRIVER_C
    flange = ycyl(DRIVER_FRAME_R, by1, by1 + 3, dx, dz).cut(ycyl(DRIVER_CUTOUT_R - 2, by1 - 1, by1 + 4, dx, dz))
    cone = Part.makeCone(DRIVER_CUTOUT_R - 2, 12, 20, V(dx, by1 + 1, dz), V(0, 1, 0))
    dustcap = Part.makeSphere(9, V(dx, by1 + 14, dz)).common(ycyl(10, by1, by1 + 14, dx, dz))
    magnet = ycyl(22.5, by1 + 22, by1 + 37, dx, dz)
    add("Driver_Frame", flange.fuse(magnet), MATTE_BLACK, g_int)
    add("Driver_Cone", cone.fuse(dustcap), (0.18, 0.17, 0.16), g_int)

    # ── Display: recessed dial window + top-down light hood ─────────────
    ex, ez = DISPLAY_C
    hb = BEZEL / 2
    bezel = box(ex - hb, by0 - 3, ez - hb, ex + hb, by0, ez + hb)
    bezel = bezel.cut(box(ex - 17, by0 - 4, ez - 17, ex + 17, by0 - 1.5, ez + 17))   # counterbored surround
    bezel = bezel.cut(box(ex - ACTIVE / 2, by0 - 4, ez - ACTIVE / 2, ex + ACTIVE / 2, by0 + 1, ez + ACTIVE / 2))
    hood_top = box(ex - hb, by0 - 16, ez + hb, ex + hb, by0, ez + hb + 3)
    hood_lip = box(ex - hb, by0 - 16, ez + hb - 3, ex + hb, by0 - 14, ez + hb)
    add("Bezel_and_Hood", bezel.fuse(hood_top).fuse(hood_lip).removeSplitter(), MATTE_BLACK, g_front)
    add("LED_Strip", box(ex - 20, by0 - 12, ez + hb - 1, ex + 20, by0 - 8, ez + hb),
        WARM_LED, g_front, emissive=WARM_LED)

    panel_y = by0 + 3.0     # e-paper sits ~6mm behind the bezel face: reads as a window
    add("EInk_Panel", box(ex - 15.5, panel_y, ez - 15.5, ex + 15.5, panel_y + 1.2, ez + 15.5), EPAPER, g_front)
    add("EInk_Module_PCB", box(ex - 24, by1, ez - 16.5, ex + 24, by1 + 1.6, ez + 16.5), PCB_GREEN, g_int)

    font = next((f for f in FONT_CANDIDATES if os.path.exists(f)), None)
    if font:
        try:
            import Draft
            rot = App.Rotation(V(1, 0, 0), 90)   # text normal +Z -> -Y (faces the viewer)

            def text(label, s, size, max_width, z):
                """Place text centred on the panel, shrunk to fit max_width —
                the panel is only 27.6mm wide, so the layout has to earn its space."""
                ss = Draft.make_shapestring(String=s, FontFile=font, Size=size)
                doc.recompute()
                width = ss.Shape.BoundBox.XLength
                if width > max_width:
                    ss.Size = size * max_width / width
                    doc.recompute()
                bb = ss.Shape.BoundBox
                ss.Placement = App.Placement(V(ex - bb.XMin - bb.XLength / 2, panel_y - 0.05, z), rot)
                g_front.addObject(ss)
                ss.Label = label
                if gui:
                    ss.ViewObject.ShapeColor = MATTE_BLACK
                return ss

            usable = ACTIVE - 3.0      # ~1.5mm margin each side
            text("Face_Time", "06:45", 9.0, usable, ez - 1.5)
            text("Face_Date", "SAT 27", 3.4, usable * 0.6, ez - 8.5)
            dot = ycyl(0.9, panel_y - 0.1, panel_y, ex + 10.5, ez + 10.0)
            add("Face_AlarmArmed", dot, MATTE_BLACK, g_front)
        except Exception as e:  # text is decorative; never fail the build on it
            App.Console.PrintWarning(f"Clock face text skipped: {e}\n")

    # ── Controls ────────────────────────────────────────────────────────
    kx, kz = KNOB_C
    knob = ycyl(KNOB_R, by0 - 16, by0 - 2, kx, kz)
    grooves = []
    for i in range(40):
        a = 2 * math.pi * i / 40
        g = box(-0.6, by0 - 15, KNOB_R - 0.8, 0.6, by0 - 3, KNOB_R + 1)
        g.rotate(V(0, 0, 0), V(0, 1, 0), math.degrees(a))
        g.translate(V(kx, 0, kz))
        grooves.append(g)
    knob = knob.cut(Part.makeCompound(grooves))
    skirt = ycyl(KNOB_R + 1.5, by0 - 2, by0, kx, kz)
    add("Encoder_Knob", knob.fuse(skirt), ALUMINIUM, g_ctrl)
    add("Knob_Indicator", ycyl(1.2, by0 - 16.3, by0 - 15.9, kx, kz + KNOB_R - 4), BRASS, g_ctrl)
    add("Encoder_EC11", box(kx - 6.25, by0 + 4, kz - 6.75, kx + 6.25, by0 + 11, kz + 6.75), (0.3, 0.3, 0.3), g_int)

    for name, bx, br, color in buttons:
        cap = zcyl(br, H - 1, H + 4, bx, 50.0)
        if name == "Snooze":
            cap = cap.fuse(zcyl(br - 2, H + 4, H + 5, bx, 50.0))
        add(f"Button_{name}", cap, color, g_ctrl)

    # ── Rear panel, port, grommet ───────────────────────────────────────
    ry0 = D - REAR_RECESS - REAR_T
    ry1 = D - REAR_RECESS
    rear = box(WALL, ry0, WALL, W - WALL, ry1, H - WALL)
    rear = rear.cut(ycyl(17.0, ry0 - 1, ry1 + 1, *PORT_C))
    rear = rear.cut(ycyl(5.0, ry0 - 1, ry1 + 1, 150.0, 22.0))
    screw_pts = [(WALL + 5, WALL + 5), (W - WALL - 5, WALL + 5), (WALL + 5, H - WALL - 5), (W - WALL - 5, H - WALL - 5)]
    add("Rear_Panel", rear, PLY, g_cab)
    add("Rear_Screws", fuse_all([ycyl(2.8, ry1, ry1 + 1.5, sx, sz) for sx, sz in screw_pts]), ALUMINIUM, g_cab)

    port = ycyl(17.0, by1 + 45, ry1, *PORT_C).cut(ycyl(15.0, by1 + 44, ry1 + 1, *PORT_C))
    port = port.fuse(ycyl(20.0, ry1, ry1 + 1.5, *PORT_C).cut(ycyl(15.0, ry1 - 1, ry1 + 3, *PORT_C)))
    add("Bass_Port", port, MATTE_BLACK, g_int)
    add("Cable_Grommet", ycyl(6.5, ry1, ry1 + 2, 150.0, 22.0).cut(ycyl(2.5, ry1 - 1, ry1 + 3, 150.0, 22.0)),
        MATTE_BLACK, g_cab)

    # ── Electronics on the floor ────────────────────────────────────────
    floor = WALL
    standoffs = [zcyl(1.5, floor, floor + 5, x, y) for x, y in [(93.5, 39.5), (151.5, 39.5), (93.5, 62.5), (151.5, 62.5)]]
    add("Pi_Standoffs", fuse_all(standoffs), (0.9, 0.9, 0.85), g_int)
    add("Pi_Zero_2W", box(90, 36, floor + 5, 155, 66, floor + 6.6), PCB_GREEN, g_int)
    add("MAX98357A_Amp", box(95, 70, floor + 5, 113, 89, floor + 6.6), PCB_BLUE, g_int)
    add("DS3231_RTC", box(118, 69, floor + 5, 156, 91, floor + 6.6), PCB_BLUE, g_int)
    add("RTC_Coin_Cell", zcyl(10, floor + 6.6, floor + 9.8, 146.0, 80.0), ALUMINIUM, g_int)

    # ── Felt feet ───────────────────────────────────────────────────────
    feet = [zcyl(7, -2, 0, x, y) for x, y in [(20, 15), (160, 15), (20, 85), (160, 85)]]
    add("Felt_Feet", fuse_all(feet), (0.25, 0.25, 0.25), g_cab)

    doc.recompute()

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DigitalRadioAlarm.FCStd")
    doc.saveAs(out)

    if gui:
        import FreeCADGui as Gui
        App.setActiveDocument(doc.Name)
        view = Gui.getDocument(doc.Name).ActiveView
        view.viewIsometric()
        view.fitAll()
    return doc


if __name__ in ("__main__", "build_radio"):
    main()
