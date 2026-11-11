"""Illustrative toroidal-chamber / truncated-spike aerospike geometry.

Lengths are in simulation units L0 (physical scale set in make_video.py).
x = engine axis (flow goes +x), r = radius.  The same analytic description
is used by the solver (cell mask) and by the renderer (outlines).

LEAP 71 has not published the XRA-2E5 contour, so this is a generic
truncated aerospike with the architecture LEAP 71 describes: a toroidal
combustion chamber feeding an annular throat around a central spike.
The spike is an ideal (Angelino) contour truncated at ~25% of the lip
radius; the throat is tilted inward by the Prandtl-Meyer angle nu_e so the
outer jet boundary leaves the cowl lip axially at the design point.
"""
import numpy as np

GAM = 1.2
EPS_E = 10.0           # design area ratio (lip area / throat area)

X_LIP = 3.00           # cowl lip
R_E = 1.80             # lip radius
R_BASE_FRAC = 0.26     # truncation: base radius / lip radius


def area_ratio(M, g=GAM):
    return (1 / M) * ((2 / (g + 1)) * (1 + (g - 1) / 2 * M * M)) ** ((g + 1) / (2 * (g - 1)))


def prandtl_meyer(M, g=GAM):
    a = np.sqrt((g + 1) / (g - 1))
    b = np.sqrt(np.maximum(M * M - 1, 0))
    return a * np.arctan(b / a) - np.arctan(b)


def mach_from_area(eps, g=GAM):
    lo, hi = 1.0, 20.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if area_ratio(mid, g) < eps: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)


M_E = mach_from_area(EPS_E)
NU_E = prandtl_meyer(M_E)

# Angelino contour
_M = np.linspace(1.0, M_E, 4000)
_alpha = NU_E - prandtl_meyer(_M) + np.arcsin(1 / _M)
_r = R_E * np.sqrt(np.clip(1 - area_ratio(_M) * _M * np.sin(_alpha) / EPS_E, 0, None))
_x = X_LIP + (R_E - _r) / np.tan(_alpha)
R_BASE = R_BASE_FRAC * R_E
_k = np.argmax(_r <= R_BASE) if np.any(_r <= R_BASE) else len(_r) - 1
SPIKE_X = _x[: _k + 1]
SPIKE_R = _r[: _k + 1]
X_T, R_T = SPIKE_X[0], SPIKE_R[0]            # throat inner point
X_SPIKE_END = SPIKE_X[-1]
GAP = np.hypot(X_LIP - X_T, R_E - R_T)
FULL_SPIKE_LEN = _x[-1] - X_LIP

D = np.array([np.cos(NU_E), -np.sin(NU_E)])  # flow direction at throat
N = np.array([np.sin(NU_E), np.cos(NU_E)])   # along throat line (inner -> lip)
T = np.array([0.5 * (X_LIP + X_T), 0.5 * (R_E + R_T)])  # throat centre

# feed passage and toroidal chamber (chamber sits radially outside the throat)
L_P = 0.80                     # passage length along -D from throat centre
W_P1 = 0.16                    # passage half-width at chamber end
CH_AX, CH_AR = 0.62, 0.36
_P1 = T - L_P * D
CH_X, CH_R = _P1[0] - 0.12, _P1[1] + 0.16
WALL = 0.13
R_BODY = CH_R + CH_AR + WALL
X_BACK = CH_X - CH_AX - 0.55
X_INJ = CH_X - CH_AX + 0.20


def r_spike(x):
    return np.interp(x, SPIKE_X, SPIKE_R, left=R_T, right=R_BASE)


def _pt(s, q):
    return T + s * D + q * N


def _halfw(s):
    t = np.clip(-s / L_P, 0, 1)
    return GAP / 2 + (W_P1 - GAP / 2) * t ** 1.3


def _ellipse(a0, a1, n, grow=0.0):
    a = np.linspace(a0, a1, n)
    return np.stack([CH_X + (CH_AX + grow) * np.cos(a), CH_R + (CH_AR + grow) * np.sin(a)], 1)


def _ang(p, grow=0.0):
    return np.arctan2((p[1] - CH_R) / (CH_AR + grow), (p[0] - CH_X) / (CH_AX + grow))


