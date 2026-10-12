window.MathJax = {
    tex: {
        inlineMath: [["\\(", "\\)"]],
        displayMath: [["\\[", "\\]"]],
        processEscapes: true,
        processEnvironments: true
    },
    options: {
        ignoreHtmlClass: ".*|",
        processHtmlClass: "arithmatex"
    }
};

// Material emits document$ on every page load, before lib-loader.js has loaded MathJax: MathJax typesets the page on
// its own when it starts, so until then there is nothing to call.
document$.subscribe(() => {
    if (typeof MathJax.typesetPromise === "function") {
        MathJax.typesetPromise()
    }
})
