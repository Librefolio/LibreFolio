// @vitest-environment jsdom
/**
 * ProfileEditModal (plan 68, E10c2): the «Modifica i dati» window, standalone (E8 wires it into the asset window).
 *
 * Pinned, through the contract (the pending changes handed back, the requests sent), never through translated text:
 * - the rows show the pending «dry» voices, the panels the two maps; a row without a voice blocks «Tieni»;
 * - a percentage typed in percent («0,20») leaves as an exact fraction («0.002»); an untouched row from a file is handed
 *   back as it came;
 * - «Lascia vuoto» (the row's menu) is an `emptied` change, «Scrivi un valore» takes it back;
 * - an untouched window hands back exactly the changes it was given, those of voices the catalogue does not list too;
 * - «Tieni» asks `POST /assets/validate` first for an asset that exists, and marks the rows it refuses;
 * - «Chiedi tutto» asks without keys; an empty voice is filled «dalla fonte», an equal one shows nothing, a different
 *   one opens the comparison window grouped and named, and the differences chosen become «dalla fonte»;
 * - «Chiedi» on a row asks for its voice only;
 * - the sources are named as sources (E10c3): the comparison window's title and intro, the panels' «ask» button; a
 *   percentage field shows «%» beside it, a number its unit;
 * - in save mode the window sends `PATCH /assets` with `profilePatch`, marks the rows the backend refuses
 *   (`profileValueInvalid`), and hands the changes back only once committed;
 * - a value is written as the «Profilo» tab writes it (`formatProfileValue`): one way to write a profile value in the
 *   app, so «Adesso» reads as the tab does (a percentage in the interface locale, an amount with its currency).
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';
import ProfileEditModal from './ProfileEditModal.svelte';
import type {ProfileVoice} from './profileStore';
import type {AskAnswer, PendingChanges} from './profileEditState';
import {formatProfileValue} from './profileTabState';
import {uiLocale} from '$lib/stores/app/uiLocale';

function voice(key: string, shape: string, extra: Partial<ProfileVoice> = {}): ProfileVoice {
    return {key, shape, sign: null, unit: null, groups: [], key_figure: false, charted: false, volatile: false, choices: [], map_keys: null, ...extra} as ProfileVoice;
}

const CATALOGUE: ProfileVoice[] = [
    voice('geography', 'map', {map_keys: 'country', groups: ['classification']}),
    voice('sector', 'map', {map_keys: 'sector', groups: ['classification']}),
    voice('ter', 'percentage', {sign: 'non_negative', groups: ['key_figures']}),
    voice('fund_size', 'amount', {sign: 'non_negative', groups: ['key_figures']}),
    voice('maturity_date', 'date', {groups: ['key_figures']}),
    voice('fund_provider', 'text', {groups: ['fund']}),
    voice('distribution_policy', 'choice', {choices: ['accumulating', 'distributing'], groups: ['fund']}),
    voice('coupon_schedule', 'table', {sign: 'non_negative', groups: ['bond']}),
];

const FROM_FILE: PendingChanges = {fund_provider: {key: 'fund_provider', kind: 'value', value: 'Vanguard', origin: 'file'}};

function mount(extra: Record<string, unknown> = {}) {
    const onkeep = vi.fn();
    const onsaved = vi.fn();
    const ask = vi.fn();
    const save = vi.fn();
    // «Tieni» asks the backend's dry run first, for an asset that exists: by default it finds nothing.
    const validate = vi.fn().mockResolvedValue({committed: false, issues: [], warnings: []});
    render(ProfileEditModal, {
        open: true,
        assetName: 'Test ETF',
        mode: 'keep',
        assetId: 7,
        catalogue: CATALOGUE,
        current: {ter: {value: '0.0022', source: 'justetf'}},
        pending: FROM_FILE,
        sourceNames: {justetf: 'justETF'},
        currencies: [{value: 'EUR', label: 'EUR'}],
        onkeep,
        onsaved,
        ask,
        save,
        validate,
        ...extra,
    });
    return {onkeep, onsaved, ask, save, validate};
}

const row = (id: string) => document.querySelector(`tr[data-row-id="${id}"]`) as HTMLTableRowElement | null;
/** The row's badge publishes what the row is: `data-origin`, `data-state` (`value` | `emptied`), `data-issue`. */
const rowState = (id: string) => screen.getByTestId(`profile-row-state-${id}`);
const valueInput = (id: string) => row(id)?.querySelector('td[data-column-id="value"] input') as HTMLInputElement;
const validity = () => screen.getByTestId('profile-edit-validity');

