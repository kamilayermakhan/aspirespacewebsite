/* Aspire refinement pass v10 — rolodex top-slot transfer for all explorers. */
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

  const stripOrdinal = value => String(value || '').replace(/^\s*\d+\.\s*/, '');

  /* ------------------------------------------------------------------
     Shared source state.
     Only the currently docked item is absent from the catalogue. Before a
     different item starts moving, the previous title is restored. The list
     itself then scrolls like a card catalogue until the newly selected row is
     physically the first visible row; only then does that title leave to the
     right, so the FIRST VISIBLE ROW is the empty source slot.
     ------------------------------------------------------------------ */
  const restoreSourceNormally = controller => {
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

    controller.frame?.querySelectorAll('.media-index-item--evacuated').forEach(row => {
      row.classList.remove('media-index-item--evacuated');
    });
    if (controller.evacuatedRows && typeof controller.evacuatedRows.clear === 'function') {
      controller.evacuatedRows.clear();
    }
  };

  if (typeof architectureTransfer !== 'undefined') restoreSourceNormally(architectureTransfer);
  if (typeof missionTransfer !== 'undefined') restoreSourceNormally(missionTransfer);
  if (typeof mediaTransfer !== 'undefined') restoreSourceNormally(mediaTransfer);

  const clearDockBeforeRoll = controller => {
    if (!controller) return;
    try { controller._cancelActive(); } catch (err) {}
    try { controller._restorePreviousLabel(); } catch (err) {}
    controller.dockedIndex = null;
    controller.dockedRow = null;
    if (controller.card) controller.card.style.display = 'none';
    if (controller.frame) {
      controller.frame.classList.remove('has-transfer-band');
      controller.frame.style.removeProperty('--transfer-band-reserve');
    }
  };

  const easeOutQuart = t => 1 - Math.pow(1 - t, 4);

  const animateListToTop = (list, row, generationRef) => new Promise(resolve => {
    if (!list || !row) { resolve(false); return; }

    const rowRect = row.getBoundingClientRect();
    const listRect = list.getBoundingClientRect();
    const rowHeight = Math.max(1, rowRect.height);

    /* Give the catalogue enough trailing space for even the last record to
       reach the top slot without changing the order of the records. */
    const reserve = Math.max(14, list.clientHeight - rowHeight + 14);
    list.style.paddingBottom = reserve + 'px';
    void list.offsetHeight;

    const from = list.scrollTop;
    const unclamped = from + (rowRect.top - listRect.top);
    const maxScroll = Math.max(0, list.scrollHeight - list.clientHeight);
    const target = Math.max(0, Math.min(maxScroll, unclamped));
    const distance = target - from;

    if (Math.abs(distance) < 1) {
      list.scrollTop = target;
      resolve(true);
      return;
    }

    const duration = Math.max(150, Math.min(340, Math.abs(distance) * 0.42));
    const start = performance.now();
    const token = generationRef.value;

    const tick = now => {
      if (token !== generationRef.value) { resolve(false); return; }
      const t = Math.min(1, (now - start) / duration);
      list.scrollTop = from + distance * easeOutQuart(t);
      if (t < 1) requestAnimationFrame(tick);
      else {
        list.scrollTop = target;
        resolve(true);
      }
    };
    requestAnimationFrame(tick);
  });

  const installRolodex = ({ list, controller, selector, onTop }) => {
    if (!list || !controller) return;
    const generation = { value: 0 };

    list.addEventListener('click', event => {
      const button = event.target.closest(selector);
      if (!button || !list.contains(button)) return;

      if (button.dataset.rolodexBypass === '1') {
        delete button.dataset.rolodexBypass;
        return;
      }

      event.preventDefault();
      event.stopImmediatePropagation();
      generation.value += 1;
      const token = generation.value;

      clearDockBeforeRoll(controller);
      list.querySelectorAll('.is-active').forEach(el => el.classList.remove('is-active'));

      animateListToTop(list, button, generation).then(ok => {
        if (!ok || token !== generation.value) return;
        if (typeof onTop === 'function') {
          onTop(button);
        } else {
          button.dataset.rolodexBypass = '1';
          button.click();
        }
      });
    }, true);
  };

  /* ------------------------------------------------------------------
     Align the docked label to the actual text column for all three explorers.
     ------------------------------------------------------------------ */
  if (typeof TransferCardController !== 'undefined') {
    const proto = TransferCardController.prototype;
    const baseMeasure = proto._measureBand;
    proto._measureBand = function (row) {
      const measured = baseMeasure.call(this, row);
      if (!measured || !this.frame) return measured;
      const scroll = this.frame.querySelector('.media-article-scroll');
      const body = this.frame.querySelector('.media-article-body');
      if (!scroll) return measured;
      const scrollRect = scroll.getBoundingClientRect();
      const scrollCS = getComputedStyle(scroll);
      const bodyCS = body ? getComputedStyle(body) : null;
      measured.dock.labelX =
        scrollRect.left - measured.frameRect.left +
        px(scrollCS.paddingLeft) +
        (bodyCS ? px(bodyCS.paddingLeft) : 0);
      return measured;
    };
  }

  /* ------------------------------------------------------------------
     UPDATES: content rendering without the old DOM-rotation routine.
     ------------------------------------------------------------------ */
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

  const updateSource = item => item
    ? (item.imageData || (item.fileId
      ? `https://drive.google.com/thumbnail?id=${encodeURIComponent(item.fileId)}&sz=w1800`
      : ''))
    : '';

  const geoFor = (item, index) => {
    if (item && item.outlet === '24KZ') return 'UAE';
    try { return (MEDIA_GEOTAGS[index] || '').replace(/\s*·\s*/g, ', '); }
    catch (err) { return ''; }
  };

  const setSelectedUpdate = index => {
    mediaList?.querySelectorAll('button[data-media-index]').forEach(button => {
      const active = Number(button.dataset.mediaIndex) === index;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-current', active ? 'true' : 'false');
    });
  };

  const showUpdate = index => {
    if (!Array.isArray(MEDIA_RELEASES)) return;
    const item = MEDIA_RELEASES[index];
    if (!item || !mediaStage || !mediaArticlePane || !mediaText) return;

    setSelectedUpdate(index);
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
    articleRoot.insertAdjacentHTML('afterbegin', `<p class="media-article-dateline">${esc(metadata)}</p>`);

    if (item.url) {
      let host = item.url;
      try { host = new URL(item.url).hostname.replace(/^www\./, ''); } catch (err) {}
      articleRoot.insertAdjacentHTML(
        'beforeend',
        `<p class="media-article-source"><a class="media-article-source-link" href="${esc(item.url)}" target="_blank" rel="noopener">Read the original on ${esc(host)} ↗</a></p>`
      );
    }

    if (mediaArticleScroll) mediaArticleScroll.scrollTop = 0;
    if (typeof window.triggerBodyEnter === 'function') window.triggerBodyEnter('#mediaText');
  };

  const transferUpdate = button => {
    const index = Number(button.dataset.mediaIndex);
    const item = Array.isArray(MEDIA_RELEASES) ? MEDIA_RELEASES[index] : null;
    if (!item || typeof mediaTransfer === 'undefined') return;
    mediaTransfer.transferTo(
      button,
      index,
      item.title,
      item.title,
      () => showUpdate(index),
      false
    );
  };

  if (mediaList && typeof mediaTransfer !== 'undefined') {
    installRolodex({
      list: mediaList,
      controller: mediaTransfer,
      selector: 'button[data-media-index]',
      onTop: transferUpdate
    });
    window.showMediaArticle = index => {
      const button = mediaList.querySelector(`button[data-media-index="${index}"]`);
      if (button) button.click();
    };
  }

  /* ------------------------------------------------------------------
     MISSION: keep the existing content renderer, but force the selected chapter
     to the first visible row before its own direct click handler runs.
     ------------------------------------------------------------------ */
  const missionList = document.getElementById('missionList');
  if (missionList && typeof missionTransfer !== 'undefined') {
    installRolodex({
      list: missionList,
      controller: missionTransfer,
      selector: 'button.mission-index-item'
    });
  }

  /* ------------------------------------------------------------------
     SYSTEM ARCHITECTURE: same rolodex/top-slot behavior, no numeric prefixes.
     ------------------------------------------------------------------ */
  const architectureList = document.getElementById('oryxList');
  if (typeof architectureTransfer !== 'undefined') {
    const baseArchitectureTransfer = architectureTransfer.transferTo.bind(architectureTransfer);
    architectureTransfer.transferTo = function (row, index, sourceText, targetText, prepareContent, immediate) {
      const clean = stripOrdinal(sourceText || targetText);
      const wrappedPrepare = () => {
        if (typeof prepareContent === 'function') prepareContent();
        const title = document.getElementById('oryxTitle');
        if (title) title.textContent = stripOrdinal(title.textContent);
      };
      return baseArchitectureTransfer(row, index, clean, clean, wrappedPrepare, immediate);
    };
  }

  const cleanArchitectureLabels = () => {
    architectureList?.querySelectorAll('.taxonomy-index-name, .media-index-item-outlet').forEach(node => {
      node.textContent = stripOrdinal(node.textContent);
    });
    const title = document.getElementById('oryxTitle');
    if (title) title.textContent = stripOrdinal(title.textContent);
    if (typeof architectureTransfer !== 'undefined' && architectureTransfer.bandLabel) {
      architectureTransfer.bandLabel.textContent = stripOrdinal(architectureTransfer.bandLabel.textContent);
    }
  };

  if (architectureList && typeof architectureTransfer !== 'undefined') {
    cleanArchitectureLabels();
    requestAnimationFrame(cleanArchitectureLabels);
    installRolodex({
      list: architectureList,
      controller: architectureTransfer,
      selector: 'button'
    });
  }

  /* ------------------------------------------------------------------
     Media preloading: warm the heavy images without blocking interaction.
     ------------------------------------------------------------------ */
  const preloadDeck = document.createElement('div');
  preloadDeck.setAttribute('aria-hidden', 'true');
  preloadDeck.style.cssText = 'position:fixed;left:-2px;top:-2px;width:1px;height:1px;overflow:hidden;opacity:.001;pointer-events:none;z-index:-1';
  const seen = new Set();
  const addPreload = src => {
    if (!src || seen.has(src)) return;
    seen.add(src);
    const img = document.createElement('img');
    img.src = src;
    img.alt = '';
    img.loading = 'eager';
    img.decoding = 'async';
    img.style.cssText = 'width:1px;height:1px;display:block';
    preloadDeck.appendChild(img);
  };
  try { if (Array.isArray(MEDIA_RELEASES)) MEDIA_RELEASES.forEach(item => addPreload(updateSource(item))); }
  catch (err) {}
  ['assets/images/system/R1V5.avif','assets/images/system/S2_5.avif','assets/images/system/Fairings_2.avif'].forEach(addPreload);
  document.body.appendChild(preloadDeck);

  /* SOCIAL is intentionally removed for this iteration. */
  document.querySelector('.social-feed-section')?.remove();

  /* ------------------------------------------------------------------
     Visual corrections for the top-slot source and Architecture specs.
     ------------------------------------------------------------------ */
  const style = document.createElement('style');
  style.id = 'aspire-refinement-v10-style';
  style.textContent = `
    /* The current first visible row remains as a structural blank source slot. */
    #missionWorkspace .media-index-item--transferring .media-index-item-title,
    #missionWorkspace .media-index-item--transferring .media-index-item-outlet,
    #missionWorkspace .media-index-item--transferring .media-index-item-arrow,
    #mediaWorkspace .media-index-item--transferring .media-index-item-title,
    #mediaWorkspace .media-index-item--transferring .media-index-item-outlet,
    #mediaWorkspace .media-index-item--transferring .media-index-item-arrow,
    #architectureWorkspace .media-index-item--transferring .media-index-item-title,
    #architectureWorkspace .media-index-item--transferring .media-index-item-outlet,
    #architectureWorkspace .media-index-item--transferring .media-index-item-arrow,
    #architectureWorkspace .media-index-item--transferring .taxonomy-index-name {
      visibility: hidden !important;
    }

    /* Legacy persistent evacuated rows must always be visible again. */
    #missionWorkspace .media-index-item--evacuated *,
    #mediaWorkspace .media-index-item--evacuated *,
    #architectureWorkspace .media-index-item--evacuated * {
      visibility: visible !important;
    }

    #missionList,
    #mediaList,
    #oryxList {
      overscroll-behavior: contain;
      scroll-behavior: auto !important;
    }

    /* Architecture specs: stronger hierarchy, cleaner data blocks. */
    #architectureWorkspace .architecture-spec-copy {
      display: grid !important;
      grid-template-columns: repeat(12, minmax(0, 1fr)) !important;
      gap: 14px !important;
      align-items: stretch !important;
      padding-top: 4px !important;
    }
    #architectureWorkspace .architecture-spec-lead,
    #architectureWorkspace .architecture-spec-kicker {
      grid-column: 1 / -1 !important;
      margin: 0 0 5px !important;
      padding: 0 0 14px !important;
      border-bottom: 1px solid rgba(255,255,255,.22) !important;
      font-family: 'Montserrat', sans-serif !important;
      font-size: clamp(18px, 1.5vw, 23px) !important;
      font-weight: 600 !important;
      line-height: 1.22 !important;
      letter-spacing: -.01em !important;
      color: #fff !important;
    }
    #architectureWorkspace .architecture-spec-group {
      grid-column: span 6 !important;
      min-height: 150px !important;
      padding: 17px 18px 16px !important;
      background: linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.018)) !important;
      border-top: 1px solid rgba(255,255,255,.42) !important;
    }
    #architectureWorkspace .architecture-spec-label {
      margin-bottom: 14px !important;
      font-family: 'Martian Mono', monospace !important;
      font-size: 10px !important;
      font-weight: 700 !important;
      letter-spacing: .16em !important;
      color: rgba(255,255,255,.65) !important;
    }
    #architectureWorkspace .architecture-spec-group p {
      margin: 0 !important;
      padding: 8px 0 !important;
      border-top: 1px solid rgba(255,255,255,.10) !important;
      font-family: 'Montserrat', sans-serif !important;
      font-size: 14px !important;
      font-weight: 500 !important;
      line-height: 1.45 !important;
      color: rgba(255,255,255,.88) !important;
    }
    #architectureWorkspace .architecture-spec-group p:first-of-type {
      border-top: 0 !important;
      padding-top: 0 !important;
    }
    #architectureWorkspace .architecture-spec-list {
      grid-column: 1 / -1 !important;
      display: grid !important;
      grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
      gap: 8px 14px !important;
      margin: 0 !important;
      padding: 0 !important;
      list-style: none !important;
    }
    #architectureWorkspace .architecture-spec-list li {
      position: relative !important;
      margin: 0 !important;
      padding: 13px 15px 13px 28px !important;
      border-top: 1px solid rgba(255,255,255,.22) !important;
      background: rgba(255,255,255,.025) !important;
      font-family: 'Montserrat', sans-serif !important;
      font-size: 13.5px !important;
      font-weight: 500 !important;
      line-height: 1.45 !important;
      color: rgba(255,255,255,.84) !important;
    }
    #architectureWorkspace .architecture-spec-list li::before {
      content: '' !important;
      position: absolute !important;
      left: 14px !important;
      top: 19px !important;
      width: 5px !important;
      height: 5px !important;
      background: rgba(255,255,255,.75) !important;
    }
    #architectureWorkspace .architecture-spec-visual {
      margin-bottom: 18px !important;
    }

    /* Keep Updates photography at intrinsic aspect ratio. */
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

    @media (max-width: 900px) {
      #architectureWorkspace .architecture-spec-group,
      #architectureWorkspace .architecture-spec-list {
        grid-column: 1 / -1 !important;
      }
      #architectureWorkspace .architecture-spec-list {
        grid-template-columns: 1fr !important;
      }
    }
  `;
  document.head.appendChild(style);
})();
