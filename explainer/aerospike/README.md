# How an aerospike starts: explainer video

A 9:16 explainer (1080×1920, 30 fps, ~28 s) on how an aerospike engine works.
It follows the same scene structure as the "How a Raptor engine starts"
bell-nozzle reference:

1. **Simulation, full frame** (0–9.6 s): a close-up of the engine start-up with a
   title, captions, a T+ clock with a slow-motion factor, live stats (thrust,
   exit Mach, chamber temperature, Pc) and chamber sparklines.
2. **Simulation vs. real** (10.3–26.9 s): the same start-up, zoomed out, above a real
   LEAP 71 aerospike hot fire, with annotations (lip expansion, plume on the spike,
   base wake, shock cells, the plume opening). The sim then lowers the ambient pressure
   to show altitude compensation.
3. **Loop**: a fade back to the first frame so the clip loops.

Output: `out/aerospike-explainer.mp4`

## Engine data (leap71.com)

LEAP 71 calls the 200 kN aerospike **XRA-2E5**. Sources:

| Fact | Source |
|---|---|
| XRA-2E5, 200 kN (20 t, 45,000 lbf), one metre tall, cryogenic methane / LOX | leap71.com/2026/03/12/hbdxleap71tctshanghai2026/ |
| Regenerative cooling: methane cools the outer chamber, LOX cools the spike | same |
| One monolithic Inconel 718 part, printed by HBD on an HBD 800 in 289 h | same |
| "Inside-out" layout: toroidal combustion chamber and central spike | same |
| Built for upper stages; 5 × 200 kN on the Aspire Space Oryx orbital stage | leap71.com/2025/11/19/… (Aspire Space agreement) |
| No XRA-2E5 hot fire reported yet ("ready to move toward hot-fire qualification") | 2026/03/12 article |
| The 20 kN methalox Noyron aerospike reached full chamber pressure, 50 bar | leap71.com/2025/12/11/… |

LEAP 71 publishes no chamber pressure, Isp, expansion ratio or contour for the
XRA-2E5. The video uses these assumptions, and the credits say so:

* **Pc = 50 bar**, taken from the 20 kN sibling engine.
* **Thrust is scaled** so that the post-climb (near-vacuum) value equals the rated 200 kN.
* **Engine geometry is traced from the XRA-2E5 turntable render**
  (`Aspire_engine_turntable_4K.mp4`). Measured in units of the spike root radius:
  * the spike leaves the flat bottom face of a turned ring (r ≈ 1.8), below a flange
    (≈ 2.1) and the main body (≈ 2.3, inside the lattice skin);
  * it is gently concave, about 29° at the root, 2.06 long, and truncated at r ≈ 0.27.

  The inside of the engine is not visible, so the internal layout is an assumption:
  a toroidal chamber, and an annular slot whose throat sits just inside the ring and
  then expands slightly to the ring face (area ratio about 8.7).

The hot-fire footage is from LEAP 71's own reel (@leap.71). It shows an earlier
Noyron aerospike, not the XRA-2E5, and the video labels it that way.

## Simulation

`euler.c` is a 2D axisymmetric Euler finite-volume solver:

* MUSCL (minmod) reconstruction with HLLC fluxes and SSP-RK2 time stepping.
* Stair-step slip walls.
* A single perfect gas (γ = 1.2) plus a passive scalar that marks exhaust vs. air.
* Grid: 1438 × 450 cells (Δ = 0.008 × spike root radius).

The chamber is fed by a thin "injector" region forced to the stagnation state (ramped
to 50 bar, ~3,400 K). Ambient air is 1 atm and 300 K. From t = 4.8 to 6.8 the
far-field pressure ramps down to 0.03 atm to imitate the climb out of the atmosphere.

```
gcc -O3 -march=native -fopenmp -o euler euler.c -lm
python3 setup_case.py RUN_DIR            # params.txt + flags.u8 (geometry mask)
./euler RUN_DIR                           # ~35 min on 4 cores, ~5 GB of snapshots
python3 make_video.py RUN_DIR hotfire.mp4 out/aerospike-explainer.mp4
```

`make_video.py` handles the rest:

* It renders the fields (exhaust fraction × temperature, with a schlieren layer)
  in a violet palette and draws the engine outline from `geometry.py`.
* It sets the type: Source Serif 4, IBM Plex Mono and Inter (OFL, see `fonts/`).
* It rotates and crops the hot-fire footage so its plume axis is horizontal like the sim.
* It mixes the audio: a synthetic rumble driven by the simulated chamber pressure in
  part 1, then the hot fire's own sound.
