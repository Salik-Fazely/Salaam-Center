/* Salaam Center progressive enhancement. No dependencies. */

document.addEventListener('DOMContentLoaded', () => {
  const cleanIndexPath = window.location.pathname.replace(/\/index\.html$/i, '/');
  if (cleanIndexPath !== window.location.pathname) {
    window.location.replace(`${cleanIndexPath}${window.location.search}${window.location.hash}`);
    return;
  }

  const navToggle = document.getElementById('nav-toggle');
  const navMenu = document.getElementById('nav-menu');

  if (navToggle && navMenu) {
    navMenu.classList.add('is-enhanced');
    navToggle.classList.add('is-enhanced');
    const mobileNav = window.matchMedia('(max-width: 1023px)');

    const setNavState = (open, { focusFirst = false, returnFocus = false } = {}) => {
      const isOpen = mobileNav.matches && open;
      const isClosedMobile = mobileNav.matches && !isOpen;

      navMenu.classList.toggle('is-open', isOpen);
      navMenu.hidden = isClosedMobile;
      navMenu.inert = isClosedMobile;
      navMenu.toggleAttribute('inert', isClosedMobile);
      navToggle.setAttribute('aria-expanded', String(isOpen));
      navToggle.setAttribute('aria-label', isOpen ? 'Close navigation menu' : 'Open navigation menu');

      if (isOpen && focusFirst) {
        navMenu.querySelector('a[href]')?.focus();
      } else if (!isOpen && returnFocus) {
        navToggle.focus();
      }
    };

    navToggle.addEventListener('click', () => {
      const willOpen = navToggle.getAttribute('aria-expanded') !== 'true';
      setNavState(willOpen, { focusFirst: willOpen });
    });

    navMenu.addEventListener('click', (event) => {
      if (!mobileNav.matches || !event.target.closest?.('a[href]')) return;
      setNavState(false);
    });

    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape' || navToggle.getAttribute('aria-expanded') !== 'true') return;
      setNavState(false, { returnFocus: true });
    });

    const resetNavState = () => setNavState(false);
    if (typeof mobileNav.addEventListener === 'function') {
      mobileNav.addEventListener('change', resetNavState);
    } else {
      mobileNav.addListener(resetNavState);
    }
    window.addEventListener('resize', resetNavState);
    resetNavState();
  }

  document.querySelectorAll('[data-youtube-id]').forEach(trigger => {
    let isActivated = false;

    trigger.addEventListener('click', () => {
      if (isActivated) return;

      const videoId = trigger.dataset.youtubeId;
      const title = trigger.dataset.youtubeTitle?.trim();
      if (!/^[A-Za-z0-9_-]{11}$/.test(videoId || '') || !title) return;

      const iframe = document.createElement('iframe');
      const origin = window.location.origin && window.location.origin !== 'null'
        ? `&origin=${encodeURIComponent(window.location.origin)}`
        : '';

      iframe.className = 'youtube-inline-player';
      iframe.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(videoId)}?autoplay=1&rel=0&playsinline=1${origin}`;
      iframe.title = title;
      iframe.tabIndex = 0;
      iframe.loading = 'lazy';
      iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
      iframe.referrerPolicy = 'strict-origin-when-cross-origin';
      iframe.allowFullscreen = true;
      iframe.addEventListener('focus', () => iframe.classList.add('has-focus'));
      iframe.addEventListener('blur', () => iframe.classList.remove('has-focus'));

      const player = document.createElement('div');
      player.className = `${trigger.className} is-playing`;
      player.setAttribute('aria-label', title);
      player.append(iframe);

      isActivated = true;
      trigger.replaceWith(player);
      requestAnimationFrame(() => {
        iframe.focus({ preventScroll: true });
      });
    });
  });
});
