"""Half-section of LEAP 71's 20 kN methalox aerospike (the middle engine of the three), with
the inside after the corrected scheme ("Gas flow and cooling").

x = engine axis (flow goes +x, the lip plane is x = 0), r = radius, units of L0 (3.54 cm).
The polygon below is the metal; the gas cavity (ring chamber + annular passage) is a slit in
it. The same polygon drives the solver mask (setup_case.py) and the drawing (make_video.py).

Outside, as on LEAP 71's photo of the three engines (body 0.29 m across, next to the 1 m
XRA-2E5): a crown of manifolds at the head, a body that widens towards its bottom, a flat
bottom face with rounded corners, and a short, horn-shaped spike.

Inside, as in the scheme:
  * ring (toroidal) combustion chamber; the injector is its head face, where methane and
    oxygen enter
  * the hot gas leaves the chamber as an annular stream through a converging passage
    between the outer shell and the central body, and exits at the lip
  * outside, the annular flow runs along the short spike and converges into an axial jet
    past its tip
  * cooling channels are inside the walls, the hot gas is outside them: methane in the
    outer shell, oxygen in the central body (cooling.py)

The throat is sized so that ~50 bar gives about 20 kN (A_t ~2.35 L0^2, 29 cm^2). The lip
radius follows the photo (spike ~9 cm across at its root); the ideal contour for it turns
the throat ~45 deg inward, close to the ~40 deg drawn in the scheme.
"""
import numpy as np

L0_M = 0.0354

# ------------------------------------------------------------------ outside (from the photo)
X_CROWN = -9.67        # top of the crown of manifolds
X_HEAD = -9.30         # top of the oxygen inlet on the axis (oxygen enters here)
X_TOPFACE = -8.10      # recessed top face inside the crown
R_INLET = 0.45         # oxygen inlet stub
R_CROWN_IN, R_CROWN = 2.35, 3.10
X_BODY = -7.83         # crown -> body
R_MAX = 4.10
X_LIP = 0.0            # bottom face = lip plane
R_LIP = 1.50           # inner edge of the bottom face = outer wall of the throat
R_BOT_CORNER = 1.05
# body radius along x (photo of the middle engine), the bottom corner is added below
_BODY = np.array([[X_BODY, 3.10], [-6.50, 3.36], [-4.55, 3.65], [-3.20, 3.88], [-1.90, 4.10],
                  [-1.10, 4.07]])

# ------------------------------------------------------------------ ring chamber
CH_X0, CH_X1 = -5.00, -1.70    # injector face .. start of the passage
CH_R0, CH_R1 = 2.20, 3.10      # inner .. outer wall
CH_RC = 0.25                   # corner radius at the injector end
INJ_DEPTH = 0.15               # reservoir cells next to the injector face

# ------------------------------------------------------------------ annular passage and throat
GAM = 1.2
A_T_TARGET = 2.35              # throat area for ~20 kN at ~50 bar (L0^2)


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


EPS_E = np.pi * R_LIP ** 2 / A_T_TARGET    # ~3.0
M_E = mach_from_area(EPS_E)                # ~2.4
NU_E = prandtl_meyer(M_E)                  # ~45 deg
THETA = NU_E                               # ideal aerospike: throat turned by nu_e
D = np.array([np.cos(THETA), -np.sin(THETA)])
N = np.array([np.sin(THETA), np.cos(THETA)])
_rt2 = R_LIP ** 2 * (1 - np.cos(NU_E) / EPS_E)          # Angelino throat inner point
W_THR = 0.5 * np.hypot(R_LIP - np.sqrt(_rt2), (R_LIP - np.sqrt(_rt2)) / np.tan(np.pi / 2 - THETA))
E = np.array([X_LIP, R_LIP]) - W_THR * N        # throat centre
X_T, R_T = E - W_THR * N                        # throat inner point


