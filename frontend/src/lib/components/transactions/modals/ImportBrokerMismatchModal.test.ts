// @vitest-environment jsdom
/**
 * ImportBrokerMismatchModal — component test (Vitest + jsdom).
 *
 * The prompt the import wizard raises right after an upload, one file at a time, when the broker's
 * default import plugin cannot read the file: where the file is (`-from`: the broker, with the
 * default plugin that refuses it), the plugin's reason when it gave one, the brokers whose default
 * plugin reads the file — one card (`-target`) or a radiogroup to choose from (`-targets`) — and
 * three answers: Move (to the chosen broker), Keep, Remove. Closing it keeps the file, except while a
 * move or a removal runs (`busy`).
 *
 * Why a component test. Which branch renders (one target, several, none, no reader at all), which
 * target Move answers with, and what `busy` locks are props in, DOM and callbacks out. The flow with a
 * real upload — the plugin check, the move, the server's files — is
 * e2e/transactions/tx-import-broker-mismatch.spec.ts (M1 one target, M4 two).
 *
 * On text. `$lib/i18n` is replaced by a translator that renders a key with its values
 * (`key(name=value, …)`, names sorted), so a label is checked by the values it is asked to show — the
 * broker names this file passes in — never by a translation. Elements are found by test id; the
 * broker and plugin names are props, not translations.
 *
 * The icons. Every broker here has a default import plugin, as the wizard's brokers do, so BrokerIcon
 * asks for the plugin list (its icon fallback) and never for a broker: the list is answered empty,
 * and any other endpoint is recorded as a stray and fails the test.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';
import {readable, writable} from 'svelte/store';
import {fireEvent, render, screen, within} from '$test/component';

const api = vi.hoisted(() => ({
    /** Endpoints the modal reached that this file does not own. Must stay empty. */
    stray: [] as string[],
}));

vi.mock('$lib/i18n', () => {
    const shown = (key: string, options?: {values?: Record<string, unknown>}) => {
        const values = options?.values;
        if (!values) return key;
        const listed = Object.keys(values)
            .sort()
            .map((name) => `${name}=${String(values[name])}`);
        return `${key}(${listed.join(', ')})`;
    };
    const translator = readable(shown);
    return {_: translator, t: translator, locale: writable('en')};
});

vi.mock('$lib/api', () => {
    const endpoints: Record<string, unknown> = {
        // BrokerIcon's plugin-icon fallback: no icon, so every icon is the briefcase.
        list_plugins_api_v1_brokers_import_plugins_get: async () => [],
    };
    return {
        zodiosApi: new Proxy(endpoints, {
            get(target, key) {
                if (typeof key !== 'string') return undefined;
                if (key in target) return target[key];
                api.stray.push(key);
                return () => Promise.reject(new Error(`unexpected request in ImportBrokerMismatchModal tests: ${key}`));
            },
        }),
    };
});

import ImportBrokerMismatchModal from './ImportBrokerMismatchModal.svelte';

type Props = ComponentProps<typeof ImportBrokerMismatchModal>;

// --- Fixtures: the Scalable pair, the overnight account's file uploaded to the broker account ----------

/** The plugin that reads the file: the overnight account's. */
const READER = {code: 'broker_scalable_deposit', name: 'Scalable Capital overnight account'};
/** The broker the file was uploaded to, and its default plugin, which refuses the file. */
const SOURCE = {id: 11, name: 'Scalable broker account', pluginCode: 'broker_scalable'};
const SOURCE_PLUGIN = {code: 'broker_scalable', name: 'Scalable Capital broker'};
/** Two brokers whose default plugin reads the file. */
const FIRST = {id: 21, name: 'Overnight account A', pluginCode: READER.code, plugin: READER};
const SECOND = {id: 22, name: 'Overnight account B', pluginCode: READER.code, plugin: READER};
const REASON = 'The default plugin’s reason, already in the UI language';

const onMove = vi.fn<(brokerId: number) => void>();
const onKeep = vi.fn<() => void>();
const onRemove = vi.fn<() => void>();

/** The prompt as the wizard opens it for one file and one target; `overrides` change what a test is about. */
function props(overrides: Partial<Props> = {}): Props {
    return {
        open: true,
        fileKey: 'entry-1',
        fileName: 'scalable-deposit-export.csv',
        broker: SOURCE,
        defaultPlugin: SOURCE_PLUGIN,
        reason: REASON,
        targets: [FIRST],
        readerNames: [READER.name],
        current: 1,
        total: 1,
        onMove,
        onKeep,
        onRemove,
        ...overrides,
    };
}

const byId = (id: string) => screen.getByTestId(`import-broker-mismatch-${id}`);
const queryById = (id: string) => screen.queryByTestId(`import-broker-mismatch-${id}`);

/** The radio of one target in the radiogroup. */
function radioOf(targetId: number): HTMLInputElement {
    return within(byId(`target-${targetId}`)).getByRole('radio') as HTMLInputElement;
}

