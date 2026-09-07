import {describe, expect, it, vi} from 'vitest';

import {createEntityStore} from './entityStore';

interface Item {
    id: number;
    name: string;
}

function normalize(raw: Record<string, unknown>): Item {
    return {
        id: Number(raw.id),
        name: String(raw.name),
    };
}

describe('createEntityStore session reset', () => {
    it('clears loaded entries without starting another request', async () => {
        const loader = vi.fn().mockResolvedValue([{id: 1, name: 'User A broker'}]);
        const store = createEntityStore<Item, number>({
            loader,
            getId: (item) => item.id,
            normalize,
        });

        await store.ensureLoaded();
        expect(store.getAll()).toEqual([{id: 1, name: 'User A broker'}]);

        store.reset();
        expect(store.getAll()).toEqual([]);
        expect(store.isLoaded()).toBe(false);
        expect(loader).toHaveBeenCalledOnce();
    });

    it('discards a load that resolves after reset', async () => {
        let resolveFirst: (items: unknown[]) => void = () => undefined;
        const loader = vi
            .fn()
            .mockImplementationOnce(
                () =>
                    new Promise<unknown[]>((resolve) => {
                        resolveFirst = resolve;
                    }),
            )
            .mockResolvedValueOnce([{id: 2, name: 'User B broker'}]);
        const store = createEntityStore<Item, number>({
            loader,
            getId: (item) => item.id,
            normalize,
        });

        const staleLoad = store.ensureLoaded();
        store.reset();
        resolveFirst([{id: 1, name: 'User A broker'}]);
        await staleLoad;

        expect(store.getAll()).toEqual([]);
        await store.ensureLoaded();
        expect(store.getAll()).toEqual([{id: 2, name: 'User B broker'}]);
    });
});
