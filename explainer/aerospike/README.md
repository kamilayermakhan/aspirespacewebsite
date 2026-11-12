# How an aerospike starts: explainer video

A 9:16 explainer (1080×1920, 30 fps, 23.8 s) on how LEAP 71's 20 kN methalox
Noyron aerospike starts. It shares the timing and transitions of the "How a Raptor
engine starts" reference. The whole clip is one continuous take, and the simulation
never restarts.

| Time | What happens |
|---|---|
| 0–8.6 s | Close-up of the chamber filling, then a slow pull-back from 2.9 s. Three typewriter captions (0.25, 3.1, 7.0 s). No flame outside the engine yet |
| 8.6–9.25 s | Title and stats fade out, the sim panel slides up, and the footage's first frame (the ignition spark) fades in |
| 10.0 s | Ignition (wide shot, footage 0.0 s). From the frame where the real flame appears (+0.10 s), the sim jet length tracks the real flame length frame by frame, both measured as a fraction of their panel: about 45 % at +0.10 s, 60 % at +0.2 s, then the full panel |
| 11.8 s | The footage cuts to the close-up; at 12.85 s the real engine reaches full flow (footage 6.35 s) and the sim panel flashes as the sim reaches full chamber pressure |
| 10.5–22.3 s | Captions start at 10.5, 12.25, 13.75, 16.5 (+17.0) and 20.0 s. Annotations appear and stay: free boundary, waves, plume closes |
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
* **The internal layout is an assumption,** because the inside is not visible:
  * a toroidal chamber;
  * an annular slot with its throat just inside the bottom face (area ratio about 7.2);
  * a short ramp and fillet from the slot into the traced spike profile.
* **The slot points the flow 50° inward,** not along the visible 20° spike root. After
  the external expansion at the lip down to 1 atm (about 37° of Prandtl–Meyer turning
  for γ = 1.2 and Pc/pa = 50), the outer jet boundary still heads inward, so sea-level
  air presses the plume onto the spike, as in the hot fire. A 22° slot made the
  boundary splay outward like a spray.
* **Footage:** LEAP 71's own reel (@leap.71).

## Simulation

`euler.c` is a 2D axisymmetric Euler finite-volume solver:

* MUSCL (minmod) reconstruction with HLLC fluxes and SSP-RK2 time stepping.
* Stair-step slip walls.
* A single perfect gas (γ = 1.2) plus a passive scalar that marks exhaust vs. air.
* A Smagorinsky eddy viscosity (Cs = 0.45) in the shear layers. It stands in for the
  turbulent entrainment that empties the base region behind the truncated spike, so
  the plume can close there as it does on the stand.
* Grid: 1150 × 280 cells (Δ = 0.01 × spike root radius). The domain is cropped to the frame, and the body runs into the top boundary.

The chamber is fed by a thin "injector" region forced to the stagnation state (ramped
to 50 bar, ~3,400 K). Ambient air is 1 atm and 300 K throughout, and the run goes to
t = 21.6.

Playback speed:
* **Before ignition** the video shows chamber filling only (t = 0.22–0.68).
* **After ignition** the sim jet length tracks the measured real flame length frame by
  frame. Both are measured as a fraction of their panel, starting on the frame where the
  real flame appears.
* **The established jet** then plays at about 1.5 sim units per second, so its eddies move
  about as fast as the real flame's.

```
gcc -O3 -march=native -fopenmp -o euler euler.c -lm
python3 setup_case.py RUN_DIR            # params.txt + flags.u8 (geometry mask)
./euler RUN_DIR                           # ~1 h on 4 cores, ~4 GB of snapshots
python3 make_video.py RUN_DIR hotfire.mp4 out/aerospike-explainer.mp4
```

`make_video.py` handles the rest:

* It renders the fields (exhaust fraction × temperature, with a schlieren layer) and draws
  the engine outline from `geometry.py`.
* It colours the flame from the footage on screen. The flame pixels of the current
  hot-fire frame are sorted by brightness and mapped onto the sim intensity, saturation
  is restored, and the palette is smoothed over time. Ignition comes out warm, the
  low-flow phase violet-pink and full flow blue-white, as in the real fire.
* It sets all type in Jost (OFL, see `fonts/`).
* It rotates and crops the hot-fire footage so its plume axis is horizontal like the sim.
* It mixes the audio: a synthetic rumble driven by the simulated chamber pressure in
  part 1, then the hot fire's own sound, synced to the footage.
