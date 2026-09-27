"""Builds the Digital Radio Alarm design model in FreeCAD.

Run inside FreeCAD (Macro > Execute, or runpy from the Python console).
Creates a fresh document "DigitalRadioAlarm" and saves it next to this file.

Axes: X = width (180), Y = depth (100, front face at Y=0, looking toward +Y),
Z = height (120). All dimensions in mm.

Interior layout
---------------
A 9mm divider splits the cabinet in two:
  * Left: a sealed speaker chamber holding only the driver and wadding.
    Nothing else pierces it, so its volume is known and its air seal is
    real - which is what makes the bass predictable.
  * Right: the electronics bay - display, encoder, buttons, Pi, amp, RTC.
    It can have every hole it needs (controls, cable, cooling vents)
    without affecting the sound.
The divider sits in 3mm grooves (dados) in the top and bottom boards. The
baffle and rear panel sit in rebates cut into the carcass after glue-up;
the rear panel seals against a foam gasket and screws into the rebate
shoulder and the divider's rear edge.

Driver: Dayton Audio PC83-4 (3", 4 ohm, Fs 80.1Hz, Qts 0.54, Vas 1.98L,
86.8dB @ 2.83V). 83mm frame, 77mm cutout, 50mm deep. Mounting screw
positions are deliberately not modelled - drill them from the real driver.
"""

import math
import os

import FreeCAD as App
import Part
from FreeCAD import Vector as V

# ── Key dimensions ──────────────────────────────────────────────────────
W, D, H = 180.0, 100.0, 120.0
WALL = 12.0

BAFFLE_Y0, BAFFLE_Y1 = 2.0, 11.0      # 9mm baffle, 2mm shadow-line recess
FRONT_REBATE = 4.0                    # baffle overlaps the carcass by 4mm each side
REAR_REBATE = 6.0
REAR_REBATE_Y = 90.0                  # rear rebate floor (gasket seat)
GASKET_T = 1.5
REAR_T = 6.0

DIV_X0, DIV_X1 = 105.0, 114.0         # 9mm divider
DADO = 3.0

DRIVER_C = (58.0, 60.0)               # x, z of the driver axis
DRIVER_FRAME_R = 41.5                 # PC83-4: 83mm OD
DRIVER_CUTOUT_R = 38.5                # 77mm cutout
DRIVER_DEPTH = 50.0
GRILLE_R = 44.0

DISPLAY_C = (140.0, 82.0)
ACTIVE = 27.6                         # 1.54" panel active area
BEZEL = 46.0
EINK_MODULE = (48.0, 33.0)            # module PCB, w x h - measure yours on arrival

KNOB_C = (140.0, 36.0)
KNOB_R = 16.0

BUTTON_X = 140.0                      # buttons line up with display and knob
BUTTONS = [("Snooze", 30.0, 10.0), ("Menu", 58.0, 6.0), ("Dismiss", 82.0, 6.0)]

# Driver parameters (manufacturer spec sheet)
FS, QTS, VAS_L = 80.1, 0.54, 1.98
WADDING_FACTOR = 1.15                 # light fill raises effective volume ~15%

WALNUT = (0.36, 0.22, 0.13)
DARK_WOOD = (0.22, 0.14, 0.09)
BIRCH_PLY = (0.80, 0.70, 0.52)
BRASS = (0.80, 0.63, 0.30)
MATTE_BLACK = (0.08, 0.08, 0.08)
PRINT_BLACK = (0.13, 0.13, 0.14)
ALUMINIUM = (0.74, 0.75, 0.77)
EPAPER = (0.86, 0.86, 0.82)
PCB_GREEN = (0.10, 0.40, 0.18)
PCB_BLUE = (0.12, 0.25, 0.55)
FOAM = (0.30, 0.30, 0.32)
WADDING = (0.95, 0.95, 0.93)
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


def xcyl(r, x0, x1, y, z):
    return Part.makeCylinder(r, x1 - x0, V(x0, y, z), V(1, 0, 0))


def fuse_all(shapes):
    result = shapes[0]
    for s in shapes[1:]:
        result = result.fuse(s)
    return result.removeSplitter()


