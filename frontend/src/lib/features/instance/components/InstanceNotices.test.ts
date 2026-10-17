// @vitest-environment jsdom
/**
 * InstanceNotices — the notices of `instanceNotices`, shown above every page of the (app) layout.
 *
 * The contract under test:
 *   - nothing is rendered while there is no notice;
 *   - otherwise one `section[data-testid=instance-notices]` named by `instance.notices.label`, holding one
 *     `[data-testid=instance-notice]` per listed notice, in the registry's order, each with `data-notice-id`,
 *     `data-severity` and a role (`alert` for danger, `status` otherwise);
 *   - the message is `$_(messageKey, {values: params})`; an action is a link to its `href`, named by its `labelKey`;
 *   - a dismiss button only on a dismissible notice, named `common.close`, which closes that notice; a closed notice
 *     shown again as not dismissible (escalated) is rendered again, without the button;
 *   - the component follows the registry: a notice shown, replaced or hidden after mount updates the DOM, and a
 *     notice replaced in place keeps its element (the list is keyed by id).
 *
 * Assertions read `data-*`, `aria-*` and roles. A text is compared only with what the catalogue answers for the key
 * the test chose (`translate`), never with a literal: the suite does not depend on the English wording. The registry is
 * module state shared with the component, so it is cleared around each test; it is imported statically, not through
 * `vi.resetModules()`, which would give the component a second Svelte runtime.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it} from 'vitest';
import {flushSync} from 'svelte';
import {get} from 'svelte/store';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import {_} from '$lib/i18n';
import {instanceNotices, type InstanceNotice} from '../instanceNotices.svelte';
import InstanceNotices from './InstanceNotices.svelte';

/** A catalogue key that takes ICU values: the message of the notices below that carry params. */
const MESSAGE_WITH_VALUES = 'instance.checks.jwtSecret.short';
const MESSAGE_PLAIN = 'instance.checks.sessionCookie.never';

function translate(key: string, values?: Record<string, string | number>): string {
    return get(_)(key, values ? {values} : undefined);
}

function notice(id: string, severity: InstanceNotice['severity'], extra: Partial<InstanceNotice> = {}): InstanceNotice {
    return {id, severity, messageKey: MESSAGE_PLAIN, ...extra};
}

/** Changes the registry outside any component, as a feature does, and lets the DOM catch up: a flush, not a wait. */
function showAll(...notices: InstanceNotice[]): void {
    for (const shown of notices) instanceNotices.show(shown);
    flushSync();
}

function noticeElement(id: string): HTMLElement {
    const element = screen.getAllByTestId('instance-notice').find((candidate) => candidate.dataset.noticeId === id);
    if (!element) throw new Error(`no instance-notice with data-notice-id="${id}" is rendered`);
    return element;
}

function text(element: Element): string {
    return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
}

beforeAll(async () => {
    await setupI18n();
    // Negative assertions below would pass vacuously in an environment where effects never run.
    assertEffectsRun();
});

beforeEach(() => {
    instanceNotices.clear();
});

afterEach(() => {
    instanceNotices.clear();
});

describe('InstanceNotices — the section', () => {
    it('renders nothing without a notice, and appears when a notice is shown after mount', () => {
        const {container} = render(InstanceNotices);

        expect(container.querySelector('*'), 'nothing at all is rendered without a notice').toBeNull();

        showAll(notice('first', 'info'));

        expect(screen.getByTestId('instance-notices'), 'the component follows the registry after mount').toBeInTheDocument();
    });

    it('is a region named by instance.notices.label', () => {
        showAll(notice('first', 'info'));
        render(InstanceNotices);
        const label = translate('instance.notices.label');

        expect(label, 'premise: the catalogue knows the key').not.toBe('instance.notices.label');
        expect(screen.getByRole('region', {name: label})).toBe(screen.getByTestId('instance-notices'));
    });

    it('goes when its last notice is hidden', () => {
        showAll(notice('only', 'warning'));
        render(InstanceNotices);
        expect(screen.getByTestId('instance-notices')).toBeInTheDocument();

        instanceNotices.hide('only');
        flushSync();

        expect(screen.queryByTestId('instance-notices')).toBeNull();
    });
});

