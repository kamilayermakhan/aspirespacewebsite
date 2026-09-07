# HIMOYA: Matrilineal Energies, Oracular Rites — post spec

Reverse-engineered from `ScreenRecording_09072026_73919AM_1.mov`
(1320×2868, 60 fps, 10.96 s).

Figma: page **04 · HIMOYA** in `p1WKqeO5MwCVKGUlbHh6eI`.

> **The recording stops before the animation finishes.** Mean frame brightness
> is still climbing at 10.96 s (47.9 → 57.9, decelerating), and `MATRILINEAL`
> and `15/10` are still fading up. Everything after ≈11 s in the spec below is
> extrapolation from the curve, not measurement. A longer capture would let the
> tail be corrected.

## Structure

```
Post · HIMOYA — ANIMATED (13s build)   1080×1920, #4D1828
├── art · ornament (tree of life)      full-bleed 2-colour image
├── date · 15/10  + FROM + 2026
├── date · 04/04  + TO + 2027
├── venue · Tselinny                   right-aligned, 4 lines
├── letter · H I M O Y A               six separate nodes, six sizes
├── 20 × name · …                      centred blocks (top / cascade / lower-left / lower-right)
├── credit · curator
└── title · MATRILINEAL / ENERGIES, / ORACULAR RITES
```

## Coordinates

Measured in reel space (1320 wide, rows 273…2620) and converted with
`X = x_reel * 0.81818`, `Y = y_reel * 0.81818` — the poster is full-bleed, so
there is no pan offset as there is on the Akerman post.

## Colour — sampled, all three are flat

| role | hex | note |
|---|---|---|
| ground | `#4D1828` | constant across the whole recording |
| ornament | `#6D2A3C` | reaches this by t=3.0 s and holds |
| all type | `#DC4554` | every element converges on this: 15/10 (219,70,85), 04/04 (221,68,82), H (220,67,82), A (219,69,83), names (208,68,84) |

The poster is deliberately low-contrast; the brightness rise through the
recording is elements *appearing*, not elements *brightening*.

## Type substitutions

| original | used |
|---|---|
| high-contrast didone (dates, H I M O Y A) | Playfair Display Regular |
| thin geometric sans (names, titles, labels) | Jost Light |

## Ornament

`assets/ornament.png` — 360×640, 2-colour indexed PNG, 7 KB.

Extracted from the last frame by:
1. per-row adaptive threshold (`row − 25th percentile`), form = `12 ≤ d ≤ 34`,
   type = `d > 34`;
2. every type pixel and every Instagram-UI region replaced by its mirror across
   the symmetry axis (found at x=643 by maximising self-agreement of the flip);
3. what is unknown on *both* sides filled by a 25 px closing;
4. 5 px median despeckle, then symmetry forced with `mask | flip(mask)`.

Rows below reel y=2010 sit under the Instagram caption overlay in every frame,
so they are set to ground rather than guessed.

## Motion — one OPACITY track per layer, timeline 13 s

Onsets were measured as the per-region contrast (std) rise in the recording:
ornament and names from ~0.5 s, `04/04` and the letters from ~3.4 s, `15/10`
from ~7.5 s, `MATRILINEAL` from ~6.5 s.

| layer | 0 → 1 |
|---|---|
| ornament | 0.3 → 3.2 |
| venue block | 0.4 → 4.4 (linear) |
| names, top | 0.5 → 1.7 and 0.8 → 2.0 |
| names, centre cascade (9 pairs) | 0.6 → 1.8, stagger +0.3 |
| names, lower right (6) | 4.0 → 5.6, stagger +0.5 |
| names, lower left (3) | 4.4 → 6.0, stagger +0.4 |
| H I M O Y A | 3.4 → 0.55 at +0.8 s, hold to 6.5, → 1 at 8.4…9.4 (stagger +0.3/+0.2) |
| 04/04 + TO + 2027 | 3.5 → 0.5 at 5.0, hold to 8.5, → 1 at 11.0 |
| CURATOR | 4.0 → 6.0 |
| MATRILINEAL / ENERGIES, / ORACULAR RITES | 6.5 → 10.5 / 7.2 → 11.2 / 7.9 → 11.9 |
| 15/10 + FROM + 2026 | 7.5 → 11.5 |

The two-stage shape on the letters and on `04/04` (rise, hold at ~half, resolve)
is what the recording shows, not a stylisation.
