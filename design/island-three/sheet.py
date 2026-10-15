"""Typeset the formula sheet that accompanies the picture."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

W_PX, DPI = 2048, 200
LINE, GAP = 27.0, 13.0          # px between rows, and between blocks
TOP, BOTTOM = 112.0, 62.0        # px for the heading and for the credit

TITLE = r"$\mathrm{Island\ Three\ (O'Neill\ cylinder)}$"
SUB = (r"$\mathrm{Every\ mark\ is\ a\ sample\ of\ one\ of\ the\ families\ below,\ drawn\ for}$"
       r"$\ k=1,2,\ldots,n\ \mathrm{and}\ t\in[0,1];$"
       r"$\ \mathrm{the\ colour\ and\ the\ weight\ of\ each\ sample\ are\ formulas\ in}\ (k,t)\ \mathrm{too.}$"
       r"$\ \mathrm{Nothing\ is\ brushed\ or\ filled:\ the\ only\ mark\ not\ made\ by\ a\ curve\ is\ the\ flat\ sky.}$")

COLS = [
[
 (r"$\mathbf{View\ from\ inside\ the\ tube}$", 1),
 (r"$\mathrm{The\ habitat\ is}\ x^2+y^2=1,\ \mathrm{axis}\ z.\ \mathrm{The\ eye\ sits\ at}$", 0),
 (r"$E=(0,-e,0),\ e=0.62,\ \mathrm{pitched\ down\ by}\ B=0.22.$", 0),
 (r"$\mathrm{A\ point\ at\ angle}\ T,\ \mathrm{axial\ distance}\ Z,\ \mathrm{radius}\ R:$", 0),
 (r"$w=(R\cos T-e)\sin B+Z\cos B$", 0),
 (r"$P(T,Z,R)=\left(\frac{R\sin T}{w},\ \frac{(e-R\cos T)\cos B+Z\sin B}{w}-\tan B\right)$", 0),
 (r"$\mathrm{with\ the\ vanishing\ point\ put\ back\ at}\ y=\tan B.$", 0),
 ("", 0),
 (r"$\mathbf{Fitting\ the\ plate}$", 1),
 (r"$\mathrm{A\ line\ of\ constant}\ T\ \mathrm{leaves\ the\ vanishing\ point\ at}$", 0),
 (r"$\theta(T)=\mathrm{atan2}\!\left(\frac{e-\cos T}{\cos B},\ \sin T\right).$", 0),
 (r"$\mathrm{The\ six\ sector\ edges\ measured\ off\ Guidice's\ painting\ are}$", 0),
 (r"$\theta=-16^\circ,\,25.5^\circ,\,67.5^\circ,\,112.5^\circ,\,154.5^\circ,\,196^\circ,$", 0),
 (r"$\mathrm{and\ fix}\ e=0.62,\ W_L=1.257\ \mathrm{to\ within\ five\ degrees.}$", 0),
 ("", 0),
 (r"$\mathbf{Six\ sectors}$", 1),
 (r"$\mathrm{Valleys\ of\ width}\ W_L\ \mathrm{centred\ at}\ T=0,\frac{2\pi}{3},\frac{4\pi}{3};$", 0),
 (r"$\mathrm{windows\ fill\ the\ rest.\ A\ ray\ sees\ space\ when}$", 0),
 (r"$\mathrm{mod}(T+\frac{W_L}{2},\,\frac{2\pi}{3})>W_L.$", 0),
 (r"$\mathrm{Axial\ parameter}\ \ Z(t)=\left(\frac{1}{Z_0}+(\frac{1}{Z_c}-\frac{1}{Z_0})t\right)^{-1},$", 0),
 (r"$Z_0=0.255,\ Z_c=9:\ \mathrm{linear\ in}\ 1/Z,\ \mathrm{so\ the\ samples\ stay}$", 0),
 (r"$\mathrm{evenly\ spaced\ on\ the\ screen\ all\ the\ way\ to\ the\ hub.}$", 0),
 ("", 0),
 (r"$\mathbf{Light\ from\ the\ window\ strips}$", 1),
 (r"$\mathrm{A\ strip\ at\ angle}\ F\ \mathrm{meets\ the\ wall\ at}\ T\ \mathrm{with\ cosine}$", 0),
 (r"$\mathrm{factor}\ \left|\sin\frac{T-F}{2}\right|,\ \mathrm{so\ the\ irradiance\ is}$", 0),
 (r"$L(T)=0.30+\left|\sin\frac{T-\pi}{2}\right|+0.34\left|\sin\frac{T-\pi/3}{2}\right|$", 0),
 (r"$\qquad\qquad\quad +\ 0.34\left|\sin\frac{T-5\pi/3}{2}\right|$", 0),
 ("", 0),
 (r"$\mathbf{Aerial\ perspective}$", 1),
 (r"$f=\mathrm{clip}\!\left(\frac{Z-0.45}{4},0,1\right)^{0.8},\quad c\mapsto(1-0.52f)c+0.52f\,a,$", 0),
 (r"$a=(0.255,\,0.205,\,0.048):\ \mathrm{the\ far\ wall\ of\ the\ tube\ is\ dark}$", 0),
 (r"$\mathrm{and\ olive,\ not\ pale\ —\ read\ straight\ off\ the\ painting.}$", 0),
 ("", 0),
 (r"$\mathbf{Deterministic\ hash}$", 1),
 (r"$h(k,\sigma)=\mathrm{frac}(43758.5453\,\sin(12.9898k+78.233\sigma))$", 0),
],
[
 (r"$\mathbf{How\ much\ ink\ a\ sample\ carries}$", 1),
 (r"$\mathrm{For\ a\ family}\ P(k,t)\ \mathrm{that\ sweeps\ a\ surface,\ one\ sample\ owns}$", 0),
 (r"$\mathcal{A}=\left|\frac{\partial P}{\partial k}\times\frac{\partial P}{\partial t}\right|\ \mathrm{square\ pixels,}$", 0),
 (r"$\mathrm{so\ depositing}\ c\cdot\mathcal{A}\ \mathrm{lays\ down\ exactly\ the\ colour}\ c,$", 0),
 (r"$\mathrm{however\ the\ family\ is\ sampled.\ Get\ this\ backwards\ and\ a}$", 0),
 (r"$\mathrm{converging\ family\ piles\ into\ a\ white\ ball\ at\ the\ hub.}$", 0),
 ("", 0),
 (r"$\mathbf{The\ three\ valleys}\quad j=0,1,2;\ \ k=1,\ldots,2400$", 1),
 (r"$s=\frac{k+\frac{1}{2}}{2400},\qquad Z=Z(t),\qquad \epsilon=|\sin\pi s|^{0.35}$", 0),
 (r"$H(s,Z)=\sum_i a_i\sin(p_i s+q_i Z+r_i),$", 0),
 (r"$(a,p,q,r)=(1,4.3,1.7,0.6),(0.7,2.1,-2.9,2.2),$", 0),
 (r"$\qquad\quad (0.45,7.7,4.3,1.1),(0.26,13,-7,0),(0.13,19,9,2.7)$", 0),
 (r"$R=1-0.0215\,\epsilon H,\qquad T=\frac{2\pi j}{3}+W_L(s-\frac{1}{2})+0.012\,\epsilon H$", 0),
 (r"$\mathrm{curve}=P(T,Z,R).\ \ \epsilon\ \mathrm{vanishes\ at}\ s=0,1,\ \mathrm{so\ the\ relief}$", 0),
 (r"$\mathrm{leaves\ the\ strip\ borders\ straight.}$", 0),
 ("", 0),
 (r"$\mathbf{Farmland}$", 1),
 (r"$\varphi=0.85\sin(1.25Z+1.9s+2.1j)+0.5j+0.45\sin(4.3Z-2.7s+1.1j)$", 0),
 (r"$u=\frac{s}{0.030}+3.4\sin(0.9Z+1.3j)+1.2\sin(2.7Z+0.4j)$", 0),
 (r"$v=\frac{Z^{0.40}}{0.0120}+2.6\sin(3.3s+0.7j)+1.3\sin(7.1s+2j)$", 0),
 (r"$\mathrm{Grid}_m:\ \alpha=u\cos\varphi_m+v\sin\varphi_m,\ \beta=v\cos\varphi_m-u\sin\varphi_m,$", 0),
 (r"$q_m=h(\lambda_m\lfloor\alpha\rfloor+3,\ \mu_m\lfloor\beta\rfloor+7),$", 0),
 (r"$e_m=\min(\{\alpha\},1-\{\alpha\},\{\beta\},1-\{\beta\})$", 0),
 (r"$\mathrm{Grid}_2\ \mathrm{uses}\ (1.63u,1.41v)\ \mathrm{and}\ \varphi+1.12+0.3j.$", 0),
 (r"$q=\mathrm{frac}(q_1+q_2),\qquad \mathrm{seam}=\min(e_1,\,0.70\,e_2)$", 0),
 (r"$\mathrm{Two\ grids\ crossed\ give\ irregular\ polygons;\ one\ gives\ a\ chequer.}$", 0),
 ("", 0),
 (r"$\mathbf{Ground\ colour}\qquad \mathcal{F}=e^{-(Z-Z_0)/1.30}$", 1),
 (r"$g=0.10+0.86\,b_1b_2,\quad b_1=\frac{1}{2}+\frac{1}{2}\sin(1.35Z+2.1s+1.9j),$", 0),
 (r"$b_2=\frac{1}{2}+\frac{1}{2}\sin(0.62Z-3.3s+0.7j+1.3)$", 0),
 (r"$c=c_{\mathrm{grass}}+(c_{\mathrm{pale}}-c_{\mathrm{grass}})g,\qquad \tilde q=(q-\frac{1}{2})\,\mathrm{clip}(0.22+1.05\mathcal{F})$", 0),
 (r"$c\mapsto c\,(1+0.80\tilde q)+(0.14,0.05,-0.03)\,\tilde q$", 0),
 (r"$\mathrm{stubble}:\ \pi=\mathrm{clip}(\frac{\tilde q-0.27}{0.11}),\ c\mapsto(1-0.78\pi)c+0.78\pi\,c_{\mathrm{cream}}$", 0),
 (r"$\mathrm{wood}:\ W=\prod_i\left(\frac{1}{2}+\frac{1}{2}\sin(\cdot)\right),$", 0),
 (r"$\quad \omega=\mathrm{clip}(\frac{W-0.155}{0.065})\,\mathrm{clip}(\frac{0.46-q}{0.13})+0.22\,\mathrm{clip}(\frac{W-0.33}{0.10})$", 0),
 (r"$\mathrm{hedge}=e^{-(\mathrm{seam}/0.014)^2}\mathcal{F},\quad \mathrm{lane}=e^{-(\sin(10.5\pi s+\ldots)/0.012)^2}\mathcal{F}$", 0),
 (r"$\mathrm{relief}=0.76+0.20\tanh(0.42H_Z)+0.11\tanh(0.16H_s)$", 0),
 (r"$c\mapsto c\cdot\mathrm{relief}\cdot\left(0.42+0.78\frac{L(T)}{1.6}\right),\ \mathrm{then\ hazed.}$", 0),
],
[
 (r"$\mathbf{Lake\ and\ river}\ \ \mathrm{(near\ valley\ only)}$", 1),
 (r"$\mathrm{Polar\ about}\ (s,Z)=(0.185,0.615)\ \mathrm{scaled\ by}\ (0.150,0.074):$", 0),
 (r"$\mathrm{rad}(\psi)=1+0.22\sin(\psi+0.7)+0.14\sin(2\psi-1.2)$", 0),
 (r"$\qquad\quad +\ 0.10\sin(3\psi+2.1)+0.06\sin 5\psi+0.04\sin(7\psi+1)$", 0),
 (r"$\mathrm{lake}=(\mathrm{rad}(\psi)-r)/0.25$", 0),
 (r"$s_r(Z)=0.352+0.030\sin(2.3Z+0.4)+0.011\sin 5.1Z-0.034e^{-(Z-0.9)^2/0.22}$", 0),
 (r"$\mathrm{river}=1-\frac{|s-s_r|}{w_r},\quad w_r=0.0052+0.0105\,e^{-(Z-1)^2/0.9}$", 0),
 (r"$\mathrm{Three\ islands\ are\ small\ ellipses\ subtracted\ from\ the\ lake.}$", 0),
 ("", 0),
 (r"$\mathbf{Woods}\quad k=1,\ldots,2600;\ \ r=\frac{i+\frac{1}{2}}{7},\ i<7$", 1),
 (r"$\mathrm{clump}\ \kappa=\lfloor k/6\rfloor,\quad Z_w=0.285+3.4\,h(\kappa,51)^{1.7}+\ldots$", 0),
 (r"$\varrho=(0.0035+0.0090\,h(k,53))\,r\,(1+0.26\sin(6\pi t+9k)+0.14\sin 10\pi t)$", 0),
 (r"$\mathrm{curve}=P(T_w+\varrho\cos 2\pi t,\ Z_w(1+0.55\varrho\sin 2\pi t),\ 0.9992)$", 0),
 (r"$\mathrm{Nested\ rings}\ r\ \mathrm{fill\ each\ canopy;\ the\ Jacobian\ is\ taken}$", 0),
 (r"$\mathrm{across\ the\ rings,\ never\ between\ one\ clump\ and\ the\ next.}$", 0),
 ("", 0),
 (r"$\mathbf{Cloud\ streaks}\quad k=1,\ldots,560$", 1),
 (r"$\mathrm{Half\ lie\ on\ the\ near\ valley\ by\ the\ horizon,\ half\ on\ the\ far\ strips.}$", 0),
 (r"$Z=\left(w_0-\delta w\,t\right)^{-1},\ w_0\in[0.20,0.98],\ \delta w=0.050+0.165h(k,78)^{1.3}$", 0),
 (r"$\mathrm{Sampling}\ 1/Z\ \mathrm{evenly\ spreads\ the\ streaks\ evenly\ on\ screen;}$", 0),
 (r"$\mathrm{sampling}\ Z\ \mathrm{crowds\ them\ all\ into\ the\ hub.}$", 0),
 (r"$T=\frac{2\pi j}{3}+0.99W_L\,\mathrm{sgn}(\eta)\frac{|2\eta|^{0.42}}{2}+\mathrm{width}\cdot b$", 0),
 (r"$R=0.895+0.045h(k,74)+\ldots,\quad \eta=h(k,73)-\frac{1}{2}$", 0),
 ("", 0),
 (r"$\mathbf{Solar\ mirror\ in\ the\ top\ window}\quad k=1,\ldots,1700$", 1),
 (r"$\rho=0.050+0.800\left(\frac{k}{1700}\right)^{1.06},\quad \vartheta=\theta_0+(\theta_1-\theta_0)t$", 0),
 (r"$(x,y)=(\rho\cos\vartheta,\ \tan B+\rho\sin\vartheta),\ \ \theta_{0,1}=\theta(\pi\mp\frac{W_W}{2})$", 0),
 (r"$c(\rho)=\sum_iC_i\,e^{-((\rho-\mu_i)/\sigma_i)^2}\ \ \mathrm{(the\ stacked\ bands)}$", 0),
 (r"$\mathrm{Sun}:\ \mathrm{nested\ ellipses\ of\ radius}\ 0.150u,\ 0.128u,\ u=\frac{k}{600},$", 0),
 (r"$\mathrm{white\ while}\ u<0.28,\ \mathrm{then\ a\ ring}\ e^{-(u-0.42)^2/0.045}.$", 0),
 ("", 0),
 (r"$\mathbf{Moon,\ sister\ hull,\ end\ cap,\ stars}$", 1),
 (r"$\mathrm{Latitude\ and\ longitude\ families\ on\ a\ sphere,\ near\ side\ only,}$", 0),
 (r"$\mathrm{shaded\ by}\ (\max(0,\,0.60X+0.56Z))^{0.8}.$", 0),
 (r"$\mathrm{End\ cap}:\ P(2\pi t,\,Z_c,\,u),\ u=\frac{k}{440},\ \mathrm{with\ a\ rim\ and\ a\ hub\ core.}$", 0),
 (r"$\mathrm{Stars}:\ (x,y)=(x_{\min}+\Delta x\,h(k,1),\ y_{\min}+\Delta y\,h(k,2)),\ \mathrm{kept}$", 0),
 (r"$\mathrm{only\ where\ the\ ray\ meets\ a\ window;\ magnitude}\ h(k,3)^7.$", 0),
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

H_PX = TOP + BOTTOM + max(
    sum(LINE if txt else GAP for txt, _ in col) for col in COLS)
fig = plt.figure(figsize=(W_PX / DPI, H_PX / DPI), dpi=DPI, facecolor="white")
fig.text(0.028, 1 - 30.0 / H_PX, TITLE, fontsize=11.5, va="top", ha="left", color="black")
fig.text(0.028, 1 - 74.0 / H_PX, SUB, fontsize=5.4, va="top", ha="left", color="black")

x0s = [0.028, 0.352, 0.676]
for ci, col in enumerate(COLS):
    y = 1 - TOP / H_PX
    for txt, head in col:
        if txt:
            fig.text(x0s[ci], y, txt, fontsize=5.9 if head else 5.4,
                     va="top", ha="left", color="black")
        y -= (LINE if txt else GAP) / H_PX
fig.text(0.028, 18.0 / H_PX,
         r"$\mathrm{Composed\ after\ the\ method\ of\ Hamid\ Naderi\ Yeganeh;\ the\ subject\ follows\ Rick\ Guidice's\ 1970s\ NASA\ painting\ of\ an\ O'Neill\ Island\ Three\ colony.}$",
         fontsize=5.0, va="bottom", ha="left", color="0.25")
fig.savefig("sheet.png", dpi=DPI, facecolor="white")
print("wrote sheet.png")
