"""common.py - shared scene helpers: data, the play renderer, cut-in panels, transitions."""
import json, math, os
import numpy as np
import skia
from scipy.interpolate import PchipInterpolator
from engine import *
import world as wd
import freak_quick_model as fq

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "results.json")))
SMP = dict(np.load(os.path.join(HERE, "samples.npz")))
PLAN = wd.PLAN
T_HIT = PLAN.T
T_TO = PLAN.t_to
NOM = wd.nominal_attempt()
_NOM_BALL = None


def nominal_ball():
    global _NOM_BALL
    if _NOM_BALL is None:
        _NOM_BALL = wd.BallPath(t_hit=T_HIT, outcome=fq.CLEAN)
    return _NOM_BALL


def pct(x, nd=0):
    return ("{:.%df}%%" % nd).format(100 * x)


def mc(label):
    return R["mc"][label]


# ------------------------------------------------------------------ time remapping
class TimeMap:
    def __init__(self, keys):
        s, tp = zip(*keys)
        self.f = PchipInterpolator(np.array(s, float), np.array(tp, float), extrapolate=True)
        self.s0, self.s1 = s[0], s[-1]
        self.tp0, self.tp1 = tp[0], tp[-1]

    def __call__(self, s):
        if s <= self.s0:
            return self.tp0
        if s >= self.s1:
            return self.tp1
        return float(self.f(s))


# ------------------------------------------------------------------ the play
def draw_play(fr, cam, tp, att=None, ball=None, setter=True, spiker=True, ball_on=True, court=True,
              spiker_alpha=1.0, setter_alpha=1.0, trail=0.0, ball_glow="#ffffff", net=True, show_far=True,
              ghost_ball=False, number=False):
    att = att or NOM
    ball = ball or nominal_ball()
    if court:
        wd.draw_court(fr, cam, net=net, show_far=show_far)
    P = ball.pos(tp)
    if ball_on:
        wd.ball_shadow(fr, cam, P, 0.45)
    items = []
    if setter and setter_alpha > 0:
        Jt = wd.setter_pose(tp)
        _, z = cam.project(np.array([Jt["neck"]]))
        items.append((z[0], lambda: wd.draw_athlete(fr, cam, Jt, PAL["setter"], glow=PAL["setter"], alpha=setter_alpha,
                                                     number="2" if number else None)))
    if spiker and spiker_alpha > 0:
        Js = wd.spiker_pose(att, tp)
        _, z = cam.project(np.array([Js["neck"]]))
        items.append((z[0], lambda: wd.draw_athlete(fr, cam, Js, PAL["spiker"], glow=PAL["spiker"], alpha=spiker_alpha,
                                                     number="4" if number else None)))
    if ball_on:
        _, zb = cam.project(np.array([P]))
        def draw_b():
            if trail > 0 and tp > 0:
                ts = np.linspace(max(0.0, tp - trail), tp, 14)
                pts = np.array([ball.pos(x) for x in ts])
                s, z = cam.project(pts)
                ok = z > 0.2
                if ok.sum() > 2:
                    for i in range(len(s) - 1):
                        if ok[i] and ok[i + 1]:
                            fr.line(s[i], s[i + 1], 3 + 10 * i / len(s), PAL["setter"], 0.12 + 0.6 * i / len(s))
            wd.draw_ball(fr, cam, P, glow=ball_glow, ghost=ghost_ball, rot=0.0)
        items.append((zb[0] - 0.05, draw_b))
    items.sort(key=lambda x: -x[0])
    for _, fn in items:
        fn()
    return P


def world_path(fr, cam, pts, color, w=4, alpha=1.0, glow=6, dash=None, reveal=1.0):
    pts = np.asarray(pts)
    n = max(2, int(len(pts) * clamp(reveal)))
    s, z = cam.project(pts[:n])
    ok = z > 0.2
    s = s[ok]
    if len(s) >= 2:
        fr.polyline(s, w, color, alpha, glow=glow, dash=dash)
    return s


