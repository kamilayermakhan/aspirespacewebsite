/* 2D axisymmetric Euler solver for an aerospike start-up (see sim_c.py).
 *
 * Finite volume, MUSCL (minmod, primitive vars) + HLLC, SSP-RK2,
 * stair-step slip walls, one perfect gas (gamma) + passive scalar Y.
 * Nondimensional: ambient p = rho = T = 1.
 *
 * usage: euler <case dir>   (reads case/params.txt, case/flags.u8)
 * writes case/sNNNNN.f32 snapshots (rho,p,Y,u,v) and case/log.txt
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

static int NX, NR;
static double DX, GAM, PC, TC, CFL, T_END, T_IGN, T_RAMP, T_ALT0, T_ALT1, PA_HIGH;
static double XSPIKE, XLIP, SNAP_DT1, SNAP_DT2, SNAP_SWITCH, NU = 0, CS = 0;
static double *NUT;   /* Smagorinsky eddy viscosity per cell */
static unsigned char *FL;  /* bit0 solid, bit1 reservoir, bit2 probe, bit3 flat_x, bit4 flat_r */
static double *rc, *rf;
#define EPS 1e-6
#define ID(i, j) ((size_t)(i) * NR + (j))
#define SOLID(c) (FL[c] & 1)

static double smooth(double s) { if (s < 0) s = 0; if (s > 1) s = 1; return s * s * (3 - 2 * s); }
static void chamber_target(double t, double *p0, double *T0) {
    double s = smooth((t - T_IGN) / T_RAMP);
    *p0 = 1 + (PC - 1) * s;
    *T0 = 1 + (TC - 1) * smooth((t - T_IGN) / 0.25);
}
static double p_amb(double t) { return 1 + (PA_HIGH - 1) * smooth((t - T_ALT0) / (T_ALT1 - T_ALT0)); }

static inline double minmod(double a, double b) {
    if (a * b <= 0) return 0;
    return fabs(a) < fabs(b) ? a : b;
}

/* HLLC: W = rho, un, ut, p, y ; F = mass, n-mom, t-mom, E, y */
static inline void hllc(const double *L, const double *R, double *F) {
    double rL = L[0], uL = L[1], vL = L[2], pL = L[3], yL = L[4];
    double rR = R[0], uR = R[1], vR = R[2], pR = R[3], yR = R[4];
    double cL = sqrt(GAM * pL / rL), cR = sqrt(GAM * pR / rR);
    double EL = pL / (GAM - 1) + 0.5 * rL * (uL * uL + vL * vL);
    double ER = pR / (GAM - 1) + 0.5 * rR * (uR * uR + vR * vR);
    double SL = fmin(uL - cL, uR - cR), SR = fmax(uL + cL, uR + cR);
    double dL = rL * (SL - uL), dR = rR * (SR - uR);
    double Ss = (pR - pL + uL * dL - uR * dR) / (dL - dR);
    if (SL >= 0) {
        F[0] = rL * uL; F[1] = rL * uL * uL + pL; F[2] = rL * uL * vL; F[3] = (EL + pL) * uL; F[4] = rL * uL * yL;
    } else if (SR <= 0) {
        F[0] = rR * uR; F[1] = rR * uR * uR + pR; F[2] = rR * uR * vR; F[3] = (ER + pR) * uR; F[4] = rR * uR * yR;
    } else if (Ss >= 0) {
        double f = dL / (SL - Ss);
        double Us[5] = {f, f * Ss, f * vL, f * (EL / rL + (Ss - uL) * (Ss + pL / dL)), f * yL};
        double U[5] = {rL, rL * uL, rL * vL, EL, rL * yL};
        double Fk[5] = {rL * uL, rL * uL * uL + pL, rL * uL * vL, (EL + pL) * uL, rL * uL * yL};
        for (int k = 0; k < 5; k++) F[k] = Fk[k] + SL * (Us[k] - U[k]);
    } else {
        double f = dR / (SR - Ss);
        double Us[5] = {f, f * Ss, f * vR, f * (ER / rR + (Ss - uR) * (Ss + pR / dR)), f * yR};
        double U[5] = {rR, rR * uR, rR * vR, ER, rR * yR};
        double Fk[5] = {rR * uR, rR * uR * uR + pR, rR * uR * vR, (ER + pR) * uR, rR * uR * yR};
        for (int k = 0; k < 5; k++) F[k] = Fk[k] + SR * (Us[k] - U[k]);
    }
}

static double *W[5], *SX[5], *SRr[5], *FX[5], *FR[5];

