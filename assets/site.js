/* Where We Eatin'? — interaction layer. Progressive: with JS off the page is fully readable. */
(function () {
  document.documentElement.classList.add('js');

  // sticky nav gets its border only once you leave the hero
  var nav = document.getElementById('nav');
  var onScroll = function () { if (nav) nav.classList.toggle('is-stuck', window.scrollY > 12); };
  onScroll(); addEventListener('scroll', onScroll, { passive: true });

  // mobile menu
  var t = document.getElementById('navToggle'), links = document.getElementById('navLinks');
  if (t && links) {
    t.addEventListener('click', function () {
      var open = links.classList.toggle('open');
      t.setAttribute('aria-expanded', open ? 'true' : 'false');
      t.textContent = open ? 'Close' : 'Menu';
    });
    links.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') { links.classList.remove('open'); t.setAttribute('aria-expanded', 'false'); t.textContent = 'Menu'; }
    });
  }

  // reveal on scroll, and never leave content hidden if the observer never fires
  var items = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && items.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en, i) {
        if (en.isIntersecting) {
          setTimeout(function () { en.target.classList.add('in'); }, Math.min(i * 60, 240));
          io.unobserve(en.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.06 });
    items.forEach(function (el) { io.observe(el); });
    setTimeout(function () { items.forEach(function (el) { el.classList.add('in'); }); }, 2500);
  } else {
    items.forEach ? items.forEach(function (el) { el.classList.add('in'); }) : null;
  }

  var y = document.getElementById('year');
  if (y) y.textContent = new Date().getFullYear();
})();
