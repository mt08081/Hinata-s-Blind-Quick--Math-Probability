# Task: Polish and Upgrade "The Blind Quick" Video Pipeline to Perfection

You are working on the programmatic video and physics simulation repository for **"The Blind Quick"**.
Do NOT re-run `analysis.py` (`results.json` and `samples.npz` are already generated and ground-truth).
Your goal is to fix all visual collisions, pacing cutoffs, formatting rounding bugs, and dead rendering code, and implement targeted cinematic upgrades across `engine.py`, `world.py`, `common.py`, `charts.py`, `scenes_a.py`, `scenes_b.py`, `audio.py`, `video.py`, and `assemble.sh`.

---

## 1. Portability & Build Paths (`video.py`, `assemble.sh`)
- **`video.py`**:
  - Replace hardcoded `SEG_DIR = "/home/claude/fq/segs"` with `SEG_DIR = os.path.join( os.path.dirname(os.path.abspath(__file__)), "segs")`.
  - In `__main__`, change the default `still` output fallback from `/tmp/claude-0/...` to `os.path.join(SEG_DIR, f"{sys.argv[2]}_{sys.argv[3]}.png")`.
- **`assemble.sh`**:
  - Replace `cd /home/claude/fq` with `cd "$(dirname "$0")"`.

---

## 2. Engine & Chart Primitives (`engine.py`, `charts.py`, `common.py`)
- **`engine.py` (`slam_text`, line 380)**:
  - Add an optional `alpha=1.0` parameter to `slam_text(fr, s, x, y, t, size=120, color=PAL["ink"], accent=PAL["spiker"], fnt="dblackit", align="center", dur=0.35, alpha=1.0)`.
  - Multiply `al = clamp(t / (dur * 0.5)) * clamp(alpha)` so callers can smoothly fade out slammed text.
- **`charts.py` (`stacked_bar`, line 82)**:
  - Lower the default `label_min=0.06` to `label_min=0.04` so the `4.6%` sweet-spot segment on the first bar in Scene 10 ("Pre-planned set") is labeled rather than left blank.
- **`common.py` (`draw_eye`, line 118)**:
  - Everything in `draw_eye` works for `close` in `[0, 1]`. Ensure that passing `close = 1.0 - ease_io(...)` cleanly animates the eye **opening** from shut to wide open (we will use this in Scene 13/14).

---

## 3. 3D World & Athlete Rig Upgrades (`world.py`, `common.py`)
- **Add Athlete Floor Shadows (`world.py` & `common.py`)**:
  - In `world.py`, add a helper `athlete_shadow(fr, cam, J, alpha=0.42)`:
    - Compute the horizontal ground midpoint `p_ground = np.array([0.5 * (J["hip_l"][0] + J["hip_r"][0]), 0.5 * (J["hip_l"][1] + J["hip_r"][1]), 0.0])` and height above floor `h = max(0.0, 0.5 * (J["an_l"][2] + J["an_r"][2]))`.
    - Project `p_ground` with `cam.project`. If `z > 0.2`, draw an elliptical blurred shadow (`scale(1.0, 0.35)`) with radius `0.32 * cam.px_per_m(z) * (1.0 - 0.25 * clamp(h / 1.0))` and alpha `alpha * clamp(1.0 - h / 1.4)`, similar to `ball_shadow`.
  - In `common.py` (`draw_play`), call `wd.athlete_shadow(fr, cam, Jt, 0.40 * setter_alpha)` and `wd.athlete_shadow(fr, cam, Js, 0.40 * spiker_alpha)` right after `wd.ball_shadow(...)` so both players cast realistic floor shadows that shrink and soften as they jump.
