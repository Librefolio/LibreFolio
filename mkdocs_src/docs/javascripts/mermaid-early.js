// Mermaid, before Material for MkDocs starts. A classic script, run in <head> right after the site's own copy of
// the library (overrides/main.html writes both, on the pages that have a diagram and only there).
//
// Why before: Material's bundle draws the diagrams as soon as it runs. If `window.mermaid` is not defined by then it
// fetches its own copy from a CDN (unpkg) — offline the diagrams stay code, online the page calls a third party. So the
// library must be defined synchronously, ahead of the bundle: the copy pinned by version and SHA-256 in
// scripts/update_js_cache.py (filled into javascripts/vendor/mermaid/ by `./dev.py cache js`).
//
// If the site has no copy (cache not filled), the same pinned file is read from the CDN here, still before the bundle.
// If that fails too, Material falls back on its own source, as it always did.
(function () {
    "use strict";

    var CDN = "https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/mermaid.min.js";

    function loaded() {
        return typeof window.mermaid !== "undefined" && typeof window.mermaid.initialize === "function";
    }

    // Material calls initialize() with its own options and no security level; the documentation's diagrams need the
    // looser one (links and HTML labels), so it is added to whatever Material passes.
    window.lfMermaidReady = function () {
        if (!loaded() || window.mermaid.lfLoose) return;
        var initialize = window.mermaid.initialize.bind(window.mermaid);
        window.mermaid.initialize = function (config) {
            return initialize(Object.assign({securityLevel: "loose"}, config));
        };
        window.mermaid.lfLoose = true;
    };

    if (!loaded()) {
        // Parser-blocking writes: the library is defined, then adjusted, before the next script of the page runs
        document.write('<script src="' + CDN + '"><\/script>');
    }
    document.write("<script>window.lfMermaidReady()<\/script>");
})();
