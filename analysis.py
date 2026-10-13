"""
analysis.py - runs every experiment behind the video and writes results.json + samples.npz
"""
import json, time, sys
import numpy as np
from multiprocessing import Pool
import freak_quick_model as fq
from kalman_approach import closed_loop_errors, ApproachKF

M = fq.Model()
PLAN = fq.make_plan(M)
KF = closed_loop_errors()
# take-off time: prior 20 ms, the plant step is seen with ~12 ms error -> posterior
T_EST = 1.0 / np.sqrt(1 / fq.HitterSD().t_to ** 2 + 1 / 0.012 ** 2)
EST = dict(pos=KF["pos_sd_empirical"], vel=KF["vel_sd_empirical"], t=T_EST, vapp_obs=0.05, hsd=fq.HitterSD())
SPIN0 = np.array(M.scene.release_spin)


def run(args):
    """Pool worker: (label, mode, hitter_scale, setter_scale, N, seed, overrides)"""
    label, mode, hk, sk, N, seed, ov = args
    hsd = fq.HitterSD().scaled(hk)
    if ov:
        hsd = fq.replace(hsd, **ov.get("hitter", {}))
    ssd = fq.SetterSD().scaled(sk)
    model, plan = M, PLAN
    if "contact_x" in ov or "T" in ov:
        cxy = (ov.get("contact_x", M.scene.contact_xy[0]), M.scene.contact_xy[1])
        model = fq.replace(M, scene=fq.replace(M.scene, contact_xy=cxy))
        plan = fq.make_plan(model, T=ov.get("T"))
    est = dict(EST); est["hsd"] = hsd
    res = fq.run_experiment(model, plan, hsd, ssd, N, mode=mode, seed=seed, est_sd=est)
    s = fq.summarize(res)
    s.update(label=label, mode=mode, hitter_scale=hk, setter_scale=sk)
    return s


def window_sweep(model, plan, key="dt_swing", values=None):
    values = np.arange(-0.040, 0.04001, 0.00025) if values is None else values
    N = values.size
    hs = {k: np.repeat(v, N) for k, v in plan.nominal.items()}
    hs[key] = values.copy() if key != "dz" else values.copy()
    tr = fq.BallTracks(np.repeat(plan.r0[None], N, 0), np.repeat(plan.v0[None], N, 0), SPIN0,
                       plan.T + 0.2, model.ball, t_store=plan.T - 0.16)
    return values, fq.evaluate_contacts(hs, tr, model, plan.T - 0.16, plan.T + 0.16)


def edges(values, outcome, ok_codes):
    ok = np.isin(outcome, ok_codes)
    if not ok.any():
        return [0.0, 0.0]
    idx = np.where(ok)[0]
    # contiguous block around zero
    z = np.argmin(np.abs(values))
    lo = z
    while lo - 1 >= 0 and ok[lo - 1]:
        lo -= 1
    hi = z
    while hi + 1 < len(values) and ok[hi + 1]:
        hi += 1
    return [float(values[lo]), float(values[hi])]


def dartboard_of(hs, r0, v0, spin, t0, model, plan):
    tr = fq.BallTracks(r0, v0, spin, plan.T + 0.2, model.ball, t0=t0, t_store=plan.T - 0.16)
    return fq.evaluate_contacts(hs, tr, model, plan.T - 0.16, plan.T + 0.16)


