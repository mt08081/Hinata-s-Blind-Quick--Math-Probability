"""
audio.py - procedural soundtrack + sound effects for the video (numpy only).
Builds music sections aligned to the scene timeline and drops SFX at each scene's events.
Writes soundtrack.wav (44.1 kHz, stereo, 16-bit).
"""
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100
BPM = 120.0
BEAT = 60.0 / BPM
rng = np.random.default_rng(12)


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def env_adsr(n, a=0.005, d=0.1, s=0.6, r=0.1, sr=SR):
    a_n, d_n, r_n = int(a * sr), int(d * sr), int(r * sr)
    s_n = max(0, n - a_n - d_n - r_n)
    e = np.concatenate([np.linspace(0, 1, max(1, a_n), endpoint=False),
                        np.linspace(1, s, max(1, d_n), endpoint=False),
                        np.full(s_n, s), np.linspace(s, 0, max(1, r_n))])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))


def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    # band-limited-ish saw: sum of harmonics up to ~10 kHz
    out = np.zeros(n)
    kmax = int(min(40, 10000 / max(f, 1)))
    for k in range(1, kmax + 1):
        out += ((-1) ** (k + 1)) * np.sin(2 * np.pi * k * f * t + k * phase) / k
    return out * 0.6


def square(f, n, duty=0.5):
    t = np.arange(n) / SR
    out = np.zeros(n)
    kmax = int(min(25, 9000 / max(f, 1)))
    for k in range(1, kmax + 1, 2):
        out += np.sin(2 * np.pi * k * f * t) / k
    return out * 0.8


def lowpass(x, fc, order=2):
    b, a = signal.butter(order, min(0.99, fc / (SR / 2)), "low")
    return signal.lfilter(b, a, x)


def highpass(x, fc, order=2):
    b, a = signal.butter(order, min(0.99, fc / (SR / 2)), "high")
    return signal.lfilter(b, a, x)


def bandpass(x, f0, f1, order=2):
    b, a = signal.butter(order, [max(1e-4, f0 / (SR / 2)), min(0.99, f1 / (SR / 2))], "band")
    return signal.lfilter(b, a, x)


# ------------------------------------------------------------------ drums
def kick(gain=1.0):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 7.5)
    x[:200] += rng.normal(0, 0.4, 200) * np.linspace(1, 0, 200)
    return np.tanh(x * 1.6) * gain


def snare(gain=1.0):
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    noise = bandpass(rng.normal(0, 1, n), 1200, 8000) * np.exp(-t * 18)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return (noise * 0.8 + tone * 0.5) * gain


def hat(gain=1.0, open_=False):
    n = int((0.22 if open_ else 0.05) * SR)
    t = np.arange(n) / SR
    x = highpass(rng.normal(0, 1, n), 7000, 3) * np.exp(-t * (14 if open_ else 70))
    return x * 0.35 * gain


def crash(gain=1.0):
    n = int(2.2 * SR)
    t = np.arange(n) / SR
    x = highpass(rng.normal(0, 1, n), 4000, 2) * np.exp(-t * 2.2)
    return x * 0.35 * gain


# ------------------------------------------------------------------ helpers
def add(buf, x, t0, gain=1.0, pan=0.0):
    i0 = int(t0 * SR)
    if i0 >= buf.shape[0] or i0 + len(x) <= 0:
        return
    if i0 < 0:
        x = x[-i0:]; i0 = 0
    i1 = min(buf.shape[0], i0 + len(x))
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    buf[i0:i1, 0] += x[:i1 - i0] * gain * l * 1.4142
    buf[i0:i1, 1] += x[:i1 - i0] * gain * r * 1.4142


def reverb_ir(seconds=1.6, decay=3.2, seed=4):
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = r.normal(0, 1, (n, 2)) * np.exp(-t * decay)[:, None]
    ir = np.stack([lowpass(ir[:, 0], 6000), lowpass(ir[:, 1], 6000)], 1)
    ir[0] = 0
    return ir / np.sqrt(np.sum(ir ** 2, axis=0))


