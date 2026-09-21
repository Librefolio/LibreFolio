import type {Action} from 'svelte/action';

import {registerClientSessionReset} from '$lib/stores/app/clientSession';

export interface GuideAnchorRegistry {
    readonly revision: number;
    register(id: string, element: HTMLElement): () => void;
    get(id: string): HTMLElement | null;
    has(id: string): boolean;
    clear(): void;
}

export type GuideAnchorBinding = string | readonly string[];

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

function normalizedAnchorIds(binding: GuideAnchorBinding): string[] {
    const ids = typeof binding === 'string' ? [binding] : binding;
    return [...new Set(ids.map((id) => id.trim()).filter(Boolean))];
}

export function createGuideAnchorAction(registry: GuideAnchorRegistry): Action<HTMLElement, GuideAnchorBinding> {
    return (node, binding) => {
        let ids = normalizedAnchorIds(binding);
        let unregister = ids.map((id) => registry.register(id, node));
        return {
            update(nextBinding: GuideAnchorBinding) {
                const nextIds = normalizedAnchorIds(nextBinding);
                if (nextIds.length === ids.length && nextIds.every((id, index) => id === ids[index])) return;
                for (const cleanup of unregister) cleanup();
                ids = nextIds;
                unregister = ids.map((id) => registry.register(id, node));
            },
            destroy() {
                for (const cleanup of unregister) cleanup();
            },
        };
    };
}

export const guideAnchors = createGuideAnchorRegistry();
export const guideAnchor = createGuideAnchorAction(guideAnchors);

registerClientSessionReset('guideAnchors', () => guideAnchors.clear());
