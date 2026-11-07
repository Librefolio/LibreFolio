/**
 * Balanced table columns.
 *
 * Two things for the tables of a page, one rule for every page and language, no markup in the pages.
 *
 * 1. A long piece of code in a cell wraps. The site keeps the code of the first two columns on one line, which suits an
 *    identifier or a variable name and does not suit a log message: the column took the width of the longest line and the
 *    table scrolled sideways. A code span over LONG_CODE characters gets the class `lf-code-long`, which static/extra.css
 *    lets wrap.
 * 2. Balanced columns. A table whose cells hold a long log line in one column and a short instruction in another is laid out by the browser
 * in proportion to the widest cell of each column: the long column takes nearly all the width, the instruction column is
 * squeezed into a few words per line, and every row grows very tall. One rule for every page and language, no markup in
 * the pages: for a table with three or more columns where one column holds long text, the columns get a width in
 * proportion to the square root of their average text length (with a floor), so a long column is wider but never takes
 * everything.
 *
 * - Only tables that need it (a column with an average cell over LONG_CELL characters); the others keep the theme's own
 *   layout. When every column is long they share the width almost equally: the default layout gave the last one a sliver.
 * - Only where there is room: below WIDE_VIEWPORT the table keeps its default layout and scrolls sideways as before.
 * - A table with a cell that spans columns is left alone.
 * - The table gets the class `lf-balanced`: static/extra.css lets its code wrap inside the cell, which a fixed layout needs.
 */
(function () {
    'use strict';

    var LONG_CODE = 60;        // characters: a code span longer than this is a message, not an identifier
    var LONG_CELL = 90;        // average characters of a cell that makes its column "long"
    var FLOOR = 7;             // weight added to every column, so a one-word column is not squeezed to nothing
    var MIN_SHARE = 8;        // percent: no column narrower than this
    var WIDE_VIEWPORT = '(min-width: 60em)';

    var MARK = 'data-lf-balanced';

    function textLength(cell) {
        return (cell.textContent || '').replace(/\s+/g, ' ').trim().length;
    }

    /** The average text length of each column, or null when the table is not a candidate. */
    function columnAverages(table) {
        var rows = Array.prototype.slice.call(table.querySelectorAll('tbody tr'));
        var head = table.querySelectorAll('thead th');
        var columns = head.length;
        if (columns < 3 || rows.length === 0) return null;
        var sums = [];
        for (var c = 0; c < columns; c++) sums.push(0);
        for (var r = 0; r < rows.length; r++) {
            var cells = rows[r].children;
            if (cells.length !== columns) return null;      // a spanning or missing cell: leave it alone
            for (var i = 0; i < columns; i++) {
                if (cells[i].colSpan > 1) return null;
                sums[i] += textLength(cells[i]);
            }
        }
        return sums.map(function (sum) { return sum / rows.length; });
    }

    function needsBalance(averages) {
        return Math.max.apply(null, averages) > LONG_CELL;
    }

    /** Column widths as percentages that add up to 100. */
    function shares(averages) {
        var weights = averages.map(function (average) { return FLOOR + Math.pow(average, 0.7); });
        var total = weights.reduce(function (a, b) { return a + b; }, 0);
        var percent = weights.map(function (weight) { return Math.max(MIN_SHARE, (weight / total) * 100); });
        var scale = 100 / percent.reduce(function (a, b) { return a + b; }, 0);
        return percent.map(function (value) { return value * scale; });
    }

    function apply(table, widths) {
        if (table.hasAttribute(MARK)) return;
        var group = document.createElement('colgroup');
        widths.forEach(function (width) {
            var col = document.createElement('col');
            col.style.width = width.toFixed(2) + '%';
            group.appendChild(col);
        });
        table.insertBefore(group, table.firstChild);
        table.style.display = 'table';
        table.style.width = '100%';
        table.style.tableLayout = 'fixed';
        table.classList.add('lf-balanced');
        table.setAttribute(MARK, '1');
    }

    function remove(table) {
        if (!table.hasAttribute(MARK)) return;
        Array.prototype.slice.call(table.children).forEach(function (child) {
            if (child.tagName === 'COLGROUP') table.removeChild(child);
        });
        table.style.display = '';
        table.style.width = '';
        table.style.tableLayout = '';
        table.classList.remove('lf-balanced');
        if (!table.getAttribute('class')) table.removeAttribute('class'); // an empty class attribute would hide it from `:not([class])`
        table.removeAttribute(MARK);
    }

    /** A code span that is a message more than a name may wrap, whatever column it is in. */
    function wrapLongCode() {
        var codes = document.querySelectorAll('.md-typeset table td code');
        Array.prototype.forEach.call(codes, function (code) {
            if (code.textContent.length > LONG_CODE) code.classList.add('lf-code-long');
        });
    }

    function run() {
        wrapLongCode();
        var wide = window.matchMedia(WIDE_VIEWPORT).matches;
        var tables = document.querySelectorAll('.md-typeset table:not([class]), .md-typeset table.lf-balanced');
        Array.prototype.forEach.call(tables, function (table) {
            if (!wide) return remove(table);
            var averages = columnAverages(table);
            if (averages && needsBalance(averages)) apply(table, shares(averages));
        });
    }

    function init() {
        run();
        var query = window.matchMedia(WIDE_VIEWPORT);
        if (query.addEventListener) query.addEventListener('change', run);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Material's instant loading, when a site turns it on
    if (typeof document$ !== 'undefined') {
        document$.subscribe(run);
    }
})();