/** Open a row's ⋮ menu. The menu follows its button and closes when the button has no size: jsdom lays nothing out. */
async function openRowMenu(id: string): Promise<void> {
    const button = screen.getByTestId(`row-actions-${id}`);
    vi.spyOn(button, 'getBoundingClientRect').mockReturnValue({left: 10, top: 10, right: 30, bottom: 30, width: 20, height: 20, x: 10, y: 10, toJSON: () => ({})} as DOMRect);
    await fireEvent.click(button);
}

/** «Tieni le modifiche», and the changes it hands back once the dry run answered. */
async function keep(onkeep: ReturnType<typeof vi.fn>): Promise<PendingChanges> {
    await fireEvent.click(screen.getByTestId('profile-edit-keep'));
    await waitFor(() => expect(onkeep).toHaveBeenCalledTimes(1));
    return onkeep.mock.calls[0][0] as PendingChanges;
}

async function addRowWithVoice(key: string): Promise<string> {
    await fireEvent.click(screen.getByTestId('profile-edit-add-row'));
    const id = 'row-1';
    await fireEvent.click(screen.getByTestId(`profile-row-voice-${id}-button`));
    await fireEvent.click(screen.getByTestId(`profile-row-voice-${id}-option-${key}`));
    return id;
}

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => cleanup());

describe('ProfileEditModal — values written as the tab writes them', () => {
    const nowText = (id: string) => (row(id)?.querySelector('td[data-column-id="now"]')?.textContent ?? '').replace(/\s+/g, ' ');
    const asTheTab = (key: string, value: unknown) => formatProfileValue(CATALOGUE.find((entry) => entry.key === key)!, value, {translate: (k) => get(_)(k), locale: uiLocale(), countryName: (iso3) => iso3});

    it('writes «Adesso» of a percentage and of an amount as the tab does', () => {
        mount({
            current: {ter: {value: '0.0022', source: 'justetf'}, fund_size: {value: {amount: '55200000000', currency: 'EUR'}, source: 'justetf'}},
            pending: {
                ter: {key: 'ter', kind: 'value', value: '0.0019', origin: 'new'},
                fund_size: {key: 'fund_size', kind: 'value', value: {amount: '56000000000', currency: 'EUR'}, origin: 'new'},
            },
        });
        expect(nowText('ter')).toContain(asTheTab('ter', '0.0022'));
        expect(nowText('fund_size')).toContain(asTheTab('fund_size', {amount: '55200000000', currency: 'EUR'}).replace(/\s+/g, ' '));
    });
});

