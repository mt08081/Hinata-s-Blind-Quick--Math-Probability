# The Blind Quick: The Physics and Probability of an Eyes-Closed Spike

Oct 12, 2026&#32;

## Abstract

An eyes-closed spike only works if the setter lands a 21 cm ball on a hand that cannot see it and is moving at 57 km/h. Using standard physics and measured human variability, we find it hits the palm's sweet spot about 1 time in 22 with a realistic setter, and only about 1 time in 3 even with a mind-reading, robot-precise setter.

We model the ball as a projectile pushed by gravity, air drag and spin. We model the spiker as a projectile too, with an arm made of three linked rods. Everything that changes from one attempt to the next (where and when he takes off, how hard he jumps, how he swings, how the setter releases) is drawn at random, with sizes taken from sports-science studies, and we simulate 100,000 attempts per scenario.

The deciding quantity is time. The ball crosses the palm sideways at 8.4 m/s, so each millisecond of mistiming moves the contact point 8.4 mm, and the palm's 5 cm sweet spot allows only about ±6 ms. For 99% success, the blind swing would need ±2 ms timing (top table-tennis players manage 3 ms with their eyes open), and the setter would need about 4.6 times the precision of a highly consistent NBA free-throw shooter.

## 1. Introduction

In *Haikyuu!!*, a spiker and a setter perform the "freak quick". The spiker sprints in, jumps, closes his eyes and swings at the spot where he trusts the ball will be. The setter sends the ball to exactly that spot, and it meets the palm.

In real volleyball terms this is a **minus-tempo attack**: the hitter leaves the floor before the setter has released the ball. Our model confirms it: in the perfect version, the spiker takes off 48 ms (milliseconds, thousandths of a second) before the ball leaves the setter's hands.

**The question.** If the spiker cannot see the ball and cannot adjust once he is in the air, how often will the ball arrive at the right place at the right moment? And what would it take to make it work every time?

**The approach, in four steps:**

1. Write down the physics of the ball and of the jumping body (Sections 3 and 4).
2. Solve the perfect world, where nothing ever varies (Section 5).
3. Add realistic human variation, sized from sports-science measurements (Sections 6 to 8).
4. Simulate 100,000 attempts per scenario, count the hits, and work backwards to what 99% success would need (Sections 9 to 12).

**How to read this paper.** Each section opens with its main result. Every equation sits in its own box, followed by what it means in words and a worked example with real numbers, so you can skip the boxes and still follow the argument. Speeds are in metres per second (1 m/s = 3.6 km/h).

| Term | What it means here |
| --- | --- |
| Projectile | Anything flying freely after launch. Its path is fixed the moment it leaves the hand or the floor. |
| Drag | Air pushing back against a moving ball, slowing it down. |
| Magnus effect | A spinning ball is pushed sideways by the air, which curves its path. |
| Standard deviation (SD, written ±) | The typical size of a random variation. About 2 attempts in 3 land within ±1 SD of the average, and 19 in 20 within ±2 SD. |
| Monte Carlo simulation | Rolling virtual dice for every uncertain quantity, running the physics, and repeating many times to count how often each outcome happens. |
| Kalman filter | A standard method for turning a series of noisy observations into a best estimate, with an honest error bar. |
| Visuomotor delay | The time between the eyes seeing something and the hands responding to it, about 0.14 s in volleyball. |
| Minus tempo | A quick attack where the hitter is already airborne when the setter releases the ball. |

## 2. Ground rules: the model's universe

We fix one geometry, one clock and eight simplifying rules, so that the only things left to study are the physics and the human variation.

**Coordinates.** The origin is on the floor, directly under the middle of the net. The x axis runs along the net (the setter stands at positive x, the attack goes toward negative x). The y axis points toward the net: our court is negative y and the net is the plane y = 0. The z axis points up. All lengths are in metres.

**Clock.** Time t = 0 is the instant the ball leaves the setter's hands. Negative times are before the release.

| Point | Coordinates (x, y, z), m | What it is |
| --- | --- | --- |
| Release point R₀ | (1.00, −0.70, 2.35) | The setter's hands as the ball leaves them (a jump set) |
| Contact point C | (−2.00, −0.45, 2.94) | Where the ball's centre should be when it meets the palm |
| Take-off spot | (−2.26, −1.31, 0) | Where the spiker's feet leave the floor (worked out in Section 5) |

The ball must travel 3.01 m horizontally and rise 0.59 m. The contact height of 2.94 m is not chosen freely: it is the spiker's reach at the top of his jump (Section 4).

&#91;embedded content: Figure 1 · drawn to scale from the model's coordinates (Section 2 table)\]

The setter's hands (right) send the ball 3 m along the net to the contact point (left). The spiker runs in from behind, takes off 1.3 m from the net and drifts toward it as he rises.

**The eight rules.**