def sealed_box_alignment(vb_litres):
    """Qtc and fc for a sealed box of the given effective volume."""
    k = math.sqrt(1 + VAS_L / vb_litres)
    return QTS * k, FS * k


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
    g_acoustic = group("Speaker_Chamber")
    g_bay = group("Electronics_Bay")

    # ── Carcass: four mitred boards, rebated front and rear, dadoed ────
    boards = {
        "Top": xz_prism([(0, H), (W, H), (W - WALL, H - WALL), (WALL, H - WALL)], 0, D),
        "Bottom": xz_prism([(0, 0), (W, 0), (W - WALL, WALL), (WALL, WALL)], 0, D),
        "Left": xz_prism([(0, 0), (WALL, WALL), (WALL, H - WALL), (0, H)], 0, D),
        "Right": xz_prism([(W, 0), (W - WALL, WALL), (W - WALL, H - WALL), (W, H)], 0, D),
    }
    fr, rr = FRONT_REBATE, REAR_REBATE
    front_rebate = box(WALL - fr, -1, WALL - fr, W - WALL + fr, BAFFLE_Y1, H - WALL + fr)
    rear_rebate = box(WALL - rr, REAR_REBATE_Y, WALL - rr, W - WALL + rr, D + 1, H - WALL + rr)
    top_dado = box(DIV_X0, BAFFLE_Y1, H - WALL - 0.01, DIV_X1, REAR_REBATE_Y, H - WALL + DADO)
    bottom_dado = box(DIV_X0, BAFFLE_Y1, WALL - DADO, DIV_X1, REAR_REBATE_Y, WALL + 0.01)
    for name, shape in boards.items():
        shape = shape.cut(front_rebate).cut(rear_rebate).cut(top_dado).cut(bottom_dado)
        if name == "Top":
            for _, by, br in BUTTONS:
                shape = shape.cut(zcyl(br + 0.5, H - WALL - 1, H + 1, BUTTON_X, by))
        add(f"Carcass_{name}", shape, WALNUT, g_cab)

    divider = box(DIV_X0, BAFFLE_Y1, WALL - DADO, DIV_X1, REAR_REBATE_Y, H - WALL + DADO)
    divider = divider.cut(xcyl(3.0, DIV_X0 - 1, DIV_X1 + 1, 70.0, 95.0))   # speaker wire pass-through
    add("Divider", divider, BIRCH_PLY, g_cab)

    # ── Front baffle, seated in the front rebate ────────────────────────
    baffle = box(WALL - fr, BAFFLE_Y0, WALL - fr, W - WALL + fr, BAFFLE_Y1, H - WALL + fr)
    baffle = baffle.cut(ycyl(DRIVER_CUTOUT_R, BAFFLE_Y0 - 1, BAFFLE_Y1 + 1, *DRIVER_C))
    ex, ez = DISPLAY_C
    panel_y = BAFFLE_Y0 + 3.0
    pcb_y0, pcb_y1 = panel_y + 1.2, panel_y + 2.8
    mw, mh = EINK_MODULE
    baffle = baffle.cut(box(ex - 16, BAFFLE_Y0 - 1, ez - 16, ex + 16, BAFFLE_Y1 + 1, ez + 16))
    baffle = baffle.cut(box(ex - mw / 2 - 0.5, pcb_y0 - 0.2, ez - mh / 2 - 0.5,
                            ex + mw / 2 + 0.5, BAFFLE_Y1 + 1, ez + mh / 2 + 0.5))   # module pocket
    # Encoder: 7mm hole, counterbored from behind so the short EC11 bushing reaches through
    baffle = baffle.cut(ycyl(3.6, BAFFLE_Y0 - 1, BAFFLE_Y1 + 1, *KNOB_C))
    baffle = baffle.cut(ycyl(12.0, BAFFLE_Y0 + 4, BAFFLE_Y1 + 1, *KNOB_C))
    # LED wire hole from under the hood into the electronics bay
    led_hole = ycyl(1.5, -13, BAFFLE_Y1 + 1, 160.0, 106.5)
    baffle = baffle.cut(led_hole)
    add("Front_Baffle", baffle, DARK_WOOD, g_front)

    # ── Brass grille ────────────────────────────────────────────────────
    grille = ycyl(GRILLE_R, BAFFLE_Y0 - 1.0, BAFFLE_Y0, *DRIVER_C)
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
                holes.append(ycyl(1.25, BAFFLE_Y0 - 2, BAFFLE_Y0 + 1, DRIVER_C[0] + dx, DRIVER_C[1] + dz))
    add("Speaker_Grille", grille.cut(Part.makeCompound(holes)), BRASS, g_front)

    # ── Speaker chamber: driver, gasket, wadding, wire pass-through ─────
    dx, dz = DRIVER_C
    y = BAFFLE_Y1
    gasket = ycyl(DRIVER_FRAME_R, y, y + 1, dx, dz).cut(ycyl(DRIVER_CUTOUT_R, y - 1, y + 2, dx, dz))
    add("Driver_Gasket", gasket, FOAM, g_acoustic)
    frame = ycyl(DRIVER_FRAME_R, y + 1, y + 4, dx, dz).cut(ycyl(35, y, y + 5, dx, dz))
    # Basket as a thin shell: a real basket is an open frame, and a solid
    # lump here would understate the chamber's air volume.
    basket = Part.makeCone(35, 27, 27, V(dx, y + 4, dz), V(0, 1, 0)).cut(
        Part.makeCone(33.5, 25.5, 27.2, V(dx, y + 3.9, dz), V(0, 1, 0)))
    magnet = ycyl(27, y + 31, y + 1 + DRIVER_DEPTH, dx, dz)
    add("Driver_PC83_4", fuse_all([frame, basket, magnet]), MATTE_BLACK, g_acoustic)
    cone = Part.makeCone(34.5, 12, 14, V(dx, y - 0.5, dz), V(0, 1, 0)).cut(
        Part.makeCone(33.5, 11, 14.2, V(dx, y - 1.3, dz), V(0, 1, 0)))
    dustcap = Part.makeSphere(9, V(dx, y + 9, dz)).common(ycyl(10, y - 1, y + 9, dx, dz))
    add("Driver_Cone", cone.fuse(dustcap), (0.20, 0.20, 0.21), g_acoustic)

    cx0, cx1 = WALL, DIV_X0
    wad = fuse_all([
        box(cx0, 64, WALL, cx0 + 10, REAR_REBATE_Y, H - WALL),
        box(cx0 + 10, 80, WALL, cx1, REAR_REBATE_Y, H - WALL),
        box(cx0 + 10, 64, H - WALL - 10, cx1, 80, H - WALL),
        box(cx0 + 10, 64, WALL, cx1, 80, WALL + 10),
    ])
    add("Acoustic_Wadding", wad, WADDING, g_acoustic, transparency=55)
    add("Speaker_Wire_Seal", xcyl(3.0, DIV_X0 - 1, DIV_X1 + 1, 70.0, 95.0), FOAM, g_acoustic)

    # ── Rear: gasket, panel, screws, grommet, bay vents ─────────────────
    ry0 = REAR_REBATE_Y + GASKET_T
    ry1 = ry0 + REAR_T
    outer = box(WALL - rr, REAR_REBATE_Y, WALL - rr, W - WALL + rr, ry0, H - WALL + rr)
    inner = box(WALL, REAR_REBATE_Y - 1, WALL, W - WALL, ry0 + 1, H - WALL)
    rear_gasket = outer.cut(inner).fuse(box(DIV_X0 + 1, REAR_REBATE_Y, WALL, DIV_X1 - 1, ry0, H - WALL))
    add("Rear_Gasket", rear_gasket.removeSplitter(), FOAM, g_cab)

    rear = box(WALL - rr, ry0, WALL - rr, W - WALL + rr, ry1, H - WALL + rr)
    grommet_xz = (155.0, 45.0)
    rear = rear.cut(ycyl(5.0, ry0 - 1, ry1 + 1, *grommet_xz))
    for i in range(6):
        vx = 124.0 + i * 7.0
        rear = rear.cut(box(vx, ry0 - 1, 62.0, vx + 3.0, ry1 + 1, 96.0))
    screw_pts = [(9, 9), (171, 9), (9, 111), (171, 111), (90, 9), (90, 111), ((DIV_X0 + DIV_X1) / 2, 60)]
    for sx, sz in screw_pts:
        rear = rear.cut(ycyl(1.6, ry0 - 1, ry1 + 1, sx, sz))
    add("Rear_Panel", rear, BIRCH_PLY, g_cab)
    add("Rear_Screws", fuse_all([ycyl(2.8, ry1, ry1 + 1.5, sx, sz) for sx, sz in screw_pts]), ALUMINIUM, g_cab)
    add("Cable_Grommet", ycyl(6.5, ry1, ry1 + 2, *grommet_xz).cut(ycyl(2.5, ry1 - 1, ry1 + 3, *grommet_xz)),
        MATTE_BLACK, g_cab)

    # ── Display: dial window, hood, panel, module in its pocket, clamp ──
    hb = BEZEL / 2
    by0 = BAFFLE_Y0
    bezel = box(ex - hb, by0 - 3, ez - hb, ex + hb, by0, ez + hb)
    bezel = bezel.cut(box(ex - 17, by0 - 4, ez - 17, ex + 17, by0 - 1.5, ez + 17))
    bezel = bezel.cut(box(ex - ACTIVE / 2, by0 - 4, ez - ACTIVE / 2, ex + ACTIVE / 2, by0 + 1, ez + ACTIVE / 2))
    hood_top = box(ex - hb, by0 - 16, ez + hb, ex + hb, by0, ez + hb + 3)
    hood_lip = box(ex - hb, by0 - 16, ez + hb - 3, ex + hb, by0 - 14, ez + hb)
    hood = bezel.fuse(hood_top).fuse(hood_lip).removeSplitter().cut(led_hole)
    add("Bezel_and_Hood", hood, PRINT_BLACK, g_front)
    add("LED_Strip", box(ex - 20, by0 - 12, ez + hb - 1, ex + 20, by0 - 8, ez + hb),
        WARM_LED, g_front, emissive=WARM_LED)

    add("EInk_Panel", box(ex - 15.5, panel_y, ez - 15.5, ex + 15.5, panel_y + 1.2, ez + 15.5), EPAPER, g_front)
    add("EInk_Module_PCB", box(ex - mw / 2, pcb_y0, ez - mh / 2, ex + mw / 2, pcb_y1, ez + mh / 2), PCB_GREEN, g_bay)
    clamp = box(ex - mw / 2 - 2, BAFFLE_Y1, ez - mh / 2 - 2, ex + mw / 2 + 2, BAFFLE_Y1 + 3, ez + mh / 2 + 2)
    clamp = clamp.cut(box(ex - 14, BAFFLE_Y1 - 1, ez - 9, ex + 14, BAFFLE_Y1 + 4, ez + 9))  # connector clearance
    add("Display_Clamp", clamp, PRINT_BLACK, g_bay)
    cs = [(ex - mw / 2 + 1, ez - mh / 2 + 1), (ex + mw / 2 - 1, ez - mh / 2 + 1),
          (ex - mw / 2 + 1, ez + mh / 2 - 1), (ex + mw / 2 - 1, ez + mh / 2 - 1)]
    add("Display_Clamp_Screws", fuse_all([ycyl(2.2, BAFFLE_Y1 + 3, BAFFLE_Y1 + 4.5, sx, sz) for sx, sz in cs]),
        ALUMINIUM, g_bay)

    font = next((f for f in FONT_CANDIDATES if os.path.exists(f)), None)
    if font:
        try:
            import Draft
            rot = App.Rotation(V(1, 0, 0), 90)

            def text(label, s, size, max_width, z):
                """Centred on the panel and shrunk to fit - it's only 27.6mm wide."""
                ss = Draft.make_shapestring(String=s, FontFile=font, Size=size)
                doc.recompute()
                if ss.Shape.BoundBox.XLength > max_width:
                    ss.Size = size * max_width / ss.Shape.BoundBox.XLength
                    doc.recompute()
                bb = ss.Shape.BoundBox
                ss.Placement = App.Placement(V(ex - bb.XMin - bb.XLength / 2, panel_y - 0.05, z), rot)
                g_front.addObject(ss)
                ss.Label = label
                if gui:
                    ss.ViewObject.ShapeColor = MATTE_BLACK
                return ss

            usable = ACTIVE - 3.0
            text("Face_Time", "06:45", 9.0, usable, ez - 1.5)
            text("Face_Date", "SAT 27", 3.4, usable * 0.6, ez - 8.5)
            add("Face_AlarmArmed", ycyl(0.9, panel_y - 0.1, panel_y, ex + 10.5, ez + 10.0), MATTE_BLACK, g_front)
        except Exception as e:
            App.Console.PrintWarning(f"Clock face text skipped: {e}\n")

    # ── Controls ────────────────────────────────────────────────────────
    kx, kz = KNOB_C
    knob = ycyl(KNOB_R, by0 - 16, by0 - 2, kx, kz)
    grooves = []
    for i in range(40):
        g = box(-0.6, by0 - 15, KNOB_R - 0.8, 0.6, by0 - 3, KNOB_R + 1)
        g.rotate(V(0, 0, 0), V(0, 1, 0), 360.0 * i / 40)
        g.translate(V(kx, 0, kz))
        grooves.append(g)
    knob = knob.cut(Part.makeCompound(grooves)).fuse(ycyl(KNOB_R + 1.5, by0 - 2, by0, kx, kz))
    add("Encoder_Knob", knob, ALUMINIUM, g_ctrl)
    add("Knob_Indicator", ycyl(1.2, by0 - 16.3, by0 - 15.9, kx, kz + KNOB_R - 4), BRASS, g_ctrl)
    add("Encoder_EC11", box(kx - 6.25, by0 + 4, kz - 6.75, kx + 6.25, by0 + 11, kz + 6.75), (0.3, 0.3, 0.3), g_bay)

    # Buttons: cap with a retaining flange, pressing a tactile switch on a
    # printed plate screwed up under the top deck.
    top_in = H - WALL
    plate_z1 = top_in - 5.5
    plate = box(BUTTON_X - 15, 18, plate_z1 - 3, BUTTON_X + 15, 88, plate_z1)
    bosses = [zcyl(3, plate_z1, top_in, BUTTON_X - 11, 46), zcyl(3, plate_z1, top_in, BUTTON_X + 11, 70)]
    add("Button_Plate", fuse_all([plate] + bosses), PRINT_BLACK, g_bay)
    for name, by, br in BUTTONS:
        add(f"Switch_{name}", box(BUTTON_X - 6, by - 6, plate_z1, BUTTON_X + 6, by + 6, plate_z1 + 3.5),
            (0.25, 0.25, 0.25), g_bay)
        cap = zcyl(br, plate_z1 + 3.5, H + 4, BUTTON_X, by).fuse(zcyl(br + 2, plate_z1 + 3.5, plate_z1 + 5, BUTTON_X, by))
        if name == "Snooze":
            cap = cap.fuse(zcyl(br - 2, H + 4, H + 5, BUTTON_X, by))
        add(f"Button_{name}", cap.removeSplitter(), BRASS if name == "Snooze" else MATTE_BLACK, g_ctrl)

    # ── Electronics bay ─────────────────────────────────────────────────
    floor = WALL
    pi = (122.0, 20.0)                       # Pi Zero 2 W, long axis front-to-back, SD card toward the rear
    holes_pi = [(pi[0] + 3.5, pi[1] + 3.5), (pi[0] + 26.5, pi[1] + 3.5),
                (pi[0] + 3.5, pi[1] + 61.5), (pi[0] + 26.5, pi[1] + 61.5)]
    add("Pi_Tray", box(pi[0] - 3, pi[1] - 3, floor, pi[0] + 33, pi[1] + 68, floor + 2), PRINT_BLACK, g_bay)
    add("Pi_Standoffs", fuse_all([zcyl(1.5, floor + 2, floor + 6, x, yy) for x, yy in holes_pi]),
        (0.9, 0.9, 0.85), g_bay)
    add("Pi_Zero_2W", box(pi[0], pi[1], floor + 6, pi[0] + 30, pi[1] + 65, floor + 7.6), PCB_GREEN, g_bay)

    wall_x = DIV_X1 + 5.0                    # boards stand off the divider's bay face
    add("Divider_Standoffs", fuse_all([xcyl(1.5, DIV_X1, wall_x, yy, zz)
                                       for yy, zz in [(24, 62), (39, 77), (52, 28), (86, 46)]]),
        (0.9, 0.9, 0.85), g_bay)
    add("MAX98357A_Amp", box(wall_x, 22, 60, wall_x + 1.6, 41, 79.3), PCB_BLUE, g_bay)
    add("DS3231_RTC", box(wall_x, 50, 26, wall_x + 1.6, 88, 48), PCB_BLUE, g_bay)
    add("RTC_Coin_Cell", xcyl(10, wall_x + 1.6, wall_x + 4.8, 75.0, 37.0), ALUMINIUM, g_bay)

    feet = [zcyl(7, -2, 0, x, yy) for x, yy in [(20, 15), (160, 15), (20, 85), (160, 85)]]
    add("Felt_Feet", fuse_all(feet), (0.25, 0.25, 0.25), g_cab)

    doc.recompute()

    # ── Acoustic check: sealed chamber volume and alignment ─────────────
    chamber = box(WALL, BAFFLE_Y1, WALL, DIV_X0, REAR_REBATE_Y, H - WALL)
    # Wadding isn't subtracted: its effect is the WADDING_FACTOR below.
    for label in ("Driver_PC83_4", "Driver_Cone", "Driver_Gasket"):
        chamber = chamber.cut(doc.getObjectsByLabel(label)[0].Shape)
    net_l = chamber.Volume / 1e6
    qtc, fc = sealed_box_alignment(net_l * WADDING_FACTOR)
    App.Console.PrintMessage(
        f"Speaker chamber: {net_l:.3f} L net ({net_l * WADDING_FACTOR:.3f} L effective with wadding) "
        f"-> Qtc {qtc:.2f}, fc {fc:.0f} Hz\n")
    doc.Comment = f"Sealed chamber {net_l:.3f}L net, Qtc {qtc:.2f}, fc {fc:.0f}Hz (PC83-4)"

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
