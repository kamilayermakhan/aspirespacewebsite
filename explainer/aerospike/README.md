# How an aerospike starts: explainer video

A 9:16 explainer (1080×1920, 30 fps, 23.8 s) on how LEAP 71's 20 kN methalox
Noyron aerospike starts and how it is cooled. It shares the timing and transitions of
the "How a Raptor engine starts" reference. The whole clip is one continuous take, and
the simulation never restarts.

| Time | What happens |
|---|---|
| 0–4.6 s | Close-up of the toroidal chamber, the injector face, the manifolds and the methane channels in the cowl. Chamber filling. Captions at 0.25 s (combustion) and 3.1 s (methane path) |
| 4.6–7.0 s | The camera glides down the spike along the LOX channels in its skin, to the tip plenum and the axial LOX feed |
| 7.0–8.6 s | Caption at 7.0 s (LOX path); the camera pulls back to the whole engine |
| 8.6–9.25 s | Title and stats fade out, the sim panel slides up, and the footage fades in |
| 9.55–10.25 s | Footage: cold propellant flow. Sim: the throat is about to choke |
| 10.25 s | Ignition fireball in the footage; the sim panel flashes, as in the reference |
| 10.58 s | The first green streaks leave the ring in the footage, and the sim jet leaves the slot. It grows on the weak first stage |
| 11.15 s | The real flame becomes one full column, and the model's second stage brings the chamber to full pressure |
| 10.5–22.3 s | Captions start at 10.5, 12.25, 13.75, 16.5 (+17.0) and 20.0 s. Annotations appear and stay: free boundary, waves, plume closes. A legend shows the computed coolant outlet temperatures and peak copper-wall temperature |
| 22.3–23.8 s | Fast rewind of the sim and push-in back to the first frame, so the clip loops |

Output: `out/aerospike-explainer.mp4`

## What is known, what is assumed

**Footage.** LEAP 71's hot fire of the 20 kN methalox aerospike at Airborne Engineering:
6.8 s at 60 fps, played 2× slower, no sound. It is straightened the way the reference is.
* **Rotation.** The flame's bright core runs 26° below horizontal in the source. After
  rotating by 26°, its upper and lower edges are symmetric (−2.0° and +2.5°).
* **Crop.** The axis sits at the vertical centre and the engine exit at 25 % of the width.

**Flame course** (source time, measured frame by frame):
* 0–0.33 s: cold propellant flow.
* 0.35–0.50 s: ignition fireball.
* 0.517 s: first thin green streaks from the ring, converging along the spike.
* 0.52–0.78 s: a growing, flickering green jet with an afterburning cloud beyond it.
* From 0.80 s: one bright full column.

**From LEAP 71 (leap71.com, photos, footage):**
* The engine is a 20 kN methalox aerospike. It reached full chamber pressure, 50 bar, on
  a single burn; the site cites startup-transient issues. It was 3D-printed in CuCrZr.
* It is the middle engine in LEAP 71's photo of its three Noyron aerospikes, and the
  engine in the footage.
* **Regenerative cooling.** The outer chamber is cooled by cryogenic methane and the
  spike by liquid oxygen. LEAP 71 states this for the XRA-2E5, and the same split, with
  kerosene instead of methane, for the 5 kN engine. The video uses it for the 20 kN engine.
* **What the cutaways show.** LEAP 71's dual-metal aerospike test part, printed by
  Fraunhofer IGCV, shows the kind of structure involved:
  * a copper liner on every hot wall and inside every channel, steel outside;
  * rows of small helical channels;
  * ribbed toroidal manifolds and branching feeds;
  * an injector face with many elements;
  * an axial feed down the spike;
  * lightening windows between ribs.

**Size and shape (units of spike root radius, L0 ≈ 3.5 cm):**
* The body is about 0.29 m across, measured against the 1 m tall XRA-2E5 in the same photo.
* An urn-shaped body, about 3.3 at the head with a bulge of about 4.1, then a rounded
  corner into an almost flat bottom.
* A short, stubby, slightly concave spike: about 20° at the root, 1.73 long, truncated
  at r ≈ 0.55.

**Assumed, because the inside is not visible:**
* **Throat.** The annular throat sits at the bottom corner (r ≈ 2.4) and points the flow
  70° inward. The almost flat bottom is the steep first part of the spike contour.
* **Chamber.** The toroidal chamber sits in the bulge of the body and feeds the throat
  through a short converging slot.
* **Consistency check.** A_t ≈ 28 cm² and ε ≈ 8. At the real size and about 46 bar the
  model produces about 19 kN, so thrust is computed, not scaled.
* **Why 70° inward.** After the external expansion to 1 atm, the outer jet boundary
  still heads inward, so sea-level air presses the plume onto the spike.
