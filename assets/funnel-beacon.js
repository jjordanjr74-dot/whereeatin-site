/* First-party conversion-intent beacon (wwe / whereeatin.com).
 *
 * Records ONLY {venture, event, page-path}: no cookies, no identifiers, no IP, no
 * third-party tracker. It exists because money telemetry cannot see the step before money -
 * a tap-to-call, an email click, or a click-through to a Stripe link never reaches Stripe,
 * so "nobody converted" and "nobody visited" read identically without this.
 *
 * TRANSPORT NOTE - the pixel is deliberate, not laziness:
 *   radar / bee / wwe are served with `Content-Security-Policy: connect-src 'self'`
 *   (set at the Cloudflare edge; our token cannot edit it). fetch() and sendBeacon() to a
 *   cross-origin collector are BLOCKED there and fail silently, leaving counts at zero.
 *   Those same policies carry `img-src 'self' data: https:`, so an image GET reaches the
 *   collector everywhere. One transport that works on all seven sites.
 * Collector: https://app.thesoapbook.com/t (see D:/Hermes_Core/scripts/funnel_collector.py).
 */
(function () {
  var V = "wwe";
  var URL = "https://app.thesoapbook.com/t";

  function send(ev) {
    try {
      var img = new Image(1, 1);
      img.src = URL + "/px.gif?v=" + encodeURIComponent(V)
              + "&e=" + encodeURIComponent(ev)
              + "&p=" + encodeURIComponent(location.pathname)
              + "&_=" + Date.now();   /* cache-buster: browsers happily reuse a pixel URL */
    } catch (e) { /* never break the page for telemetry */ }
  }

  document.addEventListener("click", function (ev) {
    var el = ev.target;
    var a = el && el.closest ? el.closest("a") : null;
    if (!a) { return; }
    var h = a.getAttribute("href") || "";
    if (h.indexOf("tel:") === 0) { send("tel_click"); }
    else if (h.indexOf("mailto:") === 0) { send("email_click"); }
    else if (h.indexOf("checkout.stripe.com") > -1 || h.indexOf("buy.stripe.com") > -1) { send("checkout_click"); }
  }, true);

  window.addEventListener("load", function () { send("view"); });
})();
