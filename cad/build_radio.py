"""Digital Radio Alarm - V1 design model for FreeCAD.

Run inside FreeCAD (Macro > Execute, or runpy from the Python console).
Creates the document "DigitalRadioAlarm", saves it next to this file, and
exports every printable part as a print-oriented STL into cad/stl/.

Axes: X = width (180), Y = depth (100, front face at Y=0, looking toward +Y),
Z = height (120). All dimensions in mm.

Layout
------
A 9mm divider splits the cabinet:
  * Left: a sealed speaker chamber holding only the driver and wadding.
  * Right: the electronics bay - display, encoder, buttons, Pi, amp, RTC,
    LED dimmer and the USB-C power inlet. It can have every hole it needs.
The divider sits in 3mm through-dados in the top and bottom boards (cut
before glue-up; the rebates hide their ends). Baffle and rear panel sit in
rebates; the rear panel seals against a foam gasket.

Printing
--------
Every non-bought part exports as an STL, rotated so its best face is on
the bed. The wooden parts (carcass, baffle, divider, rear panel) export
too, so a complete test model can be printed at full size before any
timber is cut. Target printer: Elegoo Centauri Carbon (256mm cube, 0.4mm
nozzle, PLA). The largest part is 180 x 100mm, so anything 220mm-class works too.
Clearances for printed fits are set by FIT.

Bought parts, dimensions from manufacturer data:
  Dayton Audio PC83-4       83mm frame, 77mm cutout, 50mm deep
  Waveshare 1.54" e-Paper   48 x 33mm module, 37.32 x 31.8 x 1.05mm glass,
                            27.6mm square active area
  Raspberry Pi Zero 2 W     65 x 30mm, M2.5 holes on 58 x 23mm
  Adafruit MAX98357A        19.4 x 17.8mm
  DS3231 (ZS-042)           38 x 22mm, CR2032 holder on the back (14mm total)
  EC11 encoder              12mm body, M7x0.75 bushing 7mm, 6mm D-shaft 20mm
  12mm tactile switch       12 x 12 x 3.8mm body, 7.3mm to top of actuator
Measure anything marked MEASURE against the part you actually receive.
"""

import math
import os

import FreeCAD as App
import Part
from FreeCAD import Vector as V

# ── Cabinet ─────────────────────────────────────────────────────────────
W, D, H = 180.0, 100.0, 120.0
WALL = 12.0
FIT = 0.2                              # per-side clearance for printed/fitted panels

BAFFLE_Y0, BAFFLE_Y1 = 2.0, 11.0       # 9mm baffle, 2mm shadow-line recess
FRONT_REBATE = 4.0
REAR_REBATE = 6.0
REAR_REBATE_Y = 90.0
GASKET_T = 1.5
REAR_T = 6.0

DIV_X0, DIV_X1 = 105.0, 114.0          # 9mm divider
DADO_DEPTH = 3.0

# ── Driver: Dayton Audio PC83-4 ─────────────────────────────────────────
DRIVER_C = (58.0, 60.0)
DRIVER_FRAME_R = 41.5
DRIVER_CUTOUT_R = 38.5
DRIVER_DEPTH = 50.0
FS, QTS, VAS_L = 80.1, 0.54, 1.98
WADDING_FACTOR = 1.15
GRILLE_R = 44.0

# ── Display: Waveshare 1.54" e-Paper module ─────────────────────────────
ACTIVE = 27.6
GLASS = (37.32, 31.8, 1.05)            # x, z, thickness (landscape on the module)
GLASS_MARGIN_NEAR = 2.2                # MEASURE: active-area margin on the -x edge;
                                       # the wider margin (FPC bond) is on +x
MODULE = (48.0, 33.0, 1.6)
BEZEL = 46.0
# The module is 48mm wide in a 54mm bay, so it is centred in the bay, and
# the display, knob and buttons all line up on the resulting active-area centre.
BAY_CENTRE_X = (114.0 + 168.0) / 2
COLUMN_X = BAY_CENTRE_X - GLASS[0] / 2 + GLASS_MARGIN_NEAR + ACTIVE / 2
DISPLAY_C = (COLUMN_X, 82.0)           # centre of the ACTIVE area

