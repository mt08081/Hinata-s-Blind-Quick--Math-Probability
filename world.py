"""
world.py - the 3D world of the video: court, net, ball, athletes, and the play timeline.
All athlete arm motion near contact comes straight from freak_quick_model (no faking).
"""
import math
import numpy as np
import skia
import freak_quick_model as fq
from engine import Frame, Camera, PAL, hexc, mix, clamp, ease_io, seg, lerp, W, H

M = fq.Model()
PLAN = fq.make_plan(M)
SPIN0 = np.array(M.scene.release_spin)
G = 9.81
R_BALL = M.ball.radius


# ================================================================== court
def clip_project(cam, P, z_near=0.15):
    """Project a planar polygon (k,3) with near-plane clipping. Returns (m,2) screen points or None."""
    P = np.asarray(P, float)
    d = P - cam.pos
    zc = d @ cam.f
    out = []
    k = len(P)
    for i in range(k):
        a, b = P[i], P[(i + 1) % k]
        za, zb = zc[i], zc[(i + 1) % k]
        if za >= z_near:
            out.append(a)
        if (za >= z_near) != (zb >= z_near):
            tt = (z_near - za) / (zb - za)
            out.append(a + (b - a) * tt)
    if len(out) < 3:
        return None
    s, _ = cam.project(np.array(out))
    return s


def _path_from(polys):
    path = skia.Path()
    for s in polys:
        if s is None:
            continue
        path.moveTo(float(s[0][0]), float(s[0][1]))
        for q in s[1:]:
            path.lineTo(float(q[0]), float(q[1]))
        path.close()
    return path


def _floor_rect(x0, x1, y0, y1, z=0.0):
    return np.array([[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]])


def court_lines_world(show_far=True):
    w = 0.025
    ymax = 9 if show_far else 0.0
    quads = []
    for x in (-4.5, 4.5):
        quads.append(_floor_rect(x - w, x + w, -9 - w, ymax + w))
    for y in ((-9, -3, 0, 3, 9) if show_far else (-9, -3, 0)):
        quads.append(_floor_rect(-4.5 - w, 4.5 + w, y - w, y + w))
    return quads


def draw_court(fr, cam, alpha=1.0, lines_alpha=0.85, net=True, show_far=True, glow=True):
    if alpha <= 0:
        return
    floor = clip_project(cam, _floor_rect(-14, 14, -18, 18))
    if floor is not None:
        fr.polygon(floor, "#0a1029", alpha)
    court = clip_project(cam, _floor_rect(-4.5, 4.5, -9, 9 if show_far else 0.0))
    if court is not None:
        fr.polygon(court, PAL["court"], alpha)
    for y0, y1 in ((-3, 0), (0, 3)) if show_far else ((-3, 0),):
        q = clip_project(cam, _floor_rect(-4.5, 4.5, y0, y1))
        if q is not None:
            fr.polygon(q, PAL["court2"], alpha)
    path = _path_from([clip_project(cam, q) for q in court_lines_world(show_far)])
    if glow:
        fr.c.drawPath(path, fr.paint(PAL["line"], alpha * lines_alpha * 0.10, stroke=9))
        fr.c.drawPath(path, fr.paint(PAL["line"], alpha * lines_alpha * 0.18, stroke=4))
    fr.c.drawPath(path, fr.paint(PAL["line"], alpha * lines_alpha))
    if net:
        draw_net(fr, cam, alpha)


def _vquad(x0, x1, z0, z1, y=0.0):
    return np.array([[x0, y, z0], [x1, y, z0], [x1, y, z1], [x0, y, z1]])