/* eddy-viscosity flux across a face (normal gradients only), added to F.
   a = cell on the minus side, b = plus side; un/ut map (u,v) to normal/tangential */
static inline void visc_flux(size_t a, size_t b, double h, int rdir, double *F) {
    double nu = NU + (CS > 0 ? 0.5 * (NUT[a] + NUT[b]) : 0.0);
    if (nu <= 0) return;
    double rho = 0.5 * (W[0][a] + W[0][b]);
    double mu = rho * nu, cp = GAM / (GAM - 1);
    double du = (W[1][b] - W[1][a]) / h, dv = (W[2][b] - W[2][a]) / h;
    double Ta = W[3][a] / W[0][a], Tb = W[3][b] / W[0][b];
    double dT = (Tb - Ta) / h, dY = (W[4][b] - W[4][a]) / h;
    double uf = 0.5 * (W[1][a] + W[1][b]), vf = 0.5 * (W[2][a] + W[2][b]);
    /* F layout: mass, n-mom, t-mom, E, Y in x-ordering (u, v) */
    F[1] -= mu * du; F[2] -= mu * dv;
    F[3] -= mu * (uf * du + vf * dv) + mu * cp * dT;
    F[4] -= mu * dY;
    (void)rdir;
}

static void cons2prim(double *const *U) {
    #pragma omp parallel for
    for (size_t c = 0; c < (size_t)NX * NR; c++) {
        double r = U[0][c]; if (r < EPS) r = EPS;
        double u = U[1][c] / r, v = U[2][c] / r;
        double p = (GAM - 1) * (U[3][c] - 0.5 * r * (u * u + v * v));
        if (p < EPS) p = EPS;
        double y = U[4][c] / r; if (y < 0) y = 0; if (y > 1) y = 1;
        W[0][c] = r; W[1][c] = u; W[2][c] = v; W[3][c] = p; W[4][c] = y;
    }
}
static void prim2cons_fix(double **U) { /* re-derive U from clipped W */
    cons2prim(U);
    #pragma omp parallel for
    for (size_t c = 0; c < (size_t)NX * NR; c++) {
        double r = W[0][c], u = W[1][c], v = W[2][c], p = W[3][c], y = W[4][c];
        U[0][c] = r; U[1][c] = r * u; U[2][c] = r * v;
        U[3][c] = p / (GAM - 1) + 0.5 * r * (u * u + v * v); U[4][c] = r * y;
    }
}
static void force_reservoir(double **U, double t) {
    double p0, T0; chamber_target(t, &p0, &T0);
    double r = p0 / T0;
    for (size_t c = 0; c < (size_t)NX * NR; c++) if (FL[c] & 2) {
        U[0][c] = r; U[1][c] = 0; U[2][c] = 0; U[3][c] = p0 / (GAM - 1); U[4][c] = r;
    }
}

/* ghost-aware primitive fetch (no slope) */
static inline void getW(int i, int j, double pa, double *w) {
    if (i < 0 || j >= NR) { w[0] = pa; w[1] = 0; w[2] = 0; w[3] = pa; w[4] = 0; return; }
    if (i >= NX) i = NX - 1;
    int mirror = 0;
    if (j < 0) { j = 0; mirror = 1; }
    size_t c = ID(i, j);
    for (int k = 0; k < 5; k++) w[k] = W[k][c];
    if (mirror) w[2] = -w[2];
}

