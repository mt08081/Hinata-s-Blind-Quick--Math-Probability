"""scenes_b.py - human noise, the contact window, Monte Carlo, requirements, levers, verdict."""
import math
import numpy as np
import skia
from engine import *
from registry import scene
from common import *
from charts import Axes, hbars, stacked_bar, seq_color
import world as wd
import freak_quick_model as fq

OUT_COL = {fq.CLEAN: PAL["good"], fq.PALM: PAL["palm"], fq.EDGE: PAL["warn"], fq.MISS: PAL["bad"]}
OUT_LAB = {fq.CLEAN: "SWEET SPOT", fq.PALM: "ON THE PALM", fq.EDGE: "FINGERTIPS / EDGE", fq.MISS: "WHIFF"}
OUT_ICON = {fq.CLEAN: "✓", fq.PALM: "✓", fq.EDGE: "!", fq.MISS: "✗"}
HSD = fq.HitterSD()
SSD = fq.SetterSD()


def _hs_arrays(prefix, idx=None):
    keys = ["x_to", "y_to", "t_to", "vx", "vy", "vz", "dt_swing", "alpha_c", "beta_c", "gamma_c", "tilt",
            "pitch_c", "pitch_rate", "wrist_rate", "omega_s", "yaw_body", "swing_az"]
    sl = slice(None) if idx is None else idx
    return {k: SMP[f"{prefix}_hs_{k}"][sl] for k in keys}


# palm positions of the blind attempts at the planned contact instant (open loop)
_HS_OPEN = _hs_arrays("open", slice(0, 1500))
_KIN = fq.hitter_kinematics(_HS_OPEN, np.array([T_HIT]), wd.M.body)
PALM_CLOUD = _KIN["palm"][:, 0]
GHOST_IDX = [3, 7, 11, 19, 23, 31, 42, 57, 64, 77, 88, 95, 101, 120]


# =====================================================================================
# 08  ENTER THE HUMAN
# =====================================================================================
NOISE_ROWS = [
    ("take-off spot", "± 10 cm", "footwork never lands on the same mark"),
    ("take-off moment", "± 20 ms", "approach rhythm"),
    ("jump power", "± 3 %", "→ peak height ± 4 cm  (spike jumps vary ~6 %)"),
    ("blind swing timing", "± 12 ms", "as steady as a pro musician's beat"),
    ("arm lean & swing direction", "± 3–4°", "the hand drifts sideways"),
    ("body lean & turn", "± 3°", "trunk and hips"),
]
CAM_GHOST = Camera((1.6, -6.2, 3.6), (-1.9, -0.75, 2.35), fov=34)


@scene("08_human", 25.0, events=[(0.3, "whoosh", 0.5)] + [(1.6 + 1.1 * i, "tick", 0.6) for i in range(6)] +
       [(9.4, "whoosh", 0.6), (16.6, "chime", 0.6), (20.4, "slam", 0.6)])
def s08(fr, s):
    background(fr, s)
    section_tag(fr, "06", "ENTER THE HUMAN", s)
    if s < 9.4:
        a0 = 1 - ease_io(seg(s, 8.9, 9.4))
        fr.text("No two jumps are identical. Here is how much a spiker varies, attempt to attempt:", 70, 165, 34,
                "semi", PAL["ink"], ease_out(seg(s, 0.4, 0.9)) * a0)
        for i, (name, val, sub) in enumerate(NOISE_ROWS):
            t0 = 1.6 + 1.1 * i
            k = ease_out(seg(s, t0, t0 + 0.35)) * a0
            if k <= 0:
                continue
            y = 240 + i * 118
            x = 120 + (1 - k) * 50
            fr.rect(x, y, 1680, 100, "#0d1430", 0.85 * k, radius=14)
            fr.rect(x, y, 8, 100, PAL["spiker"], k, radius=3)
            fr.text(name, x + 40, y + 62, 38, "black", PAL["ink"], k)
            fr.text(val, x + 760, y + 64, 46, "dblackit", PAL["spiker"], k)
            fr.text(sub, x + 1040, y + 62, 28, "med", PAL["ink2"], k)
        fr.text("(± = one standard deviation, attempt to attempt; sources at the end)", 120, 975, 24, "med", PAL["ink3"],
                ease_out(seg(s, 8.2, 8.6)) * a0)
        return
    cam = CAM_GHOST
    wd.draw_court(fr, cam)
    # setter + ideal ball path
    wd.draw_athlete(fr, cam, wd.setter_pose(0.0), PAL["setter"], glow=PAL["setter"], alpha=0.7)
    ball = nominal_ball()
    path = np.array([ball.pos(x) for x in np.linspace(0, T_HIT, 50)])
    world_path(fr, cam, path, PAL["setter"], 4, 0.9, glow=6)
    k_g = ease_out(seg(s, 9.6, 11.5))
    n_g = int(round(len(GHOST_IDX) * k_g))
    if s < 16.4:
        for j in GHOST_IDX[:n_g]:
            att = {k: float(v[j]) for k, v in _HS_OPEN.items()}
            J = wd.spiker_pose(att, T_HIT)
            wd.draw_athlete(fr, cam, J, PAL["spiker"], ghost=True, alpha=0.55)
            pp, _ = cam.project(np.array([J["hand_r"]]))
            fr.circle(pp[0], 7, PAL["spiker"], 0.95)
        wd.draw_athlete(fr, cam, wd.spiker_pose(NOM, T_HIT), PAL["spiker"], glow=PAL["spiker"],
                        alpha=1 - 0.5 * k_g)
        fr.text("%d blind attempts, frozen at the planned contact instant" % n_g, 70, 170, 34, "semi", PAL["ink"],
                ease_out(seg(s, 9.6, 10.0)))
    else:
        k = ease_io(seg(s, 16.4, 18.4))
        n = int(len(PALM_CLOUD) * k)
        if n > 0:
            sp, z = cam.project(PALM_CLOUD[:n])
            p = fr.paint(PAL["spiker"], 0.55)
            p.setStrokeWidth(6); p.setStrokeCap(skia.Paint.kRound_Cap)
            fr.c.drawPoints(skia.Canvas.kPoints_PointMode, [skia.Point(float(a), float(b)) for a, b in sp], p)
        wd.draw_ball(fr, cam, PLAN.target, glow="#ffffff")
        fr.text("Where the palm actually is when the ball arrives", 70, 170, 34, "semi", PAL["ink"],
                ease_out(seg(s, 16.6, 17.0)))
        fr.text("(1,500 simulated attempts)", 70, 214, 28, "med", PAL["ink2"], ease_out(seg(s, 16.8, 17.2)))
    if s > 20.3:
        a = ease_out(seg(s, 20.3, 20.7))
        fr.rect(0, 840, W, 170, "#03050c", 0.75 * a)
        fr.text("The hand is not a point. It's a cloud —", W / 2, 910, 52, "xboldit", PAL["ink"], a, "center")
        fr.text("and it's moving at 57 km/h.", W / 2, 975, 52, "xboldit", PAL["spiker"], ease_out(seg(s, 21.2, 21.6)),
                "center")
    slash_wipe(fr, s - 24.55, 0.45, PAL["hi"])


# =====================================================================================
# 09  THE CONTACT WINDOW
# =====================================================================================
HAND_SCALE = 2300.0  # px per metre in the palm diagram