def draw_net(fr, cam, alpha=1.0, mesh=True):
    top, depth = 2.43, 1.0
    # posts (as vertical quads facing the camera roughly)
    posts = [_vquad(x - 0.045, x + 0.045, 0, top + 0.12) for x in (-5.0, 5.0)]
    fr.c.drawPath(_path_from([clip_project(cam, q) for q in posts]), fr.paint("#39426b", alpha))
    if mesh:
        pts = []
        for x in np.arange(-4.5, 4.51, 0.1):
            pts.append(([x, 0, top - depth], [x, 0, top]))
        for z in np.arange(top - depth, top + 0.001, 0.1):
            pts.append(([-4.5, 0, z], [4.5, 0, z]))
        P = np.array(pts).reshape(-1, 3)
        s, zc = cam.project(P)
        path = skia.Path()
        for i in range(0, len(P), 2):
            if zc[i] > 0.15 and zc[i + 1] > 0.15:
                path.moveTo(float(s[i][0]), float(s[i][1])); path.lineTo(float(s[i + 1][0]), float(s[i + 1][1]))
        fr.c.drawPath(path, fr.paint("#c9d2ff", alpha * 0.22, stroke=1.1))
    bands = [_vquad(-4.55, 4.55, top - 0.07, top), _vquad(-4.55, 4.55, top - depth - 0.05, top - depth)]
    fr.c.drawPath(_path_from([clip_project(cam, q) for q in bands]), fr.paint("#f4f6ff", alpha))
    red, white = [], []
    for x in (-4.5, 4.5):  # antennas, red/white 10 cm bands
        for k in range(18):
            z0 = top - 0.5 + k * 0.1
            q = _vquad(x - 0.012, x + 0.012, z0, z0 + 0.1)
            (red if k % 2 == 0 else white).append(clip_project(cam, q))
    fr.c.drawPath(_path_from(red), fr.paint("#ff4d5e", alpha))
    fr.c.drawPath(_path_from(white), fr.paint("#f4f6ff", alpha))


# ================================================================== ball
def draw_ball(fr, cam, P, rot=0.0, alpha=1.0, glow=None, scale=1.0, ghost=False, tint=None):
    s, z = cam.project(np.asarray(P)[None])
    if z[0] <= 0.2 or alpha <= 0.003:
        return None
    c = s[0]
    r = R_BALL * cam.px_per_m(z[0]) * scale
    if glow:
        fr.circle(c, r * 1.3, glow, alpha * 0.5, blur=max(2, r * 0.6))
    if ghost:
        fr.circle(c, r, tint or "#f4f6ff", alpha * 0.22)
        fr.circle(c, r, tint or "#f4f6ff", alpha * 0.75, stroke=max(1.0, r * 0.09))
        return c, r
    sh = skia.GradientShader.MakeRadial(skia.Point(c[0] - r * 0.35, c[1] - r * 0.4), r * 1.7,
                                        [hexc("#ffffff"), hexc("#eef0f8"), hexc("#7d86aa")], [0.0, 0.5, 1.0])
    fr.circle(c, r, "#ffffff", alpha, shader=sh)
    fr.c.save()
    path = skia.Path(); path.addCircle(float(c[0]), float(c[1]), float(r))
    fr.c.clipPath(path, doAntiAlias=True)
    # two bold curved panels + seams (generic volleyball look)
    for k, col in ((0, "#f2c94c"), (1, "#f2c94c")):
        a = rot + k * math.pi * 0.95
        d = np.array([math.cos(a), math.sin(a)]); nrm = np.array([-d[1], d[0]])
        p0 = c + d * r * 1.3 - nrm * r * 0.05
        p1 = c - d * r * 1.3 - nrm * r * 0.05
        ctrl = c + nrm * r * 0.95
        pth = skia.Path(); pth.moveTo(float(p0[0]), float(p0[1])); pth.quadTo(float(ctrl[0]), float(ctrl[1]), float(p1[0]), float(p1[1]))
        fr.c.drawPath(pth, fr.paint(col, alpha * 0.9, stroke=r * 0.42, cap="butt"))
        fr.c.drawPath(pth, fr.paint("#2a3157", alpha * 0.55, stroke=max(1.0, r * 0.045)))
    fr.c.restore()
    hl = skia.GradientShader.MakeRadial(skia.Point(c[0] - r * 0.38, c[1] - r * 0.42), r * 0.55,
                                        [skia.Color(255, 255, 255, 170), skia.Color(255, 255, 255, 0)])
    fr.circle(c, r, "#ffffff", alpha, shader=hl)
    fr.circle(c, r, PAL["outline"], alpha * 0.9, stroke=max(1.2, r * 0.07))
    return c, r


def ball_shadow(fr, cam, P, alpha=0.5):
    Q = np.array([P[0], P[1], 0.0])
    s, z = cam.project(Q[None])
    if z[0] <= 0.2:
        return
    r = R_BALL * cam.px_per_m(z[0]) * (1.0 + 0.15 * P[2])
    fr.c.save()
    fr.c.translate(float(s[0][0]), float(s[0][1]))
    fr.c.scale(1.0, 0.35)
    fr.circle((0, 0), r, "#000000", alpha * clamp(1.2 - P[2] / 5), blur=r * 0.5)
    fr.c.restore()