beforeEach(() => {
    onMove.mockReset();
    onKeep.mockReset();
    onRemove.mockReset();
    api.stray.length = 0;
});

afterEach(() => {
    expect(api.stray, 'the modal reached an endpoint these tests do not own').toEqual([]);
});

describe('ImportBrokerMismatchModal — where the file is, and why it does not fit', () => {
    it('shows the broker the file was uploaded to, with the default plugin that cannot read it', () => {
        render(ImportBrokerMismatchModal, props());
        const from = byId('from');
        expect(from).toBeVisible();
        expect(from).toHaveTextContent(SOURCE.name);
        expect(from, 'the plugin that refuses the file, named as the wizard names it').toHaveTextContent(SOURCE_PLUGIN.name);
        expect(from, 'the source card is not a target').not.toHaveTextContent(FIRST.name);
        expect(byId('intro'), 'the intro names the file, its broker and the plugin').toHaveTextContent(`file=scalable-deposit-export.csv, plugin=${SOURCE_PLUGIN.name}`);
        expect(byId('intro')).toHaveTextContent(`broker=${SOURCE.name}`);
    });

    it('shows the default plugin’s reason when it gave one', () => {
        render(ImportBrokerMismatchModal, props());
        expect(byId('reason')).toBeVisible();
        expect(byId('reason')).toHaveTextContent(REASON);
    });

    it.each([
        ['null', null],
        ['empty', ''],
    ])('has no reason box when the reason is %s', (_label, reason) => {
        render(ImportBrokerMismatchModal, props({reason}));
        expect(byId('from'), 'presence barrier: the prompt is rendered').toBeVisible();
        expect(queryById('reason')).not.toBeInTheDocument();
    });

    it('counts the files under review only when there is more than one', async () => {
        const {rerender} = render(ImportBrokerMismatchModal, props({current: 2, total: 3}));
        expect(byId('counter')).toHaveTextContent('current=2, total=3');
        await rerender(props({current: 1, total: 1}));
        expect(byId('from'), 'presence barrier: the prompt is still rendered').toBeVisible();
        expect(queryById('counter')).not.toBeInTheDocument();
    });
});

describe('ImportBrokerMismatchModal — one broker whose default plugin reads the file', () => {
    it('is one card, with no choice to make, and Move answers with its broker', async () => {
        render(ImportBrokerMismatchModal, props());
        const target = byId('target');
        expect(target).toBeVisible();
        expect(target).toHaveTextContent(FIRST.name);
        expect(target, 'with the plugin that reads the file').toHaveTextContent(READER.name);
        expect(queryById('targets'), 'no radiogroup for a single target').not.toBeInTheDocument();
        expect(queryById('no-target')).not.toBeInTheDocument();
        expect(queryById('no-reader')).not.toBeInTheDocument();
        expect(byId('move'), 'Move names the target').toHaveTextContent(`broker=${FIRST.name}`);

        await fireEvent.click(byId('move'));

        expect(onMove).toHaveBeenCalledExactlyOnceWith(FIRST.id);
        expect(onKeep).not.toHaveBeenCalled();
        expect(onRemove).not.toHaveBeenCalled();
    });
});

describe('ImportBrokerMismatchModal — several brokers whose default plugin reads the file', () => {
    it('are a radiogroup, the first one chosen, with no single-target card', () => {
        render(ImportBrokerMismatchModal, props({targets: [FIRST, SECOND]}));
        const group = byId('targets');
        expect(group).toBeVisible();
        expect(group).toHaveAttribute('role', 'radiogroup');
        expect(within(group).getAllByRole('radio'), 'one radio per target').toHaveLength(2);
        expect(byId(`target-${FIRST.id}`)).toHaveTextContent(FIRST.name);
        expect(byId(`target-${SECOND.id}`)).toHaveTextContent(SECOND.name);
        expect(queryById('target'), 'no single-target card').not.toBeInTheDocument();
        expect(radioOf(FIRST.id), 'the first target is chosen until the user picks another').toBeChecked();
        expect(radioOf(SECOND.id)).not.toBeChecked();
        expect(byId('move')).toHaveTextContent(`broker=${FIRST.name}`);
    });

    it('Move answers with the broker the user chose: the second one', async () => {
        render(ImportBrokerMismatchModal, props({targets: [FIRST, SECOND]}));

        await fireEvent.click(radioOf(SECOND.id));

        expect(radioOf(SECOND.id)).toBeChecked();
        expect(radioOf(FIRST.id)).not.toBeChecked();
        expect(byId('move'), 'Move names the chosen broker').toHaveTextContent(`broker=${SECOND.name}`);

        await fireEvent.click(byId('move'));

        expect(onMove).toHaveBeenCalledExactlyOnceWith(SECOND.id);
        expect(onKeep).not.toHaveBeenCalled();
        expect(onRemove).not.toHaveBeenCalled();
    });

    it('a new file starts again from the first target: a choice belongs to its file', async () => {
        const {rerender} = render(ImportBrokerMismatchModal, props({targets: [FIRST, SECOND]}));
        await fireEvent.click(radioOf(SECOND.id));
        expect(radioOf(SECOND.id), 'precondition: the second target is chosen for the first file').toBeChecked();

        await rerender(props({targets: [FIRST, SECOND], fileKey: 'entry-2', fileName: 'another-export.csv', current: 2, total: 2}));

        expect(radioOf(FIRST.id)).toBeChecked();
        expect(radioOf(SECOND.id)).not.toBeChecked();
        await fireEvent.click(byId('move'));
        expect(onMove).toHaveBeenCalledExactlyOnceWith(FIRST.id);
    });
});

