"""Aerospike half-section after the corrected scheme ("Gas flow and cooling", LEAP 71 20 kN
methalox), sized to the hot-fired engine.

x = engine axis (flow goes +x), r = radius, units of L0 (3.54 cm, L0_M). The polygon below
is the metal; the gas cavity (ring chamber + annular passage) is a slit in it. The same
polygon drives the solver mask (setup_case.py) and the drawing (make_video.py).

How it works, as in the scheme:
  * ring (toroidal) combustion chamber at the head end; the injector is its head face,
    where methane and oxygen enter
  * the hot gas leaves the chamber as an annular stream through a converging passage
    between the outer shell and the central body, and exits at the lip
  * outside, the annular flow wraps the long, slender central body and converges into an
    axial jet past its tip
  * cooling channels are inside the walls, the hot gas is outside them: methane in the
    outer shell, oxygen in the central body (cooling.py)

Sizes: body 0.29 m across (LEAP 71's photo, next to the 1 m XRA-2E5); chamber, passage
and central body in the proportions of the scheme; the throat is sized so that 50 bar
gives about 20 kN (A_t ~2.4 L0^2). The scheme turns the flow ~40 deg inward at the lip;
here it is 62 deg, because with Pc/pa ~46 the external expansion at the lip turns the
outer boundary ~63 deg outward, and only a steep throat keeps it heading inward at sea
level, as on the stand (see README).
"""
import numpy as np

L0_M = 0.0354

# ------------------------------------------------------------------ outer shell
X_HEAD = -1.20         # flat head face
R_MAX = 4.10
R_HEAD_CORNER = 0.30
X_SH = 1.77            # shoulder starts (end of the flat top)
X_LIP = 3.57           # lip (end of the outer shell)
R_LIP_OUT = 2.62       # outer edge of the lip face
R_LIP = 2.25           # inner edge of the lip = outer wall of the throat (about half the body radius)

# ------------------------------------------------------------------ ring chamber
CH_X0, CH_X1 = -0.35, 1.45     # injector face .. start of the passage
CH_R0, CH_R1 = 2.55, 3.45      # inner .. outer wall
CH_RC = 0.22                   # corner radius at the injector end
INJ_DEPTH = 0.15               # reservoir cells next to the injector face

# ------------------------------------------------------------------ annular passage and throat
GAM = 1.2
A_T_TARGET = 2.35              # throat area for ~20 kN at ~46 bar (L0^2)


def area_ratio(M, g=GAM):
    return (1 / M) * ((2 / (g + 1)) * (1 + (g - 1) / 2 * M * M)) ** ((g + 1) / (2 * (g - 1)))


def prandtl_meyer(M, g=GAM):
    a = np.sqrt((g + 1) / (g - 1)); b = np.sqrt(np.maximum(M * M - 1, 0))
    return a * np.arctan(b / a) - np.arctan(b)


def mach_from_area(eps):
    lo, hi = 1.0, 20.0
    for _ in range(200):
        m = 0.5 * (lo + hi)
        if area_ratio(m) < eps: lo = m
        else: hi = m
    return 0.5 * (lo + hi)


EPS_E = np.pi * R_LIP ** 2 / A_T_TARGET    # ~6.8: full expansion to 1 atm at ~46 bar
M_E = mach_from_area(EPS_E)                # ~3.0
NU_E = prandtl_meyer(M_E)                  # ~64 deg
THETA = NU_E                               # ideal aerospike: throat turned by nu_e
D = np.array([np.cos(THETA), -np.sin(THETA)])
N = np.array([np.sin(THETA), np.cos(THETA)])
_rt2 = R_LIP ** 2 * (1 - np.cos(NU_E) / EPS_E)          # Angelino throat inner point
W_THR = 0.5 * np.hypot(R_LIP - np.sqrt(_rt2), (R_LIP - np.sqrt(_rt2)) / np.tan(np.pi / 2 - THETA))
E = np.array([X_LIP, R_LIP]) - W_THR * N        # throat centre
X_T, R_T = E - W_THR * N                        # throat inner point
_C0 = np.array([CH_X1, 0.5 * (CH_R0 + CH_R1)])
_W0 = 0.5 * (CH_R1 - CH_R0)


def _bez(u):
    L = np.linalg.norm(E - _C0)
    b0, b3 = _C0, E
    b1 = _C0 + np.array([0.48 * L, 0.0])
    b2 = E - D * 0.42 * L
    u = np.asarray(u, float)[..., None]
    return (1 - u) ** 3 * b0 + 3 * (1 - u) ** 2 * u * b1 + 3 * (1 - u) * u ** 2 * b2 + u ** 3 * b3


def _bez_t(u):
    du = 1e-4
    t = (_bez(np.minimum(u + du, 1)) - _bez(np.maximum(u - du, 0)))
    return t / np.linalg.norm(t, axis=-1, keepdims=True)


def halfw(u):
    u = np.asarray(u, float)
    sm = u * u * (3 - 2 * u)
    return W_THR + (_W0 - W_THR) * (1 - sm)


