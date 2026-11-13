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
    d.line(pts + [pts[0]], fill=(232, 178, 140, 255), width=int(2.2 * ss), joint="curve")
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
    # cold propellant gas (before ignition and in the cold flow): a pale vapour, as in the footage
    Tg = p[sl].astype(np.float64) / (np.maximum(rho[sl].astype(np.float64), 1e-6) * run.r_mix(yy))
    Vf = (np.clip(yy, 0, 1) * np.clip((2.2 - Tg) / 1.4, 0, 1)).astype(np.float32)
    if Vf.max() > 0.01:
        vimg = np.clip(sample(Vf, run.xc[i0], run.dx, xs, rs), 0, 1)[..., None] * 0.42
        rgb = rgb * (1 - vimg) + np.array([170, 190, 222], np.float32) * vimg
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
T_A_END = 8.6       # part A: close-up of the cold engine, slow pull-back
T_TR_END = 9.25     # the panel shrinks, the footage fades in below
T_FLASH = 10.25     # ignition fireball in the footage == ignition in the sim; the panel flashes
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


TITLE = "Aerospike by LEAP 71"
FUEL = (("Methalox", INK), (" · ", DIM), ("liquid methane", None), (" + ", DIM), ("liquid oxygen", None))
PANEL_A = (322, 1330)       # part A: the panel fills the screen under the title
PANEL_B = (322, 560)        # part B: simulation on top, footage below (as in the reference)
FOOT_Y = 1012
# camera keyframes: (centre x, centre r, width) in L0
CAM_CHAMBER = (-3.25, 2.70, 4.6)     # ring chamber, injector face, outer shell, channels
CAM_SPIKE = (-0.60, 1.55, 5.4)       # passage, lip, spike, oxygen along the axis
CAM_A1 = (-4.10, 0.0, 13.6)          # the whole engine, crown to spike
VIEW_B = (-4.5, 13.5)                # lip at 25 % of the width, as the engine exit in the footage
CAM_B = (0.5 * (VIEW_B[0] + VIEW_B[1]), 0.0, VIEW_B[1] - VIEW_B[0])

# Flame course in the footage (source time): cold propellant flow 0-0.33 s; ignition fireball
# 0.35-0.50 s that fills the whole frame at once; thin green streaks across the frame from
# 0.517 s; one bright full column from 0.80 s. The sim: cold flow until T_IGN = 8.0, then
# the gas in the chamber ignites; its jet crosses the panel during the fireball (the start-up
# is compressed); a weak first stage; full pressure (T_STAGE2 = 20.4) with the full column.
SIM_MAP = [(0.0, 0.10), (T_A_END, 5.20), (T_TR_END, 5.60), (V0, 6.40), (T_FLASH - 0.04, 7.96),
           # ignition with the fireball; the jet crosses the panel while the fireball fills the frame
           # (jet front: lip at 8.3, x = 5 at 10.6, x = 9.6 at 15, panel edge x = 13.5 at 19.7)
           (T_FLASH, 8.02), (fv(0.38), 8.60), (fv(0.42), 10.50), (fv(0.46), 14.00), (fv(0.50), 19.70),
           # weak first stage while the real flame is thin green streaks
           (fv(0.78), 20.30),
           # full pressure when the real flame becomes one full column
           (fv(0.80), 20.50), (fv(0.90), 21.10), (fv(1.10), 21.90),
           # then the established jet
           (T_B_END, 27.30),
           (T_RW_END, 0.5), (TOTAL, 0.10)]

SIZE_FOOT = (1080, 639)


def smooth_step(t, a, b):
    return ease((t - a) / (b - a)) if b > a else float(t >= a)


def cam_at(t):
    """Camera (centre x, centre r, width) at video time t."""
    def mix(c0, c1, u):
        u = ease(u)
        w = math.exp(math.log(c0[2]) + (math.log(c1[2]) - math.log(c0[2])) * u)
        return (c0[0] + (c1[0] - c0[0]) * u, c0[1] + (c1[1] - c0[1]) * u, w)
    c_end = (CAM_CHAMBER[0] + 0.15, CAM_CHAMBER[1] - 0.05, CAM_CHAMBER[2] * 0.92)
    if t < 4.6: return mix(CAM_CHAMBER, c_end, t / 4.6)
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


def header(d, prog):
    """Progress ruler (no text)."""
    y = 290
    d.line([(100, y), (980, y)], fill=(70, 67, 88), width=1)
    for i in range(0, 89):
        x = 100 + i * 10
        hh = 7 if i % 5 == 0 else 4
        d.line([(x, y), (x, y - hh)], fill=(70, 67, 88), width=1)
    xm = 100 + prog * 880
    d.line([(xm, y + 6), (xm, y - 18)], fill=INK, width=2)


def title_block(d):
    """The only text in the video: the engine and its propellants (coloured as their channels)."""
    d.text((100, 118), TITLE, font=F_TITLE, fill=INK)
    x = 100
    cols = {"liquid methane": CL.COOL["ch4"][1], "liquid oxygen": CL.COOL["lox"][1]}
    for txt, col in FUEL:
        c = col if col is not None else cols[txt]
        d.text((x, 204), txt, font=F_SUB, fill=c)
        x += d.textlength(txt, font=F_SUB)


def to_px(view, size, origin, x, r):
    x0, x1, rmax, rc = view
    w, h = size
    s = w / (x1 - x0)
    return origin[0] + (x - x0) * s, origin[1] + h / 2 - (r - rc) * s


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


def make_frame(run, foot, n):
    t = n / FPS
    tn = sim_time(t)
    py, ph, ps = panel_at(t)
    cx_, cr_, cw_ = cam_at(t)
    x0, x1 = cx_ - cw_ / 2, cx_ + cw_ / 2
    view = (x0, x1, cw_ * ph / W / 2, cr_)
    size = (W, ph)
    im = Image.new("RGB", (W, H), BG)

    aF = smooth_step(t, 9.0, 9.4) * (1 - smooth_step(t, T_B_END, T_B_END + 0.45))
    # footage (bottom), fades in from black
    fr_for_palette = None
    fidx = max(0, int(round((t - V0) * FPS)))
    if t >= T_FLASH - 0.03:
        fr_for_palette = foot.frame_at(fidx)
    if aF > 0:
        fr = foot.frame_at(fidx)
        fr = Image.blend(Image.new("RGB", SIZE_FOOT, BG), fr, aF)
        im.paste(fr, (0, FOOT_Y))
        im.paste(Image.new("RGB", (W, 130), (6, 5, 14)), (0, FOOT_Y), _shade_mask().point(lambda v: int(v * aF)))

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
    header(d, t / TOTAL)
    title_block(d)
    return im


def main():
    run_dir, footage, out = sys.argv[1:4]
    run = Run(run_dir)
    global THERMAL
    print("conduction (cached after the first run) ...", flush=True)
    THERMAL = CL.thermal_fields(run, avg_from=22.0, avg_to=27.4, verbose=True)
    print(f"metal: full-pressure range {np.nanmin(THERMAL['T_hot']):.0f}-{np.nanmax(THERMAL['T_hot']):.0f} K, "
          f"heat load {THERMAL['Q_hot'] / 1e3:.0f} kW", flush=True)
    print(f"L0 = {run.L0:.4f} m, time unit = {run.t_unit * 1e3:.4f} ms", flush=True)
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
    cold = (0.06 + 0.08 * np.clip((tt - 9.0) / 0.4, 0, 1)) * hiss * np.clip(tt / 0.5, 0, 1) \
        * np.clip((T_FLASH - tt) / 0.1, 0, 1)
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