# ================================================================== the play: ball timeline
T_SET_START = -0.06        # setter's hands meet the ball
PASS_T0 = -1.55
PASS_P0 = np.array([-0.4, -6.6, 0.9])
P_IN = PLAN.r0 + np.array([0.06, 0.0, -0.10])


def _pass_vel():
    T = T_SET_START - PASS_T0
    return (P_IN - PASS_P0 - 0.5 * np.array([0, 0, -G]) * T * T) / T


V_PASS = _pass_vel()


class BallPath:
    """Full ball history for one attempt: pass -> set contact -> set flight -> (hit | miss)."""

    def __init__(self, r0=None, v0=None, spin=None, t0=0.0, outcome=fq.CLEAN, t_hit=None, n_palm=None,
                 out_speed=25.0, seed=0):
        self.r0 = PLAN.r0 if r0 is None else np.asarray(r0, float)
        self.v0 = PLAN.v0 if v0 is None else np.asarray(v0, float)
        self.spin = SPIN0 if spin is None else np.asarray(spin, float)
        self.t0 = float(t0)
        self.tracks = fq.BallTracks(self.r0[None], self.v0[None], self.spin[None], 2.2, M.ball, dt=2e-3,
                                    t0=np.array([self.t0]))
        self.outcome = outcome
        self.t_hit = t_hit
        self.n_palm = PLAN.n_palm if n_palm is None else np.asarray(n_palm, float)
        rng = np.random.default_rng(seed)
        if t_hit is not None and not np.isnan(t_hit):
            p_hit, _ = self.flight(t_hit)
            self.p_hit = p_hit
            if outcome in (fq.CLEAN, fq.PALM):
                d = self.n_palm + np.array([0, 0, -0.62]) + np.array([rng.normal(0, 0.05), 0, 0])
                d /= np.linalg.norm(d)
                self.v_out = d * out_speed * (1.0 if outcome == fq.CLEAN else 0.75)
            else:
                d = np.array([rng.normal(0, 0.8), rng.uniform(-0.6, 0.6), rng.uniform(0.2, 1.0)])
                d /= np.linalg.norm(d)
                self.v_out = d * 7.0
        else:
            self.p_hit = None

    def flight(self, t):
        p, v = self.tracks.at(np.array([[t]]))
        return p[0, 0], v[0, 0]

    def pos(self, t):
        if t < T_SET_START:
            tt = t - PASS_T0
            return PASS_P0 + V_PASS * tt + 0.5 * np.array([0, 0, -G]) * tt * tt
        if t < self.t0:
            # set contact: dip toward the low point, then accelerate to the release point
            u = seg(t, T_SET_START, self.t0)
            low = P_IN + np.array([0.0, 0.0, -0.05])
            if u < 0.5:
                return lerp(P_IN, low, ease_io(u * 2))
            return lerp(low, self.r0, ease_io((u - 0.5) * 2))
        if self.p_hit is not None and t >= self.t_hit:
            dt = t - self.t_hit
            p = self.p_hit + self.v_out * dt + 0.5 * np.array([0, 0, -G]) * dt * dt
            return _bounce(p)
        p, _ = self.flight(t)
        return _bounce(p)


def _bounce(p):
    if p[2] < R_BALL:
        p = p.copy()
        p[2] = R_BALL + (R_BALL - p[2]) * 0.45
    return p


# ================================================================== athletes
LIMB_R = dict(upper=0.048, fore=0.04, hand=0.042, thigh=0.078, shin=0.058, foot=0.045, neck=0.05)
HEAD_R = 0.118


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def nominal_attempt():
    return {k: float(v[0]) for k, v in PLAN.nominal.items()}


def attempt_from_samples(smp, prefix, i):
    keys = ["x_to", "y_to", "t_to", "vx", "vy", "vz", "dt_swing", "alpha_c", "beta_c", "gamma_c", "tilt",
            "pitch_c", "pitch_rate", "wrist_rate", "omega_s", "yaw_body", "swing_az"]
    return {k: float(smp[f"{prefix}_hs_{k}"][i]) for k in keys}


def _hs(att):
    return {k: np.array([v]) for k, v in att.items()}


