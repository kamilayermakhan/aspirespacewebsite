/* Aspire refinement pass — loaded after transfer-band-v3.js */
(function () {
  'use strict';

  const esc = value => String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  /* Preload update imagery so the selected article does not visually "drop in" later. */
  try {
    if (Array.isArray(MEDIA_RELEASES)) {
      MEDIA_RELEASES.forEach(item => {
        const src = item.imageData || (item.fileId ? `https://drive.google.com/thumbnail?id=${encodeURIComponent(item.fileId)}&sz=w1800` : '');
        if (src) { const img = new Image(); img.decoding = 'async'; img.src = src; }
      });
    }
  } catch (err) {}

  const list = document.getElementById('oryxList');
  const stage = document.getElementById('oryxStage');
  const text = document.getElementById('oryxText');
  const title = document.getElementById('oryxTitle');
  if (!list || !text || !title || typeof architectureTransfer === 'undefined') return;

  const entries = [
    {
      navTitle: '1. ORYX ROCKETSHIP',
      image: 'assets/images/system/oryx-rocketship.svg',
      imageAlt: 'Oryx Rocketship',
      html: `
        <div class="architecture-spec-copy">
          <p class="architecture-spec-lead">Reusable first and second stages</p>
          <div class="architecture-spec-group">
            <div class="architecture-spec-label">PAYLOAD MASS</div>
            <p>LEO — H=200 km, i=51.6°</p>
            <p>up to 5t fully reusable</p>
          </div>
          <div class="architecture-spec-group">
            <div class="architecture-spec-label">PROPULSION</div>
            <p>First stage: 5 engines × 1,000 kN / 225,000 lbf</p>
            <p>Second stage: 5 engines × 200 kN / 45,000 lbf</p>
          </div>
        </div>`
    },
    {
      navTitle: '2. D3 CARGO SPACESHIP',
      image: 'assets/images/system/d3-cargo.svg',
      imageAlt: 'D3 Cargo Spaceship',
      html: `
        <div class="architecture-spec-copy">
          <p class="architecture-spec-lead">Reusable second stage, first of the kind</p>
          <ul class="architecture-spec-list">
            <li>up to 3t to LEO and return to Earth</li>
            <li>Stations refuel and manoeuver</li>
            <li>Standalone orbital lab</li>
            <li>Future crew missions</li>
            <li>Future Moon missions</li>
          </ul>
        </div>`
    },
    {
      navTitle: '3. ASPIRE LAUNCHER',
      image: 'assets/images/system/aspire-launcher.svg',
      imageAlt: 'Aspire Launcher',
      html: `
        <div class="architecture-spec-copy">
          <p class="architecture-spec-lead architecture-spec-kicker">R1 TWO-STAGE MEDIUM-LIFT LAUNCHER</p>
          <div class="architecture-spec-group">
            <div class="architecture-spec-label">VEHICLE</div>
            <p>Two-stage medium-lift space launch vehicle</p>
            <p>LEO — H=200 km, i=51.6°</p>
            <p>15 t reusable, 17 t expendable</p>
          </div>
          <ul class="architecture-spec-list">
            <li>Reusable first stage and fairing leading to lower operating costs</li>
            <li>Green methane-oxygen engines optimized for reusability</li>
            <li>Composite second stage with high mass ratio</li>
            <li>First in class reusable fairing for launching satellites</li>
          </ul>
        </div>`
    }
  ];

  function showEntry(index) {
    const entry = entries[index];
    if (!entry) return;
    stage?.classList.add('has-article');
    title.textContent = entry.navTitle;
    text.innerHTML = `<div class="architecture-spec-layout"><figure class="architecture-spec-visual"><img src="${esc(entry.image)}" alt="${esc(entry.imageAlt)}"></figure>${entry.html}</div>`;
    list.querySelectorAll('button[data-refinement-architecture-index]').forEach(btn => {
      const active = Number(btn.dataset.refinementArchitectureIndex) === index;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-current', active ? 'true' : 'false');
    });
    const scroll = stage?.querySelector('.media-article-scroll');
    if (scroll) scroll.scrollTop = 0;
  }

  function transfer(button, index, immediate) {
    const entry = entries[index];
    architectureTransfer.transferTo(
      button,
      index,
      entry.navTitle,
      entry.navTitle,
      () => showEntry(index),
      !!immediate
    );
  }

  architectureTransfer.reset();
  list.innerHTML = '';
  entries.forEach((entry, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.refinementArchitectureIndex = String(index);
    button.className = 'media-index-item architecture-rubricator';
    button.innerHTML = `<span class="media-index-item-outlet taxonomy-index-name">${esc(entry.navTitle)}</span><span class="media-index-item-arrow" aria-hidden="true">↗</span>`;
    button.addEventListener('click', () => transfer(button, index, false));
    list.appendChild(button);
  });

  const first = list.querySelector('button[data-refinement-architecture-index="0"]');
  if (first) transfer(first, 0, true);
})();
