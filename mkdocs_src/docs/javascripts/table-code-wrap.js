/**
 * Long code in a table cell wraps.
 *
 * static/extra.css keeps the code of the first two columns of a table on one line: it suits an identifier or a variable
 * name and does not suit a log message, which then took the width of its longest line (the table scrolled sideways, or the
 * other columns were squeezed). A code span in a table cell that is a message, not a name, gets the class
 * `lf-code-long`: one over LONG_CODE characters, or over LONG_PHRASE characters with a space in it (a name or a path has
 * no space; a command with a few words is short), which static/extra.css lets wrap. Nothing else changes: the table stays a table, its columns share
 * the width under the `min-width` and `max-width` of static/extra.css.
 */
(function () {
    'use strict';

    var LONG_CODE = 60;        // characters: a code span longer than this is a message, not an identifier
    var LONG_PHRASE = 28;      // characters: with a space in it, a code span longer than this is a message

    function run() {
        var codes = document.querySelectorAll('.md-typeset table td code');
        Array.prototype.forEach.call(codes, function (code) {
            var text = code.textContent;
            if (text.length > LONG_CODE || (text.length > LONG_PHRASE && /\s/.test(text))) code.classList.add('lf-code-long');
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', run);
    } else {
        run();
    }

    // Material's instant loading, when a site turns it on
    if (typeof document$ !== 'undefined') {
        document$.subscribe(run);
    }
})();
