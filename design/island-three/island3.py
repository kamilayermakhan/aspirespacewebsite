"""
Island Three (O'Neill cylinder) — drawn entirely from explicit formulas.

Method after Hamid Naderi Yeganeh: every mark is a sample of a closed-form
family of curves indexed by an integer k.  No raster fills, no brushes, no
bitmap textures — the shading is the accumulated density of lines.

Geometry.  The habitat is the cylinder x^2 + y^2 = 1 with axis z.  The eye is
at E = (0, -e, 0), e = 0.62, pitched down by B = 0.22 rad.  A point at angular
coordinate T and axial coordinate Z therefore projects to

      u = sin T
      v = (e - cos T) cos B + Z sin B
      w = (cos T - e) sin B + Z cos B
      P(T, Z) = ( u / w , v / w ).

Six sectors alternate around the tube: valleys of width WL = 1.257 rad centred
on T = 0, 2pi/3, 4pi/3, and windows of width 2pi/3 - WL centred on T = pi/3,
pi, 5pi/3.  A line of constant T leaves the vanishing point at screen angle
arctan2((e - cos T)/cos B, sin T); the six values measured off Guidice's
painting fix e and WL to within five degrees.
"""
import numpy as np

W, H = 2048, 1613
XMIN, XMAX = -1.322, 0.622
YMIN, YMAX = -0.5725, 0.9585
EY = 0.62                      # eye offset from the axis
PITCH = 0.22                   # camera pitch, radians (looking down)
ZC = 9.0                       # axial distance of the far end cap
TAU = 2.0 * np.pi
PHI0 = 0.0                     # measured off the painting: a valley runs
                               # straight down, the sun window straight up
ROLL = 0.0                     # camera roll, radians
CB, SB = np.cos(PITCH), np.sin(PITCH)
CR, SR = np.cos(ROLL), np.sin(ROLL)
VPY = SB / CB                  # vanishing point of the axis, on screen


# ---------------------------------------------------------------- canvas ----
class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.n = w * h
        self.buf = np.zeros((self.n, 3), np.float64)
        self.sx = (w - 1) / (XMAX - XMIN)
        self.sy = (h - 1) / (YMAX - YMIN)

    def splat(self, X, Y, rgb, amp):
        X = np.asarray(X, np.float64)
        Y = np.asarray(Y, np.float64)
        shape = np.broadcast_shapes(X.shape, Y.shape)
        X = np.broadcast_to(X, shape).ravel()
        Y = np.broadcast_to(Y, shape).ravel()
        a = np.asarray(amp, np.float64)
        a = a.ravel() if a.size == X.size else np.broadcast_to(a, shape).ravel()
        c = np.asarray(rgb, np.float64)
        if c.ndim == 1:
            c = np.broadcast_to(c, (X.size, 3))
        else:
            c = c.reshape(-1, 3)
            if c.shape[0] != X.size:
                c = np.repeat(c, X.size // c.shape[0], axis=0)
        px = (X - XMIN) * self.sx
        py = (YMAX - Y) * self.sy
        ok = (np.isfinite(px) & np.isfinite(py) &
              (px >= 0) & (px <= self.w - 1.001) &
              (py >= 0) & (py <= self.h - 1.001))
        if not ok.any():
            return
        px, py, a, c = px[ok], py[ok], a[ok], c[ok]
        for lo in range(0, px.size, 600_000):
            hi = lo + 600_000
            qx, qy, qa, qc = px[lo:hi], py[lo:hi], a[lo:hi], c[lo:hi]
            x0 = qx.astype(np.int64); y0 = qy.astype(np.int64)
            fx = qx - x0; fy = qy - y0
            for dx in (0, 1):
                wx = fx if dx else 1.0 - fx
                for dy in (0, 1):
                    wgt = wx * (fy if dy else 1.0 - fy) * qa
                    idx = (y0 + dy) * self.w + (x0 + dx)
                    for ch in range(3):
                        self.buf[:, ch] += np.bincount(
                            idx, weights=qc[:, ch] * wgt, minlength=self.n)

    def image(self, gain=1.0, sat=1.0, gamma=1.0):
        """Tone-map the accumulated energy.

        m -> m / (1 + m^3)^(1/3) is near the identity below half a unit and
        folds everything brighter into [0, 1).  It is applied to the largest
        of the three channels and the other two are scaled with it, so
        compressing the highlights never bleaches a hue — the usual
        per-channel curve turns the deep greens of the valley into the milky
        olive of an over-exposed photograph.
        """
        b = np.nan_to_num(np.clip(self.buf * gain, 0, None), nan=0.0, posinf=0.0)
        m = b.max(1)
        f = 1.0 / np.cbrt(1.0 + m ** 3)
        c = b * f[:, None]
        if sat != 1.0:
            g = c.mean(1)[:, None]
            c = np.clip(g + sat * (c - g), 0, 1)
        if gamma != 1.0:
            c = np.power(np.clip(c, 0, 1), 1.0 / gamma)
        c = c.reshape(self.h, self.w, 3)
        return (np.clip(c, 0, 1) * 255 + 0.5).astype(np.uint8)


# ------------------------------------------------------------ projection ----
def proj(T, Z, R=1.0):
    T = T + PHI0
    u = R * np.sin(T)
    v = (EY - R * np.cos(T)) * CB + Z * SB
    w = (R * np.cos(T) - EY) * SB + Z * CB
    x, y = u / w, v / w - VPY
    return x * CR - y * SR, x * SR + y * CR + VPY


def front(T, Z, R=1.0):
    """Depth of a point along the view axis; non-positive is behind the eye."""
    return (R * np.cos(T + PHI0) - EY) * SB + Z * CB


def sector_of(X, Y):
    """Inverse projection: the cylinder angle seen at screen point (X, Y)."""
    x, y = X, Y - VPY
    X = x * CR + y * SR
    Y = -x * SR + y * CR + VPY
    dy = Y * CB - SB
    A = X * X + dy * dy
    B = -2.0 * EY * dy
    C = EY * EY - 1.0
    t = (-B + np.sqrt(np.maximum(B * B - 4 * A * C, 0.0))) / (2.0 * np.maximum(A, 1e-12))
    return np.mod(np.arctan2(t * X, EY - t * dy) - PHI0, TAU), t


WL = 1.257                     # angular width of a valley strip
WW = TAU / 3 - WL              # angular width of a window strip


def is_window(T):
    return np.mod(T + WL / 2, TAU / 3) > WL


def light(T):
    """Irradiance on the inner wall from the three window strips.

    A strip at angle F illuminates a point at angle T with cosine factor
    |sin((T - F)/2)|; the sun sits in the strip at F = pi.
    """
    return (0.30
            + 1.00 * np.abs(np.sin((T - np.pi) / 2))
            + 0.34 * np.abs(np.sin((T - np.pi / 3) / 2))
            + 0.34 * np.abs(np.sin((T - 5 * np.pi / 3) / 2)))


# ------------------------------------------------------ deterministic hash --
def frac(x):
    return x - np.floor(x)


def hsh(k, s):
    return frac(np.sin(k * 12.9898 + s * 78.233) * 43758.5453)


def dens(Z):
    """Kept for families that are not surfaces; see `area` in scene.py."""
    return 1.0 / np.asarray(Z)


AIR = np.array([0.255, 0.205, 0.048])   # the far wall of the tube, read off
                                        # the painting: dark, warm, olive


def haze(Z, rgb, k=0.52):
    f = np.clip((Z - 0.45) / 4.0, 0, 1)[:, None] ** 0.80
    return rgb * (1 - k * f) + AIR * (k * f)