def _wall_curve(p0, p3, n, k1=0.45, k2=0.40):
    L = np.linalg.norm(p3 - p0)
    b1 = p0 + np.array([k1 * L, 0.0]); b2 = p3 - D * k2 * L
    u = np.linspace(0, 1, n)[:, None]
    return (1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * b1 + 3 * (1 - u) * u ** 2 * b2 + u ** 3 * p3


def passage_walls(n=120):
    """Outer and inner walls of the annular passage (chamber end -> throat) and their mid-line.
    Both leave the chamber level and arrive at the throat along the throat direction."""
    outer = _wall_curve(np.array([CH_X1, CH_R1]), np.array([X_LIP, R_LIP]), n, 0.40, 0.45)
    inner = _wall_curve(np.array([CH_X1, CH_R0]), np.array([X_T, R_T]), n, 0.45, 0.30)
    return outer, inner, 0.5 * (outer + inner)


# ------------------------------------------------------------------ spike (outside part)
R_TRUNC = 0.38         # the spike is truncated here (photo: a short horn)


def _spike():
    """Ideal (Angelino) plug for the lip's design Mach, truncated: every Mach line from the
    lip carries the isentropic area, so the annular flow expands along the spike and turns
    towards the axis."""
    Ms = np.linspace(1.0, M_E, 4000)
    a = NU_E - prandtl_meyer(Ms) + np.arcsin(1 / Ms)
    r = R_LIP * np.sqrt(np.clip(1 - area_ratio(Ms) * Ms * np.sin(a) / EPS_E, 0, None))
    x = X_LIP + (R_LIP - r) / np.tan(a)
    keep = r >= R_TRUNC
    x, r = x[keep], r[keep]
    xf = np.linspace(x[0], x[-1], 600)
    rf = np.interp(xf, x, r)
    return xf, rf


SPIKE_X, SPIKE_R = _spike()
X_SPIKE_END = SPIKE_X[-1]
R_BASE = SPIKE_R[-1]
A_THROAT = 2 * np.pi * E[1] * 2 * W_THR
X_BACK = X_HEAD


def r_spike(x):
    return np.interp(x, SPIKE_X, SPIKE_R, left=R_T, right=R_BASE)


def _body_r(x):
    """Smooth body radius between the photo's points (monotone cubic)."""
    from numpy import interp
    xs, rs = _BODY[:, 0], _BODY[:, 1]
    # Catmull-Rom through the points
    out = np.empty_like(np.asarray(x, float))
    for k, xv in enumerate(np.atleast_1d(x)):
        i = int(np.clip(np.searchsorted(xs, xv) - 1, 0, len(xs) - 2))
        p0 = rs[max(i - 1, 0)]; p1 = rs[i]; p2 = rs[i + 1]; p3 = rs[min(i + 2, len(xs) - 1)]
        u = (xv - xs[i]) / (xs[i + 1] - xs[i])
        out.flat[k] = 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                             + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)
    return out


