import {decimalArrowStep, resetDecimalArrowHold} from '$lib/utils/core/parseDecimalInput';

/**
 * Arrow-key stepping for any numeric input, with hold-to-accelerate.
 *
 * `<input type="number">` gives arrows for free but at a fixed step, so reaching a
 * value three orders of magnitude away means holding the key for a minute; text
 * inputs (used wherever a decimal has to survive the user's locale) get no arrows
 * at all. This action gives both the same behaviour, so a number behaves like a
 * number everywhere in the app rather than depending on which field it landed in.
 *
 * It writes to the element and dispatches `input`, which is exactly what `bind:value`
 * listens for — no change is needed at the call site beyond `use:numericArrows`.
 */
export interface NumericArrowsOptions {
    /**
     * Smallest move, and the rung the acceleration starts from. Default 1: arrows are
     * for the whole units, the keyboard is for the decimals.
     */
    step?: number;
    /** Lower bound. Falls back to the element's own `min` attribute. */
    min?: number;
    /** Upper bound. Falls back to the element's own `max` attribute. */
    max?: number;
    /** Set to false to leave the arrows to the browser. */
    enabled?: boolean;
}

function attributeNumber(raw: string): number | undefined {
    if (raw === '') return undefined;
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : undefined;
}

export function numericArrows(node: HTMLInputElement, options: NumericArrowsOptions = {}) {
    let current = options;

    function onKeydown(event: KeyboardEvent) {
        if (current.enabled === false || node.disabled || node.readOnly) return;
        const stepped = decimalArrowStep(event, node.value, current.step ?? 1);
        if (stepped === null) return;

        const min = current.min ?? attributeNumber(node.min);
        const max = current.max ?? attributeNumber(node.max);
        let next = Number(stepped);
        if (!Number.isFinite(next)) return;
        if (min !== undefined && next < min) next = min;
        if (max !== undefined && next > max) next = max;

        // Keep the decimals the step produced (0.10, not 0.1) unless clamping changed
        // the number, which only ever lands it on a bound the caller wrote itself.
        node.value = next === Number(stepped) ? stepped : String(next);
        node.dispatchEvent(new Event('input', {bubbles: true}));
        node.dispatchEvent(new Event('change', {bubbles: true}));
    }

    // The run ends when the key comes up or the field is left; without this, coming
    // back to the field later would resume at whatever magnitude it stopped at.
    function endHold() {
        resetDecimalArrowHold();
    }

    node.addEventListener('keydown', onKeydown);
    node.addEventListener('keyup', endHold);
    node.addEventListener('blur', endHold);

    return {
        update(next: NumericArrowsOptions = {}) {
            current = next;
        },
        destroy() {
            node.removeEventListener('keydown', onKeydown);
            node.removeEventListener('keyup', endHold);
            node.removeEventListener('blur', endHold);
        },
    };
}
