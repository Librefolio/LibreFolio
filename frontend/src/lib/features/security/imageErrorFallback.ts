/**
 * What an icon does when its image cannot load, without an inline event handler (lot H-55 v2).
 *
 * The Content-Security-Policy LibreFolio enforces on its pages blocks inline event-handler attributes (an `onerror`
 * attribute written in the markup), which the HTML strings of the tables and tooltips used to carry on their icons.
 * They carry data attributes instead, and one listener, in the capture phase of the document (an image's `error` does
 * not bubble), does what the handler did:
 *
 * - `data-fallback-text="XX"`: the image's parent shows that text instead (a provider's initials), as text, never HTML;
 * - `data-fallbacks='["url", …]'`: the next address of an icon's chain (a broker's icon candidates); the attribute keeps
 *   the rest. Once the chain is spent, the image does what `data-hide-on-error` says;
 * - `data-hide-on-error="display"` hides the image (`display: none`), `"visibility"` keeps its room
 *   (`visibility: hidden`), `"next-sibling"` hides it and shows its next sibling (a hidden fallback icon).
 *
 * Only an image carrying `data-hide-on-error` or `data-fallback-text` is handled: a component whose own handler walks a
 * `data-fallbacks` chain (an enum option's icon) is left alone. `startImageErrorFallback()` runs once per page (the root
 * layout); a second call installs nothing more.
 */

export const HIDE_ON_ERROR_ATTRIBUTE = 'data-hide-on-error';
export const FALLBACKS_ATTRIBUTE = 'data-fallbacks';
export const FALLBACK_TEXT_ATTRIBUTE = 'data-fallback-text';

const installed = new WeakMap<Document, () => void>();

/** The next address of the image's chain, the attribute keeping the rest; null once the chain is spent. */
function nextFallback(image: HTMLImageElement): string | null {
    const raw = image.getAttribute(FALLBACKS_ATTRIBUTE);
    if (raw === null) {
        return null;
    }
    let rest: unknown[];
    try {
        const parsed: unknown = JSON.parse(raw);
        rest = Array.isArray(parsed) ? parsed : [];
    } catch {
        rest = [];
    }
    while (rest.length > 0) {
        const candidate = rest.shift();
        if (typeof candidate === 'string' && candidate) {
            image.setAttribute(FALLBACKS_ATTRIBUTE, JSON.stringify(rest));
            return candidate;
        }
    }
    image.setAttribute(FALLBACKS_ATTRIBUTE, '[]');
    return null;
}

function onImageError(event: Event): void {
    const image = event.target;
    // Only an image that opts in: a component with a data-fallbacks chain of its own walks it with its own handler
    if (!(image instanceof HTMLImageElement) || !(image.hasAttribute(HIDE_ON_ERROR_ATTRIBUTE) || image.hasAttribute(FALLBACK_TEXT_ATTRIBUTE))) {
        return;
    }
    const text = image.getAttribute(FALLBACK_TEXT_ATTRIBUTE);
    if (text !== null && image.parentElement) {
        image.parentElement.textContent = text;
        return;
    }
    const next = nextFallback(image);
    if (next !== null) {
        image.src = next;
        return;
    }
    switch (image.getAttribute(HIDE_ON_ERROR_ATTRIBUTE)) {
        case 'display':
            image.style.display = 'none';
            break;
        case 'visibility':
            image.style.visibility = 'hidden';
            break;
        case 'next-sibling': {
            image.style.display = 'none';
            const sibling = image.nextElementSibling;
            if (sibling instanceof HTMLElement || (sibling && 'style' in sibling)) {
                (sibling as HTMLElement).style.display = 'inline-flex';
            }
            break;
        }
        default:
            break;
    }
}

/** Listen for the images of `doc` that fail to load; the function returned stops it. Once per document. */
export function startImageErrorFallback(doc: Document = document): () => void {
    const existing = installed.get(doc);
    if (existing) {
        return existing;
    }
    doc.addEventListener('error', onImageError, true);
    const stop = () => {
        doc.removeEventListener('error', onImageError, true);
        installed.delete(doc);
    };
    installed.set(doc, stop);
    return stop;
}
