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

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts")
W, H, FPS = 1080, 1920, 30

# ------------------------------------------------------------------ physics scale
GAM = 1.2
P_ATM = 101325.0
T_AMB = 300.0
U_REF = math.sqrt(287.0 * T_AMB)        # velocity unit (p = rho T, air gas constant)
RATED_THRUST_KN = 200.0                  # LEAP 71: XRA-2E5, 200 kN

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
    files = {"mono": "ibm-plex-mono-latin-400-normal.woff", "monom": "ibm-plex-mono-latin-500-normal.woff",
             "serifb": "source-serif-4-latin-700-normal.woff", "serifi": "source-serif-4-latin-400-italic.woff",
             "sans": "inter-latin-500-normal.woff", "sansr": "inter-latin-400-normal.woff"}
    return ImageFont.truetype(os.path.join(FONT, files[name]), size)


F_LABEL = font("mono", 21)
F_SMALL = font("mono", 15)
F_TINY = font("mono", 14)
F_TITLE = font("serifb", 56)
F_SUB = font("serifi", 31)
F_CAP = font("serifi", 33)
F_CAPB = font("serifi", 31)
F_VAL = font("sans", 46)
F_VALB = font("sans", 33)
F_UNIT = font("sansr", 17)
F_ANN = font("mono", 15)


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
    def __init__(self, d):
        self.d = d
        g = np.load(os.path.join(d, "grid.npz"))
        self.xc, self.rc, self.solid = g["xc"], g["rc"], g["solid"]
        self.dx = float(g["DX"])
        self.nx, self.nr = len(self.xc), len(self.rc)
        L = np.loadtxt(os.path.join(d, "log.txt"))
        n = len([f for f in os.listdir(d) if f.startswith("s") and f.endswith(".f32")])
        L = L[:n]
        self.k, self.t = L[:, 0].astype(int), L[:, 1]
        self.thrust, self.Tch, self.pch = L[:, 2], L[:, 3], L[:, 4]
        self.mach_exit, self.mach_thr, self.pa = L[:, 5], L[:, 6], L[:, 7]
        # smooth the wall-pressure thrust a little (start-up waves ring on the walls)
        self.thrust_s = self._smooth(self.thrust, self.t, 0.12)
        self.mach_s = self._smooth(self.mach_exit, self.t, 0.12)
        # physical scale: thrust after the climb-out (vacuum-like) == rated 200 kN
        vac = self.thrust_s[self.t > self.t.max() - 0.4].mean()
        self.L0 = math.sqrt(RATED_THRUST_KN * 1e3 / (vac * P_ATM))
        self.t_unit = self.L0 / U_REF
        self.kN = self.L0 ** 2 * P_ATM / 1e3
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
        a = np.fromfile(os.path.join(self.d, f"s{k:05d}.f32"), np.float32).reshape(3, self.nx, self.nr)
        if len(self.cache) > 6: self.cache.pop(next(iter(self.cache)))
        self.cache[k] = a
        return a


def intensity(rho, p, y, pa, dx):
    """Grid -> display intensity (0..1) and an air-schlieren layer."""
    T = p / rho
    lt = np.clip(np.log(np.maximum(T, 1e-3)) / np.log(11.7), 0, 1)
    lr = np.log(np.maximum(rho, 1e-5))
    gx = np.zeros_like(lr); gr = np.zeros_like(lr)
    gx[1:-1] = (lr[2:] - lr[:-2]) / (2 * dx)
    gr[:, 1:-1] = (lr[:, 2:] - lr[:, :-2]) / (2 * dx)
    sch = np.clip(np.hypot(gx, gr) / 14.0, 0, 1)
    yy = np.clip(y, 0, 1) ** 0.75
    comp = np.clip(np.log(np.maximum(p, 1e-4) / max(pa, 1e-3)) / 3.0, -1, 1)
    I = yy * (0.22 + 0.62 * lt ** 1.1 + 0.16 * (0.5 + 0.5 * comp))
    I *= 1 - 0.32 * sch * yy                                 # wave structure inside the plume
    air = (1 - yy) * sch * 0.16                              # faint waves in the air
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
    outside = (xs < 0) | (xs > field.shape[0] * dx)
    out[:, outside] = 0
    return out


