"""Aerospike half-section modelled on LEAP 71's hot-fired 20 kN methalox engine.

Lengths are in simulation units L0 = spike root radius (about 3.5 cm on the real
engine, see L0_M).  x = engine axis (flow goes +x), r = radius.  The same polygon
drives the solver mask (setup_case.py) and the outline in the video (make_video.py).

What is taken from LEAP 71's photo of its three Noyron aerospikes (the 20 kN engine
in the middle) and from the hot-fire footage, in units of the spike root radius:
  * an urn-shaped body bulging to ~4.1, with a rounded corner into an almost flat
    bottom; the body is ~0.29 m across next to the 1 m tall XRA-2E5, which sets L0
  * a short, stubby, slightly concave spike: ~20 deg at the root, 1.73 long,
    truncated at r ~0.55
  * the flame leaves the engine as a large bright ring at the bottom corner

What is assumed (the inside is not visible):
  * the annular throat sits at the bottom corner (r ~2.4) and points the flow
    70 deg inward; the almost flat bottom is the steep first part of the spike,
    a fillet turns it into the slender visible spike
  * the toroidal chamber sits in the bulge of the body and feeds the throat
    through a short converging slot
  * the regenerative cooling network is in cooling.py
With 50 bar this throat (A_t ~2.3 L0^2) gives ~20 kN at the real size, so the size,
the chamber pressure and the rated thrust agree.
"""
import numpy as np

L0_M = 0.0354          # metres per unit (body 0.29 m across / 2 / 4.1)

# ------------------------------------------------------------ body (urn shape)
X_LIP = 3.60           # plane of the cowl lip (bottom corner)
R_MAX = 4.10           # bulge just above the bottom corner
R_TOP = 3.30           # narrower towards the injector head (off-screen)
R_CORNER = 2.56        # where the rounded corner meets the lip
X_BULGE = X_LIP - 1.90
X_BACK = -9.0          # body continues upstream out of the domain
X_TAPER = -2.0         # the body tapers from R_TOP here to R_MAX at the bulge

# ------------------------------------------------------------ annular throat
R_LIP = 2.42           # cowl lip = outer edge of the throat
THETA = np.radians(70.0)                         # flow direction, inward from the axis
D = np.array([np.cos(THETA), -np.sin(THETA)])   # along the slot
N = np.array([np.sin(THETA), np.cos(THETA)])    # across the slot (inner -> lip)
W_THR = 0.075          # half-width of the throat (gap 0.15)
L_P = 0.70             # slot length from the chamber to the throat
W_P1 = 0.14            # half-width where the slot leaves the chamber
E = np.array([X_LIP, R_LIP]) - W_THR * N         # throat centre
X_T, R_T = E - W_THR * N                         # throat inner point

# ------------------------------------------------------------ spike
# steep "bottom" (part of the spike contour), fillet, then the measured profile
BOTTOM_ANGLE = np.radians(80.0)
R_FILLET = 0.30
_S = np.array([0.0, 0.27, 0.53, 0.80, 1.07, 1.33, 1.60, 1.73])
_R = np.array([1.00, 0.90, 0.81, 0.74, 0.675, 0.615, 0.565, 0.55])


def _spike_contour():
    th1, th2 = BOTTOM_ANGLE, np.radians(20.0)
    drop_arc = R_FILLET * (np.cos(th2) - np.cos(th1))
    run_arc = R_FILLET * (np.sin(th1) - np.sin(th2))
    r_b = 1.0 + drop_arc                                  # start of the fillet
    x_b = X_T + (R_T - r_b) / np.tan(th1)
    seg = np.stack([np.linspace(X_T, x_b, 30), np.linspace(R_T, r_b, 30)], 1)
    # arc parametrised by the local wall angle th (from the axis), th1 -> th2
    th = np.linspace(th1, th2, 40)
    arc_x = x_b + R_FILLET * (np.sin(th1) - np.sin(th))
    arc_r = r_b - R_FILLET * (np.cos(th) - np.cos(th1))
    x_c, r_c = arc_x[-1], arc_r[-1]
    prof = np.stack([x_c + _S, 1.0 * _R], 1)
    pts = np.concatenate([seg, np.stack([arc_x, arc_r], 1)[1:], prof[1:]])
    xf = np.linspace(pts[0, 0], pts[-1, 0], 800)
    rf = np.interp(xf, pts[:, 0], pts[:, 1])
    return xf, rf, (x_c, r_c)


SPIKE_X, SPIKE_R, ROOT = _spike_contour()
X_SPIKE_END = SPIKE_X[-1]
R_BASE = SPIKE_R[-1]

# ------------------------------------------------------------ toroidal chamber
CH_X, CH_R, CH_AX, CH_AR = X_LIP - 0.62, 3.05, 0.36, 0.30
WALL = 0.12
X_INJ = CH_X - CH_AX + 0.14
_P1 = E - L_P * D

