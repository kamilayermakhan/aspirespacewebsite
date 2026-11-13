# How an aerospike starts: explainer video

A 9:16 explainer (1080×1920, 30 fps, 23.8 s) on how LEAP 71's 20 kN methalox
aerospike works and how it is cooled. It shares the timing and transitions of the
"How a Raptor engine starts" reference: one continuous take in which the simulation never
restarts.

Output: `out/aerospike-explainer.mp4`

## How it works (the corrected scheme)

1. **Ring chamber.** The combustion chamber is a ring at the head end. Its head face is
   the injector, where methane and oxygen enter.
2. **Annular flow.** The hot gas leaves the chamber as an annular stream. It runs
   through a converging passage between the outer shell and the central body and exits
   at the lip.
3. **Axial jet.** Outside, the annular flow wraps the long, slender central body and
   converges into an axial jet past its tip.
4. **Methane.** It cools the outer shell. It enters at the lip and runs back through
   channels inside the shell (throat, passage, outer chamber wall) to the injector.
5. **Oxygen.** It cools the central body. It enters along the axis, runs inside the
   central body to its tip, turns, and comes back through channels under the body's hot
   surface to the injector.
6. **Channels inside the walls, hot gas outside them.** The routing and size of the
   channels are notional.
7. **The green colour** of the test flame is copper burning, per LEAP 71. It does not
   indicate nominal cooling.

Flame phases (time from the start of the hot-fire clip):

| Footage time | Phase |
|---|---|
| ~0.2 s | Initial gas release; the flame has not formed yet |
| ~0.7–1.2 s | The axial jet forms; the annular flow wraps the central body |
| from ~1.7 s | Developed test flame; green glow from copper |

## Timeline of the video

| Time | What happens |
|---|---|
| 0–8.6 s | Close-up of the ring chamber and the injector face. The camera then follows the hot gas down the annular passage and along the central body to its tip, and pulls back. Captions at 0.25 s (combustion), 3.1 s (methane) and 7.0 s (oxygen) |
| 8.6–9.25 s | Title and stats fade out, the sim panel slides up, and the footage fades in |
| 10.25 s | Ignition fireball in the footage; the sim panel flashes |
| 10.0 / 11.0 / 13.0 s | Phase captions, at footage times 0.23, 0.73 and 1.73 s |
| 16.5 s | "Channels inside the walls, hot gas outside them." |
| 22.3–23.8 s | Fast rewind and push-in back to the first frame, so the clip loops |

## Engine (`geometry.py`, units of L0 = 3.54 cm)

* **Size.** The body is 0.29 m across, measured on LEAP 71's photo next to the 1 m
  XRA-2E5. The other proportions follow the scheme.
* **Chamber.** A ring at the head end, x = −0.35…1.45, r = 2.55…3.45.
* **Throat.** It sits at the lip, r ≈ 2.2. Its area of 2.35 L0² (29 cm²) gives about
  20 kN at 46–50 bar.
* **Central body: an ideal (Angelino) aerospike contour.**
  * The lip radius is ~0.55 of the body radius, so the area ratio is ε = 6.8. That is
    full expansion to 1 atm at ~46 bar (M_e = 3.0).
  * The throat is turned ν(M_e) = 64° inward.
  * Every Mach line from the lip carries the isentropic area, so the annular flow
    expands along the central body and converges towards the axis.
  * The contour is truncated where it is r = 0.25 thin, 4.7 L0 behind the lip.
  * The scheme draws the flow ~40° inward at the lip. With only 40°, the external
    expansion at the lip would turn the outer jet boundary outward, like a spray. The
    ideal contour is what makes the flow wrap the central body, as the scheme shows.

## Model

**Flow** (`euler.c`) is a 2D axisymmetric compressible solver:
* MUSCL / HLLC / SSP-RK2 on 1167 × 600 cells (Δ = 0.015 L0, about 11 cells across the
  throat).
* The domain reaches r = 9 L0, more than twice the body radius, and 1.8 L0 ahead of the
  head face. The jet can then entrain still air freely. A boundary close to the engine
  confines the jet, and its exhaust then circulates back in a cloud around it.
* Two gases: methalox exhaust (γ 1.2, 22 g/mol) and air (γ 1.4).
* Afterburning of the fuel-rich exhaust in air.
* Cooled walls with a wall function, St = 0.0025 at Tw = 800 K.
* Smagorinsky eddy viscosity with Cs = 0.45, chosen, not validated.
* The chamber is not combusting. An "injector" layer at its head face is forced to the
  stagnation state (~3,500 K) in two stages, ~20 bar then full pressure. Ambient air is
  1 atm, 300 K.

**Coolant** (`cooling.py`, every frame) uses a 1D energy balance along both circuits with
the flow solution's wall heat flux:
  T_coolant(s) = T_in + Q(s) / (ṁ cp)
* ṁ = Pc·A_t/c* (c* = 1800 m/s, O/F = 3.3) at the nominal pressure.
* CH4: in at 120 K, cp 3.6 kJ/kg/K.
* O2: in at 95 K, cp 1.7 kJ/kg/K.
* The channel coefficient is h = 60 kW/m²/K.

**Metal** (`cooling.conduction`) uses steady 2D axisymmetric conduction:
* CuCrZr (k = 320 W/m/K) on the hot walls and around the channels, steel
  (k = 20 W/m/K) elsewhere.
* Hot-gas side: q = h_g (T_gas − T_wall), with h_g and T_gas from the flow solution.
* Coolant side: q = h_c (T_wall − T_coolant).
* It is solved once at full pressure and once chilled down; frames are blended by the
  current heat load.

**Limits.**
* No injector, 3D or boundary-layer resolution.
* The coolant is a 1D balance with constant properties: methane's pseudo-critical
  behaviour is ignored.
* The real channel geometry of the 20 kN engine is not public.
* The start-up time scale is compressed, so playback is matched to the footage.

## Build

```
gcc -O3 -march=native -fopenmp -o euler euler.c -lm
python3 setup_case.py RUN_DIR            # params.txt + flags.u8 (geometry mask)
./euler RUN_DIR                           # ~1 h on 4 cores
python3 make_video.py RUN_DIR hotfire.mov out/aerospike-explainer.mp4
```

`make_video.py`:
* **Flame brightness** comes from the model's temperature and density. **Flame colour**
  is sampled from the footage on screen.
* **The metal** is coloured by its computed temperature.
* **The coolant channels** are coloured by the computed coolant temperature, with flow
  arrows: oxygen blue, methane violet.
* **The footage** is the hot fire at Airborne Engineering (60 fps, played 2× slower).
  It is rotated by its measured 26° flame axis and centred, as in the reference.
* **Audio** is synthetic, because the footage has no sound.
* **Type** is set in Jost.