describe('ProfileEditModal — rows and panels', () => {
    it('shows the pending dry voices as rows and the two maps as panels', () => {
        mount();
        expect(row('fund_provider')).not.toBeNull();
        expect(rowState('fund_provider').dataset.origin).toBe('file');
        expect(screen.getByTestId('profile-panel-geography')).toBeInTheDocument();
        expect(screen.getByTestId('profile-panel-sector')).toBeInTheDocument();
        expect(validity().dataset.valid).toBe('true');
    });

    it('a row without a voice blocks keeping', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('profile-edit-add-row'));
        expect(row('row-1')).not.toBeNull();
        expect(validity().dataset.valid).toBe('false');
        expect(screen.getByTestId('profile-edit-keep')).toBeDisabled();
    });

    it('a percentage typed in percent is kept as an exact fraction; the file row comes back as it was', async () => {
        const {onkeep} = mount();
        const id = await addRowWithVoice('ter');
        const input = valueInput(id);
        await fireEvent.input(input, {target: {value: '0,20'}});
        await fireEvent.blur(input);
        await waitFor(() => expect(validity().dataset.valid).toBe('true'));
        const pending = await keep(onkeep);
        expect(pending.ter).toMatchObject({kind: 'value', value: '0.002', origin: 'new'});
        expect(pending.fund_provider).toEqual(FROM_FILE.fund_provider);
    });

    it('«Leave empty» from the row menu is an emptied change, and «Write a value» takes it back', async () => {
        const {onkeep} = mount();
        await openRowMenu('fund_provider');
        await fireEvent.click(await screen.findByTestId('profile-row-empty-fund_provider'));
        expect(rowState('fund_provider').dataset.state).toBe('emptied');
        expect((await keep(onkeep)).fund_provider).toMatchObject({kind: 'emptied'});
    });

    it('«Write a value» undoes «Leave empty»', async () => {
        mount({pending: {fund_provider: {key: 'fund_provider', kind: 'emptied', origin: 'new'}}});
        expect(rowState('fund_provider').dataset.state).toBe('emptied');
        await openRowMenu('fund_provider');
        await fireEvent.click(await screen.findByTestId('profile-row-write-fund_provider'));
        expect(rowState('fund_provider').dataset.state).toBe('value');
        expect(validity().dataset.valid).toBe('false');
    });

    it('an untouched window hands back exactly what it was given, voices it does not know included', async () => {
        const given: PendingChanges = {
            ...FROM_FILE,
            sector: {key: 'sector', kind: 'value', value: {Technology: '0.6', Financials: '0.4'}, origin: 'file'},
            lane_62_voice: {key: 'lane_62_voice', kind: 'value', value: 'kept', origin: 'new'},
        };
        const {onkeep} = mount({pending: given, current: {ter: {value: '0.0022', source: 'justetf'}, geography: {value: {USA: '0.7', JPN: '0.3'}, source: 'justetf'}}});
        expect(await keep(onkeep)).toEqual(given);
    });

    it('«Keep» asks the backend first and marks the rows it refuses', async () => {
        const {onkeep, validate} = mount();
        validate.mockResolvedValueOnce({committed: false, issues: [{asset_id: 7, index: 0, code: 'profileValueInvalid', message: 'refused', params: {voice: 'fund_provider'}, field: 'profile.fund_provider'}]});
        await fireEvent.click(screen.getByTestId('profile-edit-keep'));
        expect(validate).toHaveBeenCalledWith([{asset_id: 7, profile: {fund_provider: 'Vanguard'}}]);
        await waitFor(() => expect(rowState('fund_provider').dataset.issue).toBe('backend'));
        expect(onkeep).not.toHaveBeenCalled();
    });

    it('an asset not created yet keeps without the dry run (its values are checked when it is created)', async () => {
        const {onkeep, validate} = mount({assetId: null, askTarget: {asset_type: 'ETF', enrichers: {}}});
        await keep(onkeep);
        expect(validate).not.toHaveBeenCalled();
    });
});

describe('ProfileEditModal — the sources and the units (E10c3)', () => {
    it('a percentage field shows «%» beside it, a number its unit', async () => {
        mount({catalogue: [...CATALOGUE, voice('modified_duration', 'number', {unit: 'years', groups: ['key_figures']})]});
        const id = await addRowWithVoice('ter');
        const unit = (rowId: string) => row(rowId)?.querySelector('[data-testid="cell-editable-text-unit"]');
        expect(unit(id)).toHaveTextContent(/^%$/);
        expect(unit('fund_provider')).toBeNull();
        await fireEvent.click(screen.getByTestId('profile-edit-add-row'));
        await fireEvent.click(screen.getByTestId('profile-row-voice-row-2-button'));
        await fireEvent.click(screen.getByTestId('profile-row-voice-row-2-option-modified_duration'));
        expect(unit('row-2')).toHaveTextContent(get(_)('assets.profile.units.years'));
    });

    it('the panels ask «the source», not «the provider»', () => {
        mount();
        expect(screen.getByTestId('distribution-ask-provider-sector')).toHaveAttribute('aria-label', get(_)('assets.profile.edit.askSource'));
    });

    it('the comparison window is «compare with the sources»', async () => {
        const {ask} = mount();
        ask.mockResolvedValue({voices: {ter: {value: '0.0019', source: 'justetf'}}, outcomes: [{code: 'justetf', status: 'ok'}]});
        await fireEvent.click(screen.getByTestId('profile-edit-ask-all'));
        await waitFor(() => expect(screen.getByTestId('comparison-title')).toHaveTextContent(get(_)('assets.profile.edit.comparisonTitle')));
        expect(screen.getByTestId('comparison-intro')).toHaveTextContent(get(_)('assets.profile.edit.comparisonDescription'));
    });
});

describe('ProfileEditModal — narrow screens (E10c4)', () => {
    /** The developer's rule: the table scrolls sideways, and no column shrinks below what it must show whole. */
    const minWidth = (column: string) => Number.parseInt(screen.getByTestId(`dt-header-${column}`).style.minWidth, 10);

    it('each column keeps the width its content needs: the badge, a voice name, a date or an amount, value and source', () => {
        mount();
        expect(minWidth('state')).toBeGreaterThanOrEqual(120);
        expect(minWidth('voice')).toBeGreaterThanOrEqual(200);
        expect(minWidth('value')).toBeGreaterThanOrEqual(220);
        expect(minWidth('now')).toBeGreaterThanOrEqual(200);
    });
});

