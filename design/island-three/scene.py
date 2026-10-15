"""Island Three — the scene, built family by family.

Every mark below is a sample of a closed-form curve family C(k, t): k is an
integer index, t runs over [0, 1], and the colour and amplitude of each sample
are themselves formulas in (k, t).  Nothing is painted, traced or sampled from
an image; the only things taken from Guidice's painting are the six sector
angles, the landmark positions and the palette — measured as numbers and
written down here as constants.
"""
import os
import numpy as np
from PIL import Image
from island3 import (Canvas, proj, front, sector_of, is_window, light, hsh,
                     haze, dens, W, H, XMIN, XMAX, YMIN, YMAX, EY, ZC, TAU,
                     WL, WW, PITCH, VPY, AIR)

Z0 = 0.255                                   # nearest ground drawn
W0, W1 = 1.0 / Z0, 1.0 / ZC
TJ = np.array([0.0, TAU / 3, 2 * TAU / 3])   # the three valley axes
cv = Canvas(W, H)

zline = lambda t: 1.0 / (W0 + (W1 - W0) * t)   # linear in 1/Z: even on screen

# ISLAND3_ONLY=land,sky renders a subset of the families, for tuning one at a
# time; unset it and the whole plate is drawn.
_only = set(filter(None, os.environ.get('ISLAND3_ONLY', '').split(',')))
on = lambda name: not _only or name in _only


def steps(X, Y):
    """Sample spacing along each curve, in pixels."""
    dx = np.diff(X, axis=1, append=X[:, -1:]) * cv.sx
    dy = np.diff(Y, axis=1, append=Y[:, -1:]) * cv.sy
    return np.clip(np.hypot(dx, dy), 0.0, 40.0)


def area(X, Y, cap=600.0):
    """Screen area each sample of a two-index family stands for.

    For a family P(k, t) that sweeps out a surface, the Jacobian
    |dP/dk x dP/dt| is exactly the number of square pixels one sample owns.
    Depositing colour * area therefore lays down that colour and no more,
    whatever the sampling density — the one rule that keeps a converging
    family from piling into a white ball at the vanishing point.
    """
    dtx = np.diff(X, axis=1, append=X[:, -1:]) * cv.sx
    dty = np.diff(Y, axis=1, append=Y[:, -1:]) * cv.sy
    dsx = np.diff(X, axis=0, append=X[-1:, :]) * cv.sx
    dsy = np.diff(Y, axis=0, append=Y[-1:, :]) * cv.sy
    return np.clip(np.abs(dsx * dty - dsy * dtx), 0.0, cap)


def surf(X, Y, col, A=1.0, cap=600.0):
    cv.splat(X, Y, col, A * area(X, Y, cap).ravel())


def area3(X, Y, cap=90.0):
    """The same Jacobian for a family indexed (object, rib, t): the sweep runs
    along axis 1, so neighbouring ribs of one object never pair with another's.
    """
    dtx = np.diff(X, axis=2, append=X[:, :, -1:]) * cv.sx
    dty = np.diff(Y, axis=2, append=Y[:, :, -1:]) * cv.sy
    dsx = np.diff(X, axis=1, append=X[:, -1:, :]) * cv.sx
    dsy = np.diff(Y, axis=1, append=Y[:, -1:, :]) * cv.sy
    return np.clip(np.abs(dsx * dty - dsy * dtx), 0.0, cap)


def surf3(X, Y, col, A=1.0, keep=None):
    a = (A * area3(X, Y)).ravel()
    if keep is None:
        cv.splat(X, Y, col, a)
    else:
        m = keep.ravel()
        cv.splat(X.ravel()[m], Y.ravel()[m], col[m], a[m])


def line(X, Y, col, A):
    cv.splat(X, Y, col, A * steps(X, Y).ravel())


def bc(a, shape):
    return np.broadcast_to(a, shape).ravel()


# -- palette, sampled off the painting ---------------------------------------
CREAM    = np.array([0.860, 0.820, 0.300])
FIELD_HI = np.array([0.690, 0.700, 0.215])
FIELD    = np.array([0.500, 0.560, 0.150])
GRASS    = np.array([0.285, 0.405, 0.100])
WOOD     = np.array([0.110, 0.215, 0.065])
WOOD_D   = np.array([0.045, 0.110, 0.040])
ROAD     = np.array([0.680, 0.630, 0.330])
WATER    = np.array([0.070, 0.235, 0.450])
FOAM     = np.array([0.420, 0.560, 0.610])
CLOUD    = np.array([1.000, 0.985, 0.935])