- **Restore Jersey Numbers & Torso Styling (`world.py`, lines 346–385)**:
  - In `draw_athlete`, the `elif kind == "torso":` block (lines 369–384) is currently dead code because the torso is added as `"cap"`.
  - After drawing the `"cap"` torso in `draw_all()` (when `not ghost` and `number is not None`), project the chest midpoint `cen = 0.5 * (sp["_pelvis"] + sp["_chest"])` and render the jersey `number` using `fr.text(number, cen[0], cen[1] + 0.04 * pxm, 0.16 * pxm, "black", "#ffffff", 0.88, "center", stroke=3, stroke_color=ol)`.
- **Dynamic Ball Spin in Flight (`common.py`, line 74)**:
  - In `draw_play`, change `rot=0.0` in `wd.draw_ball(fr, cam, P, glow=ball_glow, ghost=ghost_ball, rot=tp * 2.5)` so the volleyball panels subtly rotate during the pass and spike.

---

## 4. Scene-by-Scene Fixes & Upgrades (`scenes_a.py`)
- **Scene 01 (`01_cold_open`, lines 134–145)**:
  - Fix the abrupt hard cuts on the three post-impact lines (`"He never looks at the ball."`, `"His eyes are closed."`, `"And the ball still finds his palm. Every time."`).
  - Pass `alpha=a` directly into `slam_text(..., alpha=a)` and remove the no-op `fr.rect(0, 0, W, H, "#03050c", (1 - a) * 0.0)`.
- **Scene 05 (`05_ball`, lines 265–279)**:
  - **Bug**: At `s = 2.0–6.0`, the red `drag` arrowhead (`a1 + d * 26`) collides with the `"drag"` text label.
  - **Fix**: In `arrow()`, increase the label offset distance from `d * 60` to `d * 78`, and for the `"drag"` call on line 277, change `offset=(0, -6)` to `offset=(38, 12)` so `"drag / 0.85 N"` sits cleanly below and to the right of the red arrowhead throughout the entire trajectory.
- **Scene 07 (`07_perfect`, lines 377–415)**:
  - **Bug**: The top-left dark panel `fr.rect(50, 125, 1010, 420, ...)` sits directly over the 3D spiker and the pulsing yellow target circle `PLAN.target`, hiding the rendezvous point where the Newton trajectories converge.
  - **Fix**:
    1. Adjust `CAM_PW` on line 346 from `Camera((2.9, -7.6, 4.1), (-0.6, -0.7, 2.2), fov=36)` to `Camera((2.7, -7.4, 3.8), (-1.15, -0.6, 2.05), fov=36)` with `center=(W * 0.60, H * 0.54)` so the spiker and setter sit lower and further right in the frame.
    2. Make the top-left info card more compact: `fr.rect(50, 118, 860, 360, "#060914", 0.82 * a, radius=18)` and tighten the vertical spacing of the 3 Newton guess lines slightly (`315 + 46 * i`) so the pulsing yellow target ring at `PLAN.target` and the spiker's hand are 100% unobstructed in the open court area.

---

## 5. Scene-by-Scene Fixes & Upgrades (`scenes_b.py` & `audio.py`)
- **Scene 09 (`09_window`, lines 145–230)**:
  - **Upgrade "ERROR ALONG THE SWING" (`4.0 <= s < 7.6`)**: In addition to scaling the ghost ball radius (`scale = 1.0 + 0.22 * math.sin(...)`), draw a compact side-profile mini-diagram inside the right column (`X = 1180, y = 700`) showing the palm sweeping through the ball plane at `15.8 m/s` with two ghost balls (`-5 cm` early / `+5 cm` late along the swing path) so the viewer visually understands *why* depth errors along the swing are forgiven.
  - **Fix "ERROR ACROSS THE SWING" Collision (`7.6 <= s < 11.0`, line 172)**: Reduce the sideways ghost-ball excursion from `rb * 2.2` to `rb * 1.65` (`bx = cx + rb * 1.65 * ease_io(seg(s, 8.0, 9.0)) * (1 - ease_io(seg(s, 10.2, 11.0)))`). At `1.65 * rb`, the ball is completely outside the palm disc (`r_hand`) and fingertips, but its right edge stays at `x ≈ 1120`, leaving a clean `60 px` gap before the right-column text at `X = 1180`.
  - **Fix Timing Ruler Label Margin (line 209)**: Change `fr.text("late (ms)", cx + 20 * msk + 52, ry + 50, ...)` to `fr.text("late (ms)", cx + 20 * msk + 18, ry + 50, 24, "semi", PAL["ink2"], b, "left")` so it doesn't crowd the right-hand card (`X - 20 = 1160`).
