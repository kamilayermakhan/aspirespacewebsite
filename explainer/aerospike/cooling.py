"""Regenerative cooling after the corrected scheme: channels inside the walls, hot gas outside.

LEAP 71: the outer chamber is cooled by the cryogenic methane fuel, and the spike (the
central body) by liquid oxygen. In the half-section of geometry.py (units of L0):

  methane (outer shell): enters at the lip, runs back through channels in the outer shell
      under its hot face -- the throat, the annular passage, the outer wall of the ring
      chamber -- to the head end, then behind the injector face into the injector
  oxygen (central body): enters along the axis, runs inside the central body to its tip,
      turns there, and comes back through channels under the central body's hot surface --
      along the slender spike, the passage, the inner wall of the ring chamber -- to the
      head end, then into the injector
  hot gas: only in the ring chamber and the annular passage, and outside after the lip

The channel routing and sizes are notional (as in the scheme); the 20 kN engine's own
channel geometry is not public.

Every frame:
  1. 1D energy balance of each coolant along its circuit, with the flow solution's wall heat
     flux: T_cool(s) = T_in + Q(s) / (mdot cp).
  2. Steady conduction in the metal (copper liner and channel walls, steel elsewhere), with
     hot-gas convection q = h_g (T_gas - T_wall) from the flow solution and coolant
     convection q = h_c (T_wall - T_cool). Solved once at full pressure and once chilled
     down; frames in between are blended by the current heat load.
"""
import math
import os
import numpy as np
from PIL import Image, ImageDraw
import geometry as G

# ------------------------------------------------------------------ properties (assumed)
OF = 3.3
C_STAR = 1800.0
PC_NOMINAL = 46.4        # bar, the model's steady chamber pressure (sets the coolant flow)
CH4_IN, CH4_CP = 120.0, 3600.0
LOX_IN, LOX_CP = 95.0, 1700.0
H_CHAN = 60e3            # W/m^2/K, wall channels
H_FEED = 8e3             # W/m^2/K, slow flow in the axial feed, manifolds and tip plenum
K_CU, K_STEEL = 320.0, 20.0
T_LINER = 0.8e-3
P_ATM, T_AMB = 101325.0, 300.0

LINER = 0.022            # hot-wall liner (L0)
BAND0, BAND_H = 0.040, 0.060   # channel band: depth of its hot side, height
RIB_PITCH = 0.065        # ribs between channels (drawn)


# ------------------------------------------------------------------ helpers
def _resample(P, step):
    P = np.asarray(P, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    keep = np.concatenate([[True], seg > 1e-9])
    P = P[keep]; seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    n = max(2, int(s[-1] / step) + 1)
    si = np.linspace(0, s[-1], n)
    return np.stack([np.interp(si, s, P[:, 0]), np.interp(si, s, P[:, 1])], 1)


def _frame(P):
    t = np.gradient(P, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    return t, np.stack([-t[:, 1], t[:, 0]], 1)


def _arclen(P):
    return np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])


def _gas_normal(P):
    _, n = _frame(P)
    test = P + 0.02 * n
    sign = np.where(G.solid(test[:, 0], test[:, 1]), -1.0, 1.0)[:, None]
    return n * sign


def _smooth_normals(n, k=7):
    out = np.stack([np.convolve(np.pad(n[:, c], k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), mode="valid")
                    for c in range(2)], 1)
    return out / np.linalg.norm(out, axis=1)[:, None]


