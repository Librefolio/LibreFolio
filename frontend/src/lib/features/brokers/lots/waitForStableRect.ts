/**
 * Resolves once the element's rectangle has not moved for two frames — and has a height. A rectangle still 0 high is
 * an element whose intro (`transition:slide`) has not started: "two identical frames" there would let the scroll go
 * to where the element will not be, and Chrome cuts a smooth scroll at the limit of that moment. `maxFrames` ends
 * the wait for an element that never opens.
 */
export function waitForStableRect(el: HTMLElement, maxFrames = 180): Promise<void> {
    return new Promise((resolve) => {
        let lastRect: DOMRect | null = null;
        let stableFrames = 0;
        let frame = 0;

        function check() {
            frame++;
            const rect = el.getBoundingClientRect();
            const same = lastRect !== null && rect.height > 0 && rect.top === lastRect.top && rect.left === lastRect.left && rect.width === lastRect.width && rect.height === lastRect.height;
            stableFrames = same ? stableFrames + 1 : 0;
            lastRect = rect;

            if (stableFrames >= 2 || frame >= maxFrames) {
                resolve();
                return;
            }
            requestAnimationFrame(check);
        }

        requestAnimationFrame(check);
    });
}