def draw_hand_2d(fr, cx, cy, k=HAND_SCALE, alpha=1.0, skin="#e7eaf8"):
    """Palm-side view of a right hand; palm centre at (cx, cy), fingertips up."""
    def P(x, y):
        return (cx + x * k, cy - y * k)
    ol = PAL["outline"]
    # forearm
    fr.line(P(0, -0.078), P(0.0, -0.40), 0.066 * k + 6, ol, alpha)
    fr.line(P(0, -0.078), P(0.0, -0.40), 0.066 * k, skin, alpha)
    fingers = [(-0.034, 0.096), (-0.0115, 0.113), (0.0115, 0.108), (0.034, 0.088)]
    for x, tip in fingers:
        fr.line(P(x, 0.02), P(x * 1.08, tip), 0.0205 * k + 6, ol, alpha)
    fr.line(P(-0.045, -0.035), P(-0.088, 0.018), 0.024 * k + 6, ol, alpha)
    palm = skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(*P(-0.047, 0.035), *P(0.047, -0.085)), 0.03 * k, 0.03 * k)
    fr.c.drawRRect(palm, fr.paint(ol, alpha, stroke=6))
    fr.c.drawRRect(palm, fr.paint(skin, alpha))
    for x, tip in fingers:
        fr.line(P(x, 0.02), P(x * 1.08, tip), 0.0205 * k, skin, alpha)
    fr.line(P(-0.045, -0.035), P(-0.088, 0.018), 0.024 * k, skin, alpha)
    # palm crease hint
    fr.line(P(-0.03, -0.02), P(0.02, 0.0), 2, "#b9c0dd", alpha * 0.8)


def draw_zones(fr, cx, cy, k=HAND_SCALE, alpha=1.0, labels=True, size=26):
    R = wd.M.body
    fr.circle((cx, cy), R.rho_clean * k, PAL["good"], alpha * 0.22)
    fr.circle((cx, cy), R.rho_clean * k, PAL["good"], alpha, stroke=4)
    fr.c.save()
    p = fr.paint(PAL["palm"], alpha, stroke=3); p.setPathEffect(skia.DashPathEffect.Make([12, 8], 0))
    fr.c.drawCircle(cx, cy, R.r_hand * k, p)
    p2 = fr.paint(PAL["warn"], alpha * 0.9, stroke=3); p2.setPathEffect(skia.DashPathEffect.Make([6, 10], 0))
    fr.c.drawCircle(cx, cy, (R.r_hand + wd.R_BALL) * k, p2)
    fr.c.restore()
    if labels:
        fr.text("sweet spot  r = 5 cm", cx + R.rho_clean * k * 0.75 + 30, cy - R.rho_clean * k * 0.75, size, "bold",
                PAL["good"], alpha)
        fr.text("palm  r = 8.5 cm", cx + R.r_hand * k * 0.72 + 30, cy - R.r_hand * k * 0.72 - 14, size, "bold",
                PAL["palm"], alpha)
        fr.text("any touch  r = 19 cm", cx + (R.r_hand + wd.R_BALL) * k * 0.7 + 20,
                cy - (R.r_hand + wd.R_BALL) * k * 0.7 - 10, size, "bold", PAL["warn"], alpha)


def ball_2d(fr, x, y, r, alpha=1.0, ghost=False, col=None):
    if ghost:
        fr.circle((x, y), r, col or "#f4f6ff", alpha * 0.16)
        fr.circle((x, y), r, col or "#f4f6ff", alpha * 0.85, stroke=3)
        return
    sh = skia.GradientShader.MakeRadial(skia.Point(x - r * 0.35, y - r * 0.4), r * 1.7,
                                        [hexc("#ffffff"), hexc("#eef0f8"), hexc("#7d86aa")], [0.0, 0.5, 1.0])
    fr.circle((x, y), r, "#ffffff", alpha * 0.92, shader=sh)
    fr.c.save()
    pth = skia.Path(); pth.addCircle(float(x), float(y), float(r)); fr.c.clipPath(pth, doAntiAlias=True)
    q = skia.Path(); q.moveTo(x - r * 1.2, y - r * 0.2); q.quadTo(x, y + r * 0.9, x + r * 1.2, y - r * 0.3)
    fr.c.drawPath(q, fr.paint("#f2c94c", alpha * 0.8, stroke=r * 0.4, cap="butt"))
    fr.c.restore()
    fr.circle((x, y), r, PAL["outline"], alpha, stroke=3)


WIN = R["window_time"]
V_IN = R["plan"]["ball_inplane_speed"]


@scene("09_window", 30.0, events=[(0.3, "whoosh", 0.5), (4.4, "pop", 0.6), (8.0, "buzz", 0.6), (11.4, "tick", 0.5),
                                  (12.4, "tick", 0.5), (13.4, "tick", 0.5), (17.0, "chime", 0.7), (19.4, "slam", 0.7),
                                  (23.0, "pop", 0.6), (24.0, "pop", 0.6), (25.0, "pop", 0.6), (26.0, "pop", 0.6)])