# ------------------------------------------------------------------ hot walls in coolant-flow order
def _hot_walls():
    outer_w, inner_w, _ = G.passage_walls(160)
    a1 = np.linspace(np.pi / 2, np.pi, 16)
    top_corner = np.stack([G.CH_X0 + G.CH_RC + G.CH_RC * np.cos(a1), G.CH_R1 - G.CH_RC + G.CH_RC * np.sin(a1)], 1)
    a2 = np.linspace(np.pi, 1.5 * np.pi, 16)
    bot_corner = np.stack([G.CH_X0 + G.CH_RC + G.CH_RC * np.cos(a2), G.CH_R0 + G.CH_RC + G.CH_RC * np.sin(a2)], 1)
    # methane: lip -> throat -> passage outer wall -> chamber outer wall -> top of the injector face
    ch4 = np.concatenate([outer_w[::-1], [[G.CH_X1, G.CH_R1]], top_corner])
    # oxygen: tip -> slender body -> throat inner point -> passage inner wall -> chamber inner wall
    spike = np.stack([G.SPIKE_X, G.SPIKE_R], 1)[::-1]
    lox = np.concatenate([spike, inner_w[::-1], [[G.CH_X1, G.CH_R0]], bot_corner[::-1]])
    out = {}
    for k, P in (("ch4", ch4), ("lox", lox)):
        P = _resample(P, 0.01)
        out[k] = (P, _smooth_normals(_gas_normal(P)))
    return out


class Network:
    def __init__(self):
        self.walls = _hot_walls()
        # channel bands inside the walls, following the hot face
        self.band = {}
        for k in ("ch4", "lox"):
            P, ng = self.walls[k]
            a = P - ng * BAND0
            b = P - ng * (BAND0 + BAND_H)
            if k == "lox":
                # the slender central body: keep the band clear of the axial feed
                rmin = 0.11
                a[:, 1] = np.maximum(a[:, 1], rmin + BAND_H + 0.02)
                b[:, 1] = np.maximum(b[:, 1], rmin + 0.02)
            self.band[k] = (a, b)
        s_ch4 = _arclen(self.walls["ch4"][0]); s_lox = _arclen(self.walls["lox"][0])
        self.s = {"ch4": s_ch4, "lox": s_lox}
        self.ribs = {k: [int(np.searchsorted(self.s[k], v)) for v in np.arange(RIB_PITCH, self.s[k][-1], RIB_PITCH)]
                     for k in ("ch4", "lox")}
        # oxygen supply along the axis and the turn at the tip
        self.bore_r = 0.085
        self.bore = np.array([[G.X_HEAD - 0.6, 0.0], [G.X_SPIKE_END - 0.16, 0.0]])
        self.tip_turn = (G.X_SPIKE_END - 0.16, G.X_SPIKE_END - 0.06, 0.0, 0.22)   # plenum x0, x1, r0, r1
        # methane inlet at the lip (fed from outside through the shoulder)
        a, b = self.band["ch4"]
        c0 = 0.5 * (a[3] + b[3])
        self.m_ch4_in = (c0[0] - 0.05, c0[1] + 0.10, 0.045)
        sh = G.shoulder(80)
        port = sh[np.argmin(np.hypot(sh[:, 0] - self.m_ch4_in[0], sh[:, 1] - self.m_ch4_in[1]))]
        out_dir = port - np.array(self.m_ch4_in[:2]); out_dir /= np.linalg.norm(out_dir)
        self.ch4_feed = np.array([port + out_dir * 0.35, port, self.m_ch4_in[:2]])
        # injector manifolds behind the injector face, and the elements through the face
        xm = G.CH_X0 - 0.20
        self.m_ch4_inj = (xm, G.CH_R1 - 0.27, 0.06)
        self.m_lox_inj = (xm, G.CH_R0 + 0.27, 0.06)
        aE, bE = self.band["ch4"]; aL, bL = self.band["lox"]
        eE = 0.5 * (aE[-1] + bE[-1]); eL = 0.5 * (aL[-1] + bL[-1])
        self.ch4_down = np.array([eE, [xm, eE[1]], self.m_ch4_inj[:2]])
        self.lox_up = np.array([eL, [xm, eL[1]], self.m_lox_inj[:2]])
        self.elements = []
        for kind, m, rs in (("ch4", self.m_ch4_inj, (G.CH_R1 - 0.20, G.CH_R1 - 0.34)),
                            ("lox", self.m_lox_inj, (G.CH_R0 + 0.20, G.CH_R0 + 0.34))):
            for rr in rs:
                self.elements.append((kind, np.array([[m[0], m[1]], [m[0] + 0.06, rr], [G.CH_X0 + 0.005, rr]])))

    # -------------------------------------------------------------- coolant cells on a grid
    def coolant_mask(self, xc, rc):
        nx, nr = len(xc), len(rc)
        dx = xc[1] - xc[0]
        lab = Image.new("L", (nx, nr), 0); hcf = Image.new("L", (nx, nr), 0)
        dl, dh = ImageDraw.Draw(lab), ImageDraw.Draw(hcf)
        def px(p): return ((p[0] - xc[0]) / dx + 0.5, (p[1] - rc[0]) / dx + 0.5)
        def poly(dr, pts, val): dr.polygon([px(p) for p in pts], fill=val)
        def line(dr, pts, val, w): dr.line([px(p) for p in pts], fill=val, width=max(1, int(round(w / dx))))
        def circ(dr, m, val):
            c = px(m[:2]); R = max(m[2] / dx, 1)
            dr.ellipse([c[0] - R, c[1] - R, c[0] + R, c[1] + R], fill=val)
        for k, lv in (("ch4", 1), ("lox", 2)):
            a, b = self.band[k]
            for i0 in range(0, len(a) - 1, 40):
                i1 = min(i0 + 41, len(a))
                seg = np.concatenate([a[i0:i1], b[i0:i1][::-1]])
                poly(dl, seg, lv); poly(dh, seg, 1)
        line(dl, self.ch4_feed[1:], 1, 0.05); line(dh, self.ch4_feed[1:], 2, 0.05)
        circ(dl, self.m_ch4_in, 1); circ(dh, self.m_ch4_in, 2)
        for pth, lv in ((self.ch4_down, 1), (self.lox_up, 2)):
            line(dl, pth, lv, 0.05); line(dh, pth, 2, 0.05)
        for m, lv in ((self.m_ch4_inj, 1), (self.m_lox_inj, 2)):
            circ(dl, m, lv); circ(dh, m, 2)
        line(dl, self.bore, 2, 2 * self.bore_r); line(dh, self.bore, 2, 2 * self.bore_r)
        x0, x1, r0, r1 = self.tip_turn
        box = [[x0, 0], [x1, 0], [x1, r1], [x0, r1]]
        poly(dl, box, 2); poly(dh, box, 2)
        L = np.asarray(lab).T.copy(); Hc = np.asarray(hcf).T.copy()
        hmap = np.select([Hc == 1, Hc == 2], [H_CHAN, H_FEED], 0.0)
        return L, hmap, np.zeros_like(L, bool)