describe('InstanceNotices — one element per notice', () => {
    it('in the registry order, each with its id, severity and role: alert for danger, status otherwise', () => {
        showAll(notice('info-1', 'info'), notice('danger-1', 'danger'), notice('warning-1', 'warning'));
        render(InstanceNotices);
        const section = screen.getByTestId('instance-notices');

        const rendered = within(section)
            .getAllByTestId('instance-notice')
            .map((element) => [element.dataset.noticeId, element.dataset.severity, element.getAttribute('role')]);

        expect(rendered).toEqual([
            ['danger-1', 'danger', 'alert'],
            ['warning-1', 'warning', 'status'],
            ['info-1', 'info', 'status'],
        ]);
    });

    it('the message is the messageKey translated with the params as its values', () => {
        const params = {source: 'JWT_SECRET', length: 12, minimum: 32};
        showAll(notice('with-values', 'warning', {messageKey: MESSAGE_WITH_VALUES, params}), notice('plain', 'info'));
        render(InstanceNotices);

        expect(text(noticeElement('with-values'))).toBe(translate(MESSAGE_WITH_VALUES, params));
        expect(text(noticeElement('with-values')), 'the values the test passed are in the message').toContain('JWT_SECRET');
        expect(text(noticeElement('plain'))).toBe(translate(MESSAGE_PLAIN));
    });

    it('an action is a link to its href, named by its labelKey; a notice without one has no link', () => {
        showAll(notice('with-action', 'warning', {action: {labelKey: 'common.documentation', href: '/settings?tab=admin'}}), notice('without-action', 'info'));
        render(InstanceNotices);

        const link = within(noticeElement('with-action')).getByTestId('instance-notice-action');
        expect(link.tagName).toBe('A');
        expect(link).toHaveAttribute('href', '/settings?tab=admin');
        expect(text(link)).toBe(translate('common.documentation'));
        expect(within(noticeElement('without-action')).queryByTestId('instance-notice-action')).toBeNull();
    });

    it('a notice shown again with the same id is updated in place, keeping its element', () => {
        showAll(notice('escalating', 'warning'));
        render(InstanceNotices);
        const before = noticeElement('escalating');

        showAll(notice('escalating', 'danger'));

        const after = noticeElement('escalating');
        expect(after, 'a replacement must not tear the notice down and rebuild it').toBe(before);
        expect([after.dataset.severity, after.getAttribute('role')]).toEqual(['danger', 'alert']);
    });
});

describe('InstanceNotices — dismissing', () => {
    it('a dismiss button only on a dismissible notice, named common.close', () => {
        showAll(notice('closable', 'warning', {dismissible: true}), notice('mandatory', 'danger'));
        render(InstanceNotices);

        const dismiss = within(noticeElement('closable')).getByTestId('instance-notice-dismiss');
        expect(dismiss.tagName).toBe('BUTTON');
        expect(dismiss).toHaveAttribute('type', 'button');
        expect(dismiss).toHaveAttribute('aria-label', translate('common.close'));
        expect(within(noticeElement('mandatory')).queryByTestId('instance-notice-dismiss')).toBeNull();
    });

    it('the button closes its notice, and only that one', async () => {
        showAll(notice('closable', 'warning', {dismissible: true}), notice('other-closable', 'info', {dismissible: true}));
        render(InstanceNotices);

        await fireEvent.click(within(noticeElement('closable')).getByTestId('instance-notice-dismiss'));
        flushSync();

        expect(screen.getAllByTestId('instance-notice').map((element) => element.dataset.noticeId)).toEqual(['other-closable']);
        expect(
            instanceNotices.list.map((listed) => listed.id),
            'the click closed it in the registry, not only on screen',
        ).toEqual(['other-closable']);
    });

    it('closing the last notice removes the section', async () => {
        showAll(notice('closable', 'warning', {dismissible: true}));
        render(InstanceNotices);

        await fireEvent.click(screen.getByTestId('instance-notice-dismiss'));
        flushSync();

        expect(screen.queryByTestId('instance-notices')).toBeNull();
    });

    it('a closed notice shown again as not dismissible is rendered again, without a dismiss button', async () => {
        showAll(notice('escalating', 'warning', {dismissible: true}));
        render(InstanceNotices);
        await fireEvent.click(screen.getByTestId('instance-notice-dismiss'));
        flushSync();
        expect(screen.queryByTestId('instance-notices'), 'premise: the user closed it').toBeNull();

        showAll(notice('escalating', 'danger'));

        const escalated = noticeElement('escalating');
        expect([escalated.dataset.severity, escalated.getAttribute('role')]).toEqual(['danger', 'alert']);
        expect(within(escalated).queryByTestId('instance-notice-dismiss'), 'the user can no longer close it').toBeNull();

        showAll(notice('escalating', 'warning', {dismissible: true}));

        expect(screen.queryByTestId('instance-notices'), 'dismissible again: the earlier dismissal still holds').toBeNull();
    });
});