describe('ProfileEditModal — asking the sources', () => {
    const ANSWER: AskAnswer = {
        voices: {
            fund_provider: {value: 'Vanguard', source: 'justetf'},
            ter: {value: '0.0019', source: 'justetf'},
            distribution_policy: {value: 'accumulating', source: 'justetf'},
        },
        outcomes: [{code: 'justetf', status: 'ok'}],
    };

    it('«Ask all» fills the empty, hides the equal, and compares the different', async () => {
        const {ask, onkeep} = mount();
        ask.mockResolvedValue(ANSWER);
        await fireEvent.click(screen.getByTestId('profile-edit-ask-all'));
        expect(ask).toHaveBeenCalledWith({asset_id: 7});
        await waitFor(() => expect(screen.getByTestId('comparison-modal')).toBeInTheDocument());
        expect(screen.getByTestId('comparison-card')).toHaveAttribute('data-field', 'ter');
        expect(screen.getByTestId('comparison-group')).toHaveAttribute('data-section', 'profile:key_figures');
        expect(screen.getByTestId('comparison-provider-label-ter')).toHaveTextContent('justETF');
        await fireEvent.click(screen.getByTestId('comparison-apply'));
        await waitFor(() => expect(rowState('ter').dataset.origin).toBe('source'));
        expect(rowState('distribution_policy').dataset.origin).toBe('source');
        const summary = screen.getByTestId('profile-ask-summary');
        expect(summary.dataset.filled).toBe('1');
        expect(summary.dataset.different).toBe('1');
        expect(summary.dataset.equal).toBe('1');
        const pending = await keep(onkeep);
        expect(pending.ter).toMatchObject({kind: 'source', source: 'justetf', seen: '0.0019'});
        expect(pending.distribution_policy).toMatchObject({kind: 'source', source: 'justetf', seen: 'accumulating'});
        expect(pending.fund_provider).toEqual(FROM_FILE.fund_provider);
    });

    it('«Ask» on a row asks for its voice only', async () => {
        const {ask} = mount();
        ask.mockResolvedValue({voices: {}, outcomes: [{code: 'justetf', status: 'not_found'}]});
        await fireEvent.click(screen.getByTestId('profile-row-ask-fund_provider'));
        expect(ask).toHaveBeenCalledWith({asset_id: 7, keys: ['fund_provider']});
        await waitFor(() => expect(screen.getByTestId('profile-ask-summary').dataset.missing).toBe('1'));
    });

    it('an asset not created yet asks by its type and enrichers', async () => {
        const {ask} = mount({assetId: null, askTarget: {asset_type: 'ETF', enrichers: {justetf: {params: {}}}}});
        ask.mockResolvedValue({voices: {}, outcomes: []});
        await fireEvent.click(screen.getByTestId('profile-edit-ask-all'));
        expect(ask).toHaveBeenCalledWith({asset_type: 'ETF', enrichers: {justetf: {params: {}}}});
    });
});

describe('ProfileEditModal — saving', () => {
    it('sends the profile patch, marks the refused rows, hands the changes back once committed', async () => {
        const {save, onsaved} = mount({mode: 'save'});
        save.mockResolvedValueOnce({committed: false, issues: [{asset_id: 7, index: 0, code: 'profileValueInvalid', message: 'refused', params: {voice: 'fund_provider'}, field: 'profile.fund_provider'}]});
        await fireEvent.click(screen.getByTestId('profile-edit-save'));
        expect(save).toHaveBeenCalledWith([{asset_id: 7, profile: {fund_provider: 'Vanguard'}}]);
        await waitFor(() => expect(rowState('fund_provider').dataset.issue).toBe('backend'));
        expect(onsaved).not.toHaveBeenCalled();

        save.mockResolvedValueOnce({committed: true, issues: [], warnings: []});
        const input = valueInput('fund_provider');
        await fireEvent.input(input, {target: {value: 'iShares'}});
        await fireEvent.blur(input);
        await waitFor(() => expect(rowState('fund_provider').dataset.issue).toBeUndefined());
        await fireEvent.click(screen.getByTestId('profile-edit-save'));
        expect(save).toHaveBeenLastCalledWith([{asset_id: 7, profile: {fund_provider: 'iShares'}}]);
        await waitFor(() => expect(onsaved).toHaveBeenCalledTimes(1));
        expect((onsaved.mock.calls[0][0] as PendingChanges).fund_provider).toMatchObject({kind: 'value', value: 'iShares'});
    });
});
