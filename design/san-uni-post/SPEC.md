# San Üni — artist announcement post

Specification reverse-engineered from a screen recording of the published
Instagram carousel, and rebuilt as an editable Figma file.

**Figma:** https://www.figma.com/design/p1WKqeO5MwCVKGUlbHh6eI

## Format

Canvas **1080 × 1440** (3:4, Instagram native). The source frame measured
1320 × 1760 in the recording — exactly 3:4 — so every measurement below was
taken there and scaled by 1080/1320.

The post is animated: it cycles between a full-colour state and a 1-bit
dithered state. Both are built as separate artboards.

## Colour

| Token | Hex | Use |
| --- | --- | --- |
| Acid green | `#9BFF81` | Colour-state ground |
| Mint | `#D9EAD3` | Dither-state ground |
| Ink | `#0D0B0C` | All type, all 1-bit art |
| White | `#FFFFFF` | Bloom behind the dithered art and type |

The corner ornament is an iridescent magenta→purple→cyan texture; it is kept
as a raster because a flat gradient loses the vertical striation.

## Type

| Role | Face | Notes |
| --- | --- | --- |
| Title, date | **Doto ExtraBold** | Dot-matrix. Title fits to 389 px wide (cap ≈72 px); date to 292 px. |
| Artist wordmark | **Pixelify Sans Bold** | Fits to 290 px wide. |
| Bio | **Tektur Bold** | 31.7 px / 32.1 px leading, centred, five hand-broken lines. |

All three are Google Fonts, so the file opens with live type for anyone.
They are close matches, not the originals — the source appears to use a
commercial square-techno face for the bio (Eurostile/Neuropol family).

## Layout (canvas px)

| Element | x | y | w | h |
| --- | --- | --- | --- | --- |
| Ornament corner L | 0 | 0 | 335 | 691 |
| Ornament corner R | 745 | 0 | 335 | 691 |
| Title “San  Üni” | 346 | 60 | 389 | 97 |
| Portrait halo | 187 | 195 | 715 | 666 |
| Tamga L (ring ø92, stroke 10) | 8 | 650 | 152 | 150 |
| Tamga R (ring ø91, stroke 10) | 918 | 650 | 160 | 158 |
| Wordmark | 395 | 925 | 290 | 97 |
| Bio block (5 lines) | 40 | 1094 | 1000 | 161 |
| Date | 394 | 1352 | 292 | 49 |

The ornament crops overlap the portrait region; in both the source and the
rebuild the portrait sits on top and masks that overlap.

## Motion

The post is a loop, not a still. Measured off the recording frame by frame:

The source plays at **~17 fps** (84 unique frames across 4.88 s), so the whole
thing reads chunky rather than smooth. **Nothing crossfades** — every state
change is a hard cut, which is why the Figma keyframes use `HOLD` easing.

| Phase | From | To | What happens |
| --- | --- | --- | --- |
| Dither hold | 0.00 s | 1.70 s | Four 1-bit noise frames round-robin every 0.17 s. The portrait silhouette stays put; only the speckle reshuffles. |
| Cut in | 1.70 s | — | Hard flip to colour. The source steps through three progressively finer dither passes over ~0.13 s first. |
| Colour hold | 1.70 s | 3.27 s | Essentially static. |
| Cut out | 3.27 s | — | Loop point — hard flip back to dither. |

Loop length **3.27 s**.

Built on the `Post · orange — ANIMATED` artboard: the colour state sits over
the dither state and its `OPACITY` is keyframed 0 → 1 at 1.70 s with `HOLD`.
Each noise layer carries its own `HOLD` opacity track so exactly one is visible
per 0.17 s slot — they blend `MULTIPLY`, so overlapping layers would compound
into the union of their black pixels.

`assets/dither_0..3.png` are the four noise frames, lifted from t = 0.28, 0.37,
0.88 and 1.48 s. They were picked by maximising the minimum pairwise difference
across eighteen candidates, so no two read as the same shuffle.

## Assets

`assets/` holds the elements that could not be rebuilt as vectors, extracted
from the recording and chroma-keyed or background-baked as noted:

- `orn_tl.jpg`, `orn_tr.jpg` — corner ornaments, green ground baked in
- `portrait.jpg` — artist portrait with its glitch halo, green ground baked in
- `dither_0.png` … `dither_3.png` — the four 1-bit noise frames of the loop
  (black on white, multiplied in Figma)

Because the baked-in green quantises slightly darker than `#9BFF81`, each
raster carries an additive correction fill in Figma (`LINEAR_DODGE`,
`rgb(8,15,4)` for the ornaments, `rgb(8,13,3)` for the portrait) so the ground
matches the artboard exactly.

The tamga symbols were redrawn as native Figma vectors rather than kept as
raster — they are simple ring-and-cross geometry and are cleaner editable.

`reference/` holds the two full source frames for side-by-side checking.

## Template

`Artist post · 3:4 template` on the Posts page is a component. Per artist,
swap the photo slot, the wordmark, the bio (break the lines by hand — the
source does) and the date. Everything else is fixed furniture.
