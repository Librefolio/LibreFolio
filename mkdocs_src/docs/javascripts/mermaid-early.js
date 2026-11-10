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
//
// The ELK layout (a diagram whose frontmatter says `layout: elk`) is an ES module: the site's own copy of it
// (javascripts/vendor/mermaid-layout-elk/, pinned by `scripts/update_js_cache.py`, an exact version that takes
// Mermaid 11) is imported here and registered with Mermaid. The registration is asynchronous, so `mermaid.render`
// waits for it: a diagram drawn before it would silently use the default layout. A copy that cannot be imported (cache
// not filled, then the same pinned file from the CDN) leaves the default layout: the diagrams still draw.
(function () {
    "use strict";

    var CDN = "https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/mermaid.min.js";
    var ELK_CDN = "https://cdn.jsdelivr.net/npm/@mermaid-js/layout-elk@0.2.3/dist/mermaid-layout-elk.esm.min.mjs";
    // Beside this script: javascripts/mermaid-early.js → javascripts/vendor/mermaid-layout-elk/
    var SCRIPT = document.currentScript && document.currentScript.src;
    var ELK_LOCAL = SCRIPT ? new URL("vendor/mermaid-layout-elk/mermaid-layout-elk.esm.min.mjs", SCRIPT).href : null;

    function loaded() {
        return typeof window.mermaid !== "undefined" && typeof window.mermaid.initialize === "function";
    }

    // Material calls initialize() with its own options and no security level; the documentation's diagrams need the
    // looser one (links and HTML labels), so it is added to whatever Material passes.
    window.lfMermaidReady = function () {
        if (!loaded() || window.mermaid.lfLoose) return;
        var mermaid = window.mermaid;
        var initialize = mermaid.initialize.bind(mermaid);
        mermaid.initialize = function (config) {
            var merged = Object.assign({securityLevel: "loose"}, config);
            merged.themeCSS = (merged.themeCSS || "") + NODE_TEXT_CSS;
            return initialize(merged);
        };
        mermaid.lfLoose = true;
        registerElk(mermaid);
    };

    // The text of a node. Mermaid writes a node's own `color` (a `style X color:…` or a `classDef`) on the label's <div> and
    // <span>, but the text is a <p> inside them, and Material's theme CSS colours `.nodeLabel p` with the theme's label colour
    // (light in the dark theme): a pale box then shows light text, whatever colour the diagram asked for. The <p> takes the
    // colour of its <span>, which is the theme's colour when the node asked for none and the node's own when it did.
    // Appended after Material's CSS (same specificity, later wins), and only for node labels: an edge label keeps its colour.
    var NODE_TEXT_CSS = ".nodeLabel p, .cluster-label p { color: inherit; }";

    function importElk(url) {
        return import(url);
    }

    // The ELK layout: the site's copy, then the pinned CDN file, then nothing (the default layout). Never rejects.
    function registerElk(mermaid) {
        if (typeof mermaid.registerLayoutLoaders !== "function") return;
        var imported = ELK_LOCAL ? importElk(ELK_LOCAL).catch(function () { return importElk(ELK_CDN); }) : importElk(ELK_CDN);
        var ready = imported
            .then(function (module) { mermaid.registerLayoutLoaders(module.default); })
            .catch(function (error) { console.warn("Mermaid ELK layout not available, using the default layout", error); });
        window.lfMermaidElkReady = ready;
        var render = mermaid.render.bind(mermaid);
        mermaid.render = function () {
            var args = arguments;
            return ready.then(function () { return render.apply(null, args); });
        };
    }

    if (!loaded()) {
        // Parser-blocking writes: the library is defined, then adjusted, before the next script of the page runs
        document.write('<script src="' + CDN + '"><\/script>');
    }
    document.write("<script>window.lfMermaidReady()<\/script>");
})();
