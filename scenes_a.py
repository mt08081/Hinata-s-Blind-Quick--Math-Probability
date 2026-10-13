"""scenes_a.py - cold open through the perfect-world solution."""
import math
import numpy as np
import skia
from engine import *
from registry import scene
from common import *
import world as wd
import freak_quick_model as fq

# =====================================================================================
# 01  COLD OPEN
# =====================================================================================
OPEN_MAP = TimeMap([(0.0, -1.32), (1.7, -0.32), (2.3, -0.10), (4.1, 0.12), (5.6, 0.30),
                    (6.3, T_HIT), (7.1, T_HIT + 0.0004), (7.9, 0.47), (9.0, 0.66)])


def OPEN_MAP_INV(tp):
    xs = np.linspace(0, 9.0, 2701)
    vals = np.array([OPEN_MAP(x) for x in xs])
    return float(xs[np.argmin(np.abs(vals - tp))])
CAM_A = Camera((4.6, -10.6, 3.5), (-0.6, -1.0, 1.7), fov=38)
CAM_B = Camera((0.6, -6.6, 3.0), (-1.7, -0.7, 2.45), fov=40)
CAM_C = Camera((-0.4, -4.4, 3.2), (-2.0, -0.5, 2.85), fov=36)


CAM_D = Camera((-0.7, -4.3, 3.0), (-2.1, 1.9, 0.5), fov=46)


def _landing_tp():
    b = nominal_ball()
    for x in np.arange(T_HIT, T_HIT + 0.6, 0.002):
        if b.pos(x)[2] <= wd.R_BALL + 1e-3:
            return x
    return T_HIT + 0.16


TP_LAND = _landing_tp()


def _open_cam(s):
    if s < 3.0:
        return cam_lerp(CAM_A, CAM_B, ease_io(seg(s, 0.4, 3.0)))
    if s < 6.3:
        return cam_lerp(CAM_B, CAM_C, ease_io(seg(s, 3.0, 6.3)))
    if s < 7.15:
        k = ease_out(seg(s, 6.3, 6.5))
        return Camera(CAM_C.pos, CAM_C.target, fov=lerp(36, 30, k))
    c30 = Camera(CAM_C.pos, CAM_C.target, fov=30)
    return cam_lerp(c30, CAM_D, ease_io(seg(s, 7.15, 7.75)))


@scene("01_cold_open", 16.0, events=[(0.0, "riser", 0.5), (1.05, "squeak", 0.6), (2.15, "stomp", 0.9),
                                     (2.45, "eye", 0.7), (3.2, "whoosh", 0.7), (6.3, "impact", 1.0),
                                     (8.05, "stomp", 1.0), (9.2, "hit_text", 0.6), (10.6, "hit_text", 0.6),
                                     (12.0, "hit_text", 0.6), (13.5, "slam", 0.9), (14.8, "slam", 0.7)])
