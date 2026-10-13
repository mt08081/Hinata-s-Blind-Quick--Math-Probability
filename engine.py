"""
engine.py - small Skia-based motion-graphics engine for the Blind Quick video.
2D drawing helpers, a 3D pinhole camera, easing/timing, text, equations, effects.
"""
import math, os, functools
import numpy as np
import skia

W, H = 1920, 1080
FPS = 30

# ------------------------------------------------------------------ palette
PAL = dict(
    bg0="#070b18", bg1="#0f1730", bg2="#18224a",
    ink="#f4f6ff", ink2="#aab4d6", ink3="#6c769c",
    spiker="#ff5fa2", setter="#3fd6f2", hi="#ffd34d",
    good="#34d17a", palm="#1f9e5a", warn="#f2b33d", bad="#ff5470",
    court="#16224f", court2="#1b2a60", line="#e9eeff",
    skin="#f1d3bd", skin_sh="#d4ad93", hair="#1c2240", outline="#060914",
    jersey="#f4f6ff", shorts="#1d2a5c",
)


def hexc(h, a=1.0):
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return skia.Color(r, g, b, int(max(0, min(1, a)) * 255))


def mix(h1, h2, t):
    a = np.array([int(h1.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)], float)
    b = np.array([int(h2.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)], float)
    c = a + (b - a) * float(np.clip(t, 0, 1))
    return "#%02x%02x%02x" % tuple(int(round(x)) for x in c)


# ------------------------------------------------------------------ easing / timing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def seg(t, t0, t1):
    """Normalised progress of t through [t0, t1] (clamped)."""
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return clamp((t - t0) / (t1 - t0))


def ease_io(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x, p=3):
    x = clamp(x)
    return 1 - (1 - x) ** p


def ease_in(x, p=3):
    x = clamp(x)
    return x ** p


def ease_back(x, s=1.70158):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def ease_elastic(x):
    x = clamp(x)
    if x in (0, 1):
        return x
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi) / 3) + 1


def fade(t, t_in, t_out, d_in=0.35, d_out=0.35):
    """Alpha envelope: fades in at t_in, out ending at t_out."""
    return ease_io(seg(t, t_in, t_in + d_in)) * (1 - ease_io(seg(t, t_out - d_out, t_out)))


def lerp(a, b, t):
    return a + (b - a) * t


# ------------------------------------------------------------------ fonts
FONT_FILES = {
    "black": "/usr/share/fonts/opentype/inter/Inter-Black.otf",
    "blackit": "/usr/share/fonts/opentype/inter/Inter-BlackItalic.otf",
    "xbold": "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
    "xboldit": "/usr/share/fonts/opentype/inter/Inter-ExtraBoldItalic.otf",
    "bold": "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
    "semi": "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
    "med": "/usr/share/fonts/opentype/inter/Inter-Medium.otf",
    "reg": "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
    "it": "/usr/share/fonts/opentype/inter/Inter-Italic.otf",
    "dblack": "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
    "dblackit": "/usr/share/fonts/opentype/inter/InterDisplay-BlackItalic.otf",
    "jp": "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
}


@functools.lru_cache(maxsize=None)
def typeface(name):
    return skia.Typeface.MakeFromFile(FONT_FILES[name])