# ── Controls ────────────────────────────────────────────────────────────
KNOB_C = (COLUMN_X, 36.0)
KNOB_R = 16.0
ENC_BODY = (12.0, 12.0, 6.5)           # x, z, depth
ENC_BUSHING = 7.0
ENC_SHAFT = 20.0                       # from mounting face
NUT_T = 2.0

BUTTON_X = COLUMN_X
BUTTONS = [("Snooze", 30.0, 10.0), ("Menu", 58.0, 6.0), ("Dismiss", 82.0, 6.0)]
SWITCH_BODY_H = 3.8
SWITCH_TOTAL_H = 7.3

BED = (256.0, 256.0)                   # Elegoo Centauri Carbon at the Canberra maker space

# ── Colours ─────────────────────────────────────────────────────────────
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
PCB_BLACK = (0.10, 0.10, 0.12)
FOAM = (0.30, 0.30, 0.32)
WADDING = (0.95, 0.95, 0.93)
WARM_LED = (1.0, 0.78, 0.45)

FONT_CANDIDATES = [
    "/usr/share/fonts/TTF/DejaVuSansCondensed-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
]

DOC_NAME = "DigitalRadioAlarm"

# Printable parts: label -> (world direction that faces the bed, role, note)
PRINTS = {
    "Carcass_Top": ((0, 0, 1), "stand-in", "outer face down; mitres print as chamfers"),
    "Carcass_Bottom": ((0, 0, -1), "stand-in", "outer face down"),
    "Carcass_Left": ((-1, 0, 0), "stand-in", "outer face down"),
    "Carcass_Right": ((1, 0, 0), "stand-in", "outer face down"),
    "Front_Baffle": ((0, -1, 0), "stand-in", "front face down; pocket and counterbore face up"),
    "Divider": ((-1, 0, 0), "stand-in", "flat"),
    "Rear_Panel": ((0, -1, 0), "stand-in", "inner face down, so the screw counterbores face up"),
    "Speaker_Grille": ((0, -1, 0), "stand-in", "flat; the real one is brass mesh"),
    "Bezel_and_Hood": ((0, 1, 0), "final", "back face down; hood prints as a wall, lip is chamfered"),
    "Encoder_Knob": ((0, -1, 0), "final", "front face down; bore and nut recess face up"),
    "Button_Snooze": ((0, 0, -1), "final", "flange down"),
    "Button_Menu": ((0, 0, -1), "final", "flange down"),
    "Button_Dismiss": ((0, 0, -1), "final", "flange down"),
    "Button_Plate": ((0, 0, -1), "final", "bosses up"),
    "Pi_Tray": ((0, 0, -1), "final", "standoffs up"),
    "Display_Clamp": ((0, 1, 0), "final", "flat"),
    "USBC_Saddle": ((0, 0, -1), "final", "flat"),
}


# ── Helpers ─────────────────────────────────────────────────────────────
def xz_prism(pts, y0, depth):
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
    k = math.sqrt(1 + VAS_L / vb_litres)
    return QTS * k, FS * k


def bed_fit(dx, dy):
    """How a footprint fits the design-rule bed, with a 5mm margin."""
    bx, by = BED[0] - 5, BED[1] - 5
    a, b = sorted((dx, dy), reverse=True)
    if a <= bx and b <= by:
        return "flat"
    if (a + b) / math.sqrt(2) <= min(bx, by):
        return "diagonal"
    return "TOO BIG"


