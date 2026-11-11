import sys, numpy as np
from PIL import Image
d = sys.argv[1]; ks = [int(k) for k in sys.argv[3:]]; out = sys.argv[2]
g = np.load(d + "/grid.npz"); nx, nr = len(g['xc']), len(g['rc'])
ims = []
for k in ks:
    a = np.fromfile(f"{d}/s{k:05d}.f32", np.float32).reshape(5, nx, nr)
    rho, p, y, u, v = a
    gx, gr = np.gradient(np.log(rho))
    sch = np.exp(-4 * np.hypot(gx, gr) / (g['DX'] / 0.025))
    T = p / rho
    M = np.hypot(u, v) / np.sqrt(1.2 * T)
    img = np.stack([y * np.clip(T / 12, 0, 1) * 255, np.clip(M / 4, 0, 1) * 200 * (y > 0.3), sch * 160 + 50 * (1 - y)], -1)
    img[g['solid']] = [90, 90, 90]
    im = np.flipud(img.transpose(1, 0, 2)); im = np.concatenate([im, np.flipud(im)], 0)
    ims.append(Image.fromarray(im.astype(np.uint8)).resize((825, 540)))
W = Image.new('RGB', (1650, 540 * ((len(ims) + 1) // 2)))
for i, im in enumerate(ims): W.paste(im, ((i % 2) * 825, (i // 2) * 540))
W.save(out)