# ------------------------------------------------------------- 1. the void --
cv.buf += np.array([0.008, 0.009, 0.024])

# ------------------------------------------- 2. nebula, high in the left sky
if on('sky'):
    k = np.arange(1, 421)[:, None]
    t = np.linspace(0, 1, 620)[None, :]
    ln, ang = 0.09 + 0.40 * hsh(k, 10.0), 2.55 + 1.00 * hsh(k, 9.0)
    nx = -1.24 + 0.62 * hsh(k, 7.0) + ln * (t - 0.5) * np.cos(ang) + 0.022 * np.sin(6.0 * t + 11 * k)
    ny = 0.26 + 0.64 * hsh(k, 8.0) + ln * (t - 0.5) * np.sin(ang) * 0.45 + 0.017 * np.sin(5.0 * t + 5 * k)
    Tn, _ = sector_of(nx, ny)
    mn = is_window(Tn) & (nx < -0.42)
    ncol = np.stack([0.46 + 0.28 * hsh(k, 13.0), 0.10 + 0.08 * hsh(k, 14.0),
                     0.50 + 0.22 * hsh(k, 15.0)], -1) * np.ones((1, t.size, 1))
    cv.splat(nx[mn], ny[mn], ncol.reshape(-1, 3)[mn.ravel()], 0.085)

# ------------------------------------ 3. mirror light, raked across that sky
if on('sky'):
    k = np.arange(1, 341)[:, None]
    t = np.linspace(0, 1, 460)[None, :]
    hx = (-1.33 + 1.05 * t) * np.ones_like(k)
    hy = 0.95 - 1.02 * (k / 340.0) - 0.330 * t
    Th, _ = sector_of(hx, hy)
    mh = is_window(Th) & (hx < -0.33)
    hcol = np.array([0.26, 0.29, 0.42]) * (0.30 + 0.95 * hsh(k, 21.0)).reshape(-1, 1)
    cv.splat(hx[mh], hy[mh], np.repeat(hcol, t.size, 0)[mh.ravel()], 0.115)

# ------------------------------------------------------------ 4. star field -
if on('sky'):
    k = np.arange(1, 9001)
    sx = XMIN + (XMAX - XMIN) * hsh(k, 1.0)
    sy = YMIN + (YMAX - YMIN) * hsh(k, 2.0)
    T, _ = sector_of(sx, sy)
    m = is_window(T)
    mag = hsh(k, 3.0) ** 7
    tint = np.stack([0.85 + 0.35 * hsh(k, 4.0), 0.88 + 0.18 * hsh(k, 5.0),
                     0.95 + 0.10 * hsh(k, 6.0)], 1)
    cv.splat(sx[m], sy[m], tint[m], 1.1 + 20.0 * mag[m])
    cv.splat(sx[m], sy[m], tint[m], 0.3 + 5.0 * mag[m])