@functools.lru_cache(maxsize=4096)
def font(name, size):
    f = skia.Font(typeface(name), size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    if name == "jp":
        f.setEmbolden(True)
    return f


def text_width(s, name, size, spacing=0.0):
    return font(name, size).measureText(s) + spacing * max(0, len(s) - 1)


# ------------------------------------------------------------------ equations (matplotlib mathtext)
_EQ_CACHE = {}


def equation_image(tex, size=40, color="#f4f6ff"):
    """Render a mathtext string to a skia.Image (white-ish on transparent)."""
    key = (tex, size, color)
    if key in _EQ_CACHE:
        return _EQ_CACHE[key]
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import mathtext
    from matplotlib.font_manager import FontProperties
    import matplotlib.pyplot as plt
    matplotlib.rcParams["mathtext.fontset"] = "cm"
    fig = plt.figure(figsize=(0.01, 0.01), dpi=100)
    fig.patch.set_alpha(0)
    t = fig.text(0, 0, tex, fontsize=size * 0.72, color=color)
    fig.canvas.draw()
    bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
    plt.close(fig)
    w, h = int(bb.width) + 16, int(bb.height) + 16
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_alpha(0)
    fig.text(8 / w, 8 / h, tex, fontsize=size * 0.72, color=color)
    fig.canvas.draw()
    arr = np.asarray(fig.canvas.buffer_rgba()).copy()
    plt.close(fig)
    # premultiply for skia
    a = arr[..., 3:4].astype(np.float32) / 255
    arr[..., :3] = (arr[..., :3].astype(np.float32) * a).astype(np.uint8)
    img = skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
    _EQ_CACHE[key] = img
    return img


# ------------------------------------------------------------------ 3D camera
class Camera:
    def __init__(self, pos, target, up=(0, 0, 1), fov=40.0, center=None, roll=0.0):
        self.pos = np.asarray(pos, float)
        self.target = np.asarray(target, float)
        self.fov = fov
        self.cx, self.cy = center if center is not None else (W / 2, H / 2)
        f = self.target - self.pos
        f /= np.linalg.norm(f)
        upv = np.asarray(up, float)
        r = np.cross(f, upv)
        if np.linalg.norm(r) < 1e-6:
            r = np.cross(f, np.array([0, 1.0, 0]))
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        if roll:
            c, s = math.cos(roll), math.sin(roll)
            r, u = c * r + s * u, -s * r + c * u
        self.f, self.r, self.u = f, r, u
        self.focal = (H / 2) / math.tan(math.radians(fov) / 2)

    def project(self, P):
        P = np.asarray(P, float)
        d = P - self.pos
        x = d @ self.r
        y = d @ self.u
        z = d @ self.f
        zc = np.maximum(z, 1e-3)
        sx = self.cx + self.focal * x / zc
        sy = self.cy - self.focal * y / zc
        return np.stack([sx, sy], -1), z

    def px_per_m(self, depth):
        return self.focal / np.maximum(depth, 1e-3)


def cam_lerp(c1, c2, t, roll=0.0):
    t = clamp(t)
    return Camera(lerp(c1.pos, c2.pos, t), lerp(c1.target, c2.target, t), fov=lerp(c1.fov, c2.fov, t),
                  center=(lerp(c1.cx, c2.cx, t), lerp(c1.cy, c2.cy, t)), roll=roll)


def cam_orbit(target, radius, azim_deg, elev_deg, fov=40, center=None):
    a, e = math.radians(azim_deg), math.radians(elev_deg)
    pos = np.asarray(target) + radius * np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
    return Camera(pos, target, fov=fov, center=center)


# ------------------------------------------------------------------ frame / drawing
class Frame:
    def __init__(self):
        self.buf = np.zeros((H, W, 4), np.uint8)
        self.surface = skia.Surface(self.buf, colorType=skia.kBGRA_8888_ColorType)
        self.c = self.surface.getCanvas()

    # ---- basics
    def clear(self, color=PAL["bg0"]):
        self.c.clear(hexc(color))

    def array(self):
        """BGRA uint8 view of the frame (no copy)."""
        self.surface.flushAndSubmit() if hasattr(self.surface, "flushAndSubmit") else None
        return self.buf

    def paint(self, color="#ffffff", alpha=1.0, stroke=None, cap="round", join="round", blur=0.0, shader=None,
              blend=None):
        p = skia.Paint(AntiAlias=True)
        p.setColor(hexc(color, alpha))
        if stroke is not None:
            p.setStyle(skia.Paint.kStroke_Style)
            p.setStrokeWidth(stroke)
            p.setStrokeCap({"round": skia.Paint.kRound_Cap, "butt": skia.Paint.kButt_Cap,
                            "square": skia.Paint.kSquare_Cap}[cap])
            p.setStrokeJoin({"round": skia.Paint.kRound_Join, "miter": skia.Paint.kMiter_Join,
                             "bevel": skia.Paint.kBevel_Join}[join])
        if blur > 0:
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
        if shader is not None:
            p.setShader(shader)
            p.setAlphaf(alpha)
        if blend == "add":
            p.setBlendMode(skia.BlendMode.kPlus)
        elif blend == "screen":
            p.setBlendMode(skia.BlendMode.kScreen)
        elif blend == "multiply":
            p.setBlendMode(skia.BlendMode.kMultiply)
        return p

    def layer(self, alpha=1.0, bounds=None, filt=None):
        p = skia.Paint()
        p.setAlphaf(clamp(alpha))
        if filt is not None:
            p.setImageFilter(filt)
        return _Layer(self.c, p, bounds)

    # ---- primitives
    def line(self, p0, p1, w=3, color="#fff", alpha=1.0, glow=0, cap="round", blend=None):
        if alpha <= 0.003:
            return
        if glow:
            self.c.drawLine(float(p0[0]), float(p0[1]), float(p1[0]), float(p1[1]),
                            self.paint(color, alpha * 0.55, stroke=w * 2.2, cap=cap, blur=glow, blend=blend))
        self.c.drawLine(float(p0[0]), float(p0[1]), float(p1[0]), float(p1[1]),
                        self.paint(color, alpha, stroke=w, cap=cap, blend=blend))

    def polyline(self, pts, w=3, color="#fff", alpha=1.0, glow=0, closed=False, cap="round", fill=False, blend=None,
                 dash=None):
        pts = np.asarray(pts, float)
        if len(pts) < 2 or alpha <= 0.003:
            return
        path = skia.Path()
        path.moveTo(*pts[0])
        for q in pts[1:]:
            path.lineTo(float(q[0]), float(q[1]))
        if closed:
            path.close()
        if fill:
            self.c.drawPath(path, self.paint(color, alpha, blend=blend))
            return
        if glow:
            self.c.drawPath(path, self.paint(color, alpha * 0.5, stroke=w * 2.4, cap=cap, blur=glow, blend=blend))
        p = self.paint(color, alpha, stroke=w, cap=cap, blend=blend)
        if dash:
            p.setPathEffect(skia.DashPathEffect.Make(dash, 0))
        self.c.drawPath(path, p)

    def polygon(self, pts, color="#fff", alpha=1.0, stroke=None, blur=0, shader=None, blend=None):
        pts = np.asarray(pts, float)
        if len(pts) < 3 or alpha <= 0.003:
            return
        path = skia.Path()
        path.moveTo(*pts[0])
        for q in pts[1:]:
            path.lineTo(float(q[0]), float(q[1]))
        path.close()
        self.c.drawPath(path, self.paint(color, alpha, stroke=stroke, blur=blur, shader=shader, blend=blend))

    def circle(self, c, r, color="#fff", alpha=1.0, stroke=None, glow=0, blur=0, shader=None, blend=None):
        if alpha <= 0.003 or r <= 0:
            return
        if glow:
            self.c.drawCircle(float(c[0]), float(c[1]), float(r), self.paint(color, alpha * 0.6, blur=glow, blend=blend))
        self.c.drawCircle(float(c[0]), float(c[1]), float(r),
                          self.paint(color, alpha, stroke=stroke, blur=blur, shader=shader, blend=blend))

    def rect(self, x, y, w, h, color="#fff", alpha=1.0, radius=0, stroke=None, blur=0, shader=None, blend=None):
        if alpha <= 0.003:
            return
        r = skia.Rect.MakeXYWH(float(x), float(y), float(w), float(h))
        p = self.paint(color, alpha, stroke=stroke, blur=blur, shader=shader, blend=blend)
        if radius:
            self.c.drawRoundRect(r, radius, radius, p)
        else:
            self.c.drawRect(r, p)

    def image(self, img, x, y, scale=1.0, alpha=1.0, anchor="tl"):
        w, h = img.width() * scale, img.height() * scale
        if anchor == "c":
            x, y = x - w / 2, y - h / 2
        elif anchor == "lc":
            y = y - h / 2
        elif anchor == "rc":
            x, y = x - w, y - h / 2
        elif anchor == "tc":
            x = x - w / 2
        p = skia.Paint(AntiAlias=True)
        p.setAlphaf(clamp(alpha))
        self.c.drawImageRect(img, skia.Rect.MakeXYWH(x, y, w, h), skia.SamplingOptions(skia.FilterMode.kLinear), p)
        return w, h

    # ---- text
    def text(self, s, x, y, size=40, fnt="bold", color=PAL["ink"], alpha=1.0, align="left", spacing=0.0,
             skew=0.0, stroke=0, stroke_color=PAL["outline"], glow=0, glow_color=None, shadow=None, scale=1.0,
             rotate=0.0):
        if alpha <= 0.003 or not s:
            return 0
        f = font(fnt, size)
        if skew:
            f = skia.Font(f.getTypeface(), size)
            f.setEdging(skia.Font.Edging.kAntiAlias)
            f.setSkewX(skew)
            if fnt == "jp":
                f.setEmbolden(True)
        w = f.measureText(s) + spacing * max(0, len(s) - 1)
        x0 = {"left": x, "center": x - w / 2, "right": x - w}[align]
        self.c.save()
        if scale != 1.0 or rotate:
            self.c.translate(x, y)
            if rotate:
                self.c.rotate(rotate)
            self.c.scale(scale, scale)
            self.c.translate(-x, -y)

        def draw(paint, dx=0, dy=0):
            if spacing == 0:
                self.c.drawString(s, x0 + dx, y + dy, f, paint)
            else:
                cx = x0
                for ch in s:
                    self.c.drawString(ch, cx + dx, y + dy, f, paint)
                    cx += f.measureText(ch) + spacing

        if glow:
            draw(self.paint(glow_color or color, alpha * 0.8, blur=glow))
        if shadow:
            dx, dy, sc = shadow
            draw(self.paint(sc, alpha), dx, dy)
        if stroke:
            draw(self.paint(stroke_color, alpha, stroke=stroke, join="round"))
        draw(self.paint(color, alpha))
        self.c.restore()
        return w

    def wrapped(self, s, x, y, max_w, size=36, fnt="med", color=PAL["ink"], alpha=1.0, line_h=1.3, align="left"):
        words = s.split(" ")
        lines, cur = [], ""
        for wd in words:
            trial = (cur + " " + wd).strip()
            if text_width(trial, fnt, size) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        for i, ln in enumerate(lines):
            self.text(ln, x, y + i * size * line_h, size, fnt, color, alpha, align)
        return len(lines) * size * line_h

    def rich(self, parts, x, y, size=40, align="left", alpha=1.0):
        """parts: list of (text, font, color). Single line."""
        total = sum(text_width(t, f, size) for t, f, _ in parts)
        cx = {"left": x, "center": x - total / 2, "right": x - total}[align]
        for t, f, col in parts:
            self.text(t, cx, y, size, f, col, alpha)
            cx += text_width(t, f, size)
        return total

    def eq(self, tex, x, y, size=44, color=PAL["ink"], alpha=1.0, anchor="tl", glow=0):
        img = equation_image(tex, size, color)
        if glow:
            with self.layer(alpha * 0.5, filt=skia.ImageFilters.Blur(glow, glow)):
                self.image(img, x, y, 1.0, 1.0, anchor)
        return self.image(img, x, y, 1.0, alpha, anchor)


class _Layer:
    def __init__(self, c, p, bounds):
        self.c, self.p, self.b = c, p, bounds

    def __enter__(self):
        self.c.saveLayer(self.b, self.p)
        return self

    def __exit__(self, *a):
        self.c.restore()


# ------------------------------------------------------------------ backgrounds & effects
_IMG_CACHE = {}


def _cached(key, make):
    if key not in _IMG_CACHE:
        s = skia.Surface(W, H)
        make(s.getCanvas())
        _IMG_CACHE[key] = s.makeImageSnapshot()
    return _IMG_CACHE[key]


_BG_ARR = {}


def background(fr: Frame, t=0, tone=0.0, hue=None):
    """Vertical gradient background (cached as a BGRA array, copied in ~1 ms)."""
    key = (round(float(tone), 2), hue)
    if key not in _BG_ARR:
        tmp = Frame()
        sh = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, H)],
                                            [hexc(mix(PAL["bg1"], hue or PAL["bg1"], key[0])), hexc(PAL["bg0"])])
        p = skia.Paint(); p.setShader(sh); p.setDither(True)
        tmp.c.drawPaint(p)
        _BG_ARR[key] = tmp.buf.copy()
    fr.buf[:] = _BG_ARR[key]


