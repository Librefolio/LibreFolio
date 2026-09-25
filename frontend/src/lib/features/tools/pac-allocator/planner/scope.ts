/**
 * The Broker scope of an explicit copy (N18): the Portfolio API reads only
 * Brokers the user owns and refuses any other with a 403. Brokers with a
 * lower role are listed as not selectable, never dropped in silence.
 */
import {ensureBrokersLoaded, getAccessibleBrokers} from '$lib/stores/reference/brokerStore';

export interface ScopeBroker {
    id: number;
    name: string;
    role: string | null;
    /** Ownership share as a fraction (`"0.5"`); `null` = never set (100% for an OWNER). */
    share: string | null;
    active: boolean;
    selectable: boolean;
}

export async function loadCopyScope(): Promise<ScopeBroker[]> {
    await ensureBrokersLoaded();
    return getAccessibleBrokers()
        .map((broker) => ({
            id: broker.id,
            name: broker.name,
            role: broker.user_role ?? null,
            share: broker.user_share_percentage ?? null,
            active: broker.is_active !== false,
            selectable: broker.user_role === 'OWNER',
        }))
        .sort((a, b) => Number(b.selectable) - Number(a.selectable) || a.name.localeCompare(b.name));
}

export function selectableIds(scope: readonly ScopeBroker[]): number[] {
    return scope.filter((broker) => broker.selectable).map((broker) => broker.id);
}
