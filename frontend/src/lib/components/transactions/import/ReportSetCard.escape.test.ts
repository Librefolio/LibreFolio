// @vitest-environment jsdom
/**
 * ReportSetCard in the import wizard — one Escape on the open «Read as» list closes the list, not the wizard
 * (Vitest + jsdom). K, step 20.
 *
 * ImportWizardModal is one ModalBase whose `onRequestClose` is `handleClose`, and with work in progress
 * `handleClose` opens the «discard the import?» confirmation. In step 2 each report set is a ReportSetCard inside
 * that modal, and the card's «Read as» is a SimpleSelect (`report-set-read-as`). SimpleSelect keeps the focus on its
 * trigger while its list is open — a combobox that names the highlighted option with `aria-activedescendant` — and
 * handles the keys there. On Escape it closes the list but lets the keydown go on: the keydown bubbles to ModalBase's
 * backdrop, which requests the close on any Escape. One Escape on the open «Read as» list therefore closes the list
 * and asks to discard the import.
 *
 * The approved cure is in SimpleSelect: the Escape its open list consumes stops its propagation. ModalBase and the
 * card do not change, so the subject is what reaches the wizard, read off the `onRequestClose` spy of the ModalBase
 * the card sits in (`ReportSetCardInModalHarness`: the wizard's ModalBase props, the real card).
 * `ui/modals/ModalBase.escapeLayers.test.ts` pins the same rule on SimpleSelect alone.
 *
 * Escape is delivered the way a browser delivers it: to the focused element — the «Read as» trigger — bubbling. The
 * red case proves first that the select handled the key — its list is closed, and nothing was chosen — and only then
 * asserts on the wizard, so a red can only be about the propagation. Then it presses Escape once more: with the list
 * closed, that one is the wizard's. The control is green before and after the cure: with the list closed, an Escape
 * on «Read as» still reaches the wizard.
 *
 * The fixture is the one-file set of `ReportSetCard.test.ts`, written again here rather than imported (importing a
 * test file runs its tests here too): open on its card, as the wizard opens the sets of its session, with a catalogue
 * where two report-set plugins read its member, so «Read as» offers three choices. Nothing here reads translated
 * text: testids, ARIA state and spies.
 *
 * Plan: `LibreFolio_developer_journal/Release_2/Phase_0/25_taxonomySelect/plan-phase00TaxonomySelectStep20SimpleSelectEscape.prompt.md`.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';

// Every API method is inert: the card receives its data as props.
vi.mock('$lib/api', async () => {
    const generated = await vi.importActual<{schemas: unknown}>('$lib/api/generated');
    const inert = () =>
        new Proxy(
            {},
            {
                get(_target, property) {
                    if (typeof property !== 'string' || property === 'then') return undefined;
                    return vi.fn(async () => undefined);
                },
            },
        );
    class ApiError extends Error {}
    return {zodiosApi: inert(), axiosInstance: inert(), ApiError, schemas: generated.schemas};
});

// ModalBase manages focus only in a browser: there it focuses its backdrop as it opens, which is the state a user
// meets and the one every test here starts from.
vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));

/**
 * This jsdom build exposes no `localStorage` at all (see `table/DataTable.test.ts`), and with `browser: true` above a
 * module that reads storage while it loads — the language store, which the card reaches through DataTable and the
 * user storage helpers — would throw before any case runs, failing the whole file for a reason that is the
 * harness's, not the card's. A Map-backed stand-in, as in `risk/BenchmarkSelect.test.ts`: installed before anything
 * is imported, and fresh for every case (`beforeEach`).
 */
const storage = vi.hoisted(() => {
    function install(): void {
        const backing = new Map<string, string>();
        Object.defineProperty(globalThis, 'localStorage', {
            configurable: true,
            writable: true,
            value: {
                getItem: (key: string) => backing.get(key) ?? null,
                setItem: (key: string, value: string) => void backing.set(key, String(value)),
                removeItem: (key: string) => void backing.delete(key),
                clear: () => backing.clear(),
                key: (index: number) => [...backing.keys()][index] ?? null,
                get length() {
                    return backing.size;
                },
            },
        });
    }
    install();
    return {install};
});

import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import Harness from '$test/harness/ReportSetCardInModalHarness.svelte';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import type {BrimSetPreview} from '$lib/types';
import type {ReportSetGroup, SetFileInfo, SetPluginInfo} from '$lib/utils/transactions/importReportSets';

beforeAll(async () => {
    await setupI18n();
    setPrivacyEnabled(false);
});