describe('ImportBrokerMismatchModal — no broker to move the file to', () => {
    it('names the plugins that read the file when no broker uses one by default, and offers no Move', () => {
        render(ImportBrokerMismatchModal, props({targets: [], readerNames: [READER.name, 'Generic CSV']}));
        expect(byId('no-target')).toHaveTextContent(`plugins=${READER.name}, Generic CSV`);
        expect(queryById('no-reader')).not.toBeInTheDocument();
        expect(queryById('move')).not.toBeInTheDocument();
        expect(byId('keep')).toBeEnabled();
        expect(byId('remove')).toBeEnabled();
    });

    it('says no plugin reads the file when none does, and offers no Move', () => {
        render(ImportBrokerMismatchModal, props({targets: [], readerNames: []}));
        expect(byId('no-reader')).toBeVisible();
        expect(queryById('no-target')).not.toBeInTheDocument();
        expect(queryById('move')).not.toBeInTheDocument();
    });
});

describe('ImportBrokerMismatchModal — Keep, Remove and closing', () => {
    it('Keep and Remove answer with their own callback', async () => {
        render(ImportBrokerMismatchModal, props());
        await fireEvent.click(byId('keep'));
        expect(onKeep).toHaveBeenCalledOnce();
        await fireEvent.click(byId('remove'));
        expect(onRemove).toHaveBeenCalledOnce();
        expect(onMove).not.toHaveBeenCalled();
    });

    it('closing it — Escape or a click on the backdrop — keeps the file', async () => {
        render(ImportBrokerMismatchModal, props());
        const backdrop = screen.getByTestId('import-broker-mismatch-modal');

        await fireEvent.keyDown(backdrop, {key: 'Escape'});
        expect(onKeep, 'Escape keeps the file').toHaveBeenCalledOnce();

        await fireEvent.mouseDown(backdrop);
        await fireEvent.click(backdrop);
        expect(onKeep, 'a click on the backdrop keeps the file').toHaveBeenCalledTimes(2);
        expect(onMove).not.toHaveBeenCalled();
        expect(onRemove).not.toHaveBeenCalled();
    });
});

describe('ImportBrokerMismatchModal — while a move or a removal runs (busy)', () => {
    // Asserted on `disabled`, the state a browser honours: it never delivers a user's click to a disabled
    // control. A synthetic click would prove nothing here — jsdom dispatches it to the button anyway.
    it('locks every answer and the choice of target', () => {
        render(ImportBrokerMismatchModal, props({targets: [FIRST, SECOND], busy: true}));
        for (const id of ['remove', 'keep', 'move']) {
            expect(byId(id), `${id} is locked`).toBeDisabled();
        }
        expect(radioOf(FIRST.id)).toBeDisabled();
        expect(radioOf(SECOND.id)).toBeDisabled();
    });

    it('locks nothing when no work runs: the same prompt, not busy', () => {
        render(ImportBrokerMismatchModal, props({targets: [FIRST, SECOND]}));
        for (const id of ['remove', 'keep', 'move']) {
            expect(byId(id), `${id} answers`).toBeEnabled();
        }
        expect(radioOf(FIRST.id)).toBeEnabled();
        expect(radioOf(SECOND.id)).toBeEnabled();
    });

    it('cannot be closed: Escape and the backdrop do not answer for the user', async () => {
        render(ImportBrokerMismatchModal, props({busy: true}));
        const backdrop = screen.getByTestId('import-broker-mismatch-modal');

        await fireEvent.keyDown(backdrop, {key: 'Escape'});
        await fireEvent.mouseDown(backdrop);
        await fireEvent.click(backdrop);

        expect(onKeep).not.toHaveBeenCalled();
        expect(backdrop, 'the prompt stays up').toBeInTheDocument();
    });

    it('answers again once the work is over', async () => {
        const {rerender} = render(ImportBrokerMismatchModal, props({busy: true}));
        await rerender(props({busy: false}));
        expect(byId('keep')).toBeEnabled();
        await fireEvent.keyDown(screen.getByTestId('import-broker-mismatch-modal'), {key: 'Escape'});
        expect(onKeep).toHaveBeenCalledOnce();
    });
});
