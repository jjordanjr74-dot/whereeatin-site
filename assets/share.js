/* Where We Eatin'? - share a truck page. Uses the Web Share API where the browser has it, otherwise copies
   the link. The button ships hidden and only appears when this script runs. */
(function () {
  function fallbackCopy(text, done) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'absolute';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    done(ok);
  }
  function copyLink(text, done) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { done(true); },
        function () { fallbackCopy(text, done); });
    } else {
      fallbackCopy(text, done);
    }
  }
  document.querySelectorAll('[data-share]').forEach(function (b) {
    b.hidden = false;
    b.addEventListener('click', function () {
      var url = b.getAttribute('data-url') || location.href;
      var title = b.getAttribute('data-title') || document.title;
      var label = b.textContent;
      function flash(msg) {
        b.textContent = msg;
        setTimeout(function () { b.textContent = label; }, 1800);
      }
      if (navigator.share) {
        navigator.share({ title: title, url: url }).catch(function () {});
        return;
      }
      copyLink(url, function (ok) { flash(ok ? 'Link copied' : 'Copy not allowed here'); });
    });
  });
})();