_outline_cache = {}


def engine_layer(view, size):
    """RGBA layer with the engine drawn as a dark body with light outline."""
    key = (view, size)
    if key in _outline_cache: return _outline_cache[key]
    w, h = size
    ss = 3
    x0, x1, rmax = view
    sx = w * ss / (x1 - x0)
    def px(pts, sign):
        return [((x - x0) * sx, (h * ss) / 2 - sign * r * sx) for x, r in pts]
    poly = G.OUTLINE
    full = np.concatenate([poly, (poly * [1, -1])[::-1]])
    lay = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    pts = px(full, 1)
    d.polygon(pts, fill=(15, 14, 30, 255))
    d.line(pts + [pts[0]], fill=(168, 164, 188, 255), width=int(2.2 * ss), joint="curve")
    lay = lay.resize((w, h), Image.LANCZOS)
    _outline_cache[key] = lay
    return lay


def render_sim(run, tn, view, size):
    w, h = size
    x0, x1, rmax = view
    k = run.idx(tn)
    rho, p, y = run.fields(k)
    pa = run.pa[k]
    # crop grid to the view for speed
    i0 = max(int((x0 - 0.1) / run.dx), 0); i1 = min(int((x1 + 0.1) / run.dx) + 2, run.nx)
    j1 = min(int((rmax + 0.1) / run.dx) + 2, run.nr)
    sl = (slice(i0, i1), slice(0, j1))
    I = intensity(rho[sl].astype(np.float64), p[sl].astype(np.float64), y[sl].astype(np.float64), pa, run.dx)
    xs = x0 + (np.arange(w) + 0.5) * (x1 - x0) / w
    rs = ((h / 2) - (np.arange(h) + 0.5)) * (x1 - x0) / w
    img = sample(I, run.xc[i0], run.dx, xs, rs)
    rgb = _lut[np.clip((img * 1023).astype(int), 0, 1023)]
    im = Image.fromarray(rgb.astype(np.uint8), "RGB")
    glow = im.filter(ImageFilter.GaussianBlur(radius=max(3, w / 160)))
    im = Image.blend(im, Image.fromarray(np.maximum(np.asarray(im), np.asarray(glow)), "RGB"), 0.55)
    im.paste(engine_layer(view, size), (0, 0), engine_layer(view, size))
    return im


# ------------------------------------------------------------------ footage
class Footage:
    def __init__(self, path, start, dur, size):
        self.size = size
        w, h = size
        vf = (f"fps={FPS},rotate=-20*PI/180:fillcolor=black,crop=600:355:80:560,"
              f"scale={w}:{h}:flags=lanczos,eq=contrast=1.04:saturation=1.05")
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
A_END = 9.6
X_FADE = 0.7
B0 = A_END + X_FADE
B_DUR = 16.6
LOOP = 0.6
TOTAL = B0 + B_DUR + LOOP
FOOT_START = 3.0

VIEW_A = (0.9, 7.1, (7.1 - 0.9) * 843 / 1080 / 2)
SIZE_A = (1080, 843)
SIZE_B = (1080, 560)
VIEW_B = (0.9, 11.4, (11.4 - 0.9) * 560 / 1080 / 2)
T_ALT0 = 4.8

SIM_A = [(0.0, 0.0), (1.8, 0.30), (4.2, 0.82), (6.8, 1.45), (A_END, 2.30)]
SIM_B = [(0.0, 0.0), (4.5, 1.25), (9.4, 4.8), (13.8, 6.8), (B_DUR, 7.4)]

