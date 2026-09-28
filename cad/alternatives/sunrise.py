"""Alternative design A - "Sunrise".

An arched (tombstone) cabinet whose front is a night sky with a sun rising
over a horizon:
  * the speaker grille is the sun, with radial ray slots;
  * a translucent halo ring around it is a warm LED wake-up light that
    fades up before the radio does, and works as a night light;
  * a full-width "horizon" bar is also the hood that lights the display
    beneath it;
  * under the horizon: snooze (left), display (centre), knob (right).
    Menu and dismiss sit on the right side face, away from sleepy hands.

Same bought parts as V1. Inside, a horizontal divider makes the sealed
speaker chamber (the arch) and the electronics bay (the base).

Axes as V1: X width, Y depth (front face at Y=0), Z height. mm.
Run inside FreeCAD; saves cad/alternatives/Sunrise.FCStd.
"""

import math
import os
import sys

import FreeCAD as App
import Part
from FreeCAD import Vector as V

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib  # noqa: E402

import common as c  # noqa: E402

importlib.reload(c)                    # FreeCAD keeps modules cached between runs
from common import box, fuse_all, placed, xcyl, ycyl, zcyl  # noqa: E402

W, D = 150.0, 94.0
SPRING = 80.0                          # where the arch starts; radius is W/2
WALL = 12.0
FIT = 0.2
BAFFLE_Y0, BAFFLE_Y1 = 2.0, 11.0
FRONT_REBATE, REAR_REBATE = 4.0, 6.0
REAR_REBATE_Y = 84.0
GASKET_T, REAR_T = 1.5, 6.0
DIV_Z0, DIV_Z1 = 48.0, 54.0            # horizontal divider
DADO = 3.0

SUN_C = (W / 2, 97.0)                  # driver / sun centre (x, z)
HALO_R0, HALO_R1 = 44.0, 47.5
GRILLE_R = 42.0
DISPLAY_C = (W / 2, 29.5)
KNOB_C = (125.0, 29.5)
SNOOZE_C = (25.0, 29.5)
SIDE_BUTTONS = [("Menu", 35.0, 30.0), ("Dismiss", 60.0, 30.0)]   # (name, y, z) on the right face

OAK = (0.74, 0.58, 0.40)
NIGHT = (0.10, 0.13, 0.22)
NIGHT_BLACK = (0.06, 0.07, 0.11)
BIRCH_PLY = (0.80, 0.70, 0.52)
HALO = (1.0, 0.72, 0.38)

DOC_NAME = "Sunrise"


def arch_prism(x0, x1, z0, y0, y1):
    """Tombstone profile (flat bottom, semicircular top) extruded along Y."""
    r = (x1 - x0) / 2
    cx = (x0 + x1) / 2
    a = V(x0, y0, z0)
    b = V(x1, y0, z0)
    c1 = V(x1, y0, SPRING)
    top = V(cx, y0, SPRING + r)
    d = V(x0, y0, SPRING)
    wire = Part.Wire([Part.LineSegment(a, b).toShape(), Part.LineSegment(b, c1).toShape(),
                      Part.Arc(c1, top, d).toShape(), Part.LineSegment(d, a).toShape()])
    return Part.Face(wire).extrude(V(0, y1 - y0, 0))


