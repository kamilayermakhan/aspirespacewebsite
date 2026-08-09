(() => {
  const root = document.documentElement;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const clamp = (n, min = 0, max = 1) => Math.min(max, Math.max(min, n));

  /* ----------------------------------------------------------
     REVEALS
     ---------------------------------------------------------- */
  const revealNodes = [...document.querySelectorAll('[data-reveal]')];
  const programme = document.querySelector('.arch-programme');

  if (!reducedMotion && 'IntersectionObserver' in window) {
    const revealObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        revealObserver.unobserve(entry.target);
      });
    }, { threshold: 0.13, rootMargin: '0px 0px -8% 0px' });
    revealNodes.forEach(node => revealObserver.observe(node));

    if (programme) {
      const programmeObserver = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) programme.classList.add('is-visible');
        });
      }, { threshold: 0.18 });
      programmeObserver.observe(programme);
    }
  } else {
    revealNodes.forEach(node => node.classList.add('is-visible'));
    if (programme) programme.classList.add('is-visible');
  }

  /* ----------------------------------------------------------
     PERSISTENT SYSTEM STAGE
     One visual surface survives through four narrative states.
     ---------------------------------------------------------- */
  const chapters = [...document.querySelectorAll('.arch-chapter[data-scene]')];
  const sceneImages = [...document.querySelectorAll('[data-scene-image]')];
  const stageIndex = document.querySelector('[data-stage-index]');
  const stageEyebrow = document.querySelector('[data-stage-eyebrow]');
  const stageTitle = document.querySelector('[data-stage-title]');
  let activeScene = chapters[0]?.dataset.scene || 'oryx';
  let activeChapter = chapters[0] || null;

  function activateChapter(chapter) {
    if (!chapter) return;
    activeChapter = chapter;
    activeScene = chapter.dataset.scene;

    chapters.forEach(node => node.classList.toggle('is-active', node === chapter));
    sceneImages.forEach(image => image.classList.toggle('is-active', image.dataset.sceneImage === activeScene));

    if (stageIndex) stageIndex.textContent = chapter.dataset.index || '01';
    if (stageEyebrow) stageEyebrow.textContent = chapter.dataset.eyebrow || '';
    if (stageTitle) stageTitle.textContent = chapter.dataset.title || '';
  }

  if ('IntersectionObserver' in window) {
    const sceneObserver = new IntersectionObserver(entries => {
      const visible = entries
        .filter(entry => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
      if (visible[0]) activateChapter(visible[0].target);
    }, {
      threshold: [0.12, 0.28, 0.5, 0.72],
      rootMargin: '-28% 0px -28% 0px'
    });
    chapters.forEach(chapter => sceneObserver.observe(chapter));
  }

  activateChapter(activeChapter);

  /* ----------------------------------------------------------
     FLIGHT SCRUB
     The viewport stays fixed while the eight states move laterally.
     ---------------------------------------------------------- */
  const flightStory = document.querySelector('[data-flight-story]');
  const flightTrack = document.querySelector('[data-flight-track]');
  const flightSteps = [...document.querySelectorAll('[data-flight-step]')];
  const flightCurrent = document.querySelector('[data-flight-current]');
  let flightDistance = 0;

  function measureFlight() {
    if (!flightTrack) return;
    const viewportWidth = window.innerWidth;
    const left = flightTrack.getBoundingClientRect().left;
    const endPadding = Math.max(22, viewportWidth * 0.08);
    flightDistance = Math.max(0, flightTrack.scrollWidth - (viewportWidth - left) + endPadding);
    root.style.setProperty('--flight-distance', `${flightDistance}px`);
  }

  function updateFlight(progress) {
    root.style.setProperty('--flight-progress', progress.toFixed(4));
    if (!flightSteps.length) return;
    const index = Math.min(flightSteps.length - 1, Math.round(progress * (flightSteps.length - 1)));
    flightSteps.forEach((step, i) => step.classList.toggle('is-current', i === index));
    if (flightCurrent) flightCurrent.textContent = String(index + 1).padStart(2, '0');
  }

  measureFlight();
  updateFlight(0);

  /* ----------------------------------------------------------
     SCROLL DRIVER
     Values are written to CSS custom properties and the browser performs
     the visual interpolation. One requestAnimationFrame per scroll burst.
     ---------------------------------------------------------- */
  const intro = document.querySelector('.arch-intro');
  let ticking = false;

  function updateScrollState() {
    ticking = false;
    const vh = window.innerHeight || 1;

    if (intro) {
      const rect = intro.getBoundingClientRect();
      const scrollable = Math.max(1, rect.height - vh);
      const progress = clamp(-rect.top / scrollable);
      root.style.setProperty('--hero-progress', progress.toFixed(4));
    }

    if (activeChapter) {
      const rect = activeChapter.getBoundingClientRect();
      const local = clamp((vh * .62 - rect.top) / Math.max(rect.height, 1));
      root.style.setProperty('--stage-local', local.toFixed(4));
    }

    if (flightStory) {
      const rect = flightStory.getBoundingClientRect();
      const scrollable = Math.max(1, rect.height - vh);
      const progress = clamp(-rect.top / scrollable);
      updateFlight(progress);
    }
  }

  function requestTick() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(updateScrollState);
  }

  window.addEventListener('scroll', requestTick, { passive: true });
  window.addEventListener('resize', () => {
    measureFlight();
    requestTick();
  }, { passive: true });

  /* Tiny pointer response on the persistent visual adds depth without
     competing with scroll choreography. Disabled for touch/reduced motion. */
  const stage = document.querySelector('[data-stage]');
  if (stage && !reducedMotion && window.matchMedia('(pointer:fine)').matches) {
    stage.addEventListener('pointermove', event => {
      const rect = stage.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width - .5) * 2;
      const y = ((event.clientY - rect.top) / rect.height - .5) * 2;
      stage.style.setProperty('--px', x.toFixed(3));
      stage.style.setProperty('--py', y.toFixed(3));
      const active = stage.querySelector('.arch-scene-image.is-active img');
      if (active) active.style.transform = `translate3d(${x * 5}px, ${y * 4}px, 0)`;
    });
    stage.addEventListener('pointerleave', () => {
      stage.style.removeProperty('--px');
      stage.style.removeProperty('--py');
      const active = stage.querySelector('.arch-scene-image.is-active img');
      if (active) active.style.transform = '';
    });
  }

  requestAnimationFrame(() => {
    measureFlight();
    updateScrollState();
  });
})();