def vignette(fr: Frame, strength=0.65):
    """No-op: the vignette is applied by ffmpeg at encode time (much cheaper)."""
    return


def screentone(fr: Frame, alpha=0.12, spacing=14, r=2.2, color="#ffffff", region=None, angle=0.35):
    """Manga halftone dots (grid of dots), optional rect region (x,y,w,h)."""
    if alpha <= 0.003:
        return
    x0, y0, w, h = region or (0, 0, W, H)
    p = fr.paint(color, alpha)
    fr.c.save()
    fr.c.clipRect(skia.Rect.MakeXYWH(x0, y0, w, h))
    fr.c.translate(x0 + w / 2, y0 + h / 2)
    fr.c.rotate(math.degrees(angle))
    span = int(max(w, h) * 0.8 / spacing) + 2
    pts = [skia.Point(i * spacing, j * spacing) for i in range(-span, span) for j in range(-span, span)]
    p.setStrokeWidth(r * 2)
    p.setStrokeCap(skia.Paint.kRound_Cap)
    fr.c.drawPoints(skia.Canvas.kPoints_PointMode, pts, p)
    fr.c.restore()


def speed_lines(fr: Frame, t, center=(W / 2, H / 2), n=90, color="#ffffff", alpha=0.35, inner=260, seed=3,
                radial=True, direction=(1, 0), speed=1.0, width=(1.5, 5)):
    """Anime speed lines: radial focus lines (radial=True) or parallel streaks."""
    if alpha <= 0.003:
        return
    rng = np.random.default_rng(seed + int(t * 24 * speed))
    if radial:
        ang = rng.uniform(0, 2 * np.pi, n)
        r0 = inner + rng.uniform(0, 140, n)
        r1 = r0 + rng.uniform(300, 1100, n)
        for a, a0, a1 in zip(ang, r0, r1):
            wdt = rng.uniform(*width)
            d = np.array([math.cos(a), math.sin(a)])
            p0 = np.array(center) + d * a0
            p1 = np.array(center) + d * a1
            path = skia.Path()
            nrm = np.array([-d[1], d[0]]) * wdt
            path.moveTo(*p0)
            path.lineTo(*(p1 + nrm))
            path.lineTo(*(p1 - nrm))
            path.close()
            fr.c.drawPath(path, fr.paint(color, alpha * rng.uniform(0.4, 1.0)))
    else:
        d = np.array(direction, float); d /= np.linalg.norm(d)
        nrm = np.array([-d[1], d[0]])
        for _ in range(n):
            off = rng.uniform(-H, H)
            along = rng.uniform(-W, W)
            L = rng.uniform(150, 600)
            c0 = np.array(center) + nrm * off + d * along
            fr.line(c0, c0 + d * L, rng.uniform(*width), color, alpha * rng.uniform(0.3, 1.0))


