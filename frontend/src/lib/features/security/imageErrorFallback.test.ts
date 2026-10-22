// @vitest-environment jsdom
/**
 * H-55 v2 — the delegated image-error fallback.
 *
 * The enforced `script-src` (no 'unsafe-inline') blocks inline event-handler attributes, so the `{@html}` strings that
 * carried `onerror="this.style.display='none'"` carry `data-hide-on-error="display|visibility"` instead and ONE
 * capture-phase `error` listener on the document does the job (image `error` events do not bubble).
 *
 * The module is imported inside each test through a computed specifier, so each case fails on its own while the module
 * is missing instead of the whole file failing at transform time.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

type Mod = {
    HIDE_ON_ERROR_ATTRIBUTE: string;
    FALLBACKS_ATTRIBUTE: string;
    FALLBACK_TEXT_ATTRIBUTE: string;
    startImageErrorFallback: (doc?: Document) => () => void;
};

async function load(): Promise<Mod> {
    const spec = './imageErrorFallback';
    return (await import(/* @vite-ignore */ spec)) as Mod;
}

const removers: Array<() => void> = [];

/** Starts the fallback and remembers the remover, so no listener outlives its test. */
async function start(doc: Document = document): Promise<() => void> {
    const {startImageErrorFallback} = await load();
    const remove = startImageErrorFallback(doc);
    removers.push(remove);
    return remove;
}

function mkImg(attr: string | null, doc: Document = document): HTMLImageElement {
    const img = doc.createElement('img');
    img.setAttribute('src', '/icons/missing.png');
    if (attr !== null) img.setAttribute('data-hide-on-error', attr);
    doc.body.appendChild(img);
    return img;
}

/** An image inside its own parent, so a text fallback has a parent to write into. */
function mkImgIn(attrs: Record<string, string>): {parent: HTMLElement; img: HTMLImageElement; sibling: HTMLElement} {
    const parent = document.createElement('span');
    const img = document.createElement('img');
    img.setAttribute('src', 'u1');
    for (const [k, v] of Object.entries(attrs)) img.setAttribute(k, v);
    const sibling = document.createElement('span');
    sibling.style.display = 'none';
    parent.append(img, sibling);
    document.body.appendChild(parent);
    return {parent, img, sibling};
}

/** The remaining fallback list; a missing attribute reads as an empty list. */
function remaining(img: HTMLImageElement): unknown {
    const raw = img.getAttribute('data-fallbacks');
    return raw === null ? [] : JSON.parse(raw);
}

function fail(el: Element): void {
    el.dispatchEvent(new Event('error'));
}

afterEach(() => {
    while (removers.length) removers.pop()!();
    document.body.innerHTML = '';
    vi.restoreAllMocks();
});