def _wall_curve(p0, p3, n, k1=0.45, k2=0.40):
    L = np.linalg.norm(p3 - p0)
    b1 = p0 + np.array([k1 * L, 0.0]); b2 = p3 - D * k2 * L
    u = np.linspace(0, 1, n)[:, None]
    return (1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * b1 + 3 * (1 - u) * u ** 2 * b2 + u ** 3 * p3


def passage_walls(n=120):
    """Outer and inner walls of the annular passage (chamber end -> throat) and their mid-line.
    Both leave the chamber level and arrive at the throat along the throat direction."""
    outer = _wall_curve(np.array([CH_X1, CH_R1]), np.array([X_LIP, R_LIP]), n)
    inner = _wall_curve(np.array([CH_X1, CH_R0]), np.array([X_T, R_T]), n, 0.55, 0.18)
    return outer, inner, 0.5 * (outer + inner)


# ------------------------------------------------------------------ central body (outside part)
R_TRUNC = 0.25         # the slender central body is truncated here


def _central_body():
    """Ideal (Angelino) plug for full expansion at the lip's design Mach, truncated:
    every Mach line from the lip carries the isentropic area, so the annular flow expands
    along the central body and converges towards the axis."""
    Ms = np.linspace(1.0, M_E, 4000)
    a = NU_E - prandtl_meyer(Ms) + np.arcsin(1 / Ms)
    r = R_LIP * np.sqrt(np.clip(1 - area_ratio(Ms) * Ms * np.sin(a) / EPS_E, 0, None))
    x = X_LIP + (R_LIP - r) / np.tan(a)
    keep = r >= R_TRUNC
    x, r = x[keep], r[keep]
    xf = np.linspace(x[0], x[-1], 900)
    rf = np.interp(xf, x, r)
    return xf, rf


SPIKE_X, SPIKE_R = _central_body()
X_SPIKE_END = SPIKE_X[-1]
R_BASE = SPIKE_R[-1]
A_THROAT = 2 * np.pi * E[1] * 2 * W_THR
X_BACK = X_HEAD


def r_spike(x):
    return np.interp(x, SPIKE_X, SPIKE_R, left=R_T, right=R_BASE)


def shoulder(n=60):
    a = np.linspace(np.pi / 2, 0, n)
    return np.stack([X_SH + (X_LIP - X_SH) * np.cos(a), R_LIP_OUT + (R_MAX - R_LIP_OUT) * np.sin(a)], 1)


def outer_surface():
    """Outer surface of the shell: head face corner, flat top, shoulder down to the lip."""
    a = np.linspace(np.pi, np.pi / 2, 16)
    corner = np.stack([X_HEAD + R_HEAD_CORNER + R_HEAD_CORNER * np.cos(a),
                       R_MAX - R_HEAD_CORNER + R_HEAD_CORNER * np.sin(a)], 1)
    top = np.stack([np.linspace(X_HEAD + R_HEAD_CORNER, X_SH, 30), np.full(30, R_MAX)], 1)
    return np.concatenate([[[X_HEAD, 0.0], [X_HEAD, R_MAX - R_HEAD_CORNER]], corner[1:], top[1:], shoulder()[1:]])


def chamber_head():
    """Injector end of the ring chamber (rounded corners), outer wall -> inner wall."""
    a1 = np.linspace(np.pi / 2, np.pi, 12)
    top = np.stack([CH_X0 + CH_RC + CH_RC * np.cos(a1), CH_R1 - CH_RC + CH_RC * np.sin(a1)], 1)
    a2 = np.linspace(np.pi, 1.5 * np.pi, 12)
    bot = np.stack([CH_X0 + CH_RC + CH_RC * np.cos(a2), CH_R0 + CH_RC + CH_RC * np.sin(a2)], 1)
    return np.concatenate([[[CH_X1, CH_R1]], top, bot, [[CH_X1, CH_R0]]])


def outline():
    """Closed polygon (x, r) of the metal half-section; the gas cavity is a slit in it."""
    outer_w, inner_w, _ = passage_walls()
    pts = outer_surface().tolist()
    pts.append([X_LIP, R_LIP + 0.002])
    pts += outer_w[::-1].tolist()                  # passage outer wall: throat -> chamber
    pts += chamber_head().tolist()                 # chamber outer wall, injector face, inner wall
    pts += inner_w.tolist()                        # passage inner wall: chamber -> throat
    pts += np.stack([SPIKE_X, SPIKE_R], 1)[1::3].tolist()
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


def solid(x, r):
    return in_polygon(x, r)


def in_chamber(x, r):
    x = np.asarray(x, float); r = np.asarray(r, float)
    return (x >= CH_X0) & (x <= CH_X1) & (r >= CH_R0) & (r <= CH_R1) & ~solid(x, r)


def reservoir(x, r):
    return in_chamber(x, r) & (np.asarray(x) < CH_X0 + INJ_DEPTH)


def chamber_probe(x, r):
    return in_chamber(x, r) & (np.asarray(x) >= CH_X0 + INJ_DEPTH + 0.10)


if __name__ == "__main__":
    print(f"throat centre ({E[0]:.3f},{E[1]:.3f}), inner ({X_T:.3f},{R_T:.3f}); tip x={X_SPIKE_END:.2f} "
          f"r={R_BASE:.2f}; A_t={A_THROAT:.3f} ({A_THROAT * L0_M ** 2 * 1e4:.1f} cm^2); body dia {2 * R_MAX * L0_M:.3f} m; "
          f"length head->tip {(X_SPIKE_END - X_HEAD) * L0_M:.3f} m")
    F_est = 1.5 * 46e5 * A_THROAT * L0_M ** 2
    print(f"thrust estimate at 46 bar (C_F ~1.5): {F_est / 1e3:.1f} kN")