def s01(fr, s):
    tp = OPEN_MAP(s)
    background(fr, s)
    cam = _open_cam(s)
    s_land = OPEN_MAP_INV(TP_LAND)
    dx, dy = shake_offset(s, 6.3, 0.5, 22)
    dx2, dy2 = shake_offset(s, s_land, 0.35, 14, seed=3)
    fr.c.save(); fr.c.translate(dx + dx2, dy + dy2)
    # speed lines behind the run
    if s < 2.2:
        speed_lines(fr, s, center=(W * 0.3, H * 0.55), n=40, radial=False, direction=(-0.25, 1), alpha=0.10 * fade(s, 0.3, 2.2),
                    width=(1, 3))
    P = draw_play(fr, cam, tp, trail=0.12 if 0 < tp < T_HIT else 0.0, ball_glow="#ffffff")
    # take-off dust ring
    if T_TO - 0.02 < tp < T_TO + 0.25:
        k = (tp - T_TO + 0.02) / 0.27
        foot = np.array([PLAN.takeoff[0], PLAN.takeoff[1], 0.0])
        sc, z = cam.project(np.array([foot]))
        rr = 30 + 160 * ease_out(k)
        fr.c.save(); fr.c.translate(*sc[0]); fr.c.scale(1, 0.3)
        fr.circle((0, 0), rr, "#ffffff", (1 - k) * 0.7, stroke=6 * (1 - k) + 1)
        fr.c.restore()
        if k < 0.6:
            sfx_text(fr, "ダンッ", sc[0][0] - 170, sc[0][1] + 10, (tp - T_TO + 0.02) * 4, size=70, rot=-6, alpha=1 - k / 0.6)
    # radial focus lines as the hand closes in
    if 4.6 < s < 6.3:
        pc, _ = cam.project(np.array([PLAN.target]))
        speed_lines(fr, s, center=pc[0], n=70, alpha=0.32 * seg(s, 4.6, 6.0), inner=200, width=(1.5, 4))
    fr.c.restore()
    # eye cut-in panel
    if 2.35 < s < 4.25:
        a = fade(s, 2.35, 4.25, 0.15, 0.2)
        x0 = W - 760 + (1 - ease_out(seg(s, 2.35, 2.6))) * 300
        pts = slanted_panel(fr, x0, 120, 640, 330, slant=70, alpha=a)
        clip_poly(fr, pts)
        sk = skia.GradientShader.MakeLinear([skia.Point(x0, 120), skia.Point(x0 + 640, 450)],
                                            [hexc("#f1ddd0"), hexc("#d9b9a6")])
        fr.rect(x0, 120, 640, 330, "#e7d6cb", a, shader=sk)
        screentone(fr, 0.10 * a, 11, 1.8, "#b38f7d", region=(x0, 330, 640, 120))
        draw_eye(fr, x0 + 330, 315, 380, close=ease_io(seg(s, 2.9, 3.35)), alpha=a)
        # hair fringe across the top of the panel
        for kk in range(9):
            hx = x0 + 40 + kk * 72
            tip = 205 + 40 * math.sin(kk * 1.7)
            fr.polygon([(hx - 50, 110), (hx + 46, 110), (hx + 12, tip)], PAL["hair"], a)
            fr.line((hx - 8, 118), (hx + 8, tip - 20), 3, "#3a4470", a * 0.8)
        speed_lines(fr, s, center=(x0 + 320, 300), n=30, color="#ffffff", alpha=0.22 * a, inner=230, width=(1, 3))
        fr.c.restore()
        fr.text("eyes: closed", x0 + 120, 500, 30, "semi", PAL["ink"], a * seg(s, 3.2, 3.5), stroke=4,
                stroke_color=PAL["bg0"])
    # release streak SFX
    if 0.0 < tp < 0.09:
        rp, _ = cam.project(np.array([PLAN.r0]))
        sfx_text(fr, "シュッ", rp[0][0] - 60, rp[0][1] + 120, (tp) * 9, size=64, rot=8, color=PAL["setter"], alpha=1 - tp / 0.09)
    # spiked ball hits the floor
    if s_land <= s < s_land + 0.9:
        u = (s - s_land) / 0.9
        land = nominal_ball().pos(TP_LAND); land[2] = 0.0
        sc, _ = cam.project(np.array([land]))
        fr.c.save(); fr.c.translate(*sc[0]); fr.c.scale(1, 0.32)
        for kk in range(3):
            rr = (40 + 260 * ease_out(u)) * (1 + 0.35 * kk)
            fr.circle((0, 0), rr, "#ffffff", (1 - u) * (0.75 - 0.2 * kk), stroke=10 * (1 - u) + 1)
        fr.c.restore()
        speed_lines(fr, s, center=sc[0], n=50, alpha=0.35 * (1 - u), inner=120, width=(1.5, 4), seed=21)
        sfx_text(fr, "ドンッ!", sc[0][0] + 40, sc[0][1] - 170, s - s_land, size=150, rot=7, color="#ffffff",
                 outline=PAL["spiker"], alpha=1 - ease_in(u))
    # impact frame
    if 6.3 <= s < 7.15:
        u = (s - 6.3) / 0.85
        pc, _ = cam.project(np.array([PLAN.target]))
        if s < 6.37:
            flash(fr, 1.0)
        elif s < 6.75:
            invert(fr, 1.0)
            speed_lines(fr, s, center=pc[0], n=110, color="#000000", alpha=0.85, inner=130, width=(2, 7), seed=9)
            impact_burst(fr, pc[0], (s - 6.37) / 0.6, 1.4, "#000000")
        else:
            impact_burst(fr, pc[0], (s - 6.37) / 0.8, 1.4, "#ffffff")
        sfx_text(fr, "バシッ!!", pc[0][0] - 330, pc[0][1] - 40, s - 6.37, size=190, rot=-10,
                 color="#ffffff" if s >= 6.75 else "#000000", outline=PAL["spiker"] if s >= 6.75 else "#ffffff")
    # post-impact text beats
    if s > 8.7:
        darken(fr, 0.62 * ease_io(seg(s, 8.7, 9.2)))
        screentone(fr, 0.05 * seg(s, 8.7, 9.4), 16, 2.2, "#ffffff")
        lines = [(9.2, 10.5, "He never looks at the ball.", PAL["ink"]),
                 (10.6, 11.9, "His eyes are closed.", PAL["spiker"]),
                 (12.0, 13.4, "And the ball still finds his palm. Every time.", PAL["ink"])]
        for t0, t1, txt, col in lines:
            if t0 <= s < t1:
                a = fade(s, t0, t1, 0.15, 0.25)
                slam_text(fr, txt, W / 2, H / 2 + 20, s - t0, size=72, color=col, accent=PAL["outline"], dur=0.25)
                fr.c.save(); fr.c.restore()
                if a < 1:
                    fr.rect(0, 0, W, H, "#03050c", (1 - a) * 0.0)
        if s >= 13.5:
            a = 1 - ease_io(seg(s, 15.6, 16.0))
            slam_text(fr, "Is that physically possible?", W / 2, H / 2 - 30, s - 13.5, size=96,
                      color=PAL["hi"], accent=PAL["spiker"], dur=0.3)
            if s >= 14.8:
                fr.text("Let's do the math.", W / 2, H / 2 + 80, 52, "xboldit", PAL["ink"], a * ease_out(seg(s, 14.8, 15.1)),
                        "center")
            if a < 1:
                fr.rect(0, 0, W, H, "#03050c", 1 - a)
    letterbox(fr, 1.0 - ease_io(seg(s, 7.6, 8.4)) * 0.0 if s < 8.0 else 1.0)
    if s < 0.35:
        fr.rect(0, 0, W, H, "#000000", 1 - s / 0.35)


