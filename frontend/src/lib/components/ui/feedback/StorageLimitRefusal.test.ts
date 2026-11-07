// @vitest-environment jsdom
/**
 * StorageLimitRefusal — component test (Vitest + jsdom), C9-1.
 *
 * The refusal of the space limit, said where the user is. An administrator reads the limit to raise and gets «Open the
 * settings», a link to Files › Advanced with its panel open; a member reads how much to free or to ask an administrator,
 * with no link; a limit the hosting provider fixes reads «ask whoever hosts it» for both, with no link. The translator
 * echoes its key, so the sentence asserted is the key the component chose.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import {cleanup, render, screen} from '$test/component';

const user = vi.hoisted(() => ({isAdmin: true}));
vi.mock('$lib/i18n', async (importOriginal) => ({...(await importOriginal<object>()), _: readable((key: string) => key)}));
vi.mock('$lib/stores/app/auth', () => ({auth: {subscribe: (run: (value: unknown) => void) => writable({user: {is_superuser: user.isAdmin}}).subscribe(run)}}));

import StorageLimitRefusal from './StorageLimitRefusal.svelte';

afterEach(cleanup);

const numbers = (extra = {}) => ({requiredMb: 120, diskMissingBytes: 0, limitLocked: false, excessBytes: 20 * 1024 * 1024, ...extra});
const box = () => screen.getByTestId('storage-limit-refusal');

describe('StorageLimitRefusal', () => {
    it('an administrator: the limit to raise and «Open the settings», a link to Files › Advanced', () => {
        user.isAdmin = true;
        render(StorageLimitRefusal, {numbers: numbers()});

        expect(box()).toHaveAttribute('data-viewer', 'admin');
        expect(box()).toHaveTextContent('storage.limit.exceeded.raise');
        expect(screen.getByTestId('storage-limit-open-settings')).toHaveAttribute('href', '/files?storage=limit');
        expect(screen.getByTestId('storage-limit-open-settings')).toHaveTextContent('storage.limit.openSettings');
    });

    it('a member: how much to free or whom to ask, and no link', () => {
        user.isAdmin = false;
        render(StorageLimitRefusal, {numbers: numbers()});

        expect(box()).toHaveAttribute('data-viewer', 'member');
        expect(box()).toHaveTextContent('storage.limit.exceeded.member');
        expect(screen.queryByTestId('storage-limit-open-settings')).toBeNull();
    });

    it.each([true, false])('a limit the hosting provider fixes (administrator %s): «ask whoever hosts it», no link', (isAdmin) => {
        user.isAdmin = isAdmin;
        render(StorageLimitRefusal, {numbers: numbers({limitLocked: true})});

        expect(box()).toHaveAttribute('data-limit-locked', 'true');
        expect(box()).toHaveTextContent('storage.limit.exceeded.locked');
        expect(screen.queryByTestId('storage-limit-open-settings')).toBeNull();
    });
});
