/* Aspire refinement pass v7 — loaded after transfer-band-v3.js */
(function () {
  'use strict';

  const esc = value => String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  const px = value => {
    const n = parseFloat(value);
    return Number.isFinite(n) ? n : 0;
  };

  const style = document.createElement('style');
  style.id = 'aspire-refinement-v7';
  style.textContent = `
    /* Outer MISSION / UPDATES / SYSTEM ARCHITECTURE shells stay rectangular. */
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
      #architectureWorkspace > .media-index-pane,
      #missionWorkspace > .media-index-pane,
      #mediaWorkspace > .media-index-pane {
        flex: none !important;
        width: auto !important;
        min-width: 0 !important;
      }
      #architectureWorkspace > .media-stage,
      #missionWorkspace > .media-stage,
      #mediaWorkspace > .media-stage {
        min-width: 0 !important;
      }
    }

    /* Content is born in its final position: no delayed drop/fade. */
    .article-body-enter,
    #mediaArticlePane,
    #mediaArticleScroll,
    #mediaText,
    #mediaText .media-article,
    #mediaArticlePane .media-article-visual,
    #mediaHeroImage,
    #mediaHeroAmbient,
    #missionArticlePane,
    #missionArticleScroll,
    #missionText,
    #missionText > *,
    #oryxText,
    #oryxText .architecture-spec-layout,
    #oryxText .architecture-spec-visual,
    #oryxText .architecture-spec-visual img {
      animation: none !important;
      transition: none !important;
      transform: none !important;
      opacity: 1 !important;
    }

    /* A source position that has already been transferred stays structurally
       present but visually empty. It never collapses the catalogue. */
    .media-index-item--evacuated,
    .media-index-item--evacuated:hover,
    .media-index-item--evacuated.is-active {
      background: transparent !important;
      background-image: none !important;
      box-shadow: none !important;
    }
    .media-index-item--evacuated .media-index-item-title,
    .media-index-item--evacuated .media-index-item-outlet,
    .media-index-item--evacuated .media-index-item-arrow,
    .media-index-item--evacuated .taxonomy-index-name {
      visibility: hidden !important;
    }

    /* Update photographs keep the current width but use their intrinsic aspect
       ratio instead of being forced into a shallow fixed-height viewport. */
    #mediaArticlePane .media-article-visual {
      width: 100% !important;
      height: auto !important;
      min-height: 0 !important;
      max-height: none !important;
      overflow: visible !important;
    }
    #mediaArticlePane .media-article-visual #mediaHeroImage {
      position: relative !important;
      display: block !important;
      width: 100% !important;
      height: auto !important;
      max-height: none !important;
      object-fit: contain !important;
    }
    #mediaHeroAmbient {
      display: none !important;
    }

    /* System Architecture renders also keep their existing width and recover
       the original image aspect ratio / height. */
    #architectureWorkspace .architecture-spec-visual {
      min-height: 0 !important;
      height: auto !important;
      align-items: flex-start !important;
    }
    #architectureWorkspace .architecture-spec-visual img {
      width: min(90%, 940px) !important;
      height: auto !important;
      max-height: none !important;
      object-fit: contain !important;
    }

    /* Remove decorative rule/facets above ROADMAP. */
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

    /* PROGRAM NETWORK starts cleanly: no outer/header rule above title. */
    .partners-shell {
      clip-path: none !important;
      border-top: 0 !important;
      box-shadow: none !important;
    }
    .partners-shell::before,
    .partners-shell::after,
    .partners-shell > .section-bar::before,
    .partners-shell > .section-bar::after {
      display: none !important;
      content: none !important;
    }
    .partners-shell > .section-bar {
      clip-path: none !important;
      border-top: 0 !important;
      box-shadow: none !important;
    }
  `;
  document.head.appendChild(style);

  /* Disable the legacy delayed entrance helper at the source. */
  window.triggerBodyEnter = function (selector) {
    if (!selector) return;
    document.querySelectorAll(selector).forEach(node => {
      node.classList.remove('article-body-enter');
      node.style.opacity = '1';
      node.style.transform = 'none';
      node.style.animation = 'none';
      node.style.transition = 'none';
    });
  };

  /* ------------------------------------------------------------------
     Shared explorer state: one current selection + persistent evacuated
     source slots. Previous source labels no longer reappear when a lower
     rubricator is selected.
     ------------------------------------------------------------------ */
  if (typeof TransferCardController !== 'undefined') {
    const proto = TransferCardController.prototype;
    const baseTransferTo = proto.transferTo;

    const ensureState = controller => {
      if (!controller.evacuatedRows) controller.evacuatedRows = new Set();
      return controller.evacuatedRows;
    };

    proto._restorePreviousLabel = function () {
      if (!this.sourceLabel) return;
      const row = this.sourceLabel;
      row.classList.remove('media-index-item--transferring');
      row.classList.add('media-index-item--evacuated');
      ensureState(this).add(row);
      this.sourceLabel = null;
    };

    proto.reset = function () {
      this._cancelActive();
      const rows = ensureState(this);
      if (this.sourceLabel) rows.add(this.sourceLabel);
      rows.forEach(row => {
        if (!row || !row.classList) return;
        row.classList.remove('media-index-item--transferring');
        row.classList.remove('media-index-item--evacuated');
      });
      rows.clear();
      this.sourceLabel = null;
      this.dockedIndex = null;
      this.dockedRow = null;
      if (this.card) this.card.style.display = 'none';
      if (this.frame) {
        this.frame.classList.remove('has-transfer-band');
        this.frame.style.removeProperty('--transfer-band-reserve');
      }
    };

    /* Dock the moving label on the exact left edge of the article text column,
       not on a hard-coded stage inset. */
    const baseMeasureBand = proto._measureBand;
    proto._measureBand = function (row) {
      const measured = baseMeasureBand.call(this, row);
      if (!measured || !this.frame) return measured;
      const body = this.frame.querySelector('.media-article-body');
      if (!body) return measured;
      const bodyRect = body.getBoundingClientRect();
      const bodyCS = getComputedStyle(body);
      measured.dock.labelX = bodyRect.left - measured.frameRect.left + px(bodyCS.paddingLeft);
      return measured;
    };

    proto.transferTo = function (row, index, sourceText, targetText, prepareContent, immediate) {
      /* Clicking the currently docked blank source slot again should not destroy
         its geometry or try to measure a hidden label. */
      if (row && row === this.sourceLabel && this.dockedIndex === index) {
        if (typeof prepareContent === 'function') prepareContent();
        return;
      }
      return baseTransferTo.call(this, row, index, sourceText, targetText, prepareContent, immediate);
    };
  }

  /* ------------------------------------------------------------------
     Image warming. The three Architecture AVIFs are tiny enough to preload
     immediately. Updates images are fetched/decode-warmed one at a time during
     idle time so clicks do not wait for network/decode, without blocking open.
     ------------------------------------------------------------------ */
  const retainedPreloads = [];
  const warmImage = src => {
    if (!src) return Promise.resolve();
    const image = new Image();
    image.decoding = 'async';
    image.src = src;
    retainedPreloads.push(image);
    if (typeof image.decode === 'function') return image.decode().catch(() => {});
    return Promise.resolve();
  };

  [
    'assets/images/system/R1V5.avif',
    'assets/images/system/S2_5.avif',
    'assets/images/system/Fairings_2.avif'
  ].forEach(src => { warmImage(src); });

  const updateSources = [];
  try {
    if (Array.isArray(MEDIA_RELEASES)) {
      MEDIA_RELEASES.forEach(item => {
        const src = item.imageData || (item.fileId
          ? `https://drive.google.com/thumbnail?id=${encodeURIComponent(item.fileId)}&sz=w1800`
          : '');
        if (src && !updateSources.includes(src)) updateSources.push(src);
      });
    }
  } catch (err) {}

  const scheduleWarm = index => {
    if (index >= updateSources.length) return;
    const run = () => {
      warmImage(updateSources[index]).finally(() => scheduleWarm(index + 1));
    };
    if ('requestIdleCallback' in window) {
      window.requestIdleCallback(run, { timeout: 900 });
    } else {
      setTimeout(run, 120 + index * 40);
    }
  };
  scheduleWarm(0);

  document.getElementById('mediaList')?.addEventListener('pointerover', event => {
    const button = event.target.closest('button[data-media-index]');
    if (!button) return;
    const index = Number(button.dataset.mediaIndex);
    if (Number.isFinite(index) && updateSources[index]) warmImage(updateSources[index]);
  }, { passive: true });

  document.getElementById('missionList')?.addEventListener('click', () => {
    requestAnimationFrame(() => window.triggerBodyEnter('#missionText'));
  });
  document.getElementById('mediaList')?.addEventListener('click', () => {
    requestAnimationFrame(() => window.triggerBodyEnter('#mediaText'));
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
    if (oldLink && oldLink.tagName !== 'A') {
      const link = document.createElement('a');
      link.className = 'partner-card-link';
      link.href = 'https://www.aspirelaunch.space/';
      link.target = '_blank';
      link.rel = 'noopener';
      link.textContent = 'VISIT SITE ↗';
      oldLink.replaceWith(link);
    } else if (oldLink) {
      oldLink.href = 'https://www.aspirelaunch.space/';
      oldLink.target = '_blank';
      oldLink.rel = 'noopener';
      oldLink.textContent = 'VISIT SITE ↗';
    }
  }

  /* SYSTEM ARCHITECTURE — shared transfer interaction + supplied AVIF renders. */
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