1. **Perfect pass.** Every repetition starts identically: the ball reaches the setter at the same place and time.
2. **Setter planted.** The setter releases from the same spot every time, hands 2.35 m up. Release noise is added in Section 6.
3. **Regulation ball.** Mass 270 g and radius 10.5 cm (circumference 66 cm). The official rules allow 260 to 280 g and 65 to 67 cm ([FIVB Rules 2025–2028, rule 3.1](https://www.fivb.com/wp-content/uploads/2025/01/FIVB-Volleyball_Rules2025_2028-EN-v05.pdf)). The ball never deforms in flight.
4. **Still air at sea level.** Air density 1.2 kg/m³, no wind.
5. **Empty court.** No blockers, no teammates. The court is 9 × 9 m per side and the net top sits at 2.43 m, the men's height (rules 1.1 and 2.1.1).
6. **He always jumps and always swings,** unconditionally.
7. **No peeking.** After take-off the spiker makes no corrections. His swing is a pre-programmed movement timed to his own jump.
8. **Simplified bodies.** A right-handed spiker whose hitting arm is three rigid links swinging in one plane. The hand is a flat disc of radius 8.5 cm with a sweet spot of radius 5 cm.

## 3. The ball in flight

Three forces act on the set ball: gravity, air drag and, if it spins, the Magnus force. At set speed, drag is about a third of the ball's weight, enough that a setter aiming with the textbook no-air formula would miss by 16 cm.

### 3.1 The equation of motion

Newton's second law says mass × acceleration = the sum of the forces. For the ball:

```latex
m\,\frac{d\vec v}{dt} \;=\; m\,\vec g \;-\; \tfrac12\,\rho\, C_D\, A\,|\vec v|\,\vec v \;+\; \tfrac12\,\rho\, C_L\, A\,|\vec v|^2\,(\hat\omega \times \hat v)
```

In words: gravity pulls straight down; drag pushes straight back against the motion and grows with the square of the speed; the Magnus force pushes at right angles to the motion, in a direction set by the spin axis.

| Symbol | Meaning | Value |
| --- | --- | --- |
| m | Ball mass | 0.270 kg |
| g | Gravity | 9.81 m/s², downward |
| ρ | Air density | 1.2 kg/m³ |
| A | Frontal area of the ball, πR² with R = 0.105 m | 0.0346 m² |
| C\_D | Drag coefficient | 0.45 (Section 3.3) |
| C\_L | Lift (Magnus) coefficient | depends on spin (Section 3.4) |
| ω̂, v̂ | Directions of the spin axis and of the motion | unit vectors |

### 3.2 Gravity

The ball weighs m × g = 0.270 × 9.81 = 2.65 N. With gravity alone, the ball follows the textbook parabola from release point R₀ with launch velocity v₀:

```latex
\vec r(t) = \vec R_0 + \vec v_0\, t + \tfrac12\, \vec g\, t^2
```

### 3.3 Drag

Worked example for a set at 10 m/s:

```latex
F_D = \tfrac12\,\rho\, C_D\, A\, v^2 = \tfrac12 \times 1.2 \times 0.45 \times 0.0346 \times 10^2 \approx 0.94\ \text{N}
```

That is 35% of the ball's weight, slowing it at 3.5 m/s². Over the flight, the ball's horizontal speed falls 10%, from 9.37 to 8.42 m/s.

**Why C\_D = 0.45.** How air flows around a ball depends on the Reynolds number, Re = ρ v D / μ, where D = 0.21 m is the diameter and μ = 1.81 × 10⁻⁵ Pa·s is air's viscosity. A 10 m/s set has Re ≈ 1.4 × 10⁵.

Wind-tunnel tests of match volleyballs find a "drag crisis", where C\_D suddenly drops to about 0.12–0.20, at Re ≈ 2.0–3.3 × 10⁵, about 14 m/s ([Asai et al. 2010](https://lida.sport-iat.de/ta/Record/4019290?lng=en); [Hong et al. 2018](https://commons.nmu.edu/isbs/vol36/iss1/212)). That regime governs fast serves and spikes, not sets.

Below the crisis a sphere's drag coefficient is roughly constant at about 0.47 ([sphere drag reference](https://arc.id.au/CannonballDrag.html)); we use 0.45. The exact value barely matters: any C\_D from 0.40 to 0.50 changes the required set speed by only ±0.6%, and a practised setter adapts to the real air anyway.

### 3.4 Spin: the Magnus force

```latex
F_L = \tfrac12\,\rho\, C_L\, A\, v^2, \qquad C_L \approx 0.9\, S, \qquad S = \frac{R\,\omega}{v}
```

The spin parameter S compares the speed of the ball's spinning surface (Rω) with its flight speed v. Worked example: a set spinning once per second has ω = 2π = 6.28 rad/s, so S = 0.105 × 6.28 / 10 = 0.066, C\_L = 0.059 and F\_L = 0.12 N.

That push, at right angles to the flight, accelerates the ball at 0.46 m/s², shifting it about ½ × 0.46 × 0.34² ≈ 2.6 cm over the flight; the full simulation gives 2.4 cm. The factor 0.9 is our cautious choice: baseball measurements fit C\_L = 1.5 S at low spin ([Meyer & Bohn 2008](https://arxiv.org/pdf/0712.0380), citing Sawicki et al. 2003), which would raise the shift to 3.9 cm.

The perfect set carries no deliberate spin. Accidental spin enters as part of the setter's release noise (Section 6).

### 3.5 Solving the equation

With drag included there is no exact formula for the path, so the computer steps forward in time. Starting at the release point, it works out the three forces, updates the velocity and the position, and repeats every 2 ms.

We use the fourth-order Runge–Kutta method (RK4), which samples the forces four times within each step. Shrinking the step from 17 ms to 0.13 ms moves the end point by less than a nanometre, so the stepping adds no meaningful error.

### 3.6 What ignoring the air would cost

Without air, the launch velocity that reaches point C after flight time T has an exact formula:

```latex
\vec v_0 = \frac{\vec C - \vec R_0}{T} - \tfrac12\, \vec g\, T
```

Worked example: C − R₀ = (−3.00, 0.25, 0.59) m and T = 0.34 s give v₀ = (−8.84, 0.74, 3.39) m/s, which is 9.49 m/s at 20.9° above horizontal.

Flown through real air, that set arrives 15 cm short and 4 cm low: a 16 cm miss, about one and a half ball radii. The correct, drag-aware set is 5% faster, 10.0 m/s at 20.6° (Section 5).

## 4. The spiker

Once his feet leave the floor, the spiker is a projectile: his path is fixed at take-off. His palm rides on that path and sweeps through the contact point at 15.8 m/s (57 km/h), close to what motion-capture studies measure in real spikes.

### 4.1 The jump

The spiker's centre of mass (his balance point, near the navel) follows the same gravity-only equation as Section 3.2, starting from his take-off point and take-off velocity:

```latex
\vec r_{\mathrm{com}}(t) = \vec r_{\mathrm{to}} + \vec v_{\mathrm{to}}\,(t - t_{\mathrm{to}}) + \tfrac12\,\vec g\,(t - t_{\mathrm{to}})^2
```

Air resistance on the body is ignored: at jumping speeds it is under 1% of body weight. Worked example with a vertical take-off speed v\_z = 3.80 m/s:

```latex
h_{\mathrm{rise}} = \frac{v_z^2}{2g} = \frac{3.80^2}{2 \times 9.81} = 0.736\ \text{m}, \qquad t_{\mathrm{peak}} = \frac{v_z}{g} = \frac{3.80}{9.81} = 0.387\ \text{s}
```

His centre of mass rises from 1.12 m at take-off to 1.86 m at the peak. Meanwhile he drifts 0.50 m toward the net at 1.3 m/s.

| Quantity | Our spiker | Measured in elite players | Source |
| --- | --- | --- | --- |
| Vertical take-off speed | 3.80 m/s | 3.47 ± 0.17 m/s | [Hu et al. 2005](https://ojs.ub.uni-konstanz.de/cpa/article/view/776/699) |
| Centre-of-mass rise | 0.74 m | 0.58 ± 0.08 m; 0.64 ± 0.09 m | Hu et al. 2005; [Fuchs et al. 2019](https://iris.unicas.it/bitstream/11580/91401/1/02640414.2019.pdf) |
| Horizontal take-off speed | 1.30 m/s | 1.15 ± 0.36 m/s | Hu et al. 2005 |
| Approach run speed | 3.75 m/s | 3.75 ± 0.38 m/s | Fuchs et al. 2019 |

Our spiker jumps a little higher than the measured averages, deliberately: a strong jumper, as the freak quick demands.

### 4.2 The body and the arm

We size the body for a 1.80 m athlete using standard proportions of height.

| Segment | Length | How it is set |
| --- | --- | --- |
| Upper arm | 0.335 m | 0.186 × height ([Ma et al. 2009](https://arxiv.org/pdf/0901.0825)) |
| Forearm | 0.263 m | 0.146 × height (same source) |
| Hand | 0.194 m | 0.108 × height (Drillis & Contini model, cited in Winter 2005; see [Wisner et al. 2006](https://ojs.ub.uni-konstanz.de/cpa/article/view/292)) |
| Palm centre from the wrist | 0.078 m | 40% along the hand (assumption) |
| Shoulder above centre of mass | 0.47 m | assumption |
| Hitting shoulder to the side | 0.17 m | assumption |

The arm is three rigid rods: upper arm, forearm and hand. The palm's position is the shoulder's position plus the three rods laid end to end:

```latex
\vec p(t) = \vec s(t) + L_1\,\hat e(\theta) + L_2\,\hat e(\theta-\beta) + L_3\,\hat e(\theta-\beta+\gamma), \qquad \hat e(\phi) = \sin\phi\;\hat u + \cos\phi\;\hat z'
```

In words: each rod points along an angle measured from "straight up" inside the swing plane. θ is the upper arm's angle, β how far the elbow is bent, and γ how far the wrist is cocked. û is the swing's forward direction and ẑ′ is "up" within the swing plane, which can lean sideways a few degrees.

Near contact, the angles follow smooth curves shaped like measured spike swings:

- **Shoulder:** passes 18° in front of vertical at contact, rotating at 12.5 rad/s (716°/s).
- **Elbow:** straightens hard in the final 0.1 s, from 86° bent to 8° at contact, peaking at 1,270°/s.
- **Wrist:** snaps forward through contact at 15 rad/s.
- **Trunk:** leans forward 10° at contact and keeps bending at 3.5 rad/s.

### 4.3 Does the model arm behave like a real one?

Yes: every speed at contact falls within about 1.3 standard deviations of the motion-capture averages, and the contact height matches.

| At contact | Our model | Measured (Hu et al. 2005) |
| --- | --- | --- |
| Fingertip speed | 20.1 m/s | 17.3 ± 2.1 m/s |
| Palm speed | 15.8 m/s | not measured (between fingertip and wrist) |
| Wrist speed | 12.9 m/s | 12.1 ± 1.3 m/s |
| Elbow speed | 7.1 m/s | 8.8 ± 1.7 m/s |
| Peak elbow extension rate | 1,270°/s | 1,230 ± 300°/s |
| Shoulder rotation rate | 716°/s | 909 ± 187°/s |
| Contact height (palm) | 2.96 m | 2.90 ± 0.09 m |

A quick sanity check on palm speed: shoulder rotation alone gives 12.5 rad/s × 0.675 m of reach = 8.4 m/s. The trunk bend, elbow straightening and wrist snap add the rest.

### 4.4 The blind swing's clock

Unable to see the ball, the spiker can only time his swing from his own body. We assume a pre-programmed swing that brings the palm to its contact pose at the peak of his jump, plus a random timing error:

```latex
t_{\mathrm{contact}} = t_{\mathrm{to}} + \frac{v_z}{g} + \Delta t_{\mathrm{swing}}
```

This choice favours success. At the peak his height changes slowest, so a timing slip there costs the least height.

## 5. The perfect world: solving the rendezvous

If nothing ever varied, the set would leave at 10.0 m/s, 20.6° above horizontal, and fly for 0.34 s. The spiker would take off 48 ms before the release, and every attempt would hit the sweet spot.

### 5.1 The problem

The setter controls three numbers, the three components of the launch velocity. He must put the ball's centre at point C at the exact moment the palm gets there: two moving objects meeting at one point in space and time, a rendezvous.

```latex
\text{find } \vec v_0 \text{ such that } \vec r_{\mathrm{ball}}(T;\,\vec v_0) = \vec C
```

That is three equations (x, y and z) in three unknowns, for a chosen flight time T. Working backwards from a desired result to the input that produces it is called an inverse problem.

### 5.2 Choosing the flight time

The flight time is a free choice, so we pick the one that makes the ball reach the top of its arc exactly at the palm. At its peak the ball's height changes slowest, so a small timing error costs the least height, the same logic as the spiker swinging at his own peak.

A root-finding search (Brent's method) gives T = 0.3395 s. Without air the ball would peak at C after √(2 × 0.586 / 9.81) = 0.346 s; drag shortens that slightly.

### 5.3 The shooting method

With drag there is no formula to invert, so the computer "shoots":

1. Guess a launch velocity.
2. Fly the ball (Section 3.5) and measure the miss at time T.
3. Correct the guess using how strongly each launch component moves the end point, measured with three slightly nudged test flights.
4. Repeat until the miss is negligible.

Step 3 is Newton's method. J, the Jacobian, is the 3 × 3 table of sensitivities, "how many metres the end point moves per m/s of launch change":

```latex
\vec v_0^{\,(k+1)} = \vec v_0^{\,(k)} - J^{-1}\left(\vec r_{\mathrm{ball}}\big(T;\,\vec v_0^{\,(k)}\big) - \vec C\right), \qquad J_{ij} = \frac{\partial r_i}{\partial v_{0j}}
```

| Attempt | Launch velocity (x, y, z), m/s | Miss at time T |
| --- | --- | --- |
| Guess 1: aim straight at C, no allowance for gravity | (−8.84, 0.74, 1.73) | 59.4 cm |
| After correction 1 | (−9.32, 0.78, 3.51) | 3.9 mm |
| After correction 2 | (−9.33, 0.78, 3.52) | 0.0003 mm |

### 5.4 The perfect set and the spiker's schedule

| Quantity | Value |
| --- | --- |
| Set speed | 10.0 m/s (36 km/h) |
| Angle above horizontal | 20.6° |
| Direction | Almost parallel to the net, angled 4.8° toward it |
| Flight time | 0.34 s |
| Ball at contact | 8.4 m/s, moving horizontally (top of its arc) |
| Palm at contact | 15.8 m/s, swinging toward the net |
| Spiker take-off | t = −0.048 s, at (−2.26, −1.31) m |

The take-off time follows from Section 4.1. Contact happens at t = 0.3395 s, and the spiker needs 0.387 s to rise to his peak, so he must leave the floor at 0.3395 − 0.387 = −0.048 s. He is airborne before the setter releases the ball: a genuine minus tempo.

An independent back-of-envelope estimate of a minus-tempo set, ignoring drag, found 8.5 m/s for a 3 m set ([Sujeevan 2026](https://journals.le.ac.uk/index.php/jist/article/download/5252/5076/21444)). Our faster, flatter set includes drag and a shorter flight, so the two agree in scale.

## 6. Human variability: what changes from one attempt to the next

No two attempts are identical. We model 14 things the spiker does slightly differently every time and 6 for the setter, each sized from sports-science measurements where they exist and from stated assumptions where they do not.

### 6.1 How randomness enters

Every uncertain quantity X is drawn from a bell curve (normal distribution) centred on its perfect-world value μ, with spread σ, the standard deviation:

```latex
X = \mu + \sigma\, Z, \qquad Z \sim \mathcal{N}(0,\,1)
```

Z is a standard random number: usually between −1 and +1, occasionally beyond ±2. All quantities are drawn independently, with one exception: a faster run-up tends to give a higher jump, so approach speed and jump speed share a correlation of 0.5 (an assumption).

### 6.2 The spiker (blind, no corrections in the air)

| Quantity | ± (1 SD) | Where the number comes from |
| --- | --- | --- |
| Take-off spot, along the net | 10 cm | Assumption. Long-jump approaches show step placement scatter of up to 58 cm in novices and much less in trained jumpers who steer their last strides ([Scott et al. 1997](https://shura.shu.ac.uk/3317/)). |
| Take-off spot, toward the net | 10 cm | Same as above. |
| Take-off moment | 20 ms | Assumption, anchored on expert table-tennis players, whose timing varies 17 ms when they start a stroke ([Bootsma et al. 2010](https://antoine-morice.pedaweb.univ-amu.fr/docs/publis/isi/Bootsma_Fernandez_Morice_Montagne_JEPHPP_2010.pdf), reporting Bootsma & van Wieringen 1990). |
| Jump speed (vertical) | 0.11 m/s (3%) | One spiker's jump height varied 6% across trials ([Lobietti et al.](https://ojs.ub.uni-konstanz.de/cpa/article/view/3163/2967)). Height grows with the square of speed, so 6% in height is 3% in speed: ±4.3 cm at the peak. |
| Forward drift speed | 0.15 m/s | Assumption. Between different players it varies 0.36 m/s ([Hu et al. 2005](https://ojs.ub.uni-konstanz.de/cpa/article/view/776/699)); one player varies less. |
| Sideways drift speed | 0.12 m/s | Assumption, as above. |
| Blind swing timing | 12 ms | Professional musicians tapping a steady beat vary about 11 ms; the motor system's timing precision is about 10 ms ([Zhang et al. 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC5834204)). |
| Arm lean (swing-plane tilt) | 3° | Assumption. |
| Swing direction | 4° | Assumption. |
| Body turn | 3° | Assumption. |
| Trunk lean | 3° | Assumption. |
| Elbow bend at contact | 4° | Assumption. |
| Wrist angle at contact | 5° | Assumption. |
| Shoulder speed | 1.0 rad/s (8%) | Assumption; measured between-player spread is about 20% (Hu et al. 2005). |

No published study reports trial-to-trial spreads for the arm and body angles, so we chose small values. That favours the freak quick, and Section 11 shows what happens when every spread is shrunk further.

### 6.3 The setter's release

We borrow the best-measured precise release in sport, the basketball free throw, and expert dart throwing for timing.

| Quantity | ± (1 SD) | Where the number comes from |
| --- | --- | --- |
| Launch angle, up and down | 1.1° | A highly consistent NBA shooter in a 2025 study ("Player B"): 1.11° (league average 2.99°) ([McGrath et al. 2025](https://arxiv.org/pdf/2512.08824)). |
| Launch angle, left and right | 1.1° | Assumed equal to up and down. |
| Launch speed | 1.6% | Same shooter: 0.24 mph at 14.7 mph (league average 2.2%) (McGrath et al. 2025). |
| Release moment | 5 ms | Expert dart throwers: 3.4–7.7 ms ([Smeets et al. 2002](https://personal.fbw.vu.nl/~jsmeets/2002/Darts_timing-EBR02.pdf)). |
| Release point, per direction | 1.5 cm | Dart throwers' hand position at release: 1.3–3.3 cm (Smeets et al. 2002). |
| Accidental spin, per axis | 1 revolution/s | Assumption for a set meant to carry no spin. |

A top volleyball setter may be better or worse than a free-throw shooter. Section 11 treats the setter's precision as a dial and finds out how far it must be turned.

### 6.4 Two simulated attempts

Two attempts drawn from the simulation, each also carrying the setter's random release errors, show how the random inputs combine:

| Difference from the plan | Attempt A | Attempt B |
| --- | --- | --- |
| Take-off spot along the net | 7 cm toward the setter | 20 cm away from the setter |
| Take-off moment | 10.5 ms late | 20.2 ms late |
| Jump speed | 0.08 m/s weaker | 0.01 m/s stronger |
| Blind swing timing | 6.3 ms late | 19.3 ms late |
| Arm lean | 4.2° less | 6.8° more |
| Outcome | Sweet spot: ball 0.8 cm across and 4 cm up the hand from the palm centre | Whiff: the ball had already passed 33 cm beyond the hand |

In attempt A the errors happened to cancel. In attempt B the late take-off and the late swing added up.

## 7. When does a blind swing connect?

The ball crosses the palm sideways at 8.4 m/s, so each millisecond of mistiming moves the contact point 8.4 mm. The 5 cm sweet spot therefore tolerates only ±6 ms of timing error, and touching the palm at all only ±10 ms.

### 7.1 Contact geometry

The hand is a flat disc of radius r\_h = 8.5 cm and the ball is a sphere of radius R = 10.5 cm. Measure the ball's centre from the palm's centre: h is how far it sits in front of the palm, and ρ how far it sits off to the side within the palm's plane. The shortest distance from the ball's centre to the disc is:

```latex
d = \sqrt{h^2 + \max(\rho - r_h,\;0)^2}
```

They touch when d ≤ R. Each attempt is graded by where the ball first touches:

| Outcome | Rule | What it means |
| --- | --- | --- |
| Sweet spot | Touches the palm's face, ρ ≤ 5 cm | A clean, powerful spike |
| On the palm | Touches the face, 5 cm < ρ ≤ 8.5 cm | A real spike, less controlled |
| Fingertips or edge | Touches only the rim of the disc | A tip or a mishit |
| Whiff | No touch at all | The ball goes past |

The computer scans each attempt in 1 ms steps around the planned contact, then pins down the first touch to under a microsecond by repeatedly halving the interval (bisection).

### 7.2 Along the swing is forgiving; across it is fatal

**Along the swing.** The palm drives through the ball's plane at 15.8 m/s. If the ball sits a few centimetres nearer or farther along that direction, the palm simply meets it a few milliseconds earlier or later.

**Across the swing.** Within the palm's plane nothing sweeps to the rescue. The ball moves across the palm at 8.36 m/s (the part of its velocity lying in that plane), so a timing error Δt becomes a sideways miss:

```latex
\Delta s = v_{\parallel}\,\Delta t = 8.36\ \tfrac{\text{m}}{\text{s}} \times \Delta t \quad\Rightarrow\quad 1\ \text{ms} \;\to\; 8.4\ \text{mm}
```

### 7.3 The timing window

A simple estimate divides each target's radius by that speed: 5.0 cm ÷ 8.36 m/s = 6.0 ms for the sweet spot. The full simulation, which moves the swing time in 0.25 ms steps, agrees:

| Contact grade | Simple estimate | Full simulation |
| --- | --- | --- |
| Sweet spot | ±6.0 ms | ±6.0 ms |
| On the palm | ±10.2 ms | ±10.3 ms |
| Any touch | ±22.7 ms | 32 ms early to 17.5 ms late |

The "any touch" window is lopsided: a hand that arrives early can still be clipped edge-on by the incoming ball, while a late hand finds it already gone.

&#91;embedded content: Figure 2 · model output: swing timing swept in 2 ms steps around the perfect-world attempt\]

Each dot is one blind swing, early (left) or late (right), with everything else perfect. Only the seven swings between −6 and +6 ms reach the sweet spot.

Height errors are far more forgiving. Shifting only the contact height, the sweet spot allows ±5.5 cm and the palm ±9.3 cm, comfortably more than the jump's own ±4.3 cm spread.

### 7.4 Four ways to miss

| Miss | What went wrong | Share of whiffs, pre-planned set |
| --- | --- | --- |
| Passed by | Hand late, or set too fast | 55% |
| Fell short | Hand early, or set too slow | 35% |
| Over the fingers | Ball too high, or jump too low | 5% |
| Under the palm | Ball too low, or jump too high | 5% |

Nine whiffs in ten are sideways misses: timing, not height, is what fails.

## 8. What the setter can know

The setter must commit to the set 92 ms before the spiker even leaves the floor. Watching the run-up can pin down where the spiker will jump to about ±3 cm, but it says almost nothing about how hard he will jump and nothing about when he will swing.

### 8.1 The eye-to-hand delay

What the eyes see takes time to reach the hands: 138 ± 33 ms in volleyball spiking (Sardinha & Bootsma 1993, reported in [Bootsma et al. 2010](https://antoine-morice.pedaweb.univ-amu.fr/docs/publis/isi/Bootsma_Fernandez_Morice_Montagne_JEPHPP_2010.pdf)). We use 0.14 s.

The ball leaves at t = 0, so the setter's last useful look is at t = −0.14 s. The spiker takes off at t = −0.048 s, so the setter commits 0.092 s before the take-off he is trying to match.

### 8.2 Three levels of knowledge

1. **Pre-planned set.** The setter sends the perfect-world set every time and ignores the spiker.
2. **Reads the approach.** The setter watches the run-up, estimates the take-off with a Kalman filter (Section 8.3), and re-solves the rendezvous of Section 5 for the predicted contact point and time.
3. **Mind reader.** The setter magically knows the exact take-off: spot, moment, drift and jump speed. Even he cannot know the swing, which happens after the ball is gone.

| What the setter knows | Pre-planned | Reads the approach | Mind reader |
| --- | --- | --- | --- |
| Take-off spot | ±10 cm (nothing) | ±3.1 cm | Exact |
| Take-off moment | ±20 ms | ±10 ms | Exact |
| Drift speed | ±0.12–0.15 m/s | ±0.14 m/s | Exact |
| Jump speed | ±0.110 m/s | ±0.098 m/s | Exact |
| Swing timing and arm angles | Unknown | Unknown | Unknown |

### 8.3 How the reading setter estimates the take-off

**The run-up model.** Along each horizontal direction, the spiker's deviation w from his planned path wanders like a weight on a spring that keeps getting random kicks:

```latex
\ddot w = -k\,w - c\,\dot w + s\,\xi(t)
```

The spring (k) pulls him back toward his plan, the damper (c) stops him overshooting, and ξ(t) is a stream of random kicks of strength s. We set k = 2.25 s⁻², c = 3.0 s⁻¹ and s = 0.37 so that the wandering settles at ±10 cm and ±0.15 m/s, matching Section 6.

**The observations.** The setter glances at the spiker 20 times a second, each glance judging his position to ±5 cm (an assumption).

**The Kalman filter** alternates two steps. *Predict:* move the estimate forward in time, letting its uncertainty grow. *Update:* blend in the new glance, trusting it in proportion to how uncertain the prediction had become:

```latex
K = \frac{P^-}{P^- + \sigma_{\mathrm{obs}}^2}, \qquad \hat w^+ = \hat w^- + K\,(z - \hat w^-), \qquad P^+ = (1-K)\,P^-
```

Here P is the uncertainty squared, z the new glance and K the trust given to it. This is the one-direction version; the real filter tracks position and speed together using 2 × 2 tables.

Worked example for the first glance: the prior uncertainty is 10 cm (P⁻ = 100 cm²) and the glance is good to 5 cm (25 cm²). Then K = 100 / 125 = 0.8, so the glance gets 80% of the weight, and the uncertainty drops to √(0.2 × 100) = 4.5 cm.

After 20 glances, projected 0.09 s ahead to the take-off, the uncertainty is ±3.1 cm. Simulating 20,000 random run-ups and running the filter on each confirms it: ±3.08 cm. Velocity barely improves (±0.14 m/s) because 0.09 s of unseen running undoes most of what was learned.

**Take-off moment.** The setter also sees the plant step, which we assume he times to ±12 ms. Combining independent estimates follows the rule for adding information:

```latex
\frac{1}{\sigma_{\mathrm{post}}^2} = \frac{1}{\sigma_{\mathrm{prior}}^2} + \frac{1}{\sigma_{\mathrm{obs}}^2} \quad\Rightarrow\quad \sigma_{\mathrm{post}} = \left(\frac{1}{20^2} + \frac{1}{12^2}\right)^{-1/2} = 10.3\ \text{ms}
```

**Jump speed.** The only clue is the run-up speed, which correlates 0.5 with jump speed (Section 6.1). Seen to ±0.05 m/s, it trims the jump-speed uncertainty from 0.110 to just 0.098 m/s.

## 9. Monte Carlo experiments: 100,000 attempts per scenario

With a realistic setter, the blind spike hits the sweet spot 4.6% of the time (1 in 22) and touches the palm at all 12% of the time. A setter who knows the take-off exactly and releases with zero error still reaches only 33%.

### 9.1 One simulated attempt, step by step

1. Draw the spiker's 14 random inputs (Section 6.2).
2. Form the setter's belief about the take-off (Section 8) and solve for the set he intends (Section 5).
3. Add the setter's random release errors (Section 6.3).
4. Fly the ball through the air (Section 3).
5. Move the spiker's body and arm (Section 4).
6. Find the first touch between ball and palm, and grade it (Section 7).

Repeating this 100,000 times per scenario and counting each outcome estimates its probability. This is the Monte Carlo method, named after the casino because it runs on random numbers.

### 9.2 How precise are the estimates?

A probability p estimated from N independent attempts carries a standard error of:

```latex
\mathrm{SE} = \sqrt{\frac{p\,(1-p)}{N}}
```

Worked example: p = 0.046 and N = 100,000 give SE = 0.0007, or 0.07 percentage points. So "4.6%" really means somewhere between 4.5% and 4.7%. Every main result below is pinned down to within ±0.3 percentage points.

### 9.3 Results

We ran six scenarios: the three setter knowledge levels of Section 8, each with human release precision ("human hands", Section 6.3) and with zero release error ("perfect hands"). The spiker is the same blind, uncorrecting spiker throughout.

&#91;embedded content: Figure 3 · Monte Carlo results, 100,000 attempts per scenario (results.json, main runs)\]

Three things stand out:

- **Reading the approach helps less than you might hope:** 4.6% to 7.2%. The setter learns where the spiker jumps, but not how hard or when he swings.
- **Perfect hands matter most once the setter knows the take-off:** 12.4% to 33.0% for the mind reader.
- **A hard ceiling remains.** Even with everything the setter could control made perfect, the spiker's own ±12 ms swing timing and arm variation cap the sweet spot at one attempt in three.

Where do the whiffs go? With the pre-planned set, 55% pass by (hand late), 35% fall short (hand early) and only 10% go over or under the hand.

## 10. What breaks it: the error budget

The spiker's own timing is the main enemy. His take-off moment alone pushes the ball 18 cm off the palm centre, and his errors combined outweigh the setter's by more than three to one: 26 cm against 8 cm.

### 10.1 Method

For each error source we nudge it by a tiny amount, re-run one perfect-world attempt, and measure how far the ball's meeting point moves on the hand. That rate, multiplied by the source's standard deviation from Section 6, gives its typical contribution in centimetres.

Independent errors partly cancel, so they combine like the sides of a right-angled triangle rather than adding straight up:

```latex
\sigma_{\mathrm{total}} = \sqrt{\sigma_1^2 + \sigma_2^2 + \sigma_3^2 + \cdots}
```

### 10.2 Results (pre-planned set)

&#91;embedded content: Figure 4 · linear sensitivity × standard deviation for each source (results.json, sensitivity)\]

The remaining eight sources each contribute under 2.3 cm. Shoulder speed contributes nothing: it changes how fast the hand sweeps through contact, not where the hand is at the planned instant.

**Worked examples.**

- **Take-off moment.** Leaving the floor 1 ms late makes everything happen 1 ms late, peak and swing included, so the ball has travelled 8.9 mm further across the palm. At ±20 ms that is ±17.7 cm.
- **Jump speed.** A jump 0.11 m/s stronger peaks 0.11 / 9.81 = 11 ms later and 4.3 cm higher. The delay alone moves the ball 9.2 cm across the palm, and the extra height 5.4 cm along it.
- **Take-off spot.** Taking off 10 cm further along the net moves the hand 10 cm along the ball's path, which is the same thing as being early or late.

### 10.3 The whole budget in one number

All sources together give a typical sideways miss of 27.3 cm: 26.2 cm from the spiker and 7.6 cm from the setter. The full simulation, which needs no straight-line approximation, measures 25.3 cm, confirming the budget.

Divide by 8.4 mm per ms and the blind spike carries about 33 ms of effective timing scatter. The sweet spot allows ±6 ms. That mismatch, more than five to one, is the whole story of this paper in one line.

## 11. Working backwards: what would 99% take?

For 99% sweet-spot hits, the spiker's in-air variability must shrink about six-fold, timing his blind swing to ±2 ms, and the setter's release noise about 4.6-fold, holding his launch angle to ±0.24°. Both lie beyond the human precision measured so far, and the spiker would need his with his eyes closed.

### 11.1 Method: turn a dial

We multiply every one of a player's standard deviations by the same factor k. At k = 1 he has the human values of Section 6; at k = 0 he is a perfect robot. For each k we rerun 20,000 attempts and look for the k where the sweet-spot rate reaches 99%.

To isolate each player, the other one is made perfect. When we test the spiker, the setter is a mind reader with perfect hands. When we test the setter, the spiker repeats himself exactly.

&#91;embedded content: Figure 5 · 20,000 attempts per point; crossings found by straight-line interpolation (results.json, hitterk and setterk runs)\]

### 11.2 What the spiker would need

The spiker reaches 99% at k = 0.165, about 6 times steadier than a human. Because the mind-reading setter absorbs every take-off error, what remains is the swing itself: its timing must hold to ±2.0 ms, and every arm and body angle to about ±0.5–0.8°.

A quick check with pencil and paper. The swing's own errors move the ball 11.0 cm across the palm, worth 13.2 ms at 8.4 mm per ms. To keep 99% of attempts inside ±6.0 ms, a bell curve's spread may be at most 6.0 / 2.58 = 2.3 ms, because 99% of a bell curve lies within 2.58 standard deviations of its centre. So k ≈ 2.3 / 13.2 = 0.18, close to the simulation's 0.165.

| Timing precision (1 SD) | Value | Can they see? |
| --- | --- | --- |
| Professional musicians tapping a beat ([Zhang et al. 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC5834204)) | 11 ms | Hearing the beat |
| Expert dart throwers releasing the dart ([Smeets et al. 2002](https://personal.fbw.vu.nl/~jsmeets/2002/Darts_timing-EBR02.pdf)) | 3.4–7.7 ms | Yes |
| Expert table-tennis players at ball contact ([Bootsma et al. 2010](https://antoine-morice.pedaweb.univ-amu.fr/docs/publis/isi/Bootsma_Fernandez_Morice_Montagne_JEPHPP_2010.pdf)) | 3.1 ms | Yes, steering the bat with their eyes |
| **Needed for the blind quick** | **2.0 ms** | **No** |

### 11.3 What the setter would need

The setter reaches 99% at k = 0.216, about 4.6 times more precise than our human values.

| Release quantity | Needed for 99% | Best measured humans |
| --- | --- | --- |
| Launch angle | ±0.24° | ±1.1°, a highly consistent NBA free-throw shooter; league average ±3.0° ([McGrath et al. 2025](https://arxiv.org/pdf/2512.08824)) |
| Launch speed | ±0.34% | ±1.6%, same shooter; league average ±2.2% |
| Release moment | ±1.1 ms | ±3.4–7.7 ms, expert dart throwers |
| Release point | ±3 mm | ±13–33 mm, dart throwers' hand position |
| Accidental spin | ±0.2 revolutions/s | not measured |

### 11.4 Both players together

&#91;embedded content: Figure 6 · 10,000 attempts per cell, mind-reading setter (results.json, grid runs)\]

Only three cells reach 99%, all in the corner where one player is a perfect robot and the other is at least five times more consistent than our human values. Even with both players at 0.15–0.2× their human spread, the rate is 96%; with both at human values, the mind-reading setter manages 12%.

## 12. Ways to widen the window

The window is narrow because the ball crosses the palm fast. Shortening the set slows it and helps a lot; slowing the set helps a little but stops it being a minus tempo; letting the spiker see is the real fix, which is why real quick attacks are hit with open eyes.

### 12.1 Attack closer to the setter

At a fixed flight time, the ball's speed across the palm is roughly the set distance divided by the flight time. Halve the distance and the timing window roughly doubles: ±35 ms at 0.6 m, ±18 ms at 1.0 m, ±6 ms at our 3.0 m, and ±4.5 ms at 4.0 m.

&#91;embedded content: Figure 7 · a fresh perfect-world set at each distance, then 20,000 attempts per point (results.json, distance runs)\]

Even a 0.6 m set falls short of 99%, because height and arm-angle errors do not shrink with distance.

### 12.2 Slow the set down

Keeping the 3 m distance but lengthening the flight also slows the ball across the palm. Every row below is a fresh perfect-world solution (Section 5) followed by 20,000 simulated attempts with the mind-reading setter.

| Flight time | Set speed | Ball across the palm | Sweet-spot window | Spiker takes off | Sweet spot, perfect hands | Sweet spot, human hands |
| --- | --- | --- | --- | --- | --- | --- |
| 0.30 s | 11.2 m/s | 9.5 m/s | ±5.3 ms | 87 ms before the release | 30.0% | 11.7% |
| 0.34 s (our set) | 10.0 m/s | 8.3 m/s | ±6.0 ms | 47 ms before | 33.0% | 12.6% |
| 0.40 s | 8.7 m/s | 7.1 m/s | ±7.0 ms | 13 ms after | 37.3% | 13.6% |
| 0.46 s | 7.8 m/s | 6.2 m/s | ±8.0 ms | 73 ms after | 40.4% | 14.1% |
| 0.52 s | 7.2 m/s | 5.6 m/s | ±8.8 ms | 133 ms after | 42.6% | 14.1% |
| 0.60 s | 6.7 m/s | 5.0 m/s | ±9.5 ms | 213 ms after | 44.1% | 13.9% |
| 0.70 s | 6.4 m/s | 4.7 m/s | ±10.0 ms | 313 ms after | 44.2% | 12.9% |

Three catches. First, once the flight exceeds the spiker's 0.387 s rise, he must take off after the release, so the attack is no longer a minus tempo and blockers gain time. Second, longer sets arrive falling, at up to 2.6 m/s. Third, the setter's own errors grow with flight time, so with human hands the gain all but vanishes: the rate only moves from 11.7% to 14.1% at best.

### 12.3 Open the eyes

With vision, players correct while they move. Expert table-tennis players start their strokes with a 17 ms timing spread yet hit the ball with 3 ms ([Bootsma et al. 2010](https://antoine-morice.pedaweb.univ-amu.fr/docs/publis/isi/Bootsma_Fernandez_Morice_Montagne_JEPHPP_2010.pdf), reporting Bootsma & van Wieringen 1990), steering the bat in the final fraction of a second.

The model shows why one fix is not enough. Making only the blind swing's timing perfect lifts the reading setter's sweet-spot rate from 7.2% to just 8.2%, because the take-off and jump errors remain. A spiker who sees the ball corrects when and where his hand goes, all at once.

We did not simulate an eyes-open spiker: that needs a model of visual steering, which is a study of its own.

## 13. Limitations and honest caveats

The physics of the ball and the jump is well established. The headline percentages rest mostly on the spiker's variability, several parts of which are assumptions, so read them as "a few percent", "about a third" and "needs about six times better", not as exact figures.

- **Assumed spreads.** No study we found reports trial-to-trial spreads for a spiker's take-off spot, take-off moment or arm angles. We chose values we consider fair or generous; Section 11 shows how the results move as every spread changes.
- **Independent errors.** We treat every error as unrelated to the others. Skilled athletes show "compensatory variability", where one part of a movement corrects another ([Bootsma et al. 2010](https://antoine-morice.pedaweb.univ-amu.fr/docs/publis/isi/Bootsma_Fernandez_Morice_Montagne_JEPHPP_2010.pdf)). A well-drilled pair could pair a late take-off with a quicker swing, so our rates may be pessimistic.
- **A stick-figure arm.** Three rigid links following prescribed angle curves, not a model of muscles. Its speeds match motion-capture data (Section 4.3), but the swing's shape is simplified.
- **Contact is pure geometry.** No ball squash, no friction, no soft hand. The 5 cm sweet spot is a judgement, not a measurement; a 6 cm sweet spot would widen the window to about ±7 ms.
- **Air.** The drag and spin coefficients are approximations. They change the perfect set by under 1% and matter mainly through accidental spin (Section 3.4).
- **A borrowed setter.** The setter's precision comes from basketball free throws and darts. Setting is a different skill, which is why Section 11 treats it as a dial.
- **One scenario.** One attack position, one release height, one jumper, a perfect pass every time, no blockers, and no learning or fatigue across attempts. Section 12 varies the distance and the tempo.
- **Fiction.** The model uses no statistics from the anime. Its spiker is a strong but human jumper (Section 4.1).

## 14. Conclusion

The blind quick is physically possible but not reliably repeatable by humans. It works on screen because fiction can grant the precision that physics demands.

1. Without variation, the rendezvous has a clean solution: a 10.0 m/s set at 20.6° that peaks at the palm 0.34 s later, with the spiker airborne 48 ms before the release.
2. The deciding quantity is the ball's speed across the palm, 8.4 m/s. It turns each millisecond of mistiming into 8.4 mm and leaves a sweet-spot window of only ±6 ms.
3. Realistic human variation spreads the meeting point by about 25 cm, the equivalent of 33 ms. Sweet-spot success is therefore 4.6% with a realistic setter, and 33% even with a setter who reads minds and never errs.
4. For 99%, the blind swing must be timed to ±2 ms and the setter must be about 4.6 times more precise than a highly consistent NBA free-throw shooter.
5. The bottleneck is the spiker, not the setter. The cure is exactly what the blind quick gives up: watching the ball.

## Appendix A: every parameter and where it comes from

The random spreads are listed with their sources in Sections 6.2 (spiker) and 6.3 (setter). This table holds every other input.

| Group | Parameter | Value | Source or reasoning |
| --- | --- | --- | --- |
| Ball | Mass | 0.270 kg | [FIVB rule 3.1](https://www.fivb.com/wp-content/uploads/2025/01/FIVB-Volleyball_Rules2025_2028-EN-v05.pdf): 260–280 g |
| Ball | Radius | 0.105 m | FIVB rule 3.1: circumference 65–67 cm |
| Air | Density | 1.20 kg/m³ | Standard sea-level air at about 20 °C |
| Air | Viscosity | 1.81 × 10⁻⁵ Pa·s | Standard value at about 20 °C |
| Air | Drag coefficient below the crisis | 0.45 | Sphere value about 0.47 ([sphere drag reference](https://arc.id.au/CannonballDrag.html)); assumption |
| Air | Drag coefficient above the crisis | 0.17 | [Asai et al. 2010](https://lida.sport-iat.de/ta/Record/4019290?lng=en); never reached by sets |
| Air | Drag-crisis speed | 14 m/s | [Fundamental aerodynamics of a new volleyball 2010](https://sponet.de/sponet/Record/4026034?lng=en) |
| Air | Lift coefficient | 0.9 × S, at most 0.35 | Assumption; baseball fit 1.5 × S ([Meyer & Bohn 2008](https://arxiv.org/pdf/0712.0380)) |
| Air | Gravity | 9.81 m/s² | Standard |
| Court | Net height | 2.43 m | FIVB rule 2.1.1, men |
| Court | Court size | 9 × 9 m per side | FIVB rule 1.1 |
| Court | Release point | (1.00, −0.70, 2.35) m | Assumption: a jump set near the net |
| Court | Contact point, horizontal | (−2.00, −0.45) m | Assumption: a quick about 3 m from the setter |
| Spiker | Standing height | 1.80 m | Assumption |
| Spiker | Upper arm, forearm, hand | 0.186, 0.146, 0.108 × height | [Ma et al. 2009](https://arxiv.org/pdf/0901.0825); Drillis & Contini model via [Wisner et al. 2006](https://ojs.ub.uni-konstanz.de/cpa/article/view/292) |
| Spiker | Centre of mass at take-off | 1.12 m | Assumption: body extended, on the toes |
| Spiker | Shoulder offset from centre of mass | 0.47 m up, 0.17 m out | Assumption |
| Spiker | Hand disc; sweet spot | radius 8.5 cm; 5 cm | Assumption |
| Jump | Vertical take-off speed | 3.80 m/s | Above the 3.47 m/s mean of [Hu et al. 2005](https://ojs.ub.uni-konstanz.de/cpa/article/view/776/699): a strong jumper |
| Jump | Horizontal take-off speed | 1.30 m/s | Hu et al. 2005: 1.15 ± 0.36 m/s |
| Jump | Approach speed | 3.75 m/s | [Fuchs et al. 2019](https://iris.unicas.it/bitstream/11580/91401/1/02640414.2019.pdf): 3.75 ± 0.38 m/s |
| Swing | Shoulder angle and rate at contact | 18°, 12.5 rad/s (716°/s) | Below Hu et al. 2005 (909 ± 187°/s): deliberately conservative |
| Swing | Elbow bend at contact; peak extension rate | 8°; 1,270°/s | Hu et al. 2005: 1,230 ± 300°/s |
| Swing | Wrist angle and snap rate at contact | 6°, 15 rad/s | Assumption |
| Swing | Trunk lean and bend rate at contact | 10°, 3.5 rad/s | Assumption |
| Swing | Swing-plane lean toward the hitting side | 8° | Assumption |
| Setter | Eye-to-hand delay | 0.14 s | Sardinha & Bootsma 1993 (138 ± 33 ms), via [Bootsma et al. 2010](https://antoine-morice.pedaweb.univ-amu.fr/docs/publis/isi/Bootsma_Fernandez_Morice_Montagne_JEPHPP_2010.pdf) |
| Setter | Glances at the spiker | 20 per second, ±5 cm each | Assumption |
| Setter | Timing of the plant step | ±12 ms | Assumption |
| Setter | Approach-to-jump correlation | 0.5 | Assumption |
| Simulation | Attempts per scenario | 100,000 main; 20,000 per curve point; 10,000 per heat-map cell | Section 9.2 |

## Appendix B: numerical methods and how to reproduce every number

Every figure in this paper is read from one results file produced by the code in the source bundle that accompanies the video. Running `python3 analysis.py` regenerates it in about 20 minutes on two processor cores (Python 3.13, NumPy 2.5, SciPy 1.18).

### B.1 Files

| File | What it does |
| --- | --- |
| freak\_quick\_model.py | Ball flight, jump, arm, contact test, shooting solver, setter knowledge levels, Monte Carlo runner |
| kalman\_approach.py | The run-up model and the setter's Kalman filter (Section 8.3) |
| analysis.py | Runs all 188 experiments and writes results.json and samples.npz |
| results.json | Every number quoted in this paper |

### B.2 The arm's angle curves

With τ = t − t\_contact (negative before contact) and σ(x) = 1 / (1 + e⁻ˣ), the joint angles in radians are:

```latex
\begin{aligned}
\theta(\tau) &= \theta_c + 1.9\,\tanh\!\left(\frac{\omega_s\,\tau}{1.9}\right) \\
\beta(\tau) &= \max\!\left(0,\; \beta_c + 1.6\left[\sigma\!\left(-\frac{\tau + 0.035}{0.018}\right) - \sigma\!\left(-\frac{0.035}{0.018}\right)\right]\right) \\
\gamma(\tau) &= \gamma_c + 0.7\,\tanh\!\left(\frac{\omega_w\,\tau}{0.7}\right) \\
\psi(\tau) &= \psi_c + 0.6\,\tanh\!\left(\frac{\omega_p\,\tau}{0.6}\right)
\end{aligned}
```

θ is the shoulder, β the elbow bend, γ the wrist and ψ the trunk lean. Each passes its contact value (subscript c) at τ = 0 with the contact rate of Appendix A, and the tanh terms make each joint saturate smoothly away from contact.

### B.3 Numerical choices

| Step | Method | Setting |
| --- | --- | --- |
| Ball flight | Fourth-order Runge–Kutta | 2 ms steps; cubic Hermite interpolation between steps (error under 10⁻¹² m) |
| Perfect set | Newton's method with a finite-difference Jacobian | nudges of 10⁻⁴ m/s; converges in 2–3 corrections |
| Reading setter's re-aim | Chord method: the perfect set's Jacobian, reused | 3 iterations per attempt |
| Flight time | Brent's root-finding on vertical speed at contact = 0 | search between 0.15 and 0.9 s |
| First contact | Scan of the ball-to-palm gap, then bisection | 1 ms scan over ±0.16 s; 0.05 ms rescan from 14 ms before to 4 ms after the closest approach; 14 halvings |
| Hit point on the hand | Measured when the palm's plane is one ball radius from the ball's centre | gives the "across" and "along" offsets used in Sections 7 and 10 |
| Error budget | Forward differences | steps of 10⁻³ (spiker), 10⁻⁴ (setter), 10⁻² rad/s (spin) |
| Random numbers | NumPy PCG64 generator, fixed seeds | drawn in chunks of 20,000 attempts |

### B.4 Checks we ran

- **Integration accuracy:** changing the ball's time step from 17 ms to 0.13 ms moves the end point by less than a nanometre.
- **Kalman filter:** its predicted ±3.09 cm matches 20,000 simulated run-ups (±3.08 cm).
- **Error budget:** the straight-line prediction of the sideways spread, 27.3 cm, matches the full simulation's 25.3 cm.
- **Body model:** joint speeds and contact height fall within about 1.3 standard deviations of motion-capture data (Section 4.3).
- **Timing window:** the simple radius-over-speed estimate (±6.0 ms) matches the full contact simulation (±6.0 ms).

## References

Every source below was opened and read for this paper; the values used are those quoted in the sections that cite them.

1. Asai, T., Ito, S., Seo, K. & Hitotsubashi, A. (2010). [Aerodynamics of a new volleyball](https://lida.sport-iat.de/ta/Record/4019290?lng=en). *Procedia Engineering*, 2(2), 2493–2498.
2. [Fundamental aerodynamics of a new volleyball](https://sponet.de/sponet/Record/4026034?lng=en) (2010). *Sports Technology*, 3(4), 235–239.
3. Bootsma, R. J., Fernandez, L., Morice, A. H. P. & Montagne, G. (2010). [Top-level players' visual control of interceptive actions: Bootsma and van Wieringen (1990) 20 years later](https://antoine-morice.pedaweb.univ-amu.fr/docs/publis/isi/Bootsma_Fernandez_Morice_Montagne_JEPHPP_2010.pdf). *Journal of Experimental Psychology: Human Perception and Performance*, 36(4), 1056–1063. Also the source for Bootsma & van Wieringen (1990) and Sardinha & Bootsma (1993).
4. [Cannonball aerodynamic drag](https://arc.id.au/CannonballDrag.html), a reference on sphere drag coefficients and the drag crisis.
5. FIVB (2025). [Official Volleyball Rules 2025–2028](https://www.fivb.com/wp-content/uploads/2025/01/FIVB-Volleyball_Rules2025_2028-EN-v05.pdf), rules 1.1, 2.1.1 and 3.1.
6. Fuchs, P. X., Menzel, H.-J. K., Guidotti, F., Bell, J., von Duvillard, S. P. & Wagner, H. (2019). [Spike jump biomechanics in male versus female elite volleyball players](https://iris.unicas.it/bitstream/11580/91401/1/02640414.2019.pdf). *Journal of Sports Sciences*, 37(21), 2411–2419.
7. Hong, S., Weon, B. M., Nakanishi, Y., Kimachi, K., Seo, K. & Asai, T. (2018). [Aerodynamic effects of a panel orientation in volleyball float serve](https://commons.nmu.edu/isbs/vol36/iss1/212). *ISBS Proceedings Archive*, 36(1), 212.
8. Hu, L.-H., Chen, Y.-H. & Huang, C. (2005). [A 3D analysis of the volleyball spike](https://ojs.ub.uni-konstanz.de/cpa/article/view/776/699). *ISBS 2005*, Beijing.
9. Lobietti, R., Fantozzi, S., Stagni, R. & Coleman, S. G. S. [A biomechanical comparison of jumping techniques in the volleyball block and spike](https://ojs.ub.uni-konstanz.de/cpa/article/view/3163/2967). *ISBS Proceedings*.
10. Ma, L., Chablat, D., Bennis, F. & Zhang, W. (2009). [A new muscle fatigue and recovery model and its ergonomics application in human simulation](https://arxiv.org/pdf/0901.0825). arXiv:0901.0825.
11. McGrath, A., Glazer, A., Bushong, V., Nguyen, M. & Goldsberry, K. (2025). [Commanding the foul shot: a new ensemble of free throw metrics](https://arxiv.org/pdf/2512.08824). arXiv:2512.08824.
12. Meyer, E. R. & Bohn, J. L. (2008). [Influence of a humidor on the aerodynamics of baseballs](https://arxiv.org/pdf/0712.0380). arXiv:0712.0380. Also the source for the lift fit of Sawicki, Hubbard & Stronge (2003).
13. Scott, M. A., Li, F.-X. & Davids, K. (1997). [Expertise and the regulation of gait in the approach phase of the long jump](https://shura.shu.ac.uk/3317/). *Journal of Sports Sciences*, 15(6), 597–605.
14. Smeets, J. B. J., Frens, M. A. & Brenner, E. (2002). [Throwing darts: timing is not the limiting factor](https://personal.fbw.vu.nl/~jsmeets/2002/Darts_timing-EBR02.pdf). *Experimental Brain Research*, 144, 268–274.
15. Sujeevan, S. (2026). [How physically feasible is the Minus Tempo attack in volleyball?](https://journals.le.ac.uk/index.php/jist/article/download/5252/5076/21444) *Journal of Interdisciplinary Science Topics*.
16. Wisner, D. M., Branta, C. F., Haubenstricker, J. L. & Seefeldt, V. (2006). [Upper body segment lengths as a proportion of height in children](https://ojs.ub.uni-konstanz.de/cpa/article/view/292). *ISBS 2006*. Also the pointer to the Drillis & Contini (1966) proportions in Winter (2005).
17. Zhang, Z., Guo, D., Huber, M. E., Park, S.-W. & Sternad, D. (2018). [Exploiting the geometry of the solution space to reduce sensitivity to neuromotor noise](https://pmc.ncbi.nlm.nih.gov/articles/PMC5834204). *PLoS Computational Biology*. Also the source for Repp's tapping data.
