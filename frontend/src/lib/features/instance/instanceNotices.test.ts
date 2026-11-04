/**
 * instanceNotices — the registry of the notices shown above every page of the (app) layout.
 *
 * The contract under test:
 *   - `show()` adds a notice, or replaces the one with the same id in place;
 *   - `list` holds the notices not closed by the user, danger first, then warning, then info, and within a severity
 *     the order they were first shown (a replacement keeps its place);
 *   - `dismiss()` closes a dismissible notice only, until the next page load: showing it again keeps it closed, unless
 *     it is shown again as not dismissible (escalated), which lists it again while the dismissal is remembered;
 *   - `hide()` removes a notice and forgets its dismissal, so a notice hidden and shown again is visible again;
 *   - `clear()` removes every notice and every dismissal, and a change of account (sign-out included) clears the
 *     registry through `registerClientSessionReset`.
 *
 * The registry keeps its state in module-level `$state` and registers its reset at import, so every test takes a
 * freshly imported graph (`vi.resetModules()` + `import()`): the registry and the `clientSession` it registered with.
 * No test relies on `clear()` to start clean, so the case that tests `clear()` cannot pass because of itself.
 *
 * The test owns the whole registry, so the exact lists below are counts it created. The node environment: the registry
 * has no `$derived` and no `$effect`; how a component reacts to it is the subject of `InstanceNotices.test.ts` (jsdom).
 */
import {describe, expect, it, vi} from 'vitest';
import type {InstanceNotice} from './instanceNotices.svelte';

/** The registry of a page load that has just begun, and the client session of the same module graph. */
async function freshPageLoad() {
    vi.resetModules();
    const {instanceNotices} = await import('./instanceNotices.svelte');
    const session = await import('$lib/stores/app/clientSession');
    return {instanceNotices, session};
}

function notice(id: string, severity: InstanceNotice['severity'], extra: Partial<InstanceNotice> = {}): InstanceNotice {
    return {id, severity, messageKey: `test.notices.${id}`, ...extra};
}

function ids(list: InstanceNotice[]): string[] {
    return list.map((shown) => shown.id);
}

describe('instanceNotices.show', () => {
    it('a fresh registry lists nothing, and a notice shown is listed as it was given', async () => {
        const {instanceNotices} = await freshPageLoad();
        expect(instanceNotices.list).toEqual([]);

        const shown = notice('assets.disallowed', 'warning', {params: {count: 3}, dismissible: true, action: {labelKey: 'common.documentation', href: '/settings'}});
        instanceNotices.show(shown);

        expect(instanceNotices.list).toEqual([shown]);
    });

    it('replaces the notice with the same id in place: one entry, the new content, its first-shown place', async () => {
        const {instanceNotices} = await freshPageLoad();
        instanceNotices.show(notice('first', 'warning', {params: {count: 1}}));
        instanceNotices.show(notice('second', 'warning'));

        instanceNotices.show(notice('first', 'warning', {params: {count: 2}}));

        expect(ids(instanceNotices.list), 'the replacement must keep the place of the notice it replaced').toEqual(['first', 'second']);
        expect(instanceNotices.list[0].params).toEqual({count: 2});
    });
});

describe('instanceNotices.list — order', () => {
    it('danger, then warning, then info; within a severity, the order first shown', async () => {
        const {instanceNotices} = await freshPageLoad();
        for (const [id, severity] of [
            ['info-1', 'info'],
            ['warning-1', 'warning'],
            ['danger-1', 'danger'],
            ['info-2', 'info'],
            ['warning-2', 'warning'],
        ] as const) {
            instanceNotices.show(notice(id, severity));
        }

        expect(ids(instanceNotices.list)).toEqual(['danger-1', 'warning-1', 'warning-2', 'info-1', 'info-2']);
    });

    it('a notice shown again keeps its first-shown place within its severity, and moves with a new severity', async () => {
        const {instanceNotices} = await freshPageLoad();
        instanceNotices.show(notice('a', 'warning'));
        instanceNotices.show(notice('b', 'warning'));
        instanceNotices.show(notice('c', 'info'));

        instanceNotices.show(notice('a', 'warning', {params: {refreshed: 1}}));
        expect(ids(instanceNotices.list), 'a refresh must not send a notice behind those shown after it').toEqual(['a', 'b', 'c']);

        instanceNotices.show(notice('c', 'danger'));
        expect(ids(instanceNotices.list), 'a notice raised to danger goes first').toEqual(['c', 'a', 'b']);
    });

    it('list is a copy: sorting it never reorders the registry', async () => {
        const {instanceNotices} = await freshPageLoad();
        instanceNotices.show(notice('info-1', 'info'));
        instanceNotices.show(notice('danger-1', 'danger'));

        instanceNotices.list.reverse();

        expect(ids(instanceNotices.list)).toEqual(['danger-1', 'info-1']);
    });
});

