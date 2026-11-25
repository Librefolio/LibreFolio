/**
 * A finger on a `use:pressable` element, in a component test on the real clock (85 BTN-0c, D16).
 *
 * jsdom has no PointerEvent: a pointer event is a MouseEvent of that name with `pointerType` defined on it, all that
 * `pressable` reads. Nothing is slept: the press is held until its tooltip is in the page.
 */
import {fireEvent, waitFor} from './component';

export function touch(element: Element, type: 'pointerdown' | 'pointerup'): void {
    const event = new MouseEvent(type, {bubbles: true, cancelable: true, clientX: 10, clientY: 10});
    Object.defineProperty(event, 'pointerType', {value: 'touch'});
    element.dispatchEvent(event);
}

/** Hold until the tooltip shows, release, and let the browser's late click come: a long press. Returns the tip's text. */
export async function longPress(element: Element): Promise<string> {
    touch(element, 'pointerdown');
    const tip = await waitFor(
        () => {
            const node = document.querySelector<HTMLElement>('[role="tooltip"]');
            if (!node) throw new Error('the long press shows nothing');
            return node;
        },
        {timeout: 2_000},
    );
    const text = tip.textContent ?? '';
    touch(element, 'pointerup');
    await fireEvent.click(element);
    return text;
}