NET = None


def network():
    global NET
    if NET is None:
        NET = Network()
    return NET


# ------------------------------------------------------------------ 1D coolant balance
class State:
    pass


def _gas_htc(run, f):
    rho, p, y, u, v = f[0], f[1], f[2], f[3], f[4]
    Rm = run.r_mix(y)
    cv = y * run.r_e / (run.gam_e - 1) + (1 - y) / (run.gam_a - 1)
    Tg = p / (rho * Rm)
    hg = run.st * rho * np.hypot(u, v) * (cv + Rm) * P_ATM * run.u_ref / T_AMB
    return hg, Tg * T_AMB


def wall_q(run, f, P, ng, Tw=800.0):
    rho, p, y, u, v = f[0], f[1], f[2], f[3], f[4]
    g = P + 0.03 * ng
    ii = np.clip(((g[:, 0] - run.xmin) / run.dx).astype(int), 0, run.nx - 1)
    jj = np.clip((g[:, 1] / run.dx).astype(int), 0, run.nr - 1)
    yy = y[ii, jj]; Rm = run.r_mix(yy)
    cv = yy * run.r_e / (run.gam_e - 1) + (1 - yy) / (run.gam_a - 1)
    Tg = p[ii, jj] / (rho[ii, jj] * Rm) * T_AMB
    hg = run.st * rho[ii, jj] * np.hypot(u[ii, jj], v[ii, jj]) * (cv + Rm) * P_ATM * run.u_ref / T_AMB
    q = hg * np.maximum(Tg - Tw, 0)
    return np.convolve(np.pad(q, 3, mode="edge"), np.ones(7) / 7, mode="valid")


