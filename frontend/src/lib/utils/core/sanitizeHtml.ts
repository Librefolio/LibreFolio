/**
 * Sanitize HTML that mixes trusted markup with values we did not write ourselves.
 *
 * `escapeHtml` (`./escapeHtml`) is the tool for a value going *into* hand-built markup. This is
 * the tool for the other side: a sink that renders a whole string with `{@html}` when that string
 * is assembled in many places (toasts, tooltips, validation messages) and a single missed
 * `escapeHtml` would otherwise become script. DOMPurify keeps the markup those strings are made
 * of — spans with classes and inline styles, flag emoji, images, inline SVG icons, KaTeX output,
 * `data-*` attributes, relative links — and drops what can run: event-handler attributes,
 * `<script>`, `javascript:` URLs.
 *
 * Browser only: the app runs with `ssr = false`, and DOMPurify needs a DOM.
 */
import DOMPurify from 'dompurify';

export function sanitizeHtml(html: string): string {
    return DOMPurify.sanitize(html);
}