def shoulder(n=60):
    """Bottom corner and bottom face, from the widest point down to the lip."""
    xc, rc = X_LIP - R_BOT_CORNER, _BODY[-1, 1] - R_BOT_CORNER
    a = np.linspace(np.pi / 2, 0, n)
    arc = np.stack([xc + R_BOT_CORNER * np.cos(a), rc + R_BOT_CORNER * np.sin(a)], 1)
    face = np.stack([np.full(max(n // 2, 4), X_LIP), np.linspace(rc, R_LIP + 0.002, max(n // 2, 4))], 1)
    return np.concatenate([arc, face[1:]])


def crown():
    """Crown of manifolds at the head (section): oxygen inlet on the axis, recessed top face,
    a ring of manifold posts with a V cut in its top."""
    return np.array([[X_HEAD, 0.0], [X_HEAD, R_INLET], [X_TOPFACE, R_INLET], [X_TOPFACE, R_CROWN_IN],
                     [X_CROWN, R_CROWN_IN], [X_CROWN + 0.55, 0.5 * (R_CROWN_IN + R_CROWN)],
                     [X_CROWN, R_CROWN], [X_BODY, R_CROWN]])


def outer_surface():
    """Outer surface: crown, body, bottom corner, bottom face to the lip."""
    xb = np.linspace(X_BODY, _BODY[-1, 0], 60)
    body = np.stack([xb, _body_r(xb)], 1)
    return np.concatenate([crown(), body[1:], shoulder()[1:]])


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
    pts += outer_w[::-1].tolist()                  # passage outer wall: throat -> chamber
    pts += chamber_head().tolist()                 # chamber outer wall, injector face, inner wall
    pts += inner_w.tolist()                        # passage inner wall: chamber -> throat
    pts += np.stack([SPIKE_X, SPIKE_R], 1)[1::2].tolist()
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
    for k in range(0, xf.size, 50000):
        X = xf[k:k + 50000, None]; Y = rf[k:k + 50000, None]
        cond = (y0 > Y) != (y1 > Y)
        xi = x0 + (Y - y0) * (x1 - x0) / np.where(y1 == y0, 1e-30, y1 - y0)
        inside[k:k + 50000] = (cond & (X < xi)).sum(1) % 2 == 1
    return inside.reshape(shp)


def solid(x, r):
    return in_polygon(x, r)


def in_chamber(x, r):
    x = np.asarray(x, float); r = np.asarray(r, float)
    return (x >= CH_X0) & (x <= CH_X1) & (r >= CH_R0) & (r <= CH_R1) & ~solid(x, r)


def in_cavity(x, r):
    """Gas inside the engine: the ring chamber and the annular passage, up to the lip."""
    env = np.concatenate([outer_surface(), [[X_LIP, R_LIP], [X_LIP, 0.0]]])
    x = np.asarray(x, float)
    return in_polygon(x, r, env) & ~solid(x, r) & (x < X_LIP)


def reservoir(x, r):
    return in_chamber(x, r) & (np.asarray(x) < CH_X0 + INJ_DEPTH)


def chamber_probe(x, r):
    return in_chamber(x, r) & (np.asarray(x) >= CH_X0 + INJ_DEPTH + 0.10)


if __name__ == "__main__":
    o, i, _ = passage_walls(400)
    gap = np.array([np.min(np.hypot(*(i - p).T)) for p in o])
    print(f"eps {EPS_E:.2f} Me {M_E:.2f} nu {np.degrees(NU_E):.1f} deg; throat centre ({E[0]:.3f},{E[1]:.3f}), "
          f"inner ({X_T:.3f},{R_T:.3f}); tip x={X_SPIKE_END:.2f} r={R_BASE:.2f}; "
          f"A_t={A_THROAT:.3f} ({A_THROAT * L0_M ** 2 * 1e4:.1f} cm^2); body dia {2 * R_MAX * L0_M:.3f} m; "
          f"length crown->tip {(X_SPIKE_END - X_CROWN) * L0_M:.3f} m")
    print("passage gap along the outer wall (chamber -> throat):", np.round(gap[::40], 3))
    print(f"chamber volume {2 * np.pi * 0.5 * (CH_R0 + CH_R1) * (CH_R1 - CH_R0) * (CH_X1 - CH_X0):.1f} L0^3, "
          f"L* {2 * np.pi * 0.5 * (CH_R0 + CH_R1) * (CH_R1 - CH_R0) * (CH_X1 - CH_X0) / A_THROAT * L0_M:.2f} m")
    print(f"thrust estimate at 50 bar (C_F ~1.45): {1.45 * 50e5 * A_THROAT * L0_M ** 2 / 1e3:.1f} kN")
    print("outer wall thickness over the chamber:",
          [round(float(_body_r(np.array([x]))[0] - CH_R1), 2) for x in (CH_X0, -3.5, CH_X1)])