* **Cooling network** (`cooling.py`), in the style of LEAP 71's parts. Both circuits run
  counterflow.
  * **CH4.** In at a small manifold in the cowl, just upstream of the lip. Through 25
    channels in the cowl and the outer chamber wall; the cowl channels are shallower
    where the cowl is thin. Into a ribbed collector torus behind the injector, then five
    branches to the CH4 injector manifold.
  * **LOX.** Down an axial bore to a plenum in the truncated spike tip. Back through 86
    channels in the base, the spike skin, the inner slot wall and the chamber floor.
    Into a collector torus, then five branches to the LOX injector manifold.
  * **Injector.** Ten elements on the injector face, alternating CH4 and LOX.
* **Start-up.** Two stages, about 20 bar then full pressure, mapped onto the flame course
  above.

## Model

`euler.c` is a 2D axisymmetric compressible finite-volume solver:

* MUSCL (minmod) reconstruction with HLLC fluxes and SSP-RK2 time stepping, on a grid of
  958 × 367 cells (Δ = 0.012 L0, about 12 cells across the throat).
* **Two gases.** Methalox exhaust (γ 1.2, 22 g/mol, frozen) and air (γ 1.4, 29 g/mol),
  mixed by the exhaust mass fraction.
* **Afterburning.** A second scalar tracks unburned fuel-rich exhaust. It burns with
  entrained air above 1,000 K, releasing about 1.2 MJ per kg of exhaust.
* **Cooled walls.** The stair-step walls carry a wall function: gas-side heat loss
  q = St ρ|V| cp (T − Tw) with St = 0.0025 and Tw = 800 K, plus skin friction from the
  Reynolds analogy.
* **Turbulence.** A Smagorinsky eddy viscosity acts in the shear layers. Its coefficient,
  Cs = 0.45, was chosen so the base region empties and the plume can close behind the
  tip; it is not validated.
* **Chamber.** The chamber is not combusting. A thin "injector" region is forced to the
  stagnation state (about 3,500 K), in two stages. Ambient air is 1 atm and 300 K.

**Coolant and wall temperatures** (`cooling.solve`, every frame). The model's wall heat
flux is sampled along both hot-wall circuits and integrated in the flow direction:
  dQ = q 2πr ds,  T_coolant = T_in + Q / (ṁ cp),  T_wall = T_coolant + q (1/h + t/k).
* **Inputs.**
  * ṁ from Pc·A_t/c* (c* = 1800 m/s, O/F = 3.3), at the nominal pressure, because the
    supply sets the coolant flow, not the chamber.
  * CH4: in at 120 K, cp 3.6 kJ/kg/K.
  * LOX: in at 95 K, cp 1.7 kJ/kg/K.
  * h = 60 kW/m²/K, and a 0.8 mm CuCrZr liner with k = 320 W/m/K.
* **Results at full pressure.**
  * About 0.45 MW goes into the methane: 120 → 194 K.
  * About 0.40 MW goes into the oxygen: 95 → 137 K.
  * The peak copper wall temperature is about 700 K, at the throat, where q ≈ 35 MW/m².
* **What it is not.** It is a 1D balance, not conjugate heat transfer. Coolant properties
  are constant: the real methane passes its pseudo-critical point, which this ignores.
  The CFD wall temperature stays fixed at 800 K.

**Limits.** There is no injector or 3D flow, and no resolved boundary layer. The channel
layout is a plausible one; the real 20 kN engine's is not public. The physical time scale
is compressed: the model reaches full pressure within about 1 ms of model time, whereas a
real start takes far longer. Playback is therefore matched to the footage.

Playback speed:
* **Before ignition.** The video shows chamber filling only (t = 0.22–0.70).
* **At ignition.** The sim flash lands on the real fireball. The sim jet leaves the slot
  with the first green streaks and grows on the first stage.
* **At full column.** The model's second stage lands on the moment the real flame becomes
  one full column.
* **Established jet.** It then plays at about 1.4 model units per second.

```
gcc -O3 -march=native -fopenmp -o euler euler.c -lm
python3 setup_case.py RUN_DIR            # params.txt + flags.u8 (geometry mask)
./euler RUN_DIR                           # ~1 h on 4 cores, ~4.5 GB of float16 snapshots
python3 make_video.py RUN_DIR hotfire.mov out/aerospike-explainer.mp4
```

`make_video.py` renders the video:

* **Brightness** follows the model: hot exhaust and afterburning mixture glow by
  temperature and density. A faint schlieren layer shows waves in the air.
* **Colour** is sampled from the footage on screen. The flame pixels are sorted by
  brightness and mapped onto the model's intensity, and the palette is smoothed over time.
* **The engine** is a steel body from `geometry.py`, with a printed-metal grain fixed to
  the part.
* **The cooling network** is drawn from `cooling.py`:
  * the copper liner is coloured by the computed wall temperature;
  * each channel's coolant is coloured by its computed temperature, with a pulse that
    travels in the flow direction;
  * the manifolds, branching feeds, injector elements, the LOX bore and tip plenum are
    drawn as well, plus lightening windows between ribs in the upper body.
* **The camera** can frame off-axis close-ups (view = x range, half-height, centre r).
* **Type** is set in Jost (OFL, see `fonts/`).
* **Audio** is synthetic, because the footage has no sound: a hiss of cold flow before
  ignition, a crack at the fireball, then a roar that follows the model's chamber
  pressure and thrust.
