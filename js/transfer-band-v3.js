/* Aspire interaction correction — sticky full-width Transfer Band, title-based
 * Updates catalogue, and System Architecture content. Loaded after script.js.
 */
(function () {
  'use strict';

  if (typeof TransferCardController === 'undefined') return;

  const px = value => {
    const n = parseFloat(value);
    return Number.isFinite(n) ? n : 0;
  };

  const escapeHTML = value => String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  const sourceLabelFor = row =>
    row && (row.querySelector('.media-index-item-title, .media-index-item-outlet') || row);

  const copySourceTypography = (el, source) => {
    const cs = getComputedStyle(source);
    el.style.fontFamily = cs.fontFamily;
    el.style.fontWeight = cs.fontWeight;
    el.style.fontSize = cs.fontSize;
    el.style.letterSpacing = cs.letterSpacing;
    el.style.lineHeight = cs.lineHeight;
    el.style.textTransform = cs.textTransform;
    el.style.color = cs.color;
    el.style.textAlign = cs.textAlign;
    el.style.whiteSpace = cs.whiteSpace;
    el.style.textOverflow = cs.textOverflow;
  };

  TransferCardController.prototype._ensureCard = function () {
    if (this.card && this.card.classList.contains('transfer-band-v3')) return this.card;

    if (this.card) {
      try { this.card.remove(); } catch (err) {}
    }

    const card = document.createElement('div');
    card.className = 'transfer-card transfer-band-v3';
    card.setAttribute('aria-hidden', 'true');

    const label = document.createElement('span');
    label.className = 'transfer-band-label';
    card.appendChild(label);

    this.layer.appendChild(card);
    this.card = card;
    this.bandLabel = label;
    this.cardSourceText = label;
    this.cardTargetText = null;
    return card;
  };

  TransferCardController.prototype._restorePreviousLabel = function () {
    if (this.sourceLabel) {
      this.sourceLabel.classList.remove('media-index-item--transferring');
      this.sourceLabel = null;
    }
  };

  TransferCardController.prototype._measureBand = function (row) {
    if (!this.frame || !row) return null;

    const frameRect = this.frame.getBoundingClientRect();
    const frameCS = getComputedStyle(this.frame);
    const rowRect = row.getBoundingClientRect();
    const labelNode = sourceLabelFor(row);
    const labelRect = labelNode.getBoundingClientRect();
    const stage = this.frame.querySelector('.media-stage');
    const stageRect = stage ? stage.getBoundingClientRect() : frameRect;

    const topInset = px(frameCS.paddingTop);
    const targetInset = 18;

    return {
      frameRect,
      labelNode,
      start: {
        x: rowRect.left - frameRect.left,
        y: rowRect.top - frameRect.top,
        width: rowRect.width,
        height: rowRect.height,
        labelX: labelRect.left - rowRect.left,
        labelY: labelRect.top - rowRect.top,
        labelWidth: labelRect.width,
        labelHeight: labelRect.height
      },
      dock: {
        x: 0,
        y: topInset,
        width: frameRect.width,
        labelX: stageRect.left - frameRect.left + targetInset
      }
    };
  };

  TransferCardController.prototype._reserveBandSpace = function (height) {
    if (!this.frame) return;
    const reserve = Math.ceil(height + 10);
    this.frame.style.setProperty('--transfer-band-reserve', reserve + 'px');
    this.frame.classList.add('has-transfer-band');
  };

  TransferCardController.prototype._placeDockedBand = function (row, text) {
    const m = this._measureBand(row);
    if (!m) return;

    const card = this._ensureCard();
    const label = this.bandLabel;

    card.style.display = '';
    card.style.transform = '';
    card.style.left = '0px';
    card.style.top = m.dock.y + 'px';
    card.style.width = m.dock.width + 'px';
    card.style.height = m.start.height + 'px';

    label.textContent = text;
    copySourceTypography(label, m.labelNode);
    label.style.left = m.dock.labelX + 'px';
    label.style.top = m.start.labelY + 'px';
    label.style.width = Math.max(m.start.labelWidth, 1) + 'px';
    label.style.height = Math.max(m.start.labelHeight, 1) + 'px';
    label.style.opacity = '1';

    this._reserveBandSpace(m.start.height);
  };

  TransferCardController.prototype.resync = function () {
    if (this.dockedIndex === null || !this.dockedRow || !this.frame) return;
    this._cancelActive();
    const labelNode = sourceLabelFor(this.dockedRow);
    const text = labelNode ? labelNode.textContent.trim() : '';
    this._placeDockedBand(this.dockedRow, text);
  };

  TransferCardController.prototype.reset = function () {
    this._cancelActive();
    this._restorePreviousLabel();
    this.dockedIndex = null;
    this.dockedRow = null;
    if (this.card) this.card.style.display = 'none';
    if (this.frame) {
      this.frame.classList.remove('has-transfer-band');
      this.frame.style.removeProperty('--transfer-band-reserve');
    }
  };

  /* One object, one label, one font. A→B is vertical only. B→C expands the
     backing into a full-width band while the same label moves horizontally. */
  TransferCardController.prototype.transferTo = function (
    row,
    index,
    sourceText,
    _targetText,
    prepareContent,
    immediate
  ) {
    if (!this.frame || !row) return;

    this._cancelActive();
    this._restorePreviousLabel();

    /* Restoring the previous source can reflow the list, so measure only after
       the restore. */
    const sourceLabel = sourceLabelFor(row);
    const sourceCS = getComputedStyle(sourceLabel);
    const before = this._measureBand(row);
    if (!before) return;

    const token = this.generation;

    this.sourceLabel = row;
    this.dockedIndex = index;
    this.dockedRow = row;

    if (typeof prepareContent === 'function') prepareContent();
    if (this.railLive) this.railLive.textContent = sourceText;

    /* Content may have changed the stage geometry; recompute the destination
       while retaining the exact source-row dimensions and typography. */
    const after = this._measureBand(row) || before;
    const start = before.start;
    const dock = after.dock;

    row.classList.add('media-index-item--transferring');

    const card = this._ensureCard();
    const label = this.bandLabel;

    card.style.display = '';
    card.style.transform = '';
    card.style.left = start.x + 'px';
    card.style.top = start.y + 'px';
    card.style.width = start.width + 'px';
    card.style.height = start.height + 'px';

    label.textContent = sourceText;
    label.style.left = start.labelX + 'px';
    label.style.top = start.labelY + 'px';
    label.style.width = Math.max(start.labelWidth, 1) + 'px';
    label.style.height = Math.max(start.labelHeight, 1) + 'px';
    label.style.opacity = '1';
    label.style.fontFamily = sourceCS.fontFamily;
    label.style.fontWeight = sourceCS.fontWeight;
    label.style.fontSize = sourceCS.fontSize;
    label.style.letterSpacing = sourceCS.letterSpacing;
    label.style.lineHeight = sourceCS.lineHeight;
    label.style.textTransform = sourceCS.textTransform;
    label.style.color = sourceCS.color;
    label.style.textAlign = sourceCS.textAlign;
    label.style.whiteSpace = sourceCS.whiteSpace;
    label.style.textOverflow = sourceCS.textOverflow;

    const finish = () => {
      if (token !== this.generation) return;
      card.style.transform = '';
      card.style.left = '0px';
      card.style.top = dock.y + 'px';
      card.style.width = dock.width + 'px';
      card.style.height = start.height + 'px';
      label.style.left = dock.labelX + 'px';
      label.style.top = start.labelY + 'px';
      label.style.width = Math.max(start.labelWidth, 1) + 'px';
      label.style.height = Math.max(start.labelHeight, 1) + 'px';
      label.style.opacity = '1';
      this._reserveBandSpace(start.height);
      this.animations = [];
      this.timers = [];
    };

    if (immediate || TransferCardController.reducedMotion() || TransferCardController.stackedLayout()) {
      finish();
      return;
    }

    const dy = dock.y - start.y;
    const vDuration = TransferCardController.clamp(Math.abs(dy) * 0.35, 100, 220);

    const vAnim = card.animate(
      [
        { transform: 'translate(0px, 0px)' },
        { transform: 'translate(0px, ' + dy + 'px)' }
      ],
      {
        duration: vDuration,
        easing: TransferCardController.V_EASE,
        fill: 'forwards'
      }
    );
    this.animations = [vAnim];

    const phase1Timer = setTimeout(() => {
      if (token !== this.generation) return;

      card.style.top = dock.y + 'px';
      card.style.transform = '';
      try { vAnim.cancel(); } catch (err) {}

      const bandAnim = card.animate(
        [
          { left: start.x + 'px', width: start.width + 'px' },
          { left: '0px', width: dock.width + 'px' }
        ],
        {
          duration: TransferCardController.H_DURATION,
          easing: TransferCardController.H_EASE,
          fill: 'forwards'
        }
      );

      const labelAnim = label.animate(
        [
          { left: start.labelX + 'px' },
          { left: dock.labelX + 'px' }
        ],
        {
          duration: TransferCardController.H_DURATION,
          easing: TransferCardController.H_EASE,
          fill: 'forwards'
        }
      );

      this.animations = [bandAnim, labelAnim];

      const phase2Timer = setTimeout(() => {
        if (token !== this.generation) return;
        try { bandAnim.cancel(); labelAnim.cancel(); } catch (err) {}
        finish();
      }, TransferCardController.H_DURATION);

      this.timers = [phase2Timer];
    }, vDuration);

    this.timers = [phase1Timer];
  };

  [architectureTransfer, missionTransfer, mediaTransfer].forEach(controller => {
    if (!controller) return;
    if (controller.card && !controller.card.classList.contains('transfer-band-v3')) {
      try { controller.card.remove(); } catch (err) {}
      controller.card = null;
      controller.cardSourceText = null;
      controller.cardTargetText = null;
    }
    if (controller.dockedRow) controller.resync();
  });

  /* ---------- UPDATES: title rubricator + cyclic catalogue ---------- */
  const mediaList = document.getElementById('mediaList');
  const mediaStage = document.getElementById('mediaStage');
  const mediaIdle = document.getElementById('mediaIdle');
  const mediaArticlePane = document.getElementById('mediaArticlePane');
  const mediaArticleScroll = document.getElementById('mediaArticleScroll');
  const mediaTitle = document.getElementById('mediaTitle');
  const mediaHeroImage = document.getElementById('mediaHeroImage');
  const mediaHeroAmbient = document.getElementById('mediaHeroAmbient');
  const mediaHeroFallback = document.getElementById('mediaHeroFallback');
  const mediaText = document.getElementById('mediaText');

  let catalogueAnim = null;
  let catalogueTimer = null;
  let catalogueGeneration = 0;

  const cancelCatalogueMotion = () => {
    catalogueGeneration++;
    if (catalogueTimer) clearTimeout(catalogueTimer);
    catalogueTimer = null;
    if (catalogueAnim) {
      try { catalogueAnim.cancel(); } catch (err) {}
    }
    catalogueAnim = null;
    if (mediaList) {
      mediaList.style.transform = '';
      mediaList.classList.remove('is-rolling');
    }
  };

  const setSelectedUpdate = index => {
    if (!mediaList) return;
    mediaList.querySelectorAll('button[data-media-index]').forEach(button => {
      const selected = Number(button.dataset.mediaIndex) === index;
      button.classList.toggle('is-active', selected);
      button.setAttribute('aria-current', selected ? 'true' : 'false');
    });
  };

  const renderCatalogue = () => {
    if (!mediaList || !Array.isArray(MEDIA_RELEASES)) return;
    mediaList.innerHTML = '';

    MEDIA_RELEASES.forEach((item, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.mediaIndex = String(index);
      button.className = 'media-index-item media-update-rubricator';
      button.innerHTML =
        '<span class="media-index-item-title">' + escapeHTML(item.title) + '</span>' +
        '<span class="media-index-item-arrow" aria-hidden="true">↗</span>';
      button.addEventListener('click', () => selectUpdate(index));
      mediaList.appendChild(button);
    });
  };

  const updateGeo = (item, index) => {
    if (item && item.outlet === '24KZ') return 'UAE';
    return (MEDIA_GEOTAGS[index] || '').replace(/\s*·\s*/g, ', ');
  };

  const showUpdateContent = index => {
    if (!Array.isArray(MEDIA_RELEASES)) return;
    const item = MEDIA_RELEASES[index];
    if (!item || !mediaStage || !mediaArticlePane || !mediaText) return;

    setSelectedUpdate(index);
    mediaStage.classList.add('has-article');
    mediaIdle?.classList.add('hidden');
    mediaArticlePane.classList.remove('hidden');
    if (mediaTitle) mediaTitle.textContent = item.title;

    const imageUrl = item.imageData ||
      `https://drive.google.com/thumbnail?id=${encodeURIComponent(item.fileId)}&sz=w1800`;

    if (mediaHeroFallback) {
      mediaHeroFallback.textContent = item.outlet;
      mediaHeroFallback.classList.remove('hidden');
    }

    if (mediaHeroImage) {
      mediaHeroImage.alt = `${item.outlet}: ${item.title}`;
      mediaHeroImage.onload = () => mediaHeroFallback?.classList.add('hidden');
      mediaHeroImage.onerror = () => {
        mediaHeroImage.removeAttribute('src');
        mediaHeroAmbient?.removeAttribute('src');
        mediaHeroFallback?.classList.remove('hidden');
      };
      mediaHeroImage.src = imageUrl;
    }
    if (mediaHeroAmbient) mediaHeroAmbient.src = imageUrl;

    mediaText.innerHTML = item.articleHtml ||
      `<article class="media-article">${(item.text || []).map(p => `<p>${p}</p>`).join('')}</article>`;

    const articleRoot = mediaText.querySelector('.media-article') || mediaText;
    const geo = updateGeo(item, index);
    const metadata = [item.date, geo, item.outlet].filter(Boolean).join(', ');
    articleRoot.insertAdjacentHTML(
      'afterbegin',
      `<p class="media-article-dateline">${escapeHTML(metadata)}</p>`
    );

    if (item.url) {
      let host = item.url;
      try { host = new URL(item.url).hostname.replace(/^www\./, ''); } catch (err) {}
      articleRoot.insertAdjacentHTML(
        'beforeend',
        `<p class="media-article-source"><a class="media-article-source-link" href="${escapeHTML(item.url)}" target="_blank" rel="noopener">Read the original on ${escapeHTML(host)} ↗</a></p>`
      );
    }

    if (mediaArticleScroll) mediaArticleScroll.scrollTop = 0;
    if (typeof triggerBodyEnter === 'function') triggerBodyEnter('#mediaText');
  };

  const transferSelectedUpdate = (button, index) => {
    const item = Array.isArray(MEDIA_RELEASES) ? MEDIA_RELEASES[index] : null;
    if (!item || !button) return;

    mediaTransfer.transferTo(
      button,
      index,
      item.title,
      item.title,
      () => showUpdateContent(index),
      false
    );
  };

  function selectUpdate(index) {
    const item = Array.isArray(MEDIA_RELEASES) ? MEDIA_RELEASES[index] : null;
    if (!item || !mediaList) return;

    cancelCatalogueMotion();

    mediaTransfer._cancelActive();
    mediaTransfer._restorePreviousLabel();
    if (mediaTransfer.card) mediaTransfer.card.style.display = 'none';
    if (mediaTransfer.frame) {
      mediaTransfer.frame.classList.remove('has-transfer-band');
      mediaTransfer.frame.style.removeProperty('--transfer-band-reserve');
    }

    let button = mediaList.querySelector(`button[data-media-index="${index}"]`);
    if (!button) return;

    const rows = Array.from(mediaList.children);
    const position = rows.indexOf(button);

    if (position <= 0 || TransferCardController.reducedMotion()) {
      if (position > 0) {
        rows.slice(0, position).forEach(row => mediaList.appendChild(row));
        button = mediaList.querySelector(`button[data-media-index="${index}"]`);
      }
      transferSelectedUpdate(button, index);
      return;
    }

    const listRect = mediaList.getBoundingClientRect();
    const rowRect = button.getBoundingClientRect();
    const dy = rowRect.top - listRect.top;
    const token = ++catalogueGeneration;

    mediaList.classList.add('is-rolling');
    catalogueAnim = mediaList.animate(
      [
        { transform: 'translateY(0px)' },
        { transform: `translateY(${-dy}px)` }
      ],
      {
        duration: 300,
        easing: 'cubic-bezier(.22,1,.36,1)',
        fill: 'forwards'
      }
    );

    catalogueTimer = setTimeout(() => {
      if (token !== catalogueGeneration) return;

      try { catalogueAnim.cancel(); } catch (err) {}
      catalogueAnim = null;
      catalogueTimer = null;

      rows.slice(0, position).forEach(row => mediaList.appendChild(row));
      mediaList.style.transform = '';
      mediaList.classList.remove('is-rolling');

      const selected = mediaList.querySelector(`button[data-media-index="${index}"]`);
      transferSelectedUpdate(selected, index);
    }, 300);
  }

  const resetUpdatesCatalogue = () => {
    if (!mediaList) return;

    cancelCatalogueMotion();
    mediaTransfer.reset();
    renderCatalogue();
    setSelectedUpdate(-1);
    mediaStage?.classList.remove('has-article');
    mediaIdle?.classList.remove('hidden');
    mediaArticlePane?.classList.add('hidden');
    mediaHeroImage?.removeAttribute('src');
    mediaHeroAmbient?.removeAttribute('src');
    if (mediaTitle) mediaTitle.textContent = 'Select Update';
    if (mediaArticleScroll) mediaArticleScroll.scrollTop = 0;

    requestAnimationFrame(() => {
      if (window.mediaSilverWorldMap) window.mediaSilverWorldMap.resize();
    });
  };

  if (mediaList && Array.isArray(MEDIA_RELEASES)) {
    renderCatalogue();
    window.resetMediaExplorer = resetUpdatesCatalogue;
    window.showMediaArticle = selectUpdate;
    resetUpdatesCatalogue();
  }

  /* Mission uses the same visual/rubricator treatment as Updates, while keeping
     its own chapter content and non-cyclic chapter order. */
  const missionList = document.getElementById('missionList');
  if (missionList) {
    missionList.querySelectorAll('.mission-index-item').forEach(button => {
      button.classList.add('media-update-rubricator');
    });
  }

  /* ---------- SYSTEM ARCHITECTURE content ---------- */
  const architectureList = document.getElementById('oryxList');
  const architectureStage = document.getElementById('oryxStage');
  const architectureText = document.getElementById('oryxText');
  const architectureTitle = document.getElementById('oryxTitle');

  const architectureEntries = [
    {
      id: 'sys-rocketship',
      navTitle: '1. ORYX ROCKETSHIP',
      image: 'assets/images/system/oryx-rocketship.svg',
      imageAlt: 'Oryx Rocketship',
      html: `
        <div class="architecture-spec-copy">
          <p class="architecture-spec-lead">Reusable first and second stages</p>
          <div class="architecture-spec-group">
            <div class="architecture-spec-label">PAYLOAD MASS</div>
            <p>LEO - H=200 км, i=51,6°</p>
            <p>up to 5t fully reusable</p>
          </div>
          <div class="architecture-spec-group">
            <div class="architecture-spec-label">PROPULSION</div>
            <p>First stage 5 engines × 1,000 kN / 225,000 lbf</p>
            <p>Second stage: 5 engines × 200 kN / 45,000 lbf</p>
          </div>
        </div>`
    },
    {
      id: 'stage-d3',
      navTitle: '2. D3 CARGO SPACESHIP',
      image: 'assets/images/oryx-orbit-2.png',
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
      id: 'aspire-launcher',
      navTitle: '3. ASPIRE LAUNCHER',
      image: 'assets/images/system/aspire-launcher.svg',
      imageAlt: 'Aspire Launcher',
      html: `
        <div class="architecture-spec-copy">
          <p class="architecture-spec-lead architecture-spec-kicker">R1 TWO-STAGE MEDIUM-LIFT LAUNCHER</p>
          <p>Two-stage medium-lift space launch vehicle</p>
          <div class="architecture-spec-group">
            <p>LEO - H=200 км, i=51,6°</p>
            <p>15 t reusable, 17 t expendable</p>
          </div>
          <p>Reusable first stage and fairing leading to lower operating costs</p>
          <ul class="architecture-spec-list">
            <li>Green methane-oxygen engines optimized for reusability</li>
            <li>Composite second stage with high mass ratio</li>
            <li>First in class reusable fairing for launching satellites</li>
          </ul>
        </div>`
    },
    {
      id: 'stage-booster',
      navTitle: 'R1V5 BOOSTER',
      html: ''
    },
    {
      id: 'infrastructure',
      navTitle: 'GROUND INFRASTRUCTURE',
      html: ''
    },
    {
      id: 'location-kazakhstan',
      navTitle: 'NEW SPACEPORT & PROPULSION TEST FACILITY, KAZAKHSTAN',
      html: ''
    },
    {
      id: 'location-uae',
      navTitle: 'HQ & MANUFACTURING FACILITY, UNITED ARAB EMIRATES',
      html: ''
    },
    {
      id: 'location-varna',
      navTitle: 'R&D OFFICE',
      html: ''
    }
  ];

  const showArchitectureEntry = index => {
    const entry = architectureEntries[index];
    if (!entry || !architectureText) return;

    architectureStage?.classList.add('has-article');
    if (architectureTitle) architectureTitle.textContent = entry.navTitle;

    const visual = entry.image
      ? `<figure class="architecture-spec-visual"><img src="${escapeHTML(entry.image)}" alt="${escapeHTML(entry.imageAlt || entry.navTitle)}"></figure>`
      : '';

    architectureText.innerHTML =
      `<div class="architecture-spec-layout">${visual}${entry.html || ''}</div>`;

    if (architectureList) {
      architectureList.querySelectorAll('button[data-architecture-index]').forEach(button => {
        const active = Number(button.dataset.architectureIndex) === index;
        button.classList.toggle('is-active', active);
        button.setAttribute('aria-current', active ? 'true' : 'false');
      });
    }

    if (typeof triggerBodyEnter === 'function') triggerBodyEnter('#oryxText');
    const scroll = architectureStage?.querySelector('.media-article-scroll');
    if (scroll) scroll.scrollTop = 0;
  };

  const transferArchitectureEntry = (button, index, immediate) => {
    const entry = architectureEntries[index];
    if (!entry || !button) return;

    architectureTransfer.transferTo(
      button,
      index,
      entry.navTitle,
      entry.navTitle,
      () => showArchitectureEntry(index),
      !!immediate
    );
  };

  const renderArchitectureCatalogue = () => {
    if (!architectureList) return;

    architectureTransfer.reset();
    architectureList.innerHTML = '';

    architectureEntries.forEach((entry, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.architectureIndex = String(index);
      button.className = 'media-index-item architecture-rubricator';
      button.innerHTML =
        `<span class="media-index-item-outlet taxonomy-index-name">${escapeHTML(entry.navTitle)}</span>` +
        '<span class="media-index-item-arrow" aria-hidden="true">↗</span>';
      button.addEventListener('click', () => transferArchitectureEntry(button, index, false));
      architectureList.appendChild(button);
    });

    const first = architectureList.querySelector('button[data-architecture-index="0"]');
    if (first) transferArchitectureEntry(first, 0, true);
  };

  if (architectureList) renderArchitectureCatalogue();

  window.addEventListener('resize', () => {
    requestAnimationFrame(() => {
      architectureTransfer.resync();
      missionTransfer.resync();
      mediaTransfer.resync();
    });
  });
})();
