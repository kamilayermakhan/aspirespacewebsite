/* 2D axisymmetric compressible solver for an aerospike start-up (see README).
 *
 * Finite volume, MUSCL (minmod, primitive vars) + HLLC, SSP-RK2, stair-step walls.
 * Two gases: methalox exhaust (GAM_E, R_E) and air (GAM_A, R=1), mixed by the
 * exhaust mass fraction Y.  A second scalar Z tracks unburned, fuel-rich exhaust,
 * which afterburns with entrained air (heat release Q_AB, rate A_AB rho Z (1-Y)
 * above T_AB).  Smagorinsky eddy viscosity (CS) in the shear layers.
 * Cooled walls: wall-function heat loss q = ST rho |V| cp (T - TW) and skin
 * friction CF2 rho |V| V on cells next to the metal.
 * Nondimensional: ambient p = rho = T = 1 (air), lengths in L0.
 *
 * usage: euler <case dir>   (reads case/params.txt, case/flags.u8)
 * writes case/sNNNNN.f16 snapshots (rho,p,Y,u,v,Z as float16) and case/log.txt
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define NV 6
static int NX, NR;
static double DX, CFL, T_END, T_IGN, T_RAMP, P1 = 0, T_STAGE2 = 1e9, T_RAMP2 = 1, PC, TC;
static double T_ALT0 = 1e9, T_ALT1 = 2e9, PA_HIGH = 1, XSPIKE, XLIP, SNAP_DT1, SNAP_DT2, SNAP_SWITCH;
static double NU = 0, CS = 0, GAM_E = 1.2, R_E = 1.318, GAM_A = 1.4;
static double ST = 0, CF2 = 0, TW = 2.67, A_AB = 0, Q_AB = 0, T_AB = 3.3;
static unsigned char *FL;  /* bit0 solid, bit1 reservoir, bit2 probe, bit3 flat_x, bit4 flat_r */
static unsigned char *NWALL;
static double *rc, *rf, *NUT;
#define EPS 1e-6
#define ID(i, j) ((size_t)(i) * NR + (j))
#define SOLID(c) (FL[c] & 1)

static inline void gas(double y, double *gam, double *R, double *cv) {
    double cve = R_E / (GAM_E - 1), cva = 1.0 / (GAM_A - 1);
    *cv = y * cve + (1 - y) * cva;
    *R = y * R_E + (1 - y);
    *gam = 1 + *R / *cv;
}
static double smooth(double s) { if (s < 0) s = 0; if (s > 1) s = 1; return s * s * (3 - 2 * s); }
static void chamber_target(double t, double *p0, double *T0) {
    double pst1 = P1 > 0 ? P1 : PC;
    *p0 = 1 + (pst1 - 1) * smooth((t - T_IGN) / T_RAMP) + (PC - pst1) * smooth((t - T_STAGE2) / T_RAMP2);
    *T0 = 1 + (TC - 1) * smooth((t - T_IGN) / 0.25);
}
static double p_amb(double t) { return 1 + (PA_HIGH - 1) * smooth((t - T_ALT0) / (T_ALT1 - T_ALT0)); }
static inline double minmod(double a, double b) { if (a * b <= 0) return 0; return fabs(a) < fabs(b) ? a : b; }