CAP_A = [(0.0, 2.1, "Methane and oxygen burn in a ring-shaped chamber."),
         (2.1, 4.3, "It chokes at the annular throat and goes supersonic."),
         (4.3, 6.8, "There's no bell. The gas expands along the spike."),
         (6.8, A_END, "The outer wall of this nozzle is the air itself.")]
CAP_B = [(0.0, 2.4, "Same start, next to a real Noyron aerospike."),
         (2.4, 4.8, "The jet leaves the ring and runs along the spike."),
         (4.8, 7.2, "Outside there's no wall: air pressure sets the edge."),
         (7.2, 9.4, "Expansion and compression waves cross the plume."),
         (9.4, 11.8, "Climb out of the air and the plume opens by itself."),
         (11.8, 14.2, "That's altitude compensation. No bell needed."),
         (14.2, B_DUR, "XRA-2E5: 200 kN, 1 m tall, one printed Inconel part.")]


def caption_at(caps, t):
    for a, b, s in caps:
        if a <= t < b:
            fa = min(1, (t - a) / 0.25, (b - t) / 0.2) if b - a > 0.5 else 1
            return s, max(0.0, fa)
    return None, 0


def slower(map_pts, t, run):
    dt_v = 1 / FPS
    s0 = lerp_map(t, map_pts); s1 = lerp_map(t + dt_v, map_pts)
    phys = (s1 - s0) * run.t_unit
    return dt_v / phys if phys > 0 else 0


def header(d, right, prog):
    spaced(d, (100, 244), "MADE WITH CLAUDE (AI)", F_LABEL, (205, 201, 218), 2.2)
    spaced(d, (980, 244), right, F_LABEL, LAV, 2.2, "r")
    y = 290
    d.line([(100, y), (980, y)], fill=(70, 67, 88), width=1)
    for i in range(0, 89):
        x = 100 + i * 10
        hh = 7 if i % 5 == 0 else 4
        d.line([(x, y), (x, y - hh)], fill=(70, 67, 88), width=1)
    xm = 100 + prog * 880
    d.line([(xm, y + 6), (xm, y - 18)], fill=INK, width=2)


def sparkline(d, run, t_now, t_max, box):
    x0, y0, x1, y1 = box
    ts = run.t[run.t <= t_max]
    for arr, col, lo, hi in [(run.Tch, (210, 206, 225), 1, 12.5), (run.pch, LAV, 1, 52)]:
        pts = []
        for tt in ts:
            if tt > t_now: break
            v = np.interp(tt, run.t, arr)
            pts.append((x0 + (x1 - x0) * tt / t_max, y1 - (y1 - y0) * (v - lo) / (hi - lo)))
        d.line([(x0, y1), (x1, y1)], fill=(52, 50, 68), width=1)
        if len(pts) > 1:
            d.line(pts, fill=col, width=2)
            d.ellipse([pts[-1][0] - 4, pts[-1][1] - 4, pts[-1][0] + 4, pts[-1][1] + 4], fill=col)


def stat_block(d, x, y, label, val, unit, fv=F_VAL):
    spaced(d, (x, y), label, F_SMALL, DIM, 1.5)
    d.text((x, y + 20), val, font=fv, fill=INK)
    wv = d.textlength(val, font=fv)
    d.text((x + wv + 6, y + 20 + fv.size * 0.62), unit, font=F_UNIT, fill=DIM)


def inline_stat(d, x, y, label, val, unit):
    w = spaced(d, (x, y + 13), label, F_SMALL, DIM, 1.5)
    x += w + 10
    d.text((x, y), val, font=F_VALB, fill=INK)
    x += d.textlength(val, font=F_VALB) + 5
    d.text((x, y + 13), unit, font=F_UNIT, fill=DIM)
    return x + d.textlength(unit, font=F_UNIT)


def to_px(view, size, origin, x, r):
    x0, x1, rmax = view
    w, h = size
    s = w / (x1 - x0)
    return origin[0] + (x - x0) * s, origin[1] + h / 2 - r * s