# ------------------------------- 5. the solar mirror, filling the top window
if on('sun'):
    #   A wedge of arcs about the vanishing point.  Its colour is a sum of
    #   Gaussian bands in the radius rho — the stack of oranges, browns and
    #   blue-greys the painting shows between the sun and the hub.
    scr = lambda T: np.arctan2((EY - np.cos(T)) / np.cos(PITCH), np.sin(T))
    A0, A1 = scr(np.pi - WW / 2), scr(np.pi + WW / 2)
    NM = 1700
    k = np.arange(1, NM + 1)[:, None]
    t = np.linspace(0, 1, 900)[None, :]
    rho = 0.050 + 0.800 * (k / NM) ** 1.06
    aa = A0 + (A1 - A0) * t
    mx = rho * np.cos(aa)
    my = VPY + rho * np.sin(aa)
    BANDS = [(np.array([0.72, 0.74, 0.78]), 0.105, 0.030),
             (np.array([0.40, 0.46, 0.56]), 0.175, 0.038),
             (np.array([0.52, 0.36, 0.20]), 0.250, 0.030),
             (np.array([0.92, 0.52, 0.12]), 0.330, 0.034),
             (np.array([0.30, 0.13, 0.06]), 0.405, 0.028),
             (np.array([0.86, 0.44, 0.10]), 0.480, 0.034),
             (np.array([1.15, 0.72, 0.20]), 0.600, 0.075),
             (np.array([0.70, 0.30, 0.10]), 0.705, 0.035),
             (np.array([0.16, 0.07, 0.04]), 0.790, 0.045)]
    mcol = sum(c * np.exp(-((rho - mu) / sg) ** 2) for c, mu, sg in BANDS)
    mcol = np.repeat(mcol, t.size, 0) * (0.82 + 0.36 * np.sin(9.0 * aa + 21.0 * rho)).reshape(-1, 1)
    surf(mx, my, np.clip(mcol, 0, None))

    # the sun itself: nested ellipses with a Gaussian core
    k = np.arange(1, 601)[:, None]
    t = np.linspace(0, 1, 1400)[None, :]
    u = k / 600.0
    SX, SY = 0.029, 0.813
    qx = SX + 0.150 * u * np.cos(TAU * t)
    qy = SY + 0.128 * u * np.sin(TAU * t)
    scol = (np.array([1.00, 0.99, 0.96])[None, :]
            * (np.clip(1.6 - 26.0 * (u - 0.22), 0, 1) * 2.4
               + np.exp(-(u ** 2) / 0.16) * 0.45).reshape(-1, 1)
            + np.array([1.00, 0.56, 0.12])[None, :]
            * np.exp(-((u - 0.42) ** 2) / 0.045).reshape(-1, 1) * 1.1)
    surf(qx, qy, np.repeat(scol, t.size, 0))

    # glare: the sun spilling over the mullions, as it does in the painting
    k = np.arange(1, 401)[:, None]
    t = np.linspace(0, 1, 1200)[None, :]
    u = k / 400.0
    gx = SX + 0.34 * u * np.cos(TAU * t)
    gy = SY + 0.30 * u * np.sin(TAU * t)
    gcol = (np.array([1.00, 0.72, 0.32])[None, :] * np.exp(-(u ** 2) / 0.055).reshape(-1, 1) * 0.34)
    surf(gx, gy, np.repeat(gcol, t.size, 0))


# -------------------------------- 6. the Moon and a sister hull, left window
if on('moon'):
    def ball(cx, cy, rad, col, nlat=70, lit=(0.60, 0.56)):
        t = np.linspace(0, 1, 1200)[None, :]
        for mode in (0, 1):
            if mode == 0:
                ph = np.pi * (np.arange(0, nlat + 1)[:, None]) / nlat
                u = TAU * t
                X, Y, Zs = np.sin(ph) * np.cos(u), np.sin(ph) * np.sin(u), np.cos(ph) * np.ones_like(u)
            else:
                lam = TAU * np.arange(0, nlat + 1)[:, None] / nlat
                v = np.pi * t
                X, Y, Zs = np.sin(v) * np.cos(lam), np.sin(v) * np.sin(lam), np.cos(v) * np.ones_like(lam)
            vis = Y < 0.02
            sh = np.clip(lit[0] * X + lit[1] * Zs, 0, 1) ** 0.8
            mott = 0.80 + 0.30 * np.sin(9.0 * X + 7.0 * Zs) * np.sin(6.0 * Y + 2.0)
            c = np.asarray(col)[None, :] * ((0.10 + 0.95 * sh) * mott).reshape(-1, 1)
            Px, Py = cx + rad * X, cy + rad * Zs
            a = (0.5 * area(Px, Py)).ravel()
            cv.splat(Px[vis], Py[vis], c[vis.ravel()], a[vis.ravel()])


    ball(-0.632, 0.323, 0.084, (1.25, 1.24, 1.28))

    k = np.arange(0, 241)[:, None]
    t = np.linspace(0, 1, 1300)[None, :]
    ph = np.pi * k / 240
    cxx, cyy, ra, rb = -0.690, 0.178, 0.224, 0.082
    hx = cxx + ra * np.sin(ph) * np.cos(TAU * t)
    hy = cyy + rb * np.cos(ph) * np.ones_like(t)
    vis = np.sin(ph) * np.sin(TAU * t) < 0.02
    band = 0.5 + 0.5 * np.sin(17.0 * ph + 1.1 * np.sin(4.0 * TAU * t))
    shade = np.clip(0.58 * np.sin(ph) * np.cos(TAU * t) + 0.60 * np.cos(ph), 0, 1) ** 0.8
    hc = (np.array([0.86, 0.72, 0.34])[None, :] * (0.50 + 0.50 * band).reshape(-1, 1)
          + np.array([0.30, 0.36, 0.30])[None, :] * (1 - band).reshape(-1, 1) * 0.60)
    ah = area(hx, hy).ravel()
    cv.splat(hx[vis], hy[vis], (hc * (0.10 + 0.95 * shade.reshape(-1, 1)))[vis.ravel()], ah[vis.ravel()])

    # a low bank of cloud lying under the sister hull
    k = np.arange(1, 701)[:, None]
    t = np.linspace(0, 1, 420)[None, :]
    k = np.arange(1, 241)[:, None, None]
    bb = ((np.arange(6) + 0.5) / 6 - 0.5)[None, :, None]
    t = np.linspace(0, 1, 360)[None, None, :]
    pw = (0.004 + 0.026 * hsh(k, 34.0)) * np.sin(np.pi * t) ** 0.7
    px = ((-1.02 + 0.44 * t + 0.020 * np.sin(5.0 * t + 9.0 * k)
           + 0.030 * (hsh(k, 31.0) - 0.5)) * np.ones_like(bb))
    py = (0.112 - 0.044 * t ** 1.3 + 0.022 * (hsh(k, 32.0) - 0.5)
          + 0.009 * np.sin(4.0 * t + 3.0 * k) + pw * bb)
    pa = 0.62 * (np.sin(np.pi * t) ** 1.1) * hsh(k, 33.0) ** 1.9 * np.cos(np.pi * bb) ** 0.8
    surf3(px, py, np.broadcast_to(CLOUD, (px.size, 3)) * pa.reshape(-1, 1), 1.0)