def impact_burst(fr: Frame, center, t, size=1.0, color="#ffffff", seed=1):
    """Starburst spikes + rings for an impact frame; t in [0,1] lifetime."""
    if t <= 0 or t >= 1:
        return
    rng = np.random.default_rng(seed)
    a = 1 - t
    n = 22
    for i in range(n):
        ang = (i / n) * 2 * np.pi + rng.uniform(-0.12, 0.12)
        L = size * (180 + rng.uniform(0, 260)) * ease_out(min(1, t * 3))
        wdt = size * rng.uniform(10, 26) * a
        d = np.array([math.cos(ang), math.sin(ang)])
        nrm = np.array([-d[1], d[0]])
        c = np.array(center)
        fr.polygon([c + nrm * wdt, c + d * L, c - nrm * wdt], color, a * 0.9)
    for k in range(3):
        rr = size * (60 + 260 * ease_out(t) * (1 + 0.4 * k))
        fr.circle(center, rr, color, a * (0.6 - 0.15 * k), stroke=size * (10 - 3 * k) * a)


def particles(fr: Frame, center, t, n=30, color="#ffffff", speed=500, seed=0, size=4, gravity=600, alpha=1.0):
    if t <= 0 or t >= 1.5:
        return
    rng = np.random.default_rng(seed)
    ang = rng.uniform(0, 2 * np.pi, n)
    sp = rng.uniform(0.3, 1.0, n) * speed
    for a, s in zip(ang, sp):
        x = center[0] + math.cos(a) * s * t
        y = center[1] + math.sin(a) * s * t + 0.5 * gravity * t * t
        fr.circle((x, y), size * (1 - t / 1.5), color, alpha * (1 - t / 1.5))