def s09(fr, s):
    background(fr, s)
    section_tag(fr, "07", "THE CONTACT WINDOW", s)
    cx, cy = 640, 560
    k = HAND_SCALE * 0.75
    rb = wd.R_BALL * k
    if s < 22.6:
        a = ease_out(seg(s, 0.3, 0.9)) * (1 - ease_io(seg(s, 22.2, 22.6)))
        fr.text("Freeze the instant the palm reaches the ball. Seen face-on:", 70, 165, 34, "semi", PAL["ink"], a)
        with fr.layer(a):
            draw_hand_2d(fr, cx, cy, k)
            draw_zones(fr, cx, cy, k, labels=False)
        if 1.5 < s < 11.4:
            la = ease_out(seg(s, 1.5, 1.9)) * a * (1 - ease_io(seg(s, 10.8, 11.2)))
            for i, (txt, col) in enumerate((("sweet spot  ·  radius 5 cm", PAL["good"]),
                                             ("palm  ·  radius 8.5 cm", PAL["palm"]),
                                             ("any touch  ·  radius 19 cm", PAL["warn"]))):
                yy = 930 + i * 44
                fr.circle((110, yy - 9), 12, col, la, stroke=4)
                fr.text(txt, 135, yy, 28, "semi", PAL["ink"], la)
        # the ball
        if s < 4.0:
            bx = cx
        elif s < 7.6:
            bx = cx  # along-swing demo keeps it centred
        elif s < 11.0:
            bx = cx + rb * 2.2 * ease_io(seg(s, 8.0, 9.0)) * (1 - ease_io(seg(s, 10.2, 11.0)))
        else:
            bx = cx
        by = cy
        scale = 1.0
        if 4.0 <= s < 7.6:
            # along-swing error: the ball sits nearer/farther along the swing -> just a size change in this view
            scale = 1.0 + 0.25 * math.sin((s - 4.0) * 2.2)
        if s < 11.0:
            ball_2d(fr, bx, by, rb * scale, a, ghost=True, col=PAL["ink"])
            fr.circle((bx, by), 7, PAL["ink"], a)
        # explanations (right column)
        X = 1180
        if 4.0 <= s < 7.6:
            b = fade(s, 4.0, 7.6, 0.3, 0.3)
            chip(fr, "ERROR ALONG THE SWING", X, 380, PAL["good"], b, size=30)
            fr.wrapped("The hand sweeps through this plane at 57 km/h, so a ball a little nearer or farther just "
                       "gets met a few milliseconds earlier or later.", X, 450, 660, 30, "med", PAL["ink"], b)
            fr.text("→ forgiven", X, 650, 44, "dblackit", PAL["good"], b)
        if 7.6 <= s < 11.0:
            b = fade(s, 7.6, 11.0, 0.3, 0.3)
            chip(fr, "ERROR ACROSS THE SWING", X, 380, PAL["bad"], b, size=30)
            fr.wrapped("Sideways, nothing sweeps to the rescue. Off by a ball-width and the palm swings through "
                       "empty air.", X, 450, 660, 30, "med", PAL["ink"], b)
            fr.text("→ fatal", X, 650, 44, "dblackit", PAL["bad"], b)
        if 11.0 <= s < 22.6:
            b = ease_out(seg(s, 11.0, 11.4)) * (1 - ease_io(seg(s, 22.2, 22.6)))
            fr.text("The ball crosses the palm sideways at", X, 300, 32, "semi", PAL["ink"], b)
            fr.text("%.1f m/s" % V_IN, X, 380, 72, "dblackit", PAL["setter"], b)
            fr.text("so a late or early swing becomes a sideways miss:", X, 440, 30, "med", PAL["ink2"], b)
            fr.text("1 ms  =  %.1f mm" % V_IN, X, 515, 52, "black", PAL["hi"], b)
            # timing ruler under the hand: where the ball centre sits for a given swing error
            ry = cy + 250
            msk = V_IN / 1000 * k   # px per ms
            fr.line((cx - 34 * msk, ry), (cx + 20 * msk, ry), 3, PAL["ink3"], b)
            fr.rect(cx + WIN["touch"][0] * 1000 * msk, ry - 9, (WIN["touch"][1] - WIN["touch"][0]) * 1000 * msk, 18, PAL["warn"], b * 0.55, radius=4)
            fr.rect(cx - WIN["spike"][1] * 1000 * msk, ry - 9, 2 * WIN["spike"][1] * 1000 * msk, 18, PAL["palm"], b, radius=4)
            fr.rect(cx - WIN["clean"][1] * 1000 * msk, ry - 9, 2 * WIN["clean"][1] * 1000 * msk, 18, PAL["good"], b, radius=4)
            for ms in (-30, -20, -10, 0, 10, 20):
                fr.line((cx + ms * msk, ry + 12), (cx + ms * msk, ry + 22), 2, PAL["ink3"], b)
                fr.text("%+d" % ms if ms else "0", cx + ms * msk, ry + 50, 24, "med", PAL["ink2"], b, "center")
            fr.text("early", cx - 34 * msk - 14, ry + 50, 24, "semi", PAL["ink2"], b, "right")
            fr.text("late (ms)", cx + 20 * msk + 52, ry + 50, 24, "semi", PAL["ink2"], b)
            # a ghost ball sweeping through the offsets
            sw = math.sin((s - 11.4) * 1.3) * 14 if s > 11.4 else 0.0
            col = PAL["good"] if abs(sw) <= WIN["clean"][1] * 1000 else (PAL["palm"] if abs(sw) <= WIN["spike"][1] * 1000 else PAL["warn"])
            ball_2d(fr, cx + sw * msk, cy, rb, b, ghost=True, col=col)
            fr.circle((cx + sw * msk, cy), 7, col, b)
            fr.line((cx + sw * msk, cy + rb), (cx + sw * msk, ry - 12), 2, col, b * 0.7)
            fr.text("%+.0f ms" % sw, cx + sw * msk, ry - 22, 28, "black", col, b, "center")
            if s > 16.8:
                c = ease_out(seg(s, 16.8, 17.2)) * b
                fr.rect(X - 20, 590, 700, 300, "#060914", 0.85 * c, radius=16)
                fr.text("sweet spot:", X + 10, 645, 32, "semi", PAL["good"], c)
                fr.text("± %.1f ms" % (WIN["clean"][1] * 1000), X + 330, 645, 40, "black", PAL["good"], c)
                fr.text("on the palm:", X + 10, 705, 32, "semi", PAL["palm"], c)
                fr.text("± %.1f ms" % (WIN["spike"][1] * 1000), X + 330, 705, 40, "black", PAL["palm"], c)
                fr.text("any touch:", X + 10, 765, 32, "semi", PAL["warn"], c)
                fr.text("−%.0f / +%.1f ms" % (-WIN["touch"][0] * 1000, WIN["touch"][1] * 1000), X + 330, 765, 40,
                        "black", PAL["warn"], c)
                fr.text("(early swings can still clip the ball with the hand's edge)", X + 10, 820, 22, "med",
                        PAL["ink3"], c)
            if s > 19.3:
                c = ease_out(seg(s, 19.3, 19.7)) * b
                fr.rect(0, 900, W, 140, "#03050c", 0.85 * c)
                total = (WIN["clean"][1] - WIN["clean"][0]) * 1000
                fr.text("The whole sweet-spot window is %.0f ms." % total, W / 2, 955, 48, "xboldit", PAL["hi"], c, "center")
                fr.text("At 60 fps, one video frame lasts 16.7 ms — the window fits inside a single frame.", W / 2,
                        1005, 30, "semi", PAL["ink"], c, "center")
    else:
        # the four ways to miss
        a = ease_out(seg(s, 22.6, 23.0))
        fr.text("Four ways a blind swing can miss", 70, 165, 40, "black", PAL["ink"], a)
        cases = [("PASSED BY", "hand late / set too fast", (0.17, 0.0), PAL["bad"]),
                 ("FELL SHORT", "hand early / set too slow", (-0.17, 0.0), PAL["bad"]),
                 ("OVER THE FINGERS", "set too high / jump too low", (0.0, 0.19), PAL["warn"]),
                 ("UNDER THE PALM", "set too low / jump too high", (0.0, -0.15), PAL["warn"])]
        for i, (title, sub, (es, ea), col) in enumerate(cases):
            t0 = 23.0 + 1.0 * i
            kk = ease_out(seg(s, t0, t0 + 0.4))
            if kk <= 0:
                continue
            col_i, row = i % 2, i // 2
            px, py = 110 + col_i * 880, 230 + row * 400
            fr.rect(px, py, 820, 370, "#0b1129", 0.9 * kk, radius=18)
            kk2 = HAND_SCALE * 0.28
            hcx, hcy = px + 215, py + 205
            fr.c.save(); fr.c.clipRect(skia.Rect.MakeXYWH(px, py, 820, 370))
            draw_hand_2d(fr, hcx, hcy, kk2, kk)
            ball_2d(fr, hcx + es * kk2, hcy - ea * kk2, wd.R_BALL * kk2, kk)
            # motion arrow for the ball (moves left -> right)
            fr.line((hcx + es * kk2 - 150, hcy - ea * kk2 + 70), (hcx + es * kk2 - 60, hcy - ea * kk2 + 70), 4, PAL["setter"], kk)
            fr.polygon([(hcx + es * kk2 - 50, hcy - ea * kk2 + 70), (hcx + es * kk2 - 66, hcy - ea * kk2 + 61),
                        (hcx + es * kk2 - 66, hcy - ea * kk2 + 79)], PAL["setter"], kk)
            fr.c.restore()
            fr.text(title, px + 450, py + 150, 40, "black", col, kk)
            fr.text(sub, px + 450, py + 200, 28, "semi", PAL["ink"], kk)
        if s > 27.2:
            c = ease_out(seg(s, 27.2, 27.6))
            fr.text("(the ball travels left → right across the palm in these views)", W / 2, 1040, 26, "med", PAL["ink2"],
                    c, "center")
    slash_wipe(fr, s - 29.55, 0.45, PAL["spiker"])