/* HLLC: W = rho, un, ut, p, y, z ; F = mass, n-mom, t-mom, E, rho y, rho z */
static inline void hllc(const double *L, const double *R, double *F) {
    double gL, gR, RL, RR, cvL, cvR;
    gas(L[4], &gL, &RL, &cvL); gas(R[4], &gR, &RR, &cvR);
    double rL = L[0], uL = L[1], vL = L[2], pL = L[3];
    double rR = R[0], uR = R[1], vR = R[2], pR = R[3];
    double cL = sqrt(gL * pL / rL), cR = sqrt(gR * pR / rR);
    double EL = pL / (gL - 1) + 0.5 * rL * (uL * uL + vL * vL);
    double ER = pR / (gR - 1) + 0.5 * rR * (uR * uR + vR * vR);
    double SL = fmin(uL - cL, uR - cR), SR = fmax(uL + cL, uR + cR);
    double dL = rL * (SL - uL), dR = rR * (SR - uR);
    double Ss = (pR - pL + uL * dL - uR * dR) / (dL - dR);
    const double *K; double rK, uK, vK, pK, EK, SK, dK;
    if (SL >= 0 || (Ss >= 0 && SR > 0)) { K = L; rK = rL; uK = uL; vK = vL; pK = pL; EK = EL; SK = SL; dK = dL; }
    else { K = R; rK = rR; uK = uR; vK = vR; pK = pR; EK = ER; SK = SR; dK = dR; }
    double Fk[NV] = {rK * uK, rK * uK * uK + pK, rK * uK * vK, (EK + pK) * uK, rK * uK * K[4], rK * uK * K[5]};
    if (SL >= 0 || SR <= 0) { for (int k = 0; k < NV; k++) F[k] = Fk[k]; return; }
    double f = dK / (SK - Ss);
    double Us[NV] = {f, f * Ss, f * vK, f * (EK / rK + (Ss - uK) * (Ss + pK / dK)), f * K[4], f * K[5]};
    double U[NV] = {rK, rK * uK, rK * vK, EK, rK * K[4], rK * K[5]};
    for (int k = 0; k < NV; k++) F[k] = Fk[k] + SK * (Us[k] - U[k]);
}

static double *W[NV], *SX[NV], *SRr[NV], *FX[NV], *FR[NV];

/* eddy-viscosity flux across a face (normal gradients only), added to F (x-ordering) */
static inline void visc_flux(size_t a, size_t b, double h, double *F) {
    double nu = NU + (CS > 0 ? 0.5 * (NUT[a] + NUT[b]) : 0.0);
    if (nu <= 0) return;
    double ga, Ra, cva, gb, Rb, cvb;
    gas(W[4][a], &ga, &Ra, &cva); gas(W[4][b], &gb, &Rb, &cvb);
    double rho = 0.5 * (W[0][a] + W[0][b]);
    double mu = rho * nu, cp = 0.5 * (cva + Ra + cvb + Rb);
    double du = (W[1][b] - W[1][a]) / h, dv = (W[2][b] - W[2][a]) / h;
    double Ta = W[3][a] / (W[0][a] * Ra), Tb = W[3][b] / (W[0][b] * Rb);
    double dT = (Tb - Ta) / h, dY = (W[4][b] - W[4][a]) / h, dZ = (W[5][b] - W[5][a]) / h;
    double uf = 0.5 * (W[1][a] + W[1][b]), vf = 0.5 * (W[2][a] + W[2][b]);
    F[1] -= mu * du; F[2] -= mu * dv;
    F[3] -= mu * (uf * du + vf * dv) + mu * cp * dT;
    F[4] -= mu * dY; F[5] -= mu * dZ;
}

static void cons2prim(double *const *U) {
    #pragma omp parallel for
    for (size_t c = 0; c < (size_t)NX * NR; c++) {
        double r = U[0][c]; if (r < EPS) r = EPS;
        double u = U[1][c] / r, v = U[2][c] / r;
        double y = U[4][c] / r; if (y < 0) y = 0; if (y > 1) y = 1;
        double z = U[5][c] / r; if (z < 0) z = 0; if (z > y) z = y;
        double g, R, cv; gas(y, &g, &R, &cv);
        double p = (g - 1) * (U[3][c] - 0.5 * r * (u * u + v * v));
        if (p < EPS) p = EPS;
        W[0][c] = r; W[1][c] = u; W[2][c] = v; W[3][c] = p; W[4][c] = y; W[5][c] = z;
    }
}
static void prim2cons_fix(double **U) {
    cons2prim(U);
    #pragma omp parallel for
    for (size_t c = 0; c < (size_t)NX * NR; c++) {
        double r = W[0][c], u = W[1][c], v = W[2][c], p = W[3][c], y = W[4][c], z = W[5][c];
        double g, R, cv; gas(y, &g, &R, &cv);
        U[0][c] = r; U[1][c] = r * u; U[2][c] = r * v;
        U[3][c] = p / (g - 1) + 0.5 * r * (u * u + v * v); U[4][c] = r * y; U[5][c] = r * z;
    }
}
static void force_reservoir(double **U, double t) {
    double p0, T0; chamber_target(t, &p0, &T0);
    double r = p0 / (R_E * T0);
    for (size_t c = 0; c < (size_t)NX * NR; c++) if (FL[c] & 2) {
        U[0][c] = r; U[1][c] = 0; U[2][c] = 0; U[3][c] = p0 / (GAM_E - 1); U[4][c] = r; U[5][c] = r;
    }
}
static inline void getW(int i, int j, double pa, double *w) {
    if (i < 0 || j >= NR) { w[0] = pa; w[1] = 0; w[2] = 0; w[3] = pa; w[4] = 0; w[5] = 0; return; }
    if (i >= NX) i = NX - 1;
    int mirror = 0;
    if (j < 0) { j = 0; mirror = 1; }
    size_t c = ID(i, j);
    for (int k = 0; k < NV; k++) w[k] = W[k][c];
    if (mirror) w[2] = -w[2];
}