def film_grain(fr: Frame, t, alpha=0.035, seed=0):
    rng = np.random.default_rng(int(t * 1000) + seed)
    n = 900
    xs = rng.uniform(0, W, n); ys = rng.uniform(0, H, n)
    p = fr.paint("#ffffff", alpha)
    p.setStrokeWidth(2)
    fr.c.drawPoints(skia.Canvas.kPoints_PointMode, [skia.Point(float(x), float(y)) for x, y in zip(xs, ys)], p)


def letterbox(fr: Frame, amount):
    if amount <= 0:
        return
    hh = 110 * amount
    fr.rect(0, 0, W, hh, "#000000", 1.0)
    fr.rect(0, H - hh, W, hh, "#000000", 1.0)


# ------------------------------------------------------------------ UI pieces
def caption(fr: Frame, s, alpha=1.0, y=H - 92, size=40, sub=None, color=PAL["ink"], width=1500):
    """Bottom caption bar."""
    if alpha <= 0.003:
        return
    tw = min(width, text_width(s, "semi", size) + 80)
    fr.rect(W / 2 - tw / 2, y - size - 22, tw, size + 46 + (size * 0.95 if sub else 0), "#05070f", alpha * 0.78,
            radius=14)
    fr.text(s, W / 2, y, size, "semi", color, alpha, "center")
    if sub:
        fr.text(sub, W / 2, y + size * 1.0, size * 0.72, "med", PAL["ink2"], alpha, "center")


