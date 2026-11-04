// @vitest-environment jsdom
/**
 * OwnerChoiceModal — which user of an uploaded backup becomes the paying administrator (lot A5-2, developer decision of
 * 23/10/2026; mounted by workstream B's restore).
 *
 * On a managed instance a backup an administrator uploads by hand is restored only after the owner is chosen: the chosen
 * account gets the owner's email, is made an administrator, is protected, and its password is reset through a link sent to
 * that email. The modal asks which one; it calls no server and answers with the user's id alone.
 *
 * The contract under test (the signature sent to B):
 *   - props `open`, `ownerEmail`, `users: OwnerCandidate[]` (`{id, username, email, is_superuser, is_active}`), `onConfirm(id)`,
 *     `onCancel()`, `busy?`; closed: nothing is drawn;
 *   - `owner-choice-modal` (the root, `data-locked="true|false"`), one `owner-choice-option` per user (`data-user-id`,
 *     `data-matches-owner`, `data-selected`, `data-admin`, `data-active`), `owner-choice-notice` (always: the user gets the
 *     owner's email, the password is reset by a link — `backup.ownerChoice.notice` given the owner's email as `{email}`),
 *     `owner-choice-empty`, `owner-choice-confirm`, `owner-choice-cancel`;
 *   - a user whose email is the owner's (any A–Z case) is selected at once and the choice is forced: `data-locked="true"`, the
 *     other options are off, «confirm» is usable; otherwise nobody is selected, «confirm» is off until one is chosen, and
 *     the choice can change;
 *   - «confirm» calls `onConfirm` once with the selected id; «cancel» and Escape call `onCancel`; with `busy` every control is off
 *     and Escape does nothing; no users: `owner-choice-empty` and «confirm» off;
 *   - the keys are sentences in the four catalogues, the notice naming `{email}` and nothing else.
 *
 * Mocks: a translator that spies its values (the identity otherwise).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, within} from '$test/component';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

const translate = vi.hoisted(() => vi.fn((key: string, _options?: {values?: Record<string, unknown>}) => key));
vi.mock('$lib/i18n', () => ({_: readable(translate)}));

import OwnerChoiceModal from './OwnerChoiceModal.svelte';

type Candidate = {id: number; username: string; email: string; is_superuser: boolean; is_active: boolean};

const OWNER_EMAIL = 'Owner@Example.com';
const MARIO: Candidate = {id: 11, username: 'mario', email: 'mario@example.com', is_superuser: true, is_active: true};
const ANNA: Candidate = {id: 12, username: 'anna', email: 'anna@example.com', is_superuser: true, is_active: true};
const LUCA: Candidate = {id: 13, username: 'luca', email: 'luca@example.com', is_superuser: false, is_active: false};
/** The user who already has the owner's email, in another case. */
const HOLDER: Candidate = {id: 14, username: 'titolare', email: 'owner@example.com', is_superuser: true, is_active: true};

const onConfirm = vi.fn();
const onCancel = vi.fn();

function mount(users: Candidate[], extra: {open?: boolean; busy?: boolean} = {}) {
    return render(OwnerChoiceModal, {props: {open: extra.open ?? true, ownerEmail: OWNER_EMAIL, users, onConfirm, onCancel, busy: extra.busy ?? false}});
}

const modal = () => screen.getByTestId('owner-choice-modal');
const options = () => within(modal()).getAllByTestId('owner-choice-option');
const optionOf = (id: number) => options().find((option) => option.getAttribute('data-user-id') === String(id)) as HTMLElement;
const confirm = () => within(modal()).getByTestId('owner-choice-confirm');

beforeEach(() => {
    onConfirm.mockReset();
    onCancel.mockReset();
    translate.mockClear();
});
afterEach(cleanup);

describe('OwnerChoiceModal — drawing (OCM-01…03)', () => {
    it('OCM-01: closed, nothing is drawn', () => {
        mount([MARIO, ANNA], {open: false});

        expect(screen.queryByTestId('owner-choice-modal')).toBeNull();
    });

    it('OCM-02: one option per user, in the order given, each saying who it is; the notice is always there', () => {
        mount([MARIO, ANNA, LUCA]);

        expect(options().map((option) => option.getAttribute('data-user-id'))).toEqual(['11', '12', '13']);
        expect(optionOf(11)).toHaveTextContent('mario');
        expect(optionOf(11)).toHaveAttribute('data-admin', 'true');
        expect(optionOf(13)).toHaveAttribute('data-admin', 'false');
        expect(optionOf(13)).toHaveAttribute('data-active', 'false');
        expect(within(modal()).getByTestId('owner-choice-notice')).toBeInTheDocument();
        expect(translate).toHaveBeenCalledWith('backup.ownerChoice.notice', {values: {email: OWNER_EMAIL}});
    });

    it('OCM-03: no users → the empty message, no option, «confirm» off', () => {
        mount([]);

        expect(within(modal()).getByTestId('owner-choice-empty')).toBeInTheDocument();
        expect(within(modal()).queryAllByTestId('owner-choice-option')).toHaveLength(0);
        expect(confirm()).toBeDisabled();
    });
});

