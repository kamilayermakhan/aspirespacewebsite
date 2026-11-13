"""Compose the aerospike explainer (1080x1920, 30 fps).

usage: python3 make_video.py RUN_DIR FOOTAGE.mp4 OUT.mp4 [--preview t1,t2,...]

Structure follows the bell-nozzle reference: full-frame start-up simulation
with captions and live stats, then simulation vs. real hot fire in a split
layout, then a loop back to the first frame.
"""
import os, sys, json, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import geometry as G
import cooling as CL

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts")
W, H, FPS = 1080, 1920, 30

# ------------------------------------------------------------------ physics scale
GAM = 1.2
P_ATM = 101325.0
T_AMB = 300.0
U_REF = math.sqrt(287.0 * T_AMB)        # velocity unit (p = rho T, air gas constant)

# ------------------------------------------------------------------ palette
BG = (9, 8, 20)
PANEL = (8, 7, 24)
INK = (236, 232, 244)
DIM = (128, 124, 146)
FAINT = (78, 75, 96)
LAV = (183, 166, 255)
STOPS = [(0.00, PANEL), (0.10, (30, 24, 70)), (0.28, (70, 56, 150)),
         (0.50, (130, 112, 220)), (0.70, (188, 172, 250)), (0.86, (226, 218, 255)),
         (1.00, (252, 250, 255))]
_lut = np.zeros((1024, 3), np.float32)
for c in range(3):
    _lut[:, c] = np.interp(np.linspace(0, 1, 1024), [s[0] for s in STOPS], [s[1][c] for s in STOPS])


def font(name, size):
    files = {"mono": "jost-latin-400-normal.woff", "monom": "jost-latin-500-normal.woff",
             "serifb": "jost-latin-600-normal.woff", "serifi": "jost-latin-400-italic.woff",
             "sans": "jost-latin-500-normal.woff", "sansr": "jost-latin-400-normal.woff"}
    return ImageFont.truetype(os.path.join(FONT, files[name]), size)


F_LABEL = font("monom", 22)
F_SMALL = font("monom", 16)
F_TINY = font("mono", 14)
F_TITLE = font("serifb", 60)
F_SUB = font("serifi", 31)
F_CAP = font("serifi", 35)
F_CAPB = font("serifi", 33)
F_VAL = font("sans", 46)
F_VALB = font("sans", 33)
F_UNIT = font("sansr", 17)
F_ANN = font("monom", 16)


def spaced(d, xy, text, f, fill, sp=2.0, anchor="l", stroke=0):
    """Letter-spaced text. anchor l/r/m for x."""
    x, y = xy
    widths = [d.textlength(ch, font=f) for ch in text]
    total = sum(widths) + sp * (len(text) - 1)
    if anchor == "r": x -= total
    if anchor == "m": x -= total / 2
    xs = []
    for w in widths:
        xs.append(x); x += w + sp
    if stroke:
        for ch, xx in zip(text, xs):
            d.text((xx, y), ch, font=f, fill=(8, 7, 20), stroke_width=stroke, stroke_fill=(8, 7, 20))
    for ch, xx in zip(text, xs):
        d.text((xx, y), ch, font=f, fill=fill)
    return total


def fmt(v, nd=0):
    return f"{v:,.{nd}f}"


def ease(s):
    s = min(max(s, 0.0), 1.0)
    return s * s * (3 - 2 * s)


def lerp_map(t, pts):
    """piecewise-linear map through (t, value) points."""
    xs, ys = zip(*pts)
    return float(np.interp(t, xs, ys))


def alpha_blend(fill, a, bg=BG):
    return tuple(int(bg[i] + (fill[i] - bg[i]) * a) for i in range(3))


# ------------------------------------------------------------------ simulation data
class Run:
    """Snapshots (float16: rho, p, Y, u, v, Z) and the solver log of one case."""
    NV = 6

    def __init__(self, d):
        self.d = d
        g = np.load(os.path.join(d, "grid.npz"))
        self.xc, self.rc, self.solid = g["xc"], g["rc"], g["solid"]
        self.dx = float(g["DX"])
        self.xmin = float(g["XMIN"]) if "XMIN" in g.files else 0.0
        self.st, self.tw = float(g["ST"]), float(g["TW"])
        self.u_ref = U_REF
        self.gam_e, self.r_e, self.gam_a = float(g["GAM_E"]), float(g["R_E"]), float(g["GAM_A"])
        self.nx, self.nr = len(self.xc), len(self.rc)
        L = np.loadtxt(os.path.join(d, "log.txt"))
        n = len([f for f in os.listdir(d) if f.startswith("s") and f.endswith(".f16")])
        L = L[:n]
        self.k, self.t = L[:, 0].astype(int), L[:, 1]
        self.thrust, self.Tch, self.pch, self.mach_exit = L[:, 2], L[:, 3], L[:, 4], L[:, 5]
        self.q_spike, self.pa, self.p0, self.q_chamber, self.Q_walls = L[:, 6], L[:, 7], L[:, 8], L[:, 9], L[:, 10]
        self.thrust_s = self._smooth(self.thrust, self.t, 0.12)
        self.mach_s = self._smooth(self.mach_exit, self.t, 0.12)
        self.q_s = self._smooth(np.maximum(self.q_spike, self.q_chamber), self.t, 0.12)
        # real size from LEAP 71's photo (body ~0.29 m across); thrust is computed, not scaled
        self.L0 = G.L0_M
        self.t_unit = self.L0 / U_REF
        self.kN = self.L0 ** 2 * P_ATM / 1e3
        self.MWm2 = P_ATM * U_REF / 1e6
        self.cache = {}

    @staticmethod
    def _smooth(y, t, w):
        out = np.empty_like(y)
        for i in range(len(y)):
            m = np.abs(t - t[i]) <= w / 2
            out[i] = y[m].mean()
        return out

    def idx(self, tn):
        return int(np.clip(np.searchsorted(self.t, tn), 0, len(self.t) - 1))

    def stat(self, tn, arr):
        return float(np.interp(tn, self.t, arr))

    def fields(self, k):
        if k in self.cache: return self.cache[k]
        a = np.fromfile(os.path.join(self.d, f"s{k:05d}.f16"), np.float16).reshape(self.NV, self.nx, self.nr)
        a = a.astype(np.float32)
        if len(self.cache) > 6: self.cache.pop(next(iter(self.cache)))
        self.cache[k] = a
        return a

    def r_mix(self, y):
        return y * self.r_e + (1 - y)