# ----------------------------------------------------- 7. the far end cap --
if on('cap'):
    t = np.linspace(0, 1, 1800)[None, :]
    k = np.arange(0, 441)[:, None]
    u = k / 440.0
    Xe, Ye = proj(TAU * t * np.ones_like(k), ZC * np.ones_like(t), u)
    tex = 0.5 + 0.5 * np.sin(5.0 * np.pi * u + 1.2 * np.sin(3.0 * TAU * t))
    spoke = 0.5 + 0.5 * np.sin(36.0 * TAU * t) * np.ones_like(u)
    rim = np.exp(-((u - 1.0) ** 2) / 0.0010) * np.ones_like(t)
    core = np.exp(-((u - 0.040) ** 2) / 0.00022) * np.ones_like(t)
    cc = (AIR[None, :] * (0.72 + 0.20 * tex.reshape(-1, 1) * (0.85 + 0.3 * spoke.reshape(-1, 1)))
          + np.array([0.95, 0.88, 0.66])[None, :] * (0.26 * rim + 0.55 * core).reshape(-1, 1))
    surf(Xe, Ye, cc)

# the three valleys: shared ground functions -------------------------------
TPAR = [(1.00, 4.3, 1.7, 0.6), (0.70, 2.1, -2.9, 2.2),
        (0.45, 7.7, 4.3, 1.1), (0.26, 13.0, -7.0, 0.0),
        (0.13, 19.0, 9.0, 2.7)]


def terrain(s, Zv):
    """Height of the valley floor and its two partial derivatives."""
    h = sum(a * np.sin(ps * s + pz * Zv + r) for a, ps, pz, r in TPAR)
    hs = sum(a * ps * np.cos(ps * s + pz * Zv + r) for a, ps, pz, r in TPAR)
    hz = sum(a * pz * np.cos(ps * s + pz * Zv + r) for a, ps, pz, r in TPAR)
    return h, hs, hz


def _grid(u, v, phi, h0, h1):
    """One rotated, quantised grid: its cell draw and the distance to a seam."""
    cp, sp = np.cos(phi), np.sin(phi)
    a, b = u * cp + v * sp, v * cp - u * sp
    ia, ib = np.floor(a), np.floor(b)
    q = hsh(h0 * ia + 3.0, h1 * ib + 7.0)
    seam = np.minimum(np.minimum(a - ia, 1.0 - (a - ia)),
                      np.minimum(b - ib, 1.0 - (b - ib)))
    return q, seam