def apply_reverb(buf, wet=0.18, ir=None):
    ir = reverb_ir() if ir is None else ir
    out = np.stack([signal.fftconvolve(buf[:, c], ir[:, c])[:len(buf)] for c in range(2)], 1)
    return buf * (1 - wet) + out * wet * 0.6


# ------------------------------------------------------------------ SFX
def sfx(name):
    t = lambda d: np.arange(int(d * SR)) / SR
    if name == "whoosh":
        tt = t(0.55); n = len(tt)
        x = rng.normal(0, 1, n)
        out = np.zeros(n)
        # sweep a bandpass upward by filtering chunks
        for i in range(0, n, 512):
            fc = 300 + 5000 * (i / n) ** 1.5
            seg_ = bandpass(x[max(0, i - 2048):i + 512], fc * 0.6, fc * 1.6, 1)[-min(512, n - i):]
            out[i:i + len(seg_)] = seg_
        return out * np.sin(np.pi * tt / tt[-1]) ** 1.5 * 0.7
    if name == "squeak":
        tt = t(0.12)
        f = 2600 + 900 * np.sin(2 * np.pi * 30 * tt)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 18) * 0.25
    if name == "stomp":
        tt = t(0.4)
        return (np.sin(2 * np.pi * (60 + 80 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 10) +
                lowpass(rng.normal(0, 1, len(tt)), 900) * np.exp(-tt * 25) * 0.6)
    if name == "eye":
        tt = t(1.2)
        x = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * (3 + i)) / (i + 1) for i, f in enumerate((1318, 1976, 2637)))
        return x * 0.35
    if name in ("impact", "slam", "hit_text", "beat_in", "outro"):
        dur = {"impact": 2.0, "slam": 1.2, "hit_text": 0.6, "beat_in": 1.5, "outro": 4.0}[name]
        tt = t(dur)
        boom = np.sin(2 * np.pi * (42 + 90 * np.exp(-tt * 18)) * tt) * np.exp(-tt * (2.5 if name != "hit_text" else 9))
        crack = highpass(rng.normal(0, 1, len(tt)), 1500) * np.exp(-tt * (25 if name != "impact" else 12))
        g = {"impact": 1.0, "slam": 0.8, "hit_text": 0.35, "beat_in": 0.7, "outro": 0.8}[name]
        x = boom * 1.1 + crack * (0.7 if name == "impact" else 0.35)
        if name in ("beat_in", "outro", "impact"):
            x = x + crash(0.8)[:len(tt)] if len(tt) <= int(2.2 * SR) else x
        return np.tanh(x * 1.2) * g
    if name == "riser":
        tt = t(6.0)
        x = rng.normal(0, 1, len(tt))
        out = np.zeros_like(x)
        n = len(tt)
        for i in range(0, n, 1024):
            fc = 200 + 6000 * (i / n) ** 2
            seg_ = bandpass(x[max(0, i - 4096):i + 1024], fc * 0.7, fc * 1.3, 1)[-min(1024, n - i):]
            out[i:i + len(seg_)] = seg_
        tone = np.sin(2 * np.pi * np.cumsum(110 + 330 * (tt / tt[-1]) ** 2) / SR) * 0.15
        return (out * 0.5 + tone) * (tt / tt[-1]) ** 1.5
    if name == "rise":
        tt = t(2.0)
        tone = np.sin(2 * np.pi * np.cumsum(220 + 660 * (tt / tt[-1]) ** 2) / SR)
        return tone * (tt / tt[-1]) ** 2 * 0.2
    if name == "tick":
        tt = t(0.06)
        return np.sin(2 * np.pi * 2200 * tt) * np.exp(-tt * 90) * 0.35
    if name == "pop":
        tt = t(0.12)
        f = 600 + 900 * np.exp(-tt * 40)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 30) * 0.4
    if name == "chime":
        out = np.zeros(int(1.6 * SR))
        for i, m in enumerate((78, 81, 85, 90)):
            tt = t(1.6 - 0.07 * i)
            x = np.sin(2 * np.pi * midi_hz(m) * tt) * np.exp(-tt * 3.5) * 0.18
            out[int(0.07 * i * SR):int(0.07 * i * SR) + len(x)] += x
        return out
    if name == "buzz":
        tt = t(0.45)
        return np.tanh(square(110, len(tt)) * 2) * np.exp(-tt * 5) * 0.18
    if name == "rain":
        n = int(3.0 * SR)
        out = np.zeros(n)
        for k in range(160):
            p = int(rng.uniform(0, 1) ** 0.8 * (n - 2000))
            f = rng.uniform(1800, 4200)
            tt = t(0.025)
            out[p:p + len(tt)] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 200) * rng.uniform(0.05, 0.18)
        return out
    if name == "kalman":
        n = int(5.0 * SR)
        out = np.zeros(n)
        for k in range(20):
            p = int((0.0 + k * 0.25) * SR)
            tt = t(0.05)
            out[p:p + len(tt)] += np.sin(2 * np.pi * (1200 + 25 * k) * tt) * np.exp(-tt * 80) * 0.18
        return out
    raise KeyError(name)


