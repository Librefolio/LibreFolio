/**
 * Shared menu (lane 84-D) — puts back the groups of the navigation that the build left out of the page.
 *
 * The page keeps, in its menu, what Material draws for a pruned navigation: the tabs and the groups of the branch the page
 * is in; every other group is one link to its first page (`li.md-nav__item--pruned`). The build writes the whole menu of the
 * language once, as a string, after this code (`mkdocs_src/hooks/shared_nav.py`): `window.LF_NAV[language]`, every link a path
 * from the site's root. This runs while the page is parsed, right after the menu and before Material's bundle starts, so
 * Material finds the menu it always found. A group is looked up by its depth and the path of its first page.
 *
 * Without this script the page still has a menu of real links.
 */
(function () {
    'use strict';

    var nav = document.currentScript && document.currentScript.previousElementSibling;
    if (!nav || !nav.hasAttribute('data-lf-nav')) return;
    var language = nav.getAttribute('data-lf-nav');
    var root = nav.getAttribute('data-lf-root') || '';
    var whole = window.LF_NAV && window.LF_NAV[language];
    if (!whole) return;

    /** How many groups hold this group, itself included: 1 for a tab. */
    function depth(item) {
        var d = 1;
        for (var up = item.parentElement; up; up = up.parentElement) {
            if (up.tagName === 'LI' && up.classList.contains('md-nav__item--nested')) d++;
        }
        return d;
    }

    // Material writes each link as short as it can be from the page (`../x/` inside the same section): a link is read against
    // the page, and the site's root (`data-lf-root`, the path up to it) is taken off.
    var base = new URL(root || './', location.href).pathname;

    /** The first page of a group, as a path from the site's root. */
    function firstPage(item, relative) {
        var link = item.querySelector('a[href]');
        var href = link ? link.getAttribute('href') : '';
        if (!relative) return href;
        var path = new URL(href, location.href).pathname;
        return path.indexOf(base) === 0 ? path.slice(base.length) : href;
    }

    var template = document.createElement('template');
    template.innerHTML = whole;
    var groups = {};
    template.content.querySelectorAll('li.md-nav__item--nested').forEach(function (item) {
        var key = depth(item) + '|' + firstPage(item, false);
        if (!(key in groups)) groups[key] = item;
    });

    // The groups to put back are collected before any is replaced, then replaced outermost first (the document's order).
    Array.prototype.slice.call(nav.querySelectorAll('li.md-nav__item--pruned')).forEach(function (stub) {
        var group = groups[depth(stub) + '|' + firstPage(stub, true)];
        if (!group) return;
        var copy = group.cloneNode(true);
        copy.querySelectorAll('a[href]').forEach(function (link) {
            link.setAttribute('href', root + link.getAttribute('href'));
        });
        stub.parentNode.replaceChild(copy, stub);
    });
})();
