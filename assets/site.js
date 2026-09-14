/* Where We Eatin'? — launch site behaviour.
   Two jobs, both with graceful degradation:
     1. Keep the "live demo" button pointing at the current public instance (assets/demo_url.json).
     2. Show live counts (trucks / cities) pulled from that instance's read-only JSON API when it
        is reachable; otherwise leave the honest static numbers that are already in the HTML. */
(function () {
  "use strict";

  var FALLBACK_DEMO = document.getElementById("demoLink");
  var FALLBACK_URL = FALLBACK_DEMO ? FALLBACK_DEMO.href : "";

  function setDemoHref(url) {
    if (!url || !FALLBACK_DEMO) return;
    FALLBACK_DEMO.href = url;
  }

  function setText(sel, value) {
    var el = document.querySelector(sel);
    if (el && value !== null && value !== undefined) el.textContent = String(value);
  }

  function fetchJSON(url, ms) {
    var ctl = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = ctl ? setTimeout(function () { ctl.abort(); }, ms || 6000) : null;
    return fetch(url, { signal: ctl ? ctl.signal : undefined, cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(r.status)); })
      .finally(function () { if (timer) clearTimeout(timer); });
  }

  // 1. current demo endpoint
  fetchJSON("assets/demo_url.json", 4000)
    .then(function (d) { if (d && d.url) setDemoHref(d.url); })
    .catch(function () { /* keep the hard-coded fallback link */ });

  // 2. live counts from the app itself (public read-only endpoints, CORS-enabled)
  fetchJSON("assets/demo_url.json", 4000)
    .then(function (d) { return (d && d.url) ? d.url : FALLBACK_URL; })
    .catch(function () { return FALLBACK_URL; })
    .then(function (base) {
      if (!base) return;
      var root = base.replace(/\/+$/, "");
      return fetchJSON(root + "/api/vendors", 7000).then(function (list) {
        if (!Array.isArray(list) || !list.length) return;
        setText('[data-live="vendors"]', list.length);
        var cities = {};
        var rated = 0, total = 0;
        list.forEach(function (v) {
          if (v && v.city) cities[String(v.city).trim()] = 1;
          var r = v && v.rating ? Number(v.rating.average || v.rating.avg) : 0;
          var c = v && v.rating ? Number(v.rating.count || 0) : 0;
          if (c > 0 && r > 0) { rated++; total += r; }
        });
        var band = document.querySelector(".band-txt");
        if (band) {
          var cityCount = Object.keys(cities).length;
          band.innerHTML = "<strong>" + list.length + " trucks live</strong> across " +
            cityCount + " Colorado " + (cityCount === 1 ? "city" : "cities") +
            " \u2014 and every one of them was added by a human, not a scraper.";
        }
      });
    })
    .catch(function () { /* static numbers stay */ });

  // 3. photo credits, inline, so the licence is visible on the page itself
  fetchJSON("assets/credits.json", 4000)
    .then(function (list) {
      if (!Array.isArray(list) || !list.length) return;
      var el = document.getElementById("photoCredits");
      if (!el) return;
      var names = list.map(function (c) {
        var a = c.author || c.creator || "Openverse contributor";
        var l = c.license || c.licence || "";
        return a + (l ? " (" + l + ")" : "");
      });
      var uniq = names.filter(function (n, i) { return names.indexOf(n) === i; }).slice(0, 6);
      el.innerHTML = "Photography: " + uniq.join(", ") +
        (names.length > uniq.length ? " and others" : "") +
        " \u2014 via Openverse. Full per-file credits in " +
        '<a href="assets/credits.json">credits.json</a>. ' +
        "Where We Eatin'? is an independent directory and is not affiliated with any truck listed.";
    })
    .catch(function () { /* keep the static credit line */ });
})();