# =====================================================================================
# 02  TITLE
# =====================================================================================
@scene("02_title", 5.5, events=[(0.05, "slam", 1.0), (0.55, "slam", 0.6), (1.2, "beat_in", 1.0)])
def s02(fr, s):
    background(fr, s, 0.4, "#2a1440")
    speed_lines(fr, s, center=(W / 2, H / 2), n=120, alpha=0.18, inner=420, width=(1.5, 5))
    screentone(fr, 0.07, 15, 2.4, "#ffffff")
    # big ghost ball behind the title
    cx, cy = W / 2 + 420, H / 2 - 40
    r = 260 + 10 * math.sin(s * 2)
    fr.circle((cx, cy), r, "#ffffff", 0.05)
    fr.circle((cx, cy), r, "#ffffff", 0.25, stroke=4)
    for k in range(3):
        a = s * 0.3 + k * 2.1
        fr.c.save(); fr.c.translate(cx, cy); fr.c.rotate(math.degrees(a))
        pth = skia.Path(); pth.moveTo(-r, 0); pth.quadTo(0, r * 0.8, r, 0)
        fr.c.drawPath(pth, fr.paint("#ffffff", 0.18, stroke=3)); fr.c.restore()
    slam_text(fr, "THE BLIND", W / 2 - 60, H / 2 - 40, s, size=170, color=PAL["ink"], accent=PAL["spiker"])
    slam_text(fr, "QUICK", W / 2 + 120, H / 2 + 130, s - 0.5, size=210, color=PAL["hi"], accent=PAL["setter"])
    a = ease_out(seg(s, 1.1, 1.6))
    fr.text("The physics of hitting a ball you can't see", W / 2, H / 2 + 250, 44, "semi", PAL["ink"], a, "center")
    fr.text("a minus-tempo spike, eyes closed  ·  modelled, simulated, measured", W / 2, H / 2 + 305, 30, "med",
            PAL["ink2"], ease_out(seg(s, 1.5, 2.0)), "center")
    slash_wipe(fr, s - 5.05, 0.45, PAL["setter"])
    if s < 0.12:
        flash(fr, 1 - s / 0.12)


# =====================================================================================
# 03  RULES OF OUR UNIVERSE (assumptions)
# =====================================================================================
RULES = [
    ("PERFECT PASS", "every rep starts identical", PAL["setter"]),
    ("SETTER PLANTED", "same release spot, hands 2.35 m up", PAL["setter"]),
    ("REGULATION BALL", "270 g, 21 cm wide, never deforms", PAL["hi"]),
    ("STILL AIR, SEA LEVEL", "air density 1.2 kg/m³", PAL["hi"]),
    ("EMPTY COURT", "no blockers, no teammates", PAL["ink"]),
    ("9 × 9 m HALF COURT", "net top at 2.43 m (men's height)", PAL["ink"]),
    ("HE ALWAYS JUMPS & SWINGS", "unconditionally, every time", PAL["spiker"]),
    ("NO PEEKING", "after take-off: no corrections at all", PAL["spiker"]),
]


@scene("03_rules", 17.0, events=[(0.2, "whoosh", 0.5)] + [(1.3 + 1.35 * i, "tick", 0.6) for i in range(8)] +
       [(13.4, "chime", 0.7)])
def s03(fr, s):
    background(fr, s)
    screentone(fr, 0.035, 18, 2.2, "#ffffff")
    section_tag(fr, "01", "THE RULES OF OUR UNIVERSE", s)
    fr.text("Simplifications we lock in — so only the interesting physics is left.", 70, 160, 34, "med", PAL["ink2"],
            ease_out(seg(s, 0.4, 0.9)))
    for i, (h, sub, col) in enumerate(RULES):
        t0 = 1.3 + 1.35 * i
        k = ease_out(seg(s, t0, t0 + 0.35))
        if k <= 0:
            continue
        col_i, row = i % 2, i // 2
        x = 90 + col_i * 880 + (1 - k) * 60
        y = 250 + row * 160
        fr.rect(x, y, 820, 128, "#0d1430", 0.85 * k, radius=16)
        fr.rect(x, y, 10, 128, col, k, radius=4)
        fr.text("%d" % (i + 1), x + 50, y + 82, 54, "dblackit", col, k * 0.9, "center")
        fr.text(h, x + 100, y + 58, 36, "black", PAL["ink"], k)
        fr.text(sub, x + 100, y + 100, 28, "med", PAL["ink2"], k)
    if s > 13.3:
        a = ease_out(seg(s, 13.3, 13.8))
        fr.text("Everything else is physics…", W / 2, 935, 46, "xboldit", PAL["ink"], a, "center")
        fr.text("…and human noise.", W / 2, 995, 46, "xboldit", PAL["spiker"], ease_out(seg(s, 14.2, 14.7)), "center")
    slash_wipe(fr, s - 16.55, 0.45, PAL["hi"])


