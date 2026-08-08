/* Aspire refinement pass v5 — loaded after transfer-band-v3.js */
(function () {
  'use strict';

  const esc = value => String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  /* Final visual corrections for the three explorer shells. */
  const style = document.createElement('style');
  style.id = 'aspire-refinement-v5';
  style.textContent = `
    /* Outer MISSION / UPDATES / SYSTEM ARCHITECTURE shells are rectangular. */
    #mission-modal .media-shell,
    #media-modal .media-shell,
    body .architecture-shell.media-shell {
      clip-path: none !important;
      border-radius: 0 !important;
    }
    #mission-modal .media-shell-header,
    #media-modal .media-shell-header,
    body .architecture-shell .media-shell-header {
      clip-path: none !important;
    }
    #mission-modal .media-shell-header::before,
    #mission-modal .media-shell-header::after,
    #media-modal .media-shell-header::before,
    #media-modal .media-shell-header::after,
    body .architecture-shell .media-shell-header::before,
    body .architecture-shell .media-shell-header::after {
      display: none !important;
      content: none !important;
    }

    /* Desktop proportion is explicitly 20 / 80. */
    @media (min-width: 681px) {
      #architectureWorkspace,
      #missionWorkspace,
      #mediaWorkspace {
        display: grid !important;
        grid-template-columns: 20% 80% !important;
        gap: 0 !important;
        padding: 0 !important;
      }
      #architectureWorkspace > .media-index-pane {
        flex: none !important;
        width: auto !important;
      }
      #architectureWorkspace > .media-stage,
      #missionWorkspace > .media-stage,
      #mediaWorkspace > .media-stage {
        min-width: 0 !important;
      }
    }

    /* No delayed body/image entrance after selecting Mission or Updates. */
    .article-body-enter,
    #mediaArticlePane,
    #mediaText,
    #mediaText .media-article,
    #mediaArticlePane .media-article-visual,
    #mediaHeroImage,
    #mediaHeroAmbient,
    #missionArticlePane,
    #missionText,
    #missionText .media-article,
    #oryxText,
    #oryxText .architecture-spec-layout,
    #oryxText .architecture-spec-visual {
      animation: none !important;
      transition: none !important;
    }
    #mediaArticlePane,
    #mediaText,
    #mediaText .media-article,
    #mediaArticlePane .media-article-visual,
    #mediaHeroImage,
    #missionArticlePane,
    #missionText,
    #missionText .media-article,
    #oryxText,
    #oryxText .architecture-spec-layout,
    #oryxText .architecture-spec-visual {
      opacity: 1 !important;
    }

    /* Remove only the decorative line/facet above ROADMAP. */
    .project-roadmap-section > .section-bar {
      border-top: 0 !important;
      clip-path: none !important;
      box-shadow: none !important;
    }
    .project-roadmap-section > .section-bar::before,
    .project-roadmap-section > .section-bar::after {
      display: none !important;
      content: none !important;
    }
  `;
  document.head.appendChild(style);

  /* Disable the legacy delayed article-body enter helper at its source. */
  window.triggerBodyEnter = function (selector) {
    document.querySelectorAll(selector || '').forEach(node => {
      node.classList.remove('article-body-enter');
      node.style.opacity = '1';
      node.style.transform = 'none';
    });
  };

  const stabilizeArticleRoot = root => {
    if (!root) return;
    root.classList.remove('article-body-enter');
    root.querySelectorAll('.article-body-enter').forEach(node => node.classList.remove('article-body-enter'));
  };
  ['mediaText', 'missionText'].forEach(id => {
    const root = document.getElementById(id);
    if (!root) return;
    stabilizeArticleRoot(root);
    new MutationObserver(() => stabilizeArticleRoot(root)).observe(root, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class']
    });
  });

  /* Decode Updates imagery ahead of interaction; pointer hover reinforces it. */
  const preloadCache = new Map();
  const preloadUpdate = index => {
    try {
      const item = Array.isArray(MEDIA_RELEASES) ? MEDIA_RELEASES[index] : null;
      if (!item) return;
      const src = item.imageData || (item.fileId ? `https://drive.google.com/thumbnail?id=${encodeURIComponent(item.fileId)}&sz=w1800` : '');
      if (!src || preloadCache.has(src)) return;
      const image = new Image();
      image.decoding = 'async';
      image.src = src;
      const ready = typeof image.decode === 'function' ? image.decode().catch(() => {}) : Promise.resolve();
      preloadCache.set(src, ready);
    } catch (err) {}
  };
  try {
    if (Array.isArray(MEDIA_RELEASES)) MEDIA_RELEASES.forEach((_, index) => preloadUpdate(index));
  } catch (err) {}
  const mediaList = document.getElementById('mediaList');
  mediaList?.addEventListener('pointerover', event => {
    const button = event.target.closest('button[data-media-index]');
    if (button) preloadUpdate(Number(button.dataset.mediaIndex));
  });

  /* Partner copy/link corrections. */
  const partnersTitle = document.getElementById('partnersTitle');
  if (partnersTitle) partnersTitle.textContent = 'PROGRAM NETWORK';
  const partnerCards = Array.from(document.querySelectorAll('.partners-grid .partner-card'));
  if (partnerCards[0]) {
    const eyebrow = partnerCards[0].querySelector('.partner-card-eyebrow');
    if (eyebrow) eyebrow.textContent = 'PROPULSION';
  }
  if (partnerCards[2]) {
    const eyebrow = partnerCards[2].querySelector('.partner-card-eyebrow');
    const heading = partnerCards[2].querySelector('.partner-card-title');
    const oldLink = partnerCards[2].querySelector('.partner-card-link');
    if (eyebrow) eyebrow.textContent = 'GROUND INFRASTRUCTURE';
    if (heading) heading.textContent = 'ASPIRE LAUNCH';
    if (oldLink) {
      const link = document.createElement('a');
      link.className = 'partner-card-link';
      link.href = 'https://www.aspirelaunch.space/';
      link.target = '_blank';
      link.rel = 'noopener';
      link.textContent = 'VISIT SITE ↗';
      oldLink.replaceWith(link);
    }
  }

  /* SYSTEM ARCHITECTURE — retain the shared transfer interaction, but use the
     supplied AVIF renders for the three requested cards. */
  const list = document.getElementById('oryxList');
  const stage = document.getElementById('oryxStage');
  const text = document.getElementById('oryxText');
  const title = document.getElementById('oryxTitle');
  if (!list || !text || !title || typeof architectureTransfer === 'undefined') return;

  const entries = [
    {
      navTitle: '1. ORYX ROCKETSHIP',
      image: 'assets/images/system/R1V5.avif',
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
      image: 'assets/images/system/S2_5.avif',
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
      image: 'assets/images/system/Fairings_2.avif',
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

  const showEntry = index => {
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
  };

  const transfer = (button, index, immediate) => {
    const entry = entries[index];
    architectureTransfer.transferTo(
      button,
      index,
      entry.navTitle,
      entry.navTitle,
      () => showEntry(index),
      !!immediate
    );
  };

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