def intensity(rho, p, y, pa, dx, r_mix):
    """Grid -> display intensity (0..1). Brightness follows the model: hot exhaust (and
    afterburning mixture) glows by temperature and density; faint schlieren in the air."""
    T = p / (rho * r_mix)
    fT = np.clip((T - 1.8) / (8.5 - 1.8), 0, 1)      # the expanded jet core (~2,000 K) glows too
    dens = np.clip((np.maximum(rho, 1e-5) / 0.25) ** 0.3, 0.35, 1.25)
    lr = np.log(np.maximum(rho, 1e-5))
    gx = np.zeros_like(lr); gr = np.zeros_like(lr)
    gx[1:-1] = (lr[2:] - lr[:-2]) / (2 * dx)
    gr[:, 1:-1] = (lr[:, 2:] - lr[:, :-2]) / (2 * dx)
    sch = np.clip(np.hypot(gx, gr) / 14.0, 0, 1)
    w = np.clip(y, 0, 1) ** 1.4                       # exhaust diluted in air glows less
    I = w * (0.12 + 0.70 * fT ** 0.9) * dens
    I *= 1 - 0.30 * sch * w                                  # wave structure inside the plume
    air = (1 - w) * sch * 0.16                               # faint waves in the air
    return np.clip(I + air, 0, 1).astype(np.float32)


def sample(field, xc0, dx, xs, rs):
    """bilinear sample of field[i(x), j(r)] at pixel coords (xs: W, rs: H)."""
    fi = (xs - xc0) / dx
    fj = (np.abs(rs) - dx / 2) / dx
    fj = np.maximum(fj, 0)
    i0 = np.clip(np.floor(fi).astype(int), 0, field.shape[0] - 2)
    j0 = np.clip(np.floor(fj).astype(int), 0, field.shape[1] - 2)
    wi = np.clip(fi - i0, 0, 1); wj = np.clip(fj - j0, 0, 1)
    I0, J0 = np.meshgrid(i0, j0, indexing="xy")
    WI, WJ = np.meshgrid(wi, wj, indexing="xy")
    f = field
    out = (f[I0, J0] * (1 - WI) * (1 - WJ) + f[I0 + 1, J0] * WI * (1 - WJ)
           + f[I0, J0 + 1] * (1 - WI) * WJ + f[I0 + 1, J0 + 1] * WI * WJ)
    outside = (xs < xc0 - dx) | (xs > xc0 + field.shape[0] * dx)
    out[:, outside] = 0
    return out


_outline_cache = {}


def engine_layer(view, size):
    """RGBA layer with the engine drawn as a dark body with light outline."""
    key = (tuple(round(v, 4) for v in view), size)
    if key in _outline_cache: return _outline_cache[key]
    if len(_outline_cache) > 8: _outline_cache.clear()
    w, h = size
    ss = 3
    x0, x1, rmax, rc = view
    sx = w * ss / (x1 - x0)
    def px(pts, sign):
        return [((x - x0) * sx, (h * ss) / 2 - (sign * r - rc) * sx) for x, r in pts]
    poly = G.OUTLINE
    full = np.concatenate([poly, (poly * [1, -1])[::-1]])
    lay = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    pts = px(full, 1)
    d.polygon(pts, fill=CL.STEEL + (255,))
    d.line(pts + [pts[0]], fill=(150, 152, 168, 255), width=int(2.2 * ss), joint="curve")
    lay = lay.resize((w, h), Image.LANCZOS)
    _outline_cache[key] = lay
    return lay


def palette_from_frame(img):
    """LUT (1024x3) that gives sim intensity the colours of the real flame in `img`:
    the flame's pixels sorted by brightness, darkest -> I~0.12, brightest -> I=1."""
    a = np.asarray(img.resize((300, 178))).astype(np.float32)
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    m = lum > 62
    if m.sum() < 600:
        return None
    px = a[m][np.argsort(lum[m])]
    nb = 40
    edges = np.linspace(0, len(px), nb + 1).astype(int)
    cols = np.array([px[edges[i]:edges[i + 1]].mean(0) for i in range(nb)])
    k = np.ones(5) / 5
    cols = np.stack([np.convolve(np.pad(cols[:, c], 2, mode="edge"), k, mode="valid") for c in range(3)], 1)
    # bin averaging washes colours out; restore the footage's saturation
    lum_c = (cols @ np.array([0.299, 0.587, 0.114]))[:, None]
    cols = np.clip(lum_c + (cols - lum_c) * 1.65, 0, 255)
    xs = np.concatenate([[0.0, 0.05, 0.15], np.linspace(0.22, 1.0, nb)])
    ys = np.concatenate([[PANEL, PANEL, (58, 54, 88)], cols])      # faint air waves stay neutral
    grid = np.linspace(0, 1, 1024)
    return np.stack([np.interp(grid, xs, ys[:, c]) for c in range(3)], 1).astype(np.float32)


