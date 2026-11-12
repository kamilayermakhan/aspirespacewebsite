"""Write params.txt + flags.u8 for the C solver (euler.c).

usage: python3 setup_case.py CASEDIR [DX]
"""
import sys, os
import numpy as np
import geometry as G

P = dict(
    DX=0.012, XMAX=11.5, RMAX=4.4,
    CFL=0.4,
    # gases: methalox exhaust (frozen, fuel-rich, M ~22 g/mol) and air (M 29); R is per unit of R_air
    GAM_E=1.2, R_E=29.0 / 22.0, GAM_A=1.4,
    TC=11.67,        # chamber temperature ~3500 K / 300 K ambient
    # two-stage start: a weak first stage, then full pressure (the footage shows a dim
    # flame first, then full flow); reservoir values give ~20 bar and ~50 bar in the chamber
    T_IGN=0.05, T_RAMP=0.6, P1=21.3,
    T_STAGE2=5.0, T_RAMP2=0.8, PC=53.2,
    T_END=21.5,
    T_ALT0=100.0, T_ALT1=101.0, PA_HIGH=0.03,   # sea level throughout
    SNAP_DT1=0.008, SNAP_DT2=0.025, SNAP_SWITCH=2.4,
    NU=0.0,
    CS=0.45,         # Smagorinsky coefficient (chosen so the plume can close behind the tip; not validated)
    # cooled walls (regenerative cooling keeps the hot-gas wall near 800 K)
    ST=0.0025,       # Stanton number for the gas-side heat transfer
    CF2=0.0025,      # half the skin-friction coefficient (Reynolds analogy)
    TW=800.0 / 300.0,
    # afterburning of the fuel-rich exhaust with entrained air
    A_AB=3.0,        # rate constant (per time unit) once the mixture is hotter than T_AB
    Q_AB=1.2e6 / (287.0 * 300.0),   # ~1.2 MJ per kg of exhaust left to burn
    T_AB=1000.0 / 300.0,
)

def main(d, dx=None):
    if dx: P["DX"] = dx
    os.makedirs(d, exist_ok=True)
    xmin = P.get("XMIN", 0.0)
    nx = int(round((P["XMAX"] - xmin) / P["DX"])); nr = int(round(P["RMAX"] / P["DX"]))
    xc = xmin + (np.arange(nx) + 0.5) * P["DX"]; rc = (np.arange(nr) + 0.5) * P["DX"]
    X, R = np.meshgrid(xc, rc, indexing="ij")
    s = G.solid(X, R)
    res = G.reservoir(X, R) & ~s
    probe = G.chamber_probe(X, R) & ~s
    sx = s.copy(); sx[1:] |= s[:-1]; sx[:-1] |= s[1:]
    sr = s.copy(); sr[:, 1:] |= s[:, :-1]; sr[:, :-1] |= s[:, 1:]
    fl = (s * 1 + res * 2 + probe * 4 + sx * 8 + sr * 16).astype(np.uint8)
    fl.tofile(os.path.join(d, "flags.u8"))
    with open(os.path.join(d, "params.txt"), "w") as f:
        # the solver works in x - XMIN
        for k, v in dict(P, NX=nx, NR=nr, XSPIKE=G.X_SPIKE_END - xmin, XLIP=G.X_LIP - xmin).items():
            f.write(f"{k} {v}\n")
    np.savez(os.path.join(d, "grid.npz"), xc=xc, rc=rc, solid=s, **dict({k: v for k, v in P.items()}, XMIN=xmin))
    print("grid", nx, nr, nx * nr)

if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else None)