def _ballistic_com(att, t):
    tf = t - att["t_to"]
    return np.array([att["x_to"] + att["vx"] * tf, att["y_to"] + att["vy"] * tf,
                     M.body.com_takeoff + att["vz"] * tf - 0.5 * G * tf * tf])


def _hermite(p0, v0, p1, v1, T, u):
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u
    h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
    return h00 * p0 + h10 * T * v0 + h01 * p1 + h11 * T * v1


APPROACH = dict(t_run=1.15, t_plant=0.30, v_run=3.75)


def spiker_com(att, t):
    """Centre of mass for approach, plant, flight and landing. Returns (com, phase, facing)."""
    t_to = att["t_to"]
    P_to = np.array([att["x_to"], att["y_to"]])
    v_to = np.array([att["vx"], att["vy"]])
    dir_in = _unit(np.array([0.22, 1.0]))
    t_plant = t_to - APPROACH["t_plant"]
    t_start = t_to - APPROACH["t_run"]
    P_plant = P_to - dir_in * 0.78
    P_start = P_plant - dir_in * APPROACH["v_run"] * (t_plant - t_start) * 0.92
    if t < t_plant:
        u = clamp((t - t_start) / (t_plant - t_start))
        xy = _hermite(P_start, dir_in * 3.0, P_plant, dir_in * APPROACH["v_run"], t_plant - t_start, u)
        step = 2 * math.pi * (t - t_start) / 0.62
        z = 0.97 + 0.03 * math.cos(2 * step)
        face = dir_in
        return np.array([xy[0], xy[1], z]), "run", face, step
    if t < t_to:
        u = (t - t_plant) / (t_to - t_plant)
        xy = _hermite(P_plant, dir_in * APPROACH["v_run"], P_to, v_to, t_to - t_plant, u)
        # dip then explode upward
        z_lo = 0.80
        if u < 0.55:
            z = _hermite(0.97, -0.6, z_lo, 0.0, 0.55 * (t_to - t_plant), u / 0.55)
        else:
            z = _hermite(z_lo, 0.0, M.body.com_takeoff, att["vz"], 0.45 * (t_to - t_plant), (u - 0.55) / 0.45)
        face = _unit(lerp(dir_in, np.array([math.sin(att["yaw_body"]), math.cos(att["yaw_body"])]), ease_io(u)))
        return np.array([xy[0], xy[1], z]), "plant", face, u
    com = _ballistic_com(att, t)
    face = np.array([math.sin(att["yaw_body"]), math.cos(att["yaw_body"])])
    t_land = t_to + (att["vz"] + math.sqrt(att["vz"] ** 2 + 2 * G * (M.body.com_takeoff - 0.98))) / G
    if t > t_land:
        land = _ballistic_com(att, t_land)
        u = clamp((t - t_land) / 0.25)
        z = 0.98 - 0.22 * math.sin(math.pi * min(1, u)) * (1 if u < 1 else 0)
        com = np.array([land[0] + att["vx"] * 0.1 * u, land[1] + att["vy"] * 0.12 * u, z])
        return com, "land", face, u
    return com, "air", face, t - t_to


def _leg(hip, f, thigh_ang, knee_flex, foot_ang=0.0, side=1.0, r=None):
    """Leg in the sagittal plane defined by facing f. Angles from vertical-down, + forward."""
    down = np.array([0, 0, -1.0])
    fx = np.array([f[0], f[1], 0.0])
    L_th, L_sh, L_ft = 0.44, 0.43, 0.15
    d_th = math.cos(thigh_ang) * down + math.sin(thigh_ang) * fx
    knee = hip + L_th * d_th
    a2 = thigh_ang - knee_flex
    d_sh = math.cos(a2) * down + math.sin(a2) * fx
    ankle = knee + L_sh * d_sh
    a3 = a2 + math.pi / 2 - 0.35 + foot_ang
    d_ft = math.cos(a3) * down + math.sin(a3) * fx
    toe = ankle + L_ft * d_ft
    return knee, ankle, toe


def _arm(sh, u, zp, th_u, beta, gam, body=M.body):
    e = lambda th: math.sin(th) * u + math.cos(th) * zp
    elbow = sh + body.upper_arm * e(th_u)
    th_f = th_u - beta
    wrist = elbow + body.forearm * e(th_f)
    th_h = th_f + gam
    palm = wrist + body.palm_from_wrist * e(th_h)
    tip = wrist + body.hand * e(th_h)
    return elbow, wrist, palm, tip