# =====================================================================================
# 10  100,000 ATTEMPTS
# =====================================================================================
DB_C = (560, 640)
DB_K = 6.0  # px per cm


def dartboard(fr, prefix, n, alpha=1.0, title=None):
    cx, cy = DB_C
    fr.rect(cx - 420, cy - 360, 840, 700, "#070b1a", 0.85 * alpha, radius=18)
    fr.c.save(); fr.c.clipRect(skia.Rect.MakeXYWH(cx - 420, cy - 360, 840, 700))
    for v in (-60, -40, -20, 0, 20, 40, 60):
        fr.line((cx + v * DB_K, cy - 330), (cx + v * DB_K, cy + 330), 1, "#1c2550", alpha)
    for v in (-40, -20, 0, 20, 40):
        fr.line((cx - 400, cy - v * DB_K), (cx + 400, cy - v * DB_K), 1, "#1c2550", alpha)
    es = SMP[f"{prefix}_e_s"][:n] * 100; ea = SMP[f"{prefix}_e_a"][:n] * 100; oc = SMP[f"{prefix}_outcome"][:n]
    for code in (fq.MISS, fq.EDGE, fq.PALM, fq.CLEAN):
        m = oc == code
        if not m.any():
            continue
        p = fr.paint(OUT_COL[code], alpha * 0.75)
        p.setStrokeWidth(6 if code in (fq.CLEAN, fq.PALM) else 5); p.setStrokeCap(skia.Paint.kRound_Cap)
        pts = [skia.Point(float(cx + x * DB_K), float(cy - y * DB_K)) for x, y in zip(es[m], ea[m])]
        fr.c.drawPoints(skia.Canvas.kPoints_PointMode, pts, p)
    fr.circle((cx, cy), 5 * DB_K, "#ffffff", alpha, stroke=2)
    fr.circle((cx, cy), 8.5 * DB_K, "#ffffff", alpha * 0.6, stroke=1.5)
    fr.c.restore()
    fr.text("← ball short (hand early)", cx - 400, cy + 330, 22, "med", PAL["ink2"], alpha)
    fr.text("ball past (hand late) →", cx + 400, cy + 330, 22, "med", PAL["ink2"], alpha, "right")
    fr.text("too high ↑", cx + 12, cy - 320, 22, "med", PAL["ink2"], alpha)
    fr.text("20 cm", cx + 20 * DB_K + 6, cy + 24, 20, "med", PAL["ink3"], alpha)
    if title:
        fr.text(title, cx - 400, cy - 380, 30, "bold", PAL["ink"], alpha)


def outcome_bars(fr, s_res, x, y, alpha=1.0, k=1.0, size=30):
    rows = [(fq.CLEAN, s_res["clean"]), (fq.PALM, s_res["palm"]), (fq.EDGE, s_res["edge"]), (fq.MISS, s_res["miss"])]
    for i, (code, v) in enumerate(rows):
        yy = y + i * 92
        fr.text(OUT_ICON[code] + "  " + OUT_LAB[code], x, yy, size, "black", OUT_COL[code], alpha)
        bw = 520 * v * k
        fr.rect(x, yy + 16, 520, 30, "#141d42", alpha, radius=4)
        fr.rect(x, yy + 16, max(3, bw), 30, OUT_COL[code], alpha, radius=4)
        fr.text("%.1f%%" % (100 * v * k), x + 540, yy + 42, size, "bold", PAL["ink"], alpha)


MODES = [("open", "main_open_setter1", "PRE-PLANNED SET", "the setter commits before he can see the jump"),
         ("closed", "main_closed_setter1", "SETTER READS THE APPROACH", "Kalman-filtered eyes, 0.14 s eye-to-hand delay"),
         ("telepathic", "main_telepathic_setter1", "MIND READER", "knows exactly how he jumped — but not his swing")]


def kalman_panel(fr, s0, s, alpha=1.0):
    """Top-view inset: the setter's estimate of the take-off spot sharpening with each look."""
    x0, y0, w, h = 580, 330, 760, 640
    fr.rect(x0, y0, w, h, "#070b1a", 0.9 * alpha, radius=18)
    fr.text("Setter's estimate of the take-off spot (top view)", x0 + 30, y0 + 50, 26, "bold", PAL["ink"], alpha)
    cx, cy = x0 + 250, y0 + 300
    K = 8.0  # px per cm
    kal = R["kalman"]
    sd = np.sqrt(np.array(kal["pred_cov"])) * 100  # cm
    n_obs = len(sd)
    u = clamp((s - s0) / 5.0)
    i = min(n_obs - 1, int(u * n_obs))
    obs_x = np.array(kal["obs"][0]) * 100; obs_y = np.array(kal["obs"][1]) * 100
    tru_x = kal["truth"][0][-1] * 100; tru_y = kal["truth"][1][-1] * 100
    r0 = 10.0
    r = sd[i] if u > 0 else r0
    est_x = np.array(kal["est"][0]) * 100; est_y = np.array(kal["est"][1]) * 100
    ex, ey = (est_x[i], est_y[i]) if u > 0 else (0.0, 0.0)
    if u >= 1:
        ex, ey = kal["pred"][0] * 100, kal["pred"][1] * 100
    for j in range(i + 1):
        fr.circle((cx + obs_x[j] * K, cy - obs_y[j] * K), 4, PAL["setter"], alpha * 0.55)
    fr.circle((cx, cy), r0 * K, PAL["ink3"], alpha * 0.6, stroke=2)
    fr.text("plan", cx - r0 * K + 6, cy - r0 * K + 4, 20, "med", PAL["ink3"], alpha)
    ec = (cx + ex * K, cy - ey * K)
    fr.circle(ec, r * K, PAL["setter"], alpha * 0.22)
    fr.circle(ec, r * K, PAL["setter"], alpha, stroke=3)
    fr.line((ec[0] - 9, ec[1]), (ec[0] + 9, ec[1]), 2, PAL["ink"], alpha); fr.line((ec[0], ec[1] - 9), (ec[0], ec[1] + 9), 2, PAL["ink"], alpha)
    fr.text("1σ = %.1f cm" % r, ec[0] + r * K + 14, ec[1] + 8, 26, "bold", PAL["setter"], alpha)
    if u >= 1:
        tx, ty = cx + tru_x * K, cy - tru_y * K
        fr.line((tx - 8, ty - 8), (tx + 8, ty + 8), 3, PAL["hi"], alpha); fr.line((tx - 8, ty + 8), (tx + 8, ty - 8), 3, PAL["hi"], alpha)
        fr.text("actual", tx + 12, ty + 24, 20, "semi", PAL["hi"], alpha)
    fr.text("looks: %d  (20 per second)" % (i + 1), x0 + 520, y0 + 140, 24, "semi", PAL["ink2"], alpha)
    fr.text("start: ±10 cm", x0 + 520, y0 + 200, 24, "semi", PAL["ink3"], alpha)
    fr.text("last useful look:", x0 + 520, y0 + 260, 24, "semi", PAL["ink2"], alpha)
    fr.text("0.14 s before the set", x0 + 520, y0 + 292, 24, "bold", PAL["ink"], alpha)
    fr.text("(eye-to-hand delay)", x0 + 520, y0 + 322, 22, "med", PAL["ink3"], alpha)
    if u >= 1:
        b = ease_out(seg(s, s0 + 5.0, s0 + 5.4)) * alpha
        fr.text("He can see WHERE the spiker jumps (±3 cm)…", x0 + 30, y0 + 560, 26, "bold", PAL["good"], b)
        fr.text("…not how high, and never when he swings.", x0 + 30, y0 + 600, 26, "bold", PAL["bad"], b)