describe('imageErrorFallback', () => {
    // Opt-in contract: the listener acts ONLY on an image carrying `data-hide-on-error` or `data-fallback-text`. A bare
    // `data-fallbacks` belongs to a component that walks its own chain (an `onerror` handler of its own): if the global
    // listener walked it too, both would consume the same chain and the icon would end up hidden.
    it('exports the attribute name the {@html} strings carry', async () => {
        const {HIDE_ON_ERROR_ATTRIBUTE} = await load();
        expect(HIDE_ON_ERROR_ATTRIBUTE).toBe('data-hide-on-error');
    });

    it('display: a failing image gets display none', async () => {
        await start();
        const img = mkImg('display');
        expect(img.style.display).not.toBe('none');
        fail(img);
        expect(img.style.display).toBe('none');
        expect(img.style.visibility).toBe('');
    });

    it('visibility: a failing image gets visibility hidden and keeps its box', async () => {
        await start();
        const img = mkImg('visibility');
        fail(img);
        expect(img.style.visibility).toBe('hidden');
        expect(img.style.display).not.toBe('none');
    });

    it('any other attribute value does nothing', async () => {
        await start();
        const img = mkImg('remove');
        fail(img);
        expect(img.style.display).toBe('');
        expect(img.style.visibility).toBe('');
    });

    it('an empty attribute value does nothing', async () => {
        await start();
        const img = mkImg('');
        fail(img);
        expect(img.style.display).toBe('');
        expect(img.style.visibility).toBe('');
    });

    it('an image without the attribute is left alone', async () => {
        await start();
        const img = mkImg(null);
        fail(img);
        expect(img.style.display).toBe('');
        expect(img.style.visibility).toBe('');
    });

    it('only the failing image is hidden, not its neighbours', async () => {
        await start();
        const a = mkImg('display');
        const b = mkImg('display');
        fail(a);
        expect(a.style.display).toBe('none');
        expect(b.style.display).toBe('');
    });

    it('a non-image target with the attribute is ignored', async () => {
        await start();
        const div = document.createElement('div');
        div.setAttribute('data-hide-on-error', 'display');
        const script = document.createElement('script');
        script.setAttribute('data-hide-on-error', 'visibility');
        document.body.append(div, script);
        fail(div);
        fail(script);
        expect(div.style.display).toBe('');
        expect(script.style.visibility).toBe('');
    });

    it('a non-error event on an image does nothing', async () => {
        await start();
        const img = mkImg('display');
        img.dispatchEvent(new Event('load'));
        expect(img.style.display).toBe('');
    });

    it('an image inside an {@html} string (innerHTML) is reached through the capture listener', async () => {
        await start();
        const cell = document.createElement('div');
        cell.innerHTML = '<span class="inline-flex"><img src="/x.png" alt="" data-testid="a" data-hide-on-error="display"/>' + '<img src="/y.png" alt="" data-testid="b" data-hide-on-error="visibility"/></span>';
        document.body.appendChild(cell);
        const a = cell.querySelector<HTMLImageElement>('[data-testid="a"]')!;
        const b = cell.querySelector<HTMLImageElement>('[data-testid="b"]')!;
        fail(a);
        fail(b);
        expect(a.style.display).toBe('none');
        expect(b.style.visibility).toBe('hidden');
    });

    it('an image added after the start is covered (delegation, not per-element)', async () => {
        await start();
        const cell = document.createElement('div');
        document.body.appendChild(cell);
        cell.innerHTML = '<img src="/late.png" alt="" data-hide-on-error="display"/>';
        const img = cell.querySelector('img')!;
        fail(img);
        expect(img.style.display).toBe('none');
    });

    it('the remover leaves no listener behind', async () => {
        const remove = await start();
        const img = mkImg('display');
        remove();
        fail(img);
        expect(img.style.display).toBe('');
    });

    it('registers one capture error listener on the document', async () => {
        const add = vi.spyOn(document, 'addEventListener');
        await start();
        const errorCalls = add.mock.calls.filter(([type]) => type === 'error');
        expect(errorCalls).toHaveLength(1);
        const opts = errorCalls[0]![2];
        expect(opts === true || (typeof opts === 'object' && opts !== null && opts.capture === true)).toBe(true);
    });

    it('is idempotent per document: a second call installs no second listener', async () => {
        const add = vi.spyOn(document, 'addEventListener');
        await start();
        await start();
        expect(add.mock.calls.filter(([type]) => type === 'error')).toHaveLength(1);
    });

    it('after two starts and both removers, no listener is left', async () => {
        const r1 = await start();
        const r2 = await start();
        const img = mkImg('display');
        r1();
        r2();
        fail(img);
        expect(img.style.display).toBe('');
    });

    it('can be started again after it was removed', async () => {
        const r1 = await start();
        r1();
        await start();
        const img = mkImg('display');
        fail(img);
        expect(img.style.display).toBe('none');
    });

    it('is independent per document', async () => {
        const other = document.implementation.createHTMLDocument('other');
        await start(other);
        const inOther = mkImg('display', other);
        const inMain = mkImg('display');
        fail(inOther);
        fail(inMain);
        expect(inOther.style.display).toBe('none');
        expect(inMain.style.display).toBe('');
    });

    it('pins the two new attribute names', async () => {
        const m = await load();
        expect(m.FALLBACKS_ATTRIBUTE).toBe('data-fallbacks');
        expect(m.FALLBACK_TEXT_ATTRIBUTE).toBe('data-fallback-text');
    });

    describe('data-fallback-text (provider initials)', () => {
        it('replaces the parent textContent with the text', async () => {
            await start();
            const {parent, img} = mkImgIn({'data-fallback-text': 'XX'});
            fail(img);
            expect(parent.textContent).toBe('XX');
        });

        it('never parses HTML in the value', async () => {
            await start();
            const {parent, img} = mkImgIn({'data-fallback-text': '<b>'});
            fail(img);
            expect(parent.textContent).toBe('<b>');
            expect(parent.querySelector('b')).toBeNull();
            expect(parent.children).toHaveLength(0);
        });

        it('takes precedence over data-hide-on-error', async () => {
            await start();
            const {parent, img} = mkImgIn({'data-fallback-text': 'XX', 'data-hide-on-error': 'display'});
            fail(img);
            expect(parent.textContent).toBe('XX');
            expect(img.style.display).toBe('');
        });

        it('takes precedence over data-fallbacks', async () => {
            await start();
            const {parent, img} = mkImgIn({'data-fallback-text': 'XX', 'data-fallbacks': '["u2"]'});
            fail(img);
            expect(parent.textContent).toBe('XX');
            expect(img.getAttribute('src')).toBe('u1');
        });

        it('does not touch the parent before an error', async () => {
            await start();
            const {parent, img} = mkImgIn({'data-fallback-text': 'XX'});
            expect(parent.contains(img)).toBe(true);
            expect(parent.textContent).toBe('');
        });
    });

    describe('opt-in: only data-hide-on-error and data-fallback-text make the global listener act', () => {
        /** What a spec can observe of an image: its address, its chain attribute (null when absent), its inline style. */
        function snapshot(img: HTMLImageElement): {src: string | null; fallbacks: string | null; style: string | null} {
            return {src: img.getAttribute('src'), fallbacks: img.getAttribute('data-fallbacks'), style: img.getAttribute('style')};
        }

        it('only data-fallbacks with items: nothing changes (the component owns its chain and walks it itself)', async () => {
            await start();
            const {img, sibling} = mkImgIn({'data-fallbacks': '["u2","u3"]'});
            const before = snapshot(img);
            const siblingStyle = sibling.getAttribute('style');
            fail(img);
            expect(snapshot(img), 'src, data-fallbacks and style as they were').toEqual(before);
            expect(img.getAttribute('src')).toBe('u1');
            expect(img.getAttribute('data-fallbacks')).toBe('["u2","u3"]');
            expect(sibling.getAttribute('style'), 'the next sibling is not touched either').toBe(siblingStyle);
        });

        it('only data-fallbacks="[]": nothing changes (not hidden, not rewritten)', async () => {
            await start();
            const {img} = mkImgIn({'data-fallbacks': '[]'});
            const before = snapshot(img);
            fail(img);
            expect(snapshot(img)).toEqual(before);
            expect(img.style.display).toBe('');
            expect(img.style.visibility).toBe('');
        });

        it('only data-fallbacks that is no valid list: the attribute is not normalised and nothing is hidden', async () => {
            await start();
            const {img} = mkImgIn({'data-fallbacks': '[not json'});
            const before = snapshot(img);
            fail(img);
            expect(snapshot(img)).toEqual(before);
        });

        it('a component image keeps its own onerror handler in charge: the listener sees the same event and leaves the image alone', async () => {
            await start();
            const {img} = mkImgIn({'data-fallbacks': '[]'});
            // The component's own handler: a listener on the element itself (what a Svelte `onerror={…}` becomes)
            const own = vi.fn(() => {
                img.style.display = 'none';
            });
            img.addEventListener('error', own);
            const before = snapshot(img);
            expect(before.style).toBeNull();
            fail(img);
            expect(own, 'the component’s own handler ran once').toHaveBeenCalledTimes(1);
            expect(img.getAttribute('src'), 'the global listener did not touch the address').toBe('u1');
            expect(img.getAttribute('data-fallbacks')).toBe('[]');
        });

        it('data-fallbacks + data-hide-on-error="display": the chain is walked, then the image is hidden', async () => {
            await start();
            const {img} = mkImgIn({'data-fallbacks': '["u2"]', 'data-hide-on-error': 'display'});
            fail(img);
            expect(img.getAttribute('src')).toBe('u2');
            expect(remaining(img)).toEqual([]);
            expect(img.style.display).toBe('');
            fail(img);
            expect(img.getAttribute('src')).toBe('u2');
            expect(img.style.display).toBe('none');
        });

        it('data-fallbacks + data-hide-on-error="next-sibling": the chain is walked, then the sibling shows', async () => {
            await start();
            const {img, sibling} = mkImgIn({'data-fallbacks': '["u2"]', 'data-hide-on-error': 'next-sibling'});
            fail(img);
            expect(img.getAttribute('src')).toBe('u2');
            expect(sibling.style.display).toBe('none');
            fail(img);
            expect(img.style.display).toBe('none');
            expect(sibling.style.display).toBe('inline-flex');
        });
    });

    describe('data-fallbacks (broker icon chain)', () => {
        it('moves to the next URL, keeps the rest, hides nothing', async () => {
            await start();
            const {img} = mkImgIn({'data-fallbacks': '["u2","u3"]', 'data-hide-on-error': 'display'});
            fail(img);
            expect(img.getAttribute('src')).toBe('u2');
            expect(remaining(img)).toEqual(['u3']);
            expect(img.style.display).toBe('');
        });

        it('walks the whole chain, then applies the exhausted action', async () => {
            await start();
            const {img} = mkImgIn({'data-fallbacks': '["u2","u3"]', 'data-hide-on-error': 'display'});
            fail(img);
            expect(img.getAttribute('src')).toBe('u2');
            fail(img);
            expect(img.getAttribute('src')).toBe('u3');
            expect(remaining(img)).toEqual([]);
            expect(img.style.display).toBe('');
            fail(img);
            expect(img.getAttribute('src')).toBe('u3');
            expect(img.style.display).toBe('none');
        });

        it('exhausted (empty list) with display: display none', async () => {
            await start();
            const {img} = mkImgIn({'data-fallbacks': '[]', 'data-hide-on-error': 'display'});
            fail(img);
            expect(img.getAttribute('src')).toBe('u1');
            expect(img.style.display).toBe('none');
        });

        it('exhausted (attribute missing) with display: display none', async () => {
            await start();
            const {img} = mkImgIn({'data-hide-on-error': 'display'});
            fail(img);
            expect(img.style.display).toBe('none');
        });

        it('exhausted (invalid JSON) with display: display none', async () => {
            await start();
            const {img} = mkImgIn({'data-fallbacks': '[not json', 'data-hide-on-error': 'display'});
            fail(img);
            expect(img.getAttribute('src')).toBe('u1');
            expect(img.style.display).toBe('none');
        });

        it('exhausted (JSON that is not an array) with display: display none', async () => {
            await start();
            const {img} = mkImgIn({'data-fallbacks': '{"a":"u2"}', 'data-hide-on-error': 'display'});
            fail(img);
            expect(img.getAttribute('src')).toBe('u1');
            expect(img.style.display).toBe('none');
        });

        it('next-sibling: hides the image and shows the next element sibling as inline-flex', async () => {
            await start();
            const {img, sibling} = mkImgIn({'data-fallbacks': '[]', 'data-hide-on-error': 'next-sibling'});
            expect(sibling.style.display).toBe('none');
            fail(img);
            expect(img.style.display).toBe('none');
            expect(sibling.style.display).toBe('inline-flex');
        });

        it('next-sibling: does not show the sibling while the chain still has a URL', async () => {
            await start();
            const {img, sibling} = mkImgIn({'data-fallbacks': '["u2"]', 'data-hide-on-error': 'next-sibling'});
            fail(img);
            expect(img.getAttribute('src')).toBe('u2');
            expect(img.style.display).toBe('');
            expect(sibling.style.display).toBe('none');
        });

        it('next-sibling without a next element sibling: hides the image, no throw', async () => {
            await start();
            const parent = document.createElement('span');
            const img = document.createElement('img');
            img.setAttribute('src', 'u1');
            img.setAttribute('data-hide-on-error', 'next-sibling');
            parent.append(img, document.createTextNode('text only'));
            document.body.appendChild(parent);
            expect(() => fail(img)).not.toThrow();
            expect(img.style.display).toBe('none');
        });

        it('skips non-string entries and never assigns them to src', async () => {
            await start();
            const {img} = mkImgIn({'data-fallbacks': '[42,null,{"a":1},"u3"]', 'data-hide-on-error': 'display'});
            fail(img);
            expect(img.getAttribute('src')).toBe('u3');
            expect(remaining(img)).toEqual([]);
            expect(img.style.display).toBe('');
        });

        it('a list of only non-string entries counts as exhausted', async () => {
            await start();
            const {img} = mkImgIn({'data-fallbacks': '[1,null]', 'data-hide-on-error': 'display'});
            fail(img);
            expect(img.getAttribute('src')).toBe('u1');
            expect(img.style.display).toBe('none');
        });
    });
});