def annotate(d, view, size, origin, x, r, label, a, side="up", length=60):
    """Marker + leader line + label. side: up/down/left/right."""
    if a <= 0: return
    px, py = to_px(view, size, origin, x, r)
    col = alpha_blend((214, 208, 236), a, PANEL)
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


def ann_alpha(t, a, b):
    return ease((t - a) / 0.3) * ease((b - t) / 0.3)


# ------------------------------------------------------------------ frames
def frame_A(run, t, out=None):
    im = Image.new("RGB", (W, H), BG)
    tn = lerp_map(t, SIM_A)
    sim = render_sim(run, tn, VIEW_A, SIZE_A)
    oy = 492
    im.paste(sim, (0, oy))
    d = ImageDraw.Draw(im)
    header(d, "SIMULATION", t / TOTAL)
    d.text((100, 300), "How an aerospike starts", font=F_TITLE, fill=INK)
    d.text((100, 392), "modelled on LEAP 71's 200 kN XRA-2E5, then a real hot fire",
           font=font("serifi", 27), fill=(170, 166, 186))
    # annotations
    org = (0, oy)
    thr_pt = G.E + G.S_THR * G.D
    annotate(d, VIEW_A, SIZE_A, org, G.CH_X + 0.25, G.CH_R + 0.22, "TOROIDAL CHAMBER", ann_alpha(t, 0.3, 2.1), "right", 230)
    annotate(d, VIEW_A, SIZE_A, org, thr_pt[0], -thr_pt[1], "ANNULAR THROAT", ann_alpha(t, 2.2, 4.3), "right", 110)
    annotate(d, VIEW_A, SIZE_A, org, 3.9, -G.r_spike(3.9), "SPIKE", ann_alpha(t, 4.4, 6.8), "down", 70)
    annotate(d, VIEW_A, SIZE_A, org, FB_A[0], FB_A[1], "FREE BOUNDARY: AIR", ann_alpha(t, 6.9, 9.4), "up", 50)
    # time row
    y = 1360
    ms = tn * run.t_unit * 1e3
    spaced(d, (100, y), f"T+ {ms:.3f} ms", F_LABEL, (205, 201, 218), 1.6)
    spaced(d, (980, y), f"{fmt(slower(SIM_A, t, run))}× SLOWER", F_LABEL, LAV, 1.6, "r")
    cap, ca = caption_at(CAP_A, t)
    if cap: d.text((100, 1398), cap, font=F_CAP, fill=alpha_blend(INK, ca))
    # stats
    y = 1470
    thr = max(0.0, run.stat(tn, run.thrust_s)) * run.kN
    me = run.stat(tn, run.mach_s)
    tc = run.stat(tn, run.Tch) * T_AMB
    pc = run.stat(tn, run.pch) * 1.01325
    stat_block(d, 100, y, "THRUST", fmt(thr), "kN")
    stat_block(d, 320, y, "EXIT MACH", f"{me:.2f}", "")
    stat_block(d, 530, y, "CHAMBER", fmt(tc), "K")
    stat_block(d, 770, y, "Pc", f"{pc:.1f}", "bar")
    sparkline(d, run, tn, SIM_A[-1][1], (100, 1575, 930, 1610))
    spaced(d, (100, 1624), "CHAMBER TEMP", F_TINY, (150, 146, 166), 1.4)
    spaced(d, (290, 1624), "CHAMBER PRESSURE", F_TINY, (140, 126, 200), 1.4)
    return im