def sensitivities():
    """Linear sensitivity of the dartboard point (e_s, e_a) to every error source."""
    base = {k: v.copy() for k, v in PLAN.nominal.items()}
    hsd, ssd = fq.HitterSD(), fq.SetterSD()
    hitter_src = [("dt_swing", "swing timing", hsd.dt_swing, 1e-3), ("t_to", "take-off time", hsd.t_to, 1e-3),
                  ("x_to", "take-off spot (along net)", hsd.x_to, 1e-3), ("y_to", "take-off spot (to net)", hsd.y_to, 1e-3),
                  ("vz", "jump power", hsd.vz, 1e-3), ("vx", "sideways drift", hsd.v_lateral, 1e-3),
                  ("vy", "forward drift", hsd.v_forward, 1e-3), ("tilt", "arm lean", hsd.tilt, 1e-3),
                  ("beta_c", "elbow bend", hsd.beta_c, 1e-3), ("gamma_c", "wrist angle", hsd.gamma_c, 1e-3),
                  ("pitch_c", "trunk lean", hsd.pitch_c, 1e-3), ("yaw_body", "body turn", hsd.yaw_body, 1e-3),
                  ("swing_az", "swing direction", hsd.swing_az, 1e-3), ("omega_s", "swing speed", hsd.omega_s, 1e-2)]
    rows = []
    hs_list = [base]
    for key, name, sd, h in hitter_src:
        d = {k: v.copy() for k, v in base.items()}
        d[key] = d[key] + h
        hs_list.append(d)
    hs = {k: np.concatenate([d[k] for d in hs_list]) for k in base}
    n = len(hs_list)
    res = dartboard_of(hs, np.repeat(PLAN.r0[None], n, 0), np.repeat(PLAN.v0[None], n, 0), SPIN0, np.zeros(n), M, PLAN)
    e0 = np.array([res["e_s"][0], res["e_a"][0]])
    for i, (key, name, sd, h) in enumerate(hitter_src):
        J = (np.array([res["e_s"][i + 1], res["e_a"][i + 1]]) - e0) / h
        rows.append(dict(key=key, name=name, who="spiker", sd=sd, J=J.tolist(),
                         contrib_s=float(abs(J[0]) * sd), contrib_a=float(abs(J[1]) * sd)))
    # setter sources: perturb release parameters
    sp, el, az = PLAN.speed, np.radians(PLAN.elevation_deg), np.radians(PLAN.azimuth_deg)
    def vel(sp_, el_, az_):
        return np.array([sp_ * np.cos(el_) * np.sin(az_), sp_ * np.cos(el_) * np.cos(az_), sp_ * np.sin(el_)])
    setter_src = [("speed", "set speed", ssd.speed_cv, 1e-4), ("el", "set angle (up/down)", ssd.elevation, 1e-4),
                  ("az", "set angle (left/right)", ssd.azimuth, 1e-4), ("t", "release timing", ssd.t_release, 1e-4),
                  ("px", "release point x", ssd.pos, 1e-4), ("pz", "release point z", ssd.pos, 1e-4),
                  ("spin_side", "spin (side axis)", ssd.spin, 1e-2)]
    n = len(setter_src) + 1
    r0 = np.repeat(PLAN.r0[None], n, 0); v0 = np.repeat(PLAN.v0[None], n, 0)
    spin = np.zeros((n, 3)); t0 = np.zeros(n)
    for i, (key, name, sd, h) in enumerate(setter_src, start=1):
        if key == "speed": v0[i] = vel(sp * (1 + h), el, az)
        if key == "el": v0[i] = vel(sp, el + h, az)
        if key == "az": v0[i] = vel(sp, el, az + h)
        if key == "t": t0[i] = h
        if key == "px": r0[i, 0] += h
        if key == "pz": r0[i, 2] += h
        if key == "spin_side": spin[i] = [0.0, 1.0 * h * 100, 0.0]   # about the y axis
    hs = {k: np.repeat(v, n) for k, v in base.items()}
    res = dartboard_of(hs, r0, v0, spin, t0, M, PLAN)
    e0 = np.array([res["e_s"][0], res["e_a"][0]])
    for i, (key, name, sd, h) in enumerate(setter_src, start=1):
        hh = h * 100 if key == "spin_side" else h
        J = (np.array([res["e_s"][i], res["e_a"][i]]) - e0) / hh
        rows.append(dict(key=key, name=name, who="setter", sd=sd, J=J.tolist(),
                         contrib_s=float(abs(J[0]) * sd), contrib_a=float(abs(J[1]) * sd)))
    return rows