describe('instanceNotices.dismiss and hide', () => {
    it('dismiss closes a dismissible notice and leaves the others listed', async () => {
        const {instanceNotices} = await freshPageLoad();
        instanceNotices.show(notice('closable', 'warning', {dismissible: true}));
        instanceNotices.show(notice('kept', 'warning'));

        instanceNotices.dismiss('closable');

        expect(ids(instanceNotices.list)).toEqual(['kept']);
    });

    it('dismiss does nothing to a notice that is not dismissible, nor for an id never shown', async () => {
        const {instanceNotices} = await freshPageLoad();
        instanceNotices.show(notice('mandatory', 'danger'));
        instanceNotices.show(notice('also-mandatory', 'info', {dismissible: false}));

        instanceNotices.dismiss('mandatory');
        instanceNotices.dismiss('also-mandatory');
        instanceNotices.dismiss('never-shown');

        expect(ids(instanceNotices.list)).toEqual(['mandatory', 'also-mandatory']);
    });

    it('a dismissed notice stays closed when its owner shows it again, until the next page load', async () => {
        const {instanceNotices} = await freshPageLoad();
        instanceNotices.show(notice('closable', 'warning', {dismissible: true, params: {count: 1}}));
        instanceNotices.dismiss('closable');

        instanceNotices.show(notice('closable', 'warning', {dismissible: true, params: {count: 2}}));

        expect(instanceNotices.list).toEqual([]);
    });

    it('a dismissal hides a notice only while it is dismissible: escalated it is listed again, dismissible again it is hidden again', async () => {
        const {instanceNotices} = await freshPageLoad();
        instanceNotices.show(notice('escalating', 'warning', {dismissible: true}));
        instanceNotices.dismiss('escalating');
        expect(instanceNotices.list, 'premise: the user closed it').toEqual([]);

        instanceNotices.show(notice('escalating', 'danger'));
        expect(ids(instanceNotices.list), 'a notice the user can no longer close must be shown, whatever they closed before').toEqual(['escalating']);

        instanceNotices.show(notice('escalating', 'warning', {dismissible: true}));
        expect(instanceNotices.list, 'dismissible again: the dismissal still holds, until hide() or the next page load').toEqual([]);
    });

    it('hide removes a notice, and a notice hidden then shown again is visible even after the user closed it', async () => {
        const {instanceNotices} = await freshPageLoad();
        instanceNotices.show(notice('closable', 'warning', {dismissible: true}));
        instanceNotices.show(notice('other', 'info'));
        instanceNotices.dismiss('closable');

        instanceNotices.hide('closable');
        instanceNotices.hide('other');
        expect(instanceNotices.list).toEqual([]);

        instanceNotices.show(notice('closable', 'warning', {dismissible: true}));
        expect(ids(instanceNotices.list), 'hide() forgets the dismissal').toEqual(['closable']);
    });
});

describe('instanceNotices.clear and the client session', () => {
    it('clear removes every notice and forgets every dismissal', async () => {
        const {instanceNotices} = await freshPageLoad();
        instanceNotices.show(notice('kept', 'info'));
        instanceNotices.show(notice('closable', 'warning', {dismissible: true}));
        instanceNotices.dismiss('closable');

        instanceNotices.clear();
        expect(instanceNotices.list).toEqual([]);

        instanceNotices.show(notice('closable', 'warning', {dismissible: true}));
        expect(ids(instanceNotices.list)).toEqual(['closable']);
    });

    it.each([
        ['signs out', null],
        ['switches account', 'user-b'],
    ])('the registry is cleared when the user %s, dismissals included, and kept while the account is the same', async (_case, nextUserId) => {
        const {instanceNotices, session} = await freshPageLoad();
        session.transitionClientSession('user-a'); // the first identity of the page load: nothing to reset yet
        instanceNotices.show(notice('kept-until-reset', 'warning'));
        instanceNotices.show(notice('closable', 'warning', {dismissible: true}));
        instanceNotices.dismiss('closable');

        expect(session.transitionClientSession('user-a'), 'premise: the same account is no transition').toBe(false);
        expect(ids(instanceNotices.list), 'the same account keeps the notices').toEqual(['kept-until-reset']);

        expect(session.transitionClientSession(nextUserId), 'premise: a real change of account').toBe(true);
        expect(instanceNotices.list, 'the notices of the previous account must go').toEqual([]);

        instanceNotices.show(notice('closable', 'warning', {dismissible: true}));
        expect(ids(instanceNotices.list), 'the dismissals of the previous account must go too').toEqual(['closable']);
    });
});
