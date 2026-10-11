/* WebMCP registration shim for Where We Eatin' (2026-10-10).
 *
 * The WebMCP CG draft (webmachinelearning.github.io/webmcp, 9 Oct 2026) defines exactly one
 * registration path: document.modelContext.registerTool({name, description, inputSchema}, callback).
 * There is NO static manifest or link-rel mechanism — <link rel="modelcontext"> is our grep-
 * discoverable convention for agents that read HTML, and THIS file is the spec-true surface.
 *
 * Honest by construction: every tool here executes as CLIENT-SIDE FILTERING of api/tools.json —
 * the exact same public roster data the page already renders. No fetch to any endpoint beyond
 * the static manifest, no write operations, nothing the page visitor couldn't already see.
 * Browsers without the API (all of them today except the Chrome flag) simply never run this.
 */
(function () {
  "use strict";
  if (!navigator.modelContext || typeof navigator.modelContext.registerTool !== "function") {
    return; // feature detection first: zero effect on normal browsers
  }
  fetch("/api/tools.json")
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (m) {
      if (!m || !Array.isArray(m.tools)) return;
      var data = m.data || { vendors: [], cuisines: [] };
      var impls = {
        list_vendors: function (args) {
          var out = data.vendors.slice();
          if (args.city) out = out.filter(function (v) { return v.city === args.city; });
          if (args.cuisine) out = out.filter(function (v) {
            return (v.cuisine || "").toLowerCase().indexOf(args.cuisine.toLowerCase()) !== -1;
          });
          return { vendors: out, distance_note: "direct distances need a position; none is collected here" };
        },
        vendor_lookup: function (args) {
          var v = data.vendors.filter(function (x) { return x.id === args.id; })[0];
          return v ? v : { error: "no vendor with id " + args.id };
        },
        list_cuisines: function () { return { cuisines: data.cuisines }; },
      };
      m.tools.forEach(function (t) {
        if (typeof impls[t.name] !== "function") return; // only tools we can execute honestly
        navigator.modelContext.registerTool(
          { name: t.name, description: t.description, inputSchema: t.inputSchema },
          function (params) { return impls[t.name](params || {}); }
        );
      });
    })
    .catch(function () { /* offline/manifest missing: the page works without tools, as before */ });
})();