- **Scene 10 (`10_montecarlo`, lines 318–389)**:
  - **Bug**: Phase 1 (`closed`, "SETTER READS THE APPROACH") runs `t0 = 14.0` to `t1 = 24.0`, with the Kalman panel taking `6.0 s` (`14.0` to `20.0`) and `dur_rain = 3.0` (`20.0` to `23.0`). That leaves only `0.6 s` before the fade-out starts at `23.6`, cutting off the converged `4,000 attempts shown` state and the bottom summary line (`palm contact at all: 19% · sweet spot: 1 in 14`).
  - **Fix**:
    1. Change the Kalman panel duration in `kalman_panel` from `5.0 s` / `6.4 s` to `4.5 s` (`u = clamp((s - s0) / 4.2)`), and set `rain_start = t0 + 4.8` (`18.8 s`) with `dur_rain = 2.8` (finishing at `21.6 s`).
    2. That gives a full `2.4 seconds` (`21.6 s` to `24.0 s`) for the viewer to read the converged `7.2%` sweet-spot bar and the yellow summary line (`palm contact at all: 19% · sweet spot: 1 in 14`) without changing the total `40.0 s` duration of `10_montecarlo` or desyncing downstream scenes!
- **Scene 12 (`12_requirements`, line 476)**:
  - **Bug**: In the 9×9 heatmap, `"%.0f" % (100 * v)` rounds `0.9968` and `0.9970` up to `100`, making three cells display `100`.
  - **Fix**: Format cell values as `"100" if v >= 0.9995 else ("%.1f" % (100 * v) if v >= 0.99 else "%.0f" % (100 * v))` so `(0, 0)` reads `100` and the two adjacent green cells `(0.15×, 0×)` and `(0×, 0.2×)` accurately read `99.7` (matching Figure 6 of the paper).
- **Scene 13 (`13_levers`, lines 505–582)**:
  - **Part 1 ("1. Attack closer to the setter")**: Add the third series from Figure 7 of the paper—`p_teleperf = [mc(f"dist_teleperf_{d['contact_x']}")["clean"] for d in di]`—plotted in `PAL["good"]` (`label="mind reader + robot"`), and change `ylim` from `(0.0, 0.6)` to `(0.0, 0.8)` with `yticks=[0, 0.2, 0.4, 0.6, 0.8]`.
  - **Part 2 ("2. Slow the set down")**: In the right-hand card (`"the catch"`, `X = 1160`), add a third bullet point highlighting the key finding from Section 12.2 of the paper:
    - `"And with human setter hands, release errors grow with flight time — so the sweet-spot rate barely moves (12.6% → 14.1% → 12.9%)."`
  - **Part 3 ("3. Open your eyes.", `s >= 20.4`)**: Add a slanted anime cut-in panel on the top-right (`slanted_panel`) using `draw_eye(..., close=1.0 - ease_io(seg(s, 21.0, 21.8)))` so the spiker's eye **snaps open** right as `"3. Open your eyes."` slams onto the screen!
- **Scene 14 (`14_verdict`, lines 588–642)**:
  - **Bring the 3D World Full Circle**: In the second half of `14_verdict` (`s >= 16.6`, `"Trust is beautiful. Feedback is better."`), render a subtle, low-opacity (`alpha = 0.22 * a * (1 - seg(s, 28.6, 30.0))`) slow-orbiting 3D camera around the contact moment (`tp = T_HIT`, `cam_orbit(PLAN.target, 5.2, -55 + (s - 16.6) * 4, 12, fov=36)`) behind the text and credits card so the video closes with the 3D athletes frozen at the apex of the spike.

