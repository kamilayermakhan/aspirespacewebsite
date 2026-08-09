(() => {
  'use strict';

  const existing = document.getElementById('stitch-bg');
  if (existing) existing.remove();

  const canvas = document.createElement('canvas');
  canvas.id = 'stitch-bg';
  canvas.setAttribute('aria-hidden', 'true');
  document.body.prepend(canvas);

  const ctx = canvas.getContext('2d', { alpha: false, desynchronized: true });
  if (!ctx) return;

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const dprCap = 2;

  const PALETTE = {
    paper: [244, 244, 241],
    ink: [86, 87, 92],
    accent: [98, 81, 118]
  };

  const CFG = {
    spacing: 8,
    size: 2.7,
    baseAlpha: 0.28,
    radius: 138,
    trailLength: 11,
    follow: 0.34,
    fade: 0.90
  };

  let width = 0;
  let height = 0;
  let dpr = 1;
  let offscreen = document.createElement('canvas');
  let offctx = offscreen.getContext('2d', { alpha: false });

  const pointer = {
    x: -1000,
    y: -1000,
    tx: -1000,
    ty: -1000,
    active: false,
    energy: 0
  };

  const trail = Array.from({ length: CFG.trailLength }, () => ({ x: -1000, y: -1000, a: 0 }));

  function rgba(rgb, a) {
    return `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${a})`;
  }

  function drawCross(target, x, y, size, color, alpha, lineWidth = 0.82) {
    target.strokeStyle = rgba(color, alpha);
    target.lineWidth = lineWidth;
    target.beginPath();
    target.moveTo(x - size, y - size);
    target.lineTo(x + size, y + size);
    target.moveTo(x + size, y - size);
    target.lineTo(x - size, y + size);
    target.stroke();
  }

  function densityAt(x, y) {
    /* Gentle deterministic density modulation gives the field the woven,
       printed quality of the reference without turning it into a map. */
    const a = Math.sin(x * 0.012 + y * 0.004) * 0.5 + 0.5;
    const b = Math.sin(y * 0.015 - x * 0.003 + 1.7) * 0.5 + 0.5;
    const c = Math.sin((x + y) * 0.006 + 0.8) * 0.5 + 0.5;
    return 0.78 + (a * 0.08 + b * 0.08 + c * 0.06);
  }

  function rebuildBase() {
    offscreen.width = Math.round(width * dpr);
    offscreen.height = Math.round(height * dpr);
    offscreen.style.width = `${width}px`;
    offscreen.style.height = `${height}px`;
    offctx = offscreen.getContext('2d', { alpha: false });
    offctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    offctx.fillStyle = `rgb(${PALETTE.paper.join(',')})`;
    offctx.fillRect(0, 0, width, height);

    offctx.lineCap = 'square';
    for (let y = -CFG.spacing; y <= height + CFG.spacing; y += CFG.spacing) {
      for (let x = -CFG.spacing; x <= width + CFG.spacing; x += CFG.spacing) {
        const density = densityAt(x, y);
        drawCross(
          offctx,
          x,
          y,
          CFG.size,
          PALETTE.ink,
          CFG.baseAlpha * density,
          0.78
        );
      }
    }
  }

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    dpr = Math.min(window.devicePixelRatio || 1, dprCap);

    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.lineCap = 'square';

    rebuildBase();
  }

  function paintAccentBlob(cx, cy, strength) {
    if (strength <= 0.01) return;

    const radius = CFG.radius * (0.82 + strength * 0.18);
    const minX = Math.floor((cx - radius) / CFG.spacing) * CFG.spacing;
    const maxX = Math.ceil((cx + radius) / CFG.spacing) * CFG.spacing;
    const minY = Math.floor((cy - radius) / CFG.spacing) * CFG.spacing;
    const maxY = Math.ceil((cy + radius) / CFG.spacing) * CFG.spacing;

    for (let y = minY; y <= maxY; y += CFG.spacing) {
      if (y < -CFG.spacing || y > height + CFG.spacing) continue;
      for (let x = minX; x <= maxX; x += CFG.spacing) {
        if (x < -CFG.spacing || x > width + CFG.spacing) continue;
        const dx = x - cx;
        const dy = y - cy;
        const dist = Math.hypot(dx, dy);
        if (dist > radius) continue;

        const t = 1 - dist / radius;
        const falloff = t * t * (3 - 2 * t);
        const weave = 0.82 + 0.18 * Math.sin(x * 0.035 + y * 0.027);
        const alpha = Math.min(0.96, falloff * strength * 0.93 * weave);
        if (alpha < 0.025) continue;

        drawCross(
          ctx,
          x,
          y,
          CFG.size * (1 + falloff * 0.23),
          PALETTE.accent,
          alpha,
          0.92 + falloff * 0.28
        );
      }
    }
  }

  function updateTrail() {
    pointer.x += (pointer.tx - pointer.x) * CFG.follow;
    pointer.y += (pointer.ty - pointer.y) * CFG.follow;
    pointer.energy += ((pointer.active ? 1 : 0) - pointer.energy) * (pointer.active ? 0.22 : 0.10);

    if (reducedMotion) {
      trail[0].x = pointer.tx;
      trail[0].y = pointer.ty;
      trail[0].a = pointer.active ? 1 : 0;
      for (let i = 1; i < trail.length; i++) trail[i].a = 0;
      return;
    }

    trail[0].x += (pointer.x - trail[0].x) * 0.46;
    trail[0].y += (pointer.y - trail[0].y) * 0.46;
    trail[0].a = pointer.energy;

    for (let i = 1; i < trail.length; i++) {
      const prev = trail[i - 1];
      const node = trail[i];
      node.x += (prev.x - node.x) * 0.30;
      node.y += (prev.y - node.y) * 0.30;
      node.a += ((prev.a * CFG.fade) - node.a) * 0.18;
    }
  }

  function render() {
    updateTrail();

    ctx.clearRect(0, 0, width, height);
    ctx.drawImage(offscreen, 0, 0, width, height);

    /* Draw oldest first so the newest cursor region stays crisp. */
    for (let i = trail.length - 1; i >= 0; i--) {
      const node = trail[i];
      const age = 1 - i / trail.length;
      paintAccentBlob(node.x, node.y, node.a * (0.30 + age * 0.70));
    }

    requestAnimationFrame(render);
  }

  window.addEventListener('pointermove', (event) => {
    if (event.pointerType === 'touch') return;
    pointer.tx = event.clientX;
    pointer.ty = event.clientY;
    pointer.active = true;
  }, { passive: true });

  window.addEventListener('pointerenter', (event) => {
    if (event.pointerType === 'touch') return;
    pointer.tx = event.clientX;
    pointer.ty = event.clientY;
    pointer.x = event.clientX;
    pointer.y = event.clientY;
    trail.forEach(node => {
      node.x = event.clientX;
      node.y = event.clientY;
    });
    pointer.active = true;
  }, { passive: true });

  window.addEventListener('pointerleave', () => {
    pointer.active = false;
  }, { passive: true });

  window.addEventListener('blur', () => {
    pointer.active = false;
  });

  window.addEventListener('resize', resize, { passive: true });

  resize();
  requestAnimationFrame(render);
})();