def render_sim(run, tn, view, size, lut=None, thermal=None):
    w, h = size
    x0, x1, rmax, rc = view
    k = run.idx(tn)
    rho, p, y = run.fields(k)[:3]
    pa = run.pa[k]
    # crop grid to the view for speed
    i0 = max(int((x0 - 0.1 - run.xmin) / run.dx), 0); i1 = min(int((x1 + 0.1 - run.xmin) / run.dx) + 2, run.nx)
    j1 = min(int((abs(rc) + rmax + 0.1) / run.dx) + 2, run.nr)
    sl = (slice(i0, i1), slice(0, j1))
    yy = y[sl].astype(np.float64)
    I = intensity(rho[sl].astype(np.float64), p[sl].astype(np.float64), yy, pa, run.dx, run.r_mix(yy))
    xs = x0 + (np.arange(w) + 0.5) * (x1 - x0) / w
    rs = rc + ((h / 2) - (np.arange(h) + 0.5)) * (x1 - x0) / w
    img = sample(I, run.xc[i0], run.dx, xs, rs)
    rgb = (_lut if lut is None else lut)[np.clip((img * 1023).astype(int), 0, 1023)]
    im = Image.fromarray(rgb.astype(np.uint8), "RGB")
    glow = im.filter(ImageFilter.GaussianBlur(radius=max(3, w / 160)))
    im = Image.blend(im, Image.fromarray(np.maximum(np.asarray(im), np.asarray(glow)), "RGB"), 0.55)
    lay = engine_layer(view, size)
    im.paste(lay, (0, 0), lay)
    alpha = np.asarray(lay)[..., 3].astype(np.float32) / 255.0
    arr = np.asarray(im).astype(np.float32)
    if thermal is not None:
        # metal temperature from the conduction solution (copper and steel tinted apart)
        Tf, cu = thermal
        Ts = sample(np.nan_to_num(Tf[sl], nan=300.0).astype(np.float32), run.xc[i0], run.dx, xs, rs)
        Cs = sample(cu[sl].astype(np.float32), run.xc[i0], run.dx, xs, rs)
        mrgb = CL.metal_rgb(Ts)
        mrgb = mrgb * (1 - 0.30 * Cs[..., None]) + np.array(CL.CU, np.float32) * 0.30 * Cs[..., None]
        arr = arr * (1 - alpha[..., None]) + mrgb * alpha[..., None]
    # printed-metal grain, in world coordinates
    sc_ = w / (x1 - x0)
    if sc_ > 60:
        ix = np.floor(xs * 90).astype(np.int64)[None, :]
        ir = np.floor(np.abs(rs) * 90).astype(np.int64)[:, None]
        hsh = (ix * 73856093) ^ (ir * 19349663)
        hsh = (hsh ^ (hsh >> 13)) * 1274126177
        nz = ((hsh >> 7) & 255).astype(np.float32) / 255.0 - 0.5
        arr += (nz * 14.0 * alpha)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


# ------------------------------------------------------------------ footage
# LEAP 71 hot fire at Airborne Engineering (60 fps, landscape after rotation): rotate so the
# plume axis is horizontal, crop away the stand clutter and the app overlay in the corner
# measured: the bright core's axis is 26 deg below horizontal in the source; after this
# rotation its edges are symmetric (-2.0 / +2.5 deg). The crop puts the axis at the vertical
# centre and the engine exit at 25 % of the width (as in the reference), 35.4 px per L0.
CROP = "rotate=-26*PI/180:fillcolor=black,crop=1230:728:442:425"
FOOT_SLOW = 2.0     # played 2x slower (the source is 60 fps, so every frame is real)


class Footage:
    def __init__(self, path, start, dur, size, crop=CROP, slow=FOOT_SLOW):
        self.size = size
        w, h = size
        vf = (f"setpts={slow}*PTS,fps={FPS},{crop},"
              f"scale={w}:{h}:flags=lanczos,eq=contrast=1.03:saturation=1.03")
        cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur + 1), "-i", path,
               "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        self.n = 0
        self.last = Image.new("RGB", size, (0, 0, 0))

    def frame_at(self, i):
        w, h = self.size
        while self.n <= i:
            buf = self.p.stdout.read(w * h * 3)
            if len(buf) < w * h * 3: break
            self.last = Image.frombytes("RGB", (w, h), buf)
            self.n += 1
        return self.last


# ------------------------------------------------------------------ timeline
# Same rhythm as the reference: one continuous take, no restart of the sim.
T_A_END = 8.6       # part A: close-up, slow pull-back, three captions
T_TR_END = 9.25     # header/title fade, panel moves up, footage fades in
T_FLASH = 10.25     # ignition fireball in the footage; the sim panel flashes (as in the reference)
T_B_END = 22.3      # end of part B
T_RW_END = 23.25    # rewind + push-in back to the first frame
TOTAL = 23.8
FOOT_IGN = 0.35     # footage time of the ignition fireball
V0 = T_FLASH - FOOT_IGN * FOOT_SLOW     # video time of footage t = 0 (cold flow before ignition)


def foot_t(t):
    """footage time shown at video time t (frozen on the first frame before V0)"""
    return max(0.0, (t - V0) / FOOT_SLOW)


def fv(f):
    """video time at which footage time f is shown"""
    return V0 + f * FOOT_SLOW


T_JET = fv(0.517)   # first green streaks leave the ring in the footage == the sim jet leaves the slot

PANEL_A = (492, 843)
PANEL_B = (322, 560)
# camera keyframes: (centre x, centre r, width) in L0
CAM_CHAMBER = (0.80, 2.85, 3.5)      # ring chamber, injector face, outer shell, passage start
CAM_SPIKE = (4.70, 1.05, 6.6)        # passage, lip, central body to its tip, LOX along the axis
CAM_A1 = (5.40, 0.0, 15.4)           # whole engine
CAM_B = (5.90, 0.0, 16.0)
VIEW_B = (-2.1, 13.9)

