"""Regenerative cooling of the aerospike: channel network, 1D coolant heat balance, drawing.

LEAP 71's own description of its methalox aerospikes: the outer chamber is cooled by
cryogenic methane, the spike by liquid oxygen. LEAP 71's cutaways (e.g. the dual-metal
Fraunhofer IGCV test part) show what that means in practice:
  * a copper (CuCrZr) liner on every hot-gas wall and inside every channel, steel outside
  * rows of small helical channels under the hot walls (cut across, they show up as a
    row of small arched holes)
  * ribbed toroidal manifolds, branching feed channels, and an injector face with many
    elements
  * an axial feed down the middle of the spike to its tip

This module builds such a network in the engine's half-section (geometry.py, units of L0)
and, every frame, runs a quasi-steady 1D energy balance along each circuit with the wall
heat flux from the flow solution:
    dQ = q(s) 2 pi r ds L0^2,   T_cool(s) = T_in + Q(s) / (mdot cp)
    T_wall,hot = T_cool + q (1/h_c + t_liner / k_Cu)
Both circuits run counterflow (coolant enters near the nozzle and leaves at the injector).
The layout is a plausible one in the style of LEAP 71's parts; the real channel
geometry of the 20 kN engine is not public.
"""
import math
import numpy as np
from PIL import ImageDraw
import geometry as G

# ------------------------------------------------------------------ properties (assumed)
OF = 3.3                 # oxidiser / fuel mass ratio
PC_NOMINAL = 46.4        # bar, the model's steady chamber pressure
C_STAR = 1800.0          # m/s, characteristic velocity of methalox at this pressure
CH4_IN, CH4_CP = 120.0, 3600.0    # K, J/kg/K (supercritical in the channels)
LOX_IN, LOX_CP = 95.0, 1700.0
H_COOL = 60e3            # W/m^2/K, coolant-side heat-transfer coefficient
T_LINER, K_CU = 0.8e-3, 320.0     # CuCrZr liner thickness (m) and conductivity (W/m/K)

LINER = 0.022            # liner thickness drawn (L0)
DEPTH = 0.030            # channel top below the hot wall (L0)


# ------------------------------------------------------------------ helpers
def _resample(P, step):
    P = np.asarray(P, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    n = max(2, int(s[-1] / step) + 1)
    si = np.linspace(0, s[-1], n)
    return np.stack([np.interp(si, s, P[:, 0]), np.interp(si, s, P[:, 1])], 1)


def _frame(P):
    t = np.gradient(P, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    n = np.stack([-t[:, 1], t[:, 0]], 1)          # left normal
    return t, n


def _arclen(P):
    return np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])


def _ellipse_pts(a0, a1, n, grow=0.0):
    a = np.linspace(a0, a1, n)
    return np.stack([G.CH_X + (G.CH_AX + grow) * np.cos(a), G.CH_R + (G.CH_AR + grow) * np.sin(a)], 1)


# ------------------------------------------------------------------ hot walls
def _hot_walls():
    """Gas-side walls in coolant-flow order (counterflow), with the gas-side normal.
    Returns {"ch4": (P, n_gas), "lox": (P, n_gas)}."""
    s = np.linspace(0.0, -G.L_P, 50)
    cowl = np.array([G._pt(si, G._halfw(si)) for si in s])            # lip -> chamber
    inner = np.array([G._pt(si, -G._halfw(si)) for si in s])         # throat -> chamber
    p_out = G._pt(-G.L_P, G._halfw(-G.L_P)); p_in = G._pt(-G.L_P, -G._halfw(-G.L_P))
    a0 = G._ang(p_out); a1 = G._ang(p_in)
    if a1 < a0: a1 += 2 * np.pi
    a_face0, a_face1 = 0.90 * np.pi, 1.10 * np.pi                     # injector face
    ch_out = _ellipse_pts(a0, a_face0, 60)                            # over the top to the face
    if a1 > 0: a1 -= 2 * np.pi
    ch_in = _ellipse_pts(a1, a_face1 - 2 * np.pi, 40)                 # under the bottom to the face
    spike = np.stack([G.SPIKE_X, G.SPIKE_R], 1)[::-1]                 # tip -> throat
    base = np.stack([np.full(12, G.X_SPIKE_END), np.linspace(0.12, G.R_BASE, 12)], 1)
    ch4 = _resample(np.concatenate([cowl, ch_out]), 0.01)
    lox = _resample(np.concatenate([base, spike, inner, ch_in]), 0.01)
    out = {}
    for k, P in (("ch4", ch4), ("lox", lox)):
        _, n = _frame(P)
        # gas side: test both normals, keep the one that is not in metal
        test = P + 0.02 * n
        sign = np.where(G.solid(test[:, 0], test[:, 1]), -1.0, 1.0)[:, None]
        out[k] = (P, n * sign)
    return out


