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
RATED_THRUST_KN = 20.0                   # LEAP 71: 20 kN methalox aerospike (sea level)

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
        # physical scale: steady sea-level thrust == the engine's 20 kN
        sl = self.thrust_s[(self.t > 3.0) & (self.t < 4.7)].mean()
        self.L0 = math.sqrt(RATED_THRUST_KN * 1e3 / (sl * P_ATM))
        self.t_unit = self.L0 / U_REF
        self.kN = self.L0 ** 2 * P_ATM / 1e3
        self.cache = {}
        self.exit_p = self._exit_pressure()

    def _exit_pressure(self):
        """Exhaust-weighted static pressure just outside the slot exit (cached)."""
        fn = os.path.join(self.d, "exit_p.npy")
        if os.path.exists(fn):
            return np.load(fn)
        i = int((G.X_LIP + 0.06) / self.dx)
        w_r = self.rc
        out = np.zeros(len(self.t))
        for k in range(len(self.t)):
            a = np.fromfile(os.path.join(self.d, f"s{k:05d}.f32"), np.float32, count=3 * self.nx * self.nr)
            a = a.reshape(3, self.nx, self.nr)
            p, y = a[1, i], a[2, i]
            w = y * w_r * (~self.solid[i])
            out[k] = (p * w).sum() / w.sum() if w.sum() > 1e-6 else 1.0
        np.save(fn, out)
        return out

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
    lay = engine_layer(view, size)
    im.paste(lay, (0, 0), lay)
    return im


# ------------------------------------------------------------------ footage
CROP_WIDE = "rotate=-30*PI/180:fillcolor=black,crop=520:308:60:320"    # wide shot, 0-1.8 s
CROP_CLOSE = "rotate=-20*PI/180:fillcolor=black,crop=600:355:80:560"   # close-up, 1.8 s on