# Flame course in the footage (source time): cold propellant flow 0-0.33 s; ignition
# fireball 0.35-0.50 s; first thin green streaks from the ring, converging along the spike,
# at 0.517 s; a growing, flickering green jet with an afterburning cloud beyond it to
# 0.78 s; one bright full column from 0.80 s.
SIM_MAP = [(0.0, 0.22), (3.0, 0.42), (7.0, 0.56), (T_A_END, 0.60), (T_TR_END, 0.64),
           # fireball: the ring chamber fills and its hot gas reaches the lip
           (T_FLASH, 0.70), (fv(0.45), 2.00),
           # weak first stage: the annular jet leaves the lip and wraps the central body
           (T_JET, 3.35), (fv(0.55), 3.75), (fv(0.65), 4.30), (fv(0.78), 5.00),
           # second stage when the real flame becomes one full column; then, as in the
           # scheme (0.73-1.23 s), the annular flow converges into the axial jet: the air left
           # behind the tip from the start is entrained and the jet closes on the axis
           (fv(0.80), 5.40), (fv(1.00), 8.80), (fv(1.23), 13.00), (fv(1.40), 14.20),
           # then the established jet plays at ~0.7 model units per second
           (T_B_END, 21.40),
           (T_RW_END, 0.9), (TOTAL, 0.22)]

TYPE_RATE = 46.0    # characters per second
CAPS_A = [(0.25, "Methane and oxygen burn in a ring-shaped chamber."),
          (3.1, "Methane runs from the lip back through the outer shell."),
          (7.0, "Oxygen runs down the central body to its tip, then back.")]
# phases of the test flame, as in the explanation (footage time)
CAPS_B = [(fv(0.23), "Gas release first: the flame has not formed yet."),
          (fv(0.73), "The annular flow wraps the central body: an axial jet forms."),
          (fv(1.73), "Developed flame. Green glow: copper burning, per LEAP 71."),
          (16.5, ("Channels inside the walls", 17.0, ", hot gas outside them.")),
          (20.0, None)]                       # closing line, filled in with the sim length
CAP_FADE_B = (19.45, 19.75)

SIZE_FOOT = (1080, 639)
CREDITS = ["FOOTAGE · LEAP 71, 20 kN METHALOX AEROSPIKE AT AIRBORNE ENGINEERING · 2× SLOWER",
           "RING CHAMBER, ANNULAR FLOW AROUND THE CENTRAL BODY · CH4 COOLS THE OUTER SHELL, LOX THE CENTRAL BODY",
           "MODEL · 2D AXISYMMETRIC FLOW · COOLANT: 1D BALANCE · METAL: STEADY CONDUCTION · ROUTING NOTIONAL",
           "START-UP COMPRESSED, PLAYBACK MATCHED TO THE REAL FLAME · COLOURS FROM THE FOOTAGE",
           "SIZE FROM LEAP 71'S PHOTO · MODEL Pc ~46 bar (LEAP 71: 50) · THRUST, HEAT FLUX COMPUTED"]
FB_B = (7.5, 2.02)     # annotation anchors (x, r), from the solution (time-averaged t = 12-20)
WV_B = (5.0, float(G.r_spike(5.0)))
PC_B = None            # set at start-up from the solution (where the plume closes)


def smooth_step(t, a, b):
    return ease((t - a) / (b - a)) if b > a else float(t >= a)


def cam_at(t):
    """Camera (centre x, centre r, width) at video time t."""
    def mix(c0, c1, u):
        u = ease(u)
        w = math.exp(math.log(c0[2]) + (math.log(c1[2]) - math.log(c0[2])) * u)
        return (c0[0] + (c1[0] - c0[0]) * u, c0[1] + (c1[1] - c0[1]) * u, w)
    if t < 4.6:
        return mix(CAM_CHAMBER, (CAM_CHAMBER[0] + 0.10, CAM_CHAMBER[1] - 0.05, CAM_CHAMBER[2] * 0.92), t / 4.6)
    c_end = (CAM_CHAMBER[0] + 0.10, CAM_CHAMBER[1] - 0.05, CAM_CHAMBER[2] * 0.92)
    if t < 7.0: return mix(c_end, CAM_SPIKE, (t - 4.6) / 2.4)
    if t < T_A_END: return mix(CAM_SPIKE, CAM_A1, (t - 7.0) / (T_A_END - 7.0))
    if t < T_TR_END: return mix(CAM_A1, CAM_B, (t - T_A_END) / (T_TR_END - T_A_END))
    if t < T_B_END: return CAM_B
    if t < T_RW_END: return mix(CAM_B, CAM_CHAMBER, (t - T_B_END) / (T_RW_END - T_B_END))
    return CAM_CHAMBER


def panel_at(t):
    if t < T_A_END or t >= T_RW_END - 0.15: s = 0.0
    elif t < T_TR_END: s = smooth_step(t, T_A_END, T_TR_END)
    elif t < T_B_END: s = 1.0
    else: s = 1 - smooth_step(t, T_B_END, T_RW_END - 0.15)
    y = PANEL_A[0] + (PANEL_B[0] - PANEL_A[0]) * s
    h = PANEL_A[1] + (PANEL_B[1] - PANEL_A[1]) * s
    return int(round(y)), int(round(h)), s


def sim_time(t):
    return lerp_map(t, SIM_MAP)


def slower(t, run):
    dt_v = 1 / FPS
    phys = abs(sim_time(t + dt_v) - sim_time(t)) * run.t_unit
    return dt_v / phys if phys > 0 else 0


