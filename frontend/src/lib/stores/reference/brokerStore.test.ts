/**
 * brokerStore — getOwnedBrokers (F2 dashboard scope).
 *
 * The dashboard aggregates only brokers the user OWNS with a positive share:
 * a 0% share is a valid grant that contributes nothing (behaves like an
 * EDITOR/VIEWER row), and a null share is the legacy "never set" value that
 * counts as 100% for an OWNER. Getting this wrong in either direction leaks
 * other people's portfolios into the dashboard totals or hides the user's own.
 *
 * The store itself is fed through `mergeBrokers` — the same ingress the API
 * loader uses — so what is asserted here is the real cached state, including
 * that `user_share_percentage` survives `normalize()` (it was added to the
 * normalizer by the same fix; dropping it there silently turns every OWNER
 * row into "null share = 100%").
 *
 * No DOM needed: node env. `$lib/api` is mocked because the store module
 * imports it for the loader — never called here.
 */

import {beforeEach, describe, expect, it, vi} from 'vitest';

// vi.mock is hoisted — the factory runs before the imports below.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get() {
                throw new Error('network is not expected in brokerStore unit tests');
            },
        },
    ),
}));

import {getOwnedBrokers, mergeBrokers, resetBrokerStore} from './brokerStore';

let nextId = 1;

/** One broker payload, as GET /brokers returns it (share is a decimal string there). */
function broker(user_role: string | null, user_share_percentage: string | null) {
    return {id: nextId++, name: `B${nextId}`, user_role, user_share_percentage};
}

/** Feed the store and return the ids getOwnedBrokers() keeps. */
function ownedIds(): number[] {
    return getOwnedBrokers().map((b) => b.id);
}

beforeEach(() => {
    resetBrokerStore();
});

describe('brokerStore — getOwnedBrokers (F2)', () => {
    it('keeps only OWNER rows with a positive share, across the roles × shares matrix', () => {
        const ownerFull = broker('OWNER', '1');
        const ownerPartial = broker('OWNER', '0.3');
        const ownerZero = broker('OWNER', '0');
        const ownerNull = broker('OWNER', null); // legacy unset = 100%
        const editor = broker('EDITOR', '0');
        const viewer = broker('VIEWER', '0');
        const inaccessible = broker(null, null);
        mergeBrokers([ownerFull, ownerPartial, ownerZero, ownerNull, editor, viewer, inaccessible]);

        expect(new Set(ownedIds())).toEqual(new Set([ownerFull.id, ownerPartial.id, ownerNull.id]));
    });

    it('treats any strictly-positive OWNER share as owned, however small', () => {
        const dust = broker('OWNER', '0.000001');
        mergeBrokers([dust]);

        expect(ownedIds()).toEqual([dust.id]);
    });

    it('reads user_share_percentage through the normalizer — a dropped field would look like null', () => {
        // If normalize() stops copying user_share_percentage, every OWNER row reads
        // as share=null → "100%": a 0%-owner would leak INTO the owned set. Seed a
        // single 0% owner; it must stay out.
        const ownerZero = broker('OWNER', '0');
        mergeBrokers([ownerZero]);

        expect(ownedIds()).toEqual([]);
    });

    it('excludes everything for a user who owns nothing', () => {
        mergeBrokers([broker('EDITOR', '0'), broker('VIEWER', '0'), broker(null, null)]);

        expect(ownedIds()).toEqual([]);
    });

    it('reflects a later merge — a revoked share leaves the owned set', () => {
        const row = broker('OWNER', '1');
        mergeBrokers([row]);
        expect(ownedIds()).toEqual([row.id]);

        // Partial PATCH payload, same id: the merge path must overwrite the share.
        mergeBrokers([{id: row.id, user_share_percentage: '0'}]);

        expect(ownedIds()).toEqual([]);
    });
});
