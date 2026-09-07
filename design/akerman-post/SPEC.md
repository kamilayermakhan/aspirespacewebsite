# In-Betweens: Chantal Akerman Retrospective — post spec

Reverse-engineered from `ScreenRecording_09072026_73853AM_1.mp4`
(1320×2868, 60 fps, 6.67 s — one and a bit loops of the reel).

Figma: page **03 · Akerman** in `p1WKqeO5MwCVKGUlbHh6eI`.

## Structure

```
Post · Akerman — ANIMATED (5.5s loop)   1080×1920, clipsContent, #E5E5E5
└── poster · 1900 wide (pans)           2000×1920 at x=-300   ← the animated layer
    ├── txt · curated by                Inter Bold
    ├── txt · film titles (grey column) Inter Medium 60.5 / 63.7
    ├── txt · 19 — 21/12                Inter Regular 190
    ├── mono · … (9 Kazakh parentheticals)  PT Mono 26 / 29
    ├── logo · CINEMATEK / CHANTAL AKERMAN / FOUNDATION / EMBASSY OF BELGIUM
    ├── logo · Tselinny mark            image, MULTIPLY
    ├── logo · Belgium crest            image, MULTIPLY
    ├── img · Jeanne Dielman film still 450×257
    ├── txt · In-Betweens:              Inter Regular 160
    ├── txt · Chantal / Akerman         Tinos Regular 147.8
    └── txt · Retrospective             Inter Regular 160
```

## Coordinates

Everything was measured in the reel's own pixel space (1320 wide, rows 273…2620
of the recording = the 9:16 reel area). Two conversions were used:

```
X_poster = x_reel * 0.81818 + 300      # +300 = the poster's left margin
Y_poster = (y_reel - 273) * 0.81818
```

The viewport therefore shows poster columns 300…1380 at rest.

## Colour

| role | hex |
|---|---|
| ground | `#E5E5E5` |
| display + body black | `#151515` |
| film-title column | `#BABABA` |
| Kazakh mono | `#9E9E9E` |
| CAF "FOUNDATION" | `#778894` |

## Type substitutions

The originals are a Helvetica-family grotesk, a Times-family serif and a
Courier-family mono. Figma equivalents used:

| original | used |
|---|---|
| Helvetica Neue | Inter (Regular / Medium / Bold) |
| Times | Tinos |
| Courier (with Kazakh) | PT Mono — chosen for full Kazakh Cyrillic coverage. The mono in the original itself falls back to a condensed face for `жағалауы`, `ман` etc. |

## Motion — measured, not invented

Tracked two independent ways (1-D ink-column correlation over the whole frame,
and 2-D normalised cross-correlation of the "Chantal Akerman" block). Both agree
the poster is a **pure horizontal translation** — no zoom until the very end.

Loop = **5.5 s**. Values below are in 1080-space; the recording's own numbers
were ×(1080/1320)·3 from the 440-wide analysis frames.

| t (s) | TRANSLATION_X | OPACITY | SCALE_XY |
|---|---|---|---|
| 0.00 | −491 | 0 | 1 |
| 0.45 | −307 | 0.34 | 1 |
| 0.90 | −177 | 0.70 | 1 |
| 1.35 | −61 | 0.95 | 1 |
| 1.85 | 0 (ease out) | 1 | 1 |
| 3.00 | 0 | 1 | 1 |
| 3.60 | +37 | 1 | 1 |
| 3.90 | +79 | 0.93 | 1 |
| 4.25 | — | 0.40 | — |
| 4.45 | +187 | — | — |
| 4.60 | — | 0 | — |
| 5.50 | +345 | 0 | 0.87 |

Total travel −491 → +345 = 836 px, which is why the poster canvas is 2000 px
wide for a 1080 px window.

## Assets

| file | source crop (reel px) | placed at |
|---|---|---|
| `assets/film_still.jpg` | 386,1423 → 936,1737 | 450×257 |
| `assets/logo_tselinny.png` | 1063,958 → 1264,1074 (1-bit) | MULTIPLY |
| `assets/logo_embassy_crest.jpg` | 1067,1278 → 1178,1390 | MULTIPLY |