def _kf(keys, x):
    """Piecewise smoothstep interpolation over keyframes [(x, value), ...]."""
    if x <= keys[0][0]:
        return keys[0][1]
    for (x0, v0), (x1, v1) in zip(keys[:-1], keys[1:]):
        if x <= x1:
            return lerp(v0, v1, ease_io((x - x0) / (x1 - x0)))
    return keys[-1][1]


def spiker_pose(att, t):
    """3D joints for the spiker at physical time t."""
    com, phase, face, ph = spiker_com(att, t)
    f = np.array([face[0], face[1], 0.0]); f = _unit(f)
    r = np.array([f[1], -f[0], 0.0])
    z = np.array([0, 0, 1.0])
    J = {}
    t_c = att["t_to"] + att["vz"] / G + att["dt_swing"]
    tau = t - t_c
    if phase in ("air", "land"):
        pitch = att["pitch_c"] + 0.6 * math.tanh(att["pitch_rate"] * tau / 0.6)
        if phase == "land":
            pitch = lerp(pitch, 0.15, ease_io(ph))
    elif phase == "plant":
        pitch = _kf([(0, 0.20), (0.55, 0.32), (1.0, -0.05)], ph)
    else:
        pitch = 0.22
    up = math.cos(pitch) * z + math.sin(pitch) * f
    sh_c = com + 0.47 * up
    J["sh_r"] = sh_c + 0.17 * r
    J["sh_l"] = sh_c - 0.17 * r
    J["neck"] = sh_c + 0.07 * up
    J["head"] = sh_c + 0.21 * up + 0.03 * f
    hip_c = com - 0.06 * up
    J["hip_r"] = hip_c + 0.10 * r
    J["hip_l"] = hip_c - 0.10 * r
    # ---------------- legs
    if phase == "run":
        s = ph
        for side, sgn in (("r", 1), ("l", -1)):
            a = math.sin(s + (0 if sgn > 0 else math.pi))
            th = 0.55 * a
            kn = 0.25 + 0.95 * max(0.0, math.sin(s + (0 if sgn > 0 else math.pi) - 0.9)) ** 1.2
            J["kn_" + side], J["an_" + side], J["toe_" + side] = _leg(J["hip_" + side], f, th, kn)
    elif phase == "plant":
        u = ph
        for side, off in (("r", 0.0), ("l", 0.08)):
            th = _kf([(0, 0.35), (0.55, 0.55 + off), (1.0, 0.05)], u)
            kn = _kf([(0, 0.6), (0.55, 1.25), (1.0, 0.08)], u)
            J["kn_" + side], J["an_" + side], J["toe_" + side] = _leg(J["hip_" + side], f, th, kn, foot_ang=_kf([(0, 0), (0.6, 0.2), (1, -0.5)], u))
    else:
        tf = t - att["t_to"]
        if phase == "air":
            th = _kf([(0.0, 0.05), (0.18, -0.25), (att["vz"] / G + att["dt_swing"], 0.10), (0.62, 0.45), (0.8, 0.30)], tf)
            kn = _kf([(0.0, 0.10), (0.18, 1.25), (att["vz"] / G, 0.95), (0.62, 0.55), (0.8, 0.35)], tf)
        else:
            th = _kf([(0, 0.35), (0.4, 0.6), (1.0, 0.25)], ph)
            kn = _kf([(0, 0.4), (0.4, 1.2), (1.0, 0.3)], ph)
        for side, d in (("r", 0.0), ("l", 0.12)):
            J["kn_" + side], J["an_" + side], J["toe_" + side] = _leg(J["hip_" + side], f, th - d, kn + d * 0.5, foot_ang=-0.5)
    # ---------------- arms
    if phase == "run":
        s = ph
        for side, off in (("r", math.pi), ("l", 0.0)):
            th = math.pi + 0.75 * math.sin(s + off)
            e, w, p, tip = _arm(J["sh_" + side], f, z, th, 1.35, 0.1)
            J["el_" + side], J["wr_" + side], J["hand_" + side], J["tip_" + side] = e, w, p, tip
    elif phase == "plant":
        u = ph
        th = _kf([(0, 3.4), (0.5, 4.3), (0.82, 2.0), (1.0, 0.15)], u)
        be = _kf([(0, 0.5), (0.5, 0.25), (1.0, 0.2)], u)
        for side, d in (("r", 0.0), ("l", 0.06)):
            e, w, p, tip = _arm(J["sh_" + side], f, z, th + d, be, 0.0)
            J["el_" + side], J["wr_" + side], J["hand_" + side], J["tip_" + side] = e, w, p, tip
    else:
        # hitting arm: animation pose blended into the physics model before contact
        kin = fq.hitter_kinematics(_hs(att), np.array([t]), M.body, want_all=True)
        sh = kin["shoulder"][0, 0]
        u = kin["u"][0, 0]; zp = kin["zp"][0, 0]
        th_u_p, th_f_p, th_h_p = kin["th_u"][0, 0], kin["th_f"][0, 0], kin["th_h"][0, 0]
        beta_p, gam_p = th_u_p - th_f_p, th_h_p - th_f_p
        tf = t - att["t_to"]
        th_a = _kf([(0.0, 0.0), (0.16, -0.55), (0.26, -0.75)], tf)
        be_a = _kf([(0.0, 0.2), (0.16, 1.7), (0.26, 1.9)], tf)
        ga_a = _kf([(0.0, 0.0), (0.2, -0.35)], tf)
        wgt = ease_io(seg(tau, -0.17, -0.10))
        th_u = lerp(th_a, th_u_p, wgt); be = lerp(be_a, beta_p, wgt); ga = lerp(ga_a, gam_p, wgt)
        if phase == "land":
            k = ease_io(ph)
            th_u = lerp(th_u, 2.6, k); be = lerp(be, 0.3, k)
        e, w, p, tip = _arm(sh, u, zp, th_u, be, ga)
        J["sh_r"] = sh
        J["el_r"], J["wr_r"], J["hand_r"], J["tip_r"] = e, w, p, tip
        # off arm: reaches up toward the ball, then pulls down through contact
        thl = _kf([(0.0, 0.0), (0.2, 0.35), (att["vz"] / G + att["dt_swing"] - 0.06, 0.45),
                   (att["vz"] / G + att["dt_swing"] + 0.08, 2.4), (0.9, 2.6)], tf)
        bel = _kf([(0.0, 0.15), (0.3, 0.2), (att["vz"] / G + att["dt_swing"] + 0.08, 1.2), (0.9, 0.5)], tf)
        e, w, p, tip = _arm(J["sh_l"], f, z, thl, -bel * 0 + bel, 0.0)
        J["el_l"], J["wr_l"], J["hand_l"], J["tip_l"] = e, w, p, tip
    return J


