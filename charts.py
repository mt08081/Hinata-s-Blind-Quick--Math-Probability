"""charts.py - chart primitives in the video's visual language (thin marks, recessive grid)."""
import math
import numpy as np
from engine import Frame, PAL, text_width, clamp, ease_out, ease_io, seg, lerp, mix

GRID = "#2a3560"
AXIS = "#56628f"


class Axes:
    def __init__(self, x, y, w, h, xlim, ylim, xlog=False):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.xlim, self.ylim = xlim, ylim
        self.xlog = xlog

    def px(self, xv):
        a, b = self.xlim
        if self.xlog:
            return self.x + (math.log10(xv) - math.log10(a)) / (math.log10(b) - math.log10(a)) * self.w
        return self.x + (xv - a) / (b - a) * self.w

    def py(self, yv):
        a, b = self.ylim
        return self.y + self.h - (yv - a) / (b - a) * self.h

    def pt(self, xv, yv):
        return np.array([self.px(xv), self.py(yv)])

    def frame(self, fr: Frame, alpha=1.0, xticks=(), yticks=(), xfmt="{:g}", yfmt="{:g}", xlabel=None, ylabel=None,
              size=24, grid=True):
        if grid:
            for v in yticks:
                fr.line((self.x, self.py(v)), (self.x + self.w, self.py(v)), 1.2, GRID, alpha)
        fr.line((self.x, self.y + self.h), (self.x + self.w, self.y + self.h), 2, AXIS, alpha)
        fr.line((self.x, self.y), (self.x, self.y + self.h), 2, AXIS, alpha)
        for v in xticks:
            fr.line((self.px(v), self.y + self.h), (self.px(v), self.y + self.h + 8), 2, AXIS, alpha)
            fr.text(xfmt.format(v), self.px(v), self.y + self.h + 14 + size, size, "med", PAL["ink2"], alpha, "center")
        for v in yticks:
            fr.text(yfmt.format(v), self.x - 14, self.py(v) + size * 0.35, size, "med", PAL["ink2"], alpha, "right")
        if xlabel:
            fr.text(xlabel, self.x + self.w / 2, self.y + self.h + 2.4 * size + 18, size * 1.05, "semi", PAL["ink"], alpha,
                    "center")
        if ylabel:
            fr.text(ylabel, self.x, self.y - 22, size * 1.05, "semi", PAL["ink"], alpha, "left")

    def series(self, fr: Frame, xs, ys, color, alpha=1.0, reveal=1.0, w=4, dots=True, glow=0, label=None,
               label_size=26, label_dy=0):
        xs = np.asarray(xs, float); ys = np.asarray(ys, float)
        n = len(xs)
        if n < 2 or reveal <= 0:
            return
        k = reveal * (n - 1)
        i = int(math.floor(k))
        pts = [self.pt(xs[j], ys[j]) for j in range(min(i + 1, n))]
        if i < n - 1:
            f = k - i
            pts.append(self.pt(lerp(xs[i], xs[i + 1], f), lerp(ys[i], ys[i + 1], f)))
        fr.polyline(pts, w, color, alpha, glow=glow)
        if dots:
            for j in range(min(i + 1, n)):
                fr.circle(self.pt(xs[j], ys[j]), 6, PAL["bg0"], alpha)
                fr.circle(self.pt(xs[j], ys[j]), 5, color, alpha)
        if label and reveal >= 0.999:
            end = pts[-1]
            fr.text(label, end[0] + 14, end[1] + 9 + label_dy, label_size, "semi", PAL["ink"], alpha)

    def hline(self, fr, yv, color, alpha=1.0, label=None, w=2, dash=(10, 8), size=24):
        fr.polyline([self.pt(self.xlim[0], yv), self.pt(self.xlim[1], yv)], w, color, alpha, dash=dash)
        if label:
            fr.text(label, self.x + self.w - 6, self.py(yv) - 10, size, "semi", color, alpha, "right")

    def vline(self, fr, xv, color, alpha=1.0, label=None, w=2, dash=(10, 8), size=24, top=True):
        fr.polyline([self.pt(xv, self.ylim[0]), self.pt(xv, self.ylim[1])], w, color, alpha, dash=dash)
        if label:
            fr.text(label, self.px(xv) + 10, self.y + (20 if top else self.h - 12), size, "semi", color, alpha)


def hbars(fr: Frame, rows, x, y, w, row_h, vmax, t_reveal=1.0, alpha=1.0, size=26, label_w=380, unit="",
          fmt="{:.1f}", stagger=0.08, value_color=None):
    """rows: list of (label, value, color[, sublabel]). Horizontal bars, drawn top->bottom with stagger."""
    for i, row in enumerate(rows):
        lab, val, col = row[0], row[1], row[2]
        k = ease_out(clamp((t_reveal - i * stagger) / 0.5))
        if k <= 0:
            continue
        yy = y + i * row_h
        fr.text(lab, x + label_w - 18, yy + row_h * 0.5 + size * 0.35, size, "semi", PAL["ink"], alpha * k, "right")
        bw = max(4, (w - label_w - 120) * val / vmax * k)
        fr.rect(x + label_w, yy + row_h * 0.18, bw, row_h * 0.64, col, alpha * k, radius=4)
        fr.text(fmt.format(val * k) + unit, x + label_w + bw + 12, yy + row_h * 0.5 + size * 0.35, size, "bold",
                value_color or PAL["ink"], alpha * k)


def stacked_bar(fr: Frame, x, y, w, h, parts, alpha=1.0, reveal=1.0, gap=2, label_min=0.06, size=24):
    """parts: list of (fraction, color, label). Horizontal stacked bar with 2px gaps."""
    cx = x
    total_w = w * reveal
    for frac, col, lab in parts:
        pw = frac * total_w
        if pw > gap:
            fr.rect(cx, y, pw - gap, h, col, alpha, radius=3)
            if frac >= label_min and reveal > 0.98:
                hx = col.lstrip("#"); lum = (0.299 * int(hx[0:2], 16) + 0.587 * int(hx[2:4], 16) + 0.114 * int(hx[4:6], 16)) / 255
                fr.text("%.0f%%" % (frac * 100) if frac >= 0.095 else "%.1f%%" % (frac * 100), cx + (pw - gap) / 2,
                        y + h / 2 + size * 0.36, size, "bold", "#0b1022" if lum > 0.55 else "#ffffff", alpha, "center")
        cx += pw


def seq_color(v, lo="#14204a", hi="#cde2fb"):
    """Sequential one-hue ramp for dark surfaces: low recedes into the background, high is bright."""
    return mix(lo, hi, clamp(v) ** 0.8)
