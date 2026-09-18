import {registerClientSessionReset} from '$lib/stores/app/clientSession';

export type OnboardingTourSurfaceId = 'brokers.create' | 'fx.create' | 'assets.create';

interface OnboardingTourSurfaceHandler {
    openPreview: () => void;
    closePreview: () => void;
}

function createOnboardingTourSurfaces() {
    const handlers = new Map<OnboardingTourSurfaceId, OnboardingTourSurfaceHandler>();
    let pending = $state<OnboardingTourSurfaceId | null>(null);
    let active = $state<OnboardingTourSurfaceId | null>(null);
    let revision = $state(0);

    function register(id: OnboardingTourSurfaceId, handler: OnboardingTourSurfaceHandler): () => void {
        handlers.set(id, handler);
        revision += 1;
        if (pending === id) {
            handler.openPreview();
            active = id;
            pending = null;
            revision += 1;
        }
        return () => {
            if (handlers.get(id) === handler) {
                if (active === id) {
                    handler.closePreview();
                    active = null;
                    pending = id;
                }
                handlers.delete(id);
                revision += 1;
            }
        };
    }

    function request(id: OnboardingTourSurfaceId): void {
        if (active && active !== id) close(active);
        const handler = handlers.get(id);
        if (handler) {
            handler.openPreview();
            active = id;
            pending = null;
        } else {
            pending = id;
        }
        revision += 1;
    }

    function close(id: OnboardingTourSurfaceId): void {
        if (pending === id) pending = null;
        if (active === id) {
            handlers.get(id)?.closePreview();
            active = null;
        }
        revision += 1;
    }

    function closeAll(): void {
        if (active) handlers.get(active)?.closePreview();
        active = null;
        pending = null;
        revision += 1;
    }

    return {
        get active() {
            return active;
        },
        get pending() {
            return pending;
        },
        get revision() {
            return revision;
        },
        register,
        request,
        close,
        closeAll,
    };
}

export const onboardingTourSurfaces = createOnboardingTourSurfaces();

registerClientSessionReset('onboardingTourSurfaces', () => onboardingTourSurfaces.closeAll());