---

## 6. Verification & Final Render
1. Render diagnostic stills for every modified beat using `python3 video.py still <scene> <t>`:
   - `01_cold_open` at `t = 10.4` and `11.8` (verify smooth text fade-out)
   - `05_ball` at `t = 2.6` (verify `drag` label is clear of the red arrowhead)
   - `07_perfect` at `t = 7.5` and `11.0` (verify the 3D spiker and pulsing target ring are unobstructed by the top-left card)
   - `09_window` at `t = 5.5`, `9.0`, and `18.0` (verify no ghost-ball/text collision and clean ruler margins)
   - `10_montecarlo` at `t = 22.8` and `35.0` (verify `closed` summary holds cleanly and `4.6%` appears on the first stacked bar)
   - `12_requirements` at `t = 29.0` (verify `100` vs `99.7` in the green heatmap cells)
   - `13_levers` at `t = 6.5`, `16.0`, and `23.5` (verify 3 curves, human-hands note, and eye-opening cut-in)
   - `14_verdict` at `t = 22.0` (verify slow-orbiting 3D background behind the closing text)
2. Inspect each still image to confirm zero text overlaps or clipping.
3. Run `python3 audio.py`, render all modified scenes via `python3 video.py render ...`, and run `bash assemble.sh` to produce the final `The_Blind_Quick.mp4`.

## 7. Synchronize the Markdown Paper (`The Blind Quick The Physics and Probability of an Eyes-Closed Spike.md`) with the Video & `results.json`

1. **Replace raw escaped underscores (`\_`) with clean subscripts** throughout `The Blind Quick The Physics and Probability of an Eyes-Closed Spike.md`:
   - Replace `C\_D` with `C<sub>D</sub>` (or `$C_D$` if the renderer supports inline math) and `C\_L` with `C<sub>L</sub>` in Sections 3.1, 3.3, and 3.4.
   - Replace `F\_D` with `F<sub>D</sub>` (Section 3.3) and `F\_L` with `F<sub>L</sub>` (Section 3.4).
   - Replace `v\_z` with `v<sub>z</sub>` (Section 4.1), `r\_h` with `r<sub>h</sub>` (Section 7.1), and `t\_contact` with `t<sub>contact</sub>` (Appendix B.2).
2. **Clarify Palm vs. Ball-Centre Contact Height (Section 4.3 table)**:
   - Change `| Contact height (palm) | 2.96 m |` to `| Contact height (palm) | 2.96 m (ball centre 2.94 m) |` so it is immediately obvious why Section 2 lists `C = (−2.00, −0.45, 2.94)` while the palm centre is at `2.96 m` (due to the downward component of the palm normal `n_z = −0.273`).
3. **Harmonize Drag Percentage Between Video Scene 05 and Paper Section 3.3**:
   - In `scenes_a.py` (`s05`, line 289), compute the card's headline percentage from `R["plan"]["drag_force_release"] / wN` (`35% of the ball's weight at release`) instead of the time-varying `dN / wN` (`31% -> 28%`), so the video card and Section 3.3 of the paper quote the exact same `35%` number (while the live arrow on the ball continues to show the instantaneous drag force decaying from `0.85 N` to `0.74 N` in flight).
4. **Align the `0.34 s (our set)` Row in Section 12.2 Table**:
   - In Section 12.2 of the Markdown file, update the second row (`0.34 s (our set)`) from `| 0.34 s (our set) | 10.0 m/s | 8.3 m/s | ±6.0 ms | 47 ms before | 33.0% | 12.6% |` to `| 0.34 s (our set) | 10.0 m/s | 8.4 m/s | ±6.0 ms | 48 ms before | 33.0% | 12.4% |` so it matches the 100,000-trial main run quoted in the Abstract, Section 5.4, Section 7.2, and Section 9.3.