SETTER_POS = np.array([PLAN.r0[0] + 0.12, PLAN.r0[1] - 0.02])
SETTER_FACE = _unit(PLAN.v0[:2])


_NOM_BALL = None


def _nom_ball():
    global _NOM_BALL
    if _NOM_BALL is None:
        _NOM_BALL = BallPath()
    return _NOM_BALL


def setter_pose(t, jump=True):
    f = np.array([SETTER_FACE[0], SETTER_FACE[1], 0.0])
    r = np.array([f[1], -f[0], 0.0]); z = np.array([0, 0, 1.0])
    # jump set: take-off at -0.30, peak near release
    t_to, vz = -0.30, 2.05
    tf = t - t_to
    base = 1.02
    if jump and 0 <= tf <= 2 * vz / G:
        zc = base + vz * tf - 0.5 * G * tf * tf
        air = True
    else:
        zc = base - (0.12 * math.exp(-((t + 0.42) / 0.09) ** 2) if t < t_to else 0.0)
        air = False
    com = np.array([SETTER_POS[0], SETTER_POS[1], zc]) - 0.10 * f
    J = {}
    up = z
    sh_c = com + 0.48 * up
    J["sh_r"], J["sh_l"] = sh_c + 0.18 * r, sh_c - 0.18 * r
    J["neck"] = sh_c + 0.07 * up
    J["head"] = sh_c + 0.21 * up + 0.02 * f
    hip_c = com - 0.06 * up
    J["hip_r"], J["hip_l"] = hip_c + 0.10 * r, hip_c - 0.10 * r
    th = 0.05 if air else 0.12
    kn = (0.35 if air else 0.25)
    for side, d in (("r", 0.0), ("l", 0.1)):
        J["kn_" + side], J["an_" + side], J["toe_" + side] = _leg(J["hip_" + side], f, th + d * 0.3, kn, foot_ang=-0.4 if air else 0.0)
    # hands: track the ball during contact, extend toward the target after release
    target_dir = _unit(PLAN.v0)
    if t < T_SET_START - 0.25:
        hand_c = J["head"] + np.array([0, 0, 0.16]) + 0.10 * f
    elif t < 0:
        bp = _nom_ball().pos(max(t, T_SET_START))
        hand_c = bp - 0.07 * f - np.array([0, 0, 0.06])
        if t < T_SET_START:
            hand_c = lerp(J["head"] + np.array([0, 0, 0.16]) + 0.10 * f, _nom_ball().pos(T_SET_START) - 0.07 * f,
                          ease_io(seg(t, T_SET_START - 0.25, T_SET_START)))
    else:
        rel = PLAN.r0 - 0.07 * f - np.array([0, 0, 0.06])
        hand_c = rel + target_dir * 0.22 * ease_io(seg(t, 0, 0.12))
    for side, sgn in (("r", 1), ("l", -1)):
        hand = hand_c + sgn * 0.075 * r
        sh = J["sh_" + side]
        d = hand - sh
        L1, L2 = M.body.upper_arm, M.body.forearm + 0.06
        dist = min(np.linalg.norm(d), L1 + L2 - 1e-3)
        # simple 2-link IK, elbow pointing outward/down
        a = math.acos(clamp((L1 ** 2 + dist ** 2 - L2 ** 2) / (2 * L1 * dist), -1, 1))
        dn = _unit(d)
        bend = _unit(np.cross(dn, f) * sgn + np.array([0, 0, -0.4]))
        elbow = sh + L1 * (math.cos(a) * dn + math.sin(a) * bend)
        wrist = elbow + _unit(hand - elbow) * (L2 - 0.06)
        J["el_" + side], J["wr_" + side], J["hand_" + side], J["tip_" + side] = elbow, wrist, hand, hand + 0.06 * up
    return J


