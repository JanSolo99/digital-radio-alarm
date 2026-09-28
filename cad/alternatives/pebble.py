"""Alternative design B - "Pebble".

A soft ellipsoidal body in the manner of a modern smart speaker:
  * the speaker fires DOWN into a 10mm gap under the body (as a HomePod
    mini does), so sound spreads evenly round the room and no grille
    breaks up the surface;
  * a front facet tilted 25 degrees back holds the e-ink display, angled
    up toward someone lying in bed, with a slim light "eyebrow" above it;
  * the top carries a rotating aluminium puck (the encoder: turn for
    volume or station, press to select, and press to snooze while the
    alarm rings) between two small buttons, menu and dismiss.

Inside, a horizontal shelf seals the lower half as the speaker chamber;
the electronics sit on top of the shelf. Printed as a 3mm shell (two
halves split at the shelf in practice), optionally fabric-wrapped.

Axes: X width, Y depth (front toward -Y), Z height. Origin on the table
under the centre. mm. Run inside FreeCAD; saves cad/alternatives/Pebble.FCStd.
"""

import importlib
import math
import os
import sys

import FreeCAD as App
import Part
from FreeCAD import Vector as V

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as c  # noqa: E402

importlib.reload(c)
from common import box, fuse_all, placed, zcyl  # noqa: E402

A, B, C = 85.0, 65.0, 65.0             # ellipsoid semi-axes (x, y, z)
ZC = 50.0                              # ellipsoid centre height
Z_BASE, Z_TOP = 10.0, 108.0            # flat base and flat top
SHELL = 3.0
THETA = 25.0                           # display facet tilt back from vertical
FACET_POINT = V(0, -40.0, 90.0)       # cut deep enough that the facet reaches the top
SHELF_Z0, SHELF_Z1 = 66.0, 69.0
DRIVER_XY = (0.0, 5.0)
PUCK_XY = (0.0, 5.0)
PUCK_R = 20.0
TOP_BUTTONS = [("Menu", -30.0, 5.0), ("Dismiss", 30.0, 5.0)]
FEET = [(0.0, 40.0), (-50.0, -25.0), (50.0, -25.0)]

CHALK = (0.86, 0.84, 0.80)
CHALK_DARK = (0.78, 0.76, 0.72)
CHARCOAL = (0.20, 0.20, 0.21)

DOC_NAME = "Pebble"

N = V(0, -math.cos(math.radians(THETA)), math.sin(math.radians(THETA)))   # facet outward normal
UP = V(0, math.sin(math.radians(THETA)), math.cos(math.radians(THETA)))   # "up" within the facet


def ellipsoid(a, b, c_, zc):
    m = App.Matrix()
    m.scale(a, b, c_)
    s = Part.makeSphere(1.0).transformGeometry(m)
    s.translate(V(0, 0, zc))
    return s


def halfspace(point, normal, size=500.0):
    """Solid occupying everything on the `normal` side of the plane through `point`."""
    h = Part.makeBox(size, size, size, V(-size / 2, -size / 2, 0))
    rot = App.Rotation(V(0, 0, 1), normal)
    h.rotate(V(0, 0, 0), rot.Axis, math.degrees(rot.Angle))
    h.translate(point)
    return h


def body_solid(offset):
    """Outer body (offset=0) or the inner cavity (offset=SHELL)."""
    s = ellipsoid(A - offset, B - offset, C - offset, ZC)
    s = s.common(box(-200, -200, Z_BASE + offset, 200, 200, Z_TOP - offset))
    return s.cut(halfspace(FACET_POINT - N * offset, N))


