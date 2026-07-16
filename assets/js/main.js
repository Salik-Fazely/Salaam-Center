/* Tarteel House — main.js
   Lightweight progressive enhancement. No dependencies. */

document.addEventListener('DOMContentLoaded', () => {
  const cleanIndexPath = window.location.pathname.replace(/\/index\.html$/i, '/');
  if (cleanIndexPath !== window.location.pathname) {
    window.location.replace(`${cleanIndexPath}${window.location.search}${window.location.hash}`);
    return;
  }

  /* ----- Mobile nav toggle ----- */
  const navToggle = document.getElementById('nav-toggle');
  const navMenu   = document.getElementById('nav-menu');

  if (navToggle && navMenu) {
    const mobileNav = window.matchMedia('(max-width: 767px)');

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

  /* ----- FAQ disclosures ----- */
  const faqTriggers = Array.from(document.querySelectorAll('.faq-question'));

  const setFaqState = (trigger, expanded) => {
    const panelId = trigger.getAttribute('aria-controls');
    const panel = panelId ? document.getElementById(panelId) : null;
    const item = trigger.closest('.faq-item');
    if (!panel || !item) return;

    trigger.setAttribute('aria-expanded', String(expanded));
    panel.hidden = !expanded;
    item.classList.toggle('is-open', expanded);
  };

  faqTriggers.forEach(trigger => {
    setFaqState(trigger, trigger.getAttribute('aria-expanded') === 'true');

    trigger.addEventListener('click', () => {
      const willExpand = trigger.getAttribute('aria-expanded') !== 'true';

      faqTriggers.forEach(otherTrigger => {
        if (otherTrigger !== trigger) setFaqState(otherTrigger, false);
      });
      setFaqState(trigger, willExpand);
    });
  });

  /* ----- Click-to-play YouTube videos ----- */
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

  /* ----- Active nav link ----- */
  const navLinks = document.querySelectorAll('.nav__link');
  const normalizePath = (value) => {
    let pathname;
    try {
      pathname = new URL(value, window.location.origin).pathname;
    } catch (err) {
      pathname = value || '/';
    }

    pathname = pathname.replace(/\/index\.html$/i, '/');
    if (pathname.length > 1) pathname = pathname.replace(/\/+$/, '');
    return pathname || '/';
  };

  const currentPath = normalizePath(window.location.href);

  navLinks.forEach(link => {
    if (normalizePath(link.getAttribute('href')) === currentPath) {
      link.classList.add('is-active');
      link.setAttribute('aria-current', 'page');
    }
  });

  /* ----- Scroll-reveal animations ----- */
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ----- Video message carousel ----- */
  document.querySelectorAll('[data-feedback-carousel]').forEach(carousel => {
    const track = carousel.querySelector('[data-carousel-track]');
    if (!track) return;

    const items = Array.from(track.children);
    const prevButton = carousel.querySelector('[data-carousel-prev]');
    const nextButton = carousel.querySelector('[data-carousel-next]');
    const dots = carousel.querySelector('[data-carousel-dots]');
    let snapPoints = [];
    let activeIndex = 0;
    let scrollTicking = false;

    const getMaxScroll = () => Math.max(0, track.scrollWidth - track.clientWidth);

    const getScrollPaddingStart = () => {
      const style = window.getComputedStyle(track);
      const padding = style.scrollPaddingInlineStart || style.scrollPaddingLeft || '0';
      return Number.parseFloat(padding) || 0;
    };

    const getSnapPoints = () => {
      const maxScroll = getMaxScroll();
      const trackRect = track.getBoundingClientRect();
      const scrollPaddingStart = getScrollPaddingStart();

      return items
        .map(item => {
          const itemRect = item.getBoundingClientRect();
          const rawPoint = itemRect.left - trackRect.left + track.scrollLeft - scrollPaddingStart;
          return Math.min(Math.max(0, Math.round(rawPoint)), maxScroll);
        })
        .filter((point, index, points) => index === 0 || Math.abs(point - points[index - 1]) > 4);
    };

    const closestSnapIndex = () => {
      if (!snapPoints.length) return 0;

      return snapPoints.reduce((closest, point, index) => {
        const currentDistance = Math.abs(track.scrollLeft - point);
        const closestDistance = Math.abs(track.scrollLeft - snapPoints[closest]);
        return currentDistance < closestDistance ? index : closest;
      }, 0);
    };

    const updateCarousel = () => {
      const maxScroll = getMaxScroll();
      activeIndex = closestSnapIndex();

      carousel.classList.toggle('is-static', maxScroll <= 1 || snapPoints.length <= 1);

      if (prevButton) prevButton.disabled = track.scrollLeft <= 1;
      if (nextButton) nextButton.disabled = maxScroll - track.scrollLeft <= 1;

      if (dots) {
        dots.querySelectorAll('.feedback-videos__dot').forEach((dot, index) => {
          const isActive = index === activeIndex;
          dot.classList.toggle('is-active', isActive);
          dot.setAttribute('aria-current', isActive ? 'true' : 'false');
        });
      }
    };

    const scrollToSnap = (index) => {
      snapPoints = getSnapPoints();
      const nextIndex = Math.min(Math.max(index, 0), snapPoints.length - 1);
      track.scrollTo({
        left: snapPoints[nextIndex] || 0,
        behavior: prefersReduced ? 'auto' : 'smooth',
      });
    };

    const renderDots = () => {
      if (!dots) return;

      dots.replaceChildren();
      snapPoints.forEach((_, index) => {
        const dot = document.createElement('button');
        dot.type = 'button';
        dot.className = 'feedback-videos__dot';
        dot.dataset.carouselIndex = String(index);
        dot.setAttribute('aria-label', `Show video message ${index + 1}`);
        dots.append(dot);
      });
    };

    const rebuildCarousel = () => {
      snapPoints = getSnapPoints();
      renderDots();
      updateCarousel();
    };

    if (prevButton) {
      prevButton.addEventListener('click', () => scrollToSnap(activeIndex - 1));
    }

    if (nextButton) {
      nextButton.addEventListener('click', () => scrollToSnap(activeIndex + 1));
    }

    if (dots) {
      dots.addEventListener('click', (event) => {
        const dot = event.target.closest('.feedback-videos__dot');
        if (!dot) return;
        scrollToSnap(Number(dot.dataset.carouselIndex || 0));
      });
    }

    track.addEventListener('scroll', () => {
      if (scrollTicking) return;

      scrollTicking = true;
      window.requestAnimationFrame(() => {
        updateCarousel();
        scrollTicking = false;
      });
    }, { passive: true });

    if ('ResizeObserver' in window) {
      new ResizeObserver(rebuildCarousel).observe(track);
    } else {
      window.addEventListener('resize', rebuildCarousel);
    }

    rebuildCarousel();
  });

  if (!prefersReduced && 'IntersectionObserver' in window) {

    /* -- Section-level reveal -- */
    const sections = document.querySelectorAll('main > section');

    const sectionObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          sectionObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });

    sections.forEach((section, i) => {
      /* First section is always visible — skip it */
      if (i === 0) {
        section.classList.add('is-revealed');
        return;
      }
      section.classList.add('reveal-section');
      sectionObserver.observe(section);
    });

    /* -- Staggered reveal — teacher cards, pricing cards & trust stats -- */
    const STAGGER_SELECTORS = [
      '.teacher-card',
      '.feedback-video-card',
      '.price-card',
      '.trust-stats__item',
    ];

    const cardObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          cardObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    STAGGER_SELECTORS.forEach(selector => {
      document.querySelectorAll(selector).forEach((card, i) => {
        card.classList.add('reveal-card');
        card.style.transitionDelay = `${i * 80}ms`;
        cardObserver.observe(card);
      });
    });

    /* -- Trust stats count-up -- */
    const statValues = document.querySelectorAll('.trust-stats__value[data-count-to]');

    const setStatValue = (el, value) => {
      const suffix = el.dataset.countSuffix || '';
      el.textContent = `${value}${suffix}`;
    };

    const animateStatValue = (el) => {
      const target = Number(el.dataset.countTo || 0);
      const duration = 1100;
      const start = performance.now();

      const tick = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        setStatValue(el, Math.round(target * eased));

        if (progress < 1) {
          requestAnimationFrame(tick);
        } else {
          setStatValue(el, target);
        }
      };

      requestAnimationFrame(tick);
    };

    if (statValues.length) {
      const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;

          entry.target
            .querySelectorAll('.trust-stats__value[data-count-to]')
            .forEach(value => {
              setStatValue(value, 0);
              animateStatValue(value);
            });

          statsObserver.unobserve(entry.target);
        });
      }, { threshold: 0.4 });

      document.querySelectorAll('.trust-stats').forEach(section => {
        statsObserver.observe(section);
      });
    }

  }

  /* ----- Page transitions -----
     Intercept internal link clicks, fade the body out, then navigate.
     Browser back/forward is handled via the pageshow event, which fires
     on fresh loads AND on bfcache restores — so we always strip the
     leaving state when a page becomes visible. */
  if (!prefersReduced) {

    window.addEventListener('pageshow', () => {
      document.body.classList.remove('is-leaving');
    });

    const isInternalNav = (e, anchor) => {
      if (e.defaultPrevented) return false;
      if (e.button !== 0) return false;
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return false;
      if (anchor.target && anchor.target !== '' && anchor.target !== '_self') return false;
      if (anchor.hasAttribute('download')) return false;

      const href = anchor.getAttribute('href');
      if (!href) return false;
      if (href.startsWith('#'))       return false;
      if (href.startsWith('mailto:')) return false;
      if (href.startsWith('tel:'))    return false;

      let url;
      try { url = new URL(anchor.href, window.location.href); }
      catch (err) { return false; }

      if (url.origin !== window.location.origin) return false;

      /* Same-page hash link (e.g. /about/#approach while on /about) */
      if (url.pathname === window.location.pathname && url.hash && !url.search) return false;

      return true;
    };

    document.addEventListener('click', (e) => {
      const anchor = e.target.closest('a[href]');
      if (!anchor) return;
      if (!isInternalNav(e, anchor)) return;

      e.preventDefault();
      const destination = anchor.href;
      document.body.classList.add('is-leaving');
      window.setTimeout(() => {
        window.location.href = destination;
      }, 250);
    });

  }

});