def label_at(fr, cam, P, text, color=PAL["ink"], dx=20, dy=-20, size=28, alpha=1.0, fnt="semi", dot=True, align="left"):
    s, z = cam.project(np.array([P]))
    if z[0] <= 0.2:
        return None
    p = s[0]
    if dot:
        fr.circle(p, 7, PAL["outline"], alpha)
        fr.circle(p, 5, color, alpha)
    if dx or dy:
        fr.line(p, p + np.array([dx * 0.8, dy * 0.8]), 2, color, alpha * 0.8)
    fr.text(text, p[0] + dx + (6 if align == "left" else -6), p[1] + dy, size, fnt, color, alpha, align,
            stroke=4, stroke_color=PAL["bg0"])
    return p


# ------------------------------------------------------------------ manga cut-in panels
def slanted_panel(fr, x, y, w, h, slant=60, alpha=1.0, fill="#0b0f22", border="#f4f6ff", bw=6):
    pts = [(x + slant, y), (x + w, y), (x + w - slant, y + h), (x, y + h)]
    fr.polygon(pts, fill, alpha)
    fr.polygon(pts, border, alpha, stroke=bw)
    return pts


def clip_poly(fr, pts):
    path = skia.Path()
    path.moveTo(*pts[0])
    for q in pts[1:]:
        path.lineTo(*q)
    path.close()
    fr.c.save()
    fr.c.clipPath(path, doAntiAlias=True)


def draw_eye(fr, cx, cy, size, close=0.0, alpha=1.0, iris=PAL["spiker"]):
    """A generic stylised anime eye. close: 0 open -> 1 shut."""
    w, h = size, size * 0.42
    lid_y = lerp(cy - h * 0.62, cy + h * 0.18, ease_io(close))
    # white of the eye (almond)
    almond = skia.Path()
    almond.moveTo(cx - w / 2, cy)
    almond.quadTo(cx, cy - h * 1.15, cx + w / 2, cy - h * 0.05)
    almond.quadTo(cx, cy + h * 0.95, cx - w / 2, cy)
    almond.close()
    fr.c.save()
    fr.c.clipPath(almond, doAntiAlias=True)
    fr.rect(cx - w, cy - h * 2, 2 * w, 4 * h, "#f4f6ff", alpha)
    sh = skia.GradientShader.MakeRadial(skia.Point(cx + w * 0.02, cy - h * 0.05), h * 0.95,
                                        [hexc(mix(iris, "#ffffff", 0.35)), hexc(iris), hexc(mix(iris, "#000000", 0.55))],
                                        [0.0, 0.55, 1.0])
    fr.circle((cx + w * 0.02, cy - h * 0.02), h * 0.88, iris, alpha, shader=sh)
    fr.circle((cx + w * 0.02, cy - h * 0.02), h * 0.38, "#0a0d1c", alpha)
    fr.circle((cx - w * 0.07, cy - h * 0.32), h * 0.2, "#ffffff", alpha)
    fr.circle((cx + w * 0.12, cy + h * 0.25), h * 0.08, "#ffffff", alpha * 0.8)
    # upper lid sweeps down (skin colour) as it closes
    fr.rect(cx - w, cy - h * 3, 2 * w, (lid_y - (cy - h * 3)), "#e7d6cb", alpha)
    fr.c.restore()
    # lash line follows the lid
    lash = skia.Path()
    lash.moveTo(cx - w * 0.55, cy + h * 0.05)
    lash.quadTo(cx, lid_y - h * 0.55 * (1 - close) + h * 0.3 * close, cx + w * 0.56, cy - h * 0.1)
    fr.c.drawPath(lash, fr.paint("#0a0d1c", alpha, stroke=size * 0.045))
    if close > 0.85:
        # closed-eye crease with lashes
        for k in range(5):
            u = 0.2 + k * 0.15
            px = cx - w * 0.5 + w * u
            py = cy + h * 0.15 + math.sin(u * math.pi) * h * 0.12
            fr.line((px, py), (px - w * 0.03, py + h * 0.28), size * 0.018, "#0a0d1c", alpha * (close - 0.85) / 0.15)
    # brow
    brow = skia.Path()
    brow.moveTo(cx - w * 0.55, cy - h * 1.35)
    brow.quadTo(cx, cy - h * 1.75 - h * 0.15 * close, cx + w * 0.5, cy - h * 1.3)
    fr.c.drawPath(brow, fr.paint("#1c2240", alpha, stroke=size * 0.05))