# ------------------------------------------------------------------ network
class Network:
    def __init__(self):
        self.walls = _hot_walls()
        self.channels = {"ch4": [], "lox": []}
        for k in ("ch4", "lox"):
            P, ng = self.walls[k]
            s = _arclen(P)
            t, _ = _frame(P)
            pos = 0.03
            while pos < s[-1] - 0.03:
                i = int(np.searchsorted(s, pos))
                i = min(i, len(P) - 1)
                r = P[i, 1]
                # narrower, denser channels where the heat flux peaks (throat region)
                near_throat = math.exp(-((P[i, 0] - G.X_LIP) ** 2 + (r - G.R_LIP) ** 2) / 0.35)
                w = 0.048 - 0.020 * near_throat
                # metal available behind the wall: thin walls (the cowl at the lip) get
                # shallower channels, as in a real cowl
                th = 0.0
                for dd in np.arange(0.01, 0.20, 0.005):
                    q_ = P[i] - ng[i] * dd
                    if not G.solid(np.array([q_[0]]), np.array([q_[1]]))[0]: break
                    th = dd
                h = float(np.clip(0.45 * (th - 2 * LINER), 0.020, 0.042))
                depth = LINER + 0.010 if th < 0.16 else DEPTH
                c = P[i] - ng[i] * (depth + h / 2)
                corners = [c + ss * t[i] * w / 2 + tt * ng[i] * h / 2 for ss in (-1, 1) for tt in (-1, 1)]
                ok = all(G.solid(np.array([q[0]]), np.array([q[1]]))[0] for q in corners) and c[1] > 0.03
                if ok:
                    self.channels[k].append(dict(c=c, t=t[i].copy(), n=-ng[i].copy(), w=w, h=h,
                                                 wi=i, s=pos, r=r))
                pos += w + 0.014
        self._manifolds()
        self.windows = lattice_windows()

    def _manifolds(self):
        """Manifolds, transfer channels and the injector (positions in L0)."""
        cx, cr, ax, ar = G.CH_X, G.CH_R, G.CH_AX, G.CH_AR
        x_face = cx - ax
        self.inj_x = x_face - 0.20
        self.m_ch4_inj = (self.inj_x, cr + 0.15, 0.050)       # CH4 injector manifold (x, r, radius)
        self.m_lox_inj = (self.inj_x, cr - 0.13, 0.050)       # LOX injector manifold
        self.m_ch4_out = (x_face - 0.66, cr + 0.26, 0.15)     # ribbed CH4 collector torus
        self.m_lox_col = (x_face - 0.60, cr - 0.56, 0.12)     # LOX collector torus
        # CH4 inlet manifold: in the cowl, just upstream of the lip
        c0 = self.channels["ch4"][0]["c"]
        self.m_ch4_in = (c0[0] - 0.02, c0[1] + 0.06, 0.030)
        # LOX tip plenum (axisymmetric cavity inside the truncated base)
        self.plenum = (G.X_SPIKE_END - 0.32, G.X_SPIKE_END - 0.10, 0.0, 0.30)
        self.bore_r = 0.10
        last_ch4 = self.channels["ch4"][-1]["c"]
        last_lox = self.channels["lox"][-1]["c"]
        mo, ml, mi, mli = self.m_ch4_out, self.m_lox_col, self.m_ch4_inj, self.m_lox_inj
        # transfer paths (polylines), in flow order
        self.paths = {
            "ch4": [
                np.array([[self.m_ch4_in[0], self.m_ch4_in[1]], self.channels["ch4"][0]["c"]]),
                np.array([last_ch4, [last_ch4[0] - 0.18, last_ch4[1] + 0.10],
                          [mo[0] + mo[2] * 0.9, mo[1] + 0.05]]),
            ],
            "lox": [
                np.array([[G.X_BACK + 0.5, self.bore_r * 0.5], [self.plenum[0], self.bore_r * 0.5]]),
                np.array([[self.plenum[1], self.plenum[3] * 0.8], [G.X_SPIKE_END - 0.05, 0.16]]),
                np.array([last_lox, [last_lox[0] - 0.20, last_lox[1] - 0.12],
                          [ml[0] + ml[2] * 0.9, ml[1] + 0.03]]),
            ],
        }
        # branching feeds ("feathers") from the collectors to the injector manifolds
        def fan(src, dst, n, spread):
            out = []
            for k in range(n):
                f = (k - (n - 1) / 2) / max(1, (n - 1) / 2)
                mid = [(src[0] + dst[0]) / 2 + 0.02 * f, (src[1] + dst[1]) / 2 + spread * f]
                out.append(np.array([[src[0] + src[2] * 0.6, src[1]], mid, [dst[0] - dst[2] * 0.6, dst[1]]]))
            return out
        self.fans = {"ch4": fan(mo, mi, 5, 0.09), "lox": fan(ml, mli, 5, 0.09)}
        # injector elements: from each injector manifold to the face
        a_face = np.linspace(0.92 * np.pi, 1.08 * np.pi, 10)
        face = np.stack([cx + ax * np.cos(a_face), cr + ar * np.sin(a_face)], 1)
        self.elements = []
        for i, p in enumerate(face):
            kind = "ch4" if i % 2 == 0 else "lox"
            m = mi if kind == "ch4" else mli
            self.elements.append((kind, np.array([[m[0], m[1]], [p[0] + 0.015, p[1]]])))
        # flow-order arc length of every channel along its whole circuit
        for k in ("ch4", "lox"):
            pre = sum(float(np.sum(np.linalg.norm(np.diff(p, axis=0), axis=1)))
                      for p in self.paths[k][: (1 if k == "ch4" else 2)])
            for ch in self.channels[k]:
                ch["sf"] = pre + ch["s"]


