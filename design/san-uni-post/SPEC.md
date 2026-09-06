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

## Assets

`assets/` holds the elements that could not be rebuilt as vectors, extracted
from the recording and chroma-keyed or background-baked as noted:

- `orn_tl.jpg`, `orn_tr.jpg` — corner ornaments, green ground baked in
- `portrait.jpg` — artist portrait with its glitch halo, green ground baked in
- `dither.png` — the 1-bit dither layer (black on white, multiplied in Figma)

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