def invert(fr, amount=1.0):
    if amount <= 0:
        return
    b = fr.buf
    if amount >= 1:
        b[..., :3] = 255 - b[..., :3]
    else:
        inv = 255 - b[..., :3].astype(np.int16)
        b[..., :3] = (b[..., :3] * (1 - amount) + inv * amount).astype(np.uint8)


def monochrome(fr, amount=1.0, tint=(255, 255, 255)):
    b = fr.buf
    lum = (0.114 * b[..., 0] + 0.587 * b[..., 1] + 0.299 * b[..., 2])
    for i in range(3):
        b[..., i] = (b[..., i] * (1 - amount) + lum * amount * tint[2 - i] / 255).astype(np.uint8)


def darken(fr, amount):
    if amount > 0:
        fr.rect(0, 0, W, H, "#03050c", amount)


def slash_wipe(fr, t, dur=0.45, color=PAL["spiker"], out=False):
    """Scene-exit wipe: a slanted dark panel sweeps in from the left and covers the frame at t = dur."""
    if t < 0:
        return
    u = ease_in(clamp(t / dur), 2)
    sl = 420
    x = lerp(-sl - 200, W + sl + 200, u)
    pts = [(-500, -60), (x + sl / 2, -60), (x - sl / 2, H + 60), (-500, H + 60)]
    fr.polygon(pts, "#05070f", 1.0)
    fr.line((x + sl / 2 + 10, -60), (x - sl / 2 + 10, H + 60), 22, color, 1.0)
    fr.line((x + sl / 2 + 34, -60), (x - sl / 2 + 34, H + 60), 5, "#ffffff", 0.9)


def wipe_in(fr, t, dur=0.38, color=PAL["hi"]):
    """Scene-entry wipe: the dark panel slides off to the right, revealing the new scene."""
    if t >= dur:
        return
    u = ease_out(clamp(t / dur), 2)
    sl = 420
    x = lerp(-sl - 200, W + sl + 200, u)
    pts = [(x + sl / 2, -60), (W + 500, -60), (W + 500, H + 60), (x - sl / 2, H + 60)]
    fr.polygon(pts, "#05070f", 1.0)
    fr.line((x + sl / 2 - 10, -60), (x - sl / 2 - 10, H + 60), 22, color, 1.0)
    fr.line((x + sl / 2 - 34, -60), (x - sl / 2 - 34, H + 60), 5, "#ffffff", 0.9)


def flash(fr, amount, color="#ffffff"):
    if amount > 0:
        fr.rect(0, 0, W, H, color, clamp(amount))


def section_tag(fr, num, title, t, alpha=1.0, y=78):
    """Small top-left chapter tag: '02  THE BALL'."""
    k = ease_out(seg(t, 0.1, 0.6))
    a = alpha * k
    x = 70 - (1 - k) * 40
    fr.text(num, x, y, 30, "dblackit", PAL["hi"], a)
    fr.text(title, x + 64, y, 30, "xbold", PAL["ink"], a, spacing=3)
    fr.line((x, y + 16), (x + 64 + text_width(title, "xbold", 30, 3), y + 16), 3, PAL["hi"], a * 0.8)


def big_number(fr, s, x, y, size=120, color=PAL["hi"], alpha=1.0, align="center", sub=None, sub_size=30):
    fr.text(s, x + 6, y + 6, size, "dblackit", PAL["outline"], alpha, align)
    fr.text(s, x, y, size, "dblackit", color, alpha, align)
    if sub:
        fr.text(sub, x, y + sub_size * 1.6, sub_size, "semi", PAL["ink2"], alpha, align)


def shake_offset(t, t0, dur=0.35, amp=18, seed=0):
    if t < t0 or t > t0 + dur:
        return 0.0, 0.0
    k = 1 - (t - t0) / dur
    rng = np.random.default_rng(int((t - t0) * 60) + seed)
    return rng.uniform(-amp, amp) * k, rng.uniform(-amp, amp) * k
