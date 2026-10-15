# Island Three — an O'Neill cylinder from explicit formulas

A reconstruction of the interior of an Island Three habitat, drawn the way
Hamid Naderi Yeganeh draws: every mark on the canvas is a sample of a
closed-form family of curves indexed by an integer `k`, with the colour and
the weight of each sample given by formulas in `(k, t)` as well. There is no
bitmap source, no tracing, no brush and no noise texture. The shading is the
accumulated density of the lines; the only mark not made by a curve is the
flat sky.

The subject follows Rick Guidice's 1970s NASA painting of an Island Three
colony — three valley strips alternating with three window strips, the solar
mirror and the sun seen through one window, the Moon and a neighbouring
habitat through another, a lake and a river in the valley underfoot.

Nothing is copied from the painting. What is taken from it is a handful of
*measurements*, written into the code as constants: the six sector angles,
the position of the vanishing point, the places of the sun, the Moon, the
sister hull and the lake, and the palette.

## Files

| file | what it is |
|---|---|
| `island3.py` | projection, the canvas, the irradiance, haze and tone models |
| `scene.py` | the eleven curve families that make the picture |
| `sheet.py` | typesets the formula sheet |
| `plate.py` | stacks picture over sheet |
| `art.png` | the picture alone, 2048 × 1613 |
| `sheet.png` | the formula sheet alone |
| `island-three.png` | the finished plate |

## Running it

Needs `numpy`, `pillow` and `matplotlib`.

```
python3 scene.py && python3 sheet.py && python3 plate.py
```

About 50 s for the picture; roughly 30 million curve samples are deposited.
`ISLAND3_ONLY=land,cloud python3 scene.py` draws a subset of the families,
which is how each one was tuned. The names are `sky sun moon cap land woods
cloud mull`.

## The three things worth knowing

**Projection.** The habitat is the cylinder `x² + y² = 1` with axis `z`. The
eye sits at `(0, −e, 0)`, `e = 0.62`, pitched down by `B = 0.22` rad, so a
point at angle `T`, axial distance `Z` and radius `R` lands at

```
w = (R cos T − e) sin B + Z cos B
P = ( R sin T / w ,  ((e − R cos T) cos B + Z sin B) / w − tan B )
```

**Fitting the plate.** A line of constant `T` leaves the vanishing point at
screen angle `θ(T) = atan2((e − cos T)/cos B, sin T)`. Measured off the
painting, the six sector edges sit at −16°, 25.5°, 67.5°, 112.5°, 154.5° and
196°; the pair `(e, W_L) = (0.62, 1.257)` reproduces all six to within five
degrees, which is as close as a 1970s gouache gets to being consistent. That
one fit is what puts the near valley across the whole bottom of the frame and
the sun straight above the hub.

**Amplitude.** For a family `P(k, t)` that sweeps out a surface, one sample
owns `|∂P/∂k × ∂P/∂t|` square pixels — the Jacobian — so depositing
`colour × that area` lays down exactly that colour, no matter how densely the
family happens to be sampled. Guessing the spacing instead (`1/Z` for a
converging family, say) is what turns the vanishing point into a white ball,
and it also quietly makes the foreground three or four times too bright. For
families that are not surfaces — scattered canopies, cloud ribbons — the
Jacobian is taken across the ribs of a single object and never between one
object and the next.

## Tone

The accumulated energy is rolled off as `m ↦ m / (1 + m³)^(1/3)` applied to
the *largest* of the three channels, with the other two scaled to match. A
per-channel curve lifts the weak channel far more than the strong one, which
is what turns the deep greens of the valley into the milky olive of an
over-exposed photograph.