class Footage:
    def __init__(self, path, start, dur, size, crop=CROP_CLOSE):
        self.size = size
        w, h = size
        vf = (f"fps={FPS},{crop},"
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
# Same rhythm as the reference: one continuous take, no restart of the sim.
T_A_END = 8.6       # part A: close-up, slow pull-back, three captions
T_TR_END = 9.25     # header/title fade, panel moves up, footage fades in
T_IGN = 10.0        # the jet leaves the slot in the sim == ignition in the footage
T_CUT = 11.8        # footage cuts from the wide shot to the close-up
T_FLASH = 12.85     # sim panel flashes when the real engine reaches full flow
T_B_END = 22.3      # end of part B
T_RW_END = 23.25    # rewind + push-in back to the first frame
TOTAL = 23.8
FOOT_WIDE0 = 0.0    # footage time of ignition (wide shot), shown at T_IGN
FOOT_FULL = 6.35    # footage time of full flow (close-up), shown at T_FLASH
FOOT_CLOSE0 = FOOT_FULL - (T_FLASH - T_CUT)

PANEL_A = (492, 843)
PANEL_B = (322, 560)
VIEW_A0 = (2.4, 8.1)
VIEW_A1 = (0.3, 11.6)
VIEW_B = (1.5, 10.5)

SIM_MAP = [(0.0, 0.22), (3.0, 0.42), (7.0, 0.58), (T_A_END, 0.62), (T_TR_END, 0.64),
           # after ignition the sim jet length tracks the real flame length frame by frame
           # (both measured as a fraction of their panel; the real flame appears on the frame at +0.10 s)
           (T_IGN, 0.68), (T_IGN + 0.067, 0.72), (T_IGN + 0.10, 1.85), (T_IGN + 0.133, 2.30),
           (T_IGN + 0.20, 2.75),
           (T_IGN + 0.80, 3.20), (T_IGN + 0.90, 3.75), (T_B_END, 4.75),
           (T_RW_END, 0.9), (TOTAL, 0.22)]

TYPE_RATE = 46.0    # characters per second
CAPS_A = [(0.25, "Methane and oxygen burn in a ring-shaped chamber."),
          (3.1, "Hot gas floods the ring and pushes into the slot."),
          (7.0, "Pressure climbs until the annular throat chokes.")]
CAPS_B = [(10.5, "First light: the jet bursts out along the spike."),
          (12.25, "A dim violet jet first, then the full flow, in both."),
          (13.75, "There's no bell, so the air itself is the outer wall."),
          (16.5, ("It pinches shut past the tip", 17.0, ", in the solve and on the stand.")),
          (20.0, None)]                       # closing line, filled in with the sim length
CAP_FADE_B = (19.45, 19.75)

SIZE_FOOT = (1080, 639)
CREDITS = ["FOOTAGE · LEAP 71 (@LEAP.71), 20 kN METHALOX AEROSPIKE HOT FIRE",
           "SIM · 2D AXISYMMETRIC EULER, SHAPE TRACED FROM THE ENGINE",
           "Pc 50 bar (LEAP71.COM) · THRUST SCALED TO 20 kN AT SEA LEVEL"]
FB_B = (6.3, 1.7)      # annotation anchors (x, r), from the solution
WV_B = (5.4, 0.85)
PC_B = None            # set at start-up from the solution (where the plume closes)


def smooth_step(t, a, b):
    return ease((t - a) / (b - a)) if b > a else float(t >= a)


def view_at(t):
    def mix(v0, v1, s):
        c0, c1 = (v0[0] + v0[1]) / 2, (v1[0] + v1[1]) / 2
        w0, w1 = v0[1] - v0[0], v1[1] - v1[0]
        c = c0 + (c1 - c0) * s
        w = math.exp(math.log(w0) + (math.log(w1) - math.log(w0)) * s)
        return (c - w / 2, c + w / 2)
    if t < 2.9: return VIEW_A0
    if t < T_A_END: return mix(VIEW_A0, VIEW_A1, smooth_step(t, 2.9, T_A_END))
    if t < T_TR_END: return mix(VIEW_A1, VIEW_B, smooth_step(t, T_A_END, T_TR_END))
    if t < T_B_END: return VIEW_B
    if t < T_RW_END: return mix(VIEW_B, VIEW_A0, smooth_step(t, T_B_END, T_RW_END))
    return VIEW_A0


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


_shade = None


def _shade_mask():
    global _shade
    if _shade is None:
        a = (np.linspace(1, 0, 130) ** 1.3 * 215).astype(np.uint8)
        _shade = Image.fromarray(np.repeat(a[:, None], W, 1), "L")
    return _shade


def make_frame(run, foot, n):
    t = n / FPS
    tn = sim_time(t)
    py, ph, ps = panel_at(t)
    x0, x1 = view_at(t)
    view = (x0, x1, (x1 - x0) * ph / W / 2)
    size = (W, ph)
    im = Image.new("RGB", (W, H), BG)

    # alphas
    aA = 1 - smooth_step(t, T_A_END, T_A_END + 0.3) if t < T_B_END else smooth_step(t, T_RW_END - 0.25, T_RW_END)
    aB = smooth_step(t, T_TR_END - 0.25, T_TR_END + 0.05) * (1 - smooth_step(t, T_B_END, T_B_END + 0.3))
    aF = smooth_step(t, 9.0, 9.4) * (1 - smooth_step(t, T_B_END, T_B_END + 0.45))

    # footage (bottom), fades in from black
    fy = 1012
    if aF > 0:
        if t < T_CUT:
            fr = foot[0].frame_at(max(0, int(round((t - T_IGN) * FPS))))
        else:
            fr = foot[1].frame_at(int(round((t - T_CUT) * FPS)))
        fr = Image.blend(Image.new("RGB", SIZE_FOOT, BG), fr, aF)
        im.paste(fr, (0, fy))
        im.paste(Image.new("RGB", (W, 130), (6, 5, 14)), (0, fy), _shade_mask().point(lambda v: int(v * aF)))

    sim = render_sim(run, tn, view, size)
    # flash when the real engine reaches full flow
    fl = 0.0
    if T_FLASH - 0.08 <= t < T_FLASH + 0.6:
        fl = 0.62 * (smooth_step(t, T_FLASH - 0.08, T_FLASH) if t < T_FLASH else math.exp(-(t - T_FLASH) / 0.16))
    if fl > 0:
        sim = Image.blend(sim, Image.new("RGB", size, (236, 232, 244)), fl)
    im.paste(sim, (0, py))
    d = ImageDraw.Draw(im)

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
        stat_block(d, 320, y, "EXIT MACH", f"{run.stat(tn, run.mach_s):.2f}", "", aA)
        stat_block(d, 530, y, "CHAMBER", fmt(run.stat(tn, run.Tch) * T_AMB), "K", aA)
        stat_block(d, 770, y, "Pc", f"{run.stat(tn, run.pch) * 1.01325:.1f}", "bar", aA)
        sparkline(d, run, tn, SIM_MAP[4][1], (100, y + 105, 930, y + 140), aA)
        spaced(d, (100, y + 154), "CHAMBER TEMP", F_TINY, alpha_blend((150, 146, 166), aA), 1.4)
        spaced(d, (290, y + 154), "CHAMBER PRESSURE", F_TINY, alpha_blend((140, 126, 200), aA), 1.4)

    # ---------------- part B overlays
    if aB > 0:
        py, ph = PANEL_B          # part-B text sits at its final place while it fades in
        org = (0, py)
        spaced(d, (100, py + 24), "SIMULATION", F_LABEL, alpha_blend((205, 201, 218), aB), 2.0, stroke=4)
        ms = tn * run.t_unit * 1e3
        spaced(d, (980, py + 24), f"T+ {ms:.2f} ms · {fmt(slower(t, run))}× SLOWER", F_LABEL,
               alpha_blend(LAV, aB), 1.6, "r", stroke=4)
        annotate(d, view, size, org, FB_B[0], FB_B[1], "FREE BOUNDARY",
                 aB * smooth_step(t, 14.0, 14.3), "up", 50)
        annotate(d, view, size, org, WV_B[0], -WV_B[1], "WAVES",
                 aB * smooth_step(t, 15.0, 15.3), "left", 105)
        annotate(d, view, size, org, PC_B[0], PC_B[1], "PLUME CLOSES",
                 aB * smooth_step(t, 17.0, 17.3), "up", 70)
        cap = typed(CAPS_B, t)
        ca = aB * (1 - smooth_step(t, *CAP_FADE_B)) if t < CAPS_B[-1][0] else aB
        if cap and ca > 0:
            d.text((100, py + ph + 14), cap, font=F_CAPB, fill=alpha_blend(INK, ca))
        y = py + ph + 68
        thr = max(0.0, run.stat(tn, run.thrust_s)) * run.kN
        x = inline_stat(d, 100, y, "THRUST", f"{thr:.1f}", "kN", aB)
        x = inline_stat(d, x + 26, y, "Pc", f"{run.stat(tn, run.pch) * 1.01325:.1f}", "bar", aB)
        x = inline_stat(d, x + 26, y, "MACH", f"{run.stat(tn, run.mach_s):.2f}", "", aB)
        x = inline_stat(d, x + 26, y, "EXIT", f"{run.stat(tn, run.exit_p):.2f}", "atm", aB)
    if aF > 0:
        spaced(d, (100, fy + 22), "REAL · LEAP 71 20 kN AEROSPIKE", F_LABEL, alpha_blend((236, 232, 244), aF), 2.0, stroke=3)
        spaced(d, (980, fy + 22), "REAL TIME", F_LABEL, alpha_blend((236, 232, 244), aF), 2.0, "r", stroke=3)
        cy = fy + SIZE_FOOT[1] + 18
        for i, line in enumerate(CREDITS):
            spaced(d, (980, cy + i * 21), line, F_TINY, alpha_blend((96, 93, 114), aF), 1.3, "r")
    return im


def find_closure(run):
    """Axis point behind the spike tip where the plume closes (steady sea level)."""
    k = run.idx(4.4)
    rho, p, y = run.fields(k)
    i0 = int((G.X_SPIKE_END + 0.2) / run.dx)
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
    total_ms = SIM_MAP[-3][1] * run.t_unit * 1e3
    CAPS_B[-1] = (20.0, f"The whole simulation is {total_ms:.1f} ms, quicker than a blink.")
    print(f"L0 = {run.L0:.4f} m, time unit = {run.t_unit * 1e3:.4f} ms, shown sim {total_ms:.2f} ms, "
          f"plume closes at x = {PC_B[0]:.2f}", flush=True)
    foot = (Footage(footage, FOOT_WIDE0, T_CUT - T_IGN + 0.2, SIZE_FOOT, CROP_WIDE),
            Footage(footage, FOOT_CLOSE0, TOTAL - T_CUT, SIZE_FOOT, CROP_CLOSE))
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
    """Rumble that follows the simulated chamber pressure, then the hot fire's own sound."""
    sr = 48000
    n = int(TOTAL * sr)
    rng = np.random.default_rng(7)
    br = np.cumsum(rng.standard_normal(n)); br -= np.convolve(br, np.ones(4801) / 4801, mode="same")
    br /= np.abs(br).max() + 1e-9
    tt = np.arange(n) / sr
    tn = np.interp(tt, [p[0] for p in SIM_MAP], [p[1] for p in SIM_MAP])
    env = np.clip(np.interp(tn, run.t, run.pch) / 50.0, 0, 1) ** 0.8
    gate = 1 - np.clip((tt - T_IGN) / 0.3, 0, 1) + np.clip((tt - T_B_END) / 0.6, 0, 1)
    rumble = br * env * np.clip(gate, 0, 1) * 0.35

    def clip(start, dur):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", footage,
                              "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
        return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()

    mix = np.zeros((n, 2), np.float32)
    mix[:, 0] += rumble; mix[:, 1] += rumble
    xf = int(0.03 * sr)
    wide = clip(FOOT_WIDE0, T_CUT - T_IGN + 0.03)
    close = clip(FOOT_CLOSE0 - 0.03, TOTAL - T_CUT + 0.03)
    i0 = int(T_IGN * sr); m = min(len(wide), n - i0)
    fade_out = np.ones(m); fade_out[-xf:] = np.linspace(1, 0, xf)
    mix[i0:i0 + m] += wide[:m] * fade_out[:, None]
    i1 = int(T_CUT * sr) - xf; m = min(len(close), n - i1)
    tl = np.arange(m) / sr + i1 / sr
    g = np.clip((tl - (T_CUT - 0.03)) / 0.03, 0, 1) * (1 - np.clip((tl - T_B_END) / 0.6, 0, 1))
    mix[i1:i1 + m] += close[:m] * g[:, None]
    mix = np.clip(mix, -1, 1)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", "-", path],
                   input=mix.astype(np.float32).tobytes(), check=True)


if __name__ == "__main__":
    main()