# =====================================================================================
# 04  COORDINATES & TIMELINE
# =====================================================================================
CAM_COORD = Camera((5.2, -8.8, 5.0), (-0.6, -1.0, 1.2), fov=40)


def _arrow3d(fr, cam, P0, P1, color, label, alpha, w=6):
    s, z = cam.project(np.array([P0, P1]))
    if (z < 0.2).any():
        return
    fr.line(s[0], s[1], w, color, alpha, glow=6)
    d = s[1] - s[0]; d = d / (np.linalg.norm(d) + 1e-9); n = np.array([-d[1], d[0]])
    fr.polygon([s[1] + d * 22, s[1] - d * 6 + n * 13, s[1] - d * 6 - n * 13], color, alpha)
    fr.text(label, s[1][0] + d[0] * 40, s[1][1] + d[1] * 40 + 14, 40, "dblackit", color, alpha, "center",
            stroke=5, stroke_color=PAL["bg0"])


@scene("04_coords", 14.0, events=[(0.3, "whoosh", 0.5), (1.4, "pop", 0.6), (2.0, "pop", 0.6), (2.6, "pop", 0.6),
                                  (4.6, "pop", 0.7), (5.6, "pop", 0.7), (8.0, "tick", 0.6), (9.3, "tick", 0.6),
                                  (10.6, "tick", 0.6)])
def s04(fr, s):
    background(fr, s)
    cam = CAM_COORD
    a_world = ease_out(seg(s, 0.0, 0.6))
    with fr.layer(a_world):
        wd.draw_court(fr, cam)
        tp = -0.25 if s < 4.0 else lerp(-0.25, -0.05, seg(s, 4.0, 4.5))
        Js = wd.spiker_pose(NOM, T_TO - 0.001)
        wd.draw_athlete(fr, cam, wd.setter_pose(-0.2), PAL["setter"], glow=PAL["setter"], alpha=0.85)
        wd.draw_athlete(fr, cam, Js, PAL["spiker"], glow=PAL["spiker"], alpha=0.85)
    section_tag(fr, "02", "WHERE & WHEN", s)
    O = np.zeros(3)
    k1, k2, k3 = (ease_out(seg(s, 1.3 + 0.6 * i, 1.8 + 0.6 * i)) for i in range(3))
    _arrow3d(fr, cam, O, O + np.array([2.2 * k1 + 1e-3, 0, 0]), PAL["hi"], "x", k1)
    _arrow3d(fr, cam, O, O + np.array([0, -2.2 * k2 - 1e-3, 0]), PAL["setter"], "−y", k2)
    _arrow3d(fr, cam, O, O + np.array([0, 0, 2.0 * k3 + 1e-3]), PAL["spiker"], "z", k3)
    if 1.3 < s < 7.6:
        a = fade(s, 1.3, 7.6, 0.4, 0.4)
        fr.rect(60, 860, 900, 130, "#060914", 0.82 * a, radius=16)
        fr.text("origin: on the floor, under the middle of the net", 90, 912, 32, "semi", PAL["ink"], a)
        fr.text("x along the net  ·  y toward the net  ·  z up   (metres)", 90, 958, 28, "med", PAL["ink2"], a)
    # key points
    if s > 4.5:
        a = ease_out(seg(s, 4.5, 5.0))
        label_at(fr, cam, PLAN.r0, "release  R₀ = (1.00, −0.70, 2.35)", PAL["setter"], dx=40, dy=-60, size=30, alpha=a)
    if s > 5.5:
        a = ease_out(seg(s, 5.5, 6.0))
        label_at(fr, cam, PLAN.target, "contact  C = (−2.00, −0.45, 2.94)", PAL["spiker"], dx=50, dy=-120, size=30,
                 alpha=a)
        pts = np.array([PLAN.r0, PLAN.target])
        world_path(fr, cam, pts, PAL["ink2"], 2, a * 0.8, glow=0, dash=(12, 10))
        mid, _ = cam.project(np.array([0.5 * (PLAN.r0 + PLAN.target)]))
        fr.text("3.0 m apart", mid[0][0], mid[0][1] + 52, 30, "bold", PAL["ink"], a, "center", stroke=4,
                stroke_color=PAL["bg0"])
    # timeline
    if s > 7.2:
        a = ease_out(seg(s, 7.2, 7.7))
        x0, x1, y = 260, 1660, 900
        tmin, tmax = -0.12, 0.40
        X = lambda tt: x0 + (tt - tmin) / (tmax - tmin) * (x1 - x0)
        fr.rect(x0 - 40, y - 150, x1 - x0 + 80, 230, "#070b18", 0.85 * a, radius=18)
        fr.line((x0, y), (x1, y), 4, PAL["ink3"], a)
        for tt in np.arange(-0.1, 0.41, 0.05):
            fr.line((X(tt), y - 8), (X(tt), y + 8), 2, PAL["ink3"], a)
        fr.text("time (s)", x1 + 20, y + 8, 24, "med", PAL["ink2"], a)
        marks = [(8.0, T_TO, "spiker leaves the floor", "t = −0.048 s", PAL["spiker"], -1),
                 (9.3, 0.0, "ball leaves the setter", "t = 0", PAL["setter"], 1),
                 (10.6, T_HIT, "hand meets ball", "t = +0.34 s", PAL["hi"], -1)]
        for t0, tt, lab, val, col, side in marks:
            k = ease_out(seg(s, t0, t0 + 0.35))
            if k <= 0:
                continue
            xx = X(tt)
            fr.circle((xx, y), 12 * k, col, a)
            fr.line((xx, y), (xx, y + side * 58), 3, col, a * k)
            yy = y + side * 70 + (8 if side < 0 else 30)
            fr.text(lab, xx, yy - (26 if side < 0 else 0), 28, "bold", col, a * k, "center")
            fr.text(val, xx, yy + (8 if side < 0 else 34), 26, "med", PAL["ink"], a * k, "center")
        if s > 11.6:
            k = ease_out(seg(s, 11.6, 12.0))
            fr.rect(X(T_TO), y - 6, X(0) - X(T_TO), 12, PAL["hi"], k)
            fr.rect(W / 2 - 520, 650, 1040, 70, "#060914", 0.9 * k, radius=35)
            chip(fr, "MINUS TEMPO: he is airborne 48 ms BEFORE the set", W / 2, 698, PAL["hi"], k, size=30,
                 align="center")
    slash_wipe(fr, s - 13.55, 0.45, PAL["setter"])