beforeEach(() => {
    storage.install();
    // Unmounting the modal restores the page scroll, and jsdom implements no scrolling.
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Fixtures: the one-file set of ReportSetCard.test.ts, and its catalogue
// ---------------------------------------------------------------------------

const BROKER = 7;
const PLUGIN_CODE = 'broker_probe_set';
const SINGLE_CODE = 'broker_probe_single_csv';
const SECOND_SET_CODE = 'broker_probe_second_bank';
const BATCH = '6f1c2d3e-4a5b-4c6d-8e7f-901a2b3c4d5e';

/** The set's plugin: two roles, custody exports and cash statements. */
const PLUGIN: SetPluginInfo = {
    code: PLUGIN_CODE,
    name: 'Probe Set Bank',
    docs_url: null,
    report_roles: [
        {code: 'custody', required: true, multiple: true, extensions: ['.xlsx'], description: 'Probe custody export', max_history: 'P1Y'},
        {code: 'cash', required: true, multiple: true, extensions: ['.csv'], description: 'Probe cash statement', max_history: 'P5Y', must_cover: 'custody'},
    ],
};
/** A single-file plugin, and a second report-set plugin that reads one custody export. */
const SINGLE_PLUGIN: SetPluginInfo = {code: SINGLE_CODE, name: 'Probe Single CSV', docs_url: null, report_roles: []};
const SECOND_SET_PLUGIN: SetPluginInfo = {code: SECOND_SET_CODE, name: 'Probe Second Bank', docs_url: null, report_roles: [{code: 'statement', required: true, multiple: false, extensions: ['.xlsx'], description: 'Probe second-bank statement'}]};
const CATALOGUE = [PLUGIN, SINGLE_PLUGIN, SECOND_SET_PLUGIN];

/** The set's one file: a custody export that both report-set plugins read. */
const CU_EARLY: SetFileInfo = {
    file_id: 'cu-early',
    filename: 'probe-custody-c.xlsx',
    uploaded_at: '2026-09-30T10:00:03Z',
    status: 'uploaded',
    target_broker_id: BROKER,
    batch_id: BATCH,
    kind: 'original',
    compatible_plugins: [PLUGIN_CODE, SECOND_SET_CODE],
};

const SET: ReportSetGroup = {key: `set:${BROKER}:${PLUGIN_CODE}:${BATCH}`, brokerId: BROKER, pluginCode: PLUGIN_CODE, batchId: BATCH, uploadedAt: CU_EARLY.uploaded_at, files: [CU_EARLY]};

/** Its preview: the custody export is there, the cash statement is missing, LibreFolio holds nothing yet. */
const PREVIEW: BrimSetPreview = {
    broker_id: BROKER,
    plugin_code: PLUGIN_CODE,
    batch_id: BATCH,
    members: [{file_id: CU_EARLY.file_id, filename: CU_EARLY.filename, role: 'custody', rows: 58, coverage: [{axis: 'trade', start: '2020-01-02', end: '2020-03-31'}]}],
    roles: [
        {code: 'custody', required: true, multiple: true, status: 'present', file_ids: [CU_EARLY.file_id]},
        {code: 'cash', required: true, multiple: true, status: 'missing', file_ids: []},
    ],
    missing: [{role: 'cash', start: '2020-01-01', end: '2020-03-31'}],
    segments: [],
    gaps: [],
    history_start: null,
    history_end: null,
    history_count: 0,
    warnings: [],
    complete: false,
};

/** What «Read as» offers this set, by the suffix of each option's testid: both report-set plugins, and one by one. */
const READ_AS_CHOICES = [PLUGIN_CODE, SECOND_SET_CODE, 'one-by-one'];

// ---------------------------------------------------------------------------
// Mounting, reading, pressing
// ---------------------------------------------------------------------------

/** The card in the wizard's modal, open, once the modal holds the focus; and the «Read as» select of the card. */
async function mountCardInWizardModal() {
    const onRequestClose = vi.fn().mockName('onRequestClose');
    const onReadAs = vi.fn().mockName('onReadAs');
    const card: ComponentProps<typeof Harness>['card'] = {
        set: SET,
        plugin: PLUGIN,
        previewState: {status: 'ready', preview: PREVIEW, error: null},
        selection: 'all',
        // The wizard opens the sets of its session on their card.
        expanded: true,
        analysed: false,
        uploadingRole: null,
        onToggleSelected: vi.fn(),
        onToggleExpanded: vi.fn(),
        onUploadMissing: vi.fn(),
        onPreviewFile: vi.fn(),
        onDeleteFile: vi.fn(),
        plugins: CATALOGUE,
        brokerDefaultPlugin: null,
        onReadAs,
        onReadAlone: vi.fn(),
        onRemoveFromSet: vi.fn(),
    };
    render(Harness, {onRequestClose, card});
    const modal = screen.getByTestId('report-set-escape-modal');
    // ModalBase focuses its backdrop on the next animation frame, and a focus placed before that frame would be
    // stolen by it: the barrier is that state, not a delay.
    await waitFor(() => expect(modal, 'premise: the open modal takes the focus').toHaveFocus());
    const root = within(within(modal).getByTestId('report-set-card')).getByTestId('report-set-read-as');
    const trigger = within(root).getByTestId('report-set-read-as-button');
    return {modal, root, trigger, onRequestClose, onReadAs};
}

/** The options of an open «Read as» list, by what they stand for: a plugin code, or one-by-one. */
function choicesIn(dropdown: HTMLElement): string[] {
    return [...dropdown.querySelectorAll<HTMLElement>('[data-testid^="report-set-read-as-option-"]')].map((option) => (option.dataset.testid ?? '').replace(/^report-set-read-as-option-/, ''));
}

/** Open means usable: the trigger says so, and the select's own dropdown is there. */
function expectReadAsOpen(root: HTMLElement, trigger: HTMLElement, why: string) {
    expect(trigger, why).toHaveAttribute('aria-expanded', 'true');
    expect(within(root).queryByTestId('report-set-read-as-dropdown'), why).not.toBeNull();
}

/** Closed means gone: the trigger says so, and the select has no dropdown, no listbox at all. */
function expectReadAsClosed(root: HTMLElement, trigger: HTMLElement, why: string) {
    expect(trigger, why).toHaveAttribute('aria-expanded', 'false');
    expect(within(root).queryByTestId('report-set-read-as-dropdown'), why).toBeNull();
    expect(within(root).queryByRole('listbox'), why).toBeNull();
}

/**
 * Opens «Read as» with a click on its trigger, and returns once its list is open with the focus still on the
 * trigger: SimpleSelect drives the list from there, naming the highlighted option with `aria-activedescendant`.
 */
async function openReadAs(root: HTMLElement, trigger: HTMLElement) {
    // A click leaves the focus on the button it pressed, in a browser; jsdom moves no focus on a click.
    trigger.focus();
    await fireEvent.click(trigger);
    expectReadAsOpen(root, trigger, 'premise: a click on the trigger opens the «Read as» list');
    const dropdown = within(root).getByTestId('report-set-read-as-dropdown');
    expect(choicesIn(dropdown).sort(), 'premise: the list offers the choices of the set').toEqual([...READ_AS_CHOICES].sort());
    expect(trigger, 'premise: the open select keeps the focus on its trigger').toHaveFocus();
    expect(trigger, 'premise: the trigger drives the open list, naming its highlighted option').toHaveAttribute('aria-activedescendant');
}

/**
 * One Escape, the way a browser delivers it: to the focused element, bubbling from there. It checks first that
 * the focus is where the test means it to be, and that it is inside the modal.
 */
async function pressEscape(modal: HTMLElement, focused: HTMLElement) {
    expect(focused, 'premise: the Escape goes to the element holding the focus').toHaveFocus();
    expect(modal.contains(focused), 'premise: the focused element is inside the modal').toBe(true);
    await fireEvent.keyDown(document.activeElement as HTMLElement, {key: 'Escape'});
}

// ---------------------------------------------------------------------------
// The tests
// ---------------------------------------------------------------------------

describe('ReportSetCard in the import wizard — one Escape on «Read as» closes its list, not the wizard', () => {
    it('Escape on the trigger of the open «Read as» list closes the list and does not request the close of the wizard (its discard confirmation); the next Escape does', async () => {
        const {modal, root, trigger, onRequestClose, onReadAs} = await mountCardInWizardModal();
        await openReadAs(root, trigger);

        await pressEscape(modal, trigger);

        expectReadAsClosed(root, trigger, 'the Escape on the trigger must close the open «Read as» list');
        expect(onReadAs, 'an Escape cancels the list: it must choose nothing').not.toHaveBeenCalled();
        expect(onRequestClose, 'one Escape on the open «Read as» list must close the list only: the onRequestClose of the wizard opens its «discard the import?» confirmation').not.toHaveBeenCalled();

        // The focus stays on the trigger, and a closed select consumes no Escape: the next one is the wizard's.
        await pressEscape(modal, trigger);
        expect(onRequestClose, 'with the «Read as» list closed, the next Escape must reach the wizard').toHaveBeenCalledTimes(1);
    });
});

describe('ReportSetCard in the import wizard — an Escape the card did not consume still reaches the wizard (control)', () => {
    it('«Read as» with its list closed: Escape on its trigger requests the close of the wizard, once', async () => {
        const {modal, root, trigger, onRequestClose} = await mountCardInWizardModal();
        trigger.focus();
        expectReadAsClosed(root, trigger, 'premise: the «Read as» list is closed');

        await pressEscape(modal, trigger);

        expect(onRequestClose, 'a «Read as» with its list closed consumed nothing, so the Escape must reach the wizard').toHaveBeenCalledTimes(1);
    });
});
