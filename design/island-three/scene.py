"""Island Three — the scene, built family by family."""
import numpy as np
from island3 import (Canvas, proj, sector_of, is_window, light, hsh, haze, dens,
                     W, H, XMIN, XMAX, YMIN, YMAX, EY, ZC, TAU, WL)

Z0 = 0.30
W0, W1 = 1.0 / Z0, 1.0 / ZC
TJ = np.array([0.0, TAU / 3, 2 * TAU / 3])
HALF = WL / 2                                   # valley half-width
cv = Canvas(W, H)

zline = lambda t: 1.0 / (W0 + (W1 - W0) * t)


def steps(X, Y):
    dx = np.diff(X, axis=1, append=X[:, -1:]) * cv.sx
    dy = np.diff(Y, axis=1, append=Y[:, -1:]) * cv.sy
    return np.clip(np.hypot(dx, dy), 0.0, 40.0)


# -------------------------------------------------------- 1. deep space -----
cv.buf += np.array([0.009, 0.011, 0.026])

# -------------------------------------------------------- 2. star field -----
k = np.arange(1, 6001)
sx = XMIN + (XMAX - XMIN) * hsh(k, 1.0)
sy = YMIN + (YMAX - YMIN) * hsh(k, 2.0)
T, _ = sector_of(sx, sy)
m = is_window(T)
mag = hsh(k, 3.0) ** 7
tint = np.stack([0.85 + 0.35 * hsh(k, 4.0), 0.88 + 0.18 * hsh(k, 5.0),
                 0.95 + 0.10 * hsh(k, 6.0)], 1)
cv.splat(sx[m], sy[m], tint[m], 2.0 + 30.0 * mag[m])
cv.splat(sx[m], sy[m], tint[m], 0.5 + 8.0 * mag[m])

# ----------------------------------------------- 3. dust lane, left window --
k = np.arange(1, 161)[:, None]
t = np.linspace(0, 1, 900)[None, :]
ln, ang = 0.12 + 0.30 * hsh(k, 10.0), 2.3 + 0.9 * hsh(k, 9.0)
dx = (-0.80 + 0.46 * hsh(k, 7.0)) + ln * (t - 0.5) * np.cos(ang) + 0.028 * np.sin(6.0 * t + 11 * k)
dy = (-0.10 + 0.50 * hsh(k, 8.0)) + ln * (t - 0.5) * np.sin(ang) * 0.5 + 0.022 * np.sin(5.0 * t + 5 * k)
Td, _ = sector_of(dx, dy)
md = is_window(Td)
cv.splat(dx[md], dy[md], np.array([0.28, 0.12, 0.33]), 0.05)

# ------------------------------------------------- 4. the sun, top window ---
SUNX, SUNY = -0.045, 0.700
k = np.arange(1, 1101)[:, None]
t = np.linspace(0, 1, 760)[None, :]
a = TAU * hsh(k, 11.0)
L = 0.028 + 0.30 * hsh(k, 12.0) ** 2.8
rx = SUNX + L * t * np.cos(a) * 1.5
ry = SUNY + L * t * np.sin(a)
Ts, _ = sector_of(rx, ry)
ms = is_window(Ts)
asun = (0.95 * (1.0 - t) ** 2.6 * np.ones_like(k)) * steps(rx, ry)
cv.splat(rx[ms], ry[ms], np.array([1.00, 0.86, 0.56]), asun[ms])
k = np.arange(1, 441)[:, None]
t = np.linspace(0, 1, 900)[None, :]
rad = 0.062 * (k / 440.0)
Xsun = SUNX + rad * np.cos(TAU * t) * 1.35
Ysun = SUNY + rad * np.sin(TAU * t)
cv.splat(Xsun, Ysun, np.array([1.0, 0.94, 0.78]),
         6.5 * np.broadcast_to(np.exp(-((k / 440.0) ** 2) / 0.10), Xsun.shape).ravel()
         * steps(Xsun, Ysun).ravel())

# ---------------------------------------- 5. moon and neighbouring habitat --
def sphere(cx, cy, rad, col, nlat=48, nlon=48, amp=0.20, lit=(-0.5, 0.6)):
    t = np.linspace(0, 1, 800)[None, :]
    for mode in (0, 1):
        if mode == 0:
            ph = np.pi * (np.arange(1, nlat + 1)[:, None] - 0.5) / nlat
            u = TAU * t
            X, Y, Zs = np.sin(ph) * np.cos(u), np.sin(ph) * np.sin(u), np.cos(ph) * np.ones_like(u)
        else:
            lam = TAU * np.arange(1, nlon + 1)[:, None] / nlon
            v = np.pi * t
            X, Y, Zs = np.sin(v) * np.cos(lam), np.sin(v) * np.sin(lam), np.cos(v) * np.ones_like(lam)
        vis = Y < 0.02
        sh = np.clip(lit[0] * X + lit[1] * Zs, 0, 1) ** 0.8
        c = np.asarray(col)[None, :] * (0.15 + 0.95 * sh.reshape(-1, 1))
        Px, Py = cx + rad * X, cy + rad * Zs
        aa = (amp * 11.0 * steps(Px, Py)).ravel()
        cv.splat(Px[vis], Py[vis], c[vis.ravel()], aa[vis.ravel()])


