(() => {
  const HERO_CONFIG = {
    oryx: {
      image: 'assets/images/system/R1V5.avif',
      alt: 'Oryx fully reusable transportation system: R1v5 booster with D3 spacecraft',
      title: 'ORYX',
      role: 'LAUNCH / ORBITAL OPERATIONS / RETURN'
    },
    launcher: {
      image: 'assets/images/system/Fairings_2.avif',
      alt: 'Aspire Launcher: reusable booster with payload fairing',
      title: 'LAUNCHER',
      role: 'DEDICATED PAYLOAD DELIVERY'
    }
  };

  const heroVisual = document.querySelector('[data-hero-visual]');
  const heroImage = document.querySelector('[data-hero-image]');
  const heroName = document.querySelector('[data-hero-name]');
  const heroRole = document.querySelector('[data-hero-role]');
  const heroButtons = [...document.querySelectorAll('[data-vehicle-switch]')];

  function setHero(key) {
    const cfg = HERO_CONFIG[key];
    if (!cfg || !heroImage) return;
    heroButtons.forEach(btn => btn.classList.toggle('is-active', btn.dataset.vehicleSwitch === key));
    if (heroVisual) heroVisual.classList.add('is-changing');
    window.setTimeout(() => {
      heroImage.src = cfg.image;
      heroImage.alt = cfg.alt;
      if (heroName) heroName.textContent = cfg.title;
      if (heroRole) heroRole.textContent = cfg.role;
      requestAnimationFrame(() => heroVisual && heroVisual.classList.remove('is-changing'));
    }, 120);
  }

  heroButtons.forEach(btn => btn.addEventListener('click', () => setHero(btn.dataset.vehicleSwitch)));

  const profileButtons = [...document.querySelectorAll('[data-profile-switch]')];
  const profiles = [...document.querySelectorAll('[data-flight-profile]')];
  function setProfile(key) {
    profileButtons.forEach(btn => btn.classList.toggle('is-active', btn.dataset.profileSwitch === key));
    profiles.forEach(profile => profile.classList.toggle('is-active', profile.dataset.flightProfile === key));
  }
  profileButtons.forEach(btn => btn.addEventListener('click', () => setProfile(btn.dataset.profileSwitch)));

  const revealNodes = [...document.querySelectorAll('[data-arch-reveal]')];
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.09, rootMargin: '0px 0px -8% 0px' });
    revealNodes.forEach(node => observer.observe(node));
  } else {
    revealNodes.forEach(node => node.classList.add('is-visible'));
  }
})();