def frame_B(run, foot, t, t_global):
    im = Image.new("RGB", (W, H), BG)
    tn = lerp_map(t, SIM_B)
    oy = 322
    sim = render_sim(run, tn, VIEW_B, SIZE_B)
    im.paste(sim, (0, oy))
    fy = 1012
    fi = int(round(t * FPS))
    fr = foot.frame_at(fi)
    im.paste(fr, (0, fy))
    im.paste(Image.new("RGB", (W, 110), (6, 5, 14)), (0, fy), _shade_mask())
    d = ImageDraw.Draw(im)
    header(d, "SIMULATION VS REAL", t_global / TOTAL)
    # sim labels
    spaced(d, (100, oy + 24), "SIMULATION", F_LABEL, (205, 201, 218), 2.0, stroke=4)
    ms = tn * run.t_unit * 1e3
    pa = run.stat(tn, run.pa)
    if tn < T_ALT0:
        rt = f"T+ {ms:.2f} ms · {fmt(slower(SIM_B, t, run))}× SLOWER"
    else:
        rt = f"AMBIENT {pa:.2f} atm"
    spaced(d, (980, oy + 24), rt, F_LABEL, LAV, 1.6, "r", stroke=4)
    org = (0, oy)
    v, s = VIEW_B, SIZE_B
    annotate(d, v, s, org, 2.85, -(G.r_spike(2.85) + 0.05), "ANNULAR JET", ann_alpha(t, 2.5, 4.8), "left", 70)
    annotate(d, v, s, org, FB_B[0], FB_B[1], "FREE BOUNDARY", ann_alpha(t, 4.9, 7.2), "up", 50)
    annotate(d, v, s, org, G.X_SPIKE_END + 0.25, 0.0, "BASE WAKE", ann_alpha(t, 4.9, 7.2), "right", 90)
    annotate(d, v, s, org, WV_B[0], -WV_B[1], "WAVES", ann_alpha(t, 7.3, 9.4), "left", 105)
    annotate(d, v, s, org, PO_B[0], PO_B[1], "PLUME OPENS", ann_alpha(t, 10.4, 14.1), "up", 40)
    # caption + stats
    cap, ca = caption_at(CAP_B, t)
    if cap: d.text((100, 896), cap, font=F_CAPB, fill=alpha_blend(INK, ca))
    y = 950
    thr = max(0.0, run.stat(tn, run.thrust_s)) * run.kN
    pc = run.stat(tn, run.pch) * 1.01325
    me = run.stat(tn, run.mach_s)
    x = inline_stat(d, 100, y, "THRUST", fmt(thr), "kN")
    x = inline_stat(d, x + 26, y, "Pc", f"{pc:.1f}", "bar")
    x = inline_stat(d, x + 26, y, "MACH", f"{me:.2f}", "")
    x = inline_stat(d, x + 26, y, "AIR", f"{pa:.2f}", "atm")
    # footage labels
    spaced(d, (100, fy + 22), "REAL · LEAP 71 AEROSPIKE HOT FIRE", F_LABEL, (225, 221, 236), 2.0)
    spaced(d, (100, fy + 50), "AN EARLIER NOYRON ENGINE, NOT THE XRA-2E5", F_SMALL, (190, 186, 206), 1.5)
    # credits
    cy = fy + SIZE_FOOT[1] + 18
    for i, line in enumerate(CREDITS):
        spaced(d, (980, cy + i * 21), line, F_TINY, (88, 85, 106), 1.3, "r")
    return im


SIZE_FOOT = (1080, 639)
FB_A = (3.6, 1.4)      # annotation anchors (x, r), set from the solution
FB_B = (3.8, 1.35)
WV_B = (3.3, 0.85)
PO_B = (4.7, 1.8)
_shade = None


def _shade_mask():
    global _shade
    if _shade is None:
        a = (np.linspace(1, 0, 110) ** 1.6 * 190).astype(np.uint8)
        _shade = Image.fromarray(np.repeat(a[:, None], W, 1), "L")
    return _shade
CREDITS = ["FOOTAGE · LEAP 71 (@LEAP.71), AEROSPIKE HOT FIRE",
           "SIM · 2D AXISYMMETRIC EULER, γ 1.2, SPIKE TRACED FROM THE XRA-2E5 RENDER",
           "SPECS · LEAP71.COM: XRA-2E5, 200 kN, CH4/LOX, 1 m, INCONEL 718",
           "Pc 50 bar FROM THE 20 kN SIBLING · THRUST SCALED TO 200 kN IN VACUUM"]