def lattice_windows():
    """Lightening windows between ribs in the upper body, following the outer contour."""
    xs = np.linspace(-1.2, G.X_LIP - 0.45, 400)
    rr = np.where(xs < G.X_BULGE, G.r_body(xs), 0)
    cor = G.corner(400)
    out_x = np.concatenate([xs[xs < G.X_BULGE], cor[:, 0]])
    out_r = np.concatenate([rr[xs < G.X_BULGE], cor[:, 1]])
    keep = out_x <= G.X_LIP - 0.45
    P = np.stack([out_x[keep], out_r[keep]], 1)
    P = _resample(P, 0.01)
    t, n = _frame(P)
    n = -n if np.mean(n[:, 1]) > 0 else n          # inward normal
    s = _arclen(P)
    wins = []
    pos, k = 0.05, 0
    while pos < s[-1] - 0.25:
        i0 = int(np.searchsorted(s, pos)); i1 = int(np.searchsorted(s, pos + 0.20))
        if i1 >= len(P): break
        d0, d1 = 0.10, 0.27
        quad = [P[i0] + n[i0] * d0, P[i1] + n[i1] * d0, P[i1] + n[i1] * d1, P[i0] + n[i0] * d1]
        q = np.array(quad)
        clear = G.solid(q[:, 0], q[:, 1]).all()
        # keep clear of the chamber, its wall channels and the manifolds
        c = q.mean(0)
        far = (((c[0] - G.CH_X) / (G.CH_AX + 0.30)) ** 2 + ((c[1] - G.CH_R) / (G.CH_AR + 0.30)) ** 2) > 1
        if clear and far:
            wins.append(q)
        pos += 0.27
        k += 1
    return wins