def parcels(s, Zv, j):
    """Farmland.

    Quantising one smooth function gives contour rings; quantising the two
    axes of a slowly turning frame gives a grid of fields, and overlaying two
    such grids at different scales and angles breaks the grid into the
    irregular polygons the painting is full of.
    """
    phi = (0.85 * np.sin(1.25 * Zv + 1.9 * s + 2.1 * j) + 0.5 * j
           + 0.45 * np.sin(4.3 * Zv - 2.7 * s + 1.1 * j))
    u = (s / 0.030 + 3.4 * np.sin(0.9 * Zv + 1.3 * j)
         + 1.2 * np.sin(2.7 * Zv + 0.4 * j))
    v = (Zv ** 0.40 / 0.0120 + 2.6 * np.sin(3.3 * s + 0.7 * j)
         + 1.3 * np.sin(7.1 * s + 2.0 * j))
    q1, e1 = _grid(u, v, phi, 17.0 + j, 11.0)
    q2, e2 = _grid(u * 1.63, v * 1.41, phi + 1.12 + 0.3 * j, 23.0 + j, 29.0)
    # frac of the sum keeps the draw uniform; averaging would bunch it at
    # the middle and flatten the fields into one tone
    return np.mod(q1 + q2, 1.0), np.minimum(e1, 0.70 * e2)


def water(s, Zv):
    """Lake and river in the near valley, as signed functions of (s, Z)."""
    u, v = (s - 0.185) / 0.150, (Zv - 0.615) / 0.074
    rr = np.hypot(u, v) + 1e-9
    an = np.arctan2(v, u)
    rad = (1.0 + 0.22 * np.sin(an + 0.7) + 0.14 * np.sin(2.0 * an - 1.2)
           + 0.10 * np.sin(3.0 * an + 2.1) + 0.06 * np.sin(5.0 * an)
           + 0.04 * np.sin(7.0 * an + 1.0))
    lake = (rad - rr) / 0.25
    sr = (0.352 + 0.030 * np.sin(2.3 * Zv + 0.4) + 0.011 * np.sin(5.1 * Zv)
          - 0.034 * np.exp(-((Zv - 0.90) ** 2) / 0.22))
    wr = 0.0052 + 0.0105 * np.exp(-((Zv - 1.00) ** 2) / 0.9)
    gate = np.clip((Zv - 0.60) / 0.07, 0, 1)
    wet = np.maximum(lake, ((1.0 - np.abs(s - sr) / wr) * gate - (1.0 - gate)) * 0.9)
    isl = np.maximum(1.0 - np.hypot((s - 0.146) / 0.028, (Zv - 0.598) / 0.0092),
                     1.0 - np.hypot((s - 0.214) / 0.017, (Zv - 0.636) / 0.0075))
    isl = np.maximum(isl, 1.0 - np.hypot((s - 0.252) / 0.013, (Zv - 0.606) / 0.0050))
    return wet, isl