describe('OwnerChoiceModal — nobody has the owner’s email yet: the person chooses (OCM-04…06)', () => {
    it('OCM-04: nobody is selected, the choice is free, «confirm» is off', () => {
        mount([MARIO, ANNA]);

        expect(modal()).toHaveAttribute('data-locked', 'false');
        for (const option of options()) {
            expect(option).toHaveAttribute('data-selected', 'false');
            expect(option).toHaveAttribute('data-matches-owner', 'false');
            expect(option).toBeEnabled();
        }
        expect(confirm()).toBeDisabled();
    });

    it('OCM-05: choosing selects that user alone and turns «confirm» on; choosing another moves the choice', async () => {
        mount([MARIO, ANNA]);

        await fireEvent.click(optionOf(11));
        expect(optionOf(11)).toHaveAttribute('data-selected', 'true');
        expect(optionOf(12)).toHaveAttribute('data-selected', 'false');
        expect(confirm()).toBeEnabled();
        await fireEvent.click(optionOf(12));

        expect(optionOf(11)).toHaveAttribute('data-selected', 'false');
        expect(optionOf(12)).toHaveAttribute('data-selected', 'true');
    });

    it('OCM-06: «confirm» answers with the id of the chosen user, once', async () => {
        mount([MARIO, ANNA]);
        await fireEvent.click(optionOf(12));

        await fireEvent.click(confirm());

        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onConfirm).toHaveBeenCalledWith(12);
        expect(onCancel).not.toHaveBeenCalled();
    });
});

describe('OwnerChoiceModal — a user already has the owner’s email: the choice is forced (OCM-07…09)', () => {
    it('OCM-07: it is selected at once, whatever the case of the address, and the modal is locked', () => {
        mount([MARIO, HOLDER, ANNA]);

        expect(modal()).toHaveAttribute('data-locked', 'true');
        expect(optionOf(14)).toHaveAttribute('data-selected', 'true');
        expect(optionOf(14)).toHaveAttribute('data-matches-owner', 'true');
        expect(confirm()).toBeEnabled();
    });

    it('OCM-08: the others are off, and a click on one changes nothing', async () => {
        mount([MARIO, HOLDER, ANNA]);

        expect(optionOf(11)).toBeDisabled();
        expect(optionOf(12)).toBeDisabled();
        optionOf(11).click();

        expect(optionOf(14)).toHaveAttribute('data-selected', 'true');
        expect(optionOf(11)).toHaveAttribute('data-selected', 'false');
    });

    it('OCM-09: «confirm» answers with the holder’s id', async () => {
        mount([MARIO, HOLDER, ANNA]);

        await fireEvent.click(confirm());

        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onConfirm).toHaveBeenCalledWith(14);
    });
});

describe('OwnerChoiceModal — leaving and waiting (OCM-10…12)', () => {
    it('OCM-10: «cancel» and Escape call onCancel, never onConfirm', async () => {
        mount([MARIO, ANNA]);
        await fireEvent.click(optionOf(11));

        await fireEvent.click(within(modal()).getByTestId('owner-choice-cancel'));
        await fireEvent.keyDown(window, {key: 'Escape'});

        expect(onCancel).toHaveBeenCalled();
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('OCM-11: busy — every control is off, and Escape does nothing', async () => {
        mount([MARIO, HOLDER], {busy: true});

        expect(confirm()).toBeDisabled();
        expect(within(modal()).getByTestId('owner-choice-cancel')).toBeDisabled();
        for (const option of options()) expect(option).toBeDisabled();
        await fireEvent.keyDown(window, {key: 'Escape'});
        expect(onCancel).not.toHaveBeenCalled();
    });

    it('OCM-12: «confirm» without a choice does not answer', () => {
        mount([MARIO, ANNA]);

        confirm().click();

        expect(onConfirm).not.toHaveBeenCalled();
    });
});

describe('OwnerChoiceModal — its words (OCM-13)', () => {
    const KEYS: Array<[string, string[]]> = [
        ['backup.ownerChoice.title', []],
        ['backup.ownerChoice.intro', []],
        ['backup.ownerChoice.notice', ['email']],
        ['backup.ownerChoice.locked', []],
        ['backup.ownerChoice.adminBadge', []],
        ['backup.ownerChoice.inactiveBadge', []],
        ['backup.ownerChoice.ownerBadge', []],
        ['backup.ownerChoice.empty', []],
        ['backup.ownerChoice.confirm', []],
        ['backup.ownerChoice.cancel', []],
    ];
    const leafOf = (catalogue: unknown, key: string): unknown => key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
    const placeholdersOf = (message: string): string[] => [...new Set([...message.matchAll(/\{\s*([A-Za-z_]\w*)\s*[,}]/g)].map((match) => match[1]))].sort();

    it.each(KEYS)('OCM-13: %s is a sentence in the four catalogues, naming only the values the modal fills', (key, filled) => {
        for (const [language, catalogue] of Object.entries({en, it: itCatalogue, fr, es})) {
            const message = leafOf(catalogue, key);
            expect(typeof message === 'string' && message.trim() !== '', `${language}: ${key}`).toBe(true);
            expect(placeholdersOf(message as string), `${language}: ${key}`).toEqual(filled);
        }
    });
});
