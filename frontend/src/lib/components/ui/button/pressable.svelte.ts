/**
 * `use:pressable` — the behaviour of the standard button (project 85, BTN-0): tap, long press, mouse, keyboard, the
 * name, the disabled reason. It goes on any clickable element: `Button.svelte` uses it, and so can a menu item, a tab
 * or an option that must show why it is off.
 *
 * | Who | Gesture | Effect |
 * |---|---|---|
 * | finger, pen | tap (released before 500 ms) | the action, on release (the browser's `click`) |
 * | | long press (500 ms within 10 px) | the name (and the help), **no action**: the click that follows is dropped. The name opens above the finger, below only when there is no room above |
 * | | moves over 10 px | nothing: a scroll |
 * | | a tap elsewhere | closes the name, and does its own work |
 * | mouse | rest 500 ms | the name |
 * | | click | the action; closes the name and cancels a pending one until the pointer leaves and comes back |
 * | keyboard | focus brought by Tab | the name, at once (a focus given back by a closing dialog shows nothing) |
 * | | Enter, Space | the action |
 * | | Esc | closes the name |
 *
 * - **Touch is told by `pointerType`**, not by a media query: Playwright's `click()` stays a mouse click in the
 *   `mobile` project, and a tablet with a mouse behaves as a computer.
 * - **A plain `click` with no pointer sequence acts** (a test's `fireEvent.click`, a screen reader, `element.click()`).
 * - **Disabled with a reason** (`reason`): the element keeps `aria-disabled`, the focus and the events; a tap, a
 *   click or a keyboard focus show the reason, and the click is stopped (`preventDefault`: a `submit` does not send).
 * - **Disabled without a reason but reachable** (`off`, an icon-only button): the same, with the name alone.
 * - **Busy**: clicks are stopped (`preventDefault`, a `submit` included), nothing starts twice.
 * - **When the name shows** (77 SEL-D2; 85, R2): only when the word is out of view, in bold on the first line, with the
 *   help or the reason from the second. With the word in view the bubble is the help or the reason alone, on a long press
 *   too; with neither there is no bubble (the long press still does not act).
 * - **A help is the element's description** to a screen reader (`aria-describedby`); the name stays the name.
 * - **A row whose parts carry their own hover tips** (`partTips`: a `Tooltip insideControl` on a badge or a ⚠ inside it):
 *   the parts answer the mouse; this behaviour gives their texts, as the row's `help`, to the finger (long press) and to
 *   the keyboard, and to a screen reader as every help. A row with no help is an ordinary one: a long press on it drops
 *   no click.
 *
 * The click listener runs in the capture phase, so it is ahead of every handler of the element itself (Svelte
 * delegates `onclick` to the root, a legacy `on:click` sits on the element): a dropped click never reaches them.
 * The tooltip is `Tooltip.svelte` in its external-target mode, mounted in the `body` on its first use.
 */
import {mount, unmount} from 'svelte';
import type {Action} from 'svelte/action';
import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
import {escapeHtml} from '$lib/utils/inlineMath';

/** A long press lasts this long, the same everywhere in the app. */
export const LONG_PRESS_MS = 500;
/** A finger that moves more than this is scrolling, not pressing. */
export const MOVE_TOLERANCE_PX = 10;
/** The mouse rests this long before the name shows (P-32, the delay of every tooltip in the app). */
export const HOVER_DELAY_MS = 500;
/** After a long press, the click the browser may still send within this window is dropped. */
export const LONG_PRESS_CLICK_WINDOW_MS = 400;
/** The pointer may cross the gap from the element to the tooltip body within this delay. */
const HOVER_LEAVE_BRIDGE_MS = 150;

export type TipPosition = 'top' | 'bottom' | 'left' | 'right';

