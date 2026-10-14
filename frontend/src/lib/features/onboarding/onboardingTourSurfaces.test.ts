import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

import {onboardingTourSurfaces, type OnboardingTourSurfaceId} from './onboardingTourSurfaces.svelte';

/**
 * The production export is intentionally one account-scoped registry singleton.
 * Each test therefore owns every registration it creates and closes/unregisters
 * it on teardown, mirroring component unmount plus client-session reset.
 */
let unregisters: Array<() => void> = [];

function register(id: OnboardingTourSurfaceId) {
    const handler = {
        openPreview: vi.fn(),
        closePreview: vi.fn(),
    };
    unregisters.push(onboardingTourSurfaces.register(id, handler));
    return handler;
}

beforeEach(() => {
    onboardingTourSurfaces.closeAll();
    unregisters = [];
});

afterEach(() => {
    onboardingTourSurfaces.closeAll();
    for (const unregister of unregisters.reverse()) unregister();
});

describe('onboardingTourSurfaces — request and ownership', () => {
    it('retains a request made before its page registers, then opens it exactly once on registration', () => {
        onboardingTourSurfaces.request('brokers.create');

        expect(onboardingTourSurfaces.pending).toBe('brokers.create');
        expect(onboardingTourSurfaces.active).toBeNull();

        const broker = register('brokers.create');

        expect(broker.openPreview).toHaveBeenCalledTimes(1);
        expect(broker.closePreview).not.toHaveBeenCalled();
        expect(onboardingTourSurfaces.pending).toBeNull();
        expect(onboardingTourSurfaces.active).toBe('brokers.create');
    });

    it('only the active surface owner closes for a matching close request', () => {
        const broker = register('brokers.create');
        const fx = register('fx.create');
        onboardingTourSurfaces.request('brokers.create');

        onboardingTourSurfaces.close('fx.create');
        expect(broker.closePreview).not.toHaveBeenCalled();
        expect(fx.closePreview).not.toHaveBeenCalled();
        expect(onboardingTourSurfaces.active).toBe('brokers.create');

        onboardingTourSurfaces.close('brokers.create');
        expect(broker.closePreview).toHaveBeenCalledTimes(1);
        expect(fx.closePreview).not.toHaveBeenCalled();
        expect(onboardingTourSurfaces.active).toBeNull();
    });

    it('closes the old owner before opening the surface for a replacement step', () => {
        const broker = register('brokers.create');
        const fx = register('fx.create');
        onboardingTourSurfaces.request('brokers.create');

        onboardingTourSurfaces.request('fx.create');

        expect(broker.openPreview).toHaveBeenCalledTimes(1);
        expect(broker.closePreview).toHaveBeenCalledTimes(1);
        expect(fx.openPreview).toHaveBeenCalledTimes(1);
        expect(broker.closePreview.mock.invocationCallOrder[0]).toBeLessThan(fx.openPreview.mock.invocationCallOrder[0]);
        expect(onboardingTourSurfaces.active).toBe('fx.create');
        expect(onboardingTourSurfaces.pending).toBeNull();
    });
});

describe('onboardingTourSurfaces — lifecycle reset', () => {
    it('unregistering the active owner closes it and makes a later request pending', () => {
        const asset = register('assets.create');
        onboardingTourSurfaces.request('assets.create');
        const unregister = unregisters.at(-1);
        if (!unregister) throw new Error('Surface fixture did not retain its unregister callback');

        unregister();

        expect(asset.closePreview).toHaveBeenCalledTimes(1);
        expect(onboardingTourSurfaces.active).toBeNull();

        onboardingTourSurfaces.request('assets.create');
        expect(asset.openPreview).toHaveBeenCalledTimes(1);
        expect(onboardingTourSurfaces.pending).toBe('assets.create');
    });

    it('hands an active surface request to its replacement owner after unregistration', () => {
        const original = register('assets.create');
        onboardingTourSurfaces.request('assets.create');
        expect(original.openPreview).toHaveBeenCalledTimes(1);
        expect(onboardingTourSurfaces.active).toBe('assets.create');
        const unregisterOriginal = unregisters.at(-1);
        if (!unregisterOriginal) throw new Error('Surface fixture did not retain its unregister callback');

        unregisterOriginal();

        expect(original.closePreview).toHaveBeenCalledTimes(1);
        expect(onboardingTourSurfaces.active).toBeNull();
        expect(onboardingTourSurfaces.pending).toBe('assets.create');

        const replacement = register('assets.create');

        expect(original.closePreview).toHaveBeenCalledTimes(1);
        expect(replacement.openPreview).toHaveBeenCalledTimes(1);
        expect(onboardingTourSurfaces.pending).toBeNull();
        expect(onboardingTourSurfaces.active).toBe('assets.create');
    });

    it('closeAll mirrors an account reset by closing an active owner and clearing a later pending request', () => {
        const broker = register('brokers.create');
        onboardingTourSurfaces.request('brokers.create');

        onboardingTourSurfaces.closeAll();

        expect(broker.closePreview).toHaveBeenCalledTimes(1);
        expect(onboardingTourSurfaces.active).toBeNull();
        expect(onboardingTourSurfaces.pending).toBeNull();

        onboardingTourSurfaces.request('fx.create');
        expect(onboardingTourSurfaces.pending).toBe('fx.create');

        onboardingTourSurfaces.closeAll();

        expect(broker.closePreview).toHaveBeenCalledTimes(1);
        expect(onboardingTourSurfaces.active).toBeNull();
        expect(onboardingTourSurfaces.pending).toBeNull();
    });
});