def solve(run, f):
    net = network()
    L0 = G.L0_M
    mdot = PC_NOMINAL * 1e5 * G.A_THROAT * L0 ** 2 / C_STAR
    m = {"ch4": mdot / (1 + OF)}; m["lox"] = mdot - m["ch4"]
    cp = {"ch4": CH4_CP, "lox": LOX_CP}; T_in = {"ch4": CH4_IN, "lox": LOX_IN}
    S = State(); S.Tc, S.Tw, S.q, S.out = {}, {}, {}, {}
    S.Q = 0.0
    for k in ("ch4", "lox"):
        P, ng = net.walls[k]
        q = wall_q(run, f, P, ng)
        Qc = np.cumsum(q * 2 * np.pi * P[:, 1] * np.gradient(net.s[k]) * L0 ** 2)
        S.Tc[k] = T_in[k] + Qc / (m[k] * cp[k])
        S.Tw[k] = S.Tc[k] + q * (1 / H_CHAN + T_LINER / K_CU)
        S.q[k] = q
        S.out[k] = float(S.Tc[k][-1])
        S.Q += float(Qc[-1])
    S.peak_wall = float(max(S.Tw["ch4"].max(), S.Tw["lox"].max()))
    S.m = m
    return S


# ------------------------------------------------------------------ steady conduction in the metal
def conduction(run, f, S, hot=True, iters=5000, omega=1.93, verbose=False):
    net = network()
    nx, nr = run.nx, run.nr
    dxm = run.dx * G.L0_M
    lab, hmap, _ = net.coolant_mask(run.xc, run.rc)
    solid = run.solid
    cool = solid & (lab > 0)
    metal = solid & ~cool
    gas = ~solid
    T_cool = np.zeros((nx, nr))
    for k, lv, T_in in (("ch4", 1, CH4_IN), ("lox", 2, LOX_IN)):
        a, b = net.band[k]
        pts = 0.5 * (a + b)[::3]; vals = S.Tc[k][::3]
        inj = np.array(net.m_ch4_inj[:2]) if k == "ch4" else np.array(net.m_lox_inj[:2])
        pts = np.concatenate([pts, [inj]]); vals = np.concatenate([vals, [S.out[k]]])
        ci, cj = np.where(cool & (lab == lv))
        X, R = run.xc[ci], run.rc[cj]
        Tk = np.empty(len(ci)); dmin = np.empty(len(ci))
        for s0 in range(0, len(ci), 6000):
            dd = (X[s0:s0 + 6000, None] - pts[None, :, 0]) ** 2 + (R[s0:s0 + 6000, None] - pts[None, :, 1]) ** 2
            j = np.argmin(dd, axis=1)
            Tk[s0:s0 + 6000] = vals[j]; dmin[s0:s0 + 6000] = np.sqrt(dd[np.arange(len(j)), j])
        Tk = np.where(dmin > 0.10, T_in, Tk)          # supply lines: inlet temperature
        T_cool[ci, cj] = Tk

    def dil(mk, n):
        o = mk.copy()
        for _ in range(n):
            o2 = o.copy(); o2[1:] |= o[:-1]; o2[:-1] |= o[1:]; o2[:, 1:] |= o[:, :-1]; o2[:, :-1] |= o[:, 1:]; o = o2
        return o
    copper = metal & (dil(gas, 3) | dil(cool, 2))
    k_ = np.where(copper, K_CU, K_STEEL)
    if hot:
        hg, Tg = _gas_htc(run, f)
    else:
        hg = np.zeros((nx, nr)); Tg = np.zeros((nx, nr))

    def nb(arr, di, dj, fill=0):
        o = np.full_like(arr, fill)
        if di == 1: o[:-1] = arr[1:]
        elif di == -1: o[1:] = arr[:-1]
        elif dj == 1: o[:, :-1] = arr[:, 1:]
        elif dj == -1: o[:, 1:] = arr[:, :-1]
        return o
    rcm = run.rc[None, :] * G.L0_M * np.ones((nx, 1))
    area = {(1, 0): rcm * dxm, (-1, 0): rcm * dxm,
            (0, 1): (rcm + dxm / 2) * dxm, (0, -1): np.maximum(rcm - dxm / 2, 0) * dxm}
    Gmm = []
    Gsum = np.zeros((nx, nr)); Bsum = np.zeros((nx, nr))
    for (di, dj), A in area.items():
        mn, cn, gn = nb(metal, di, dj, False), nb(cool, di, dj, False), nb(gas, di, dj, False)
        kn = nb(k_, di, dj, K_STEEL)
        kf = 2 * k_ * kn / (k_ + kn)
        g_m = np.where(metal & mn, kf * A / dxm, 0.0)
        hn = np.maximum(nb(hmap, di, dj), 1.0)
        g_c = np.where(metal & cn, A / (dxm / (2 * k_) + 1.0 / hn), 0.0)
        hgn = nb(hg, di, dj); Tgn = nb(Tg, di, dj)
        g_g = np.where(metal & gn, A / (dxm / (2 * k_) + 1.0 / np.maximum(hgn, 1e-3)), 0.0)
        Gmm.append((di, dj, g_m))
        Gsum += g_m + g_c + g_g
        Bsum += g_c * nb(T_cool, di, dj) + g_g * Tgn
    iso = metal & (Gsum <= 0)
    Gsum = np.where(Gsum > 0, Gsum, 1.0)
    T = np.where(metal, 0.5 * (CH4_IN + LOX_IN), 0.0)
    red = ((np.arange(nx)[:, None] + np.arange(nr)[None, :]) % 2 == 0)
    for it in range(iters):
        for colour in (red, ~red):
            acc = Bsum.copy()
            for di, dj, g in Gmm:
                acc += g * nb(T, di, dj)
            upd = metal & colour & ~iso
            T = np.where(upd, T + omega * (acc / Gsum - T), T)
        if verbose and it % 500 == 0:
            print("  iter", it, "T range %.0f-%.0f K" % (float(T[metal].min()), float(T[metal].max())), flush=True)
    out = np.full((nx, nr), np.nan)
    out[metal] = T[metal]
    out[cool] = T_cool[cool]
    return out, copper, cool


