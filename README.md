# The Blind Quick — model, simulation and video source

Physics + Monte Carlo model of a minus-tempo quick where the spiker swings with his eyes
closed and the setter has to put the ball on his palm. Every number in the video comes
from these files.

## Files

| file | what it does |
|---|---|
| `freak_quick_model.py` | the physics: ball flight (gravity + drag + Magnus, RK4), ballistic jump, 3-link arm, sphere-vs-palm contact test, shooting-method inverse solver, setter information models, Monte Carlo runner |
| `kalman_approach.py` | what the setter can see: Kalman filter on the spiker's run-in, with the eye-to-hand delay |
| `analysis.py` | runs every experiment and writes `results.json` + `samples.npz` |
| `results.json` | all results used on screen |
| `engine.py`, `world.py`, `common.py`, `charts.py`, `scenes_a.py`, `scenes_b.py`, `video.py`, `audio.py` | the renderer (Skia), scenes, and procedural soundtrack |

Run: `python3 analysis.py` (≈20 min on 2 cores), then `python3 video.py render <scene>` and `python3 audio.py`.
Needs numpy, scipy, matplotlib, skia-python, ffmpeg.

## Coordinates

Origin on the floor under the middle of the net; x along the net (setter at +x), y toward
the net (our court is y < 0), z up; t = 0 when the ball leaves the setter's hands.

## Assumptions

Perfect pass; setter planted (release at (1.00, −0.70, 2.35) m); regulation ball (270 g,
r = 10.5 cm), rigid; still sea-level air (ρ = 1.2 kg/m³); empty court; net 2.43 m; the
spiker always jumps and always swings and makes no corrections after take-off; right-handed
spiker, arm = planar 3-link chain; hand = disc of radius 8.5 cm with a 5 cm sweet spot.

## Governing equations

Ball: m dv/dt = m g − ½ ρ C_D A |v| v + ½ ρ C_L A |v|² (ω̂ × v̂), C_D = 0.45 below the
drag crisis (~14 m/s), C_L ≈ 0.9·Rω/|v|.

Spiker centre of mass after take-off: r(t) = r₀ + v₀ t + ½ g t² (projectile).

Palm: p(t) = s(t) + L₁ ê(θ) + L₂ ê(θ − β) + L₃ ê(θ − β + γ), with shoulder, elbow and wrist
angles following measured spike swing speeds (shoulder ≈ 720°/s, elbow ≈ 1270°/s peak),
in a swing plane that can lean and turn.

Contact: first instant the ball sphere touches the palm disc,
dist = √(h² + max(ρ − r_hand, 0)²) ≤ R_ball (h = distance along the palm normal, ρ = offset
in the palm plane). Graded as sweet spot (ρ ≤ 5 cm), palm (≤ 8.5 cm), edge/fingertips, or whiff.

Inverse problem: find v₀ such that r_ball(T; v₀) = palm target — Newton/shooting with a
finite-difference Jacobian; T chosen so the ball is at the top of its arc at the palm.

## Key results (100,000 attempts per case unless noted)

Perfect world: set at 10.0 m/s, 20.6° up, flight 0.34 s; the spiker leaves the floor 48 ms
before the release; ball arrives at 8.4 m/s, palm moving at 15.8 m/s. Ignoring air
resistance misses by 16 cm; 1 rev/s of spin moves the ball 2.4 cm.

Timing window at 3 m: sweet spot ±6.0 ms, on the palm ±10.3 ms, any touch −32/+17.5 ms.

| setter | sweet spot | on the palm (incl. sweet spot) | any touch |
|---|---|---|---|
| pre-planned (open loop) | 4.6 % | 12.3 % | 46.5 % |
| reads the approach (Kalman, 0.14 s delay) | 7.2 % | 18.8 % | 61.3 % |
| mind reader (knows the jump exactly) | 12.4 % | 30.8 % | 78.6 % |
| mind reader + zero release error | 33.0 % | 54.6 % | 89.6 % |

For 99 % sweet spot: the spiker's in-air variability must shrink ~6× (blind swing timing
±2 ms) and the setter's release noise ~4.6× (angle ±0.24°, speed ±0.35 %, timing ±1.1 ms).

Shorter sets help (0.6 m away: window ±35 ms); slower sets help a little (0.70 s flight:
±10 ms) but stop being minus tempo.

## Data anchors

FIVB ball specs; drag crisis ~14 m/s (Asai et al. 2010); spike kinematics (Hu et al. 2005;
Fuchs et al. 2019); spike jump-height CV ~6 % (Lobietti et al.); timing precision: table
tennis 3.1 ms at contact (Bootsma & van Wieringen 1990), darts 3.4–7.7 ms (Smeets et al.
2002), tapping ~11 ms (Repp), eye-to-hand delay 138 ms in spiking (Sardinha & Bootsma 1993);
NBA free-throw release consistency (McGrath et al. 2025). Spiker variability values are
modelling assumptions anchored to these.