def typed(caps, t):
    """Typewriter caption: the newest caption that has started, typed out."""
    cur = None
    for c in caps:
        if t >= c[0]: cur = c
    if cur is None or cur[1] is None:
        return None
    t0, text = cur
    if isinstance(text, tuple):
        a, t1, b = text
        n_a = min(len(a), int((t - t0) * TYPE_RATE))
        if t < t1: return a[:n_a]
        return a + b[:max(0, int((t - t1) * TYPE_RATE))]
    return text[:max(0, int((t - t0) * TYPE_RATE))]


def header(d, right, prog, a_right=1.0):
    if right and a_right > 0:
        spaced(d, (980, 244), right, F_LABEL, alpha_blend(LAV, a_right), 2.2, "r")
    y = 290
    d.line([(100, y), (980, y)], fill=(70, 67, 88), width=1)
    for i in range(0, 89):
        x = 100 + i * 10
        hh = 7 if i % 5 == 0 else 4
        d.line([(x, y), (x, y - hh)], fill=(70, 67, 88), width=1)
    xm = 100 + prog * 880
    d.line([(xm, y + 6), (xm, y - 18)], fill=INK, width=2)


def sparkline(d, run, t_now, t_max, box, a):
    x0, y0, x1, y1 = box
    ts = run.t[run.t <= t_max]
    d.line([(x0, y1), (x1, y1)], fill=alpha_blend((52, 50, 68), a), width=1)
    for arr, col, lo, hi in [(run.Tch, (210, 206, 225), 1, 12.5), (run.pch, LAV, 1, 52)]:
        pts = []
        for tt in ts:
            if tt > t_now: break
            v = np.interp(tt, run.t, arr)
            pts.append((x0 + (x1 - x0) * tt / t_max, y1 - (y1 - y0) * (v - lo) / (hi - lo)))
        if len(pts) > 1:
            c = alpha_blend(col, a)
            d.line(pts, fill=c, width=2)
            d.ellipse([pts[-1][0] - 4, pts[-1][1] - 4, pts[-1][0] + 4, pts[-1][1] + 4], fill=c)


def stat_block(d, x, y, label, val, unit, a):
    spaced(d, (x, y), label, F_SMALL, alpha_blend(DIM, a), 1.5)
    d.text((x, y + 20), val, font=F_VAL, fill=alpha_blend(INK, a))
    wv = d.textlength(val, font=F_VAL)
    d.text((x + wv + 6, y + 20 + F_VAL.size * 0.62), unit, font=F_UNIT, fill=alpha_blend(DIM, a))


def inline_stat(d, x, y, label, val, unit, a):
    w = spaced(d, (x, y + 13), label, F_SMALL, alpha_blend(DIM, a), 1.5)
    x += w + 10
    d.text((x, y), val, font=F_VALB, fill=alpha_blend(INK, a))
    x += d.textlength(val, font=F_VALB) + 5
    d.text((x, y + 13), unit, font=F_UNIT, fill=alpha_blend(DIM, a))
    return x + d.textlength(unit, font=F_UNIT)


def to_px(view, size, origin, x, r):
    x0, x1, rmax, rc = view
    w, h = size
    s = w / (x1 - x0)
    return origin[0] + (x - x0) * s, origin[1] + h / 2 - (r - rc) * s


def annotate(d, view, size, origin, x, r, label, a, side="up", length=60, color=(214, 208, 236)):
    """Marker + leader line + label. side: up/down/left/right."""
    if a <= 0: return
    px, py = to_px(view, size, origin, x, r)
    col = alpha_blend(color, a, PANEL)
    d.ellipse([px - 4, py - 4, px + 4, py + 4], outline=col, width=2)
    if side in ("up", "down"):
        sgn = -1 if side == "up" else 1
        d.line([(px, py + sgn * 5), (px, py + sgn * length)], fill=col, width=1)
        ty = py - length - 22 if side == "up" else py + length + 6
        spaced(d, (px, ty), label, F_ANN, col, 1.6, "m", stroke=3)
    else:
        sgn = -1 if side == "left" else 1
        d.line([(px + sgn * 5, py), (px + sgn * length, py)], fill=col, width=1)
        tx = px + sgn * (length + 8)
        spaced(d, (tx, py - 10), label, F_ANN, col, 1.6, "r" if side == "left" else "l", stroke=3)


_shade = None


def _shade_mask():
    global _shade
    if _shade is None:
        a = (np.linspace(1, 0, 130) ** 1.3 * 215).astype(np.uint8)
        _shade = Image.fromarray(np.repeat(a[:, None], W, 1), "L")
    return _shade


_pal = {"n": None, "lut": None}
LUT_A = None          # first-light colours, used before ignition and after the rewind


def flame_lut(t, n, frame):
    """Sim palette that follows the colours of the real flame shown below."""
    target = LUT_A
    if frame is not None and T_FLASH - 0.03 <= t < T_B_END:
        p = palette_from_frame(frame)
        if p is not None:
            target = p
    if t >= T_B_END:
        target = LUT_A
    prev = _pal["lut"] if _pal["n"] == n - 1 else None
    k = 0.35 if t < fv(1.0) else 0.18
    lut = target if prev is None else prev + (target - prev) * k
    _pal["n"], _pal["lut"] = n, lut
    return lut


def ann_win(t, a, b):
    return smooth_step(t, a, a + 0.3) * (1 - smooth_step(t, b - 0.3, b))


THERMAL = None


def cooling_state(run, tn):
    """1D coolant balance for this frame and the metal temperature field, blended between the
    chilled-down and full-pressure conduction solutions by the current heat load."""
    f = run.fields(run.idx(tn))
    S = CL.solve(run, f)
    th = THERMAL
    s_ = float(np.clip(S.Q / max(th["Q_hot"], 1.0), 0.0, 1.2))
    T = th["T_cold"] + s_ * (th["T_hot"] - th["T_cold"])
    hot_cu = th["copper"] & np.isfinite(T)
    S.metal_peak = float(np.nanmax(np.where(hot_cu, T, np.nan)))
    return S, (T, th["copper"])


