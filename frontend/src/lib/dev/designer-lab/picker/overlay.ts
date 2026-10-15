/**
 * Designer Lab — picking mode in an app tab: a transparent veil over the page, a frame on the element under the
 * pointer, a click to pick it. Loaded only when a pick starts.
 *
 * The veil takes every pointer event, so the element below is not hovered (its colours are the resting ones) and a
 * click never reaches the app; events are stopped at the window in the capture phase, before any app listener sees
 * them. The wheel still scrolls what is under the pointer, and Escape cancels. The veil, frame and label carry only
 * inline styles, which the stylesheet engine never rewrites.
 */

import {OWN_ATTR} from '../engine/vars';
import {isPendingStart, writePick, type PickMessage} from '../pick';
import {retarget, testidChain} from './anchor';
import {describeElement} from './describe';

const BLOCKED = ['pointerdown', 'pointerup', 'pointerover', 'pointerout', 'mousedown', 'mouseup', 'mousemove', 'mouseover', 'mouseout', 'dblclick', 'auxclick', 'contextmenu', 'touchstart', 'touchmove', 'touchend'] as const;
const KEYS = ['keydown', 'keyup', 'keypress'] as const;
const OPTIONS: AddEventListenerOptions = {capture: true, passive: false};

let armedId: string | null = null;
let nodes: {veil: HTMLDivElement; frame: HTMLDivElement; label: HTMLDivElement} | null = null;
let busy = false;
let frameRequest = 0;
let lastPoint = {x: 0, y: 0};

export function isArmed(): boolean {
    return armedId !== null;
}

function block(event: Event): void {
    event.preventDefault();
    event.stopImmediatePropagation();
}

function styled(css: string): HTMLDivElement {
    const el = document.createElement('div');
    el.setAttribute(OWN_ATTR, '');
    el.setAttribute('style', css);
    return el;
}

function underPointer(x: number, y: number): Element | null {
    for (const el of document.elementsFromPoint(x, y)) {
        if (!el.closest(`[${OWN_ATTR}]`)) return retarget(el);
    }
    return null;
}

function highlight(): void {
    if (!nodes) return;
    const el = underPointer(lastPoint.x, lastPoint.y);
    const {frame, label} = nodes;
    if (!el) {
        frame.style.display = label.style.display = 'none';
        return;
    }
    const r = el.getBoundingClientRect();
    Object.assign(frame.style, {display: 'block', left: `${r.left}px`, top: `${r.top}px`, width: `${r.width}px`, height: `${r.height}px`});
    const id = testidChain(el)[0];
    label.textContent = id ? `${el.tagName.toLowerCase()} · ${id}` : el.tagName.toLowerCase();
    Object.assign(label.style, {display: 'block', left: `${Math.max(0, r.left)}px`, top: `${r.top > 22 ? r.top - 22 : r.bottom + 2}px`});
}

function scheduleHighlight(): void {
    if (!frameRequest)
        frameRequest = requestAnimationFrame(() => {
            frameRequest = 0;
            highlight();
        });
}

function onMove(event: PointerEvent): void {
    block(event);
    lastPoint = {x: event.clientX, y: event.clientY};
    scheduleHighlight();
}

function scrollableAt(el: Element | null): Element {
    for (let cur = el; cur && cur !== document.body && cur !== document.documentElement; cur = cur.parentElement) {
        const s = getComputedStyle(cur);
        const scrollsY = /(auto|scroll|overlay)/.test(s.overflowY) && cur.scrollHeight > cur.clientHeight;
        const scrollsX = /(auto|scroll|overlay)/.test(s.overflowX) && cur.scrollWidth > cur.clientWidth;
        if (scrollsX || scrollsY) return cur;
    }
    return document.scrollingElement ?? document.documentElement;
}

function onWheel(event: WheelEvent): void {
    block(event);
    const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? window.innerHeight : 1;
    scrollableAt(underPointer(event.clientX, event.clientY)).scrollBy({left: event.deltaX * unit, top: event.deltaY * unit});
    scheduleHighlight();
}

function onKey(event: KeyboardEvent): void {
    if (event.metaKey || event.ctrlKey) return;
    block(event);
    if (event.type === 'keydown' && event.key === 'Escape') {
        const id = armedId;
        teardown();
        if (id) writePick({op: 'cancel', id, at: Date.now()});
    }
}

function onClick(event: MouseEvent): void {
    block(event);
    const id = armedId;
    if (busy || !id || event.button !== 0) return;
    const el = underPointer(event.clientX, event.clientY);
    if (!el) return;
    busy = true;
    describeElement(el, {x: event.clientX, y: event.clientY})
        .then((element) => writePick({op: 'result', id, at: Date.now(), element}))
        .catch((error: unknown) => {
            console.error('Designer Lab: the element could not be described', error);
            writePick({op: 'cancel', id, at: Date.now()});
        })
        .finally(() => {
            busy = false;
            if (armedId === id) teardown();
        });
}

function teardown(): void {
    armedId = null;
    for (const type of BLOCKED) window.removeEventListener(type, block, OPTIONS);
    for (const type of KEYS) window.removeEventListener(type, onKey as EventListener, OPTIONS);
    window.removeEventListener('pointermove', onMove as EventListener, OPTIONS);
    window.removeEventListener('click', onClick as EventListener, OPTIONS);
    window.removeEventListener('wheel', onWheel as EventListener, OPTIONS);
    if (frameRequest) cancelAnimationFrame(frameRequest);
    frameRequest = 0;
    if (nodes) for (const node of Object.values(nodes)) node.remove();
    nodes = null;
}

/** Enter picking mode for request `id`. Idempotent per id; a new id replaces the current request. */
export function arm(id: string): void {
    if (armedId === id) return;
    if (armedId) teardown();
    armedId = id;
    const veil = styled('position:fixed;inset:0;z-index:2147483646;cursor:crosshair;background:transparent;');
    veil.setAttribute('data-testid', 'lf-lab-pick-veil');
    const frame = styled('position:fixed;z-index:2147483647;pointer-events:none;box-sizing:border-box;border:2px solid #d6008f;background:rgba(214,0,143,0.08);display:none;');
    const label = styled(
        "position:fixed;z-index:2147483647;pointer-events:none;font:12px/1.5 var(--font-mono, 'LF Flags', ui-monospace, monospace);color:#ffffff;background:#1c1c1e;padding:1px 6px;border-radius:4px;white-space:nowrap;max-width:70vw;overflow:hidden;text-overflow:ellipsis;display:none;",
    );
    document.body.append(veil, frame, label);
    nodes = {veil, frame, label};
    for (const type of BLOCKED) window.addEventListener(type, block, OPTIONS);
    for (const type of KEYS) window.addEventListener(type, onKey as EventListener, OPTIONS);
    window.addEventListener('pointermove', onMove as EventListener, OPTIONS);
    window.addEventListener('click', onClick as EventListener, OPTIONS);
    window.addEventListener('wheel', onWheel as EventListener, OPTIONS);
}

/** Follow the Lab: join a pending request; leave on its cancel, on any result (another tab picked), or when the key is cleared. */
export function follow(message: PickMessage | null): void {
    if (message && isPendingStart(message)) arm(message.id);
    else if (armedId && (!message || message.op === 'result' || message.id === armedId)) teardown();
}