@scene("10_montecarlo", 40.0, events=[(0.3, "whoosh", 0.5), (1.0, "slam", 0.8), (3.0, "rain", 1.0), (13.5, "chime", 0.7),
                                      (14.4, "whoosh", 0.6), (15.0, "kalman", 0.8), (23.0, "chime", 0.7),
                                      (24.4, "whoosh", 0.6), (25.0, "rain", 0.8), (30.4, "chime", 0.7),
                                      (31.4, "whoosh", 0.6), (33.2, "impact", 0.7), (36.8, "slam", 0.9)])
def s10(fr, s):
    background(fr, s)
    section_tag(fr, "08", "100,000 ATTEMPTS", s)
    if s < 3.0:
        slam_text(fr, "Let's play it 100,000 times.", W / 2, H / 2, s - 0.9, size=96, color=PAL["hi"],
                  accent=PAL["spiker"])
        return
    # three phases: open (3-14), closed (14-24), mind reader (24-31), summary (31-42)
    phases = [(3.0, 14.0, 0), (14.0, 24.0, 1), (24.0, 31.0, 2)]
    for t0, t1, mi in phases:
        if not (t0 <= s < t1):
            continue
        prefix, key, title, sub = MODES[mi]
        res = mc(key)
        a = fade(s, t0, t1, 0.4, 0.4)
        fr.text(title, 70, 170, 44, "black", PAL["setter"], a)
        fr.text(sub, 70, 212, 28, "semi", PAL["ink2"], a)
        if mi == 1 and s < t0 + 6.4:
            kalman_panel(fr, t0 + 0.6, s, a * fade(s, t0, t0 + 6.4, 0.3, 0.3))
            continue
        dur_rain = 6.0 if mi == 0 else 3.0
        rain_start = t0 + 0.6 if mi != 1 else t0 + 6.0
        kk = ease_io(seg(s, rain_start, rain_start + dur_rain))
        dartboard(fr, prefix, int(4000 * kk), a * ease_out(seg(s, rain_start - 0.4, rain_start)),
                  title="every dot = one attempt (where the ball met the palm plane)")
        n_show = int(4000 * kk)
        ca = a * ease_out(seg(s, rain_start - 0.2, rain_start + 0.2))
        fr.text("%s attempts shown" % format(n_show, ","), 1100, 330, 44, "dblackit", PAL["ink"], ca)
        fr.text("(of 100,000 simulated)", 1100, 372, 26, "semi", PAL["ink2"], ca)
        oc = SMP[f"{prefix}_outcome"][:max(1, n_show)]
        run = {"clean": float(np.mean(oc == fq.CLEAN)), "palm": float(np.mean(oc == fq.PALM)),
               "edge": float(np.mean(oc == fq.EDGE)), "miss": float(np.mean(oc == fq.MISS))}
        fin = ease_io(seg(s, rain_start + dur_rain, rain_start + dur_rain + 0.5))
        shown = {k_: lerp(run[k_], res[k_], fin) for k_ in run} if n_show > 0 else res
        outcome_bars(fr, shown, 1100, 450, a * ease_out(seg(s, rain_start, rain_start + 0.3)), k=1.0)
        if kk >= 1:
            b = ease_out(seg(s, rain_start + dur_rain, rain_start + dur_rain + 0.4)) * a
            fr.text("palm contact at all: %.0f%%   ·   sweet spot: 1 in %d" % (100 * res["spike"], round(1 / res["clean"])),
                    1100, 830, 30, "bold", PAL["hi"], b)
    if s >= 31.0:
        a = ease_out(seg(s, 31.0, 31.5))
        fr.text("Who's setting?  (blind spiker, 100,000 attempts each)", 70, 170, 40, "black", PAL["ink"], a)
        rows = [("Pre-planned set", "main_open_setter1"), ("Reads the approach", "main_closed_setter1"),
                ("Mind reader", "main_telepathic_setter1"), ("Mind reader + robot arms", "main_telepathic_setter0")]
        for i, (lab, key) in enumerate(rows):
            t0 = 31.6 + 0.6 * i
            kk = ease_out(seg(s, t0, t0 + 0.7))
            if kk <= 0:
                continue
            res = mc(key)
            y = 260 + i * 150
            fr.text(lab, 90, y + 58, 36, "black", PAL["hi"] if i == 3 else PAL["ink"], kk)
            parts = [(res["clean"], OUT_COL[fq.CLEAN], ""), (res["palm"], OUT_COL[fq.PALM], ""),
                     (res["edge"], OUT_COL[fq.EDGE], ""), (res["miss"], OUT_COL[fq.MISS], "")]
            stacked_bar(fr, 640, y + 18, 1180, 64, parts, kk, reveal=kk, size=26)
        # legend
        lx = 640
        for code in (fq.CLEAN, fq.PALM, fq.EDGE, fq.MISS):
            fr.rect(lx, 862, 22, 22, OUT_COL[code], a, radius=4)
            fr.text(OUT_LAB[code].lower(), lx + 32, 882, 24, "semi", PAL["ink"], a)
            lx += 60 + text_width(OUT_LAB[code].lower(), "semi", 24)
        if s > 36.6:
            b = ease_out(seg(s, 36.6, 37.0))
            fr.rect(0, 920, W, 130, "#03050c", 0.85 * b)
            fr.text("Even a mind-reading robot setter finds the sweet spot only 1 time in 3.", W / 2, 985, 46, "xboldit",
                    PAL["ink"], b, "center")
    slash_wipe(fr, s - 39.55, 0.45, PAL["hi"])


# =====================================================================================
# 11  WHAT BREAKS IT (error budget)
# =====================================================================================
def _budget():
    rows = []
    for r in R["sensitivity"]:
        v = math.hypot(r["contrib_s"], r["contrib_a"]) * 100
        rows.append((r["name"], v, PAL["spiker"] if r["who"] == "spiker" else PAL["setter"], r["who"]))
    rows.sort(key=lambda x: -x[1])
    return rows[:11]


BUDGET = _budget()


def clock_icon(fr, x, y, r, col, a):
    fr.circle((x, y), r, col, a, stroke=3)
    fr.line((x, y), (x, y - r * 0.65), 3, col, a)
    fr.line((x, y), (x + r * 0.5, y + r * 0.1), 3, col, a)
    fr.line((x - r * 0.35, y - r * 1.35), (x + r * 0.35, y - r * 1.35), 3, col, a)
TIME_KEYS = {"take-off time", "swing timing", "jump power", "release timing", "take-off spot (along net)", "set speed"}


@scene("11_budget", 15.5, events=[(0.3, "whoosh", 0.5)] + [(1.2 + 0.25 * i, "tick", 0.4) for i in range(11)] +
       [(8.6, "chime", 0.7), (12.0, "slam", 0.7)])
