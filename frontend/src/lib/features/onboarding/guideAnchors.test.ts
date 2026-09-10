import {describe, expect, it} from 'vitest';

import {createGuideAnchorAction, createGuideAnchorRegistry} from './guideAnchors.svelte';

/**
 * Guide anchor registry — lifecycle, staleness and duplicate-id handling.
 *
 * The registry only ever reads `element.isConnected` off whatever it is given, so a
 * plain object shaped like that (never a full jsdom node) is enough to exercise every
 * branch here without paying for a DOM environment. `createGuideAnchorAction` is a
 * plain function too — calling it directly is exactly what Svelte's own action
 * lifecycle does (mount -> optional `update`s -> `destroy`), just without a real
 * component wrapping it.
 */

function fakeNode(connected = true): HTMLElement {
    return {isConnected: connected} as unknown as HTMLElement;
}

describe('guide anchor registry — register/get/has', () => {
    it('registers an element and makes it retrievable by id', () => {
        const registry = createGuideAnchorRegistry();
        const node = fakeNode();

        registry.register('step-1', node);

        expect(registry.get('step-1')).toBe(node);
        expect(registry.has('step-1')).toBe(true);
    });

    it('returns null and reports absent for an id nothing registered', () => {
        const registry = createGuideAnchorRegistry();
        expect(registry.get('missing')).toBeNull();
        expect(registry.has('missing')).toBe(false);
    });

    it('rejects an empty/whitespace-only id', () => {
        const registry = createGuideAnchorRegistry();
        expect(() => registry.register('', fakeNode())).toThrow('Guide anchor ID cannot be empty');
        expect(() => registry.register('   ', fakeNode())).toThrow('Guide anchor ID cannot be empty');
    });

    it('bumps the revision on every registration, so a $derived reading it can react', () => {
        const registry = createGuideAnchorRegistry();
        const before = registry.revision;

        registry.register('step-1', fakeNode());
        expect(registry.revision).toBe(before + 1);

        registry.register('step-2', fakeNode());
        expect(registry.revision).toBe(before + 2);
    });
});

describe('guide anchor registry — unregister/destroy', () => {
    it('the unregister function returned by register() removes exactly that anchor', () => {
        const registry = createGuideAnchorRegistry();
        const unregister = registry.register('step-1', fakeNode());

        unregister();

        expect(registry.get('step-1')).toBeNull();
        expect(registry.has('step-1')).toBe(false);
    });

    it('a stale unregister (superseded by a re-register under the same id) is a no-op', () => {
        const registry = createGuideAnchorRegistry();
        const firstUnregister = registry.register('step-1', fakeNode());
        const secondNode = fakeNode();
        registry.register('step-1', secondNode); // same id, different element — e.g. re-mount

        // The first registration's cleanup must not evict the element that replaced it.
        firstUnregister();

        expect(registry.get('step-1')).toBe(secondNode);
    });

    it('clear() empties every anchor and bumps the revision once', () => {
        const registry = createGuideAnchorRegistry();
        registry.register('step-1', fakeNode());
        registry.register('step-2', fakeNode());
        const before = registry.revision;

        registry.clear();

        expect(registry.get('step-1')).toBeNull();
        expect(registry.get('step-2')).toBeNull();
        expect(registry.revision).toBe(before + 1);
    });

    it('clear() on an already-empty registry does not bump the revision', () => {
        const registry = createGuideAnchorRegistry();
        const before = registry.revision;
        registry.clear();
        expect(registry.revision).toBe(before);
    });
});

describe('guide anchor registry — stale (disconnected) nodes', () => {
    it('get() treats a disconnected element as absent and evicts it', () => {
        const registry = createGuideAnchorRegistry();
        const node = fakeNode(false); // never attached / already removed from the DOM
        registry.register('step-1', node);

        expect(registry.get('step-1')).toBeNull();
        // The eviction is real, not just a read-time illusion: has() re-checks and still
        // reports absent, and a second read does not re-throw or re-scan a dead entry.
        expect(registry.has('step-1')).toBe(false);
        expect(registry.get('step-1')).toBeNull();
    });

    it('a node that disconnects after registration is dropped on the next read', () => {
        const registry = createGuideAnchorRegistry();
        const node = fakeNode(true);
        registry.register('step-1', node);
        expect(registry.get('step-1')).toBe(node);

        (node as unknown as {isConnected: boolean}).isConnected = false;

        expect(registry.get('step-1')).toBeNull();
        expect(registry.has('step-1')).toBe(false);
    });
});

describe('guide anchor registry — duplicate ids', () => {
    it('registering a second element under the same id replaces the first', () => {
        const registry = createGuideAnchorRegistry();
        const first = fakeNode();
        const second = fakeNode();

        registry.register('step-1', first);
        registry.register('step-1', second);

        expect(registry.get('step-1')).toBe(second);
    });

    it('unregistering the *current* holder of a duplicated id actually removes it', () => {
        const registry = createGuideAnchorRegistry();
        const first = fakeNode();
        registry.register('step-1', first);
        const secondUnregister = registry.register('step-1', fakeNode());

        secondUnregister();

        expect(registry.get('step-1')).toBeNull();
    });
});

describe('createGuideAnchorAction — the Svelte action wrapper', () => {
    it('registers on mount, re-registers under a new id on update, and cleans up on destroy', () => {
        const registry = createGuideAnchorRegistry();
        const guideAnchor = createGuideAnchorAction(registry);
        const node = fakeNode();

        const lifecycle = guideAnchor(node, 'step-1');
        expect(registry.get('step-1')).toBe(node);

        lifecycle?.update?.('step-1'); // same id — must not unregister/re-register
        expect(registry.get('step-1')).toBe(node);

        lifecycle?.update?.('step-2');
        expect(registry.get('step-1')).toBeNull();
        expect(registry.get('step-2')).toBe(node);

        lifecycle?.destroy?.();
        expect(registry.get('step-2')).toBeNull();
    });

    it('two actions on two nodes are independent — destroying one leaves the other registered', () => {
        const registry = createGuideAnchorRegistry();
        const guideAnchor = createGuideAnchorAction(registry);
        const nodeA = fakeNode();
        const nodeB = fakeNode();

        const a = guideAnchor(nodeA, 'a');
        const b = guideAnchor(nodeB, 'b');

        a?.destroy?.();

        expect(registry.get('a')).toBeNull();
        expect(registry.get('b')).toBe(nodeB);

        b?.destroy?.();
        expect(registry.get('b')).toBeNull();
    });
});
