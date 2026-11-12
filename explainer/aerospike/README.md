# How an aerospike starts: explainer video

A 9:16 explainer (1080×1920, 30 fps, 23.8 s) on how LEAP 71's 20 kN methalox
Noyron aerospike starts. It shares the timing and transitions of the "How a Raptor
engine starts" reference. The whole clip is one continuous take, and the simulation
never restarts.

| Time | What happens |
|---|---|
| 0–8.6 s | Close-up of the chamber filling, then a slow pull-back from 2.9 s. Typewriter captions (0.25, 3.1, 7.0 s): combustion, methane cooling the outer chamber, LOX cooling the spike. Both cooling circuits are drawn with flowing coolant, arrows and a legend. No flame outside the engine yet |
| 8.6–9.25 s | Title and stats fade out, the sim panel slides up, and the footage fades in |
| 9.55–10.25 s | Footage: cold propellant flow before ignition. Sim: the throat is about to choke |
| 10.25 s | Ignition fireball in the footage; the sim panel flashes, as in the reference |
| 10.55 s | The green jet leaves the ring in the footage, and the sim jet leaves the slot. Its length then tracks the real flame frame by frame until full length (~11.2 s), where the model's second stage brings the chamber to full pressure |
| 10.5–22.3 s | Captions start at 10.5, 12.25, 13.75, 16.5 (+17.0) and 20.0 s. Annotations appear and stay: free boundary, waves, plume closes |
| 22.3–23.8 s | Fast rewind of the sim and push-in back to the first frame, so the clip loops |

Output: `out/aerospike-explainer.mp4`

## What is known, what is assumed

**Footage:** LEAP 71's hot fire of the 20 kN methalox aerospike at Airborne Engineering.
It is 6.8 s at 60 fps, played 2× slower, and has no sound.

**From LEAP 71 (leap71.com, photo, footage):**
* The engine is a 20 kN methalox aerospike. It reached full chamber pressure, 50 bar, on
  a single burn; the site cites startup-transient issues. It was 3D-printed in CuCrZr.
* It is the middle engine in LEAP 71's photo of its three Noyron aerospikes, and the
  engine in the footage.
* Regenerative cooling: the outer chamber is cooled by cryogenic methane and the spike
  by liquid oxygen. LEAP 71 states this for the XRA-2E5, and the same split, with
  kerosene instead of methane, for the 5 kN engine. The video draws the 20 kN engine
  the same way: methane comes in at the cowl lip and runs up the cowl wall and around
  the outside of the toroidal chamber to the injector face. LOX runs down the axis to
  the spike tip, back along the spike wall to the throat, and under the chamber to the
  injector face. The circuits are drawn, not simulated; the model has cooled walls but
  no coolant flow.

**Size and shape (units of spike root radius, L0 ≈ 3.5 cm):**
* The body is about 0.29 m across, measured against the 1 m tall XRA-2E5 in the same photo.
* An urn-shaped body, about 3.3 at the head with a bulge of about 4.1, then a rounded
  corner into an almost flat bottom.
* A short, stubby, slightly concave spike: about 20° at the root, 1.73 long, truncated
  at r ≈ 0.55.
* The flame leaves the engine as a large bright ring at the bottom corner (footage).

**Assumed, because the inside is not visible:**
* **Throat.** The annular throat sits at the bottom corner (r ≈ 2.4) and points the flow
  70° inward. The almost flat bottom is the steep first part of the spike contour, and a
  fillet turns it into the slender visible spike.
* **Chamber.** The toroidal chamber sits in the bulge of the body and feeds the throat
  through a short converging slot.
* **Consistency check.** A_t ≈ 28 cm² and ε ≈ 8. At the real size and 50 bar the model
  then produces about 20 kN, so thrust is computed, not scaled.
* **Pressure is 70° inward.** After the external expansion to 1 atm (about 65° of
  Prandtl–Meyer turning from sonic for γ = 1.2 and Pc/pa = 50), the outer jet boundary
  still heads inward. Sea-level air therefore presses the plume onto the spike.
* **Coolants.** LOX in the spike, methane in the chamber wall and cowl, by analogy
  with LEAP 71's other aerospikes.
* **Start-up.** Two stages, about 20 bar then full pressure. Their timing is mapped onto
  the footage: the jet grows from the first green streaks to full length in about
  0.4 s of real time.

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
  Reynolds analogy. The heat flux on the spike is drawn as a glow, and its peak is
  shown on screen.
* **Turbulence.** A Smagorinsky eddy viscosity acts in the shear layers. Its coefficient,
  Cs = 0.45, was chosen so the base region empties and the plume can close behind the
  tip; it is not validated.
* **Chamber.** The chamber is not combusting. A thin "injector" region is forced to the
  stagnation state (about 3,500 K), in two stages. Ambient air is 1 atm and 300 K.

**Limits.** There is no injector or 3D flow, and no resolved boundary layer. There is no
conjugate heat transfer: the coolant is drawn, not simulated. The physical time scale is
compressed: the model reaches full pressure within about 1 ms of model time, whereas a
real start takes far longer. Playback is therefore matched to the footage.

Playback speed:
* **Before ignition.** The video shows chamber filling only (t = 0.22–0.70).
* **At ignition.** The sim flash lands on the real fireball. The sim jet leaves the slot
  when the real green jet leaves the ring, and its length then tracks the real flame,
  both as a fraction of their panel.
* **At full length.** The model's second stage lands on the moment the real jet reaches
  full length.
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
* **The engine** is drawn from `geometry.py`, with the model's wall heat flux as a glow
  on the spike.
* **Type** is set in Jost (OFL, see `fonts/`).
* **Footage** is rotated and cropped so its plume axis is horizontal like the sim.
* **Audio** is synthetic, because the footage has no sound: a hiss of cold flow before
  ignition, a crack at the fireball, then a roar that follows the model's chamber
  pressure and thrust.
* **Cooling circuits** are drawn inside the metal from `geometry.coolant_paths()`. The
  coolant pulses move in the flow direction and warm from cold to hot along the way.