def s11(fr, s):
    background(fr, s)
    section_tag(fr, "09", "WHAT BREAKS IT", s)
    a = ease_out(seg(s, 0.3, 0.8))
    fr.text("How far each error source pushes the ball off the palm (1 SD, pre-planned set)", 70, 170, 32, "semi",
            PAL["ink"], a)
    rows = [(n, v, c) for n, v, c, _ in BUDGET]
    hbars(fr, rows, 70, 220, 1500, 64, max(v for _, v, _ in rows), t_reveal=(s - 1.2) * 2.2, alpha=1.0, size=28,
          label_w=470, unit=" cm", fmt="{:.1f}", stagger=0.12)
    fr.rect(1500, 420, 24, 24, PAL["spiker"], a, radius=4); fr.text("spiker", 1534, 441, 26, "semi", PAL["ink"], a)
    fr.rect(1500, 460, 24, 24, PAL["setter"], a, radius=4); fr.text("setter", 1534, 481, 26, "semi", PAL["ink"], a)
    if s > 8.4:
        b = ease_out(seg(s, 8.4, 8.8))
        for i, (n, v, c, _) in enumerate(BUDGET):
            if n in TIME_KEYS:
                clock_icon(fr, 70 + 470 - 18 - text_width(n, "semi", 28) - 30, 220 + i * 64 + 32, 13, PAL["hi"], b)
        fr.rect(1060, 560, 800, 200, "#060914", 0.88 * b, radius=18)
        clock_icon(fr, 1104, 608, 15, PAL["hi"], b)
        fr.text("= a timing error in disguise", 1130, 620, 32, "black", PAL["hi"], b)
        fr.wrapped("Anything that shifts WHEN the hand or ball arrives — or WHERE along the ball's path — "
                   "becomes a sideways miss at 8.4 mm per ms.", 1090, 670, 740, 26, "med", PAL["ink"], b)
    if s > 11.9:
        b = ease_out(seg(s, 11.9, 12.3))
        fr.rect(0, 930, W, 120, "#03050c", 0.85 * b)
        fr.text("The real enemy isn't distance. It's time.", W / 2, 1000, 50, "xboldit", PAL["ink"], b, "center")
    slash_wipe(fr, s - 15.05, 0.45, PAL["setter"])


# =====================================================================================
# 12  WHAT WOULD IT TAKE (inverse problem)
# =====================================================================================
KS = R["ks"]


def _interp_req(xs, ys, target=0.99):
    """Largest multiplier with P >= target (linear interpolation, xs ascending)."""
    best = 0.0
    for i in range(len(xs) - 1):
        if ys[i] >= target > ys[i + 1]:
            return xs[i] + (ys[i] - target) / (ys[i] - ys[i + 1]) * (xs[i + 1] - xs[i])
        if ys[i] >= target:
            best = xs[i]
    return best


HK = [mc(f"hitterk_{k}")["clean"] for k in KS]
SK = [mc(f"setterk_{k}")["clean"] for k in KS]
REQ_H = _interp_req(KS, HK)
REQ_S = _interp_req(KS, SK)


@scene("12_requirements", 36.0, events=[(0.3, "whoosh", 0.5), (1.0, "slam", 0.7), (3.0, "rise", 0.7), (8.0, "chime", 0.7),
                                        (12.6, "whoosh", 0.6), (14.0, "rise", 0.7), (18.4, "chime", 0.7),
                                        (23.6, "whoosh", 0.6), (25.0, "rain", 0.6), (30.0, "impact", 0.8)])
