# Aerospike by LEAP 71: explainer video

A 9:16 video (1080×1920, 30 fps, 23.8 s) of LEAP 71's 20 kN methalox aerospike. It shares the
timing and transitions of the "How a Raptor engine starts" reference: one continuous take in
which the simulation never restarts.

* **Top:** the simulation.
* **Bottom:** the hot-fire footage, 2× slower.
* **Text:** only "Aerospike by LEAP 71" and the propellants, "Methalox · liquid methane +
  liquid oxygen". The propellant names are coloured like their cooling channels.

Output: `out/aerospike-explainer.mp4`

## How it works (the corrected scheme)

1. **Ring chamber.** The combustion chamber is a ring at the head end of the body. Its head
   face is the injector, where methane and oxygen enter.
2. **Annular flow.** The hot gas leaves the chamber as an annular stream. It runs through a
   converging passage between the outer shell and the central body and exits at the lip.
3. **Axial jet.** Outside, the annular flow runs along the short spike and converges into an
   axial jet past its tip.
4. **Methane.** It cools the outer shell. It enters at the lip, through the inlet on the
   bottom face, and runs back through channels inside the shell to the injector.
5. **Oxygen.** It cools the central body. It enters along the axis at the top, runs inside
   the central body to the spike's tip, turns, and comes back through channels under the
   body's hot surface to the injector.
6. **Channels inside the walls, hot gas outside them.** The routing and size of the channels
   are notional.

## Engine (`geometry.py`, units of L0 = 3.54 cm, lip plane at x = 0)

**Outside.** The shape is the middle engine on LEAP 71's photo of three engines: the 20 kN
methalox engine fired in December. Its proportions are measured on that photo.
* **Crown.** A crown of manifolds at the head, with the oxygen inlet on the axis.
* **Body.** It is 0.29 m across and widens towards the bottom. Its height is 1.18× its width.
* **Bottom.** A flat bottom face with rounded corners carries the methane inlet.
* **Spike.** It is short and horn-shaped, about 9 cm across at its root.

**Inside.**
* **Chamber.** A ring at x = −5.0…−1.7, r = 2.2…3.1, with L* ≈ 0.74 m.
* **Passage.** It converges from 0.9 to the throat.
* **Throat.** It is at the lip, r = 1.31…1.50. Its area of 2.35 L0² (29 cm²) gives about
  20 kN at ~50 bar.
* **Spike contour.** It is the ideal (Angelino) contour for the lip:
  * The area ratio is ε = 3.0 and the design Mach is 2.4.
  * The throat is turned 45° inward, close to the ~40° drawn in the scheme.
  * The contour is truncated where the spike is r = 0.38 thin, as on the photo.
* **Expansion.** At ~50 bar the flow leaves the lip under-expanded at sea level.

## Start-up and timing

The simulation runs the start in the same order as the footage:

| Footage time | Footage | Simulation (model time) |
|---|---|---|
| 0–0.33 s | Cold propellant flow, a pale cloud | Cold propellant gas (150 K, 3 bar) flows through the engine (0–8) |
| 0.35 s | Ignition fireball fills the frame | The gas in the chamber ignites (8.0); the panel flashes |
| 0.35–0.52 s | Fireball | The jet crosses the panel, fast-forwarded |
| 0.52–0.78 s | Thin green streaks | Weak first stage, ~25 bar |
| from 0.80 s | One bright full column | Full pressure (~49 bar) |

The start-up is compressed: the model's start takes a few milliseconds, the real one about
half a second. Playback is matched to the footage.

## Timeline of the video

| Time | What happens |
|---|---|
| 0–8.6 s | Close-up of the ring chamber, injector and channels during the cold flow. The camera then follows the passage to the lip and the spike, and pulls back to the whole engine |
| 8.6–9.25 s | The panel shrinks to the top and the footage fades in below |
| 10.25 s | Ignition fireball in the footage and in the simulation; the panel flashes |
| 22.3–23.8 s | Fast rewind and push-in back to the first frame, so the clip loops |

## Model

**Flow** (`euler.c`) is a 2D axisymmetric compressible solver:
* MUSCL / HLLC / SSP-RK2 on 1234 × 450 cells, Δ = 0.02 L0, 13 cells across the throat.
* Two gases: methalox exhaust (γ 1.2, 22 g/mol) and air (γ 1.4).
* Afterburning of the fuel-rich exhaust in air.
* Cooled walls with a wall function, St = 0.0025 at Tw = 800 K.
* Smagorinsky eddy viscosity with Cs = 0.45, chosen, not validated.
* Domain:
  * It reaches r = 9 L0, more than twice the body radius, so the jet can entrain still air
    freely.
  * The outlet lets no air flow back in.
* Start-up:
  * The cold flow is cold propellant gas (tagged as exhaust, unburned).
  * At ignition, the gas in the chamber and passage is heated to ~3,500 K at constant pressure.
  * After ignition, an "injector" layer at the chamber's head face is forced to the
    stagnation state in two stages.
* The chamber chemistry is not modelled. Ambient air is 1 atm, 300 K.

**Coolant** (`cooling.py`, every frame) uses a 1D energy balance along both circuits with the
flow solution's wall heat flux:
  T_coolant(s) = T_in + Q(s) / (ṁ cp)
* ṁ = Pc·A_t/c* (c* = 1800 m/s, O/F = 3.3) at the nominal pressure.
* CH4: in at 120 K, cp 3.6 kJ/kg/K.
* O2: in at 95 K, cp 1.7 kJ/kg/K.
* The channel coefficient is h = 60 kW/m²/K.

**Metal** (`cooling.conduction`) uses steady 2D axisymmetric conduction:
* CuCrZr (k = 320 W/m/K) on the hot walls and around the channels, steel (k = 20 W/m/K)
  elsewhere.
* Hot-gas side: q = h_g (T_gas − T_wall). Coolant side: q = h_c (T_wall − T_coolant).
* It is solved at full pressure and chilled down; frames are blended by the heat load.
* It is drawn in copper colours, glowing where hot.

**Limits.**
* No injector, 3D or boundary-layer resolution.
* The coolant is a 1D balance with constant properties.
* The real channel geometry of the 20 kN engine is not public.
* The start-up time scale is compressed.

## Build

```
gcc -O3 -march=native -fopenmp -o euler euler.c -lm
python3 setup_case.py RUN_DIR            # params.txt + flags.u8 (geometry mask)
./euler RUN_DIR                           # ~40 min on 4 cores
python3 make_video.py RUN_DIR hotfire.mov out/aerospike-explainer.mp4
```

`make_video.py`:
* **Flame brightness** comes from the model's temperature and density. **Flame colour** is
  sampled from the footage on screen. **Cold propellant gas** is drawn as a pale vapour.
* **The metal** is coloured by its computed temperature.
* **The coolant channels** are coloured by the computed coolant temperature, with flow
  arrows: oxygen blue, methane violet.
* **The footage** is the hot fire at Airborne Engineering (60 fps, played 2× slower). It is
  rotated by its measured 26° flame axis and centred, as in the reference.
* **Audio** is synthetic, because the footage has no sound.
* **Type** is set in Jost.