# =====================================================================================
# 05  THE BALL
# =====================================================================================
CAM_BALL = Camera((0.2, -4.6, 3.1), (-0.6, -0.55, 2.75), fov=40)
_AIR_PTS = None


def air_points():
    global _AIR_PTS
    if _AIR_PTS is None:
        ts = np.linspace(1e-4, T_HIT, 60)
        p, _ = fq.ball_endpoint(np.repeat(PLAN.r0[None], len(ts), 0), np.repeat(PLAN.v0_vac[None], len(ts), 0),
                                None, ts, wd.M.ball)
        _AIR_PTS = p
    return _AIR_PTS


def _ball_cam(s):
    ball = nominal_ball()
    tp = lerp(0.05, 0.20, ease_io(seg(s, 0.0, 11.2)))
    P, _ = ball.flight(tp)
    close = Camera(P + np.array([0.75, -2.5, 0.25]), P + np.array([0.0, 0.0, 0.05]), fov=40)
    if s < 11.2:
        return close, tp
    return cam_lerp(close, CAM_BALL, ease_io(seg(s, 11.2, 12.4))), tp


@scene("05_ball", 21.0, events=[(0.3, "whoosh", 0.5), (1.2, "pop", 0.6), (2.2, "pop", 0.6), (3.2, "pop", 0.6),
                                (5.0, "chime", 0.5), (11.4, "whoosh", 0.6), (14.2, "buzz", 0.8), (17.4, "tick", 0.6)])