def main():
    if DOC_NAME in App.listDocuments():
        App.closeDocument(DOC_NAME)
    doc = App.newDocument(DOC_NAME)
    gui = App.GuiUp

    def group(name):
        return doc.addObject("App::DocumentObjectGroup", name)

    def add(name, shape, color, grp, transparency=0, emissive=None):
        obj = doc.addObject("Part::Feature", name)
        obj.Label = name
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

    fr, rr = FRONT_REBATE, REAR_REBATE
    top_in, floor = H - WALL, WALL

    # ── Carcass: four mitred boards, rebated, through-dadoed ────────────
    boards = {
        "Top": xz_prism([(0, H), (W, H), (W - WALL, H - WALL), (WALL, H - WALL)], 0, D),
        "Bottom": xz_prism([(0, 0), (W, 0), (W - WALL, WALL), (WALL, WALL)], 0, D),
        "Left": xz_prism([(0, 0), (WALL, WALL), (WALL, H - WALL), (0, H)], 0, D),
        "Right": xz_prism([(W, 0), (W - WALL, WALL), (W - WALL, H - WALL), (W, H)], 0, D),
    }
    front_rebate = box(WALL - fr, -1, WALL - fr, W - WALL + fr, BAFFLE_Y1, H - WALL + fr)
    rear_rebate = box(WALL - rr, REAR_REBATE_Y, WALL - rr, W - WALL + rr, D + 1, H - WALL + rr)
    dx0, dx1 = DIV_X0 - FIT, DIV_X1 + FIT
    top_dado = box(dx0, -1, top_in - 0.01, dx1, D + 1, top_in + DADO_DEPTH)
    bottom_dado = box(dx0, -1, floor - DADO_DEPTH, dx1, D + 1, floor + 0.01)
    for name, shape in boards.items():
        shape = shape.cut(front_rebate).cut(rear_rebate).cut(top_dado).cut(bottom_dado)
        if name == "Top":
            for _, by, br in BUTTONS:
                shape = shape.cut(zcyl(br + 0.5, top_in - 1, H + 1, BUTTON_X, by))
        add(f"Carcass_{name}", shape, WALNUT, g_cab)

    divider = box(DIV_X0, BAFFLE_Y1, floor - DADO_DEPTH + FIT, DIV_X1, REAR_REBATE_Y, top_in + DADO_DEPTH - FIT)
    divider = divider.cut(xcyl(4.0, DIV_X0 - 1, DIV_X1 + 1, 50.0, 95.0))   # grommet for speaker wire
    add("Divider", divider, BIRCH_PLY, g_cab)

    # ── Front baffle ────────────────────────────────────────────────────
    by0 = BAFFLE_Y0
    baffle = box(WALL - fr + FIT, BAFFLE_Y0, WALL - fr + FIT, W - WALL + fr - FIT, BAFFLE_Y1, H - WALL + fr - FIT)
    baffle = baffle.cut(ycyl(DRIVER_CUTOUT_R, BAFFLE_Y0 - 1, BAFFLE_Y1 + 1, *DRIVER_C))

    ex, ez = DISPLAY_C
    gx0 = ex - ACTIVE / 2 - GLASS_MARGIN_NEAR          # glass extents
    gx1 = gx0 + GLASS[0]
    gz0, gz1 = ez - GLASS[1] / 2, ez + GLASS[1] / 2
    glass_y0 = BAFFLE_Y0 + 3.0                        # 3mm behind the baffle face
    glass_y1 = glass_y0 + GLASS[2]
    mcx = (gx0 + gx1) / 2                             # MEASURE: module assumed centred on the glass
    mx0, mx1 = mcx - MODULE[0] / 2, mcx + MODULE[0] / 2
    mz0, mz1 = ez - MODULE[1] / 2, ez + MODULE[1] / 2
    pcb_y0, pcb_y1 = glass_y1, glass_y1 + MODULE[2]
    baffle = baffle.cut(box(gx0 - 0.3, BAFFLE_Y0 - 1, gz0 - 0.3, gx1 + 0.3, pcb_y0 + 0.1, gz1 + 0.3))
    baffle = baffle.cut(box(mx0 - 0.4, pcb_y0 - 0.1, mz0 - 0.4, mx1 + 0.4, BAFFLE_Y1 + 1, mz1 + 0.4))

    kx, kz = KNOB_C
    enc_face_y = BAFFLE_Y0 + 4.0                      # counterbore floor = encoder mounting face
    baffle = baffle.cut(ycyl(3.75, BAFFLE_Y0 - 1, BAFFLE_Y1 + 1, kx, kz))
    baffle = baffle.cut(box(kx - 7, enc_face_y, kz - 7, kx + 7, BAFFLE_Y1 + 1, kz + 7))

    led_x, led_z = ex + 18.0, 106.4
    baffle = baffle.cut(ycyl(1.6, BAFFLE_Y0 - 1, BAFFLE_Y1 + 1, led_x, led_z))
    add("Front_Baffle", baffle, DARK_WOOD, g_front)

    # ── Grille (brass mesh in the real build; printable stand-in) ───────
    grille = ycyl(GRILLE_R, by0 - 1.2, by0, *DRIVER_C)
    holes = []
    pitch = 4.5
    rows = int(GRILLE_R / (pitch * 0.866)) + 1
    for row in range(-rows, rows + 1):
        dz = row * pitch * 0.866
        offset = (pitch / 2) if row % 2 else 0.0
        cols = int(GRILLE_R / pitch) + 1
        for col in range(-cols, cols + 1):
            ddx = col * pitch + offset
            if math.hypot(ddx, dz) < GRILLE_R - 5:
                holes.append(ycyl(1.25, by0 - 2, by0 + 1, DRIVER_C[0] + ddx, DRIVER_C[1] + dz))
    add("Speaker_Grille", grille.cut(Part.makeCompound(holes)), BRASS, g_front)

    # ── Speaker chamber ─────────────────────────────────────────────────
    dx_, dz_ = DRIVER_C
    y = BAFFLE_Y1
    add("Driver_Gasket", ycyl(DRIVER_FRAME_R, y, y + 1, dx_, dz_).cut(ycyl(DRIVER_CUTOUT_R, y - 1, y + 2, dx_, dz_)),
        FOAM, g_acoustic)
    frame = ycyl(DRIVER_FRAME_R, y + 1, y + 4, dx_, dz_).cut(ycyl(35, y, y + 5, dx_, dz_))
    basket = Part.makeCone(35, 27, 27, V(dx_, y + 4, dz_), V(0, 1, 0)).cut(
        Part.makeCone(33.5, 25.5, 27.2, V(dx_, y + 3.9, dz_), V(0, 1, 0)))
    magnet = ycyl(27, y + 31, y + 1 + DRIVER_DEPTH, dx_, dz_)
    add("Driver_PC83_4", fuse_all([frame, basket, magnet]), MATTE_BLACK, g_acoustic)
    cone = Part.makeCone(34.5, 12, 14, V(dx_, y - 0.5, dz_), V(0, 1, 0)).cut(
        Part.makeCone(33.5, 11, 14.2, V(dx_, y - 1.3, dz_), V(0, 1, 0)))
    dustcap = Part.makeSphere(9, V(dx_, y + 9, dz_)).common(ycyl(10, y - 1, y + 9, dx_, dz_))
    add("Driver_Cone", cone.fuse(dustcap), (0.20, 0.20, 0.21), g_acoustic)

    cx0, cx1 = WALL, DIV_X0
    wad = fuse_all([
        box(cx0, 66, floor, cx0 + 10, REAR_REBATE_Y, top_in),
        box(cx0 + 10, 80, floor, cx1, REAR_REBATE_Y, top_in),
        box(cx0 + 10, 66, top_in - 10, cx1, 80, top_in),
        box(cx0 + 10, 66, floor, cx1, 80, floor + 10),
    ])
    add("Acoustic_Wadding", wad, WADDING, g_acoustic, transparency=55)
    grommet = xcyl(5.0, DIV_X0 - 1.5, DIV_X0, 50.0, 95.0).fuse(xcyl(5.0, DIV_X1, DIV_X1 + 1.5, 50.0, 95.0))
    grommet = grommet.fuse(xcyl(4.0, DIV_X0, DIV_X1, 50.0, 95.0)).cut(xcyl(1.5, DIV_X0 - 2, DIV_X1 + 2, 50.0, 95.0))
    add("Speaker_Wire_Grommet", grommet, FOAM, g_acoustic)

    # ── Rear: gasket, panel, screws, USB-C inlet, bay vents ─────────────
    ry0 = REAR_REBATE_Y + GASKET_T
    ry1 = ry0 + REAR_T
    outer = box(WALL - rr, REAR_REBATE_Y, WALL - rr, W - WALL + rr, ry0, H - WALL + rr)
    inner = box(WALL, REAR_REBATE_Y - 1, WALL, W - WALL, ry0 + 1, H - WALL)
    add("Rear_Gasket", outer.cut(inner).fuse(box(DIV_X0 + 1, REAR_REBATE_Y, floor, DIV_X1 - 1, ry0, top_in)).removeSplitter(),
        FOAM, g_cab)

    usb_cx, usb_z0 = 161.5, floor + 3.0               # breakout board sits on a printed saddle
    sock_z0 = usb_z0 + 1.6
    rear = box(WALL - rr + FIT, ry0, WALL - rr + FIT, W - WALL + rr - FIT, ry1, H - WALL + rr - FIT)
    rear = rear.cut(box(usb_cx - 5.0, ry0 - 1, sock_z0 - 0.3, usb_cx + 5.0, ry1 + 1, sock_z0 + 3.6))
    for i in range(6):
        vx = 124.0 + i * 7.0
        rear = rear.cut(box(vx, ry0 - 1, 62.0, vx + 3.0, ry1 + 1, 96.0))
    screw_pts = [(9, 9), (171, 9), (9, 111), (171, 111), (90, 9), (90, 111), ((DIV_X0 + DIV_X1) / 2, 60)]
    for sx, sz in screw_pts:
        rear = rear.cut(ycyl(1.7, ry0 - 1, ry1 + 1, sx, sz))
        rear = rear.cut(ycyl(3.0, ry1 - 2.0, ry1 + 1, sx, sz))                 # counterbore for the head
    add("Rear_Panel", rear, BIRCH_PLY, g_cab)
    add("Rear_Screws", fuse_all([ycyl(2.7, ry1 - 2.0, ry1 - 0.2, sx, sz) for sx, sz in screw_pts]), ALUMINIUM, g_cab)

    add("USBC_Saddle", box(usb_cx - 5.5, 72, floor, usb_cx + 5.5, REAR_REBATE_Y - 0.5, usb_z0), PRINT_BLACK, g_bay)
    add("USBC_Breakout", box(usb_cx - 5.5, 73, usb_z0, usb_cx + 5.5, REAR_REBATE_Y - 0.2, sock_z0), PCB_BLACK, g_bay)
    add("USBC_Socket", box(usb_cx - 4.5, ry1 - 7.4, sock_z0, usb_cx + 4.5, ry1 - 0.3, sock_z0 + 3.3), ALUMINIUM, g_bay)

    # ── Display: dial window, hood, glass, module, clamp ────────────────
    hb = BEZEL / 2
    bezel = box(ex - hb, by0 - 3, ez - hb, ex + hb, by0, ez + hb)
    bezel = bezel.cut(box(ex - 17, by0 - 4, ez - 17, ex + 17, by0 - 1.5, ez + 17))
    win = ACTIVE / 2 + 0.4
    bezel = bezel.cut(box(ex - win, by0 - 4, ez - win, ex + win, by0 + 1, ez + win))
    hood_z0 = ez + hb
    hood_top = box(ex - hb, by0 - 16, hood_z0, ex + hb, by0, hood_z0 + 3.5)
    # Lip along the hood's front edge, chamfered underneath so it prints without support
    lip_pts = [(by0 - 16, hood_z0), (by0 - 13, hood_z0), (by0 - 16, hood_z0 - 3)]   # 45° underside
    lip = Part.Face(Part.makePolygon([V(ex - hb, yy, zz) for yy, zz in lip_pts] +
                                     [V(ex - hb, lip_pts[0][0], lip_pts[0][1])])).extrude(V(BEZEL, 0, 0))
    channel = box(led_x - 1.6, by0 - 12, hood_z0 - 0.1, led_x + 1.6, by0 + 0.1, hood_z0 + 2.0)   # LED wire channel
    hood = bezel.fuse(hood_top).fuse(lip).removeSplitter().cut(channel)
    add("Bezel_and_Hood", hood, PRINT_BLACK, g_front)
    add("LED_Strip_COB", box(ex - 20, by0 - 13, hood_z0 - 1.0, ex + 20, by0 - 5, hood_z0), WARM_LED, g_front,
        emissive=WARM_LED)

    add("EInk_Glass", box(gx0, glass_y0, gz0, gx1, glass_y1, gz1), EPAPER, g_front)
    add("EInk_Module_PCB", box(mx0, pcb_y0, mz0, mx1, pcb_y1, mz1), PCB_GREEN, g_bay)
    # Clamp is only 1mm wider than the module (the bay allows no more); its
    # screws sit above and below the module instead of beside it.
    clamp = box(mx0 - 1, BAFFLE_Y1, mz0 - 5, mx1 + 1, BAFFLE_Y1 + 3, mz1 + 5)
    clamp = clamp.cut(box(mx0 + 5, BAFFLE_Y1 - 1, mz0 + 5, mx1 - 5, BAFFLE_Y1 + 4, mz1 - 5))   # parts + connector
    cs = [(mx0 + 5, mz0 - 2.5), (mx1 - 5, mz0 - 2.5), (mx0 + 5, mz1 + 2.5), (mx1 - 5, mz1 + 2.5)]
    for sx, sz in cs:
        clamp = clamp.cut(ycyl(1.35, BAFFLE_Y1 - 1, BAFFLE_Y1 + 4, sx, sz))    # M2.5 clearance into the baffle
    add("Display_Clamp", clamp, PRINT_BLACK, g_bay)

    font = next((f for f in FONT_CANDIDATES if os.path.exists(f)), None)
    if font:
        try:
            import Draft
            rot = App.Rotation(V(1, 0, 0), 90)

            def text(label, s, size, max_width, z):
                ss = Draft.make_shapestring(String=s, FontFile=font, Size=size)
                doc.recompute()
                if ss.Shape.BoundBox.XLength > max_width:
                    ss.Size = size * max_width / ss.Shape.BoundBox.XLength
                    doc.recompute()
                bb = ss.Shape.BoundBox
                ss.Placement = App.Placement(V(ex - bb.XMin - bb.XLength / 2, glass_y0 - 0.05, z), rot)
                g_front.addObject(ss)
                ss.Label = label
                if gui:
                    ss.ViewObject.ShapeColor = MATTE_BLACK
                return ss

            usable = ACTIVE - 3.0
            text("Face_Time", "06:45", 9.0, usable, ez - 1.5)
            text("Face_Date", "SAT 27", 3.4, usable * 0.6, ez - 8.5)
            add("Face_AlarmArmed", ycyl(0.9, glass_y0 - 0.1, glass_y0, ex + 10.5, ez + 10.0), MATTE_BLACK, g_front)
        except Exception as e:
            App.Console.PrintWarning(f"Clock face text skipped: {e}\n")

    # ── Encoder and knob ────────────────────────────────────────────────
    ebx, ebz, ebd = ENC_BODY
    enc = box(kx - ebx / 2, enc_face_y, kz - ebz / 2, kx + ebx / 2, enc_face_y + ebd, kz + ebz / 2)
    enc = enc.fuse(ycyl(3.5, enc_face_y - ENC_BUSHING, enc_face_y, kx, kz))
    shaft = ycyl(3.0, enc_face_y - ENC_SHAFT, enc_face_y - ENC_BUSHING, kx, kz)
    enc = enc.fuse(shaft.cut(box(kx + 1.5, -30, kz - 4, kx + 4, 10, kz + 4)))   # 6mm D, 4.5mm across the flat
    add("Encoder_EC11", enc, (0.45, 0.45, 0.47), g_bay)
    add("Encoder_Nut", ycyl(5.0, BAFFLE_Y0 - NUT_T, BAFFLE_Y0, kx, kz).cut(ycyl(3.5, -5, 5, kx, kz)), ALUMINIUM, g_bay)

    shaft_tip = enc_face_y - ENC_SHAFT
    knob_back = BAFFLE_Y0 - NUT_T - 1.5                 # clears the nut and the bushing tip
    knob_front = shaft_tip - 1.5
    knob = ycyl(KNOB_R, knob_front, knob_back - 1.5, kx, kz)
    knob = knob.fuse(Part.makeCone(KNOB_R, KNOB_R + 1.5, 1.5, V(kx, knob_back - 1.5, kz), V(0, 1, 0)))
    grooves = []
    for i in range(40):
        g = box(-0.6, knob_front + 1, KNOB_R - 0.8, 0.6, knob_back + 1, KNOB_R + 2)   # run out through the skirt
        g.rotate(V(0, 0, 0), V(0, 1, 0), 360.0 * i / 40)
        g.translate(V(kx, 0, kz))
        grooves.append(g)
    knob = knob.cut(Part.makeCompound(grooves))
    knob = knob.cut(ycyl(6.5, knob_back - 3.0, knob_back + 1, kx, kz))          # nut / bushing recess
    bore = ycyl(3.1, shaft_tip - 0.3, knob_back, kx, kz).cut(box(kx + 1.65, -30, kz - 4, kx + 4, 10, kz + 4))
    knob = knob.cut(bore)                                                        # 6mm D-shaft
    knob = knob.cut(ycyl(1.2, knob_front - 1, knob_front + 0.8, kx, kz + KNOB_R - 4))   # indicator dot
    add("Encoder_Knob", knob, ALUMINIUM, g_ctrl)

    # ── Buttons ─────────────────────────────────────────────────────────
    cap_bottom = top_in - 0.5 - 1.5                     # flange stops 0.5mm under the deck
    plate_top = cap_bottom - SWITCH_TOTAL_H
    plate = box(BUTTON_X - 15, 18, plate_top - 3, BUTTON_X + 15, 88, plate_top)
    boss_pts = [(BUTTON_X - 11, 46), (BUTTON_X + 11, 70)]
    bplate = fuse_all([plate] + [zcyl(3.5, plate_top, top_in - 0.3, x, yy) for x, yy in boss_pts])
    for x, yy in boss_pts:
        bplate = bplate.cut(zcyl(1.7, plate_top - 4, top_in, x, yy))           # M3 clearance, screws up into the deck
    add("Button_Plate", bplate, PRINT_BLACK, g_bay)
    for name, by, br in BUTTONS:
        sw = box(BUTTON_X - 6, by - 6, plate_top, BUTTON_X + 6, by + 6, plate_top + SWITCH_BODY_H).fuse(
            zcyl(1.75, plate_top + SWITCH_BODY_H, cap_bottom, BUTTON_X, by))
        add(f"Switch_{name}", sw, (0.25, 0.25, 0.25), g_bay)
        cap = zcyl(br, cap_bottom, H + 4, BUTTON_X, by).fuse(zcyl(br + 2, cap_bottom, cap_bottom + 1.5, BUTTON_X, by))
        if name == "Snooze":
            cap = cap.fuse(zcyl(br - 2, H + 4, H + 5, BUTTON_X, by))
        add(f"Button_{name}", cap.removeSplitter(), BRASS if name == "Snooze" else MATTE_BLACK, g_ctrl)

    # ── Electronics bay ─────────────────────────────────────────────────
    pi = (122.0, 20.0)                      # 30 x 65, long axis front-to-back, SD card to the rear
    holes_pi = [(pi[0] + 3.5, pi[1] + 3.5), (pi[0] + 26.5, pi[1] + 3.5),
                (pi[0] + 3.5, pi[1] + 61.5), (pi[0] + 26.5, pi[1] + 61.5)]
    tray = box(pi[0] - 3, pi[1] - 3, floor, pi[0] + 33, pi[1] + 68, floor + 2)
    tray = fuse_all([tray] + [zcyl(2.6, floor + 2, floor + 6, x, yy) for x, yy in holes_pi])
    for x, yy in holes_pi:
        tray = tray.cut(zcyl(1.1, floor + 0.8, floor + 7, x, yy))             # M2.5 self-tap pilot
    add("Pi_Tray", tray, PRINT_BLACK, g_bay)
    pi_z = floor + 6
    add("Pi_Zero_2W", box(pi[0], pi[1], pi_z, pi[0] + 30, pi[1] + 65, pi_z + 1.6), PCB_GREEN, g_bay)
    add("Pi_GPIO_Header", box(pi[0] + 30 - 5.1, pi[1] + 7, pi_z + 1.6, pi[0] + 30 - 0.1, pi[1] + 58, pi_z + 10.1),
        MATTE_BLACK, g_bay)

    tape = 1.0                               # divider-mounted boards sit on foam tape: no guessed hole positions
    wx = DIV_X1 + tape
    add("Mount_Tape", fuse_all([box(DIV_X1, 23, 61, wx, 40, 76), box(DIV_X1, 52, 28, wx, 86, 46),
                                box(DIV_X1, 60, 83, wx, 76, 98)]), (0.85, 0.85, 0.80), g_bay)
    add("MAX98357A_Amp", box(wx, 22, 60, wx + 1.6, 41.4, 77.8), PCB_BLUE, g_bay)
    add("DS3231_ZS042", box(wx, 50, 26, wx + 1.6, 88, 48), PCB_BLUE, g_bay)
    add("RTC_Battery_Holder", xcyl(10.5, wx + 1.6, wx + 1.6 + 7.0, 75.0, 37.0), MATTE_BLACK, g_bay)
    add("MOSFET_Dimmer", box(wx, 59, 82, wx + 1.6, 77, 99), PCB_BLUE, g_bay)

    feet = [zcyl(7, -2, 0, x, yy) for x, yy in [(20, 15), (160, 15), (20, 85), (160, 85)]]
    add("Felt_Feet", fuse_all(feet), (0.25, 0.25, 0.25), g_cab)

    doc.recompute()

    # ── Acoustics ───────────────────────────────────────────────────────
    chamber = box(WALL, BAFFLE_Y1, WALL, DIV_X0, REAR_REBATE_Y, H - WALL)
    for label in ("Driver_PC83_4", "Driver_Cone", "Driver_Gasket"):
        chamber = chamber.cut(doc.getObjectsByLabel(label)[0].Shape)
    net_l = chamber.Volume / 1e6
    qtc, fc = sealed_box_alignment(net_l * WADDING_FACTOR)
    doc.Comment = f"V1 · sealed chamber {net_l:.3f}L net · Qtc {qtc:.2f} · fc {fc:.0f}Hz (PC83-4)"
    App.Console.PrintMessage(doc.Comment + "\n")

    here = os.path.dirname(os.path.abspath(__file__))
    doc.saveAs(os.path.join(here, "DigitalRadioAlarm.FCStd"))
    export_stls(doc, os.path.join(here, "stl"))

    if gui:
        import FreeCADGui as Gui
        App.setActiveDocument(doc.Name)
        view = Gui.getDocument(doc.Name).ActiveView
        view.viewIsometric()
        view.fitAll()
    return doc