export interface PressableOptions {
    /** The name: the tooltip's bold line, and what a long press shows. */
    label: string;
    /** An explanation shown under the name (plain text), and the element's description to a screen reader. */
    help?: string;
    /** The help holds `$…$` inline maths (KaTeX), as `Tooltip`. */
    math?: boolean;
    /** Disabled with a reason: the reason shown at the first tap, click or keyboard focus; the click is stopped. */
    reason?: string;
    /** Disabled and still reachable, without a reason (an icon-only button): the name shown at the first tap, click or
     *  keyboard focus, the click stopped. An icon's name must reach the finger even while it is off. */
    off?: boolean;
    /** Busy: clicks are stopped. */
    busy?: boolean;
    /** Whether the word is in view now. Absent: the word is never in view (an icon-only element). */
    wordVisible?: (element: HTMLElement) => boolean;
    /** Mouse and keyboard side of the tooltip; a finger always opens above (below only without room). */
    tipPosition?: TipPosition;
    /** A row whose parts carry their own hover tips (`Tooltip insideControl`): no tip from here on a mouse rest, and
     *  without a help a long press is an ordinary press (85 BTN-0c, D16). */
    partTips?: boolean;
    /** The action, run on a click the behaviour lets through. */
    onpress?: (event: MouseEvent) => void;
}

type TipSource = 'touch' | 'mouse' | 'keyboard' | 'reason';

interface Press {
    x: number;
    y: number;
    timer: ReturnType<typeof setTimeout> | null;
    fired: boolean;
}

/** The tooltip's props, reactive: the mounted Tooltip follows them. */
interface TipProps {
    trigger: HTMLElement | null;
    open: boolean;
    html: string;
    math: boolean;
    position: TipPosition;
    onbodypointer: (inside: boolean) => void;
}

/** The ids of the descriptions, unique in the page. */
let describedCount = 0;

/** Only one name is open in the whole app at a time. */
let closeOpenTip: (() => void) | null = null;

/** The focus arriving now comes from Tab (a keyboard user moving), not from a click or a dialog giving it back. */
let tabbing = false;
let tabListenerInstalled = false;

function installTabListener(): void {
    if (tabListenerInstalled || typeof document === 'undefined') return;
    tabListenerInstalled = true;
    document.addEventListener(
        'keydown',
        (event) => {
            if (event.key !== 'Tab') return;
            tabbing = true;
            setTimeout(() => (tabbing = false), 0);
        },
        true,
    );
}

/** The tooltip's HTML for these options, or '' when there is nothing worth showing. The name is the first line, in bold,
 *  only when the word is out of view: above a word in view there is no title, the text alone. Exported for its tests. */
export function tipHtml(options: PressableOptions, wordInView: boolean): string {
    const name = wordInView ? '' : `<strong>${escapeHtml(options.label)}</strong>`;
    const text = escapeHtml(options.reason || (options.off ? '' : options.help) || '');
    return [name, text].filter(Boolean).join('\n');
}

