"""
freak_quick_model.py
====================

Physics + stochastic model of a *blind minus-tempo quick*: the spiker leaves the
floor before the setter touches the ball, swings with his eyes closed, and the
setter has to put the ball exactly where (and when) the blind hand will be.

Everything below is plain NumPy and vectorised over N simultaneous attempts, so
the same functions drive the deterministic "perfect world" solution, the Monte
Carlo experiments and the animation.

Coordinate system (metres, seconds)
-----------------------------------
    origin  : floor, directly below the middle of the net
    x       : along the net (setter stands at +x, the attack goes to -x)
    y       : perpendicular to the net, our court is y < 0, net plane y = 0
    z       : up
    t = 0   : the instant the ball leaves the setter's hands

Main assumptions (the "physics contract")
-----------------------------------------
 1. Perfect pass: the ball reaches the setter at the same place and time every rep.
 2. Setter stands still at a fixed spot; release point is fixed (plus small noise).
 3. Regulation ball (FIVB: 65-67 cm circumference, 260-280 g), rigid, no deformation
    before the hit; still indoor air at sea level.
 4. No blockers, no other players; the net only defines geometry.
 5. The spiker always jumps and always swings. After take-off he is a projectile
    (no air resistance on the body) and he makes no corrections: the blind swing
    is an open-loop motor program referenced to his own jump apex.
 6. A right-handed spiker; the arm is a planar 3-link chain (upper arm, forearm,
    hand) in a swing plane that may be tilted and turned.
 7. The hand is a flat disc (radius r_hand). The ball is a sphere. "Contact" means
    the sphere touches the disc; contact quality is graded by where it touches.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace, asdict
import numpy as np

g = 9.81
GVEC = np.array([0.0, 0.0, -g])
RAD = np.pi / 180.0

# Outcome codes
CLEAN, PALM, EDGE, MISS = 0, 1, 2, 3
OUTCOME_NAMES = {CLEAN: "clean (sweet spot)", PALM: "on the palm", EDGE: "fingertips / edge", MISS: "whiff"}
# Miss / offset directions (dartboard quadrants)
PASSED, SHORT, OVER, UNDER = 0, 1, 2, 3
DIRECTION_NAMES = {PASSED: "passed by (hand late)", SHORT: "fell short (hand early)",
                   OVER: "over the fingers", UNDER: "under the palm"}


# --------------------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class BallParams:
    mass: float = 0.270            # kg   FIVB 260-280 g
    radius: float = 0.105          # m    circumference 0.66 m
    rho_air: float = 1.20          # kg/m^3 (sea level, ~20 C)
    cd_sub: float = 0.45           # drag coefficient below the drag crisis (assumption, typical subcritical sphere)
    cd_super: float = 0.17         # after the drag crisis (Asai et al. 2010)
    v_crit: float = 14.0           # m/s drag-crisis speed (Asai et al. 2010); sets fly at 7-10 m/s
    crisis_width: float = 1.5      # m/s width of the transition
    cl_per_spin: float = 0.9       # Magnus lift: C_L ~ cl_per_spin * S, S = R*omega/v
    cl_max: float = 0.35

    @property
    def area(self) -> float:
        return np.pi * self.radius ** 2

    @property
    def k(self) -> float:
        """0.5*rho*A/m, so that a_drag = -k*Cd*|v|*v"""
        return 0.5 * self.rho_air * self.area / self.mass


@dataclass(frozen=True)
class Anthro:
    """Spiker body dimensions (Winter-style segment ratios of standing height)."""
    height: float = 1.80
    upper_arm: float = 0.186 * 1.80
    forearm: float = 0.146 * 1.80
    hand: float = 0.108 * 1.80
    palm_from_wrist: float = 0.40 * 0.108 * 1.80    # palm centre along the hand
    shoulder_right: float = 0.17       # hitting shoulder: lateral offset from body centre of mass
    shoulder_up: float = 0.47          # shoulder height above centre of mass (trunk upright)
    com_takeoff: float = 1.12          # centre-of-mass height at the instant of take-off
    r_hand: float = 0.085              # effective radius of the hitting surface (disc)
    rho_clean: float = 0.050           # sweet-spot radius on that disc

    @property
    def reach(self) -> float:
        return self.upper_arm + self.forearm + self.palm_from_wrist


@dataclass(frozen=True)
class Scene:
    net_height: float = 2.43
    release_point: tuple = (1.00, -0.70, 2.35)    # setter's hands (jump set)
    contact_xy: tuple = (-2.00, -0.45)            # where the ball centre should meet the hand
    release_spin: tuple = (0.0, 0.0, 0.0)         # nominal spin (rad/s), a "dead" set


@dataclass(frozen=True)
class HitterMeans:
    vz: float = 3.80               # m/s vertical take-off velocity  -> rise 0.74 m
    v_forward: float = 1.30        # m/s horizontal take-off velocity toward the net
    v_lateral: float = 0.0
    alpha_c: float = 18 * RAD      # upper-arm angle in swing plane at contact (0 = vertical)
    beta_c: float = 8 * RAD        # elbow flexion at contact (0 = straight)
    gamma_c: float = 6 * RAD       # wrist flexion at contact
    tilt: float = 8 * RAD          # swing plane leans toward the hitting side
    pitch_c: float = 10 * RAD      # trunk forward lean at contact
    omega_s: float = 12.5          # rad/s shoulder angular speed at contact (~720 deg/s)
    pitch_rate: float = 3.5        # rad/s trunk flexion speed at contact
    wrist_rate: float = 15.0       # rad/s wrist snap at contact


@dataclass(frozen=True)
class HitterSD:
    """Trial-to-trial variability of the *blind* spiker (one SD)."""
    x_to: float = 0.10             # m   take-off spot along the net   (footwork)
    y_to: float = 0.10             # m   take-off spot toward the net
    t_to: float = 0.020            # s   take-off time (approach rhythm)
    vz: float = 0.11               # m/s -> jump-height CV ~6 % (Lobietti et al.)
    v_forward: float = 0.15        # m/s
    v_lateral: float = 0.12        # m/s
    dt_swing: float = 0.012        # s   blind swing timing vs. own apex (pro-musician tapping SD ~11 ms)
    tilt: float = 3 * RAD
    beta_c: float = 4 * RAD
    gamma_c: float = 5 * RAD
    pitch_c: float = 3 * RAD
    yaw_body: float = 3 * RAD
    swing_az: float = 4 * RAD
    omega_s: float = 1.0
    v_approach: float = 0.12       # m/s approach speed (only used for the Bayesian v_z prediction)
    corr_vapp_vz: float = 0.5      # correlation between approach speed and jump velocity

    def scaled(self, k: float) -> "HitterSD":
        d = {f: getattr(self, f) * k for f in self.__dataclass_fields__ if f not in ("corr_vapp_vz",)}
        d["corr_vapp_vz"] = self.corr_vapp_vz
        return HitterSD(**d)


@dataclass(frozen=True)
class SetterSD:
    """Release noise of the setter (one SD). Default = the most consistent NBA free-throw
    shooters (angle ~1.1 deg, speed ~1.6 %), release timing like expert dart throwers."""
    t_release: float = 0.005       # s
    pos: float = 0.015             # m per axis
    speed_cv: float = 0.016        # relative
    elevation: float = 1.1 * RAD
    azimuth: float = 1.1 * RAD
    spin: float = 2 * np.pi * 1.0  # rad/s per axis (about one revolution per second)

    def scaled(self, k: float) -> "SetterSD":
        return SetterSD(**{f: getattr(self, f) * k for f in self.__dataclass_fields__})


@dataclass(frozen=True)
class Model:
    ball: BallParams = field(default_factory=BallParams)
    body: Anthro = field(default_factory=Anthro)
    scene: Scene = field(default_factory=Scene)
    hit: HitterMeans = field(default_factory=HitterMeans)


# --------------------------------------------------------------------------------------
# Ball flight: m dv/dt = m g - 1/2 rho A Cd |v| v + 1/2 rho A C_L |v|^2 (w_hat x v_hat)
# --------------------------------------------------------------------------------------
def drag_coefficient(speed, bp: BallParams):
    s = 1.0 / (1.0 + np.exp((speed - bp.v_crit) / (bp.crisis_width / 4.0)))
    return bp.cd_super + (bp.cd_sub - bp.cd_super) * s


def ball_acceleration(v, spin, bp: BallParams, drag=True):
    """v: (...,3) velocity, spin: (...,3) angular velocity (rad/s) or None."""
    if not drag:
        a = np.zeros_like(v); a[..., 2] = -g
        return a
    speed = np.sqrt(np.sum(v * v, axis=-1, keepdims=True))
    speed = np.maximum(speed, 1e-9)
    a = (-bp.k * drag_coefficient(speed, bp) * speed) * v
    if spin is not None:
        w = np.sqrt(np.sum(spin * spin, axis=-1, keepdims=True))
        S = bp.radius * w / speed
        cl = np.minimum(bp.cl_per_spin * S, bp.cl_max)
        w_hat = spin / np.maximum(w, 1e-12)
        a = a + (bp.k * cl * speed) * np.cross(w_hat, v)
    a[..., 2] -= g
    return a


def integrate_ball(r0, v0, spin, t_end, bp: BallParams, dt=2e-3, drag=True, t0=None, tau_store=0.0):
    """RK4 on each ball's own clock tau = t - t0 (t0 = release time, default 0).
    r0, v0, spin: (N,3). Stores samples for tau >= tau_store only (memory).
    Returns taus (K,), pos (N,K,3), vel (N,K,3), t0 (N,)."""
    r0 = np.atleast_2d(np.asarray(r0, float))
    v0 = np.atleast_2d(np.asarray(v0, float))
    N = max(r0.shape[0], v0.shape[0])
    r0 = np.broadcast_to(r0, (N, 3)); v0 = np.broadcast_to(v0, (N, 3))
    spin = None if spin is None else np.broadcast_to(np.atleast_2d(spin), (N, 3)).astype(float)
    if spin is not None and not np.any(spin):
        spin = None
    t0 = np.zeros(N) if t0 is None else np.broadcast_to(np.asarray(t0, float), (N,))
    tau_end = t_end - t0.min()
    K_all = int(np.ceil(tau_end / dt)) + 2
    i0 = max(0, int(np.floor(tau_store / dt)))
    taus = np.arange(i0, K_all) * dt
    pos = np.empty((N, K_all - i0, 3)); vel = np.empty((N, K_all - i0, 3))
    r = r0.copy(); v = v0.copy()
    if i0 == 0:
        pos[:, 0] = r; vel[:, 0] = v
    f = lambda vv: ball_acceleration(vv, spin, bp, drag)
    for i in range(1, K_all):
        k1v = f(v)
        k2v = f(v + 0.5 * dt * k1v)
        k3v = f(v + 0.5 * dt * k2v)
        k4v = f(v + dt * k3v)
        r = r + dt * (v + dt / 6 * (k1v + k2v + k3v))
        v = v + dt / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
        if i >= i0:
            pos[:, i - i0] = r; vel[:, i - i0] = v
    return taus, pos, vel, t0


class BallTracks:
    """Integrated trajectories; position/velocity at arbitrary absolute times (Hermite/linear interp)."""
    def __init__(self, r0, v0, spin, t_end, bp, dt=2e-3, drag=True, t0=None, t_store=None):
        tau_store = 0.0 if t_store is None else max(0.0, t_store - 0.05)
        self.taus, self.pos, self.vel, self.t0 = integrate_ball(r0, v0, spin, t_end, bp, dt, drag, t0, tau_store)
        self.dt = dt
        self.N = self.pos.shape[0]

    def at(self, t, rows=None):
        """t: (n,K) or (K,) absolute times -> pos (n,K,3), vel (n,K,3). rows: optional index array/slice."""
        idx = np.arange(self.N) if rows is None else np.arange(self.N)[rows]
        n_ = idx.size
        t = np.asarray(t, float)
        if t.ndim == 1:
            t = np.broadcast_to(t, (n_, t.size))
        tau = t - self.t0[idx][:, None]
        f = np.clip((tau - self.taus[0]) / self.dt, 0, len(self.taus) - 1.000001)
        i = np.floor(f).astype(int)
        w = (f - i)[..., None]
        r = idx[:, None]
        p0, p1 = self.pos[r, i], self.pos[r, i + 1]
        v0, v1 = self.vel[r, i], self.vel[r, i + 1]
        # cubic Hermite for position (exact for constant acceleration), linear for velocity
        h = self.dt
        w2, w3 = w * w, w * w * w
        p = (2*w3 - 3*w2 + 1) * p0 + (w3 - 2*w2 + w) * h * v0 + (-2*w3 + 3*w2) * p1 + (w3 - w2) * h * v1
        v = v0 * (1 - w) + v1 * w
        return p, v


def vacuum_launch(r0, target, T):
    """Velocity that reaches `target` after time T with gravity only."""
    return (np.asarray(target) - np.asarray(r0) - 0.5 * GVEC * np.asarray(T)[..., None] ** 2) / np.asarray(T)[..., None]


def ball_endpoint(r0, v0, spin, T, bp, K=160, drag=True):
    """State of each ball exactly at its own flight time T (per-sample step T/K, RK4).
    Returns pos (N,3), vel (N,3)."""
    r = np.array(np.broadcast_to(np.atleast_2d(r0), np.broadcast_shapes(np.shape(np.atleast_2d(r0)), np.shape(np.atleast_2d(v0)))), float)
    v = np.array(np.broadcast_to(np.atleast_2d(v0), r.shape), float)
    N = r.shape[0]
    spin = None if spin is None else np.broadcast_to(np.atleast_2d(spin), (N, 3)).astype(float)
    if spin is not None and not np.any(spin):
        spin = None
    dt = (np.broadcast_to(np.asarray(T, float), (N,)) / K)[:, None]
    f = lambda vv: ball_acceleration(vv, spin, bp, drag)
    for _ in range(K):
        k1v = f(v)
        k2v = f(v + 0.5 * dt * k1v)
        k3v = f(v + 0.5 * dt * k2v)
        k4v = f(v + dt * k3v)
        r = r + dt * (v + dt / 6 * (k1v + k2v + k3v))
        v = v + dt / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
    return r, v


def launch_jacobian(r0, v0, T, spin, bp, h=1e-4, drag=True):
    """d(endpoint position)/d(v0) (3x3) and d(endpoint)/dT (3,), for one plan."""
    r0 = np.asarray(r0, float)[None]; v0 = np.asarray(v0, float)
    vs = np.vstack([v0, v0 + [h, 0, 0], v0 + [0, h, 0], v0 + [0, 0, h]])
    p, vel = ball_endpoint(np.repeat(r0, 4, 0), vs, spin, np.full(4, T), bp, drag=drag)
    J = ((p[1:] - p[0]) / h).T
    return J, vel[0]


def solve_launch(r0, target, T, spin, bp, iters=4, drag=True, return_history=False, J_fixed=None):
    """Shooting method: find v0 so that the ball launched from r0 at t=0 is at `target` at time T.
    Newton with a finite-difference Jacobian (or, if J_fixed is given, the chord method with that
    fixed Jacobian - one integration per iteration). Vectorised over N problems."""
    r0 = np.atleast_2d(np.asarray(r0, float)); target = np.atleast_2d(np.asarray(target, float))
    T = np.atleast_1d(np.asarray(T, float))
    N = max(r0.shape[0], target.shape[0], T.shape[0])
    r0 = np.broadcast_to(r0, (N, 3)); target = np.broadcast_to(target, (N, 3)); T = np.broadcast_to(T, (N,))
    spin = None if spin is None else np.broadcast_to(np.atleast_2d(spin), (N, 3))
    v = vacuum_launch(r0, target, T)
    hist = [v.copy()]
    h = 1e-4
    for _ in range(iters):
        p, _ = ball_endpoint(r0, v, spin, T, bp, drag=drag)
        F = p - target
        if J_fixed is not None:
            v = v - np.linalg.solve(J_fixed, F.T).T
        else:
            J = np.empty((N, 3, 3))
            for j in range(3):
                dv = np.zeros(3); dv[j] = h
                pj, _ = ball_endpoint(r0, v + dv, spin, T, bp, drag=drag)
                J[:, :, j] = (pj - p) / h
            v = v - np.linalg.solve(J, F[..., None])[..., 0]
        hist.append(v.copy())
    if return_history:
        return v, hist
    return v


# --------------------------------------------------------------------------------------
# Spiker: projectile body + planar 3-link arm
# --------------------------------------------------------------------------------------
def _sig(x):
    return 1.0 / (1.0 + np.exp(-x))


def arm_angles(tau, s):
    """Swing-plane angles as functions of tau = t - t_contact (s). s: dict of (N,1) arrays.
    Angles measured from the plane's 'up' axis, positive = forward (toward the swing direction).
    Shoulder angle ~ linear through contact (rate omega_s) and saturates far from it.
    Elbow extends in the last ~60 ms, wrist snaps through contact."""
    A = 1.9
    th_u = s["alpha_c"] + A * np.tanh(s["omega_s"] * tau / A)
    b_amp, tau_e, w_e = 1.6, 0.035, 0.018
    beta = s["beta_c"] + b_amp * (_sig(-(tau + tau_e) / w_e) - _sig(-tau_e / w_e))
    beta = np.maximum(beta, 0.0)
    Gw = 0.7
    gam = s["gamma_c"] + Gw * np.tanh(s["wrist_rate"] * tau / Gw)
    th_f = th_u - beta
    th_h = th_f + gam
    return th_u, th_f, th_h


def hitter_kinematics(hs: dict, t, body: Anthro, want_all=False):
    """hs: dict of (N,) arrays describing each attempt (see sample_hitters / nominal_hitter).
    t: (N,K) or (K,) absolute times. Returns dict of (N,K,3) arrays."""
    N = hs["x_to"].shape[0]
    t = np.asarray(t, float)
    if t.ndim == 1:
        t = np.broadcast_to(t, (N, t.size))
    col = lambda k: hs[k][:, None]
    tau_f = t - col("t_to")                     # time since take-off
    t_c = col("t_to") + col("vz") / g + col("dt_swing")
    tau = t - t_c                              # time relative to the swing's contact instant
    # centre of mass (ballistic; before take-off we just freeze it - not used for contact)
    tf = np.maximum(tau_f, 0.0)
    com = np.stack([col("x_to") + col("vx") * tf,
                    col("y_to") + col("vy") * tf,
                    body.com_takeoff + col("vz") * tf - 0.5 * g * tf ** 2
                    + (col("dz") if "dz" in hs else 0.0)], axis=-1)
    yaw = col("yaw_body")
    fwd = np.stack([np.sin(yaw), np.cos(yaw), 0 * yaw], -1)      # facing direction
    right = np.stack([np.cos(yaw), -np.sin(yaw), 0 * yaw], -1)
    zhat = np.array([0.0, 0.0, 1.0])
    # trunk pitch (forward lean) around the body's right axis, pivot at the COM
    pitch = col("pitch_c") + 0.6 * np.tanh(col("pitch_rate") * tau / 0.6)
    sh = (com + body.shoulder_right * right
          + body.shoulder_up * (np.cos(pitch)[..., None] * zhat + np.sin(pitch)[..., None] * fwd))
    # swing plane: horizontal direction u (body yaw + swing azimuth), 'up' axis tilted toward the right
    az = yaw + col("swing_az")
    u = np.stack([np.sin(az), np.cos(az), 0 * az], -1)
    ru = np.stack([np.cos(az), -np.sin(az), 0 * az], -1)
    tl = col("tilt")[..., None]
    zp = np.cos(tl) * zhat + np.sin(tl) * ru
    s = {k: col(k) for k in ("alpha_c", "beta_c", "gamma_c", "omega_s", "wrist_rate")}
    th_u, th_f, th_h = arm_angles(tau, s)
    e = lambda th: np.sin(th)[..., None] * u + np.cos(th)[..., None] * zp
    de = lambda th: np.cos(th)[..., None] * u - np.sin(th)[..., None] * zp
    elbow = sh + body.upper_arm * e(th_u)
    wrist = elbow + body.forearm * e(th_f)
    a_axis = e(th_h)                    # along the hand, toward the fingertips
    palm = wrist + body.palm_from_wrist * a_axis
    n_axis = de(th_h)                   # palm normal (palm faces the direction of the swing)
    out = dict(com=com, shoulder=sh, elbow=elbow, wrist=wrist, palm=palm, n=n_axis, a=a_axis, tau=tau)
    if want_all:
        out.update(fingertip=wrist + body.hand * a_axis, fwd=fwd, right=right, u=u, zp=zp,
                   th_u=th_u, th_f=th_f, th_h=th_h, pitch=pitch)
    return out


def hitter_template(model: Model):
    """Nominal attempt with the contact instant at t=0 and the take-off point at the origin.
    Returns the ball-centre contact offset relative to the take-off point and the palm speed."""
    hm = model.hit
    hs = dict(x_to=np.zeros(1), y_to=np.zeros(1), t_to=np.array([-hm.vz / g]),
              vx=np.array([hm.v_lateral]), vy=np.array([hm.v_forward]), vz=np.array([hm.vz]),
              dt_swing=np.zeros(1), alpha_c=np.array([hm.alpha_c]), beta_c=np.array([hm.beta_c]),
              gamma_c=np.array([hm.gamma_c]), tilt=np.array([hm.tilt]), pitch_c=np.array([hm.pitch_c]),
              pitch_rate=np.array([hm.pitch_rate]), wrist_rate=np.array([hm.wrist_rate]),
              omega_s=np.array([hm.omega_s]), yaw_body=np.zeros(1), swing_az=np.zeros(1))
    dt = 1e-5
    k = hitter_kinematics(hs, np.array([-dt, 0.0, dt]), model.body)
    palm = k["palm"][0, 1]; n = k["n"][0, 1]
    ball_c = palm + model.ball.radius * n
    v_palm = (k["palm"][0, 2] - k["palm"][0, 0]) / (2 * dt)
    return hs, ball_c, v_palm, n, k["a"][0, 1]


# --------------------------------------------------------------------------------------
# The deterministic plan ("perfect world")
# --------------------------------------------------------------------------------------
@dataclass
class Plan:
    T: float                     # flight time of the set (s)
    v0: np.ndarray               # release velocity (3,)
    r0: np.ndarray               # release point (3,)
    target: np.ndarray           # ball-centre contact point (3,)
    takeoff: np.ndarray          # hitter take-off point (x,y)
    t_to: float                  # hitter take-off time (s, negative = before the release)
    v_palm: np.ndarray           # palm velocity at contact
    n_palm: np.ndarray
    a_palm: np.ndarray
    v_ball_c: np.ndarray         # ball velocity at contact
    v0_vac: np.ndarray           # vacuum solution for the same T (for comparison)
    shooting_history: list
    nominal: dict                # nominal hitter parameter dict (N=1)

    @property
    def speed(self):
        return float(np.linalg.norm(self.v0))

    @property
    def elevation_deg(self):
        return float(np.degrees(np.arctan2(self.v0[2], np.hypot(self.v0[0], self.v0[1]))))

    @property
    def azimuth_deg(self):
        return float(np.degrees(np.arctan2(self.v0[0], self.v0[1])))


def make_plan(model: Model, T=None, contact_xy=None, apex_at_contact=True):
    """Solve the perfect-world rendezvous. If T is None and apex_at_contact, pick the flight time
    for which the ball is at the top of its arc when it reaches the hand (v_z = 0 there)."""
    bp, sc, hm = model.ball, model.scene, model.hit
    hs0, ball_off, v_palm, n, a = hitter_template(model)
    r0 = np.array(sc.release_point, float)
    cxy = np.array(sc.contact_xy if contact_xy is None else contact_xy, float)
    rise_time = hm.vz / g
    # ball-centre contact point: x,y chosen; z fixed by the hitter's reach at his apex
    com_apex = np.array([0.0, 0.0, model.body.com_takeoff + hm.vz ** 2 / (2 * g)])
    # offset from take-off point to ball-centre at contact (template has take-off at origin)
    target_rel = ball_off.copy()
    target = np.array([cxy[0], cxy[1], target_rel[2]])
    takeoff_xy = cxy - target_rel[:2]
    spin = np.array(sc.release_spin, float)

    def vz_at_T(TT):
        v = solve_launch(r0, target, TT, spin, bp, iters=3)
        _, vv = ball_endpoint(r0[None], v, spin, np.array([TT]), bp)
        return vv[0, 2], v[0]

    if T is None:
        if apex_at_contact:
            from scipy.optimize import brentq
            T = brentq(lambda TT: vz_at_T(TT)[0], 0.15, 0.9, xtol=1e-6)
        else:
            T = 0.40
    v0, hist = solve_launch(r0, target, T, spin, bp, return_history=True)
    v0 = v0[0]
    _, vb = ball_endpoint(r0[None], v0[None], spin, np.array([T]), bp)
    vb = vb[:, None, :]
    nominal = {k: v.copy() for k, v in hs0.items()}
    nominal["x_to"] = np.array([takeoff_xy[0]]); nominal["y_to"] = np.array([takeoff_xy[1]])
    nominal["t_to"] = np.array([T - rise_time])
    return Plan(T=T, v0=v0, r0=r0, target=target, takeoff=takeoff_xy, t_to=T - rise_time,
                v_palm=v_palm, n_palm=n, a_palm=a, v_ball_c=vb[0, 0],
                v0_vac=vacuum_launch(r0, target, np.array(T)), shooting_history=[h[0] for h in hist],
                nominal=nominal)


# --------------------------------------------------------------------------------------
# Random attempts
# --------------------------------------------------------------------------------------
def sample_hitters(plan: Plan, model: Model, sd: HitterSD, N, rng, z=None):
    """Draw N blind attempts around the plan. z: optional dict of standard normals
    (common random numbers) so different SD levels reuse the same randomness."""
    hm = model.hit
    keys = ["x_to", "y_to", "t_to", "vx", "vy", "vz_ind", "vapp", "dt_swing", "tilt", "beta_c",
            "gamma_c", "pitch_c", "yaw_body", "swing_az", "omega_s"]
    if z is None:
        z = {k: rng.standard_normal(N) for k in keys}
    r = sd.corr_vapp_vz
    z_vz = r * z["vapp"] + np.sqrt(1 - r * r) * z["vz_ind"]
    hs = dict(
        x_to=plan.takeoff[0] + sd.x_to * z["x_to"],
        y_to=plan.takeoff[1] + sd.y_to * z["y_to"],
        t_to=plan.t_to + sd.t_to * z["t_to"],
        vx=hm.v_lateral + sd.v_lateral * z["vx"],
        vy=hm.v_forward + sd.v_forward * z["vy"],
        vz=hm.vz + sd.vz * z_vz,
        v_app=3.75 + sd.v_approach * z["vapp"],
        dt_swing=sd.dt_swing * z["dt_swing"],
        tilt=hm.tilt + sd.tilt * z["tilt"],
        beta_c=np.maximum(0.0, hm.beta_c + sd.beta_c * z["beta_c"]),
        gamma_c=hm.gamma_c + sd.gamma_c * z["gamma_c"],
        pitch_c=hm.pitch_c + sd.pitch_c * z["pitch_c"],
        yaw_body=sd.yaw_body * z["yaw_body"],
        swing_az=sd.swing_az * z["swing_az"],
        omega_s=hm.omega_s + sd.omega_s * z["omega_s"],
        alpha_c=np.full(N, hm.alpha_c),
        pitch_rate=np.full(N, hm.pitch_rate),
        wrist_rate=np.full(N, hm.wrist_rate),
    )
    return hs, z


def setter_execution(v_cmd, plan: Plan, model: Model, sd: SetterSD, rng, z=None):
    """Apply release noise to commanded velocities v_cmd (N,3). Returns r0, v0, spin, t0."""
    N = v_cmd.shape[0]
    if z is None:
        z = {k: rng.standard_normal((N, 3) if k in ("pos", "spin") else N)
             for k in ("t", "pos", "speed", "el", "az", "spin")}
    sp = np.linalg.norm(v_cmd, axis=1)
    el = np.arctan2(v_cmd[:, 2], np.hypot(v_cmd[:, 0], v_cmd[:, 1]))
    az = np.arctan2(v_cmd[:, 0], v_cmd[:, 1])
    sp = sp * (1 + sd.speed_cv * z["speed"])
    el = el + sd.elevation * z["el"]
    az = az + sd.azimuth * z["az"]
    v0 = np.stack([sp * np.cos(el) * np.sin(az), sp * np.cos(el) * np.cos(az), sp * np.sin(el)], 1)
    r0 = plan.r0[None] + sd.pos * z["pos"]
    spin = np.array(model.scene.release_spin)[None] + sd.spin * z["spin"]
    t0 = sd.t_release * z["t"]
    return r0, v0, spin, t0, z


# --------------------------------------------------------------------------------------
# Contact geometry: does the swept palm disc touch the ball sphere?
# --------------------------------------------------------------------------------------
def _disc_sphere_gap(b, p, n, r_hand, R):
    d = b - p
    h = np.einsum("...i,...i->...", d, n)
    rho = np.linalg.norm(d - h[..., None] * n, axis=-1)
    dist = np.sqrt(h ** 2 + np.maximum(rho - r_hand, 0.0) ** 2)
    return dist - R, h, rho


def _geom_at(sub, tracks, sl, t, body, R):
    """Exact geometry at per-sample times t (n,)."""
    kin = hitter_kinematics(sub, t[:, None], body)
    bb, vb = tracks.at(t[:, None], rows=sl)
    b, vb = bb[:, 0], vb[:, 0]
    p, n, a = kin["palm"][:, 0], kin["n"][:, 0], kin["a"][:, 0]
    gap, h, rho = _disc_sphere_gap(b, p, n, body.r_hand, R)
    return dict(gap=gap, h=h, rho=rho, b=b, vb=vb, p=p, n=n, a=a)


def _bisect(fun, t_lo, t_hi, iters=14):
    """Root of fun (sign change from >0 at t_lo to <=0 at t_hi), vectorised."""
    for _ in range(iters):
        mid = 0.5 * (t_lo + t_hi)
        neg = fun(mid) <= 0
        t_hi = np.where(neg, mid, t_hi)
        t_lo = np.where(neg, t_lo, mid)
    return t_hi


def evaluate_contacts(hs, tracks: BallTracks, model: Model, t_lo, t_hi, chunk=2000):
    """For every attempt, find the first instant the ball sphere touches the palm disc.
    Returns a dict of (N,) arrays:
      outcome   CLEAN / PALM / EDGE / MISS
      t_hit     first-contact time (nan for misses)
      rho_hit   distance of the ball's touch point from the palm centre
      e_s, e_a  'dartboard' coordinates of the ball centre in the palm plane at the instant the palm
                plane is one ball-radius from the ball centre (when a face contact would begin):
                s = across the hand, signed so that + means the ball had already gone past;
                a = along the hand, + toward the fingertips (ball too high)
      direction PASSED / SHORT / OVER / UNDER (the dominant way the ball was off)
      v_inplane ball speed across the palm plane (m/s)
    """
    body, R = model.body, model.ball.radius
    N = hs["x_to"].shape[0]
    out = {k: np.full(N, np.nan) for k in ("t_hit", "e_s", "e_a", "rho_hit", "v_inplane", "t_R")}
    out["outcome"] = np.full(N, MISS, int)
    out["direction"] = np.full(N, -1, int)
    coarse = np.arange(t_lo, t_hi, 1e-3)
    fine_off = np.arange(-14e-3, 4e-3, 5e-5)
    for c0 in range(0, N, chunk):
        sl = slice(c0, min(N, c0 + chunk))
        sub = {k: v[sl] for k, v in hs.items()}
        n_ = sl.stop - sl.start
        rows = np.arange(n_)
        kin = hitter_kinematics(sub, coarse, body)
        b, _ = tracks.at(coarse, rows=sl)
        gap, h, rho = _disc_sphere_gap(b, kin["palm"], kin["n"], body.r_hand, R)
        i_min = np.argmin(gap, axis=1)
        tf = coarse[i_min][:, None] + fine_off[None, :]
        kin_f = hitter_kinematics(sub, tf, body)
        bf, _ = tracks.at(tf, rows=sl)
        gap_f, h_f, rho_f = _disc_sphere_gap(bf, kin_f["palm"], kin_f["n"], body.r_hand, R)
        # ---- first contact (gap crosses zero), refined by bisection
        hit_mask = gap_f <= 0
        any_hit = hit_mask.any(axis=1)
        j = np.argmax(hit_mask, axis=1)
        jm = np.maximum(j - 1, 0)
        t_hit = _bisect(lambda tt: _geom_at(sub, tracks, sl, tt, body, R)["gap"], tf[rows, jm], tf[rows, j])
        g_hit = _geom_at(sub, tracks, sl, t_hit, body, R)
        # ---- dartboard instant: palm plane one ball radius from the ball centre (h crosses R)
        reach = h_f <= R
        has_R = reach.any(axis=1)
        jR = np.where(has_R, np.argmax(reach, axis=1), np.argmin(np.abs(h_f - R), axis=1))
        jRm = np.maximum(jR - 1, 0)
        t_R = np.where(has_R, _bisect(lambda tt: _geom_at(sub, tracks, sl, tt, body, R)["h"] - R,
                                      tf[rows, jRm], tf[rows, jR]), tf[rows, jR])
        gR = _geom_at(sub, tracks, sl, t_R, body, R)
        d = gR["b"] - gR["p"]
        sR = np.cross(gR["a"], gR["n"])
        vball_s = np.einsum("ij,ij->i", gR["vb"], sR)
        sgn = np.where(vball_s >= 0, 1.0, -1.0)
        e_s = np.einsum("ij,ij->i", d, sR) * sgn
        e_a = np.einsum("ij,ij->i", d, gR["a"])
        vn = np.einsum("ij,ij->i", gR["vb"], gR["n"])
        v_in = np.linalg.norm(gR["vb"] - vn[:, None] * gR["n"], axis=1)
        rho_hit, h_hit = g_hit["rho"], g_hit["h"]
        outc = np.full(n_, MISS)
        face = any_hit & (rho_hit <= body.r_hand + 1e-9) & (h_hit > 0)
        outc[face & (rho_hit <= body.rho_clean)] = CLEAN
        outc[face & (rho_hit > body.rho_clean)] = PALM
        outc[any_hit & ~face] = EDGE
        direction = np.where(np.abs(e_s) >= np.abs(e_a),
                             np.where(e_s > 0, PASSED, SHORT),
                             np.where(e_a > 0, OVER, UNDER))
        out["outcome"][sl] = outc
        out["t_hit"][sl] = np.where(any_hit, t_hit, np.nan)
        out["e_s"][sl] = e_s
        out["e_a"][sl] = e_a
        out["rho_hit"][sl] = np.where(any_hit, rho_hit, np.nan)
        out["v_inplane"][sl] = v_in
        out["t_R"][sl] = t_R
        out["direction"][sl] = direction
    return out


def _palm_velocity(sub, t, body, dt=1e-5):
    k1 = hitter_kinematics(sub, np.stack([t - dt, t + dt], 1), body)
    return (k1["palm"][:, 1] - k1["palm"][:, 0]) / (2 * dt)


# --------------------------------------------------------------------------------------
# What the setter can know before he commits (visuomotor delay ~140 ms)
# --------------------------------------------------------------------------------------
def setter_estimate(hs, plan: Plan, model: Model, mode: str, rng, est_sd=None):
    """Return the setter's belief about each attempt's take-off state.
    mode = 'open'      : knows nothing beyond the plan (pre-planned set)
           'closed'    : Kalman-filtered view of the approach + Bayesian guess of jump power
           'telepathic': knows the take-off state exactly (but never the swing itself)"""
    N = hs["x_to"].shape[0]
    hm = model.hit
    est = {k: hs[k].copy() for k in hs}
    if mode == "open":
        est.update(x_to=np.full(N, plan.takeoff[0]), y_to=np.full(N, plan.takeoff[1]),
                   t_to=np.full(N, plan.t_to), vx=np.full(N, hm.v_lateral), vy=np.full(N, hm.v_forward),
                   vz=np.full(N, hm.vz))
    elif mode == "closed":
        e = est_sd or {}
        est["x_to"] = hs["x_to"] + e.get("pos", 0.03) * rng.standard_normal(N)
        est["y_to"] = hs["y_to"] + e.get("pos", 0.03) * rng.standard_normal(N)
        est["t_to"] = hs["t_to"] + e.get("t", 0.010) * rng.standard_normal(N)
        est["vx"] = hs["vx"] + e.get("vel", 0.05) * rng.standard_normal(N)
        est["vy"] = hs["vy"] + e.get("vel", 0.05) * rng.standard_normal(N)
        # Bayesian prediction of jump velocity from the (seen) approach speed
        sdh = e.get("hsd", HitterSD())
        vapp_seen = hs["v_app"] + e.get("vapp_obs", 0.05) * rng.standard_normal(N)
        r = sdh.corr_vapp_vz
        var_app = sdh.v_approach ** 2 + e.get("vapp_obs", 0.05) ** 2
        cov = r * sdh.vz * sdh.v_approach
        est["vz"] = hm.vz + cov / var_app * (vapp_seen - 3.75)
    elif mode == "telepathic":
        pass
    else:
        raise ValueError(mode)
    # the setter never knows the swing: assume a nominal arm and on-time swing
    for k in ("dt_swing",):
        est[k] = np.zeros(N)
    for k, v in (("tilt", hm.tilt), ("beta_c", hm.beta_c), ("gamma_c", hm.gamma_c), ("pitch_c", hm.pitch_c),
                 ("yaw_body", 0.0), ("swing_az", 0.0), ("omega_s", hm.omega_s)):
        est[k] = np.full(N, v)
    return est


def predicted_contact(est, model: Model):
    """Ball-centre contact point and time predicted from a belief `est` (dict of (N,))."""
    N = est["x_to"].shape[0]
    t_c = est["t_to"] + est["vz"] / g + est["dt_swing"]
    dt = 1e-5
    k = hitter_kinematics(est, np.stack([t_c - dt, t_c, t_c + dt], 1), model.body)
    target = k["palm"][:, 1] + model.ball.radius * k["n"][:, 1]
    return target, t_c


# --------------------------------------------------------------------------------------
# One full experiment
# --------------------------------------------------------------------------------------
def run_experiment(model: Model, plan: Plan, hsd: HitterSD, ssd: SetterSD, N, mode="open",
                   seed=0, est_sd=None, return_all=False, chunk=20000):
    """Monte Carlo: N blind attempts. mode = 'open' | 'closed' | 'telepathic' (see setter_estimate)."""
    J_nom, _ = launch_jacobian(plan.r0, plan.v0, plan.T, np.array(model.scene.release_spin), model.ball)
    parts = []
    for c, start in enumerate(range(0, N, chunk)):
        n = min(chunk, N - start)
        rng = np.random.default_rng([seed, c])
        hs, _ = sample_hitters(plan, model, hsd, n, rng)
        if mode == "open":
            v_cmd = np.broadcast_to(plan.v0, (n, 3)).copy()
        else:
            est = setter_estimate(hs, plan, model, mode, rng, est_sd=est_sd)
            target, t_c = predicted_contact(est, model)
            v_cmd = solve_launch(plan.r0, target, t_c, np.array(model.scene.release_spin), model.ball,
                                 iters=3, J_fixed=J_nom)
        r0, v0, spin, t0, _ = setter_execution(v_cmd, plan, model, ssd, rng)
        t_lo, t_hi = plan.T - 0.16, plan.T + 0.16
        tracks = BallTracks(r0, v0, spin, t_hi + 0.03, model.ball, t0=t0, t_store=t_lo)
        res = evaluate_contacts(hs, tracks, model, t_lo, t_hi)
        if return_all:
            res.update(hs=hs, r0=r0, v0=v0, spin=spin, t0=t0, v_cmd=v_cmd)
        parts.append(res)
    out = {}
    for k in parts[0]:
        if isinstance(parts[0][k], dict):
            out[k] = {kk: np.concatenate([p[k][kk] for p in parts]) for kk in parts[0][k]}
        else:
            out[k] = np.concatenate([p[k] for p in parts])
    return out


def summarize(res):
    o = res["outcome"]
    N = o.size
    s = {"N": int(N)}
    for code, name in ((CLEAN, "clean"), (PALM, "palm"), (EDGE, "edge"), (MISS, "miss")):
        s[name] = float(np.mean(o == code))
    s["spike"] = s["clean"] + s["palm"]           # ball met the palm: a real spike
    s["touch"] = s["spike"] + s["edge"]
    miss = o == MISS
    for code, name in DIRECTION_NAMES.items():
        s["miss_" + name.split(" ")[0]] = float(np.mean(res["direction"][miss] == code)) if miss.any() else 0.0
    s["se_clean"] = float(np.sqrt(s["clean"] * (1 - s["clean"]) / N))
    s["se_spike"] = float(np.sqrt(s["spike"] * (1 - s["spike"]) / N))
    return s
