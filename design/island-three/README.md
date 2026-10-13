# Island Three — an O'Neill cylinder from explicit formulas

A reconstruction of the interior of an Island Three habitat, drawn the way
Hamid Naderi Yeganeh draws: every mark on the canvas is a sample of a
closed-form family of curves indexed by an integer `k`. There is no bitmap
source, no tracing, no brush and no noise texture. The shading is the
accumulated density of the lines; the only mark not made by a curve is the
flat background colour.

The subject follows Rick Guidice's 1970s NASA painting of an Island Three
colony — three valley strips alternating with three window strips, the sun
seen through one window, the Moon and a neighbouring habitat through another.

## Files

| file | what it is |
|---|---|
| `island3.py` | projection, the canvas, the irradiance and haze models |
| `scene.py` | the eleven curve families that make the picture |
| `sheet.py` | typesets the formula sheet |
| `plate.py` | stacks picture over sheet |
| `art.png` | the picture alone, 2048 × 1560 |
| `sheet.png` | the formula sheet alone |
| `island-three.png` | the finished plate, 2048 × 2830 |

## Running it

Needs `numpy`, `pillow` and `matplotlib`.

```
python3 scene.py && python3 sheet.py && python3 plate.py
```

About 25 s for the picture; roughly 11 million curve samples are deposited.

## The two things worth knowing

**Projection.** The habitat is the cylinder `x² + y² = 1` with axis `z`. The
eye sits at `(0, −0.62, 0)`, pitched down by 0.22 rad and rolled by 0.05, so a
point at angle `T`, axial distance `Z` and radius `R` lands at

```
w  = (R cos T − e) sin B + Z cos B
x₀ = R sin T / w
y₀ = ((e − R cos T) cos B + Z sin B) / w
```

followed by the roll about the axis vanishing point `(0, tan B)`.

**Amplitude.** Energy deposited per square pixel is `A / (δ · Δ)`, where `δ`
is the spacing between samples along a curve and `Δ` the spacing between
neighbouring curves of the family. Neighbouring curves of a family converging
on the vanishing point sit `1/Z` apart, so each sample must carry
`A = c · δ / Z`. Getting this backwards is what turns the vanishing point into
a white ball — every converging family dumps its samples into a handful of
pixels.