def s05(fr, s):
    background(fr, s)
    cam, tp_show = _ball_cam(s)
    ball = nominal_ball()
    wd.draw_court(fr, cam, alpha=0.8)
    pts = np.array([ball.pos(x) for x in np.linspace(0, T_HIT, 60)])
    ba = 1 - ease_io(seg(s, 11.6, 12.3))
    world_path(fr, cam, pts, PAL["setter"], 3, 0.55 * ba, glow=0)
    P, V = ball.flight(tp_show)
    sb = wd.draw_ball(fr, cam, P, glow="#ffffff", rot=tp_show * 3.0, alpha=ba)
    if sb is None:
        s2_, _ = cam.project(np.array([P]))
        sb = (s2_[0], 10.0)
    section_tag(fr, "03", "THE BALL", s)
    if sb is None:
        return
    c, r = sb
    vhat = V / np.linalg.norm(V)
    wN = R["plan"]["weight"]
    spd = np.linalg.norm(V)
    dN = 0.5 * 1.2 * 0.45 * np.pi * 0.105 ** 2 * spd ** 2
    fa = 1 - ease_io(seg(s, 10.8, 11.3))

    def arrow(vec_world, color, label, val, k, L, offset=(0, 0)):
        if k <= 0:
            return
        s2, _ = cam.project(np.array([P, P + vec_world]))
        d = s2[1] - s2[0]
        d = d / (np.linalg.norm(d) + 1e-9)
        a0 = c + d * r * 1.08
        a1 = a0 + d * L * k
        fr.line(a0, a1, 8, color, k, glow=6)
        n = np.array([-d[1], d[0]])
        fr.polygon([a1 + d * 26, a1 + n * 15, a1 - n * 15], color, k)
        lx, ly = a1[0] + d[0] * 60 + offset[0], a1[1] + d[1] * 60 + offset[1]
        fr.text(label, lx, ly, 36, "black", color, k, "center", stroke=5, stroke_color=PAL["bg0"])
        fr.text(val, lx, ly + 38, 28, "semi", PAL["ink"], k, "center", stroke=4, stroke_color=PAL["bg0"])

    arrow(np.array([0, 0, -1.0]), PAL["ink"], "gravity", "%.2f N" % wN, ease_out(seg(s, 1.0, 1.5)) * fa, 190)
    arrow(-vhat, PAL["bad"], "drag", "%.2f N" % dN, ease_out(seg(s, 2.0, 2.5)) * fa, 190 * dN / wN, offset=(0, -6))
    arrow(np.array([0, 0, 1.0]), PAL["setter"], "Magnus", "only if it spins", ease_out(seg(s, 3.0, 3.5)) * fa, 70,
          offset=(90, -10))
    if 4.6 < s:
        a = ease_out(seg(s, 4.6, 5.2))
        fr.rect(60, 140, 870, 340, "#060914", 0.85 * a, radius=18)
        fr.text("Newton's 2nd law for the ball", 90, 190, 30, "bold", PAL["hi"], a)
        fr.eq(r"$m\,\dot{\vec v} = m\vec g \;-\; \frac{1}{2}\rho C_D A\,|\vec v|\,\vec v \;+\; \frac{1}{2}\rho C_L A\,|\vec v|^2\,(\hat\omega\times\hat v)$",
              85, 220, 40, alpha=a)
        fr.text("m = 0.27 kg   A = 0.035 m²   ρ = 1.2 kg/m³", 90, 350, 26, "med", PAL["ink2"], a)
        fr.text("set speed ≈ 10 m/s → below the drag crisis (~14 m/s)", 90, 390, 26, "med", PAL["ink2"], a)
        fr.text("→ C_D ≈ 0.45:  drag ≈ %d%% of the ball's weight" % round(100 * dN / wN), 90, 432, 28, "bold",
                PAL["ink"], a)
    # vacuum vs air demo
    if s > 12.2:
        k = ease_io(seg(s, 12.4, 14.0))
        vac = [PLAN.r0 + PLAN.v0_vac * x + 0.5 * np.array([0, 0, -9.81]) * x * x for x in np.linspace(0, T_HIT, 50)]
        world_path(fr, cam, vac, PAL["ink"], 3, 0.9, glow=0, dash=(10, 10), reveal=k)
        world_path(fr, cam, air_points(), PAL["bad"], 5, 1.0, glow=8, reveal=k)
        a0 = ease_out(seg(s, 12.2, 12.6))
        fr.rect(70, 760, 860, 230, "#060914", 0.85 * a0, radius=18)
        fr.text("Same launch, two worlds:", 100, 815, 32, "bold", PAL["ink"], a0)
        fr.text("- - -  no air (textbook parabola)", 100, 865, 28, "semi", PAL["ink"], ease_out(seg(s, 12.4, 12.8)))
        fr.text("——  real air", 100, 905, 28, "semi", PAL["bad"], ease_out(seg(s, 12.6, 13.0)))
        if s > 14.2:
            miss = R["plan"]["vacuum_miss_dist"] * 100
            a = ease_out(seg(s, 14.2, 14.6))
            pt, _ = cam.project(np.array([PLAN.target]))
            fr.circle(pt[0], 22, PAL["hi"], a, stroke=4)
            fr.text("Ignore the air → miss by %.0f cm" % miss, 100, 960, 34, "black", PAL["hi"], a)
    if s > 17.2:
        a = ease_out(seg(s, 17.2, 17.7))
        sp = R["plan"]["spin1rps_miss_dist"] * 100
        fr.rect(1010, 760, 860, 150, "#060914", 0.85 * a, radius=18)
        fr.text("Spin matters too:", 1040, 815, 30, "bold", PAL["setter"], a)
        fr.text("just 1 revolution/second of spin → %.0f cm off" % sp, 1040, 860, 28, "semi", PAL["ink"], a)
    slash_wipe(fr, s - 20.55, 0.45, PAL["spiker"])


# =====================================================================================
# 06  THE SPIKER
# =====================================================================================
CAM_SIDE = Camera((-8.6, -1.05, 2.05), (-2.35, -1.05, 1.95), fov=42)


@scene("06_spiker", 22.0, events=[(0.3, "whoosh", 0.5), (1.0, "stomp", 0.6), (6.0, "pop", 0.6), (10.0, "whoosh", 0.7),
                                  (12.6, "whoosh", 0.8), (17.0, "chime", 0.6)])
