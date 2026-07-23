/**
 * Auth-boundary coordinator for module-level frontend state.
 *
 * The SPA runtime survives logout/login navigation, so user-scoped caches must
 * be cleared whenever the resolved account changes. The generation counter also
 * lets async callers discard responses started by a previous account.
 */

export type ClientSessionUserId = number | string | null;

export interface ClientSessionTransition {
    previousUserId: string | null;
    nextUserId: string | null;
    generation: number;
}

export type ClientSessionResetter = (transition: ClientSessionTransition) => void;

function normalizeUserId(userId: ClientSessionUserId): string | null {
    return userId == null ? null : String(userId);
}

export class ClientSessionState {
    private userId: string | null = null;
    private generation = 0;
    private hasResolvedIdentity = false;
    private readonly resetters = new Map<string, ClientSessionResetter>();

    register(key: string, resetter: ClientSessionResetter): () => void {
        this.resetters.set(key, resetter);
        return () => {
            if (this.resetters.get(key) === resetter) {
                this.resetters.delete(key);
            }
        };
    }

    transition(nextUserId: ClientSessionUserId): boolean {
        const normalizedNext = normalizeUserId(nextUserId);
        if (!this.hasResolvedIdentity) {
            this.hasResolvedIdentity = true;
            this.userId = normalizedNext;
            this.generation += 1;
            return true;
        }
        if (normalizedNext === this.userId) return false;

        const previousUserId = this.userId;
        this.userId = normalizedNext;
        this.generation += 1;
        const transition = {
            previousUserId,
            nextUserId: normalizedNext,
            generation: this.generation,
        };

        for (const [key, resetter] of this.resetters) {
            try {
                resetter(transition);
            } catch (error) {
                console.error(`[clientSession] Failed to reset "${key}"`, error);
            }
        }
        return true;
    }

    getUserId(): string | null {
        return this.userId;
    }

    getGeneration(): number {
        return this.generation;
    }

    isCurrent(generation: number): boolean {
        return generation === this.generation;
    }
}

const clientSession = new ClientSessionState();

export const registerClientSessionReset = (key: string, resetter: ClientSessionResetter): (() => void) => clientSession.register(key, resetter);
export const transitionClientSession = (userId: ClientSessionUserId): boolean => clientSession.transition(userId);
export const getClientSessionUserId = (): string | null => clientSession.getUserId();
export const getClientSessionGeneration = (): number => clientSession.getGeneration();
export const isClientSessionCurrent = (generation: number): boolean => clientSession.isCurrent(generation);