A_THROAT = 2 * np.pi * E[1] * 2 * W_THR
EPS_E = np.pi * R_LIP ** 2 / A_THROAT


def r_spike(x):
    return np.interp(x, SPIKE_X, SPIKE_R, left=R_T, right=R_BASE)


def _pt(s, q):
    return E + s * D + q * N


def _halfw(s):
    u = np.clip(-np.asarray(s, dtype=float) / L_P, 0, 1)
    return W_THR + (W_P1 - W_THR) * u ** 1.4


def _ellipse(a0, a1, n, grow=0.0):
    a = np.linspace(a0, a1, n)
    return np.stack([CH_X + (CH_AX + grow) * np.cos(a), CH_R + (CH_AR + grow) * np.sin(a)], 1)


def _ang(p):
    return np.arctan2((p[1] - CH_R) / CH_AR, (p[0] - CH_X) / CH_AX)


def r_body(x):
    """Outer radius of the body upstream of the bottom corner."""
    x = np.asarray(x, dtype=float)
    t = np.clip((X_BULGE - x) / (X_BULGE - X_TAPER), 0, 1)
    return R_MAX - (R_MAX - R_TOP) * t ** 1.6


def corner(n=40):
    ax, ar = X_LIP - X_BULGE, R_MAX - R_CORNER
    a = np.linspace(np.pi / 2, 0, n)
    return np.stack([X_BULGE + ax * np.cos(a), R_CORNER + ar * np.sin(a)], 1)


def outline():
    """Closed polygon (x, r) of the metal half-section, chamber as a slit."""
    pts = [[X_BACK, 0.0]]
    xs = np.linspace(X_BACK, X_BULGE, 40)
    pts += np.stack([xs, r_body(xs)], 1).tolist()
    pts += corner()[1:].tolist()                               # rounded corner to the lip
    pts.append([X_LIP, R_LIP + 0.004])
    pts += [_pt(s, _halfw(s)).tolist() for s in np.linspace(0, -L_P, 40)]
    p_out = _pt(-L_P, _halfw(-L_P)); p_in = _pt(-L_P, -_halfw(-L_P))
    a0, a1 = _ang(p_out), _ang(p_in)
    if a1 < a0: a1 += 2 * np.pi
    pts += _ellipse(a0, a1, 90)[1:-1].tolist()
    pts += [_pt(s, -_halfw(s)).tolist() for s in np.linspace(-L_P, 0, 40)]
    pts += np.stack([SPIKE_X, SPIKE_R], 1)[1::4].tolist()
    pts += [[X_SPIKE_END, R_BASE], [X_SPIKE_END, 0.0]]
    return np.array(pts)


OUTLINE = outline()


def in_polygon(x, r, poly=OUTLINE):
    x = np.asarray(x, dtype=float); r = np.asarray(r, dtype=float)
    shp = x.shape
    xf, rf = x.ravel(), r.ravel()
    inside = np.zeros(xf.shape, bool)
    P = np.concatenate([poly, (poly * [1, -1])[::-1]])
    x0, y0 = P[:, 0], P[:, 1]
    x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    for k in range(0, xf.size, 100000):
        X = xf[k:k + 100000, None]; Y = rf[k:k + 100000, None]
        cond = (y0 > Y) != (y1 > Y)
        xi = x0 + (Y - y0) * (x1 - x0) / np.where(y1 == y0, 1e-30, y1 - y0)
        inside[k:k + 100000] = (cond & (X < xi)).sum(1) % 2 == 1
    return inside.reshape(shp)


def in_chamber(x, r):
    return ((x - CH_X) / CH_AX) ** 2 + ((r - CH_R) / CH_AR) ** 2 <= 1.0


def solid(x, r):
    return in_polygon(x, r)


def reservoir(x, r):
    return in_chamber(x, r) & (x < X_INJ)


def chamber_probe(x, r):
    return in_chamber(x, r) & (x >= X_INJ + 0.08)


if __name__ == "__main__":
    print(f"throat inner ({X_T:.3f},{R_T:.3f}), root {ROOT[0]:.3f},{ROOT[1]:.3f}; spike end x={X_SPIKE_END:.3f} "
          f"r_base={R_BASE:.3f}; A_t={A_THROAT:.3f} ({A_THROAT * L0_M**2 * 1e4:.1f} cm^2), eps={EPS_E:.2f}; "
          f"P1 in chamber: {in_chamber(*_P1)}; body dia {2 * R_MAX * L0_M:.3f} m")
    F_est = 1.5 * 50e5 * A_THROAT * L0_M ** 2
    print(f"thrust estimate at 50 bar (C_F ~1.5): {F_est / 1e3:.1f} kN")