static double rhs(double **U, double t, double **dU, int want_dt) {
    cons2prim(U);
    double pa = p_amb(t);
    /* slopes */
    #pragma omp parallel for
    for (int i = 0; i < NX; i++) for (int j = 0; j < NR; j++) {
        size_t c = ID(i, j);
        double a[5], b[5], m[5];
        int fx = (FL[c] & 8) || i == 0 || i == NX - 1;
        int fr = (FL[c] & 16) || j == NR - 1;
        getW(i - 1, j, pa, a); getW(i + 1, j, pa, b);
        for (int k = 0; k < 5; k++) SX[k][c] = fx ? 0 : minmod(W[k][c] - a[k], b[k] - W[k][c]);
        getW(i, j - 1, pa, a); getW(i, j + 1, pa, b);
        for (int k = 0; k < 5; k++) SRr[k][c] = fr ? 0 : minmod(W[k][c] - a[k], b[k] - W[k][c]);
        (void)m;
    }
    /* Smagorinsky eddy viscosity: nu_t = (CS*DX)^2 |S| (shear layers only) */
    if (CS > 0) {
        double l2 = (CS * DX) * (CS * DX), cap = 3.0 * DX;
        #pragma omp parallel for
        for (int i = 0; i < NX; i++) for (int j = 0; j < NR; j++) {
            size_t c = ID(i, j);
            if (SOLID(c) || i == 0 || i == NX - 1 || j == NR - 1) { NUT[c] = 0; continue; }
            size_t e = ID(i + 1, j), w = ID(i - 1, j), n = ID(i, j + 1), s_ = j > 0 ? ID(i, j - 1) : c;
            if (SOLID(e)) e = c; if (SOLID(w)) w = c; if (SOLID(n)) n = c; if (SOLID(s_)) s_ = c;
            double dxw = (e != c && w != c) ? 2 * DX : DX, dyw = (n != c && s_ != c) ? 2 * DX : DX;
            double ux = (W[1][e] - W[1][w]) / dxw, vx = (W[2][e] - W[2][w]) / dxw;
            double ur = (W[1][n] - W[1][s_]) / dyw, vr = (W[2][n] - W[2][s_]) / dyw;
            double vor = W[2][c] / rc[j];
            double S2 = 2 * (ux * ux + vr * vr + vor * vor) + (ur + vx) * (ur + vx);
            double nt = l2 * sqrt(S2);
            NUT[c] = nt < cap ? nt : cap;
        }
    }
    /* x faces: face i between cell i-1 and i, i = 0..NX */
    #pragma omp parallel for
    for (int i = 0; i <= NX; i++) for (int j = 0; j < NR; j++) {
        double L[5], R[5], F[5];
        int sL = (i - 1 >= 0) && SOLID(ID(i - 1, j));
        int sR = (i < NX) && SOLID(ID(i, j));
        size_t f = (size_t)i * NR + j;
        if (sL && sR) { for (int k = 0; k < 5; k++) FX[k][f] = 0; continue; }
        getW(i - 1, j, pa, L); getW(i, j, pa, R);
        if (i - 1 >= 0) { size_t c = ID(i - 1, j); for (int k = 0; k < 5; k++) L[k] += 0.5 * SX[k][c]; }
        if (i < NX)     { size_t c = ID(i, j);     for (int k = 0; k < 5; k++) R[k] -= 0.5 * SX[k][c]; }
        if (L[0] <= EPS || L[3] <= EPS || R[0] <= EPS || R[3] <= EPS) { getW(i - 1, j, pa, L); getW(i, j, pa, R); }
        if (sR) { memcpy(R, L, sizeof L); R[1] = -L[1]; }
        if (sL) { memcpy(L, R, sizeof R); L[1] = -R[1]; }
        hllc(L, R, F);   /* (rho,u,v) normal = u */
        if ((NU > 0 || CS > 0) && !sL && !sR && i > 0 && i < NX) visc_flux(ID(i - 1, j), ID(i, j), DX, 0, F);
        for (int k = 0; k < 5; k++) FX[k][f] = F[k];
    }
    /* r faces: face j between cell j-1 and j, j = 0..NR */
    #pragma omp parallel for
    for (int i = 0; i < NX; i++) for (int j = 0; j <= NR; j++) {
        double L[5], R[5], F[5], l[5], r[5];
        size_t f = (size_t)i * (NR + 1) + j;
        int sL = (j - 1 >= 0) && SOLID(ID(i, j - 1));
        int sR = (j < NR) && SOLID(ID(i, j));
        if ((sL && sR) || j == 0) { for (int k = 0; k < 5; k++) FR[k][f] = 0; continue; }
        getW(i, j - 1, pa, L); getW(i, j, pa, R);
        if (j - 1 >= 0) { size_t c = ID(i, j - 1); for (int k = 0; k < 5; k++) L[k] += 0.5 * SRr[k][c]; }
        if (j < NR)     { size_t c = ID(i, j);     for (int k = 0; k < 5; k++) R[k] -= 0.5 * SRr[k][c]; }
        if (L[0] <= EPS || L[3] <= EPS || R[0] <= EPS || R[3] <= EPS) { getW(i, j - 1, pa, L); getW(i, j, pa, R); }
        if (sR) { memcpy(R, L, sizeof L); R[2] = -L[2]; }
        if (sL) { memcpy(L, R, sizeof R); L[2] = -R[2]; }
        l[0] = L[0]; l[1] = L[2]; l[2] = L[1]; l[3] = L[3]; l[4] = L[4];
        r[0] = R[0]; r[1] = R[2]; r[2] = R[1]; r[3] = R[3]; r[4] = R[4];
        hllc(l, r, F);
        { double t1 = F[1]; F[1] = F[2]; F[2] = t1; }   /* back to (mass, u-mom, v-mom, E, Y) */
        if ((NU > 0 || CS > 0) && !sL && !sR && j > 0 && j < NR) visc_flux(ID(i, j - 1), ID(i, j), DX, 1, F);
        double rr = rf[j];
        for (int k = 0; k < 5; k++) FR[k][f] = F[k] * rr;
    }
    double smax = 1e-12;
    #pragma omp parallel for reduction(max:smax)
    for (int i = 0; i < NX; i++) for (int j = 0; j < NR; j++) {
        size_t c = ID(i, j);
        if (SOLID(c)) { for (int k = 0; k < 5; k++) dU[k][c] = 0; continue; }
        size_t fx0 = (size_t)i * NR + j, fx1 = (size_t)(i + 1) * NR + j;
        size_t fr0 = (size_t)i * (NR + 1) + j, fr1 = fr0 + 1;
        for (int k = 0; k < 5; k++)
            dU[k][c] = -(FX[k][fx1] - FX[k][fx0]) / DX - (FR[k][fr1] - FR[k][fr0]) / (rc[j] * DX);
        dU[2][c] += W[3][c] / rc[j];
        if (NU > 0 || CS > 0) dU[2][c] -= W[0][c] * (NU + (CS > 0 ? NUT[c] : 0)) * W[2][c] / (rc[j] * rc[j]);
        if (want_dt) {
            double cs = sqrt(GAM * W[3][c] / W[0][c]);
            double s = (fabs(W[1][c]) + cs) / DX + (fabs(W[2][c]) + cs) / DX + CFL * 4 * (NU + (CS > 0 ? NUT[c] : 0)) * GAM / (DX * DX);
            if (s > smax) smax = s;
        }
    }
    return CFL / smax;
}

