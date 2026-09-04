/**
 * portal — a Svelte action that relocates its node to `document.body`.
 *
 * Used by overlay/popover UI (date-range dropdowns, grace popovers) that must
 * escape an ancestor's `overflow`, `transform` or stacking context to be
 * positioned against the viewport. On `use:portal` the node is moved to the end
 * of `<body>`; on destroy it is removed again, but only if it is still a direct
 * child of body (a parent that already tore it down is left alone).
 *
 * The caller keeps ownership of positioning (usually `position: fixed` with
 * viewport coordinates) — this action only moves the node.
 */
export function portal(node: HTMLElement) {
    document.body.appendChild(node);
    return {
        destroy() {
            if (node.parentElement === document.body) node.remove();
        },
    };
}