# --------------------------------------------------- 8. the three valleys --
if on('land'):
    NS, MS, BLK = 2400, 1700, 240
    t = np.linspace(0, 1, MS)[None, :]
    Z = zline(t)
    fade = np.exp(-(Z - Z0) / 1.30)                  # detail dies with distance
    for j in range(3):
        for b0 in range(0, NS, BLK):
            kk = np.arange(b0, min(b0 + BLK, NS) + 1)[:, None]
            s = (kk + 0.5) / NS
            edge = np.abs(np.sin(np.pi * s)) ** 0.35
            h, hs, hz = terrain(s + 3.1 * j, Z + 1.7 * j)
            R = 1.0 - 0.0215 * edge * h
            T = TJ[j] + WL * (s - 0.5) + 0.012 * edge * h
            X, Y = proj(T, Z, R)
            sh = X.shape
            FD = bc(fade, sh)[:, None]

            # large-scale ground tone, from deep grass to pale stubble
            b1 = 0.5 + 0.5 * np.sin(1.35 * Z + 2.1 * s + 1.9 * j)
            b2 = 0.5 + 0.5 * np.sin(0.62 * Z - 3.3 * s + 0.7 * j + 1.3)
            g = bc(0.10 + 0.86 * b1 * b2, sh)[:, None]
            col = GRASS + (FIELD_HI - GRASS) * g

            # parcels: a brightness and warmth jitter, field by field
            q, seam = parcels(s * np.ones_like(t), np.broadcast_to(Z, sh), j)
            # the parcel grid goes sub-pixel in the distance; let it fade out
            # there rather than alias into moire
            qq = (bc(q, sh)[:, None] - 0.5) * np.clip(0.22 + 1.05 * FD, 0, 1)
            col = col * (1.0 + 0.80 * qq) + np.array([0.14, 0.05, -0.030]) * qq
            pale = np.clip((qq - 0.27) / 0.11, 0, 1)
            col = np.clip(col, 0.0, None) * (1 - 0.78 * pale) + CREAM * (0.78 * pale)

            # woodland: coherent dark masses, not single fields
            # woodland sits on whole fields inside the wooded districts,
            # the way it does on the plate
            wm = ((0.5 + 0.5 * np.sin(9.0 * s + 3.9 * Z + 2.2 * j))
                  * (0.5 + 0.5 * np.sin(4.3 * s - 6.1 * Z + 1.1 * j))
                  * (0.55 + 0.45 * np.sin(27.0 * s + 12.0 * Z + 0.7 * j)))
            WM, Q = bc(wm, sh)[:, None], bc(q, sh)[:, None]
            wk = (np.clip((WM - 0.155) / 0.065, 0, 1)
                  * np.clip((0.46 - Q) / 0.13, 0, 1))
            wk = np.clip(wk + 0.22 * np.clip((WM - 0.33) / 0.10, 0, 1), 0, 1)
            col = col * (1 - 0.88 * wk) + WOOD * (0.88 * wk)

            hedge = bc(np.exp(-(seam / 0.014) ** 2), sh)[:, None] * FD
            gl = np.sin(10.5 * np.pi * s + 1.9 * np.sin(1.7 * Z + 2.0 * j) + 2.3 * j)
            lane = np.exp(-((gl / 0.012) ** 2)) * fade
            gz = np.sin(2.3 * Z + 3.0 * np.sin(5.0 * s + 1.0 * j))
            lane = bc(np.maximum(lane, np.exp(-((gz / 0.005) ** 2)) * fade * 0.8), sh)[:, None]
            col = col * (1 - 0.68 * hedge) + WOOD_D * (0.68 * hedge)
            col = col * (1 - 0.65 * lane) + ROAD * (0.65 * lane)

            if j == 0:
                wet, isl = water(s * np.ones_like(t), np.broadcast_to(Z, sh))
                w = (np.clip(wet * 2.2, 0, 1) * np.clip(-isl * 26.0, 0, 1)).reshape(-1, 1)
                sheen = np.exp(-((s - 0.210) / 0.075) ** 2 - ((Z - 0.600) / 0.14) ** 2)
                wc = WATER + FOAM * (0.34 * bc(sheen, sh)
                                     + 0.26 * np.exp(-(wet.ravel() / 0.45) ** 2))[:, None]
                col = col * (1 - w) + wc * w

            rel = 0.76 + 0.20 * np.tanh(0.42 * hz) + 0.11 * np.tanh(0.16 * hs)
            col = col * bc(rel, sh)[:, None]
            col = col * (0.42 + 0.78 * (light(T).ravel() / 1.6))[:, None]
            col = col * bc(0.78 + 0.30 * np.clip((Z - 0.26) / 0.55, 0, 1), sh)[:, None]
            col = haze(bc(Z, sh), col)
            a = area(X, Y).ravel() * (bc(front(T, Z, R), sh) > 0.14)
            n = (kk.size - 1) * MS                       # drop the overlap row
            cv.splat(X.ravel()[:n], Y.ravel()[:n], col[:n], a[:n])

