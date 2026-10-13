"""Typeset the formula sheet that accompanies the picture."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

W_PX, H_PX, DPI = 2048, 1270, 200
FIG = (W_PX / DPI, H_PX / DPI)

TITLE = r"$\mathrm{Island\ Three\ (O'Neill\ cylinder)}$"
SUB = (r"$\mathrm{Every\ mark\ is\ a\ sample\ of\ one\ of\ the\ curve\ families\ below,\ drawn\ for}$"
       r"$\ k=1,2,3,\ldots,n\ \mathrm{and}\ t\in[0,1].$"
       r"$\ \mathrm{The\ shading\ is\ the\ accumulated\ density\ of\ the\ curves;}$"
       r"$\ \mathrm{The\ only\ mark\ not\ made\ by\ a\ curve\ is\ the\ flat\ background\ colour.}$")

COLS = [
[
 (r"$\mathbf{View\ from\ inside\ the\ tube}$", 1),
 (r"$\mathrm{The\ habitat\ is}\ x^2+y^2=1,\ \mathrm{axis}\ z.\ \mathrm{The\ eye\ is\ at}$", 0),
 (r"$E=(0,-e,0),\ e=0.62,\ \mathrm{pitched\ down\ by}\ B=0.22,$", 0),
 (r"$\mathrm{rolled\ by}\ \rho=0.05.\ \mathrm{A\ point\ at\ angle}\ T,\ \mathrm{axial}$", 0),
 (r"$\mathrm{distance}\ Z\ \mathrm{and\ radius}\ R\ \mathrm{lands\ at}$", 0),
 (r"$w=(R\cos T-e)\sin B+Z\cos B$", 0),
 (r"$x_0=\frac{R\sin T}{w},\qquad y_0=\frac{(e-R\cos T)\cos B+Z\sin B}{w}$", 0),
 (r"$P(T,Z,R)=(x_0\cos\rho-(y_0-\tau)\sin\rho,$", 0),
 (r"$\qquad\qquad x_0\sin\rho+(y_0-\tau)\cos\rho+\tau),\quad \tau=\tan B$", 0),
 ("", 0),
 (r"$\mathbf{Axial\ parameter}$", 1),
 (r"$Z(t)=(\frac{1}{Z_0}+(\frac{1}{Z_c}-\frac{1}{Z_0})t)^{-1},\ Z_0=0.30,\ Z_c=9$", 0),
 (r"$\mathrm{Linear\ in}\ 1/Z,\ \mathrm{so\ samples\ stay\ evenly\ spaced\ on\ screen.}$", 0),
 ("", 0),
 (r"$\mathbf{Six\ sectors}$", 1),
 (r"$\mathrm{Valleys\ of\ width}\ W_L=1.30\ \mathrm{centred\ at}\ T=0,\frac{2\pi}{3},\frac{4\pi}{3};$", 0),
 (r"$\mathrm{windows\ fill\ the\ rest.\ A\ point\ sees\ space\ when}$", 0),
 (r"$\mathrm{mod}(T+\frac{W_L}{2},\ \frac{2\pi}{3})>W_L$", 0),
 ("", 0),
 (r"$\mathbf{Light\ from\ the\ window\ strips}$", 1),
 (r"$\mathrm{A\ strip\ at\ angle}\ F\ \mathrm{meets\ the\ wall\ at}\ T\ \mathrm{with\ cosine}$", 0),
 (r"$\mathrm{factor}\ \left|\sin\frac{T-F}{2}\right|,\ \mathrm{so\ the\ irradiance\ is}$", 0),
 (r"$L(T)=0.30+\left|\sin\frac{T-\pi}{2}\right|$", 0),
 (r"$\qquad\quad +\ 0.34\left|\sin\frac{T-\pi/3}{2}\right|+0.34\left|\sin\frac{T-5\pi/3}{2}\right|$", 0),
 ("", 0),
 (r"$\mathbf{Aerial\ perspective}$", 1),
 (r"$f=\mathrm{clip}(\frac{Z-0.55}{5.5},0,1)^{0.9},\quad c\mapsto(1-0.70f)\,c+0.70f\,a$", 0),
 (r"$a=(0.330,\,0.372,\,0.405)$", 0),
 ("", 0),
 (r"$\mathbf{Deterministic\ hash}$", 1),
 (r"$h(k,\sigma)=\mathrm{frac}(43758.5453\,\sin(12.9898k+78.233\sigma))$", 0),
],
[
 (r"$\mathbf{The\ three\ valleys}\quad j=0,1,2;\ \ k=1,\ldots,1000$", 1),
 (r"$s=\frac{k-\frac{1}{2}}{1000},\qquad Z=Z(t)$", 0),
 (r"$T_j(k,t)=\frac{2\pi j}{3}+W_L(s-\frac{1}{2})+\sin(\pi s)[$", 0),
 (r"$\quad 0.050\sin(5.3Z+11s+2.1j)$", 0),
 (r"$\quad +\ 0.020\sin(12.1Z+23s)+0.009\sin(29Z+7s)]$", 0),
 (r"$R_j(k,t)=1-0.021\sin(\pi s)[\sin(4.1Z+9s)+0.6\sin(11Z+3s)]$", 0),
 (r"$\mathrm{curve}\ =\ P(T_j(k,t),\,Z(t),\,R_j(k,t))$", 0),
 ("", 0),
 (r"$\mathrm{The\ factor}\ \sin(\pi s)\ \mathrm{vanishes\ at}\ s=0,1,\ \mathrm{so\ the\ meander}$", 0),
 (r"$\mathrm{and\ the\ relief\ leave\ the\ strip\ borders\ straight.}$", 0),
 ("", 0),
 (r"$\mathbf{Ground\ colour}$", 1),
 (r"$G=\frac{1}{2}+\frac{1}{2}\sin(8.6\pi s+2.2\sin(3.3Z+1.9j)$", 0),
 (r"$\qquad\qquad\quad +\ 1.1\sin(2.1Z+6s)+1.7j)$", 0),
 (r"$g=\mathrm{clip}(0.76\,G+0.24(\frac{1}{2}+\frac{1}{2}\sin(57s+15Z)),0,1)$", 0),
 (r"$c=\mathrm{ramp}(g;\ c_1,c_2,c_3)\cdot\frac{L(T)}{1.5},\quad \mathrm{then\ hazed}$", 0),
 (r"$c_1=(0.045,0.095,0.030)\quad \mathrm{(forest)}$", 0),
 (r"$c_2=(0.235,0.345,0.075)\quad \mathrm{(pasture)}$", 0),
 (r"$c_3=(0.640,0.655,0.200)\quad \mathrm{(sunlit\ grain)}$", 0),
 ("", 0),
 (r"$\mathbf{Field\ parcels}\quad k=1,\ldots,440$", 1),
 (r"$Z_p=0.42+3.3\,h(k,31)^{1.35},\quad \theta=2\pi h(k,34)$", 0),
 (r"$\ell=0.055+0.13\,h(k,33)$", 0),
 (r"$T=\frac{2\pi}{3}(k\ \mathrm{mod}\ 3)+0.86W_L(h(k,32)-\frac{1}{2})$", 0),
 (r"$\qquad +\ \ell(t-\frac{1}{2})\cos\theta$", 0),
 (r"$Z=Z_p(1+0.16\,\ell\,(t-\frac{1}{2})\sin\theta)$", 0),
 ("", 0),
 (r"$\mathbf{Amplitude}$", 1),
 (r"$\mathrm{Energy\ per\ square\ pixel}=\frac{A}{\delta\cdot\Delta},\ \ \delta=\mathrm{sample\ spacing},$", 0),
 (r"$\Delta=\mathrm{spacing\ between\ neighbouring\ curves}\propto 1/Z.$", 0),
 (r"$\mathrm{So\ each\ sample\ carries}\ A=c\cdot\delta/Z\ \mathrm{for\ the\ valleys.}$", 0),
],
[
 (r"$\mathbf{River}\quad k=1,\ldots,160$", 1),
 (r"$Z=(\frac{1}{0.33}+(\frac{1}{5.2}-\frac{1}{0.33})t)^{-1}$", 0),
 (r"$S=1+2.2\,e^{-(Z-0.95)^2/0.070}+1.1\,e^{-(Z-2.3)^2/0.18}$", 0),
 (r"$T=0.085\sin(2.3Z)+0.030\sin(5.9Z+1)$", 0),
 (r"$\qquad +\ (0.0135+0.006\sin(1.9Z))\,S\,(\frac{2k-1}{160}-1)$", 0),
 (r"$\mathrm{The\ bumps\ of}\ S\ \mathrm{are\ where\ the\ channel\ opens\ into\ lakes.}$", 0),
 ("", 0),
 (r"$\mathbf{Cloud\ decks}\quad k=1,\ldots,600$", 1),
 (r"$Z_0=0.48+2.1\,h(k,22)^{1.25},\ \ Z=Z_0(1+(0.07+0.24h(k,23))t)$", 0),
 (r"$T=\frac{2\pi}{3}(k\ \mathrm{mod}\ 3)+0.78W_L(h(k,21)-\frac{1}{2})$", 0),
 (r"$\qquad +\ 0.034(h(k,24)-\frac{1}{2})\sin(\pi t)+0.010\sin(2t+k)$", 0),
 (r"$R=0.930+0.012\sin(3t+2k)\quad \mathrm{(they\ float\ below\ the\ wall)}$", 0),
 ("", 0),
 (r"$\mathbf{Far\ end\ cap}\quad u=k/300$", 1),
 (r"$\mathrm{curve}=P(2\pi t,\ Z_c,\ u)$", 0),
 (r"$\mathrm{rim}=2.6\,e^{-(u-1)^2/0.00016},\quad \mathrm{hub}=0.22\,e^{-(u-0.145)^2/0.00045}$", 0),
 (r"$\mathrm{Spokes}:\ P(\frac{2\pi k}{36},\ Z_c,\ t),\ \mathrm{faded\ as}\ t^{1.6}.$", 0),
 ("", 0),
 (r"$\mathbf{Sun\ in\ the\ top\ window}\quad k=1,\ldots,1100$", 1),
 (r"$\alpha=2\pi h(k,11),\quad \lambda=0.028+0.30\,h(k,12)^{2.8}$", 0),
 (r"$(x,y)=(x_s+1.5\lambda t\cos\alpha,\ y_s+\lambda t\sin\alpha)$", 0),
 (r"$\mathrm{amplitude}\ \propto(1-t)^{2.6};\ \mathrm{kept\ only\ where\ the\ ray\ falls\ on\ a\ window.}$", 0),
 ("", 0),
 (r"$\mathbf{Moon\ and\ the\ neighbouring\ cylinder}$", 1),
 (r"$\mathrm{Latitude\ and\ longitude\ families\ on\ a\ sphere,\ near\ side\ only;}$", 0),
 (r"$\mathrm{shading}=(\max(0,-0.5X+0.6Z))^{0.8}.\ \mathrm{The\ neighbour\ is\ the}$", 0),
 (r"$\mathrm{same\ family\ banded\ by}\ \frac{1}{2}+\frac{1}{2}\sin(14\varphi+1.3\sin(10\pi t)).$", 0),
 ("", 0),
 (r"$\mathbf{Stars}\quad k=1,\ldots,6000$", 1),
 (r"$(x,y)=(x_{\min}+(x_{\max}-x_{\min})h(k,1),\ y_{\min}+(y_{\max}-y_{\min})h(k,2))$", 0),
 (r"$\mathrm{A\ star\ is\ drawn\ only\ if\ the\ ray\ through}\ (x,y)\ \mathrm{meets\ a\ window}$", 0),
 (r"$\mathrm{sector;\ its\ magnitude\ is}\ h(k,3)^{7}.$", 0),
],
]

from matplotlib import mathtext
_parser = mathtext.MathTextParser("agg")
_bad = []
for _blk in [[(TITLE, 1), (SUB, 0)]] + COLS:
    for _txt, _ in _blk:
        if not _txt:
            continue
        try:
            _parser.parse(_txt, 100, None)
        except Exception as e:
            _bad.append((_txt[:70], str(e).strip().splitlines()[-1][:90]))
if _bad:
    for b in _bad:
        print("BAD:", b[0], "||", b[1])
    raise SystemExit(1)

fig = plt.figure(figsize=FIG, dpi=DPI, facecolor="white")
fig.text(0.030, 0.958, TITLE, fontsize=11.5, va="top", ha="left", color="black")
fig.text(0.030, 0.925, SUB, fontsize=5.6, va="top", ha="left", color="black")

x0s = [0.030, 0.355, 0.680]
for ci, col in enumerate(COLS):
    y = 0.882
    for txt, head in col:
        if txt:
            fig.text(x0s[ci], y, txt, fontsize=6.0 if head else 5.5,
                     va="top", ha="left", color="black")
        y -= 0.0272 if txt else 0.0121
fig.text(0.030, 0.014,
         r"$\mathrm{Composed\ after\ the\ method\ of\ Hamid\ Naderi\ Yeganeh;\ the\ subject\ follows\ Rick\ Guidice's\ 1970s\ NASA\ painting\ of\ an\ O'Neill\ Island\ Three\ colony.}$",
         fontsize=5.0, va="bottom", ha="left", color="0.25")
fig.savefig("sheet.png", dpi=DPI, facecolor="white")
print("wrote sheet.png")