sphere(-0.742, 0.258, 0.063, (0.80, 0.80, 0.86), amp=0.22)
k = np.arange(1, 131)[:, None]
t = np.linspace(0, 1, 860)[None, :]
ph = np.pi * (k - 0.5) / 130
hx = -0.536 + 0.074 * np.sin(ph) * np.cos(TAU * t) * 1.5
hy = 0.062 + 0.074 * np.cos(ph) * np.ones_like(t)
vis = np.sin(ph) * np.sin(TAU * t) < 0.02
band = 0.5 + 0.5 * np.sin(14.0 * ph + 1.3 * np.sin(5.0 * TAU * t))
shade = np.clip(-0.55 * np.sin(ph) * np.cos(TAU * t) + 0.62 * np.cos(ph), 0, 1) ** 0.8
hc = (np.array([0.74, 0.61, 0.26])[None, :] * (0.55 + 0.45 * band).reshape(-1, 1)
      + np.array([0.26, 0.30, 0.28])[None, :] * (1 - band).reshape(-1, 1) * 0.6)
ahab = (12.0 * steps(hx, hy)).ravel()
cv.splat(hx[vis], hy[vis], (hc * (0.14 + 0.95 * shade.reshape(-1, 1)))[vis.ravel()], ahab[vis.ravel()])

# ------------------------------------------------- 6. the far end cap -------
t = np.linspace(0, 1, 1500)[None, :]
k = np.arange(1, 301)[:, None]
u = k / 300.0
Xe, Ye = proj(TAU * t * np.ones_like(k), ZC * np.ones_like(t), u)
tex = 0.5 + 0.5 * np.sin(5.0 * np.pi * u + 0.6 * np.sin(3.0 * TAU * t))
rim = np.exp(-((u - 1.0) ** 2) / 0.00016) * 2.6 * np.ones_like(t)
hub = np.exp(-((u - 0.145) ** 2) / 0.00045) * 0.22 * np.ones_like(t)
cc = (np.array([0.055, 0.064, 0.078])[None, :] * (0.70 + 0.30 * tex.reshape(-1, 1))
      + np.array([1.00, 0.88, 0.62])[None, :] * (rim + hub).reshape(-1, 1) * 0.42)
cv.splat(Xe, Ye, cc, 0.42 * steps(Xe, Ye).ravel())
k = np.arange(1, 37)[:, None]
t = np.linspace(0, 1, 620)[None, :]
Xs, Ys = proj(np.ones_like(t) * (TAU * k / 36), ZC * np.ones_like(t), t)
cv.splat(Xs, Ys, np.array([0.150, 0.160, 0.165]),
         1.3 * (t ** 1.6 * np.ones_like(k)).ravel() * steps(Xs, Ys).ravel())

# ------------------------------------------------ 7. the three valley strips
NS, MS = 1000, 2400
t = np.linspace(0, 1, MS)[None, :]
Z = zline(t)
dark = np.array([0.045, 0.095, 0.030])
mid = np.array([0.235, 0.345, 0.075])
lite = np.array([0.640, 0.655, 0.200])
for j, tj in enumerate(TJ):
    k = np.arange(1, NS + 1)[:, None]
    s = (k - 0.5) / NS
    edge = np.sin(np.pi * s)
    T = (tj + 2 * HALF * (s - 0.5)
         + edge * (0.050 * np.sin(5.3 * Z + 11.0 * s + 2.1 * j)
                   + 0.020 * np.sin(12.1 * Z + 23.0 * s)
                   + 0.009 * np.sin(29.0 * Z + 7.0 * s)))
    relief = 1.0 - 0.021 * edge * (np.sin(4.1 * Z + 9.0 * s) + 0.6 * np.sin(11.0 * Z + 3.0 * s))
    X, Y = proj(T, Z, relief)
    # patchwork of fields: varies both across the strip and along the axis
    g = np.clip(0.5 + 0.5 * np.sin(8.6 * s * np.pi + 2.2 * np.sin(3.3 * Z + 1.9 * j)
                                   + 1.1 * np.sin(2.1 * Z + 6.0 * s) + 1.7 * j), 0, 1)
    g = np.clip(0.76 * g + 0.24 * (0.5 + 0.5 * np.sin(57.0 * s + 15.0 * Z)), 0, 1)
    g1 = np.clip(g * 2, 0, 1).reshape(-1, 1)
    g2 = np.clip(g * 2 - 1, 0, 1).reshape(-1, 1)
    col = dark * (1 - g1) + mid * g1
    col = col * (1 - g2) + lite * g2
    col = col * (light(T).reshape(-1, 1) / 1.5)          # window irradiance
    col = haze(Z.repeat(NS, 0).ravel(), col)
    cv.splat(X, Y, col, 1.45 * np.broadcast_to(dens(Z), X.shape).ravel()
             * steps(X, Y).ravel())