def make_frame(run, foot, n):
    t = n / FPS
    if t < A_END:
        return frame_A(run, t)
    if t < B0:
        a = ease((t - A_END) / X_FADE)
        fa = frame_A(run, A_END - 1e-3)
        fb = frame_B(run, foot, 0.0, t)
        return Image.blend(fa, fb, a)
    if t < B0 + B_DUR:
        return frame_B(run, foot, t - B0, t)
    a = ease((t - B0 - B_DUR) / LOOP)
    fb = frame_B(run, foot, B_DUR - 1e-3, t)
    return Image.blend(fb, frame_A(run, 0.0), a)


def main():
    run_dir, footage, out = sys.argv[1:4]
    run = Run(run_dir)
    print(f"L0 = {run.L0:.4f} m, time unit = {run.t_unit * 1e3:.4f} ms, total sim "
          f"{run.t[-1] * run.t_unit * 1e3:.2f} ms, engine length "
          f"{(G.X_SPIKE_END - G.X_T) * run.L0:.2f} m spike, body dia {2 * G.R_BODY * run.L0:.2f} m, "
          f"sea-level thrust {run.stat(5.4, run.thrust_s) * run.kN:.0f} kN", flush=True)
    if "--preview" in sys.argv:
        ts = [float(v) for v in sys.argv[sys.argv.index("--preview") + 1].split(",")]
        foot = Footage(footage, FOOT_START, B_DUR, SIZE_FOOT)
        for t in sorted(ts):
            n = int(t * FPS)
            if t >= B0:
                foot.frame_at(int((t - B0) * FPS))
            make_frame(run, foot, n).save(out.replace(".mp4", f"_{t:05.2f}.png"))
        return
    foot = Footage(footage, FOOT_START, B_DUR, SIZE_FOOT)
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
    # audio: synthesized rumble for part A, the hot-fire's own sound for part B
    make_audio(run, footage, out + ".audio.wav")
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", out + ".audio.wav",
                           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out])
    os.remove(tmp); os.remove(out + ".audio.wav")
    print("wrote", out)


def make_audio(run, footage, path):
    sr = 48000
    n = int(TOTAL * sr)
    rng = np.random.default_rng(7)
    # brown-ish noise rumble following simulated chamber pressure in part A
    wn = rng.standard_normal(n)
    br = np.cumsum(wn); br -= np.convolve(br, np.ones(4801) / 4801, mode="same")
    br /= np.abs(br).max() + 1e-9
    tt = np.arange(n) / sr
    tn = np.interp(tt, [p[0] for p in SIM_A], [p[1] for p in SIM_A])
    env = np.interp(tn, run.t, run.pch) / 50.0
    env = np.clip(env, 0, 1) ** 0.8 * (tt < A_END + X_FADE)
    env *= np.clip((A_END + X_FADE - tt) / X_FADE, 0, 1)
    rumble = br * env * 0.35
    # footage audio
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(FOOT_START - X_FADE), "-t", str(B_DUR + LOOP + X_FADE),
                          "-i", footage, "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True).stdout
    fa = np.frombuffer(raw, np.float32).reshape(-1, 2)
    mix = np.zeros((n, 2), np.float32)
    mix[:, 0] += rumble; mix[:, 1] += rumble
    s0 = int((B0 - X_FADE) * sr)
    m = min(len(fa), n - s0)
    fade = np.clip(np.arange(m) / (X_FADE * sr), 0, 1)[:, None]
    tail = np.clip((n - s0 - np.arange(m)) / (LOOP * sr), 0, 1)[:, None]
    mix[s0:s0 + m] += fa[:m] * fade * tail
    mix = np.clip(mix, -1, 1)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", "-", path],
                   input=mix.astype(np.float32).tobytes(), check=True)


if __name__ == "__main__":
    main()