NET = None


def network():
    global NET
    if NET is None:
        NET = Network()
    return NET


# ------------------------------------------------------------------ heat balance
class State:
    def __init__(self):
        self.Tc = {}; self.Tw = {}; self.q = {}
        self.out = {"ch4": CH4_IN, "lox": LOX_IN}
        self.peak_wall = 300.0
        self.Q = {"ch4": 0.0, "lox": 0.0}


def solve(run, f, pc_bar):
    """Quasi-steady coolant temperatures for one snapshot f (rho, p, Y, u, v, Z)."""
    net = network()
    rho, p, y, u, v = f[0], f[1], f[2], f[3], f[4]
    st = run.st; tw = run.tw
    L0 = G.L0_M
    qs = run.MWm2 * 1e6
    # the coolant is fed by the propellant supply at its nominal rate (not by Pc), so use the
    # model's steady chamber pressure for the flow rate
    mdot = PC_NOMINAL * 1e5 * G.A_THROAT * L0 ** 2 / C_STAR
    m_ch4 = mdot / (1 + OF); m_lox = mdot - m_ch4
    S = State()
    for k, (m, cp, T_in) in (("ch4", (m_ch4, CH4_CP, CH4_IN)), ("lox", (m_lox, LOX_CP, LOX_IN))):
        P, ng = net.walls[k]
        g_pts = P + 0.03 * ng
        ii = np.clip(((g_pts[:, 0] - run.xmin) / run.dx).astype(int), 0, run.nx - 1)
        jj = np.clip((g_pts[:, 1] / run.dx).astype(int), 0, run.nr - 1)
        yy = y[ii, jj]; Rm = run.r_mix(yy)
        cv = yy * run.r_e / (run.gam_e - 1) + (1 - yy) / (run.gam_a - 1)
        T = p[ii, jj] / (rho[ii, jj] * Rm)
        q = st * rho[ii, jj] * np.hypot(u[ii, jj], v[ii, jj]) * (cv + Rm) * np.maximum(T - tw, 0) * qs
        q = np.convolve(np.pad(q, 3, mode="edge"), np.ones(7) / 7, mode="valid")
        s = _arclen(P)
        dQ = q * 2 * np.pi * P[:, 1] * np.gradient(s) * L0 ** 2
        Qc = np.cumsum(dQ)
        Tc = T_in + Qc / (m * cp)
        Tw = Tc + q * (1 / H_COOL + T_LINER / K_CU)
        S.Tc[k], S.Tw[k], S.q[k] = Tc, Tw, q
        S.out[k] = float(Tc[-1]); S.Q[k] = float(Qc[-1])
    S.peak_wall = float(max(S.Tw["ch4"].max(), S.Tw["lox"].max()))
    return S


# ------------------------------------------------------------------ drawing
COOL = {"ch4": ((215, 95, 25), (255, 226, 160)), "lox": ((30, 95, 235), (190, 232, 255))}
STEEL = (56, 58, 68)
STEEL_HI = (92, 95, 108)


def _mix(a, b, u):
    u = min(max(u, 0.0), 1.0)
    return tuple(int(a[c] + (b[c] - a[c]) * u) for c in range(3))


def _blend(col, a, bg):
    return tuple(int(bg[c] + (col[c] - bg[c]) * a) for c in range(3))