static double rhs(double **U, double t, double **dU, int want_dt) {
    cons2prim(U);
    double pa = p_amb(t);
    #pragma omp parallel for
    for (int i = 0; i < NX; i++) for (int j = 0; j < NR; j++) {
        size_t c = ID(i, j);
        double a[NV], b[NV];
        int fx = (FL[c] & 8) || i == 0 || i == NX - 1;
        int fr = (FL[c] & 16) || j == NR - 1;
        getW(i - 1, j, pa, a); getW(i + 1, j, pa, b);
        for (int k = 0; k < NV; k++) SX[k][c] = fx ? 0 : minmod(W[k][c] - a[k], b[k] - W[k][c]);
        getW(i, j - 1, pa, a); getW(i, j + 1, pa, b);
        for (int k = 0; k < NV; k++) SRr[k][c] = fr ? 0 : minmod(W[k][c] - a[k], b[k] - W[k][c]);
    }
    if (CS > 0) {
        double l2 = (CS * DX) * (CS * DX), cap = 3.0 * DX;
        #pragma omp parallel for
        for (int i = 0; i < NX; i++) for (int j = 0; j < NR; j++) {
            size_t c = ID(i, j);
            if (SOLID(c) || i == 0 || i == NX - 1 || j == NR - 1) { NUT[c] = 0; continue; }
            size_t e = ID(i + 1, j), w = ID(i - 1, j), n = ID(i, j + 1), s_ = j > 0 ? ID(i, j - 1) : c;
            if (SOLID(e)) e = c;
            if (SOLID(w)) w = c;
            if (SOLID(n)) n = c;
            if (SOLID(s_)) s_ = c;
            double dxw = (e != c && w != c) ? 2 * DX : DX, dyw = (n != c && s_ != c) ? 2 * DX : DX;
            double ux = (W[1][e] - W[1][w]) / dxw, vx = (W[2][e] - W[2][w]) / dxw;
            double ur = (W[1][n] - W[1][s_]) / dyw, vr = (W[2][n] - W[2][s_]) / dyw;
            double vor = W[2][c] / rc[j];
            double S2 = 2 * (ux * ux + vr * vr + vor * vor) + (ur + vx) * (ur + vx);
            double nt = l2 * sqrt(S2);
            NUT[c] = nt < cap ? nt : cap;
        }
    }
    #pragma omp parallel for
    for (int i = 0; i <= NX; i++) for (int j = 0; j < NR; j++) {
        double L[NV], R[NV], F[NV];
        int sL = (i - 1 >= 0) && SOLID(ID(i - 1, j));
        int sR = (i < NX) && SOLID(ID(i, j));
        size_t f = (size_t)i * NR + j;
        if (sL && sR) { for (int k = 0; k < NV; k++) FX[k][f] = 0; continue; }
        getW(i - 1, j, pa, L); getW(i, j, pa, R);
        if (i - 1 >= 0) { size_t c = ID(i - 1, j); for (int k = 0; k < NV; k++) L[k] += 0.5 * SX[k][c]; }
        if (i < NX)     { size_t c = ID(i, j);     for (int k = 0; k < NV; k++) R[k] -= 0.5 * SX[k][c]; }
        if (L[0] <= EPS || L[3] <= EPS || R[0] <= EPS || R[3] <= EPS) { getW(i - 1, j, pa, L); getW(i, j, pa, R); }
        if (sR) { memcpy(R, L, sizeof L); R[1] = -L[1]; }
        if (sL) { memcpy(L, R, sizeof R); L[1] = -R[1]; }
        hllc(L, R, F);
        if ((NU > 0 || CS > 0) && !sL && !sR && i > 0 && i < NX) visc_flux(ID(i - 1, j), ID(i, j), DX, F);
        for (int k = 0; k < NV; k++) FX[k][f] = F[k];
    }
    #pragma omp parallel for
    for (int i = 0; i < NX; i++) for (int j = 0; j <= NR; j++) {
        double L[NV], R[NV], F[NV], l[NV], r[NV];
        size_t f = (size_t)i * (NR + 1) + j;
        int sL = (j - 1 >= 0) && SOLID(ID(i, j - 1));
        int sR = (j < NR) && SOLID(ID(i, j));
        if ((sL && sR) || j == 0) { for (int k = 0; k < NV; k++) FR[k][f] = 0; continue; }
        getW(i, j - 1, pa, L); getW(i, j, pa, R);
        if (j - 1 >= 0) { size_t c = ID(i, j - 1); for (int k = 0; k < NV; k++) L[k] += 0.5 * SRr[k][c]; }
        if (j < NR)     { size_t c = ID(i, j);     for (int k = 0; k < NV; k++) R[k] -= 0.5 * SRr[k][c]; }
        if (L[0] <= EPS || L[3] <= EPS || R[0] <= EPS || R[3] <= EPS) { getW(i, j - 1, pa, L); getW(i, j, pa, R); }
        if (sR) { memcpy(R, L, sizeof L); R[2] = -L[2]; }
        if (sL) { memcpy(L, R, sizeof R); L[2] = -R[2]; }
        for (int k = 0; k < NV; k++) { l[k] = L[k]; r[k] = R[k]; }
        l[1] = L[2]; l[2] = L[1]; r[1] = R[2]; r[2] = R[1];
        hllc(l, r, F);
        { double t1 = F[1]; F[1] = F[2]; F[2] = t1; }
        if ((NU > 0 || CS > 0) && !sL && !sR && j > 0 && j < NR) visc_flux(ID(i, j - 1), ID(i, j), DX, F);
        double rr = rf[j];
        for (int k = 0; k < NV; k++) FR[k][f] = F[k] * rr;
    }
    double smax = 1e-12;
    #pragma omp parallel for reduction(max:smax)
    for (int i = 0; i < NX; i++) for (int j = 0; j < NR; j++) {
        size_t c = ID(i, j);
        if (SOLID(c)) { for (int k = 0; k < NV; k++) dU[k][c] = 0; continue; }
        size_t fx0 = (size_t)i * NR + j, fx1 = (size_t)(i + 1) * NR + j;
        size_t fr0 = (size_t)i * (NR + 1) + j, fr1 = fr0 + 1;
        for (int k = 0; k < NV; k++)
            dU[k][c] = -(FX[k][fx1] - FX[k][fx0]) / DX - (FR[k][fr1] - FR[k][fr0]) / (rc[j] * DX);
        double rho = W[0][c], u = W[1][c], v = W[2][c], p = W[3][c], y = W[4][c], z = W[5][c];
        dU[2][c] += p / rc[j];
        double nuc = NU + (CS > 0 ? NUT[c] : 0);
        if (nuc > 0) dU[2][c] -= rho * nuc * v / (rc[j] * rc[j]);
        double g, R, cv; gas(y, &g, &R, &cv);
        double T = p / (rho * R);
        /* afterburning of fuel-rich exhaust with entrained air */
        if (A_AB > 0 && z > 1e-4 && T > T_AB && !(FL[c] & 2)) {
            double w = A_AB * rho * z * (1 - y);
            dU[5][c] -= w; dU[3][c] += w * Q_AB;
        }
        /* cooled walls: heat loss and skin friction (wall function) */
        if (NWALL[c] && !(FL[c] & 2)) {
            double V = hypot(u, v), nw = NWALL[c];
            double q = ST * rho * V * (cv + R) * (T - TW);
            dU[3][c] -= q * nw / DX;
            dU[1][c] -= CF2 * rho * V * u * nw / DX;
            dU[2][c] -= CF2 * rho * V * v * nw / DX;
        }
        if (want_dt) {
            double cs = sqrt(g * p / rho);
            double s = (fabs(u) + cs) / DX + (fabs(v) + cs) / DX + CFL * 4 * nuc * g / (DX * DX);
            if (s > smax) smax = s;
        }
    }
    return CFL / smax;
}