def export_stls(doc, out_dir):
    """Export each printable part, rotated so its chosen face sits on the bed."""
    os.makedirs(out_dir, exist_ok=True)
    report = []
    for label, (down, role, note) in PRINTS.items():
        shape = doc.getObjectsByLabel(label)[0].Shape.copy()
        rot = App.Rotation(V(*down), V(0, 0, -1))
        shape.rotate(V(0, 0, 0), rot.Axis, math.degrees(rot.Angle))
        bb = shape.BoundBox
        shape.translate(V(-bb.Center.x, -bb.Center.y, -bb.ZMin))
        bb = shape.BoundBox
        # Binary STL at 0.02mm chordal tolerance: far finer than any FDM printer
        # resolves, without the tens-of-megabytes ASCII files exportStl writes.
        import MeshPart
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02, AngularDeflection=0.25, Relative=False)
        mesh.write(os.path.join(out_dir, f"{label}.stl"))
        report.append((label, role, round(bb.XLength, 1), round(bb.YLength, 1), round(bb.ZLength, 1),
                       bed_fit(bb.XLength, bb.YLength), note))
    with open(os.path.join(out_dir, "prints.tsv"), "w") as f:
        f.write("part\trole\tx\ty\tz\tbed\tnote\n")
        for row in report:
            f.write("\t".join(str(v) for v in row) + "\n")
    return report


if __name__ in ("__main__", "build_radio"):
    main()