def copper_glow(T):
    """CuCrZr colour by temperature: dull copper when cold, glowing orange-white near 1000 K."""
    u = (T - 300) / 700
    if u <= 0: return (150, 82, 52)
    if u < 0.6: return _mix((150, 82, 52), (235, 120, 45), u / 0.6)
    return _mix((235, 120, 45), (255, 228, 170), (u - 0.6) / 0.4)


def draw(d, run, S, view, size, origin, t, a, to_px, bg=(15, 14, 30), detail=1.0):
    """Draw the cooling network (both halves of the section)."""
    net = network()
    x0, x1 = view[0], view[1]
    sc = size[0] / (x1 - x0)
    top, bot = origin[1], origin[1] + size[1]

    def P(x, r, sgn):
        return to_px(view, size, origin, x, sgn * r)

    def vis(pt, m=4):
        return top + m <= pt[1] <= bot - m and -20 <= pt[0] <= size[0] + 20

    lw = lambda L: max(2, int(round(L * sc)))
    phase = t * 0.9
    dT = {"ch4": 200.0, "lox": 70.0}
    Tin = {"ch4": CH4_IN, "lox": LOX_IN}

    for sgn in (1, -1):
        # ---- lightening windows in the upper body (steel ribs between voids)
        for q in net.windows:
            pts = [P(px, pr, sgn) for px, pr in q]
            if any(vis(p_, 0) for p_ in pts):
                d.polygon(pts, fill=_blend((14, 13, 24), a, bg), outline=_blend(STEEL_HI, a, bg))
        # ---- axial LOX feed bore and tip plenum (copper-lined)
        bx0 = max(x0, G.X_BACK + 0.5)
        pa, pb = P(bx0, net.bore_r, sgn), P(net.plenum[0], net.bore_r, sgn)
        pc_ = P(net.plenum[0], 0.0, sgn)
        if sgn == 1:
            # bore drawn once as a band across the axis
            ya, yb = P(0, net.bore_r, 1)[1], P(0, -net.bore_r, 1)[1]
            xa, xb = pa[0], pb[0]
            if xb > 0:
                d.rectangle([xa, ya - lw(LINER), xb, yb + lw(LINER)], fill=_blend((150, 82, 52), a, bg))
                col = _mix(*COOL["lox"], 0.0)
                d.rectangle([xa, ya, xb, yb], fill=_blend(col, a, bg))
                # flow pulses down the bore
                L = (xb - xa)
                for k in range(int(L / 26) + 2):
                    xm = xa + ((k * 26 + phase * 60) % max(L, 1))
                    d.polygon([(xm + 7, (ya + yb) / 2), (xm - 4, ya + 2), (xm - 4, yb - 2)],
                              fill=_blend((220, 240, 255), a, bg))
                px0, px1 = P(net.plenum[0], 0, 1)[0], P(net.plenum[1], 0, 1)[0]
                pya, pyb = P(0, net.plenum[3], 1)[1], P(0, -net.plenum[3], 1)[1]
                d.rounded_rectangle([px0 - lw(LINER), pya - lw(LINER), px1 + lw(LINER), pyb + lw(LINER)],
                                    radius=lw(0.05), fill=_blend((150, 82, 52), a, bg))
                d.rounded_rectangle([px0, pya, px1, pyb], radius=lw(0.04), fill=_blend(col, a, bg))

        # ---- transfer channels, fans and injector elements
        for k in ("ch4", "lox"):
            cold, warm = COOL[k]
            Tout = S.out[k]
            for poly in net.paths[k] + net.fans[k]:
                pts = [P(px, pr, sgn) for px, pr in poly]
                if not any(vis(q) for q in pts): continue
                warmth = 0.0 if poly is net.paths[k][0] else (Tout - Tin[k]) / dT[k]
                col = _mix(cold, warm, warmth)
                wid = 0.032 if poly is net.paths[k][0] or any(poly is p_ for p_ in net.paths[k]) else 0.018
                d.line(pts, fill=_blend((175, 98, 60), a, bg), width=lw(wid) + 2 * max(1, lw(LINER * 0.5)), joint="curve")
                d.line(pts, fill=_blend(col, a, bg), width=lw(wid), joint="curve")
            for kind, poly in net.elements:
                if kind != k: continue
                pts = [P(px, pr, sgn) for px, pr in poly]
                if vis(pts[0]) and vis(pts[1]):
                    col = _mix(cold, warm, (Tout - Tin[k]) / dT[k])
                    d.line(pts, fill=_blend(col, a, bg), width=max(2, lw(0.014)))

        # ---- manifolds (copper-lined toroids; the CH4 collector has internal ribs)
        for k, m, ribs in (("ch4", net.m_ch4_in, 0), ("ch4", net.m_ch4_out, 8), ("lox", net.m_lox_col, 6),
                           ("ch4", net.m_ch4_inj, 0), ("lox", net.m_lox_inj, 0)):
            c = P(m[0], m[1], sgn)
            R = m[2] * sc
            if not vis(c, R * 0.3): continue
            cold, warm = COOL[k]
            warmth = 0.0 if m is net.m_ch4_in else (S.out[k] - Tin[k]) / dT[k]
            Rl = R + lw(LINER)
            d.ellipse([c[0] - Rl, c[1] - Rl, c[0] + Rl, c[1] + Rl], fill=_blend((150, 82, 52), a, bg))
            d.ellipse([c[0] - R, c[1] - R, c[0] + R, c[1] + R], fill=_blend(_mix(cold, warm, warmth), a, bg))
            for rb in range(ribs):
                ang = 2 * math.pi * rb / ribs + 0.3
                d.line([(c[0] + 0.25 * R * math.cos(ang), c[1] + 0.25 * R * math.sin(ang)),
                        (c[0] + R * math.cos(ang), c[1] + R * math.sin(ang))],
                       fill=_blend((150, 82, 52), a, bg), width=max(2, lw(0.02)))
            if ribs:
                d.ellipse([c[0] - 0.28 * R, c[1] - 0.28 * R, c[0] + 0.28 * R, c[1] + 0.28 * R],
                          fill=_blend(STEEL, a, bg), outline=_blend((150, 82, 52), a, bg), width=2)

        # ---- copper liner on the hot walls, coloured by the computed wall temperature
        for k in ("ch4", "lox"):
            Pw, ng = net.walls[k]
            Tw = S.Tw[k]
            step = 3
            for i in range(0, len(Pw) - step, step):
                pa_ = P(Pw[i, 0] - ng[i, 0] * LINER / 2, Pw[i, 1] - ng[i, 1] * LINER / 2, sgn)
                pb_ = P(Pw[i + step, 0] - ng[i + step, 0] * LINER / 2, Pw[i + step, 1] - ng[i + step, 1] * LINER / 2, sgn)
                if vis(pa_) and vis(pb_):
                    d.line([pa_, pb_], fill=_blend(copper_glow(Tw[i]), a, bg), width=lw(LINER) + 1)

        # ---- channel rows: copper-lined cross-sections of the helical channels
        for k in ("ch4", "lox"):
            cold, warm = COOL[k]
            Tc = S.Tc[k]
            for ch in net.channels[k]:
                c, tt, nn, w, h = ch["c"], ch["t"], ch["n"], ch["w"], ch["h"]
                quad = [c + s1 * tt * w / 2 + s2 * nn * h / 2 for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
                pts = [P(q[0], q[1], sgn) for q in quad]
                if not all(vis(q, 1) for q in pts): continue
                warmth = (Tc[ch["wi"]] - Tin[k]) / dT[k]
                col = _mix(cold, warm, warmth)
                # travelling pulse in the flow direction
                pulse = 0.5 + 0.5 * math.cos(2 * math.pi * ((ch["sf"] - phase) / 0.55))
                col = _mix(col, (255, 255, 255), 0.30 * pulse ** 6)
                d.polygon(pts, fill=_blend(col, a, bg), outline=_blend((175, 98, 60), a, bg))