def s06(fr, s):
    background(fr, s)
    section_tag(fr, "04", "THE SPIKER", s)
    cam = CAM_SIDE
    wd.draw_court(fr, cam)
    # phase A (0-9 s): jump in slow motion, trace the centre-of-mass parabola
    if s < 9.5:
        tp = lerp(T_TO - 0.1, T_TO + 0.42, ease_io(seg(s, 0.8, 7.0)))
    elif s < 12.0:
        tp = lerp(T_HIT - 0.17, T_HIT - 0.17, 0)
    else:
        tp = lerp(T_HIT - 0.17, T_HIT + 0.07, ease_io(seg(s, 12.5, 16.5)))
    J = wd.spiker_pose(NOM, tp)
    wd.draw_athlete(fr, cam, J, PAL["spiker"], glow=PAL["spiker"], highlight_arm=PAL["hi"] if s > 9.8 else None)
    # COM parabola
    ts = np.linspace(T_TO, T_TO + 0.774, 80)
    com = np.array([wd._ballistic_com(NOM, x) for x in ts])
    reveal = seg(tp, T_TO, T_TO + 0.774) if s < 9.5 else 1.0
    if s > 0.8:
        world_path(fr, cam, com, PAL["hi"], 3, 0.9 * (1 - 0.6 * seg(s, 9.5, 10.5)), glow=0, dash=(12, 9), reveal=max(0.02, reveal))
        cpos, _ = cam.project(np.array([wd._ballistic_com(NOM, max(tp, T_TO))]))
        if s < 9.5:
            fr.circle(cpos[0], 9, PAL["hi"], 1.0)
    if 2.5 < s < 10.2:
        a = fade(s, 2.5, 10.2, 0.4, 0.4)
        fr.rect(1060, 150, 800, 300, "#060914", 0.82 * a, radius=18)
        fr.text("After take-off he is a projectile", 1090, 205, 32, "bold", PAL["hi"], a)
        fr.eq(r"$z(t)=z_0+v_z\,t-\frac{1}{2}g\,t^2$", 1090, 235, 46, alpha=a)
        fr.text("v_z = 3.80 m/s  →  rises 0.74 m in 0.39 s", 1090, 360, 28, "semi", PAL["ink"], a)
        fr.text("His path is fixed the instant he leaves the floor.", 1090, 410, 28, "med", PAL["ink2"], a)
    # phase B: the arm chain
    if s > 10.0:
        a = ease_out(seg(s, 10.0, 10.6))
        fr.rect(1060, 150, 800, 420, "#060914", 0.82 * a, radius=18)
        fr.text("The arm: three rigid links", 1090, 205, 32, "bold", PAL["hi"], a)
        fr.text("shoulder θ  ·  elbow β  ·  wrist γ", 1090, 250, 28, "semi", PAL["ink"], a)
        fr.eq(r"$\vec p(t)=\vec s+L_1\hat e(\theta)+L_2\hat e(\theta-\beta)+L_3\hat e(\theta-\beta+\gamma)$", 1080, 280,
              34, alpha=a)
        fr.text("joint angles follow measured spike swings", 1090, 400, 26, "med", PAL["ink2"], a)
        fr.text("(shoulder ~720°/s, elbow ~1200°/s)", 1090, 436, 26, "med", PAL["ink2"], a)
        # palm swept arc (physics model) up to current time
        tt = np.linspace(T_HIT - 0.17, max(T_HIT - 0.169, tp), 70)
        kin = fq.hitter_kinematics(wd._hs(NOM), tt, wd.M.body)
        palm = kin["palm"][0]
        if s > 12.4:
            world_path(fr, cam, palm, PAL["spiker"], 6, 1.0, glow=10)
    if s > 16.6:
        a = ease_out(seg(s, 16.6, 17.1))
        v = R["plan"]["palm_speed"]
        big_number(fr, "%.1f m/s" % v, 1460, 690, 96, PAL["spiker"], a)
        fr.text("palm speed at contact  (≈ %.0f km/h)" % (v * 3.6), 1460, 760, 30, "semi", PAL["ink"], a, "center")
    slash_wipe(fr, s - 21.55, 0.45, PAL["hi"])


# =====================================================================================
# 07  THE PERFECT WORLD (inverse problem)
# =====================================================================================
CAM_PW = Camera((2.9, -7.6, 4.1), (-0.6, -0.7, 2.2), fov=36)
NEWTON = [np.array(v) for v in R["plan"]["newton"]]
NEWTON_MISS = R["plan"]["newton_miss"]


def _traj(v0, T=T_HIT, n=50):
    pts = []
    for x in np.linspace(1e-4, T, n):
        p, _ = fq.ball_endpoint(PLAN.r0[None], v0[None], None, np.array([x]), wd.M.ball)
        pts.append(p[0])
    return np.array(pts)


_NEWTON_TRAJ = None


def newton_traj():
    global _NEWTON_TRAJ
    if _NEWTON_TRAJ is None:
        _NEWTON_TRAJ = [_traj(v) for v in NEWTON]
    return _NEWTON_TRAJ


PW_MAP = TimeMap([(15.2, -0.55), (16.4, -0.06), (18.2, 0.26), (19.2, T_HIT), (19.9, T_HIT + 0.0004), (20.6, 0.55)])


@scene("07_perfect", 24.0, events=[(0.3, "whoosh", 0.5), (3.2, "tick", 0.6), (5.0, "tick", 0.6), (6.6, "tick", 0.6),
                                   (8.2, "tick", 0.6), (9.6, "chime", 0.8), (19.2, "impact", 1.0), (20.4, "slam", 0.8)])
