import type {Action} from 'svelte/action';

import {registerClientSessionReset} from '$lib/stores/app/clientSession';

export interface GuideAnchorRegistry {
    readonly revision: number;
    register(id: string, element: HTMLElement): () => void;
    get(id: string): HTMLElement | null;
    has(id: string): boolean;
    clear(): void;
}

export function createGuideAnchorRegistry(): GuideAnchorRegistry {
    const anchors = new Map<string, HTMLElement>();
    let revision = $state(0);

    function register(id: string, element: HTMLElement): () => void {
        if (!id.trim()) throw new Error('Guide anchor ID cannot be empty');
        anchors.set(id, element);
        revision += 1;
        return () => {
            if (anchors.get(id) === element) {
                anchors.delete(id);
                revision += 1;
            }
        };
    }

    function get(id: string): HTMLElement | null {
        void revision;
        const element = anchors.get(id);
        if (!element?.isConnected) {
            if (element) {
                anchors.delete(id);
                revision += 1;
            }
            return null;
        }
        return element;
    }

    function clear(): void {
        if (anchors.size === 0) return;
        anchors.clear();
        revision += 1;
    }

    return {
        get revision() {
            return revision;
        },
        register,
        get,
        has: (id: string) => get(id) !== null,
        clear,
    };
}

export function createGuideAnchorAction(registry: GuideAnchorRegistry): Action<HTMLElement, string> {
    return (node, id) => {
        let unregister = registry.register(id, node);
        return {
            update(nextId: string) {
                if (nextId === id) return;
                unregister();
                id = nextId;
                unregister = registry.register(id, node);
            },
            destroy() {
                unregister();
            },
        };
    };
}

export const guideAnchors = createGuideAnchorRegistry();
export const guideAnchor = createGuideAnchorAction(guideAnchors);

registerClientSessionReset('guideAnchors', () => guideAnchors.clear());
