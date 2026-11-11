"""Write params.txt + flags.u8 for the C solver (euler.c).

usage: python3 setup_case.py CASEDIR [DX]
"""
import sys, os
import numpy as np
import geometry as G

P = dict(
    DX=0.0125, XMAX=16.5, RMAX=5.4,
    GAM=1.2,
    PC=53.2,         # reservoir; gives ~50 bar in the chamber
    TC=11.7,         # ~3500 K chamber / 300 K ambient
    CFL=0.4,
    T_END=8.6,
    T_IGN=0.05, T_RAMP=1.10,          # ignition and pressure ramp
    T_ALT0=5.6, T_ALT1=7.8, PA_HIGH=0.03,   # ambient pressure drop: climb-out
    SNAP_DT1=0.008, SNAP_DT2=0.016, SNAP_SWITCH=2.4, NU=0.0,
)

def main(d, dx=None):
    if dx: P["DX"] = dx
    os.makedirs(d, exist_ok=True)
    nx = int(round(P["XMAX"] / P["DX"])); nr = int(round(P["RMAX"] / P["DX"]))
    xc = (np.arange(nx) + 0.5) * P["DX"]; rc = (np.arange(nr) + 0.5) * P["DX"]
    X, R = np.meshgrid(xc, rc, indexing="ij")
    s = G.solid(X, R)
    res = G.reservoir(X, R) & ~s
    probe = G.chamber_probe(X, R) & ~s
    sx = s.copy(); sx[1:] |= s[:-1]; sx[:-1] |= s[1:]
    sr = s.copy(); sr[:, 1:] |= s[:, :-1]; sr[:, :-1] |= s[:, 1:]
    fl = (s * 1 + res * 2 + probe * 4 + sx * 8 + sr * 16).astype(np.uint8)
    fl.tofile(os.path.join(d, "flags.u8"))
    with open(os.path.join(d, "params.txt"), "w") as f:
        for k, v in dict(P, NX=nx, NR=nr, XSPIKE=G.X_SPIKE_END, XLIP=G.X_LIP).items():
            f.write(f"{k} {v}\n")
    np.savez(os.path.join(d, "grid.npz"), xc=xc, rc=rc, solid=s, **{k: v for k, v in P.items()})
    print("grid", nx, nr, nx * nr)

if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else None)