def thermal_fields(run, avg_from=12.0, avg_to=20.0, iters=5000, verbose=False):
    """Full-pressure and chilled-down metal temperatures (cached in the run directory)."""
    fn = os.path.join(run.d, "thermal.npz")
    if os.path.exists(fn):
        return dict(np.load(fn))
    ks = [k for k in range(len(run.t)) if avg_from <= run.t[k] <= avg_to][::8]
    f = np.mean([run.fields(k) for k in ks], axis=0)
    S = solve(run, f)
    T_hot, copper, cool = conduction(run, f, S, hot=True, iters=iters, verbose=verbose)
    S0 = solve(run, f * np.array([1, 1, 0, 1, 1, 0])[:, None, None])
    T_cold, _, _ = conduction(run, f, S0, hot=False, iters=max(600, iters // 6), verbose=verbose)
    out = dict(T_hot=T_hot, T_cold=T_cold, copper=copper, cool=cool, Q_hot=S.Q,
               ch4_out=S.out["ch4"], lox_out=S.out["lox"])
    np.savez_compressed(fn, **out)
    return out


# ------------------------------------------------------------------ drawing
COOL = {"ch4": ((168, 110, 255), (236, 214, 255)), "lox": ((40, 150, 255), (200, 236, 255))}
HOTGAS = (255, 186, 120)
STEEL = (56, 58, 68)
CU = (175, 98, 60)

# CuCrZr: copper colour when cold (frosted darker at cryogenic temperature), glowing when hot
_TMAP = [(80, (122, 80, 66)), (150, (146, 90, 64)), (300, (178, 106, 66)), (450, (198, 104, 52)),
         (600, (226, 120, 50)), (780, (248, 172, 80)), (950, (255, 236, 190))]


def metal_rgb(T):
    T = np.asarray(T, np.float32)
    xs = np.array([a for a, _ in _TMAP], np.float32)
    out = np.empty(T.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(T, xs, np.array([b[c] for _, b in _TMAP], np.float32))
    return out


def _mix(a, b, u):
    u = min(max(u, 0.0), 1.0)
    return tuple(int(a[c] + (b[c] - a[c]) * u) for c in range(3))


def _blend(col, a, bg):
    return tuple(int(bg[c] + (col[c] - bg[c]) * a) for c in range(3))


def copper_glow(T):
    u = (T - 300) / 700
    if u <= 0: return (150, 82, 52)
    if u < 0.6: return _mix((150, 82, 52), (235, 120, 45), u / 0.6)
    return _mix((235, 120, 45), (255, 228, 170), (u - 0.6) / 0.4)


def draw(d, S, view, size, origin, t, a, to_px, bg=(15, 14, 30)):
    """Both coolant circuits inside the walls (both halves of the section)."""
    net = network()
    x0, x1 = view[0], view[1]
    sc = size[0] / (x1 - x0)
    top, bot = origin[1], origin[1] + size[1]
    def P(x, r, sgn): return to_px(view, size, origin, x, sgn * r)
    def vis(pt, m=3): return top + m <= pt[1] <= bot - m and -40 <= pt[0] <= size[0] + 40
    lw = lambda L: max(1, int(round(L * sc)))
    phase = t * 0.55
    dT = {"ch4": 120.0, "lox": 60.0}
    T_in = {"ch4": CH4_IN, "lox": LOX_IN}
    cu = _blend(CU, a, bg)
    def ccol(k, T): return _blend(_mix(*COOL[k], (T - T_in[k]) / dT[k]), a, bg)

    def arrow(pa_, pb_, k, hs):
        L_ = math.hypot(pb_[0] - pa_[0], pb_[1] - pa_[1]) or 1
        ux, uy = (pb_[0] - pa_[0]) / L_, (pb_[1] - pa_[1]) / L_
        xb, yb = pb_
        d.polygon([(xb + ux * hs, yb + uy * hs), (xb - ux * hs - uy * hs * 0.75, yb - uy * hs + ux * hs * 0.75),
                   (xb - ux * hs + uy * hs * 0.75, yb - uy * hs - ux * hs * 0.75)],
                  fill=_blend(_mix(COOL[k][1], (255, 255, 255), 0.6), a, bg))

    for sgn in (1, -1):
        def path_line(pts_w, k, T, width, arrows=True, spacing=0.40):
            pts = [P(p[0], p[1], sgn) for p in pts_w]
            if not any(vis(q) for q in pts): return
            d.line(pts, fill=cu, width=lw(width) + 2, joint="curve")
            d.line(pts, fill=ccol(k, T), width=lw(width), joint="curve")
            if arrows:
                s = _arclen(np.asarray(pts_w, float))
                for s_ar in np.arange(spacing / 2, s[-1], spacing):
                    sv = (s_ar + phase) % s[-1]
                    m = min(max(int(np.searchsorted(s, sv)), 1), len(pts) - 1)
                    if vis(pts[m], 6): arrow(pts[m - 1], pts[m], k, max(3, lw(width) * 1.2))
        # channel bands (continuous, ribs between channels), coolant coloured by its temperature
        for k in ("ch4", "lox"):
            A_, B_ = net.band[k]
            Tc = S.Tc[k]
            n = len(A_)
            for i0 in range(0, n - 1, 6):
                i1 = min(i0 + 7, n)
                seg = np.concatenate([A_[i0:i1], B_[i0:i1][::-1]])
                pts = [P(p[0], p[1], sgn) for p in seg]
                if not any(vis(q, 0) for q in pts): continue
                pulse = 0.5 + 0.5 * math.cos(2 * math.pi * (net.s[k][i0] - phase * 1.6) / 0.5)
                col = _mix(_mix(*COOL[k], (Tc[i0] - T_in[k]) / dT[k]), (255, 255, 255), 0.28 * pulse ** 8)
                d.polygon(pts, fill=_blend(col, a, bg))
            for edge in (A_, B_):
                pts = [P(p[0], p[1], sgn) for p in edge[::3]]
                if any(vis(q, 0) for q in pts):
                    d.line(pts, fill=cu, width=max(1, lw(0.010)), joint="curve")
            for i in net.ribs[k]:
                pa_, pb_ = P(*A_[i], sgn), P(*B_[i], sgn)
                if vis(pa_, 0): d.line([pa_, pb_], fill=cu, width=max(1, lw(0.010)))
            Mid = 0.5 * (A_ + B_)
            for s_ar in np.arange(0.2, net.s[k][-1], 0.55):
                sv = (s_ar + phase) % net.s[k][-1]
                m = min(max(int(np.searchsorted(net.s[k], sv)), 2), n - 1)
                pa_, pb_ = P(*Mid[m - 2], sgn), P(*Mid[m], sgn)
                if vis(pb_, 6): arrow(pa_, pb_, k, max(3, lw(BAND_H) * 0.55))
        # methane supply at the lip, injector manifolds and elements
        path_line(net.ch4_feed, "ch4", CH4_IN, 0.05, spacing=0.25)
        for mfd, k, T in ((net.m_ch4_in, "ch4", CH4_IN), (net.m_ch4_inj, "ch4", S.out["ch4"]),
                          (net.m_lox_inj, "lox", S.out["lox"])):
            c = P(mfd[0], mfd[1], sgn); R = mfd[2] * sc
            if vis(c, 0):
                d.ellipse([c[0] - R - 2, c[1] - R - 2, c[0] + R + 2, c[1] + R + 2], fill=cu)
                d.ellipse([c[0] - R, c[1] - R, c[0] + R, c[1] + R], fill=ccol(k, T))
        path_line(net.ch4_down, "ch4", S.out["ch4"], 0.05, spacing=0.3)
        path_line(net.lox_up, "lox", S.out["lox"], 0.05, spacing=0.3)
        for kind, poly in net.elements:
            path_line(poly, kind, S.out[kind], 0.03, arrows=False)
        # oxygen: turn at the tip
        xa_, xb_, _, r1 = net.tip_turn
        pa_, pb_ = P(xa_, r1, sgn), P(xb_, 0.0, sgn)
        if vis(pa_, 0) or vis(pb_, 0):
            box = [min(pa_[0], pb_[0]), min(pa_[1], pb_[1]), max(pa_[0], pb_[0]), max(pa_[1], pb_[1])]
            d.rectangle([box[0] - 2, box[1] - 2, box[2] + 2, box[3] + 2], fill=cu)
            d.rectangle(box, fill=ccol("lox", LOX_IN))
    # oxygen supply along the axis (drawn once, across the axis)
    xa_ = P(max(x0 - 1, net.bore[0, 0]), 0, 1)[0]; xb_ = P(net.bore[1, 0], 0, 1)[0]
    ya = P(0, net.bore_r, 1)[1]; yb = P(0, -net.bore_r, 1)[1]
    if xb_ > 0 and ya < bot and yb > top:
        d.rectangle([xa_, ya - 2, xb_, yb + 2], fill=cu)
        d.rectangle([xa_, ya, xb_, yb], fill=ccol("lox", LOX_IN))
        L = xb_ - xa_
        sp_ = max(26, int(0.5 * sc))
        hs = max(3, (yb - ya) * 0.45)
        for kk in range(int(L / sp_) + 2):
            xm = xa_ + ((kk * sp_ + phase * sc) % max(L, 1))
            d.polygon([(xm + hs, (ya + yb) / 2), (xm - hs * 0.6, ya + 1), (xm - hs * 0.6, yb - 1)],
                      fill=_blend((230, 245, 255), a, bg))