# -------------------------------------------------------- 8. river and lake -
k = np.arange(1, 161)[:, None]
t = np.linspace(0, 1, 2600)[None, :]
Zr = 1.0 / (1.0 / 0.33 + (1.0 / 5.2 - 1.0 / 0.33) * t)
# the channel swells into a lake where the bulge function peaks
swell = 1.0 + 2.2 * np.exp(-((Zr - 0.95) ** 2) / 0.070) + 1.1 * np.exp(-((Zr - 2.3) ** 2) / 0.18)
wid = (0.0135 + 0.006 * np.sin(1.9 * Zr)) * swell * (((k - 0.5) / 160 - 0.5) * 2)
axis = 0.085 * np.sin(2.3 * Zr) + 0.030 * np.sin(5.9 * Zr + 1.0)
Tr2 = axis + wid
Xr, Yr = proj(Tr2, Zr, 0.9975)
shore = (0.45 + 0.75 * np.abs(((k - 0.5) / 160 - 0.5) * 2) * np.ones_like(t)).reshape(-1, 1)
rc = haze(Zr.repeat(160, 0).ravel(),
          np.array([0.060, 0.125, 0.195]) * shore * (light(Tr2).reshape(-1, 1) / 1.7))
cv.splat(Xr, Yr, rc, 0.85 * np.broadcast_to(dens(Zr), Xr.shape).ravel()
         * steps(Xr, Yr).ravel())

# ----------------------------------------------------------- 9. cloud decks -
k = np.arange(1, 601)[:, None]
t = np.linspace(0, 1, 700)[None, :]
jj = np.mod(k, 3)
tc = TJ[jj.ravel()].reshape(-1, 1) + 2 * HALF * 0.78 * (hsh(k, 21.0) - 0.5)
Zc0 = 0.48 + 2.1 * hsh(k, 22.0) ** 1.25
Zcl = Zc0 * (1.0 + (0.07 + 0.24 * hsh(k, 23.0)) * t)
Tcl = tc + 0.034 * (hsh(k, 24.0) - 0.5) * np.sin(np.pi * t) + 0.010 * np.sin(2.0 * t + k)
Rcl = 0.930 + 0.012 * np.sin(3.0 * t + 2.0 * k)
Xc, Yc = proj(Tcl, Zcl, Rcl)
bright = (np.sin(np.pi * t) ** 1.8) * (0.16 + 0.48 * hsh(k, 25.0))
ccol = (haze(Zcl.ravel(), np.array([0.97, 0.96, 0.92]))
        * bright.reshape(-1, 1) * (light(Tcl).reshape(-1, 1) / 1.7))
cv.splat(Xc, Yc, ccol, 0.62 * steps(Xc, Yc).ravel())

# ------------------------------------------- 9b. field parcels on the land --
k = np.arange(1, 441)[:, None]
t = np.linspace(0, 1, 900)[None, :]
jj = np.mod(k, 3)
Zp = 0.42 + 3.3 * hsh(k, 31.0) ** 1.35
tp = TJ[jj.ravel()].reshape(-1, 1) + WL * 0.86 * (hsh(k, 32.0) - 0.5)
span = 0.055 + 0.13 * hsh(k, 33.0)
ori = TAU * hsh(k, 34.0)
Tp = tp + span * (t - 0.5) * np.cos(ori)
Zq = Zp * (1.0 + 0.16 * span * (t - 0.5) * np.sin(ori))
Xp, Yp = proj(Tp, Zq, 0.9992)
pc = haze(Zq.ravel(), np.array([0.105, 0.145, 0.055])
          * ((0.5 + 1.1 * hsh(k, 35.0)) * np.ones_like(t)).reshape(-1, 1))
cv.splat(Xp, Yp, pc, 0.95 * steps(Xp, Yp).ravel())

# ------------------------------------------------- 10. structural ribs ------
t = np.linspace(0, 1, 2600)[None, :]
Zb = zline(t)
for m0 in range(6):
    for d, wgt in ((-1, 0.40), (0, 1.0), (1, 0.40)):
        Tb = np.full_like(Zb, WL / 2 + (m0 // 2) * TAU / 3
                         + (m0 % 2) * (TAU / 3 - WL) + d * 0.009)
        Xb, Yb = proj(Tb, Zb, 1.0)
        cv.splat(Xb, Yb, haze(Zb.ravel(), np.array([0.86, 0.84, 0.74]) * wgt),
                 1.7 * steps(Xb, Yb).ravel())

from PIL import Image
Image.fromarray(cv.image(gamma=1.85, gain=1.0)).save('art.png')
print('wrote art.png')