def s12(fr, s):
    background(fr, s)
    section_tag(fr, "10", "WHAT WOULD IT TAKE?", s)
    if s < 12.6:
        a = fade(s, 0.0, 12.6, 0.4, 0.4)
        slam_text(fr, "Run it backwards: what gives 99%?", W / 2, 180, s - 0.9, size=64, color=PAL["ink"],
                  accent=PAL["spiker"])
        ax = Axes(160, 300, 860, 520, (1.0, 0.0), (0.0, 1.0))
        ax.frame(fr, a, xticks=[1.0, 0.8, 0.6, 0.4, 0.2, 0.0], yticks=[0, 0.25, 0.5, 0.75, 1.0], yfmt="{:.0%}",
                 xfmt="{:g}×", xlabel="spiker's in-air variability  (1× = real human)",
                 ylabel="sweet-spot rate  (mind reader + robot setter)", size=24)
        ax.hline(fr, 0.99, PAL["good"], a, "99%")
        ax.series(fr, KS[::-1], HK[::-1], PAL["spiker"], a, reveal=seg(s, 3.0, 7.0), w=5, glow=6)
        if s > 7.6:
            b = ease_out(seg(s, 7.6, 8.0)) * a
            ax.vline(fr, REQ_H, PAL["good"], b, None)
            fr.text("needs ≈ %.2f×" % REQ_H, ax.px(REQ_H) - 12, ax.py(0.55), 30, "black", PAL["good"], b, "right")
            X = 1110
            fr.rect(X - 20, 290, 790, 560, "#060914", 0.88 * b, radius=18)
            fr.text("≈ %.0f× steadier than a human" % (1 / REQ_H), X + 10, 345, 36, "black", PAL["spiker"], b)
            fr.text("blind swing timing must stay within ±%.0f ms" % (12 * REQ_H), X + 10, 395, 28, "semi", PAL["ink"], b)
            fr.text("Timing spread (1 SD), real measurements:", X + 10, 460, 26, "bold", PAL["ink2"], b)
            comp = [("pro musician tapping a beat", 11.0, PAL["ink3"], "11 ms"),
                    ("expert dart throwers' release", 5.5, PAL["ink3"], "3–8 ms"),
                    ("table-tennis pros at contact, EYES OPEN", 3.1, PAL["setter"], "3.1 ms"),
                    ("needed here, EYES CLOSED", 12 * REQ_H, PAL["good"], "%.1f ms" % (12 * REQ_H))]
            for i, (lab, v, col, vl) in enumerate(comp):
                kk = ease_out(seg(s, 8.4 + 0.5 * i, 8.9 + 0.5 * i)) * b
                y = 500 + i * 82
                fr.text(lab, X + 10, y + 26, 24, "semi", PAL["ink"], kk)
                fr.rect(X + 10, y + 38, 560 * v / 12.0 * kk, 22, col, kk, radius=4)
                fr.text(vl, X + 20 + 560 * v / 12.0 * kk, y + 57, 24, "bold", PAL["ink"], kk)
    elif s < 23.6:
        a = fade(s, 12.6, 23.6, 0.4, 0.4)
        fr.text("…and the setter? (perfect spiker, mind-reader setter)", 70, 175, 40, "black", PAL["ink"], a)
        ax = Axes(160, 300, 860, 520, (1.0, 0.0), (0.0, 1.0))
        ax.frame(fr, a, xticks=[1.0, 0.8, 0.6, 0.4, 0.2, 0.0], yticks=[0, 0.25, 0.5, 0.75, 1.0], yfmt="{:.0%}",
                 xfmt="{:g}×", xlabel="setter's release noise  (1× = best NBA free-throw shooters)",
                 ylabel="sweet-spot rate", size=24)
        ax.hline(fr, 0.99, PAL["good"], a, "99%")
        ax.series(fr, KS[::-1], SK[::-1], PAL["setter"], a, reveal=seg(s, 14.0, 18.0), w=5, glow=6)
        if s > 18.2:
            b = ease_out(seg(s, 18.2, 18.6)) * a
            ax.vline(fr, REQ_S, PAL["good"], b, None)
            fr.text("needs ≈ %.2f×" % REQ_S, ax.px(REQ_S) - 12, ax.py(0.55), 30, "black", PAL["good"], b, "right")
            X = 1110
            fr.rect(X - 20, 290, 790, 520, "#060914", 0.88 * b, radius=18)
            fr.text("Release precision for 99%", X + 10, 345, 34, "black", PAL["setter"], b)
            rows = [("launch angle", "± %.2f°" % (1.1 * REQ_S), "best free-throw shooters ± 1.1°"),
                    ("launch speed", "± %.2f %%" % (1.6 * REQ_S), "best free-throw shooters ± 1.6 %"),
                    ("release timing", "± %.1f ms" % (5.0 * REQ_S), "expert dart throwers ± 3–8 ms")]
            for i, (lab, need, ref) in enumerate(rows):
                kk = ease_out(seg(s, 18.8 + 0.6 * i, 19.3 + 0.6 * i)) * b
                y = 400 + i * 120
                fr.text(lab, X + 10, y + 30, 30, "bold", PAL["ink"], kk)
                fr.text(need, X + 420, y + 32, 40, "dblackit", PAL["good"], kk)
                fr.text(ref, X + 10, y + 74, 24, "med", PAL["ink2"], kk)
    else:
        a = ease_out(seg(s, 23.6, 24.1))
        fr.text("Where the blind quick actually works", 70, 175, 40, "black", PAL["ink"], a)
        fr.text("sweet-spot rate, mind-reader setter", 70, 220, 28, "semi", PAL["ink2"], a)
        hk, sk = R["grid_axes"]["hitter"], R["grid_axes"]["setter"]
        x0, y0, cw, ch = 330, 270, 118, 62
        reveal = seg(s, 24.6, 27.0)
        for i, h in enumerate(hk):
            for j, sv in enumerate(sk):
                if (i + j) / (len(hk) + len(sk) - 2) > reveal:
                    continue
                v = mc(f"grid_{h}_{sv}")["clean"]
                x = x0 + i * cw; y = y0 + (len(sk) - 1 - j) * ch
                fr.rect(x + 1, y + 1, cw - 2, ch - 2, seq_color(v), a, radius=3)
                fr.text("%.0f" % (100 * v), x + cw / 2, y + ch / 2 + 9, 24, "bold", "#0b1022" if v > 0.45 else PAL["ink"],
                        a, "center")
                if v >= 0.99:
                    fr.rect(x + 3, y + 3, cw - 6, ch - 6, PAL["good"], a, radius=3, stroke=3)
        for i, h in enumerate(hk):
            fr.text("%g×" % h, x0 + i * cw + cw / 2, y0 + len(sk) * ch + 34, 22, "med", PAL["ink2"], a, "center")
        for j, sv in enumerate(sk):
            fr.text("%g×" % sv, x0 - 14, y0 + (len(sk) - 1 - j) * ch + ch / 2 + 8, 22, "med", PAL["ink2"], a, "right")
        fr.text("spiker variability  (× human) →", x0 + len(hk) * cw / 2, y0 + len(sk) * ch + 76, 26, "semi",
                PAL["ink"], a, "center")
        fr.text("setter noise (× elite) ↑", x0 - 20, y0 - 18, 26, "semi", PAL["ink"], a)
        if s > 27.4:
            b = ease_out(seg(s, 27.4, 27.8))
            # mark real humans (1.05x, 1.0x) ~ the cell nearest (1.0, 1.0)
            ih = int(np.argmin(np.abs(np.array(hk) - 1.0))); js = int(np.argmin(np.abs(np.array(sk) - 1.0)))
            x = x0 + ih * cw; y = y0 + (len(sk) - 1 - js) * ch
            fr.rect(x - 2, y - 2, cw + 4, ch + 4, PAL["spiker"], b, radius=4, stroke=5)
            gx = x0 + len(hk) * cw
            fr.line((x + cw + 4, y + ch / 2), (gx + 40, y + ch / 2), 3, PAL["spiker"], b)
            fr.text("real humans", gx + 50, y + ch / 2 + 10, 30, "black", PAL["spiker"], b)
            fr.rect(1450, 560, 420, 300, "#060914", 0.88 * b, radius=18)
            fr.text("green boxes:", 1480, 615, 30, "black", PAL["good"], b)
            fr.text("≥ 99% sweet spot", 1480, 655, 28, "semi", PAL["ink"], b)
            fr.wrapped("Only a corner where both players are ~4–6× more consistent than the human values used here.",
                       1480, 710, 370, 26, "med", PAL["ink2"], b)
        if s > 30.0:
            b = ease_out(seg(s, 30.0, 30.4))
            fr.rect(0, 960, W, 120, "#03050c", 0.85 * b)
            fr.text("Physically allowed. Humanly out of reach — with eyes closed.", W / 2, 1030, 48, "xboldit", PAL["hi"],
                    b, "center")
    slash_wipe(fr, s - 35.55, 0.45, PAL["spiker"])


# =====================================================================================
# 13  HOW TO MAKE IT WORK (levers)
# =====================================================================================
@scene("13_levers", 28.0, events=[(0.3, "whoosh", 0.5), (1.4, "rise", 0.6), (9.6, "whoosh", 0.6), (11.0, "rise", 0.6),
                                  (20.4, "whoosh", 0.6), (21.6, "slam", 0.9), (25.2, "chime", 0.8)])