def main():
    bld = c.Builder(DOC_NAME)
    add = bld.add

    outer = body_solid(0.0)
    inner = body_solid(SHELL)
    shell = outer.cut(inner)

    # Display facet: find the flat face, centre the display a little below its middle
    facet = max((f for f in outer.Faces if f.normalAt(0, 0).getAngle(N) < 0.05), key=lambda f: f.Area)
    # The display has to clear the shelf below and leave room for the light above,
    # so place it by height on the facet plane rather than at the facet's centroid.
    dcen = FACET_POINT + UP * ((86.7 - FACET_POINT.z) / UP.z)
    dpl = App.Placement(dcen, App.Rotation(V(1, 0, 0), -THETA))
    disp = c.display_local(SHELL, recess=1.0)
    shell = shell.cut(placed(disp["cut"], dpl))

    # Openings: driver (bottom), puck shaft and buttons (top), USB-C (back)
    dx, dy = DRIVER_XY
    shell = shell.cut(zcyl(c.DRIVER_CUTOUT_R, Z_BASE - 1, Z_BASE + SHELL + 1, dx, dy))
    shell = shell.cut(zcyl(41.3, Z_BASE - 1, Z_BASE + 1.2, dx, dy))                  # grille counterbore
    px, py = PUCK_XY
    shell = shell.cut(zcyl(4.5, Z_TOP - SHELL - 1, Z_TOP + 1, px, py))
    for _, bx, by in TOP_BUTTONS:
        shell = shell.cut(zcyl(5.5, Z_TOP - SHELL - 1, Z_TOP + 1, bx, by))
    shelf_top = SHELF_Z1
    usb_x, usb_z0 = 40.0, shelf_top + 3.0
    sock_z0 = usb_z0 + 1.6
    shell = shell.cut(box(usb_x - 5.0, 40, sock_z0 - 0.3, usb_x + 5.0, 70, sock_z0 + 3.6))
    add("Shell", shell, CHALK, "Body")

    # ── Display on the facet ────────────────────────────────────────────
    # The whole facet becomes a black glass face (like a smart display's front),
    # so the flat oval reads as the device's face rather than a cut-off patch.
    face_plate = facet.extrude(N * 0.8).cut(placed(disp["window"], dpl))
    add("Glass_Face", face_plate, (0.07, 0.07, 0.08), "Front")
    add("EInk_Glass", placed(disp["glass"], dpl), c.EPAPER, "Front")
    add("EInk_Module_PCB", placed(disp["module"], dpl), c.PCB_GREEN, "Electronics")
    brow = box(-22, -8.8, 17.5, 22, -0.8, 19.5)
    brow = brow.fuse(Part.Face(Part.makePolygon([V(-22, -8.8, 17.5), V(-22, -6.3, 17.5), V(-22, -8.8, 15.5),
                                                 V(-22, -8.8, 17.5)])).extrude(V(44, 0, 0))).removeSplitter()
    add("Light_Eyebrow", placed(brow, dpl), CHALK_DARK, "Front")
    add("LED_Strip", placed(box(-19, -5.3, 16.5, 19, -1.6, 17.5), dpl), c.WARM_LED, "Front", emissive=c.WARM_LED)
    mx0, mx1, mz0, mz1, my1 = disp["module_bounds"]
    # The inside narrows sharply toward the top front and the shelf is just below,
    # so the module is held by a strap across its middle, screwed to posts at the
    # widest point of the facet.
    clamp = box(mx0 - 6.5, my1, -4, mx1 + 6.5, my1 + 3, 4)
    bosses = [Part.makeCylinder(3.0, my1 - SHELL - 0.3, V(x_, SHELL + 0.3, 0), V(0, 1, 0))
              for x_ in (mx0 - 3.5, mx1 + 3.5)]
    add("Display_Clamp", placed(fuse_all([clamp] + bosses), dpl), c.PRINT_BLACK, "Electronics")

    # ── Down-firing driver, bottom grille, feet ─────────────────────────
    drv_pl = App.Placement(V(dx, dy, Z_BASE + SHELL), App.Rotation(V(1, 0, 0), 90))
    drv = c.driver_local()
    add("Driver_Gasket", placed(drv["gasket"], drv_pl), c.FOAM, "Speaker_Chamber")
    add("Driver_PC83_4", placed(drv["body"], drv_pl), c.MATTE_BLACK, "Speaker_Chamber")
    add("Driver_Cone", placed(drv["cone"], drv_pl), (0.20, 0.20, 0.21), "Speaker_Chamber")
    grille = zcyl(41.0, Z_BASE, Z_BASE + 1.2, dx, dy)
    holes = []
    for row in range(-10, 11):
        yy = row * 4.0 * 0.866
        for col in range(-10, 11):
            xx = col * 4.0 + (2.0 if row % 2 else 0.0)
            if math.hypot(xx, yy) < 36:
                holes.append(zcyl(1.2, Z_BASE - 1, Z_BASE + 2, dx + xx, dy + yy))
    add("Bottom_Grille", grille.cut(Part.makeCompound(holes)), CHARCOAL, "Body")
    add("Feet", fuse_all([zcyl(8.0, 0, Z_BASE, fx, fy) for fx, fy in FEET]), CHARCOAL, "Body")

    # ── Shelf: lid of the sealed chamber, floor of the electronics ──────
    shelf = inner.common(box(-200, -200, SHELF_Z0, 200, 200, SHELF_Z1))
    shelf = shelf.cut(zcyl(4.0, SHELF_Z0 - 1, SHELF_Z1 + 1, -45.0, 35.0))
    add("Shelf", shelf, c.PRINT_BLACK, "Speaker_Chamber")
    add("Speaker_Wire_Grommet", zcyl(5.0, SHELF_Z0 - 1.5, SHELF_Z0, -45.0, 35.0).fuse(
        zcyl(5.0, SHELF_Z1, SHELF_Z1 + 1.5, -45.0, 35.0)).fuse(zcyl(4.0, SHELF_Z0, SHELF_Z1, -45.0, 35.0)).cut(
        zcyl(1.5, SHELF_Z0 - 2, SHELF_Z1 + 2, -45.0, 35.0)), c.FOAM, "Speaker_Chamber")

    # ── Top: rotating puck on the encoder, two buttons ──────────────────
    top_in = Z_TOP - SHELL
    face = Z_TOP - 12.0                               # encoder mounting face, on a bracket under the top
    enc = box(px - 6, py - 6, face - 6.5, px + 6, py + 6, face)
    enc = enc.fuse(zcyl(3.5, face, face + c.ENC_BUSHING, px, py))
    enc = enc.fuse(zcyl(3.0, face + c.ENC_BUSHING, face + c.ENC_SHAFT, px, py).cut(
        box(px + 1.5, py - 4, face, px + 4, py + 4, face + 30)))
    add("Encoder_EC11", enc, (0.45, 0.45, 0.47), "Electronics")
    bracket = box(px - 12, py - 12, face, px + 12, py + 12, face + 3).cut(zcyl(3.6, face - 1, face + 4, px, py))
    bracket = fuse_all([bracket] + [zcyl(3.0, face + 3, top_in, px + sx, py) for sx in (-9.0, 9.0)])
    add("Encoder_Bracket", bracket, c.PRINT_BLACK, "Electronics")
    add("Encoder_Nut", zcyl(5.0, face + 3, face + 5, px, py).cut(zcyl(3.5, face, face + 6, px, py)), c.ALUMINIUM, "Electronics")

    shaft_tip = face + c.ENC_SHAFT
    puck_top = shaft_tip + 2.5
    puck = zcyl(PUCK_R, Z_TOP + 1.0, puck_top, px, py)
    grooves = []
    for i in range(48):
        g = box(-0.5, PUCK_R - 0.7, Z_TOP + 1.8, 0.5, PUCK_R + 1, puck_top + 1)
        g.rotate(V(0, 0, 0), V(0, 0, 1), 360.0 * i / 48)
        g.translate(V(px, py, 0))
        grooves.append(g)
    puck = puck.cut(Part.makeCompound(grooves))
    puck = puck.cut(zcyl(PUCK_R - 4, puck_top - 0.8, puck_top + 1, px, py))         # shallow dish
    puck = puck.cut(zcyl(3.1, Z_TOP, shaft_tip + 0.3, px, py).cut(box(px + 1.65, py - 4, 0, px + 4, py + 4, 200)))
    add("Puck_Knob", puck, c.ALUMINIUM, "Controls")

    for name, bx, by in TOP_BUTTONS:
        sw, cap, sw_z0 = c.tactile_button(5.0, Z_TOP + 2.0, top_in, bx, by)
        add(f"Switch_{name}", sw, (0.25, 0.25, 0.25), "Electronics")
        add(f"Button_{name}", cap, CHALK_DARK, "Controls")
        plate = box(bx - 8, by - 8, sw_z0 - 3, bx + 8, by + 8, sw_z0)
        plate = fuse_all([plate] + [zcyl(2.5, sw_z0, top_in, bx * 0.75, by + s) for s in (-9.0, 9.0)])
        add(f"Button_Plate_{name}", plate, c.PRINT_BLACK, "Electronics")

    # ── Electronics on the shelf ────────────────────────────────────────
    s1 = SHELF_Z1
    tray, board, header = c.pi_zero(-15.0, -12.0, s1)
    add("Pi_Tray", tray, c.PRINT_BLACK, "Electronics")
    add("Pi_Zero_2W", board, c.PCB_GREEN, "Electronics")
    add("Pi_GPIO_Header", header, c.MATTE_BLACK, "Electronics")
    t = s1 + 1.0
    add("MAX98357A_Amp", box(22, -2, t, 39.8, 17.4, t + 1.6), c.PCB_BLUE, "Electronics")
    add("MOSFET_Dimmer", box(22, 18, t, 40, 35, t + 1.6), c.PCB_BLUE, "Electronics")
    add("DS3231_ZS042", box(-50, -10, t, -28, 28, t + 1.6), c.PCB_BLUE, "Electronics")
    add("RTC_Battery_Holder", zcyl(10.5, t + 1.6, t + 8.6, -39.0, 12.0), c.MATTE_BLACK, "Electronics")
    add("Mount_Tape", fuse_all([box(22, -2, s1, 39.8, 17.4, t), box(22, 18, s1, 40, 35, t),
                                box(-50, -10, s1, -28, 28, t)]), (0.85, 0.85, 0.80), "Electronics")
    add("USBC_Saddle", box(usb_x - 5.5, 37, s1, usb_x + 5.5, 45, usb_z0), c.PRINT_BLACK, "Electronics")
    add("USBC_Breakout", box(usb_x - 5.5, 37.5, usb_z0, usb_x + 5.5, 46, sock_z0), c.PCB_BLACK, "Electronics")
    add("USBC_Socket", box(usb_x - 4.5, 44, sock_z0, usb_x + 4.5, 51.5, sock_z0 + 3.3), c.ALUMINIUM, "Electronics")

    bld.doc.recompute()

    chamber = inner.common(box(-200, -200, Z_BASE + SHELL, 200, 200, SHELF_Z0))
    for label in ("Driver_PC83_4", "Driver_Cone", "Driver_Gasket"):
        chamber = chamber.cut(bld.doc.getObjectsByLabel(label)[0].Shape)
    net_l = chamber.Volume / 1e6
    qtc, fc = c.sealed_box_alignment(net_l * c.WADDING_FACTOR)
    bb = outer.optimalBoundingBox()
    bld.doc.Comment = (f"Pebble · {bb.XLength:.0f}w x {Z_TOP:.0f}h x {bb.YLength:.0f}d mm · sealed chamber "
                       f"{net_l:.3f}L net · Qtc {qtc:.2f} · fc {fc:.0f}Hz · facet {facet.BoundBox.XLength:.0f}mm wide")
    App.Console.PrintMessage(bld.doc.Comment + "\n")
    bld.doc.saveAs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Pebble.FCStd"))
    return bld


if __name__ in ("__main__", "pebble"):
    main()