static void diagnostics(double t, FILE *lg, int k) {
    double pa = p_amb(t), F = 0, Tsum = 0, psum = 0, qsp = 0, qch = 0, Qtot = 0; int n = 0;
    int ip = (int)((XSPIKE + 0.05) / DX);
    for (int j = 0; j < NR; j++) {          /* thrust: exhaust momentum + pressure flux behind the spike */
        size_t c = ID(ip, j);
        if (SOLID(c) || W[4][c] < 0.02) continue;
        F += (W[0][c] * W[1][c] * W[1][c] + W[3][c] - pa) * 2 * M_PI * rc[j] * DX;
    }
    for (int i = 0; i < NX; i++) for (int j = 0; j < NR; j++) {
        size_t c = ID(i, j);
        if (SOLID(c)) continue;
        double g, R, cv; gas(W[4][c], &g, &R, &cv);
        double T = W[3][c] / (W[0][c] * R);
        if (FL[c] & 4) { Tsum += T; psum += W[3][c]; n++; }
        if (NWALL[c] && !(FL[c] & 2)) {
            double q = ST * W[0][c] * hypot(W[1][c], W[2][c]) * (cv + R) * (T - TW);
            double x = (i + 0.5) * DX;
            if (x > XLIP - 0.25) { if (q > qsp) qsp = q; } else { if (q > qch) qch = q; }
            Qtot += q * NWALL[c] * 2 * M_PI * rc[j] * DX;
        }
    }
    /* Mach at the spike truncation plane, mass-flux weighted over the exhaust */
    double sw = 0, sm = 0;
    for (int j = 0; j < NR; j++) {
        size_t c = ID(ip, j);
        if (SOLID(c)) continue;
        double g, R, cv; gas(W[4][c], &g, &R, &cv);
        double M = hypot(W[1][c], W[2][c]) / sqrt(g * W[3][c] / W[0][c]);
        double w = fabs(W[0][c] * W[1][c]) * W[4][c] * rc[j];
        sw += w; sm += M * w;
    }
    double p0, T0; chamber_target(t, &p0, &T0);
    fprintf(lg, "%d %.6f %.5f %.5f %.5f %.5f %.5f %.5f %.5f %.5f %.5f\n", k, t, F, Tsum / n, psum / n,
            sw > 1e-12 ? sm / sw : 0, qsp, pa, p0, qch, Qtot);
    fflush(lg);
}