def s13(fr, s):
    background(fr, s)
    section_tag(fr, "11", "THREE WAYS TO CHEAT PHYSICS", s)
    if s < 9.6:
        a = fade(s, 0.0, 9.6, 0.4, 0.4)
        fr.text("1.  Attack closer to the setter", 70, 175, 44, "black", PAL["hi"], a)
        fr.text("a short set crosses the palm slowly → a wider timing window", 70, 222, 28, "semi", PAL["ink2"], a)
        di = R["dist_info"]
        D = [d["D"] for d in di]
        p_tele = [mc(f"dist_tele_{d['contact_x']}")["clean"] for d in di]
        p_closed = [mc(f"dist_closed_{d['contact_x']}")["clean"] for d in di]
        ax = Axes(170, 300, 900, 520, (0.0, 4.5), (0.0, 0.6))
        ax.frame(fr, a, xticks=[0, 1, 2, 3, 4], yticks=[0, 0.2, 0.4, 0.6], yfmt="{:.0%}", xfmt="{:g} m",
                 xlabel="distance from setter's hands to the hit", ylabel="sweet-spot rate", size=24)
        r = seg(s, 1.4, 5.0)
        ax.series(fr, D, p_tele, PAL["setter"], a, reveal=r, w=5, label="mind reader", label_dy=-6)
        ax.series(fr, D, p_closed, PAL["ink2"], a, reveal=r, w=4, label="reads approach", label_dy=10)
        if s > 5.4:
            b = ease_out(seg(s, 5.4, 5.8)) * a
            X = 1160
            fr.rect(X - 20, 300, 720, 420, "#060914", 0.88 * b, radius=18)
            fr.text("sweet-spot window", X + 10, 355, 30, "bold", PAL["ink"], b)
            for i, d in enumerate([di[0], di[1], di[5], di[7]]):
                y = 420 + i * 72
                fr.text("%.1f m away" % d["D"], X + 10, y, 30, "semi", PAL["ink2"], b)
                fr.text("± %.0f ms" % (d["clean"][1] * 1000), X + 330, y, 38, "black",
                        PAL["good"] if d["clean"][1] > 0.01 else PAL["warn"], b)
            fr.text("our 3 m set is the hard version", X + 10, 700, 24, "med", PAL["ink3"], b)
    elif s < 20.4:
        a = fade(s, 9.6, 20.4, 0.4, 0.4)
        fr.text("2.  Slow the set down", 70, 175, 44, "black", PAL["hi"], a)
        fr.text("same 3 m, longer flight → slower across the palm", 70, 222, 28, "semi", PAL["ink2"], a)
        ti = R["tempo_info"]
        Ts = [d["T"] for d in ti]
        win = [d["clean"][1] * 1000 for d in ti]
        ax = Axes(170, 300, 900, 520, (0.28, 0.72), (0.0, 12.0))
        ax.frame(fr, a, xticks=[0.3, 0.4, 0.5, 0.6, 0.7], yticks=[0, 4, 8, 12], yfmt="±{:g} ms", xfmt="{:g} s",
                 xlabel="flight time of the set", ylabel="sweet-spot window", size=24)
        ax.series(fr, Ts, win, PAL["good"], a, reveal=seg(s, 11.0, 14.5), w=5)
        if s > 14.8:
            b = ease_out(seg(s, 14.8, 15.2)) * a
            X = 1160
            fr.rect(X - 20, 300, 720, 470, "#060914", 0.88 * b, radius=18)
            fr.text("the catch", X + 10, 355, 34, "black", PAL["bad"], b)
            d0, d1 = ti[0], ti[-1]
            fr.wrapped("At %.2f s the spiker leaves the floor %.0f ms BEFORE the set (minus tempo)." % (d0["T"], -d0["t_to"] * 1000),
                       X + 10, 410, 670, 28, "med", PAL["ink"], b)
            fr.wrapped("At %.2f s he must wait and jump %.0f ms AFTER it — the window doubles, but it's no longer "
                       "a minus-tempo attack, and blockers get time to arrive." % (d1["T"], d1["t_to"] * 1000),
                       X + 10, 530, 670, 28, "med", PAL["ink"], b)
    else:
        a = ease_out(seg(s, 20.4, 20.9))
        sfx_text(fr, "ゴゴゴ", 1600, 260, s - 20.6, size=110, color=PAL["spiker"], rot=-6, alpha=0.7 * a)
        slam_text(fr, "3.  Open your eyes.", W / 2, 360, s - 21.6, size=110, color=PAL["ink"], accent=PAL["spiker"])
        if s > 23.0:
            b = ease_out(seg(s, 23.0, 23.4))
            fr.text("With vision, top players steer the hand onto the ball while it flies.", W / 2, 520, 36, "semi",
                    PAL["ink"], b, "center")
            fr.text("Table-tennis pros: ~17 ms timing spread when the stroke starts → 3 ms at contact.", W / 2, 580, 32,
                    "med", PAL["ink2"], b, "center")
        if s > 25.0:
            b = ease_out(seg(s, 25.0, 25.4))
            fr.rect(W / 2 - 640, 680, 1280, 160, "#060914", 0.88 * b, radius=18)
            fr.text("Feedback beats blind precision.", W / 2, 750, 52, "dblackit", PAL["hi"], b, "center")
            fr.text("(the same reason a hitter who watches the ball can adjust in the air)", W / 2, 805, 28, "med",
                    PAL["ink2"], b, "center")
    slash_wipe(fr, s - 27.55, 0.45, PAL["setter"])


# =====================================================================================
# 14  VERDICT + CREDITS
# =====================================================================================
@scene("14_verdict", 30.0, events=[(0.2, "impact", 0.9), (2.0, "tick", 0.6), (3.2, "tick", 0.6), (4.4, "tick", 0.6),
                                   (5.6, "tick", 0.6), (8.4, "slam", 0.8), (12.4, "chime", 0.9), (17.0, "outro", 1.0)])
def s14(fr, s):
    background(fr, s, 0.3, "#2a1440")
    speed_lines(fr, s, center=(W / 2, H / 2), n=80, alpha=0.10, inner=520, width=(1, 3))
    if s < 16.6:
        a = 1 - ease_io(seg(s, 16.2, 16.6))
        slam_text(fr, "VERDICT", W / 2, 200, s - 0.1, size=150, color=PAL["hi"], accent=PAL["spiker"])
        rows = [("Pre-planned set", mc("main_open_setter1")),
                ("Setter reads the approach", mc("main_closed_setter1")),
                ("Mind-reading setter", mc("main_telepathic_setter1")),
                ("Mind reader + robot arms", mc("main_telepathic_setter0"))]
        for i, (lab, res) in enumerate(rows):
            kk = ease_out(seg(s, 2.0 + 1.2 * i, 2.4 + 1.2 * i)) * a
            y = 330 + i * 92
            fr.text(lab, 400, y, 36, "bold", PAL["ink"], kk)
            fr.text("sweet spot %4.1f%%" % (100 * res["clean"]), 1050, y, 36, "black", PAL["good"], kk)
            fr.text("palm %4.1f%%" % (100 * res["spike"]), 1430, y, 36, "semi", PAL["ink2"], kk)
        if s > 8.3:
            b = ease_out(seg(s, 8.3, 8.7)) * a
            fr.rect(W / 2 - 760, 720, 1520, 120, "#060914", 0.85 * b, radius=18)
            fr.text("For 99%%: a spiker ~%.0f× steadier than a human, and a setter ~%.0f× more precise than the best "
                    "free-throw shooters." % (1 / REQ_H, 1 / REQ_S), W / 2, 795, 32, "semi", PAL["ink"], b, "center")
        if s > 12.3:
            b = ease_out(seg(s, 12.3, 12.7)) * a
            fr.text("Physically possible?  Yes.     Reliable with eyes closed?  Only in anime.", W / 2, 940, 46,
                    "xboldit", PAL["hi"], b, "center")
    else:
        a = ease_out(seg(s, 16.6, 17.2))
        slam_text(fr, "Trust is beautiful.", W / 2, 300, s - 16.8, size=100, color=PAL["ink"], accent=PAL["setter"])
        slam_text(fr, "Feedback is better.", W / 2, 430, s - 18.0, size=100, color=PAL["hi"], accent=PAL["spiker"])
        if s > 20.0:
            b = ease_out(seg(s, 20.0, 20.6))
            fr.rect(140, 560, 1640, 430, "#060914", 0.85 * b, radius=18)
            lines = [
                "MODEL  ball flight with gravity, drag (C_D 0.45) and Magnus lift · ballistic jump · 3-link arm · "
                "sphere-vs-palm contact · Kalman-filtered setter · Monte Carlo, 100,000 attempts per case",
                "BALL & AIR  FIVB ball (65–67 cm, 260–280 g) · drag crisis ~14 m/s (Asai et al. 2010)",
                "SPIKE  hand 17 m/s, shoulder ~900°/s (Hu et al. 2005) · jump height & approach (Fuchs et al. 2019) · "
                "jump-height CV 6% (Lobietti et al.)",
                "TIMING  table tennis 3.1 ms at contact (Bootsma & van Wieringen 1990) · darts 3.4–7.7 ms "
                "(Smeets et al. 2002) · tapping 11 ms (Repp) · eye-to-hand delay 138 ms in spiking (Sardinha & Bootsma 1993)",
                "RELEASE  NBA free throws: angle SD 1.1–3.0°, speed SD 1.6–2.2% (McGrath et al. 2025)",
                "Characters are original. Spiker variability values are modelling assumptions anchored to the data above.",
            ]
            y = 610
            for ln in lines:
                h = fr.wrapped(ln, 180, y, 1560, 24, "med", PAL["ink2"], b, line_h=1.3)
                y += h + 14
        if s > 28.6:
            fr.rect(0, 0, W, H, "#000000", ease_io(seg(s, 28.6, 30.0)))
