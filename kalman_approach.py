"""
kalman_approach.py
==================
What can the setter actually *see* before he commits to the set?

The spiker's run-in is modelled, per horizontal axis, as a deviation w(t) from his
planned path that wanders but is pulled back toward the plan (a critically-damped
stochastic oscillator):

        w'' = -k w - c w' + s * xi(t)        (xi = white noise)

Its stationary spread is chosen to match the blind spiker's take-off scatter
(sigma_w = 10 cm, sigma_w' = 15 cm/s). The setter samples the spiker's position with
his eyes (~20 looks per second, ~5 cm error each) and fuses them with a Kalman filter.
Because of the eye-to-hand delay (~140 ms in volleyball spiking, Sardinha & Bootsma 1993),
only looks taken before t_release - 0.14 s can influence the set; the filter then
predicts forward to the take-off instant.
"""
import numpy as np


def model_matrices(dt, k, c, s):
    """Exact discretisation of the linear SDE via the matrix exponential (Van Loan)."""
    from scipy.linalg import expm
    A = np.array([[0.0, 1.0], [-k, -c]])
    Q = np.array([[0.0, 0.0], [0.0, s * s]])
    M = np.zeros((4, 4))
    M[:2, :2] = -A; M[:2, 2:] = Q; M[2:, 2:] = A.T
    E = expm(M * dt)
    F = E[2:, 2:].T
    Qd = F @ E[:2, 2:]
    return F, Qd


class ApproachKF:
    def __init__(self, sigma_w=0.10, sigma_v=0.15, zeta=1.0, obs_sd=0.05, rate=20.0):
        self.k = (sigma_v / sigma_w) ** 2
        self.c = 2 * zeta * np.sqrt(self.k)
        self.s = np.sqrt(2 * self.c) * sigma_v
        self.P0 = np.diag([sigma_w ** 2, sigma_v ** 2])
        self.obs_sd = obs_sd
        self.rate = rate
        self.dt = 1.0 / rate
        self.F, self.Q = model_matrices(self.dt, self.k, self.c, self.s)
        self.H = np.array([[1.0, 0.0]])
        self.R = np.array([[obs_sd ** 2]])

    def simulate_truth(self, n_steps, rng, n_paths=1, fine=10):
        """True deviation paths sampled at the observation rate (exact discretisation)."""
        L = np.linalg.cholesky(self.P0)
        x = (L @ rng.standard_normal((2, n_paths))).T          # (n_paths, 2)
        Lq = np.linalg.cholesky(self.Q + 1e-18 * np.eye(2))
        out = np.empty((n_paths, n_steps, 2))
        for i in range(n_steps):
            out[:, i] = x
            x = x @ self.F.T + (Lq @ rng.standard_normal((2, n_paths))).T
        return out

    def run(self, z_obs, horizon):
        """Filter observations z_obs (n_paths, n_obs) then predict `horizon` seconds ahead.
        Returns history of (mean, cov) after each update, and the final prediction."""
        n_paths, n_obs = z_obs.shape
        m = np.zeros((n_paths, 2)); P = self.P0.copy()
        hist_m, hist_P = [], []
        for i in range(n_obs):
            if i > 0:
                m = m @ self.F.T; P = self.F @ P @ self.F.T + self.Q
            S = self.H @ P @ self.H.T + self.R
            K = P @ self.H.T / S
            m = m + (z_obs[:, i:i + 1] - m[:, :1]) * K.T
            P = (np.eye(2) - K @ self.H) @ P
            hist_m.append(m.copy()); hist_P.append(P.copy())
        Fh, Qh = model_matrices(horizon, self.k, self.c, self.s)
        m_pred = m @ Fh.T
        P_pred = Fh @ P @ Fh.T + Qh
        return np.array(hist_m), np.array(hist_P), m_pred, P_pred

    def prediction_cov_vs_time(self, n_obs, horizon_after_last):
        """Covariance of the take-off prediction made after each look (deterministic)."""
        P = self.P0.copy(); out = []
        for i in range(n_obs):
            if i > 0:
                P = self.F @ P @ self.F.T + self.Q
            S = self.H @ P @ self.H.T + self.R
            K = P @ self.H.T / S
            P = (np.eye(2) - K @ self.H) @ P
            h = (n_obs - 1 - i) * self.dt + horizon_after_last
            Fh, Qh = model_matrices(h, self.k, self.c, self.s)
            out.append(Fh @ P @ Fh.T + Qh)
        return np.array(out)


def closed_loop_errors(t_cut_before_takeoff=0.090, look_window=1.0, rng=None, n_paths=20000):
    """Monte Carlo check of the Kalman prediction error of the take-off state."""
    rng = rng or np.random.default_rng(7)
    kf = ApproachKF()
    n_obs = int(round(look_window * kf.rate))
    # truth on the observation grid, continued to take-off
    extra = t_cut_before_takeoff
    truth = kf.simulate_truth(n_obs, rng, n_paths)
    # propagate the last true state exactly to take-off
    Fh, Qh = model_matrices(extra, kf.k, kf.c, kf.s)
    Lq = np.linalg.cholesky(Qh)
    x_to = truth[:, -1] @ Fh.T + (Lq @ rng.standard_normal((2, n_paths))).T
    z = truth[:, :, 0] + kf.obs_sd * rng.standard_normal((n_paths, n_obs))
    _, _, m_pred, P_pred = kf.run(z, extra)
    err = m_pred - x_to
    return dict(pos_sd_empirical=float(err[:, 0].std()), vel_sd_empirical=float(err[:, 1].std()),
                pos_sd_theory=float(np.sqrt(P_pred[0, 0])), vel_sd_theory=float(np.sqrt(P_pred[1, 1])),
                prior_pos_sd=float(np.sqrt(kf.P0[0, 0])), prior_vel_sd=float(np.sqrt(kf.P0[1, 1])),
                n_obs=n_obs, rate=kf.rate, obs_sd=kf.obs_sd, horizon=extra)


if __name__ == "__main__":
    print(closed_loop_errors())