def draw_athlete(fr, cam, J, jersey, glow=None, alpha=1.0, ghost=False, outline=None, skin="#e7eaf8",
                 number=None, highlight_arm=None):
    """Depth-sorted cel-shaded mannequin."""
    if alpha <= 0.003:
        return
    keys = list(J.keys())
    P = np.array([J[k] for k in keys])
    S, Z = cam.project(P)
    if (Z < 0.2).any():
        return
    sp = {k: S[i] for i, k in enumerate(keys)}
    dp = {k: Z[i] for i, k in enumerate(keys)}
    ol = outline or PAL["outline"]
    prims = []

    def cap(a, b, rad, col, kind="limb"):
        if a in sp and b in sp:
            d = 0.5 * (dp[a] + dp[b])
            prims.append((d, "cap", (sp[a], sp[b], rad * cam.px_per_m(d), col)))

    shorts = PAL["shorts"]
    for side in ("l", "r"):
        cap("hip_" + side, "kn_" + side, LIMB_R["thigh"], skin)
        cap("kn_" + side, "an_" + side, LIMB_R["shin"], skin)
        cap("an_" + side, "toe_" + side, LIMB_R["foot"], "#f4f6ff")
        cap("sh_" + side, "el_" + side, LIMB_R["upper"], skin)
        cap("el_" + side, "wr_" + side, LIMB_R["fore"], skin)
        cap("wr_" + side, "tip_" + side, LIMB_R["hand"], skin)
    cap("neck", "head", LIMB_R["neck"], skin)
    # torso as volumes: chest capsule (pelvis->chest), shoulder bar, hip bar
    J2 = dict(J)
    J2["_pelvis"] = 0.5 * (J["hip_l"] + J["hip_r"])
    J2["_chest"] = 0.5 * (J["sh_l"] + J["sh_r"]) * 0.85 + J2["_pelvis"] * 0.15
    S2, Z2 = cam.project(np.array([J2["_pelvis"], J2["_chest"]]))
    sp["_pelvis"], sp["_chest"] = S2[0], S2[1]
    dp["_pelvis"], dp["_chest"] = Z2[0], Z2[1]
    td = 0.5 * (Z2[0] + Z2[1])
    prims.append((td, "cap", (sp["_pelvis"], sp["_chest"], 0.13 * cam.px_per_m(td), jersey)))
    sd = 0.5 * (dp["sh_l"] + dp["sh_r"])
    prims.append((sd - 0.02, "cap", (sp["sh_l"], sp["sh_r"], 0.075 * cam.px_per_m(sd), jersey)))
    hdp = 0.5 * (dp["hip_l"] + dp["hip_r"])
    prims.append((hdp - 0.02, "cap", (sp["hip_l"], sp["hip_r"], 0.095 * cam.px_per_m(hdp), PAL["shorts"])))
    prims.append((hdp - 0.03, "cap", (sp["_pelvis"], lerp(sp["_pelvis"], sp["_chest"], 0.25), 0.125 * cam.px_per_m(hdp), PAL["shorts"])))
    hd = dp["head"]
    prims.append((hd - 0.01, "head", None))
    prims.sort(key=lambda x: -x[0])

    def draw_all():
        for d, kind, data in prims:
            if kind == "cap":
                a, b, w, col = data
                if ghost:
                    fr.line(a, b, max(2.0, w * 0.5), "#ffb3d4", 0.55)
                    continue
                fr.line(a, b, w * 2 + 5, ol, 1.0)
                fr.line(a, b, w * 2, col, 1.0)
            elif kind == "torso":
                sl, sr, hl, hr = (sp[k] for k in ("sh_l", "sh_r", "hip_l", "hip_r"))
                pxm = cam.px_per_m(td)
                widen = 0.03 * pxm
                cen = (sl + sr + hl + hr) / 4
                pts = [sl + _unit(sl - cen) * widen, sr + _unit(sr - cen) * widen,
                       hr + _unit(hr - cen) * widen * 0.4, hl + _unit(hl - cen) * widen * 0.4]
                if ghost:
                    fr.polygon(pts, "#ffb3d4", 0.5, stroke=2)
                    continue
                fr.polygon(pts, ol, 1.0, stroke=10)
                fr.polygon(pts, jersey, 1.0)
                # shorts band
                hcen = (hl + hr) / 2
                fr.polygon([hl + _unit(hl - cen) * widen * 0.4, hr + _unit(hr - cen) * widen * 0.4,
                            hr + (hr - sr) * 0.22, hl + (hl - sl) * 0.22], shorts, 1.0)
                # side stripe
                fr.line(lerp(sl, hl, 0.08), lerp(sl, hl, 0.92), max(2, 0.025 * pxm), mix(jersey, "#ffffff", 0.55), 0.9)
                if number:
                    fr.text(number, cen[0], cen[1] + 0.04 * pxm, 0.17 * pxm, "black", "#ffffff", 0.9, "center")
            elif kind == "head":
                c = sp["head"]
                rr = HEAD_R * cam.px_per_m(hd)
                if ghost:
                    fr.circle(c, rr, "#ffb3d4", 0.6, stroke=2)
                    continue
                fr.circle(c, rr + 2.5, ol, 1.0)
                fr.circle(c, rr, skin, 1.0)
                # hair cap: top portion of the head, toward 'up' on screen
                up_s = sp["head"] - sp["neck"]
                ang = math.degrees(math.atan2(up_s[1], up_s[0]))
                oval = skia.Rect.MakeXYWH(c[0] - rr * 1.04, c[1] - rr * 1.04, rr * 2.08, rr * 2.08)
                pth = skia.Path()
                pth.arcTo(oval, ang - 105, 210, True)
                pth.close()
                fr.c.drawPath(pth, fr.paint(PAL["hair"], 1.0))

    xs = S[:, 0]; ys = S[:, 1]
    pad = 60 + HEAD_R * cam.px_per_m(float(np.min(Z))) * 2
    bounds = skia.Rect.MakeLTRB(float(xs.min() - pad), float(ys.min() - pad), float(xs.max() + pad), float(ys.max() + pad))
    if glow and not ghost:
        filt = skia.ImageFilters.DropShadow(0, 0, 8, 8, hexc(glow, 0.85))
        with fr.layer(alpha, bounds=bounds, filt=filt):
            draw_all()
    else:
        with fr.layer(alpha, bounds=bounds):
            draw_all()
    if highlight_arm:
        for a, b in (("sh_r", "el_r"), ("el_r", "wr_r"), ("wr_r", "tip_r")):
            fr.line(sp[a], sp[b], 4, highlight_arm, alpha, glow=6)
        for k in ("sh_r", "el_r", "wr_r"):
            fr.circle(sp[k], 7, highlight_arm, alpha)
            fr.circle(sp[k], 7, PAL["outline"], alpha, stroke=2)