def outline():
    """Closed polygon (x, r) of the metal half-section, chamber as a slit."""
    pts = [[X_BACK + 0.25, 0.0]]
    rb = 0.9
    for t in np.linspace(0, 1, 30)[1:]:                       # back plate
        pts.append([X_BACK + 0.25 - 0.25 * t ** 3, t * (R_BODY - rb)])
    c = np.array([X_BACK + rb, R_BODY - rb])
    for a in np.linspace(np.pi, np.pi / 2, 30)[1:]:           # rounded corner
        pts.append([c[0] + rb * np.cos(a), c[1] + rb * np.sin(a)])
    # cowl outer surface: smooth curve from the housing down to the lip
    a_c = -0.55
    P2 = np.array([CH_X + (CH_AX + WALL) * np.cos(a_c), CH_R + (CH_AR + WALL) * np.sin(a_c)])
    P0 = np.array([X_LIP + 0.01, R_E + 0.012])
    P1 = np.array([X_LIP + 0.10, R_E + 0.30])
    t = np.linspace(0, 1, 30)[:, None]
    cowl = ((1 - t) ** 2 * P2 + 2 * (1 - t) * t * P1 + t ** 2 * P0)[:-1]
    pts.extend(_ellipse(np.pi / 2, a_c, 40, WALL)[1:].tolist())   # housing
    pts.extend(cowl.tolist())
    pts.append([X_LIP + 0.01, R_E + 0.012])                   # lip
    pts.append([X_LIP, R_E])
    # passage outer wall up into the chamber, around it, inner wall back down
    pts.extend([_pt(s, _halfw(s)).tolist() for s in np.linspace(0, -L_P, 25)[1:]])
    p_out = _pt(-L_P, _halfw(-L_P))
    p_in = _pt(-L_P, -_halfw(-L_P))
    a0, a1 = _ang(p_out), _ang(p_in)
    if a1 < a0: a1 += 2 * np.pi
    pts.extend(_ellipse(a0, a1, 90)[1:-1].tolist())
    pts.extend([_pt(s, -_halfw(s)).tolist() for s in np.linspace(-L_P, 0, 25)])
    pts.append([X_T, R_T])
    pts.extend(np.stack([SPIKE_X, SPIKE_R], 1)[1::20].tolist())   # spike
    pts.append([X_SPIKE_END, R_BASE])
    pts.append([X_SPIKE_END, 0.0])
    return np.array(pts)


OUTLINE = outline()


def in_polygon(x, r, poly=OUTLINE):
    x = np.asarray(x, dtype=float); r = np.asarray(r, dtype=float)
    shp = x.shape
    xf, rf = x.ravel(), r.ravel()
    inside = np.zeros(xf.shape, bool)
    # symmetric about the axis: test against polygon + mirror so r=0 edge is interior
    P = np.concatenate([poly, (poly * [1, -1])[::-1]])
    x0, y0 = P[:, 0], P[:, 1]
    x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    for k in range(0, xf.size, 200000):
        X = xf[k:k + 200000, None]; Y = rf[k:k + 200000, None]
        cond = (y0 > Y) != (y1 > Y)
        xi = x0 + (Y - y0) * (x1 - x0) / np.where(y1 == y0, 1e-30, y1 - y0)
        inside[k:k + 200000] = (cond & (X < xi)).sum(1) % 2 == 1
    return inside.reshape(shp)


def in_chamber(x, r):
    return ((x - CH_X) / CH_AX) ** 2 + ((r - CH_R) / CH_AR) ** 2 <= 1.0


def solid(x, r):
    return in_polygon(x, r)


def reservoir(x, r):
    return in_chamber(x, r) & (x < X_INJ)


def chamber_probe(x, r):
    return in_chamber(x, r) & (x >= X_INJ + 0.1)


if __name__ == "__main__":
    print(f"Me={M_E:.3f} nu_e={np.degrees(NU_E):.1f} deg gap={GAP:.4f} "
          f"throat inner=({X_T:.3f},{R_T:.3f}) spike end x={X_SPIKE_END:.3f} "
          f"truncation={(X_SPIKE_END - X_LIP) / FULL_SPIKE_LEN:.2f} of full length {FULL_SPIKE_LEN:.2f}")
    print("R_BODY", R_BODY, "X_BACK", X_BACK)