def sample_attempts(mode, N, seed, setter_scale=1.0):
    """A small set of fully-specified attempts for the animation."""
    rng = np.random.default_rng(seed)
    hsd, ssd = fq.HitterSD(), fq.SetterSD().scaled(setter_scale)
    hs, _ = fq.sample_hitters(PLAN, M, hsd, N, rng)
    if mode == "open":
        v_cmd = np.broadcast_to(PLAN.v0, (N, 3)).copy()
    else:
        est = fq.setter_estimate(hs, PLAN, M, mode, rng, est_sd=EST)
        target, t_c = fq.predicted_contact(est, M)
        v_cmd = fq.solve_launch(PLAN.r0, target, t_c, SPIN0, M.ball, iters=4)
    r0, v0, spin, t0, _ = fq.setter_execution(v_cmd, PLAN, M, ssd, rng)
    res = dartboard_of(hs, r0, v0, spin, t0, M, PLAN)
    return dict(hs=hs, r0=r0, v0=v0, spin=spin, t0=t0, v_cmd=v_cmd, **res)


def main(quick=False):
    t_start = time.time()
    R = {}
    nmain = 20000 if quick else 100000
    ncurve = 6000 if quick else 20000
    ngrid = 3000 if quick else 10000

    # ---------------- A. perfect-world plan -----------------
    p = PLAN
    vac_end, _ = fq.ball_endpoint(p.r0[None], p.v0_vac[None], None, np.array([p.T]), M.ball)
    spin_end, _ = fq.ball_endpoint(p.r0[None], p.v0[None], np.array([[0.0, 2 * np.pi, 0.0]]), np.array([p.T]), M.ball)
    # Newton iterations from a naive guess: straight-line aim at 8 m/s, no gravity compensation
    naive_dir = (p.target - p.r0) / np.linalg.norm(p.target - p.r0)
    v_try = naive_dir * np.linalg.norm(p.target - p.r0) / p.T
    newton = [v_try.copy()]
    J_nom, _ = fq.launch_jacobian(p.r0, p.v0, p.T, SPIN0, M.ball)
    for _ in range(4):
        e, _ = fq.ball_endpoint(p.r0[None], v_try[None], None, np.array([p.T]), M.ball)
        Jv, _ = fq.launch_jacobian(p.r0, v_try, p.T, SPIN0, M.ball)
        v_try = v_try - np.linalg.solve(Jv, e[0] - p.target)
        newton.append(v_try.copy())
    newton_miss = []
    for v in newton:
        e, _ = fq.ball_endpoint(p.r0[None], v[None], None, np.array([p.T]), M.ball)
        newton_miss.append(float(np.linalg.norm(e[0] - p.target)))
    v_in = p.v_ball_c - np.dot(p.v_ball_c, p.n_palm) * p.n_palm
    R["plan"] = dict(T=p.T, speed=p.speed, elevation_deg=p.elevation_deg, azimuth_deg=p.azimuth_deg,
                     v0=p.v0.tolist(), v0_vac=p.v0_vac.tolist(), r0=p.r0.tolist(), target=p.target.tolist(),
                     takeoff=p.takeoff.tolist(), t_to=p.t_to, palm_speed=float(np.linalg.norm(p.v_palm)),
                     v_palm=p.v_palm.tolist(), n_palm=p.n_palm.tolist(), a_palm=p.a_palm.tolist(),
                     ball_speed_contact=float(np.linalg.norm(p.v_ball_c)), v_ball_contact=p.v_ball_c.tolist(),
                     ball_inplane_speed=float(np.linalg.norm(v_in)),
                     set_distance=float(np.linalg.norm(p.target[:2] - p.r0[:2])),
                     rise=float(M.hit.vz ** 2 / (2 * fq.g)), rise_time=float(M.hit.vz / fq.g),
                     apex_com=float(M.body.com_takeoff + M.hit.vz ** 2 / (2 * fq.g)),
                     vacuum_miss=(vac_end[0] - p.target).tolist(), vacuum_miss_dist=float(np.linalg.norm(vac_end[0] - p.target)),
                     spin1rps_miss=(spin_end[0] - p.target).tolist(), spin1rps_miss_dist=float(np.linalg.norm(spin_end[0] - p.target)),
                     newton=[v.tolist() for v in newton], newton_miss=newton_miss,
                     drag_force_release=float(M.ball.mass * M.ball.k * fq.drag_coefficient(p.speed, M.ball) * p.speed ** 2),
                     weight=float(M.ball.mass * fq.g), ball=dict(mass=M.ball.mass, radius=M.ball.radius, cd=M.ball.cd_sub,
                     k=M.ball.k), body=dict(height=M.body.height, reach=M.body.reach, r_hand=M.body.r_hand,
                     rho_clean=M.body.rho_clean, com_takeoff=M.body.com_takeoff), hitter=fq.asdict(M.hit) if hasattr(fq, "asdict") else {})
    print("A done %.0fs" % (time.time() - t_start), flush=True)

    # ---------------- B. tolerance windows -----------------
    vals, w = window_sweep(M, p, "dt_swing")
    R["window_time"] = dict(clean=edges(vals, w["outcome"], [fq.CLEAN]), spike=edges(vals, w["outcome"], [fq.CLEAN, fq.PALM]),
                            touch=edges(vals, w["outcome"], [fq.CLEAN, fq.PALM, fq.EDGE]),
                            values=vals[::8].tolist(), e_s=w["e_s"][::8].tolist(), e_a=w["e_a"][::8].tolist(),
                            outcome=w["outcome"][::8].tolist())
    vals, w = window_sweep(M, p, "dz", np.arange(-0.25, 0.2501, 0.0005))
    R["window_height"] = dict(clean=edges(vals, w["outcome"], [fq.CLEAN]), spike=edges(vals, w["outcome"], [fq.CLEAN, fq.PALM]),
                              touch=edges(vals, w["outcome"], [fq.CLEAN, fq.PALM, fq.EDGE]))
    print("B done %.0fs" % (time.time() - t_start), R["window_time"]["clean"], R["window_height"]["clean"], flush=True)

    # ---------------- C. sensitivities / error budget -----------------
    R["sensitivity"] = sensitivities()
    print("C done %.0fs" % (time.time() - t_start), flush=True)

    # ---------------- D..I. Monte Carlo -----------------
    jobs = []
    for mode in ("open", "closed", "telepathic"):
        for sk in (1.0, 0.0):
            jobs.append((f"main_{mode}_setter{sk:g}", mode, 1.0, sk, nmain, 11, {}))
    # E. swing timing curves
    sw = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]
    for ms in sw:
        jobs.append((f"swing_tele_perfect_{ms}", "telepathic", 1.0, 0.0, ncurve, 21, {"hitter": {"dt_swing": ms / 1000}}))
        jobs.append((f"swing_tele_elite_{ms}", "telepathic", 1.0, 1.0, ncurve, 21, {"hitter": {"dt_swing": ms / 1000}}))
        jobs.append((f"swing_closed_elite_{ms}", "closed", 1.0, 1.0, ncurve, 21, {"hitter": {"dt_swing": ms / 1000}}))
    # F. requirement multipliers
    ks = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]
    for k in ks:
        jobs.append((f"hitterk_{k}", "telepathic", k, 0.0, ncurve, 31, {}))
        jobs.append((f"setterk_{k}", "telepathic", 0.0, k, ncurve, 32, {}))
    # G. heat map (telepathic setter, multipliers)
    hk_grid = np.round(np.linspace(0, 1.2, 9), 3).tolist()
    sk_grid = np.round(np.linspace(0, 1.6, 9), 3).tolist()
    for hk in hk_grid:
        for sk in sk_grid:
            jobs.append((f"grid_{hk}_{sk}", "telepathic", hk, sk, ngrid, 41, {}))
    # H. distance sweep
    dist_x = [0.5, 0.0, -0.5, -1.0, -1.5, -2.0, -2.5, -3.0]
    for cx in dist_x:
        jobs.append((f"dist_tele_{cx}", "telepathic", 1.0, 1.0, ncurve, 51, {"contact_x": cx}))
        jobs.append((f"dist_closed_{cx}", "closed", 1.0, 1.0, ncurve, 51, {"contact_x": cx}))
        jobs.append((f"dist_teleperf_{cx}", "telepathic", 1.0, 0.0, ncurve, 51, {"contact_x": cx}))
    # I. tempo trade-off (D = 3 m), flight times not tied to the apex
    Ts = [0.30, 0.34, 0.40, 0.46, 0.52, 0.60, 0.70]
    for T in Ts:
        jobs.append((f"tempo_teleperf_{T}", "telepathic", 1.0, 0.0, ncurve, 61, {"T": T}))
        jobs.append((f"tempo_tele_{T}", "telepathic", 1.0, 1.0, ncurve, 61, {"T": T}))
    print("running %d MC jobs" % len(jobs), flush=True)
    with Pool(2) as pool:
        out = []
        for i, s in enumerate(pool.imap(run, jobs, chunksize=1)):
            out.append(s)
            if i % 10 == 0:
                print("  %d/%d  %.0fs  %s clean=%.3f spike=%.3f" % (i, len(jobs), time.time() - t_start, s["label"], s["clean"], s["spike"]), flush=True)
    R["mc"] = {s["label"]: s for s in out}
    R["grid_axes"] = dict(hitter=hk_grid, setter=sk_grid)
    R["swing_ms"] = sw
    R["ks"] = ks
    R["dist_x"] = dist_x
    R["tempo_T"] = Ts
    # windows and ball speeds for each distance / tempo plan
    R["dist_info"] = []
    for cx in dist_x:
        mdl = fq.replace(M, scene=fq.replace(M.scene, contact_xy=(cx, M.scene.contact_xy[1])))
        pl = fq.make_plan(mdl)
        vals, w = window_sweep(mdl, pl, "dt_swing")
        vin = pl.v_ball_c - np.dot(pl.v_ball_c, pl.n_palm) * pl.n_palm
        R["dist_info"].append(dict(contact_x=cx, D=float(np.linalg.norm(pl.target[:2] - pl.r0[:2])), T=pl.T,
                                   speed=pl.speed, v_in=float(np.linalg.norm(vin)),
                                   clean=edges(vals, w["outcome"], [fq.CLEAN]),
                                   spike=edges(vals, w["outcome"], [fq.CLEAN, fq.PALM])))
    R["tempo_info"] = []
    for T in Ts:
        pl = fq.make_plan(M, T=T)
        vals, w = window_sweep(M, pl, "dt_swing")
        vin = pl.v_ball_c - np.dot(pl.v_ball_c, pl.n_palm) * pl.n_palm
        R["tempo_info"].append(dict(T=T, speed=pl.speed, elevation=pl.elevation_deg, v_in=float(np.linalg.norm(vin)),
                                    vz_contact=float(pl.v_ball_c[2]), t_to=pl.t_to,
                                    clean=edges(vals, w["outcome"], [fq.CLEAN]),
                                    spike=edges(vals, w["outcome"], [fq.CLEAN, fq.PALM])))
    print("MC done %.0fs" % (time.time() - t_start), flush=True)

    # ---------------- J/K. samples for the animation & dartboards -----------------
    smp = {}
    for mode, seed in (("open", 101), ("closed", 102), ("telepathic", 103)):
        a = sample_attempts(mode, 4000, seed)
        for k, v in a.items():
            if isinstance(v, dict):
                for kk, vv in v.items():
                    smp[f"{mode}_hs_{kk}"] = vv
            else:
                smp[f"{mode}_{k}"] = v
    np.savez_compressed("samples.npz", **smp)
    # Kalman demo data
    kf = ApproachKF()
    rng = np.random.default_rng(5)
    n_obs = 20
    truth = kf.simulate_truth(n_obs, rng, n_paths=2)
    z = truth[:, :, 0] + kf.obs_sd * rng.standard_normal((2, n_obs))
    hm, hP, mp, Pp = kf.run(z, 0.09)
    R["kalman"] = dict(errors=KF, t_est_sd=T_EST, pred_cov=kf.prediction_cov_vs_time(n_obs, 0.09)[:, 0, 0].tolist(),
                       truth=truth[:, :, 0].tolist(), obs=z.tolist(), est=hm[:, :, 0].T.tolist() if hm.ndim == 3 else [],
                       pred=mp[:, 0].tolist(), rate=kf.rate)
    R["est_sd"] = {k: v for k, v in EST.items() if k != "hsd"}
    R["hitter_sd"] = {k: getattr(fq.HitterSD(), k) for k in fq.HitterSD.__dataclass_fields__}
    R["setter_sd"] = {k: getattr(fq.SetterSD(), k) for k in fq.SetterSD.__dataclass_fields__}
    R["runtime_s"] = time.time() - t_start
    with open("results.json", "w") as f:
        json.dump(R, f, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print("ALL DONE %.0fs" % (time.time() - t_start))


if __name__ == "__main__":
    main(quick="--quick" in sys.argv)
