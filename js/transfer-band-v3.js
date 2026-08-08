/* Aspire interaction correction — full-width Transfer Band + Updates catalogue.
 * Loaded after script.js so it deliberately replaces only the interaction layer
 * introduced by TransferCardController, leaving the site's data/content intact.
 */
(function () {
  'use strict';

  if (typeof TransferCardController === 'undefined') return;

  const px = value => {
    const n = parseFloat(value);
    return Number.isFinite(n) ? n : 0;
  };

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

  /* One label only. There is no source/target text pair and therefore no
     typography morph or crossfade. */
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

  TransferCardController.prototype._measureBand = function (row) {
    if (!this.frame || !this.rail || !row) return null;

    const frameRect = this.frame.getBoundingClientRect();
    const rowRect = row.getBoundingClientRect();
    const labelNode = sourceLabelFor(row);
    const labelRect = labelNode.getBoundingClientRect();
    const railRect = this.rail.getBoundingClientRect();
    const railCS = getComputedStyle(this.rail);

    return {
      frameRect,
      rowRect,
      labelNode,
      labelRect,
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
        y: railRect.top - frameRect.top,
        width: frameRect.width,
        labelX: railRect.left - frameRect.left + px(railCS.paddingLeft)
      }
    };
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
    label.style.width = m.start.labelWidth + 'px';
    label.style.height = m.start.labelHeight + 'px';
    label.style.opacity = '1';
  };

  TransferCardController.prototype.resync = function () {
    if (this.dockedIndex === null || !this.dockedRow || !this.frame || !this.rail) return;
    this._cancelActive();
    const labelNode = sourceLabelFor(this.dockedRow);
    const text = labelNode ? labelNode.textContent.trim() : '';
    this._placeDockedBand(this.dockedRow, text);
  };

  /* Final interaction model:
     A -> B: the source card rises vertically without changing shape/text.
     B -> C: the single faceted backing grows into one full-width band while
             the SAME label slides horizontally to the right-side heading rail.
     Font family, size, weight, tracking, line-height and label box are copied
     from the source and never morph. */
  TransferCardController.prototype.transferTo = function (
    row,
    index,
    sourceText,
    _targetText,
    prepareContent,
    immediate
  ) {
    if (!this.frame || !this.rail || !row) return;

    const sourceRowRect = row.getBoundingClientRect();
    const sourceLabel = sourceLabelFor(row);
    const sourceLabelRect = sourceLabel.getBoundingClientRect();
    const sourceCS = getComputedStyle(sourceLabel);

    this._cancelActive();
    const token = this.generation;

    this._restorePreviousLabel();
    row.classList.add('media-index-item--transferring');
    this.sourceLabel = row;
    this.dockedIndex = index;
    this.dockedRow = row;

    if (typeof prepareContent === 'function') prepareContent();
    if (this.railLive) this.railLive.textContent = sourceText;

    const frameRect = this.frame.getBoundingClientRect();
    const railRect = this.rail.getBoundingClientRect();
    const railCS = getComputedStyle(this.rail);

    const start = {
      x: sourceRowRect.left - frameRect.left,
      y: sourceRowRect.top - frameRect.top,
      width: sourceRowRect.width,
      height: sourceRowRect.height,
      labelX: sourceLabelRect.left - sourceRowRect.left,
      labelY: sourceLabelRect.top - sourceRowRect.top,
      labelWidth: sourceLabelRect.width,
      labelHeight: sourceLabelRect.height
    };

    const dock = {
      x: 0,
      y: railRect.top - frameRect.top,
      width: frameRect.width,
      labelX: railRect.left - frameRect.left + px(railCS.paddingLeft)
    };

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
    label.style.width = start.labelWidth + 'px';
    label.style.height = start.labelHeight + 'px';
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
      label.style.width = start.labelWidth + 'px';
      label.style.height = start.labelHeight + 'px';
      label.style.opacity = '1';
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

  /* UPDATES: article titles become rubricator headings. The source/outlet moves
     into the article metadata line after date + geography. The index behaves as
     a cyclic card catalogue. */
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

  if (!mediaList || !Array.isArray(MEDIA_RELEASES)) return;

  let catalogueAnim = null;
  let catalogueTimer = null;
  let catalogueGeneration = 0;

  const escapeHTML = value => String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  const cancelCatalogueMotion = () => {
    catalogueGeneration++;
    if (catalogueTimer) clearTimeout(catalogueTimer);
    catalogueTimer = null;
    if (catalogueAnim) {
      try { catalogueAnim.cancel(); } catch (err) {}
    }
    catalogueAnim = null;
    mediaList.style.transform = '';
    mediaList.classList.remove('is-rolling');
  };

  const setSelectedUpdate = index => {
    mediaList.querySelectorAll('button[data-media-index]').forEach(button => {
      const selected = Number(button.dataset.mediaIndex) === index;
      button.classList.toggle('is-active', selected);
      button.setAttribute('aria-current', selected ? 'true' : 'false');
    });
  };

  const renderCatalogue = () => {
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
    const item = MEDIA_RELEASES[index];
    if (!item) return;

    setSelectedUpdate(index);
    mediaStage.classList.add('has-article');
    mediaIdle.classList.add('hidden');
    mediaArticlePane.classList.remove('hidden');
    mediaTitle.textContent = item.title;

    const imageUrl = item.imageData ||
      `https://drive.google.com/thumbnail?id=${encodeURIComponent(item.fileId)}&sz=w1800`;

    mediaHeroFallback.textContent = item.outlet;
    mediaHeroFallback.classList.remove('hidden');
    mediaHeroImage.alt = `${item.outlet}: ${item.title}`;
    mediaHeroImage.onload = () => mediaHeroFallback.classList.add('hidden');
    mediaHeroImage.onerror = () => {
      mediaHeroImage.removeAttribute('src');
      mediaHeroAmbient.removeAttribute('src');
      mediaHeroFallback.classList.remove('hidden');
    };
    mediaHeroImage.src = imageUrl;
    mediaHeroAmbient.src = imageUrl;

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

    mediaArticleScroll.scrollTop = 0;
    if (typeof triggerBodyEnter === 'function') triggerBodyEnter('#mediaText');
  };

  const transferSelectedUpdate = (button, index) => {
    const item = MEDIA_RELEASES[index];
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
    const item = MEDIA_RELEASES[index];
    if (!item) return;

    cancelCatalogueMotion();

    mediaTransfer._cancelActive();
    mediaTransfer._restorePreviousLabel();
    if (mediaTransfer.card) mediaTransfer.card.style.display = 'none';

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
    cancelCatalogueMotion();
    mediaTransfer.reset();
    renderCatalogue();
    setSelectedUpdate(-1);
    mediaStage.classList.remove('has-article');
    mediaIdle.classList.remove('hidden');
    mediaArticlePane.classList.add('hidden');
    mediaHeroImage.removeAttribute('src');
    mediaHeroAmbient.removeAttribute('src');
    mediaTitle.textContent = 'Select Update';
    mediaArticleScroll.scrollTop = 0;

    requestAnimationFrame(() => {
      if (window.mediaSilverWorldMap) window.mediaSilverWorldMap.resize();
    });
  };

  renderCatalogue();
  window.resetMediaExplorer = resetUpdatesCatalogue;
  window.showMediaArticle = selectUpdate;
  resetUpdatesCatalogue();
})();