static void diagnostics(double t, FILE *lg, int k) {
    /* thrust = momentum + pressure flux of the exhaust through a plane just
       downstream of the cowl lip + pressure force on the spike/base behind it.
       (The wall integral over the whole engine is polluted by the artificial
       injector reservoir during the first fraction of a millisecond.) */
    double pa = p_amb(t), F = 0, Tsum = 0, psum = 0; int n = 0;
    int ic = (int)((XLIP + 0.06) / DX);
    for (int j = 0; j < NR; j++) {
        size_t c = ID(ic, j);
        if (SOLID(c)) continue;
        double A = 2 * M_PI * rc[j] * DX;
        if (W[4][c] < 0.02) continue;
        F += (W[0][c] * W[1][c] * W[1][c] + W[3][c] - pa) * A;
    }
    for (int i = ic; i < NX; i++) for (int j = 0; j < NR; j++) {
        size_t c = ID(i, j);
        if (SOLID(c)) continue;
        double A = 2 * M_PI * rc[j] * DX, p = W[3][c] - pa;
        if (i + 1 < NX && SOLID(ID(i + 1, j))) F -= p * A;   /* fluid pushes solid +x: reduces thrust */
        if (i - 1 >= ic && SOLID(ID(i - 1, j))) F += p * A;  /* spike surface facing +x */
    }
    for (int i = 0; i < NX; i++) for (int j = 0; j < NR; j++) {
        size_t c = ID(i, j);
        if (FL[c] & 4) { Tsum += W[3][c] / W[0][c]; psum += W[3][c]; n++; }
    }
    double Fx = -F;
    double mach[2];
    double xs[2] = {XSPIKE, XLIP};
    for (int q = 0; q < 2; q++) {
        int i = (int)(xs[q] / DX) + (q == 0 ? 1 : 2);
        double sw = 0, sm = 0;
        for (int j = 0; j < NR; j++) {
            size_t c = ID(i, j);
            if (SOLID(c)) continue;
            double cs = sqrt(GAM * W[3][c] / W[0][c]);
            double M = hypot(W[1][c], W[2][c]) / cs;
            double w = fabs(W[0][c] * W[1][c]) * W[4][c] * rc[j];
            sw += w; sm += M * w;
        }
        mach[q] = sw > 1e-12 ? sm / sw : 0;
    }
    double p0, T0; chamber_target(t, &p0, &T0);
    fprintf(lg, "%d %.6f %.5f %.5f %.5f %.5f %.5f %.5f %.5f\n", k, t, -Fx, Tsum / n, psum / n, mach[0], mach[1], pa, p0);
    fflush(lg);
}

