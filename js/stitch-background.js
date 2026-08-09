(() => {
  'use strict';

  /*
   * Aspire Space — reference-faithful interactive halftone field.
   *
   * The supplied Aspen reference is not a field of hand-drawn X marks. Its
   * material character comes from a 5px ordered-dither lattice: tiny square
   * stitches combine into cross-like clusters as the source luminance changes.
   *
   * The compact PNG below is a tonal-density map extracted from the supplied
   * Figma reference (the captured background image, reduced to 64px wide). It
   * is NOT displayed directly. We sample its luminance and reconstruct the
   * screen pattern at native CSS-pixel resolution, so the texture stays crisp.
   * The cursor then recolours only stitches that already belong to that field.
   */

  const REFERENCE_DENSITY_MAP = 'data:image/png;base64,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';

  const old = document.getElementById('stitch-bg');
  if (old) old.remove();

  const canvas = document.createElement('canvas');
  canvas.id = 'stitch-bg';
  canvas.setAttribute('aria-hidden', 'true');
  document.body.prepend(canvas);

  const ctx = canvas.getContext('2d', { alpha: false, desynchronized: true });
  if (!ctx) return;

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const COLOR = {
    paper: '#ffffff',
    ink: [48, 47, 52],
    accent: [98, 81, 118]
  };

  /* 4×4 Bayer order. The reference's visible 5px / 20px periodicity maps to
     a 5px stitch cell controlled by a four-cell ordered-dither matrix. */
  const BAYER4 = [
     0,  8,  2, 10,
    12,  4, 14,  6,
     3, 11,  1,  9,
    15,  7, 13,  5
  ];

  const CELL = 5;
  const STITCH = 2;
  const DPR_CAP = 2;
  const MAP_W = 64;
  const MAP_H = 84;

  let width = 0;
  let height = 0;
  let dpr = 1;
  let base = document.createElement('canvas');
  let baseCtx = base.getContext('2d', { alpha: false });
  let densityPixels = null;
  let visibleCells = [];
  let animationId = 0;

  const densityImage = new Image();
  densityImage.decoding = 'async';

  const pointer = {
    x: -1000,
    y: -1000,
    targetX: -1000,
    targetY: -1000,
    active: false,
    energy: 0,
    vx: 0,
    vy: 0
  };

  const trail = Array.from({ length: 7 }, (_, i) => ({
    x: -1000,
    y: -1000,
    a: 0,
    lag: 0.42 - i * 0.045
  }));

  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  function rgba(rgb, alpha) {
    return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;
  }

  function bayerThreshold(gx, gy) {
    return (BAYER4[((gy & 3) << 2) + (gx & 3)] + 0.5) / 16;
  }

  function fallbackDensity(x, y) {
    const nx = x / Math.max(1, width);
    const ny = y / Math.max(1, width);
    const a = Math.sin(nx * 8.3 + ny * 3.1);
    const b = Math.sin(nx * -4.7 + ny * 10.6 + 1.8);
    const c = Math.cos((nx + ny) * 7.2 - 0.6);
    const tonal = 0.5 + 0.22 * a + 0.18 * b + 0.12 * c;
    return clamp(tonal, 0.06, 0.94);
  }

  function sampleDensity(x, y) {
    if (!densityPixels) return fallbackDensity(x, y);

    /* The Figma capture is 1913×2490. The original desktop treatment maps its
       width directly to the viewport width, while mobile uses a cover crop. */
    const coverScale = Math.max(width / MAP_W, height / MAP_H);
    const renderedW = MAP_W * coverScale;
    const left = (width - renderedW) * 0.5;

    const sx = clamp(Math.floor((x - left) / coverScale), 0, MAP_W - 1);
    const sy = clamp(Math.floor(y / coverScale), 0, MAP_H - 1);
    const i = (sy * MAP_W + sx) * 4;
    const lum = (densityPixels[i] * 0.2126 + densityPixels[i + 1] * 0.7152 + densityPixels[i + 2] * 0.0722) / 255;

    /* Downsampling turns the reference's existing screen pattern back into a
       continuous tonal map. Re-screen it with the native ordered lattice. */
    const ink = Math.pow(clamp(1 - lum, 0, 1), 0.82);
    return clamp(0.035 + ink * 1.24, 0.035, 0.98);
  }

  function drawStitch(target, x, y, rgb, alpha = 1) {
    target.fillStyle = rgba(rgb, alpha);
    target.fillRect(x + 1, y + 1, STITCH, STITCH);
  }

  function rebuildBase() {
    if (!width || !height) return;

    base.width = Math.round(width * dpr);
    base.height = Math.round(height * dpr);
    baseCtx = base.getContext('2d', { alpha: false });
    baseCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    baseCtx.imageSmoothingEnabled = false;
    baseCtx.fillStyle = COLOR.paper;
    baseCtx.fillRect(0, 0, width, height);

    visibleCells = [];

    const cols = Math.ceil(width / CELL) + 1;
    const rows = Math.ceil(height / CELL) + 1;

    for (let gy = -1; gy < rows; gy++) {
      const y = gy * CELL;
      for (let gx = -1; gx < cols; gx++) {
        const x = gx * CELL;
        const density = sampleDensity(x + CELL * 0.5, y + CELL * 0.5);
        if (density <= bayerThreshold(gx, gy)) continue;

        /* The reference modulates coverage, not line opacity. Keep every
           printed stitch nearly equally dark; density comes from occupancy. */
        const alpha = 0.72 + density * 0.20;
        drawStitch(baseCtx, x, y, COLOR.ink, alpha);
        visibleCells.push({ x, y });
      }
    }
  }

  function resize() {
    width = Math.max(1, window.innerWidth);
    height = Math.max(1, window.innerHeight);
    dpr = Math.min(window.devicePixelRatio || 1, DPR_CAP);

    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = false;

    rebuildBase();
  }

  function updateTrail() {
    const oldX = pointer.x;
    const oldY = pointer.y;

    const follow = reducedMotion ? 1 : 0.24;
    pointer.x += (pointer.targetX - pointer.x) * follow;
    pointer.y += (pointer.targetY - pointer.y) * follow;
    pointer.vx = pointer.x - oldX;
    pointer.vy = pointer.y - oldY;

    const targetEnergy = pointer.active ? 1 : 0;
    pointer.energy += (targetEnergy - pointer.energy) * (pointer.active ? 0.16 : 0.075);

    if (reducedMotion) {
      trail[0].x = pointer.x;
      trail[0].y = pointer.y;
      trail[0].a = pointer.energy;
      for (let i = 1; i < trail.length; i++) trail[i].a = 0;
      return;
    }

    for (let i = 0; i < trail.length; i++) {
      const prev = i === 0 ? pointer : trail[i - 1];
      const node = trail[i];
      const ease = Math.max(0.08, node.lag);
      node.x += (prev.x - node.x) * ease;
      node.y += (prev.y - node.y) * ease;
      const age = i / (trail.length - 1);
      const targetA = pointer.energy * (1 - age * 0.72);
      node.a += (targetA - node.a) * (0.19 - age * 0.07);
    }
  }

  function glowAt(x, y) {
    let value = 0;

    const speed = Math.min(1, Math.hypot(pointer.vx, pointer.vy) / 24);
    const rxBase = 205 + speed * 60;
    const ryBase = 142 + speed * 24;

    for (let i = 0; i < trail.length; i++) {
      const node = trail[i];
      if (node.a < 0.01) continue;

      const age = i / Math.max(1, trail.length - 1);
      const rx = rxBase * (1 + age * 0.20);
      const ry = ryBase * (1 + age * 0.10);
      const dx = (x - node.x) / rx;
      const dy = (y - node.y) / ry;
      const d2 = dx * dx + dy * dy;
      if (d2 > 1.35) continue;

      /* Gaussian lobes overlap to reproduce the wide irregular glow / tail in
         the supplied video instead of a hard radial cursor spotlight. */
      const lobe = Math.exp(-d2 * 2.65) * node.a * (1 - age * 0.48);
      value += lobe;
    }

    return clamp(value, 0, 1);
  }

  function render() {
    updateTrail();

    ctx.clearRect(0, 0, width, height);
    ctx.drawImage(base, 0, 0, width, height);

    if (pointer.energy > 0.004) {
      /* A barely perceptible paper tint gives the same soft luminous body as
         the video, while the actual highlighted elements stay dark lilac. */
      const newest = trail[0];
      if (newest && newest.a > 0.01) {
        const haze = ctx.createRadialGradient(newest.x, newest.y, 0, newest.x, newest.y, 255);
        haze.addColorStop(0, rgba(COLOR.accent, 0.055 * newest.a));
        haze.addColorStop(0.46, rgba(COLOR.accent, 0.024 * newest.a));
        haze.addColorStop(1, rgba(COLOR.accent, 0));
        ctx.fillStyle = haze;
        ctx.fillRect(newest.x - 260, newest.y - 260, 520, 520);
      }

      /* Reprint only existing ordered-dither stitches. Nothing new is drawn
         inside the glow, so the tonal image and its stitch logic are preserved. */
      for (let i = 0; i < visibleCells.length; i++) {
        const cell = visibleCells[i];
        const g = glowAt(cell.x + 2, cell.y + 2);
        if (g < 0.045) continue;
        drawStitch(ctx, cell.x, cell.y, COLOR.accent, 0.24 + g * 0.76);
      }
    }

    animationId = requestAnimationFrame(render);
  }

  function seedPointer(x, y) {
    pointer.x = pointer.targetX = x;
    pointer.y = pointer.targetY = y;
    for (let i = 0; i < trail.length; i++) {
      trail[i].x = x;
      trail[i].y = y;
      trail[i].a = 0;
    }
  }

  window.addEventListener('pointermove', (event) => {
    if (event.pointerType === 'touch') return;
    if (pointer.x < -500) seedPointer(event.clientX, event.clientY);
    pointer.targetX = event.clientX;
    pointer.targetY = event.clientY;
    pointer.active = true;
  }, { passive: true });

  window.addEventListener('pointerenter', (event) => {
    if (event.pointerType === 'touch') return;
    seedPointer(event.clientX, event.clientY);
    pointer.active = true;
  }, { passive: true });

  window.addEventListener('pointerleave', () => {
    pointer.active = false;
  }, { passive: true });

  window.addEventListener('blur', () => {
    pointer.active = false;
  });

  let resizeTimer = 0;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(resize, 80);
  }, { passive: true });

  densityImage.onload = () => {
    const densityCanvas = document.createElement('canvas');
    densityCanvas.width = MAP_W;
    densityCanvas.height = MAP_H;
    const densityCtx = densityCanvas.getContext('2d', { willReadFrequently: true });
    densityCtx.imageSmoothingEnabled = true;
    densityCtx.drawImage(densityImage, 0, 0, MAP_W, MAP_H);
    densityPixels = densityCtx.getImageData(0, 0, MAP_W, MAP_H).data;
    rebuildBase();
  };

  densityImage.src = REFERENCE_DENSITY_MAP;

  resize();
  if (animationId) cancelAnimationFrame(animationId);
  animationId = requestAnimationFrame(render);
})();