# ------------------------------------------- 9. woods: clustered dark canopy
if on('woods'):
    NW, NRG, NT = 2600, 7, 84
    k = np.arange(1, NW + 1)[:, None, None]
    r = ((np.arange(NRG) + 0.5) / NRG)[None, :, None]
    t = np.linspace(0, 1, NT)[None, None, :]
    jj = np.mod(k, 3)
    cl = np.floor(k / 6.0)
    Zw = 0.285 + 3.4 * hsh(cl, 51.0) ** 1.7 + 0.075 * (hsh(k, 55.0) - 0.5)
    sw = hsh(cl, 52.0) + 0.060 * (hsh(k, 56.0) - 0.5)
    Tw = TJ[jj.ravel()].reshape(-1, 1, 1) + WL * 0.95 * (sw - 0.5)
    wet, isl = water(sw, Zw)
    dry = (jj != 0) | (wet < 0.03) | (isl > -0.1)
    rad = (0.0035 + 0.0090 * hsh(k, 53.0)) * r * (
        1.0 + 0.26 * np.sin(3.0 * TAU * t + 9.0 * k) + 0.14 * np.sin(5.0 * TAU * t))
    Xw, Yw = proj(Tw + rad * np.cos(TAU * t),
                  Zw * (1.0 + 0.55 * rad * np.sin(TAU * t)), 0.9992)
    wc = WOOD * (0.20 + 0.40 * hsh(k, 54.0)).reshape(-1, 1) + WOOD_D * 0.45
    wc = haze(bc(Zw, Xw.shape), np.repeat(wc, NRG * NT, 0))
    surf3(Xw, Yw, wc, 1.0,
          keep=np.broadcast_to(dry & (front(Tw, Zw, 0.9992) > 0.16), Xw.shape))

# ------------------------------------------------ 10. cloud banks and veils
if on('cloud'):
    NC, NB, NT = 560, 7, 260
    k = np.arange(1, NC + 1)[:, None, None]
    b = ((np.arange(NB) + 0.5) / NB - 0.5)[None, :, None]
    t = np.linspace(0, 1, NT)[None, None, :]
    near = hsh(k, 79.0) < 0.55                      # over half lie on the near
    jj = np.where(near, 0, 1 + (hsh(k, 80.0) > 0.5))  # valley, by the horizon
    w0 = np.where(near, 0.24 + 0.52 * hsh(k, 71.0),
                  0.20 + 0.78 * hsh(k, 71.0))       # 1/Z: even across the screen
    dw = 0.050 + 0.165 * hsh(k, 78.0) ** 1.3        # streaks of even length too
    Zcl = 1.0 / np.maximum(w0 - dw * t, 0.105)
    wid = (0.007 + 0.024 * hsh(k, 76.0)) * np.sin(np.pi * t) ** 0.6
    es = hsh(k, 73.0) - 0.5
    es = np.sign(es) * np.abs(2.0 * es) ** 0.42 * 0.5
    Tcl = (TJ[jj.ravel()].reshape(-1, 1, 1) + WL * 0.99 * es
           + 0.011 * np.sin(4.0 * t + 3.0 * k) + wid * b)
    Rcl = (0.895 + 0.045 * hsh(k, 74.0) + 0.005 * np.sin(5.0 * t + k)
           + 0.010 * (0.25 - b * b))
    Xc, Yc = proj(Tcl, Zcl, Rcl)
    puff = ((np.sin(np.pi * t) ** 0.40) * (0.22 + 1.15 * hsh(k, 75.0) ** 1.3)
            * np.cos(np.pi * b) ** 0.7)
    ccol = np.broadcast_to(CLOUD, (Xc.size, 3)) * puff.reshape(-1, 1)
    surf3(Xc, Yc, ccol, 1.0,
          keep=np.broadcast_to(front(Tcl, Zcl, 0.9) > 0.16, Xc.shape))

# ------------------------------------------------- 11. the window mullions -
if on('mull'):
    t = np.linspace(0, 1, 2400)[None, :]
    Zb = zline(t)
    for m0 in range(6):
        Tb = np.full_like(Zb, WL / 2 + (m0 // 2) * TAU / 3 + (m0 % 2) * (TAU / 3 - WL))
        for d, wgt in ((-1, 0.30), (0, 1.0), (1, 0.30)):
            Xb, Yb = proj(Tb + d * 0.0065, Zb, 1.0)
            line(Xb, Yb, haze(Zb.ravel(), np.array([0.92, 0.86, 0.66]) * wgt, 0.35),
                 0.95 * (front(Tb, Zb) > 0.14))

Image.fromarray(cv.image(gain=1.22, sat=1.05)).save('art.png')
print('wrote art.png')