def colour_bar(d, x, y, w, a):
    """Metal temperature scale."""
    for i in range(w):
        T = 80 + (950 - 80) * i / (w - 1)
        c = CL.metal_rgb(np.array([T]))[0]
        d.line([(x + i, y), (x + i, y + 7)], fill=alpha_blend(tuple(int(v) for v in c), a))
    for T in (100, 300, 500, 700, 900):
        xx = x + (T - 80) / (950 - 80) * (w - 1)
        d.line([(xx, y + 8), (xx, y + 12)], fill=alpha_blend((200, 196, 214), a))
        spaced(d, (xx, y + 13), f"{T}", F_TINY, alpha_blend((200, 196, 214), a), 1.0, "m", stroke=2)
    spaced(d, (x, y - 19), "METAL TEMPERATURE · K", F_TINY, alpha_blend((214, 208, 236), a), 1.4, stroke=2)


def make_frame(run, foot, n):
    t = n / FPS
    tn = sim_time(t)
    py, ph, ps = panel_at(t)
    cx_, cr_, cw_ = cam_at(t)
    x0, x1 = cx_ - cw_ / 2, cx_ + cw_ / 2
    view = (x0, x1, cw_ * ph / W / 2, cr_)
    size = (W, ph)
    im = Image.new("RGB", (W, H), BG)

    # alphas
    aA = 1 - smooth_step(t, T_A_END, T_A_END + 0.3) if t < T_B_END else smooth_step(t, T_RW_END - 0.25, T_RW_END)
    aB = smooth_step(t, T_TR_END - 0.25, T_TR_END + 0.05) * (1 - smooth_step(t, T_B_END, T_B_END + 0.3))
    aF = smooth_step(t, 9.0, 9.4) * (1 - smooth_step(t, T_B_END, T_B_END + 0.45))

    # footage (bottom), fades in from black
    fy = 1012
    fr_for_palette = None
    fidx = max(0, int(round((t - V0) * FPS)))
    if t >= T_FLASH - 0.03:
        fr_for_palette = foot.frame_at(fidx)
    if aF > 0:
        fr = foot.frame_at(fidx)
        fr = Image.blend(Image.new("RGB", SIZE_FOOT, BG), fr, aF)
        im.paste(fr, (0, fy))
        im.paste(Image.new("RGB", (W, 130), (6, 5, 14)), (0, fy), _shade_mask().point(lambda v: int(v * aF)))

    CS, thermal = cooling_state(run, tn)
    sim = render_sim(run, tn, view, size, flame_lut(t, n, fr_for_palette), thermal)
    CL.draw(ImageDraw.Draw(sim), CS, view, size, (0, 0), t, 1.0, to_px)
    # flash with the real ignition fireball
    fl = 0.0
    if T_FLASH - 0.08 <= t < T_FLASH + 0.6:
        fl = 0.62 * (smooth_step(t, T_FLASH - 0.08, T_FLASH) if t < T_FLASH else math.exp(-(t - T_FLASH) / 0.16))
    if fl > 0:
        sim = Image.blend(sim, Image.new("RGB", size, (236, 232, 244)), fl)
    im.paste(sim, (0, py))
    d = ImageDraw.Draw(im)

    # coolant legend inside the sim panel (part B), with the computed temperatures
    if ps >= 0.5:
        # in the empty band above the panel, so it never covers the engine
        lg_y, lx = 104, 100
        rows = (("OXYGEN · CENTRAL BODY", CL.COOL["lox"][0], f"OUT {CS.out['lox']:.0f} K"),
                ("METHANE · OUTER SHELL", CL.COOL["ch4"][0], f"OUT {CS.out['ch4']:.0f} K"),
                ("HOT GAS · ANNULAR FLOW", CL.HOTGAS, f"{run.stat(tn, run.Tch) * T_AMB:,.0f} K"),
                ("CuCrZr WALL PEAK", CL.copper_glow(CS.metal_peak), f"{CS.metal_peak:.0f} K"))
        aL_ = aB
        for i, (name, col, val) in enumerate(rows):
            yy = lg_y + i * 26
            d.rounded_rectangle([lx, yy + 5, lx + 26, yy + 12], radius=3, fill=alpha_blend(col, aL_))
            wn = spaced(d, (lx + 36, yy), name, F_ANN, alpha_blend((214, 208, 236), aL_), 1.5)
            spaced(d, (lx + 36 + wn + 12, yy), val, F_ANN, alpha_blend((255, 255, 255), aL_), 1.5)
        colour_bar(d, 680, lg_y + 22, 300, aL_)
    else:
        colour_bar(d, 660, py + 40, 300, aA)

    right = "SIMULATION" if ps < 0.5 else "SIMULATION VS REAL"
    header(d, right, t / TOTAL, 1.0 if abs(ps - 0.5) > 0.2 else abs(ps - 0.5) / 0.2)

    # ---------------- part A overlays
    if aA > 0:
        d.text((100, 300), "How an aerospike starts", font=F_TITLE, fill=alpha_blend(INK, aA))
        d.text((100, 392), "LEAP 71's 20 kN Noyron aerospike: simulated, then the real test",
               font=font("serifi", 28), fill=alpha_blend((170, 166, 186), aA))
        ms = tn * run.t_unit * 1e3
        y = py + ph + 25
        spaced(d, (100, y), f"T+ {ms:.3f} ms", F_LABEL, alpha_blend((205, 201, 218), aA), 1.6)
        spaced(d, (980, y), f"{fmt(slower(t, run))}× SLOWER", F_LABEL, alpha_blend(LAV, aA), 1.6, "r")
        if t < T_B_END:
            cap = typed(CAPS_A, t)
            if cap: d.text((100, y + 38), cap, font=F_CAP, fill=alpha_blend(INK, aA))
        y += 110
        thr = max(0.0, run.stat(tn, run.thrust_s)) * run.kN
        stat_block(d, 100, y, "THRUST", f"{thr:.1f}", "kN", aA)
        stat_block(d, 270, y, "Pc", f"{run.stat(tn, run.pch) * 1.01325:.1f}", "bar", aA)
        stat_block(d, 450, y, "CH4 OUT", f"{CS.out['ch4']:.0f}", "K", aA)
        stat_block(d, 625, y, "LOX OUT", f"{CS.out['lox']:.0f}", "K", aA)
        stat_block(d, 800, y, "Cu WALL", f"{CS.metal_peak:.0f}", "K", aA)
        for xx, col in ((450, CL.COOL["ch4"][0]), (625, CL.COOL["lox"][0]), (800, CL.copper_glow(CS.metal_peak))):
            d.rounded_rectangle([xx, y - 12, xx + 26, y - 6], radius=3, fill=alpha_blend(col, aA))
        sparkline(d, run, tn, SIM_MAP[4][1], (100, y + 105, 930, y + 140), aA)
        spaced(d, (100, y + 154), "CHAMBER TEMP", F_TINY, alpha_blend((150, 146, 166), aA), 1.4)
        spaced(d, (290, y + 154), "CHAMBER PRESSURE", F_TINY, alpha_blend((140, 126, 200), aA), 1.4)
        if t < T_A_END + 0.3:
            org = (0, py)
            net = CL.network()
            annotate(d, view, size, org, 0.6, G.CH_R1, "RING CHAMBER",
                     aA * ann_win(t, 0.3, 3.0), "up", 60)
            annotate(d, view, size, org, G.CH_X0 + 0.04, G.CH_R0 + 0.12, "INJECTOR · CH4 + O2",
                     aA * ann_win(t, 0.3, 3.0), "down", 70)
            _, _, cl = G.passage_walls(60)
            pm = cl[30]
            annotate(d, view, size, org, pm[0], pm[1], "HOT GAS · ANNULAR PASSAGE",
                     aA * ann_win(t, 0.3, 3.0), "right", 80, color=CL.HOTGAS)
            aE, bE = net.band["ch4"]
            mE = 0.5 * (aE[len(aE) * 2 // 3] + bE[len(bE) * 2 // 3])
            annotate(d, view, size, org, mE[0], mE[1], "CH4 CHANNELS · OUTER SHELL",
                     aA * ann_win(t, 3.1, 5.0), "up", 70, color=CL.COOL["ch4"][1])
            annotate(d, view, size, org, net.m_ch4_in[0], net.m_ch4_in[1], "CH4 IN AT THE LIP",
                     aA * ann_win(t, 3.6, 6.4), "right", 70, color=CL.COOL["ch4"][1])
            aL, bL = net.band["lox"]
            mL = 0.5 * (aL[len(aL) // 5] + bL[len(bL) // 5])
            annotate(d, view, size, org, mL[0], mL[1], "O2 CHANNELS · CENTRAL BODY",
                     aA * ann_win(t, 5.4, 8.4), "up", 90, color=CL.COOL["lox"][1])
            annotate(d, view, size, org, 2.6, 0.0, "O2 IN ALONG THE AXIS",
                     aA * ann_win(t, 6.6, 8.6), "down", 70, color=CL.COOL["lox"][1])
            annotate(d, view, size, org, G.X_SPIKE_END - 0.1, 0.0, "O2 TURNS AT THE TIP",
                     aA * ann_win(t, 6.9, 8.6), "up", 110, color=CL.COOL["lox"][1])

    # ---------------- part B overlays
    if aB > 0:
        py, ph = PANEL_B          # part-B text sits at its final place while it fades in
        org = (0, py)
        spaced(d, (100, py + 24), "SIMULATION", F_LABEL, alpha_blend((205, 201, 218), aB), 2.0, stroke=4)
        ms = tn * run.t_unit * 1e3
        spaced(d, (980, py + 24), f"T+ {ms:.2f} ms · {fmt(slower(t, run))}× SLOWER", F_LABEL,
               alpha_blend(LAV, aB), 1.6, "r", stroke=4)
        annotate(d, view, size, org, FB_B[0], FB_B[1], "FREE BOUNDARY · HELD BY AIR PRESSURE",
                 aB * smooth_step(t, 14.0, 14.3), "up", 50)
        annotate(d, view, size, org, WV_B[0], -WV_B[1], "FLOW HUGS THE CENTRAL BODY",
                 aB * smooth_step(t, 15.0, 15.3), "down", 110)
        annotate(d, view, size, org, PC_B[0], PC_B[1], "AXIAL JET",
                 aB * smooth_step(t, fv(0.73), fv(0.73) + 0.3), "up", 70)
        cap = typed(CAPS_B, t)
        ca = aB * (1 - smooth_step(t, *CAP_FADE_B)) if t < CAPS_B[-1][0] else aB
        if cap and ca > 0:
            d.text((100, py + ph + 14), cap, font=F_CAPB, fill=alpha_blend(INK, ca))
        y = py + ph + 68
        thr = max(0.0, run.stat(tn, run.thrust_s)) * run.kN
        x = inline_stat(d, 100, y, "THRUST", f"{thr:.1f}", "kN", aB)
        x = inline_stat(d, x + 26, y, "Pc", f"{run.stat(tn, run.pch) * 1.01325:.1f}", "bar", aB)
        x = inline_stat(d, x + 26, y, "MACH", f"{run.stat(tn, run.mach_s):.2f}", "", aB)
        x = inline_stat(d, x + 26, y, "WALL HEAT", f"{run.stat(tn, run.q_s) * run.MWm2:.0f}", "MW/m²", aB)
    if aF > 0:
        spaced(d, (100, fy + 22), "REAL · LEAP 71 20 kN METHALOX AEROSPIKE", F_LABEL, alpha_blend((236, 232, 244), aF), 2.0, stroke=3)
        spaced(d, (980, fy + 22), "2× SLOWER", F_LABEL, alpha_blend((236, 232, 244), aF), 2.0, "r", stroke=3)
        an = aF * smooth_step(t, fv(1.6), fv(1.6) + 0.4)
        if an > 0:
            spaced(d, (100, fy + 54), "GREEN GLOW: COPPER BURNING (LEAP 71) · NOT NOMINAL COOLING", F_SMALL,
                   alpha_blend((150, 240, 190), an), 1.5, stroke=3)
        cy = fy + SIZE_FOOT[1] + 18
        for i, line in enumerate(CREDITS):
            spaced(d, (980, cy + i * 21), line, F_TINY, alpha_blend((96, 93, 114), aF), 1.3, "r")
    return im


def find_closure(run):
    """Axis point behind the spike tip where the plume closes (steady sea level)."""
    k = run.idx(12.0)
    rho, p, y = run.fields(k)[:3]
    i0 = int((G.X_SPIKE_END + 0.2 - run.xmin) / run.dx)
    j = 3
    yy = y[i0:, j]
    hit = np.where(yy > 0.5)[0]
    x = G.X_SPIKE_END + 1.2 if len(hit) == 0 else run.xc[i0 + hit[0]]
    return (float(min(x, VIEW_B[1] - 1.5)), 0.0)


def main():
    global PC_B
    run_dir, footage, out = sys.argv[1:4]
    run = Run(run_dir)
    PC_B = find_closure(run)
    global THERMAL
    print("conduction (cached after the first run) ...", flush=True)
    THERMAL = CL.thermal_fields(run, verbose=True)
    print(f"metal: full-pressure range {np.nanmin(THERMAL['T_hot']):.0f}-{np.nanmax(THERMAL['T_hot']):.0f} K, "
          f"heat load {THERMAL['Q_hot'] / 1e3:.0f} kW", flush=True)
    total_ms = SIM_MAP[-3][1] * run.t_unit * 1e3
    CAPS_B[-1] = (20.0, f"The whole simulation is {total_ms:.1f} ms, quicker than a blink.")
    print(f"L0 = {run.L0:.4f} m, time unit = {run.t_unit * 1e3:.4f} ms, shown sim {total_ms:.2f} ms, "
          f"plume closes at x = {PC_B[0]:.2f}", flush=True)
    global LUT_A
    LUT_A = palette_from_frame(Footage(footage, 0.40, 0.1, SIZE_FOOT).frame_at(0))   # ignition glow
    foot = Footage(footage, 0.0, 7.0, SIZE_FOOT)
    if "--preview" in sys.argv:
        ts = [float(v) for v in sys.argv[sys.argv.index("--preview") + 1].split(",")]
        for t in sorted(ts):
            make_frame(run, foot, int(round(t * FPS))).save(out.replace(".mp4", f"_{t:05.2f}.png"))
        return
    nframes = int(round(TOTAL * FPS))
    tmp = out + ".video.mp4"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
    for n in range(nframes):
        enc.stdin.write(make_frame(run, foot, n).tobytes())
        if n % 60 == 0: print("frame", n, "/", nframes, flush=True)
    enc.stdin.close(); enc.wait()
    make_audio(run, footage, out + ".audio.wav")
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", out + ".audio.wav",
                           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out])
    os.remove(tmp); os.remove(out + ".audio.wav")
    print("wrote", out)


def make_audio(run, footage, path):
    """The new footage has no sound, so the track is synthetic: a hiss of cold flow before
    ignition, a crack at the fireball, then a roar that follows the model's chamber
    pressure and thrust."""
    sr = 48000
    n = int(TOTAL * sr)
    rng = np.random.default_rng(7)
    tt = np.arange(n) / sr
    tn = np.interp(tt, [p[0] for p in SIM_MAP], [p[1] for p in SIM_MAP])

    def brown(seed, win):
        r = np.random.default_rng(seed)
        b = np.cumsum(r.standard_normal(n)); b -= np.convolve(b, np.ones(win) / win, mode="same")
        return b / (np.abs(b).max() + 1e-9)

    low = brown(7, 4801)
    mid = brown(8, 601)
    hiss = rng.standard_normal(n); hiss -= np.convolve(hiss, np.ones(9) / 9, mode="same"); hiss /= np.abs(hiss).max()
    pc = np.clip(np.interp(tn, run.t, run.pch) / 46.0, 0, 1)
    thr = np.clip(np.interp(tn, run.t, run.thrust_s) / 150.0, 0, 1)
    part_a = np.clip((T_A_END + 0.6 - tt) / 0.6, 0, 1)
    rewind = np.clip((tt - T_B_END) / 0.4, 0, 1)
    roar = 2.8 * (0.30 * low + 0.18 * mid) * (0.35 * pc * part_a + 0.9 * thr * (1 - part_a)) * (1 - 0.8 * rewind)
    cold = 0.14 * hiss * np.clip((tt - 9.0) / 0.4, 0, 1) * np.clip((T_FLASH - tt) / 0.1, 0, 1)
    crack = np.zeros(n)
    i0 = int(T_FLASH * sr)
    k = np.arange(int(0.6 * sr))
    crack[i0:i0 + len(k)] = 2.2 * mid[i0:i0 + len(k)] * np.exp(-k / (0.12 * sr))
    mono = np.clip(roar + cold + crack, -1, 1).astype(np.float32)
    mix = np.stack([mono, np.roll(mono, 37)], 1)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", "-", path],
                   input=mix.astype(np.float32).tobytes(), check=True)


if __name__ == "__main__":
    main()