static void read_params(const char *dir) {
    char fn[1024]; snprintf(fn, sizeof fn, "%s/params.txt", dir);
    FILE *f = fopen(fn, "r"); if (!f) { perror(fn); exit(1); }
    char key[64]; double val; int NXd = 0, NRd = 0;
    double dummy;
    while (fscanf(f, "%63s %lf", key, &val) == 2) {
#define P(name, var) if (!strcmp(key, name)) var = val;
        P("NX", NXd) P("NR", NRd) P("DX", DX) P("CFL", CFL) P("T_END", T_END) P("T_IGN", T_IGN)
        P("T_RAMP", T_RAMP) P("P1", P1) P("T_STAGE2", T_STAGE2) P("T_RAMP2", T_RAMP2) P("PC", PC) P("TC", TC)
        P("T_ALT0", T_ALT0) P("T_ALT1", T_ALT1) P("PA_HIGH", PA_HIGH) P("XSPIKE", XSPIKE) P("XLIP", XLIP)
        P("SNAP_DT1", SNAP_DT1) P("SNAP_DT2", SNAP_DT2) P("SNAP_SWITCH", SNAP_SWITCH)
        P("NU", NU) P("CS", CS) P("GAM_E", GAM_E) P("R_E", R_E) P("GAM_A", GAM_A)
        P("ST", ST) P("CF2", CF2) P("TW", TW) P("A_AB", A_AB) P("Q_AB", Q_AB) P("T_AB", T_AB)
        P("GAM", dummy)
    }
    NX = NXd; NR = NRd;
    fclose(f);
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: euler dir\n"); return 1; }
    const char *dir = argv[1];
    read_params(dir);
    size_t N = (size_t)NX * NR;
    FL = malloc(N); NWALL = calloc(N, 1);
    char fn[1024]; snprintf(fn, sizeof fn, "%s/flags.u8", dir);
    FILE *f = fopen(fn, "rb"); if (!f || fread(FL, 1, N, f) != N) { fprintf(stderr, "flags\n"); return 1; }
    fclose(f);
    for (int i = 0; i < NX; i++) for (int j = 0; j < NR; j++) {
        size_t c = ID(i, j);
        if (SOLID(c)) continue;
        int nw = 0;
        if (i > 0 && SOLID(ID(i - 1, j))) nw++;
        if (i < NX - 1 && SOLID(ID(i + 1, j))) nw++;
        if (j > 0 && SOLID(ID(i, j - 1))) nw++;
        if (j < NR - 1 && SOLID(ID(i, j + 1))) nw++;
        NWALL[c] = nw;
    }
    rc = malloc(NR * sizeof(double)); rf = malloc((NR + 1) * sizeof(double)); NUT = calloc(N, sizeof(double));
    for (int j = 0; j < NR; j++) rc[j] = (j + 0.5) * DX;
    for (int j = 0; j <= NR; j++) rf[j] = j * DX;
    double *U[NV], *U1[NV], *K[NV];
    for (int k = 0; k < NV; k++) {
        U[k] = calloc(N, 8); U1[k] = calloc(N, 8); K[k] = calloc(N, 8);
        W[k] = calloc(N, 8); SX[k] = calloc(N, 8); SRr[k] = calloc(N, 8);
        FX[k] = calloc((size_t)(NX + 1) * NR, 8); FR[k] = calloc((size_t)NX * (NR + 1), 8);
    }
    for (size_t c = 0; c < N; c++) { U[0][c] = 1; U[3][c] = 1 / (GAM_A - 1); }
    snprintf(fn, sizeof fn, "%s/log.txt", dir);
    FILE *lg = fopen(fn, "w");
    _Float16 *buf = malloc(N * sizeof(_Float16));
    double t = 0, next = 0; int k = 0; long steps = 0;
    double wall0 = omp_get_wtime();
    while (t <= T_END) {
        if (t >= next) {
            cons2prim(U);
            diagnostics(t, lg, k);
            snprintf(fn, sizeof fn, "%s/s%05d.f16", dir, k);
            FILE *o = fopen(fn, "wb");
            int order[NV] = {0, 3, 4, 1, 2, 5};
            for (int q = 0; q < NV; q++) { for (size_t c = 0; c < N; c++) buf[c] = (_Float16)W[order[q]][c]; fwrite(buf, 2, N, o); }
            fclose(o);
            if (k % 25 == 0) { printf("t=%.4f steps=%ld snaps=%d wall=%.0fs\n", t, steps, k, omp_get_wtime() - wall0); fflush(stdout); }
            k++;
            next += (t < SNAP_SWITCH) ? SNAP_DT1 : SNAP_DT2;
        }
        force_reservoir(U, t);
        double dt = rhs(U, t, K, 1);
        if (next - t < dt && next > t) dt = next - t + 1e-12;
        #pragma omp parallel for
        for (size_t c = 0; c < N; c++) for (int q = 0; q < NV; q++) U1[q][c] = U[q][c] + dt * K[q][c];
        prim2cons_fix(U1);
        force_reservoir(U1, t + dt);
        rhs(U1, t + dt, K, 0);
        #pragma omp parallel for
        for (size_t c = 0; c < N; c++) if (!SOLID(c)) for (int q = 0; q < NV; q++) U[q][c] = 0.5 * U[q][c] + 0.5 * (U1[q][c] + dt * K[q][c]);
        prim2cons_fix(U);
        t += dt; steps++;
        force_reservoir(U, t);
    }
    printf("done steps=%ld wall=%.0fs\n", steps, omp_get_wtime() - wall0);
    return 0;
}
