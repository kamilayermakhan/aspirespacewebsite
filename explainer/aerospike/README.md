# How an aerospike starts: explainer video

A 9:16 explainer (1080×1920, 30 fps, 23.8 s) on how LEAP 71's 20 kN methalox
Noyron aerospike starts. It shares the timing and transitions of the "How a Raptor
engine starts" reference. The whole clip is one continuous take, and the simulation
never restarts.

| Time | What happens |
|---|---|
| 0–8.6 s | Close-up of the chamber, then a slow pull-back from 2.9 s. Three typewriter captions (0.25, 3.1, 7.0 s). Live T+ clock, slow-motion factor, thrust / exit Mach / chamber T / Pc, sparklines |
| 8.6–9.25 s | Title and stats fade out, the sim panel slides up, and the hot-fire footage fades in below it |
| 10.25 s | The sim panel flashes as the real engine reaches full flow (footage at 6.35 s) |
| 10.5–22.3 s | Simulation vs. real. Captions start at 10.5, 12.25, 13.75, 16.5 (+17.0) and 20.0 s. Annotations appear and stay: free boundary, waves, plume closes |
| 22.3–23.8 s | Fast rewind of the sim and push-in back to the first frame, so the clip loops |

Output: `out/aerospike-explainer.mp4`

## Engine data and assumptions

* **Engine:** LEAP 71's 20 kN methalox aerospike, the middle engine in LEAP 71's photo of
  its three Noyron aerospikes. It is the engine in the footage.
* **Chamber pressure:** LEAP 71 reports 50 bar (leap71.com/2025/12/11/…), and the sim
  uses 50 bar.
* **Thrust** is scaled so that the steady sea-level value is 20 kN.
* **Shape, traced from the photo** (units of spike root radius):
  * an urn-shaped body: about 3.3 at the head, a bulge of about 4.1, then a rounded
    corner into an almost flat bottom face;
  * a short, stubby spike: about 20° at the root, 1.73 long, truncated at r ≈ 0.56.
* **The internal layout is an assumption,** because the inside is not visible: a toroidal
  chamber, and an annular slot with its throat just inside the bottom face (area ratio
  about 7.9).
* **Footage:** LEAP 71's own reel (@leap.71).

## Simulation

`euler.c` is a 2D axisymmetric Euler finite-volume solver:

* MUSCL (minmod) reconstruction with HLLC fluxes and SSP-RK2 time stepping.
* Stair-step slip walls.
* A single perfect gas (γ = 1.2) plus a passive scalar that marks exhaust vs. air.
* Grid: 1400 × 460 cells (Δ = 0.01 × spike root radius).

The chamber is fed by a thin "injector" region forced to the stagnation state (ramped
to 50 bar, ~3,400 K). Ambient air is 1 atm and 300 K. The video shows t = 0.22–4.75
(sea level). The run continues with a far-field pressure ramp to 0.03 atm, which the
video does not use.

```
gcc -O3 -march=native -fopenmp -o euler euler.c -lm
python3 setup_case.py RUN_DIR            # params.txt + flags.u8 (geometry mask)
./euler RUN_DIR                           # ~35 min on 4 cores, ~5 GB of snapshots
python3 make_video.py RUN_DIR hotfire.mp4 out/aerospike-explainer.mp4
```

`make_video.py` handles the rest:

* It renders the fields (exhaust fraction × temperature, with a schlieren layer)
  in a violet palette and draws the engine outline from `geometry.py`.
* It sets all type in Jost (OFL, see `fonts/`).
* It rotates and crops the hot-fire footage so its plume axis is horizontal like the sim.
* It mixes the audio: a synthetic rumble driven by the simulated chamber pressure in
  part 1, then the hot fire's own sound, synced to the footage.