# ------------------------------------------------------------------ music
PROG = [(42, [66, 69, 73]), (38, [62, 66, 69]), (45, [69, 73, 76]), (40, [64, 68, 71])]   # F#m D A E


def music(total, sections):
    """sections: list of (t0, t1, energy) with energy in {0: drone, 1: light, 2: groove, 3: full}."""
    buf = np.zeros((int(total * SR) + SR, 2))
    pad_bus = np.zeros_like(buf)
    nbeats = int(total / BEAT) + 1
    for b in range(nbeats):
        tb = b * BEAT
        en = 0
        for t0, t1, e in sections:
            if t0 <= tb < t1:
                en = e
        bar_pos = b % 4
        chord_i = (b // 8) % 4
        root, tones = PROG[chord_i]
        # drums
        if en >= 2:
            if bar_pos in (0, 2) or (en == 3 and bar_pos == 3 and b % 8 == 7):
                add(buf, kick(0.9), tb)
            if bar_pos in (1, 3):
                add(buf, snare(0.55 if en == 3 else 0.35), tb, pan=0.05)
            for h in range(2):
                add(buf, hat(0.6 if en == 3 else 0.4, open_=(h == 1 and bar_pos == 3)), tb + h * BEAT / 2,
                    pan=0.3)
        elif en == 1:
            if bar_pos == 0:
                add(buf, kick(0.45), tb)
            add(buf, hat(0.25), tb + BEAT / 2, pan=0.3)
        # bass (8ths)
        if en >= 1:
            for h in range(2):
                n = int(BEAT / 2 * SR * 0.9)
                f = midi_hz(root - 12 + (12 if (en == 3 and h == 1) else 0))
                x = lowpass(saw(f, n), 600 if en < 3 else 1100) * env_adsr(n, 0.004, 0.08, 0.5, 0.05)
                add(buf, x, tb + h * BEAT / 2, 0.30 if en >= 2 else 0.18)
        # arp (16ths) for groove/full
        if en >= 2:
            for q in range(4):
                m = tones[(b * 4 + q) % 3] + (12 if (q % 2 == 1 and en == 3) else 0)
                n = int(BEAT / 4 * SR)
                x = lowpass(square(midi_hz(m), n), 2600) * env_adsr(n, 0.002, 0.06, 0.15, 0.03)
                add(buf, x, tb + q * BEAT / 4, 0.055 if en == 2 else 0.075, pan=(-0.35 if q % 2 else 0.35))
        # pad: one chord per 8 beats
        if b % 8 == 0 and en >= 0:
            dur = 8 * BEAT
            n = int(dur * SR)
            x = np.zeros(n)
            for m in tones:
                for det in (-0.08, 0.0, 0.07):
                    x += saw(midi_hz(m - 12) * 2 ** (det / 12), n, phase=rng.uniform(0, 6))
            x = lowpass(x, 900 if en < 3 else 1600) * env_adsr(n, 0.8, 0.5, 0.8, 1.5)
            add(pad_bus, x, tb, 0.020 if en == 0 else 0.028)
        # drone for energy 0
        if en == 0 and b % 8 == 0:
            n = int(8 * BEAT * SR)
            x = lowpass(saw(midi_hz(root - 12), n), 260) * env_adsr(n, 1.0, 0.5, 0.9, 1.0)
            add(buf, x, tb, 0.22)
    # sidechain-style ducking of the pad on each beat in groove sections
    duck = np.ones(len(buf))
    for b in range(nbeats):
        tb = b * BEAT
        en = max([e for t0, t1, e in sections if t0 <= tb < t1] or [0])
        if en >= 2:
            i0 = int(tb * SR); n = int(0.35 * SR)
            seg_ = 1 - 0.6 * np.exp(-np.arange(n) / SR * 9)
            duck[i0:i0 + n] = np.minimum(duck[i0:i0 + n], seg_[:len(duck[i0:i0 + n])])
    buf += pad_bus * duck[:, None]
    return buf


def build(timeline, events, out="soundtrack.wav"):
    """timeline: list of (name, start, dur); events: dict name -> [(t, sfx, gain)]."""
    total = timeline[-1][1] + timeline[-1][2]
    st = {n: s for n, s, d in timeline}
    # music energy per scene
    E = {"01_cold_open": 0, "02_title": 3, "03_rules": 1, "04_coords": 1, "05_ball": 2, "06_spiker": 2,
         "07_perfect": 2, "08_human": 1, "09_window": 2, "10_montecarlo": 2, "11_budget": 2,
         "12_requirements": 2, "13_levers": 2, "14_verdict": 3}
    sections = []
    for n, s, d in timeline:
        e = E.get(n, 1)
        if n == "01_cold_open":
            sections += [(s, s + 6.3, 0), (s + 6.3, s + 16.0, 0)]
        elif n == "10_montecarlo":
            sections += [(s, s + 31.0, 2), (s + 31.0, s + d, 3)]
        elif n == "14_verdict":
            sections += [(s, s + 16.5, 3), (s + 16.5, s + d - 6, 2), (s + d - 6, s + d, 0)]
        else:
            sections.append((s, s + d, e))
    mus = music(total, sections)
    # fade the music at the very end
    n_end = int(total * SR)
    fade_n = int(4 * SR)
    mus[n_end - fade_n:n_end] *= np.linspace(1, 0, fade_n)[:, None]
    mus[n_end:] = 0
    mus = apply_reverb(mus, 0.16)
    fx = np.zeros_like(mus)
    for n, s, d in timeline:
        for (t, name, gain) in events.get(n, []):
            add(fx, sfx(name), s + t, gain * 0.9, pan=float(rng.uniform(-0.15, 0.15)))
    fx = apply_reverb(fx, 0.12, reverb_ir(1.0, 4.5, 9))
    mix = mus * 0.55 + fx * 0.85
    mix = mix[:n_end]
    # gentle master: soft clip + normalise
    peak = np.max(np.abs(mix)) + 1e-9
    mix = np.tanh(mix / peak * 1.25) / np.tanh(1.25)
    mix *= 0.89
    wavfile.write(out, SR, (mix * 32767).astype(np.int16))
    return out, total


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    import video
    video.import_scenes()
    from registry import SCENES, EVENTS
    tl, t = [], 0.0
    for n, d, _ in SCENES:
        tl.append((n, t, d)); t += d
    out, total = build(tl, EVENTS)
    print("wrote", out, "%.1f s" % total)