static void read_params(const char *dir) {
    char fn[1024]; snprintf(fn, sizeof fn, "%s/params.txt", dir);
    FILE *f = fopen(fn, "r"); if (!f) { perror(fn); exit(1); }
    char key[64]; double val;
    while (fscanf(f, "%63s %lf", key, &val) == 2) {
#define P(name, var) if (!strcmp(key, name)) var = val;
        P("NX", NX) P("NR", NR) P("DX", DX) P("GAM", GAM) P("PC", PC) P("TC", TC) P("CFL", CFL)
        P("T_END", T_END) P("T_IGN", T_IGN) P("T_RAMP", T_RAMP) P("T_ALT0", T_ALT0) P("T_ALT1", T_ALT1)
        P("PA_HIGH", PA_HIGH) P("XSPIKE", XSPIKE) P("XLIP", XLIP)
        P("NU", NU) P("CS", CS) P("SNAP_DT1", SNAP_DT1) P("SNAP_DT2", SNAP_DT2) P("SNAP_SWITCH", SNAP_SWITCH)
    }
    fclose(f);
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: euler dir\n"); return 1; }
    const char *dir = argv[1];
    read_params(dir);
    size_t N = (size_t)NX * NR;
    FL = malloc(N);
    char fn[1024]; snprintf(fn, sizeof fn, "%s/flags.u8", dir);
    FILE *f = fopen(fn, "rb"); if (!f || fread(FL, 1, N, f) != N) { fprintf(stderr, "flags\n"); return 1; }
    fclose(f);
    NUT = calloc(N, sizeof(double));
    rc = malloc(NR * sizeof(double)); rf = malloc((NR + 1) * sizeof(double));
    for (int j = 0; j < NR; j++) rc[j] = (j + 0.5) * DX;
    for (int j = 0; j <= NR; j++) rf[j] = j * DX;
    double *U[5], *U1[5], *K[5];
    for (int k = 0; k < 5; k++) {
        U[k] = calloc(N, 8); U1[k] = calloc(N, 8); K[k] = calloc(N, 8);
        W[k] = calloc(N, 8); SX[k] = calloc(N, 8); SRr[k] = calloc(N, 8);
        FX[k] = calloc((size_t)(NX + 1) * NR, 8); FR[k] = calloc((size_t)NX * (NR + 1), 8);
    }
    for (size_t c = 0; c < N; c++) { U[0][c] = 1; U[3][c] = 1 / (GAM - 1); }
    snprintf(fn, sizeof fn, "%s/log.txt", dir);
    FILE *lg = fopen(fn, "w");
    float *buf = malloc(N * sizeof(float));
    double t = 0, next = 0; int k = 0; long steps = 0;
    double wall0 = omp_get_wtime();
    while (t <= T_END) {
        if (t >= next) {
            cons2prim(U);
            diagnostics(t, lg, k);
            snprintf(fn, sizeof fn, "%s/s%05d.f32", dir, k);
            FILE *o = fopen(fn, "wb");
            int order[3] = {0, 3, 4};
            for (int q = 0; q < 3; q++) { for (size_t c = 0; c < N; c++) buf[c] = (float)W[order[q]][c]; fwrite(buf, 4, N, o); }
            fclose(o);
            if (k % 25 == 0) { printf("t=%.4f steps=%ld snaps=%d wall=%.0fs\n", t, steps, k, omp_get_wtime() - wall0); fflush(stdout); }
            k++;
            next += (t < SNAP_SWITCH) ? SNAP_DT1 : SNAP_DT2;
        }
        force_reservoir(U, t);
        double dt = rhs(U, t, K, 1);
        if (next - t < dt && next > t) dt = next - t + 1e-12;
        #pragma omp parallel for
        for (size_t c = 0; c < N; c++) for (int q = 0; q < 5; q++) U1[q][c] = U[q][c] + dt * K[q][c];
        prim2cons_fix(U1);
        force_reservoir(U1, t + dt);
        rhs(U1, t + dt, K, 0);
        #pragma omp parallel for
        for (size_t c = 0; c < N; c++) if (!SOLID(c)) for (int q = 0; q < 5; q++) U[q][c] = 0.5 * U[q][c] + 0.5 * (U1[q][c] + dt * K[q][c]);
        prim2cons_fix(U);
        t += dt; steps++;
        force_reservoir(U, t);
    }
    printf("done steps=%ld wall=%.0fs\n", steps, omp_get_wtime() - wall0);
    return 0;
}