export const pressable: Action<HTMLElement, PressableOptions> = (element, initial) => {
    let options = initial;
    let press: Press | null = null;
    let hoverTimer: ReturnType<typeof setTimeout> | null = null;
    let leaveTimer: ReturnType<typeof setTimeout> | null = null;
    /** Clicked by the mouse: no name from resting until the pointer leaves. */
    let quiet = false;
    /** The mouse went down on the element: the click that follows is the mouse's. */
    let mouseDown = false;
    let tipSource: TipSource | null = null;
    /** The pointer is over the tooltip body (mouse): a leave of the element does not close it. */
    let overTip = false;
    let tipProps: TipProps | null = null;
    let tipInstance: ReturnType<typeof mount> | null = null;
    /** The help as the hidden text the element's `aria-describedby` points at. */
    let description: HTMLElement | null = null;

    installTabListener();
    describe();

    /** Adds or removes the description among the ids of the element's `aria-describedby`: the caller's own stay. */
    function listDescription(id: string, listed: boolean) {
        const ids = (element.getAttribute('aria-describedby') ?? '').split(/\s+/).filter((other) => other && other !== id);
        if (listed) ids.push(id);
        if (ids.length > 0) element.setAttribute('aria-describedby', ids.join(' '));
        else element.removeAttribute('aria-describedby');
    }

    function dropDescription() {
        if (!description) return;
        listDescription(description.id, false);
        description.remove();
        description = null;
    }

    /** The help is the element's description. The text stays out of the element, so out of its name. */
    function describe() {
        if (!options.help) {
            dropDescription();
            return;
        }
        if (!description) {
            description = document.createElement('span');
            description.id = `lf-described-${++describedCount}`;
            description.hidden = true;
            document.body.appendChild(description);
            listDescription(description.id, true);
        }
        description.textContent = options.help;
    }

    /** `partTips` with nothing to say: the long press has no tip to show, so it must not drop the click either. */
    const isPlainRow = () => !!options.partTips && !isOff() && !tipHtml(options, wordInView());

    const wordInView = () => options.wordVisible?.(element) ?? false;
    /** Off and reachable: a reason, or an icon's name. */
    const isOff = () => !!options.reason || !!options.off;

    function clearHover() {
        if (hoverTimer) clearTimeout(hoverTimer);
        hoverTimer = null;
    }

    function clearLeave() {
        if (leaveTimer) clearTimeout(leaveTimer);
        leaveTimer = null;
    }

    function ensureTip(): TipProps {
        if (tipProps) return tipProps;
        const props: TipProps = $state({
            trigger: element,
            open: false,
            html: '',
            math: false,
            position: 'top',
            onbodypointer: (inside: boolean) => {
                overTip = inside;
                if (inside) clearLeave();
                else if (tipSource === 'mouse') scheduleLeave();
            },
        });
        tipProps = props;
        tipInstance = mount(Tooltip, {target: document.body, props});
        return props;
    }

    /** Opens the name; `false` when there is nothing worth showing. */
    function showTip(source: TipSource): boolean {
        const html = tipHtml(options, wordInView());
        if (!html) return false;
        if (closeOpenTip && closeOpenTip !== hideTip) closeOpenTip();
        const tip = ensureTip();
        tip.html = html;
        tip.math = !!options.math;
        tip.position = source === 'touch' ? 'top' : (options.tipPosition ?? 'top');
        tip.open = true;
        tipSource = source;
        closeOpenTip = hideTip;
        document.addEventListener('pointerdown', handleOutsidePointer, true);
        document.addEventListener('keydown', handleEscape, true);
        return true;
    }

    function hideTip() {
        clearLeave();
        overTip = false;
        tipSource = null;
        if (tipProps) tipProps.open = false;
        if (closeOpenTip === hideTip) closeOpenTip = null;
        document.removeEventListener('pointerdown', handleOutsidePointer, true);
        document.removeEventListener('keydown', handleEscape, true);
    }

    function scheduleLeave() {
        clearLeave();
        leaveTimer = setTimeout(() => {
            leaveTimer = null;
            if (!overTip) hideTip();
        }, HOVER_LEAVE_BRIDGE_MS);
    }

    /** A tap or a click elsewhere closes the name, and goes on doing its own work. */
    function handleOutsidePointer(event: PointerEvent) {
        const target = event.target instanceof Node ? event.target : null;
        if (target && element.contains(target)) return;
        if (target && target instanceof Element && target.closest('[role="tooltip"]')) return;
        hideTip();
    }

    function handleEscape(event: KeyboardEvent) {
        if (event.key === 'Escape') hideTip();
    }

    function endPress() {
        if (press?.timer) clearTimeout(press.timer);
        if (press) press.timer = null;
        element.classList.remove('lf-pressing');
    }

    function onPointerDown(event: PointerEvent) {
        if (event.pointerType === 'mouse') {
            // A mouse press: the click acts; a stale press mark never lingers.
            endPress();
            press = null;
            clearHover();
            mouseDown = true;
            return;
        }
        endPress();
        if (tipSource && tipSource !== 'reason') hideTip();
        press = null;
        if (isPlainRow()) return;
        const current: Press = {x: event.clientX, y: event.clientY, timer: null, fired: false};
        press = current;
        if (options.busy) return;
        element.classList.add('lf-pressing');
        current.timer = setTimeout(() => {
            current.timer = null;
            current.fired = true;
            element.classList.remove('lf-pressing');
            showTip(isOff() ? 'reason' : 'touch');
        }, LONG_PRESS_MS);
    }

    function onPointerMove(event: PointerEvent) {
        if (!press || press.fired || event.pointerType === 'mouse') return;
        if (Math.hypot(event.clientX - press.x, event.clientY - press.y) > MOVE_TOLERANCE_PX) {
            endPress();
            press = null;
        }
    }

    /** The finger left (released, or the browser took the gesture over: a scroll, its own long-press handling). */
    function onPointerEnd(event: PointerEvent) {
        if (event.pointerType === 'mouse') return;
        endPress();
        const released = press;
        if (released?.fired) {
            // Kept only for the click the browser may send right after the release. A cancel after the long press
            // fired (a browser that ends the gesture itself) keeps the window too: a late click must not act.
            setTimeout(() => {
                if (press === released) press = null;
            }, LONG_PRESS_CLICK_WINDOW_MS);
        } else {
            press = null;
        }
    }

    /** The browser's menu of a long press (Android) never opens on the element, and the event does not reach the row
     *  around it (a table row's menu would open over the name). A mouse's right click goes up as always. */
    function onContextMenu(event: MouseEvent) {
        if (!press) return;
        event.preventDefault();
        event.stopPropagation();
    }

    function onClick(event: MouseEvent) {
        if (press?.fired) {
            press = null;
            event.preventDefault();
            event.stopImmediatePropagation();
            return;
        }
        press = null;
        if (isOff()) {
            event.preventDefault();
            event.stopImmediatePropagation();
            showTip('reason');
            return;
        }
        if (options.busy) {
            event.preventDefault();
            event.stopImmediatePropagation();
            return;
        }
        clearHover();
        hideTip();
        quiet = mouseDown;
        mouseDown = false;
        options.onpress?.(event);
    }

    function onPointerEnter(event: PointerEvent) {
        if (event.pointerType !== 'mouse') return;
        clearLeave();
        if (options.partTips || quiet || tipSource) return;
        clearHover();
        hoverTimer = setTimeout(() => {
            hoverTimer = null;
            showTip('mouse');
        }, HOVER_DELAY_MS);
    }

    function onPointerLeave(event: PointerEvent) {
        if (event.pointerType !== 'mouse') return;
        clearHover();
        quiet = false;
        if (tipSource === 'mouse' || tipSource === 'keyboard') scheduleLeave();
    }

    function onFocus() {
        if (tabbing) showTip(isOff() ? 'reason' : 'keyboard');
    }

    function onBlur() {
        if (tipSource) hideTip();
    }

    const listeners: [string, EventListener, boolean][] = [
        ['pointerdown', onPointerDown as EventListener, false],
        ['pointermove', onPointerMove as EventListener, false],
        ['pointerup', onPointerEnd as EventListener, false],
        ['pointercancel', onPointerEnd as EventListener, false],
        ['pointerenter', onPointerEnter as EventListener, false],
        ['pointerleave', onPointerLeave as EventListener, false],
        ['contextmenu', onContextMenu as EventListener, false],
        ['click', onClick as EventListener, true],
        ['focus', onFocus as EventListener, false],
        ['blur', onBlur as EventListener, false],
    ];
    for (const [type, listener, capture] of listeners) element.addEventListener(type, listener, capture);

    return {
        update(next: PressableOptions) {
            options = next;
            describe();
            if (!tipSource || !tipProps) return;
            // A reason that went away, or a name that has nothing left to say, closes; otherwise the text follows.
            if (tipSource === 'reason' && !isOff()) {
                hideTip();
                return;
            }
            const html = tipHtml(options, wordInView());
            if (html) tipProps.html = html;
            else hideTip();
        },
        destroy() {
            for (const [type, listener, capture] of listeners) element.removeEventListener(type, listener, capture);
            endPress();
            clearHover();
            hideTip();
            if (tipInstance) void unmount(tipInstance);
            tipInstance = null;
            tipProps = null;
            dropDescription();
        },
    };
};
