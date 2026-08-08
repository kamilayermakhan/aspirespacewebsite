/* Aspire refinement pass v9 — radio-style Mission/Updates transfer state. */
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

  /* Mission + Updates are true master/detail lists:
     - only the CURRENT source row is visually empty while its title is docked;
     - when another item is selected, the previous source title returns to its
       original row before the new title begins its transfer;
     - no persistent evacuated source slots. */
  const installRadioSourceState = controller => {
    if (!controller) return;

    controller._restorePreviousLabel = function () {
      const row = this.sourceLabel;
      if (!row) return;

      row.classList.remove('media-index-item--transferring');
      row.classList.remove('media-index-item--evacuated');
      if (this.evacuatedRows && typeof this.evacuatedRows.delete === 'function') {
        this.evacuatedRows.delete(row);
      }
      this.sourceLabel = null;
    };

    /* Clear stale v7/v8 state left in the current DOM before the user starts a
       new interaction. This does not alter layout/order. */
    controller.frame?.querySelectorAll('.media-index-item--evacuated').forEach(row => {
      row.classList.remove('media-index-item--evacuated');
    });
    if (controller.evacuatedRows && typeof controller.evacuatedRows.clear === 'function') {
      controller.evacuatedRows.clear();
    }
  };

  if (typeof missionTransfer !== 'undefined') installRadioSourceState(missionTransfer);
  if (typeof mediaTransfer !== 'undefined') installRadioSourceState(mediaTransfer);

  /* Keep the Architecture controller untouched here. Its behavior is managed
     independently by the architecture refinement layer. */

  if (typeof TransferCardController !== 'undefined') {
    const proto = TransferCardController.prototype;
    const previousMeasure = proto._measureBand;

    /* Dock the moving title to the real text column, using the article scroll
       box + body padding instead of a fixed inset. */
    proto._measureBand = function (row) {
      const measured = previousMeasure.call(this, row);
      if (!measured || !this.frame) return measured;

      const scroll = this.frame.querySelector('.media-article-scroll');
      const body = this.frame.querySelector('.media-article-body');
      if (!scroll) return measured;

      const scrollRect = scroll.getBoundingClientRect();
      const scrollCS = getComputedStyle(scroll);
      const bodyCS = body ? getComputedStyle(body) : null;
      const bodyPadding = bodyCS ? px(bodyCS.paddingLeft) : 0;

      measured.dock.labelX =
        scrollRect.left - measured.frameRect.left +
        px(scrollCS.paddingLeft) +
        bodyPadding;

      return measured;
    };
  }

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

  const updateSource = item => {
    if (!item) return '';
    return item.imageData || (item.fileId
      ? `https://drive.google.com/thumbnail?id=${encodeURIComponent(item.fileId)}&sz=w1800`
      : '');
  };

  /* Eager, non-blocking preload deck. */
  const preloadDeck = document.createElement('div');
  preloadDeck.id = 'aspire-media-preload-deck';
  preloadDeck.setAttribute('aria-hidden', 'true');
  preloadDeck.style.cssText = [
    'position:fixed',
    'left:-10px',
    'top:-10px',
    'width:1px',
    'height:1px',
    'overflow:hidden',
    'opacity:.001',
    'pointer-events:none',
    'z-index:-1'
  ].join(';');

  const seenSources = new Set();
  const addPreload = src => {
    if (!src || seenSources.has(src)) return;
    seenSources.add(src);
    const image = document.createElement('img');
    image.src = src;
    image.alt = '';
    image.loading = 'eager';
    image.decoding = 'async';
    try { image.fetchPriority = 'high'; } catch (err) {}
    image.style.cssText = 'display:block;width:1px;height:1px;object-fit:cover;';
    preloadDeck.appendChild(image);
  };

  try {
    if (Array.isArray(MEDIA_RELEASES)) {
      MEDIA_RELEASES.forEach(item => addPreload(updateSource(item)));
    }
  } catch (err) {}

  [
    'assets/images/system/R1V5.avif',
    'assets/images/system/S2_5.avif',
    'assets/images/system/Fairings_2.avif'
  ].forEach(addPreload);

  document.body.appendChild(preloadDeck);

  const setSelected = index => {
    if (!mediaList) return;
    mediaList.querySelectorAll('button[data-media-index]').forEach(button => {
      const active = Number(button.dataset.mediaIndex) === index;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-current', active ? 'true' : 'false');
    });
  };

  const geoFor = (item, index) => {
    if (item && item.outlet === '24KZ') return 'UAE';
    try {
      return (MEDIA_GEOTAGS[index] || '').replace(/\s*·\s*/g, ', ');
    } catch (err) {
      return '';
    }
  };

  const showStableUpdate = index => {
    if (!Array.isArray(MEDIA_RELEASES)) return;
    const item = MEDIA_RELEASES[index];
    if (!item || !mediaStage || !mediaArticlePane || !mediaText) return;

    setSelected(index);
    mediaStage.classList.add('has-article');
    mediaIdle?.classList.add('hidden');
    mediaArticlePane.classList.remove('hidden');
    if (mediaTitle) mediaTitle.textContent = item.title;

    const src = updateSource(item);
    if (mediaHeroFallback) {
      mediaHeroFallback.textContent = item.outlet || 'ASPIRE SPACE';
      mediaHeroFallback.classList.toggle('hidden', !!src);
    }

    if (mediaHeroImage) {
      mediaHeroImage.alt = `${item.outlet || 'Aspire Space'}: ${item.title}`;
      mediaHeroImage.onload = () => mediaHeroFallback?.classList.add('hidden');
      mediaHeroImage.onerror = () => {
        mediaHeroImage.removeAttribute('src');
        mediaHeroFallback?.classList.remove('hidden');
      };
      if (src) mediaHeroImage.src = src;
      else mediaHeroImage.removeAttribute('src');
    }

    mediaHeroAmbient?.removeAttribute('src');

    mediaText.innerHTML = item.articleHtml ||
      `<article class="media-article">${(item.text || []).map(p => `<p>${p}</p>`).join('')}</article>`;

    const articleRoot = mediaText.querySelector('.media-article') || mediaText;
    const metadata = [item.date, geoFor(item, index), item.outlet].filter(Boolean).join(', ');
    articleRoot.insertAdjacentHTML(
      'afterbegin',
      `<p class="media-article-dateline">${esc(metadata)}</p>`
    );

    if (item.url) {
      let host = item.url;
      try { host = new URL(item.url).hostname.replace(/^www\./, ''); } catch (err) {}
      articleRoot.insertAdjacentHTML(
        'beforeend',
        `<p class="media-article-source"><a class="media-article-source-link" href="${esc(item.url)}" target="_blank" rel="noopener">Read the original on ${esc(host)} ↗</a></p>`
      );
    }

    mediaArticleScroll && (mediaArticleScroll.scrollTop = 0);
    if (typeof window.triggerBodyEnter === 'function') window.triggerBodyEnter('#mediaText');
  };

  const selectStableUpdate = index => {
    if (!mediaList || !Array.isArray(MEDIA_RELEASES)) return;
    const item = MEDIA_RELEASES[index];
    const button = mediaList.querySelector(`button[data-media-index="${index}"]`);
    if (!item || !button || typeof mediaTransfer === 'undefined') return;

    /* mediaTransfer.transferTo() first restores the previous source row through
       the instance-level radio-state hook above, then hides/transfers the newly
       selected row. Thus exactly one source position is empty at a time. */
    mediaTransfer.transferTo(
      button,
      index,
      item.title,
      item.title,
      () => showStableUpdate(index),
      false
    );
  };

  if (mediaList) {
    mediaList.addEventListener('click', event => {
      const button = event.target.closest('button[data-media-index]');
      if (!button || !mediaList.contains(button)) return;

      event.preventDefault();
      event.stopImmediatePropagation();
      const index = Number(button.dataset.mediaIndex);
      if (Number.isFinite(index)) selectStableUpdate(index);
    }, true);
  }

  window.showMediaArticle = selectStableUpdate;

  const style = document.createElement('style');
  style.id = 'aspire-refinement-v9-style';
  style.textContent = `
    /* Only the currently transferred source row is blank. Previous rows are
       restored by JS before the new transfer begins. */
    #missionWorkspace .media-index-item--transferring .media-index-item-title,
    #missionWorkspace .media-index-item--transferring .media-index-item-outlet,
    #missionWorkspace .media-index-item--transferring .media-index-item-arrow,
    #mediaWorkspace .media-index-item--transferring .media-index-item-title,
    #mediaWorkspace .media-index-item--transferring .media-index-item-outlet,
    #mediaWorkspace .media-index-item--transferring .media-index-item-arrow {
      visibility: hidden !important;
    }

    #missionWorkspace .media-index-item--evacuated .media-index-item-title,
    #missionWorkspace .media-index-item--evacuated .media-index-item-outlet,
    #missionWorkspace .media-index-item--evacuated .media-index-item-arrow,
    #mediaWorkspace .media-index-item--evacuated .media-index-item-title,
    #mediaWorkspace .media-index-item--evacuated .media-index-item-outlet,
    #mediaWorkspace .media-index-item--evacuated .media-index-item-arrow {
      visibility: visible !important;
    }

    #mediaArticlePane .media-article-visual {
      width: 100% !important;
      height: auto !important;
      min-height: 0 !important;
      max-height: none !important;
    }
    #mediaArticlePane #mediaHeroImage {
      display: block !important;
      width: 100% !important;
      height: auto !important;
      max-height: none !important;
      object-fit: contain !important;
    }
  `;
  document.head.appendChild(style);
})();