def s07(fr, s):
    background(fr, s)
    section_tag(fr, "05", "THE PERFECT WORLD", s)
    cam = CAM_PW
    if s < 15.0:
        wd.draw_court(fr, cam)
        J = wd.spiker_pose(NOM, T_HIT)
        wd.draw_athlete(fr, cam, wd.setter_pose(0.0), PAL["setter"], glow=PAL["setter"], alpha=0.8)
        wd.draw_athlete(fr, cam, J, PAL["spiker"], glow=PAL["spiker"], alpha=0.8)
        pt, _ = cam.project(np.array([PLAN.target]))
        pulse = 0.5 + 0.5 * math.sin(s * 6)
        fr.circle(pt[0], 26 + 6 * pulse, PAL["hi"], 0.9, stroke=4)
        a = ease_out(seg(s, 0.4, 0.9))
        fr.rect(50, 125, 1010, 420, "#060914", 0.8 * a, radius=18)
        fr.text("If nothing varies, it is a rendezvous problem:", 70, 170, 34, "semi", PAL["ink"], a)
        fr.text("find the launch velocity that puts the ball on the palm at t = 0.34 s.", 70, 215, 30, "med",
                PAL["ink2"], a)
        trajs = newton_traj()
        cols = [PAL["bad"], PAL["warn"], PAL["hi"]]
        for i, tr in enumerate(trajs[:3]):
            t0 = 2.8 + 2.0 * i
            if s < t0:
                continue
            k = ease_io(seg(s, t0, t0 + 0.9))
            last = (i == 2)
            al = 1.0 if (s < t0 + 2.0 or last) else 0.3
            world_path(fr, cam, tr, cols[i], 5 if last else 3, al, glow=8 if last else 0, reveal=k)
            miss = NEWTON_MISS[i] * 100
            txt = ("guess %d:  miss %.1f cm" % (i + 1, miss)) if miss >= 0.1 else ("guess %d:  miss < 1 mm" % (i + 1))
            fr.text(txt, 70, 340 + 54 * i, 36, "bold", cols[i], ease_out(seg(s, t0 + 0.8, t0 + 1.1)) * (1.0 if (last or s < t0 + 2.0) else 0.6))
        if s > 8.2:
            fr.text("converged: 2 corrections", 70, 520, 30, "semi", PAL["ink2"], ease_out(seg(s, 8.2, 8.6)))
        if s > 2.8:
            fr.text("shooting method: fly it, measure the miss, correct (Newton)", 70, 290, 26, "med", PAL["ink2"],
                    ease_out(seg(s, 2.8, 3.2)))
        if s > 9.4:
            a = ease_out(seg(s, 9.4, 9.9))
            fr.rect(1080, 640, 780, 340, "#060914", 0.85 * a, radius=18)
            fr.text("THE PERFECT SET", 1110, 700, 38, "black", PAL["hi"], a)
            fr.text("speed  %.1f m/s   ·   angle  %.1f° up" % (PLAN.speed, PLAN.elevation_deg), 1110, 752, 30,
                    "semi", PAL["ink"], a)
            fr.text("flight time  %.2f s" % T_HIT, 1110, 796, 30, "semi", PAL["ink"], a)
            fr.text("ball reaches its peak exactly at the palm:", 1110, 850, 28, "med", PAL["ink2"], a)
            fr.text("not rising, not falling → one less thing to time", 1110, 890, 28, "med", PAL["ink2"], a)
            fr.text("arrives at %.1f m/s, sideways across the hand" % R["plan"]["ball_speed_contact"], 1110, 934, 28,
                    "med", PAL["ink2"], a)
        if s > 14.5:
            fr.rect(0, 0, W, H, "#03050c", ease_io(seg(s, 14.5, 15.0)))
    else:
        tp = PW_MAP(s)
        camp = cam_lerp(Camera((3.2, -9.4, 3.8), (-0.5, -0.8, 1.9), fov=38),
                        Camera((0.3, -5.6, 3.3), (-1.8, -0.6, 2.6), fov=36), ease_io(seg(s, 15.2, 19.2)))
        dx, dy = shake_offset(s, 19.2, 0.4, 18)
        fr.c.save(); fr.c.translate(dx, dy)
        draw_play(fr, camp, tp, trail=0.12)
        fr.c.restore()
        if 15.3 < s < 20.3:
            ha = fade(s, 15.3, 20.3, 0.3, 0.3)
            fr.rect(W - 420, 120, 360, 110, "#060914", 0.8 * ha, radius=16)
            fr.text("t = %+.3f s" % tp, W - 400, 175, 44, "black", PAL["hi"], ha)
            fr.text("slow motion ×10", W - 400, 212, 24, "semi", PAL["ink2"], ha)
        if 19.2 <= s < 19.9:
            pc, _ = camp.project(np.array([PLAN.target]))
            if s < 19.27:
                flash(fr, 1.0)
            else:
                impact_burst(fr, pc[0], (s - 19.27) / 0.7, 1.2, "#ffffff")
            sfx_text(fr, "バシッ", pc[0][0] - 250, pc[0][1] - 30, s - 19.27, size=150, rot=-8)
        if s > 20.3:
            darken(fr, 0.55 * ease_io(seg(s, 20.3, 20.8)))
            slam_text(fr, "Perfect world: 100% success.", W / 2, H / 2, s - 20.4, size=86, color=PAL["good"],
                      accent=PAL["outline"])
            if s > 21.6:
                fr.text("But nobody jumps the same way twice.", W / 2, H / 2 + 90, 44, "xboldit", PAL["ink"],
                        ease_out(seg(s, 21.6, 22.0)), "center")
        if s < 15.4:
            fr.rect(0, 0, W, H, "#03050c", 1 - ease_io(seg(s, 15.0, 15.4)))
    slash_wipe(fr, s - 23.55, 0.45, PAL["spiker"])