def main():
    bld = c.Builder(DOC_NAME)
    add = bld.add
    fr, rr = FRONT_REBATE, REAR_REBATE

    # ── Arch carcass: a 12mm tube of the tombstone profile ──────────────
    outer = arch_prism(0, W, 0, 0, D)
    inner = arch_prism(WALL, W - WALL, WALL, -1, D + 1)
    carcass = outer.cut(inner)
    carcass = carcass.cut(arch_prism(WALL - fr, W - WALL + fr, WALL - fr, -1, BAFFLE_Y1))
    carcass = carcass.cut(arch_prism(WALL - rr, W - WALL + rr, WALL - rr, REAR_REBATE_Y, D + 1))
    carcass = carcass.cut(box(WALL - DADO, -1, DIV_Z0 - FIT, W - WALL + DADO, D + 1, DIV_Z1 + FIT))
    for _, by, bz in SIDE_BUTTONS:
        carcass = carcass.cut(xcyl(5.5, W - WALL - 1, W + 1, by, bz))
    add("Carcass_Arch", carcass, OAK, "Cabinet")
    add("Divider", box(WALL - DADO + FIT, BAFFLE_Y1, DIV_Z0, W - WALL + DADO - FIT, REAR_REBATE_Y, DIV_Z1).cut(
        zcyl(4.0, DIV_Z0 - 1, DIV_Z1 + 1, 60.0, 60.0)), BIRCH_PLY, "Cabinet")

    # ── Baffle: the night sky ───────────────────────────────────────────
    baffle = arch_prism(WALL - fr + FIT, W - WALL + fr - FIT, WALL - fr + FIT, BAFFLE_Y0, BAFFLE_Y1)
    sx, sz = SUN_C
    baffle = baffle.cut(ycyl(c.DRIVER_CUTOUT_R, 0, BAFFLE_Y1 + 1, sx, sz))
    halo_groove = ycyl(HALO_R1 + 0.3, BAFFLE_Y0 - 1, BAFFLE_Y0 + 5, sx, sz).cut(
        ycyl(HALO_R0 - 0.3, BAFFLE_Y0 - 2, BAFFLE_Y0 + 6, sx, sz))
    baffle = baffle.cut(halo_groove)
    wire_z = sz - (HALO_R0 + HALO_R1) / 2
    baffle = baffle.cut(ycyl(1.5, BAFFLE_Y0 + 4, BAFFLE_Y1 + 1, sx, wire_z))            # halo LED wires...
    baffle = baffle.cut(box(sx - 1.5, BAFFLE_Y1 - 2, DIV_Z0 - 4, sx + 1.5, BAFFLE_Y1 + 1, wire_z))   # ...down to the bay

    disp = c.display_local(BAFFLE_Y1 - BAFFLE_Y0)
    dpl = App.Placement(V(DISPLAY_C[0], BAFFLE_Y0, DISPLAY_C[1]), App.Rotation())
    baffle = baffle.cut(placed(disp["cut"], dpl))
    enc = c.encoder_local(BAFFLE_Y1 - BAFFLE_Y0)
    kpl = App.Placement(V(KNOB_C[0], BAFFLE_Y0, KNOB_C[1]), App.Rotation())
    baffle = baffle.cut(placed(enc["cut"], kpl))
    snx, snz = SNOOZE_C
    baffle = baffle.cut(ycyl(10.5, BAFFLE_Y0 - 1, BAFFLE_Y1 + 1, snx, snz))
    baffle = baffle.cut(ycyl(12.5, BAFFLE_Y0 + 3.5, BAFFLE_Y1 + 1, snx, snz))          # flange counterbore
    add("Front_Baffle", baffle, NIGHT, "Front")

    # ── The sun: ray grille + halo light ────────────────────────────────
    sun = ycyl(GRILLE_R, BAFFLE_Y0 - 1.2, BAFFLE_Y0, sx, sz)
    rays = []
    for i in range(24):
        ray = box(-1.5, BAFFLE_Y0 - 2, 11, 1.5, BAFFLE_Y0 + 1, GRILLE_R - 4)
        ray.rotate(V(0, 0, 0), V(0, 1, 0), 360.0 * i / 24)
        ray.translate(V(sx, 0, sz))
        rays.append(ray)
    sun = sun.cut(Part.makeCompound(rays))
    add("Sun_Grille", sun, c.BRASS, "Front")
    # ── Horizon bar (also the display's light hood) ─────────────────────
    hz0 = DISPLAY_C[1] + 20.0
    # The sun sits just behind the horizon: its halo's lowest arc tucks in behind the bar.
    halo = ycyl(HALO_R1, BAFFLE_Y0 - 0.4, BAFFLE_Y0 + 2, sx, sz).cut(
        ycyl(HALO_R0, BAFFLE_Y0 - 1, BAFFLE_Y0 + 3, sx, sz))
    halo = halo.cut(box(0, -20, 0, W, BAFFLE_Y0 + 0.3, hz0 + 3.8))
    add("Halo_Diffuser", halo, HALO, "Front", emissive=HALO)
    horizon = box(WALL + 2, BAFFLE_Y0 - 14, hz0, W - WALL - 2, BAFFLE_Y0, hz0 + 3.5)
    lip = Part.Face(Part.makePolygon([V(WALL + 2, BAFFLE_Y0 - 14, hz0), V(WALL + 2, BAFFLE_Y0 - 11, hz0),
                                      V(WALL + 2, BAFFLE_Y0 - 14, hz0 - 3), V(WALL + 2, BAFFLE_Y0 - 14, hz0)])
                    ).extrude(V(W - 2 * WALL - 4, 0, 0))
    add("Horizon_Hood", horizon.fuse(lip).removeSplitter(), c.BRASS, "Front")
    add("LED_Strip_Display", box(DISPLAY_C[0] - 20, BAFFLE_Y0 - 11, hz0 - 1, DISPLAY_C[0] + 20, BAFFLE_Y0 - 3, hz0),
        c.WARM_LED, "Front", emissive=c.WARM_LED)

    # ── Display ─────────────────────────────────────────────────────────
    # 48mm wide: the glass is 37.3mm and sits off-centre on its module, so a
    # square bezel lets its edge show on one side.
    bezel = box(-24, -3, -20, 24, 0, 20).cut(box(-17, -4, -17, 17, -1.5, 17)).cut(disp["window"])
    add("Display_Bezel", placed(bezel, dpl), NIGHT_BLACK, "Front")
    add("EInk_Glass", placed(disp["glass"], dpl), c.EPAPER, "Front")
    add("EInk_Module_PCB", placed(disp["module"], dpl), c.PCB_GREEN, "Electronics_Bay")
    mx0, mx1, mz0, mz1, my1 = disp["module_bounds"]
    back = BAFFLE_Y1 - BAFFLE_Y0
    clamp = box(mx0 - 5, back, mz0 - 0.5, mx1 + 5, back + 3, mz1 + 0.5)
    clamp = clamp.cut(box(mx0 + 5, back - 1, mz0 + 5, mx1 - 5, back + 4, mz1 - 5))
    for cx_ in (mx0 - 2.5, mx1 + 2.5):
        for cz_ in (-9.0, 9.0):
            clamp = clamp.cut(ycyl(1.35, back - 1, back + 4, cx_, cz_))
    add("Display_Clamp", placed(clamp, dpl), c.PRINT_BLACK, "Electronics_Bay")

    # ── Knob and snooze, flanking the display ───────────────────────────
    add("Encoder_EC11", placed(enc["encoder"], kpl), (0.45, 0.45, 0.47), "Electronics_Bay")
    add("Encoder_Nut", placed(enc["nut"], kpl), c.ALUMINIUM, "Electronics_Bay")
    knob = c.knurled_knob(12.0, enc["shaft_tip_y"] - 1.5, -3.5, enc["shaft_tip_y"])
    add("Encoder_Knob", placed(knob, kpl), c.ALUMINIUM, "Controls")

    sw_y0 = BAFFLE_Y1 + 3.8                       # switch body behind the baffle, actuator facing forward
    add("Switch_Snooze", box(snx - 6, BAFFLE_Y1, snz - 6, snx + 6, sw_y0, snz + 6).fuse(
        ycyl(1.75, BAFFLE_Y1 - 3.5, BAFFLE_Y1, snx, snz)), (0.25, 0.25, 0.25), "Electronics_Bay")
    cap_back = BAFFLE_Y1 - 3.5
    snooze = ycyl(10.0, BAFFLE_Y0 - 5, cap_back, snx, snz).fuse(ycyl(12.0, cap_back - 1.5, cap_back, snx, snz))
    add("Button_Snooze", snooze.fuse(ycyl(8.0, BAFFLE_Y0 - 6, BAFFLE_Y0 - 5, snx, snz)), c.BRASS, "Controls")
    add("Snooze_Bracket", box(snx - 9, sw_y0, snz - 9, snx + 9, sw_y0 + 3, snz + 9), c.PRINT_BLACK, "Electronics_Bay")

    # ── Side buttons: menu and dismiss on the right face ────────────────
    inner_x = W - WALL
    act_x = inner_x - 2.0                          # 0.5mm gap + 1.5mm flange
    for name, by, bzz in SIDE_BUTTONS:
        cap = xcyl(5.0, act_x, W + 3, by, bzz).fuse(xcyl(7.0, act_x, act_x + 1.5, by, bzz))
        add(f"Button_{name}", cap.removeSplitter(), NIGHT_BLACK, "Controls")
        add(f"Switch_{name}", box(act_x - 7.3, by - 6, bzz - 6, act_x - 3.5, by + 6, bzz + 6).fuse(
            xcyl(1.75, act_x - 3.5, act_x, by, bzz)), (0.25, 0.25, 0.25), "Electronics_Bay")
    plate_x1 = act_x - 7.3
    side_plate = box(plate_x1 - 3, 25, 22, plate_x1, 70, 38)
    side_plate = fuse_all([side_plate] + [xcyl(3.0, plate_x1, inner_x, 47.5, zz) for zz in (24.5, 35.5)])
    add("Side_Button_Plate", side_plate, c.PRINT_BLACK, "Electronics_Bay")

    # ── Speaker chamber (the arch) ──────────────────────────────────────
    dpl_drv = App.Placement(V(sx, BAFFLE_Y1, sz), App.Rotation())
    drv = c.driver_local()
    add("Driver_Gasket", placed(drv["gasket"], dpl_drv), c.FOAM, "Speaker_Chamber")
    add("Driver_PC83_4", placed(drv["body"], dpl_drv), c.MATTE_BLACK, "Speaker_Chamber")
    add("Driver_Cone", placed(drv["cone"], dpl_drv), (0.20, 0.20, 0.21), "Speaker_Chamber")
    add("Speaker_Wire_Grommet", zcyl(5.0, DIV_Z0 - 1.5, DIV_Z0, 60.0, 60.0).fuse(
        zcyl(5.0, DIV_Z1, DIV_Z1 + 1.5, 60.0, 60.0)).fuse(zcyl(4.0, DIV_Z0, DIV_Z1, 60.0, 60.0)).cut(
        zcyl(1.5, DIV_Z0 - 2, DIV_Z1 + 2, 60.0, 60.0)), c.FOAM, "Speaker_Chamber")

    # ── Electronics bay (the base) ──────────────────────────────────────
    floor = WALL
    tray, board, header = c.pi_zero(15.0, 15.0, floor)
    add("Pi_Tray", tray, c.PRINT_BLACK, "Electronics_Bay")
    add("Pi_Zero_2W", board, c.PCB_GREEN, "Electronics_Bay")
    add("Pi_GPIO_Header", header, c.MATTE_BLACK, "Electronics_Bay")
    t = floor + 1.0
    add("MAX98357A_Amp", box(108, 18, t, 125.8, 37.4, t + 1.6), c.PCB_BLUE, "Electronics_Bay")
    add("DS3231_ZS042", box(104, 40, t, 126, 78, t + 1.6), c.PCB_BLUE, "Electronics_Bay")
    add("RTC_Battery_Holder", zcyl(10.5, t + 1.6, t + 8.6, 115.0, 65.0), c.MATTE_BLACK, "Electronics_Bay")
    add("MOSFET_Dimmer_2ch", box(50, 60, t, 68, 77, t + 1.6), c.PCB_BLUE, "Electronics_Bay")
    add("Mount_Tape", fuse_all([box(108, 18, floor, 125.8, 37.4, t), box(104, 40, floor, 126, 78, t),
                                box(50, 60, floor, 68, 77, t)]), (0.85, 0.85, 0.80), "Electronics_Bay")

    ry0 = REAR_REBATE_Y + GASKET_T
    ry1 = ry0 + REAR_T
    usb_x, usb_z0 = 85.5, floor + 3.0
    sock_z0 = usb_z0 + 1.6
    add("USBC_Saddle", box(usb_x - 5.5, 66, floor, usb_x + 5.5, REAR_REBATE_Y - 0.5, usb_z0), c.PRINT_BLACK, "Electronics_Bay")
    add("USBC_Breakout", box(usb_x - 5.5, 67, usb_z0, usb_x + 5.5, REAR_REBATE_Y - 0.2, sock_z0), c.PCB_BLACK, "Electronics_Bay")
    add("USBC_Socket", box(usb_x - 4.5, ry1 - 7.4, sock_z0, usb_x + 4.5, ry1 - 0.3, sock_z0 + 3.3), c.ALUMINIUM, "Electronics_Bay")

    # ── Rear panel and gasket ───────────────────────────────────────────
    gasket = arch_prism(WALL - rr, W - WALL + rr, WALL - rr, REAR_REBATE_Y, ry0).cut(
        arch_prism(WALL, W - WALL, WALL, REAR_REBATE_Y - 1, ry0 + 1))
    add("Rear_Gasket", gasket.fuse(box(WALL, REAR_REBATE_Y, DIV_Z0 + 1, W - WALL, ry0, DIV_Z1 - 1)).removeSplitter(),
        c.FOAM, "Cabinet")
    rear = arch_prism(WALL - rr + FIT, W - WALL + rr - FIT, WALL - rr + FIT, ry0, ry1)
    rear = rear.cut(box(usb_x - 5.0, ry0 - 1, sock_z0 - 0.3, usb_x + 5.0, ry1 + 1, sock_z0 + 3.6))
    for i in range(5):
        vx = 95.0 + i * 7.0
        rear = rear.cut(box(vx, ry0 - 1, 22.0, vx + 3.0, ry1 + 1, 44.0))
    add("Rear_Panel", rear, BIRCH_PLY, "Cabinet")

    add("Felt_Feet", fuse_all([zcyl(7, -2, 0, x, y) for x, y in [(18, 15), (132, 15), (18, 79), (132, 79)]]),
        (0.25, 0.25, 0.25), "Cabinet")

    bld.doc.recompute()

    chamber = arch_prism(WALL, W - WALL, WALL, BAFFLE_Y1, REAR_REBATE_Y).common(
        box(0, 0, DIV_Z1, W, D, 400))
    for label in ("Driver_PC83_4", "Driver_Cone", "Driver_Gasket"):
        chamber = chamber.cut(bld.doc.getObjectsByLabel(label)[0].Shape)
    net_l = chamber.Volume / 1e6
    qtc, fc = c.sealed_box_alignment(net_l * c.WADDING_FACTOR)
    bld.doc.Comment = (f"Sunrise · {W:.0f}w x {SPRING + W / 2:.0f}h x {D:.0f}d mm · sealed chamber {net_l:.3f}L net "
                       f"· Qtc {qtc:.2f} · fc {fc:.0f}Hz")
    App.Console.PrintMessage(bld.doc.Comment + "\n")
    bld.doc.saveAs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Sunrise.FCStd"))
    return bld


if __name__ in ("__main__", "sunrise"):
    main()
