"""Aerospike half-section traced from the Aspire / LEAP 71 XRA-2E5 render.

Lengths are in simulation units L0 = spike root radius.  x = engine axis
(flow goes +x), r = radius.  The same polygon drives the solver mask
(setup_case.py) and the outline in the video (make_video.py).

From the turntable render (Aspire_engine_turntable_4K.mp4), measured in
units of the spike root radius:
  * the spike leaves the flat bottom face of a turned ring, root slope ~29 deg,
    gently concave, length ~2.06, truncated at r ~0.27
  * ring radius ~1.8 below a flange (~2.1), main body ~2.3 (inside the lattice)
The inside is not visible, so the toroidal chamber and the annular feed slot
(throat just inside the ring, small internal expansion to the ring face,
exit aligned with the spike root) are a plausible layout, not LEAP 71's.
"""
import numpy as np

GAM = 1.2

# ------------------------------------------------------------ spike (measured)
_S = np.array([0, 42, 92, 142, 192, 242, 292, 342, 392, 442, 462]) / 224.0
_R = np.array([224, 201, 176, 155, 136, 119, 104, 90, 77, 65, 60]) / 224.0

X_LIP = 2.60           # ring bottom face (exit plane of the slot)
R_LIP = 1.10           # outer lip of the annular slot
THETA = np.radians(29.0)  # slot / jet direction, inward from the axis
D = np.array([np.cos(THETA), -np.sin(THETA)])   # flow direction in the slot
N = np.array([np.sin(THETA), np.cos(THETA)])    # across the slot (inner -> lip)

W_EXIT = 0.055         # half-width at the ring face
W_THR = 0.030          # half-width at the throat
S_THR = -0.22          # throat position along the slot (upstream of the face)
L_P = 0.80             # slot length
W_P1 = 0.15            # half-width where the slot meets the chamber

E = np.array([X_LIP, R_LIP]) - W_EXIT * N       # slot exit centre
X_T, R_T = E - W_EXIT * N                       # inner exit point = spike root
SPIKE_X = X_T + _S * R_T
SPIKE_R = _R * R_T
# smooth the measured profile
_xf = np.linspace(SPIKE_X[0], SPIKE_X[-1], 400)
_rf = np.interp(_xf, SPIKE_X, SPIKE_R)
_rf = np.convolve(np.pad(_rf, 6, mode="edge"), np.ones(13) / 13, mode="valid")
_rf[0] = SPIKE_R[0]
SPIKE_X, SPIKE_R = _xf, _rf
X_SPIKE_END = SPIKE_X[-1]
R_BASE = SPIKE_R[-1]

# ------------------------------------------------------------ body
R_BODY = 2.30          # main body (inside the lattice skin)
R_FLANGE = 2.12
R_RING = 1.80
X_FLANGE0 = X_LIP - 0.42
X_RING0 = X_LIP - 0.20

# toroidal chamber
_P1 = E - L_P * D
CH_X, CH_R, CH_AX, CH_AR = X_LIP - 0.95, 1.62, 0.42, 0.30
WALL = 0.12
X_BACK = -0.5          # body continues upstream out of the domain
X_INJ = CH_X - CH_AX + 0.18

GAP_T = 2 * W_THR
A_THROAT = 2 * np.pi * (E[1] + (-S_THR) * np.sin(THETA)) * GAP_T
EPS_E = np.pi * R_LIP ** 2 / A_THROAT


def r_spike(x):
    return np.interp(x, SPIKE_X, SPIKE_R, left=R_T, right=R_BASE)


def _pt(s, q):
    return E + s * D + q * N


def _halfw(s):
    s = np.asarray(s, dtype=float)
    down = np.clip((s - S_THR) / (0 - S_THR), 0, 1)            # throat -> exit
    up = np.clip((S_THR - s) / (L_P + S_THR), 0, 1)             # throat -> chamber
    return np.where(s >= S_THR, W_THR + (W_EXIT - W_THR) * down ** 1.4,
                    W_THR + (W_P1 - W_THR) * up ** 1.3)


def _ellipse(a0, a1, n, grow=0.0):
    a = np.linspace(a0, a1, n)
    return np.stack([CH_X + (CH_AX + grow) * np.cos(a), CH_R + (CH_AR + grow) * np.sin(a)], 1)


def _ang(p):
    return np.arctan2((p[1] - CH_R) / CH_AR, (p[0] - CH_X) / CH_AX)


def outline():
    """Closed polygon (x, r) of the metal half-section, chamber as a slit."""
    c = 0.06
    pts = [[X_BACK, 0.0], [X_BACK, R_BODY],
           [X_FLANGE0 - c, R_BODY], [X_FLANGE0, R_BODY - c],          # body -> flange
           [X_FLANGE0, R_FLANGE], [X_RING0 - 0.03, R_FLANGE],
           [X_RING0, R_FLANGE - 0.03], [X_RING0, R_RING],            # flange -> ring
           [X_LIP - 0.03, R_RING], [X_LIP, R_RING - 0.03],
           [X_LIP, R_LIP + 0.004]]                                    # ring face to lip
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
    print(f"spike root ({X_T:.3f},{R_T:.3f}) end x={X_SPIKE_END:.3f} r_base={R_BASE:.3f} "
          f"length={X_SPIKE_END - X_T:.2f}; throat gap {GAP_T:.3f}, A_t={A_THROAT:.3f}, eps={EPS_E:.2f}; "
          f"P1 in chamber: {in_chamber(*_P1)}")
