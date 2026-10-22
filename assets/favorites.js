/* Where We Eatin'? - saved trucks. Client-side only: a list of truck slugs in this browser's localStorage.
   No account, no request, nothing sent anywhere. Save buttons ship hidden and only appear when this runs. */
(function () {
  var KEY = 'wwe.favorites.v1';
  var SLUG = /^[a-z0-9-]{1,80}$/;

  function load() {
    try {
      var a = JSON.parse(window.localStorage.getItem(KEY) || '[]');
      return Array.isArray(a) ? a.filter(function (s) { return typeof s === 'string' && SLUG.test(s); }) : [];
    } catch (e) { return []; }
  }
  function store(list) {
    try { window.localStorage.setItem(KEY, JSON.stringify(list)); } catch (e) { /* storage blocked: nothing saved */ }
  }

  function renderMine(list) {
    var section = document.getElementById('mytrucks');
    var box = document.getElementById('myTrucksList');
    if (!section || !box) return;
    box.innerHTML = '';
    var cards = document.querySelectorAll('article[data-slug]');
    list.forEach(function (slug) {
      for (var i = 0; i < cards.length; i++) {
        if (cards[i].getAttribute('data-slug') === slug) {
          var copy = cards[i].cloneNode(true);
          copy.classList.remove('reveal');
          box.appendChild(copy);
          break;
        }
      }
    });
    section.hidden = list.length === 0;
  }

  function paint() {
    var list = load();
    document.querySelectorAll('[data-fav]').forEach(function (b) {
      var on = list.indexOf(b.getAttribute('data-fav')) !== -1;
      var name = b.getAttribute('data-name') || 'this truck';
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.textContent = on ? '\u2665 Saved' : '\u2661 Save';
      b.setAttribute('aria-label', (on ? 'Remove ' : 'Save ') + name + (on ? ' from my trucks' : ' to my trucks'));
    });
    renderMine(list);
  }

  document.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest('[data-fav]') : null;
    if (!b) return;
    e.preventDefault();
    var slug = b.getAttribute('data-fav');
    if (!SLUG.test(slug)) return;
    var list = load();
    var i = list.indexOf(slug);
    if (i === -1) list.push(slug); else list.splice(i, 1);
    store(list);
    paint();
  });

  document.querySelectorAll('[data-fav]').forEach(function (b) { b.hidden = false; });
  paint();
})();