def chip(fr: Frame, s, x, y, color, alpha=1.0, size=26, fnt="xbold", fill_alpha=0.18, align="left", ink=None):
    w = text_width(s, fnt, size) + 34
    x0 = {"left": x, "center": x - w / 2, "right": x - w}[align]
    fr.rect(x0, y - size * 0.95, w, size * 1.45, color, alpha * fill_alpha, radius=size * 0.72)
    fr.rect(x0, y - size * 0.95, w, size * 1.45, color, alpha * 0.9, radius=size * 0.72, stroke=2)
    fr.text(s, x0 + 17, y + size * 0.05, size, fnt, ink or color, alpha)
    return w


def slam_text(fr: Frame, s, x, y, t, size=120, color=PAL["ink"], accent=PAL["spiker"], fnt="dblackit",
              align="center", dur=0.35):
    """Anime title slam: scales down from big with an offset colour shadow."""
    if t <= 0:
        return
    k = ease_out(seg(t, 0, dur), 4)
    sc = 1.0 + (1 - k) * 0.9
    al = clamp(t / (dur * 0.5))
    fr.text(s, x + 8, y + 8, size, fnt, accent, al, align, scale=sc)
    fr.text(s, x, y, size, fnt, color, al, align, scale=sc, stroke=6, stroke_color=PAL["outline"])


def sfx_text(fr: Frame, s, x, y, t, size=150, color="#ffffff", outline=PAL["outline"], rot=-8, dur=0.25, alpha=1.0):
    """Japanese onomatopoeia stamp."""
    if t <= 0:
        return
    k = ease_back(seg(t, 0, dur), 2.5)
    sc = 0.4 + 0.6 * k
    al = alpha * clamp(t / 0.06)
    fr.text(s, x, y, size, "jp", color, al, "center", stroke=size * 0.14, stroke_color=outline, scale=sc, rotate=rot)
