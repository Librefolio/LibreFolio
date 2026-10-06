/**
 * Report sets, phase C3 of the Danske Bank workstream — the gap-fix model ("Align with the bank").
 *
 * After the review, the wizard compares what LibreFolio will know with what the bank states at
 * its truth points (`POST /brokers/import/gap-fix`) and proposes the corrections that close the
 * difference. `gapFixModel.ts` keeps that logic out of the wizard: which parse results carry
 * truth points, how a truth position's fake asset id becomes the asset the user resolved, how
 * the requests are built (one per broker and plugin), and the view the step renders, with its
 * keys and its default selection. Every contract below is the one pinned in the plan (C3.0).
 *
 * Shapes. The module is structural: it accepts plain objects, decimals arrive as strings, and
 * these tests build plain objects. The inner layout of the view is the module's own business;
 * what the plan pins is its keys — group `<broker>:<plugin>`, checkpoint `<group>:cp:<i>`,
 * proposal `<checkpoint>:p:<j>`, verification `<group>:v:<i>` — the `needsCost` and `error` it
 * carries, and the `{tx, todos}` the selection hands over. So the view is read through those
 * only: `keyedNodes` collects every object of the view that carries a string `key`, wherever it
 * sits. Two choices the plan leaves open are pinned here, both after the wizard's own state:
 * `resolutions` is the wizard's `assetResolutions` (an array of `{fakeAssetId, resolvedAssetId}`,
 * as `isRowAssetResolved` already takes it), and a selection is a `ReadonlySet<string>` of keys.
 *
 * The module is loaded inside each test, through `c3()`: while it — or one of its exports — does
 * not exist, every test fails on its own with "not implemented yet", instead of the whole file
 * failing at collection and hiding which pieces are missing.
 *
 * Plan: `LibreFolio_developer_journal/Release_2/Phase_0/26_brimDanskeBank/plan-phase00BrimDanskeBankStep4Implementation.prompt.md`, C3.0.
 */
import {describe, expect, it, vi} from 'vitest';
import {FAKE_ASSET_ID_BASE} from '$lib/utils/brim/isFakeAssetId';

// ---------------------------------------------------------------------------
// The pinned shapes
// ---------------------------------------------------------------------------

interface TruthCash {
    currency: string;
    amount: string;
}
interface TruthPosition {
    asset_id: number;
    quantity: string;
    exactness: 'exact' | 'at_least';
    unit_cost?: {code: string; amount: string} | null;
}
interface Checkpoint {
    as_of: string;
    kind: 'opening' | 'gap';
    cash: TruthCash[];
    positions: TruthPosition[];
    absorbed?: unknown;
    evidence?: unknown[];
}
interface Verification {
    as_of: string;
    cash: TruthCash[];
    evidence?: unknown[];
}
interface TxLike {
    broker_id: number;
    type: string;
    date: string;
    asset_id?: number | null;
    quantity?: string | null;
    cash?: {code: string; amount: string} | null;
    tags?: string[];
    description?: string | null;
}
interface ParseResponseLike {
    plugin_code: string;
    transactions?: TxLike[];
    checkpoints?: Checkpoint[] | null;
    verifications?: Verification[] | null;
}
interface ParseResultLike {
    fileId: string;
    brokerId: number;
    /** The wizard's own pick; the truth source reads the plugin from the response instead. */
    pluginUsed?: string;
    status: 'pending' | 'parsing' | 'done' | 'error';
    response: ParseResponseLike | null;
}
interface TruthSource {
    fileId: string;
    brokerId: number;
    pluginCode: string;
    checkpoints: Checkpoint[];
    verifications: Verification[];
}
interface ResolveContext {
    fakeRemapByFile: ReadonlyMap<string, ReadonlyMap<number, number>>;
    survivorOf: ReadonlyMap<number, number>;
    resolutions: ReadonlyArray<{fakeAssetId: number; resolvedAssetId: number | null}>;
}
interface GapFixRequestBody {
    broker_id: number;
    plugin_code: string;
    checkpoints: Checkpoint[];
    verifications: Verification[];
    selection: TxLike[];
    pending_creates: TxLike[];
    pending_delete_tx_ids: number[];
}
interface FieldTodoLike {
    tx_index: number;
    field: string;
    severity: 'blocker' | 'warning';
    reason_code: string;
    message: string;
    evidence?: unknown[] | null;
    context?: Record<string, unknown> | null;
}
interface NoticeLike {
    severity: 'info' | 'warning';
    code: string;
    message: string;
    evidence?: unknown[];
    context?: Record<string, unknown> | null;
}
interface CashRowLike {
    currency: string;
    bank: string;
    librefolio: string;
    difference: string;
}
interface CheckpointResultLike {
    as_of: string;
    kind: 'opening' | 'gap';
    cash: CashRowLike[];
    positions: Array<{asset_id: number; exactness: 'exact' | 'at_least'; bank: string; librefolio: string; difference: string}>;
    proposals: TxLike[];
    todos: FieldTodoLike[];
    explanation: {absorbed_count?: number; absorbed_missing_count?: number; absorbed_missing_cash?: TruthCash[]; opening_cash?: TruthCash[]; unexplained_cash?: TruthCash[]; notes?: NoticeLike[]};
}
interface GapFixResponseLike {
    checkpoints: CheckpointResultLike[];
    verifications: Array<{as_of: string; ok: boolean; cash: CashRowLike[]}>;
}
interface GapFixOutcome {
    brokerId: number;
    pluginCode: string;
    response?: GapFixResponseLike;
    error?: string;
}
interface ImportTodoLike {
    field: string;
    severity: 'blocker' | 'warning';
    reasonCode: string;
    message: string;
    evidence?: unknown[];
    context?: Record<string, unknown>;
}
/** The view: its layout is the module's own; these tests read it through its keys. */
type GapFixView = unknown;

interface GapFixModule {
    truthSourcesOf(parseResults: ParseResultLike[]): TruthSource[];
    resolveTruthAssetId(fileId: string, assetId: number, ctx: ResolveContext): number;
    buildGapFixRequests(sources: TruthSource[], selection: TxLike[], pendingCreates: TxLike[], pendingDeleteTxIds: number[], resolveAsset: (fileId: string, assetId: number) => number): GapFixRequestBody[];
    buildGapFixView(outcomes: GapFixOutcome[], localizeTodo: (reasonCode: string, message: string) => string): GapFixView;
    gapFixHasSomethingToShow(view: GapFixView): boolean;
    defaultGapFixSelection(view: GapFixView): Iterable<string>;
    selectedGapFixCreates(view: GapFixView, selected: ReadonlySet<string>): Array<{tx: TxLike; todos: ImportTodoLike[]}>;
    gapFixSelectedCount(view: GapFixView, selected: ReadonlySet<string>): number;
}

/** One export of the module, loaded for the test that needs it. */
async function c3<K extends keyof GapFixModule>(name: K): Promise<GapFixModule[K]> {
    let mod: Partial<GapFixModule>;
    try {
        mod = (await import('./gapFixModel')) as unknown as Partial<GapFixModule>;
    } catch (error) {
        throw new Error(`gapFixModel.ts cannot be loaded — not implemented yet (gap-fix, phase C3): ${String(error)}`);
    }
    const fn = mod[name];
    if (typeof fn !== 'function') throw new Error(`gapFixModel.${name} is not implemented yet (gap-fix, phase C3)`);
    return fn as GapFixModule[K];
}

// ---------------------------------------------------------------------------
// Reading the view through its keys
// ---------------------------------------------------------------------------

type KeyedNode = Record<string, unknown> & {key: string};

/** Every object of the view that carries a string `key`, each once, wherever it sits (arrays, maps, records). */
function keyedNodes(view: GapFixView): KeyedNode[] {
    const found: KeyedNode[] = [];
    const seen = new Set<unknown>();
    const walk = (value: unknown): void => {
        if (value === null || typeof value !== 'object' || seen.has(value)) return;
        seen.add(value);
        if (value instanceof Set) return; // a set of keys holds no node
        if (value instanceof Map) {
            for (const item of value.values()) walk(item);
            return;
        }
        if (Array.isArray(value)) {
            for (const item of value) walk(item);
            return;
        }
        const record = value as Record<string, unknown>;
        if (typeof record.key === 'string') found.push(record as KeyedNode);
        for (const item of Object.values(record)) walk(item);
    };
    walk(view);
    return found;
}

/** The distinct keys of the view, sorted. */
function viewKeys(view: GapFixView): string[] {
    return [...new Set(keyedNodes(view).map((node) => node.key))].sort();
}

/** The node of the view with this key; a key the view lacks is a failure that names it. */
function nodeOf(view: GapFixView, key: string): KeyedNode {
    const node = keyedNodes(view).find((candidate) => candidate.key === key);
    if (!node) throw new Error(`the gap-fix view has no node with key "${key}"; its keys: ${JSON.stringify(viewKeys(view))}`);
    return node;
}

// ---------------------------------------------------------------------------
// Fixtures: invented truth points, in the shape the parse and POST /gap-fix return
// ---------------------------------------------------------------------------

/** Plugin fakes and the wizard's global fakes share one range, counting down from here. */
const B = FAKE_ASSET_ID_BASE;
const DANSKE = 'broker_danske_bank';
const OTHER_SET = 'broker_other_bank';
const GENERIC = 'broker_generic_csv';

const EVIDENCE = {title: 'Saldo', headers: ['Pvm', 'Saldo'], rows: [['02.02.2020', '2699,50']], row_numbers: [21], comment: null};

/** The opening truth point of a file: cash, two positions with plugin fakes, one with a real id. */
function openingCheckpoint(asOf = '2020-02-02'): Checkpoint {
    return {
        as_of: asOf,
        kind: 'opening',
        cash: [{currency: 'EUR', amount: '2699.50'}],
        positions: [
            {asset_id: B, quantity: '100', exactness: 'exact', unit_cost: null},
            {asset_id: B - 1, quantity: '180', exactness: 'at_least', unit_cost: null},
            {asset_id: 41, quantity: '5', exactness: 'exact', unit_cost: {code: 'EUR', amount: '12.50'}},
        ],
        absorbed: {count: 14, cash: [{currency: 'EUR', amount: '2699.50'}], rows: [{as_of: '2020-02-03', currency: 'EUR', amount: '-120', label: 'Osto Pohjola'}], opening_cash: [{currency: 'EUR', amount: '0'}]},
        evidence: [EVIDENCE],
    };
}

function gapCheckpoint(asOf: string, assetId: number): Checkpoint {
    return {as_of: asOf, kind: 'gap', cash: [{currency: 'EUR', amount: '1500.00'}], positions: [{asset_id: assetId, quantity: '30', exactness: 'at_least'}], absorbed: {count: 6, cash: [], rows: [], opening_cash: []}, evidence: []};
}

function verification(asOf: string, amount: string): Verification {
    return {as_of: asOf, cash: [{currency: 'EUR', amount}], evidence: [EVIDENCE]};
}

function source(fileId: string, brokerId: number, pluginCode: string, checkpoints: Checkpoint[], verifications: Verification[]): TruthSource {
    return {fileId, brokerId, pluginCode, checkpoints, verifications};
}

function tx(brokerId: number, date: string, over: Partial<TxLike> = {}): TxLike {
    return {broker_id: brokerId, type: 'DEPOSIT', date, cash: {code: 'EUR', amount: '10.00'}, tags: ['import'], ...over};
}

const MSG_COST = 'Enter the per-unit cost of this position (the bank’s website shows the average price)';

function proposal(type: string, over: Partial<TxLike> = {}): TxLike {
    return {broker_id: 7, type, date: '2020-02-02', tags: ['import', 'danske_bank', 'gap_fix'], description: 'Gap-fix 2020-02-02 — Danske Bank', ...over};
}

function cashRow(bank: string, librefolio: string, difference: string): CashRowLike {
    return {currency: 'EUR', bank, librefolio, difference};
}

const UNRESOLVED_NOTE: NoticeLike = {severity: 'warning', code: 'unresolved_asset', message: 'A position of the bank refers to a security that is not resolved yet: it was left out', evidence: [], context: {asset_id: B - 3}};

/** Broker 7: an opening with three proposals, a gap with two, one verification that holds. */
function response7(): GapFixResponseLike {
    return {
        checkpoints: [
            {
                as_of: '2020-02-02',
                kind: 'opening',
                cash: [cashRow('2699.50', '0', '2699.50')],
                positions: [
                    {asset_id: 41, exactness: 'exact', bank: '100', librefolio: '0', difference: '100'},
                    {asset_id: 42, exactness: 'at_least', bank: '180', librefolio: '0', difference: '180'},
                ],
                proposals: [proposal('DEPOSIT', {cash: {code: 'EUR', amount: '2699.50'}}), proposal('ADJUSTMENT', {asset_id: 41, quantity: '100'}), proposal('ADJUSTMENT', {asset_id: 42, quantity: '180'})],
                todos: [
                    // Out of order on purpose: tx_index, not position, says which proposal a todo belongs to.
                    {tx_index: 2, field: 'cost_basis_override', severity: 'blocker', reason_code: 'gap_fix_cost', message: MSG_COST, evidence: [EVIDENCE], context: {asset_id: 42}},
                    {tx_index: 1, field: 'cost_basis_override', severity: 'blocker', reason_code: 'gap_fix_cost', message: MSG_COST},
                ],
                explanation: {absorbed_count: 14, absorbed_missing_count: 14, absorbed_missing_cash: [{currency: 'EUR', amount: '2699.50'}], opening_cash: [{currency: 'EUR', amount: '0'}], unexplained_cash: [], notes: [UNRESOLVED_NOTE]},
            },
            {
                as_of: '2020-08-31',
                kind: 'gap',
                cash: [cashRow('1500.00', '3500.00', '-2000.00')],
                positions: [],
                proposals: [proposal('WITHDRAWAL', {date: '2020-08-31', cash: {code: 'EUR', amount: '-2000.00'}}), proposal('ADJUSTMENT', {date: '2020-08-31', asset_id: 43, quantity: '-30'})],
                todos: [
                    // tx_index counts inside this checkpoint: 0 is the withdrawal of the gap, not the deposit of the opening.
                    {tx_index: 0, field: 'cost_basis_override', severity: 'warning', reason_code: 'gap_fix_check', message: 'Check this correction'},
                    {tx_index: 1, field: 'quantity', severity: 'blocker', reason_code: 'gap_fix_quantity', message: 'Confirm the quantity'},
                ],
                explanation: {absorbed_count: 8, notes: []},
            },
        ],
        verifications: [{as_of: '2021-01-31', ok: true, cash: [cashRow('1994.46', '1994.46', '0.00')]}],
    };
}

/** Broker 9: one gap checkpoint with one proposal, and a verification that does not hold. */
function response9(): GapFixResponseLike {
    return {
        checkpoints: [{as_of: '2021-03-01', kind: 'gap', cash: [cashRow('80.00', '70.00', '10.00')], positions: [], proposals: [proposal('DEPOSIT', {broker_id: 9, date: '2021-03-01', cash: {code: 'EUR', amount: '10.00'}})], todos: [], explanation: {notes: []}}],
        verifications: [{as_of: '2021-06-30', ok: false, cash: [cashRow('100.00', '90.00', '10.00')]}],
    };
}

/** A response with nothing to correct: the positions were unresolved (only a note), and the verification holds. */
function quietResponse(): GapFixResponseLike {
    return {
        checkpoints: [{as_of: '2020-02-02', kind: 'opening', cash: [cashRow('0.00', '0.00', '0.00')], positions: [], proposals: [], todos: [], explanation: {notes: [UNRESOLVED_NOTE]}}],
        verifications: [{as_of: '2020-06-26', ok: true, cash: [cashRow('1994.46', '1994.46', '0.00')]}],
    };
}

const G7 = `7:${DANSKE}`;
const G8 = `8:${DANSKE}`;
const G9 = `9:${DANSKE}`;

const localize = () => vi.fn((reasonCode: string, message: string) => `«${reasonCode}» ${message}`);

// ---------------------------------------------------------------------------
// truthSourcesOf
// ---------------------------------------------------------------------------

describe('truthSourcesOf', () => {
    const response = (over: Partial<ParseResponseLike>): ParseResponseLike => ({plugin_code: DANSKE, transactions: [], ...over});

    it('one source per done result whose response holds a checkpoint or a verification, in input order', async () => {
        const truthSourcesOf = await c3('truthSourcesOf');
        const checkpoints = [openingCheckpoint()];
        const verifications = [verification('2020-06-26', '1994.46')];
        const results: ParseResultLike[] = [
            {fileId: 'only-verifications', brokerId: 9, status: 'done', response: response({checkpoints: [], verifications})},
            {fileId: 'generic', brokerId: 7, status: 'done', response: response({plugin_code: GENERIC, checkpoints: [], verifications: []})},
            {fileId: 'combined-a', brokerId: 7, status: 'done', response: response({checkpoints, verifications})},
            {fileId: 'no-fields', brokerId: 7, status: 'done', response: response({})},
            {fileId: 'null-fields', brokerId: 7, status: 'done', response: response({checkpoints: null, verifications: null})},
            {fileId: 'failed', brokerId: 7, status: 'error', response: response({checkpoints, verifications})},
            {fileId: 'pending', brokerId: 7, status: 'pending', response: null},
            {fileId: 'parsing', brokerId: 7, status: 'parsing', response: response({checkpoints})},
            {fileId: 'done-without-response', brokerId: 7, status: 'done', response: null},
        ];

        const sources = truthSourcesOf(results);

        expect(sources.map((s) => s.fileId)).toEqual(['only-verifications', 'combined-a']);
    });

    it('carries the file, the broker, the plugin of the response and the truth points as they came', async () => {
        const truthSourcesOf = await c3('truthSourcesOf');
        const checkpoints = [openingCheckpoint(), gapCheckpoint('2020-08-31', B - 2)];
        const verifications = [verification('2021-01-31', '1994.46')];
        // The wizard's own pick says generic: the truth points belong to the plugin that produced them.
        const sources = truthSourcesOf([{fileId: 'combined-a', brokerId: 7, pluginUsed: GENERIC, status: 'done', response: response({checkpoints, verifications})}]);

        expect(sources).toEqual([{fileId: 'combined-a', brokerId: 7, pluginCode: DANSKE, checkpoints: [openingCheckpoint(), gapCheckpoint('2020-08-31', B - 2)], verifications: [verification('2021-01-31', '1994.46')]}]);
    });

    it('a source with only checkpoints, or only verifications, has an empty list for the other', async () => {
        const truthSourcesOf = await c3('truthSourcesOf');
        const sources = truthSourcesOf([
            {fileId: 'checkpoints-only', brokerId: 7, status: 'done', response: response({checkpoints: [openingCheckpoint()]})},
            {fileId: 'verifications-only', brokerId: 7, status: 'done', response: response({verifications: [verification('2020-06-26', '1.00')], checkpoints: null})},
        ]);

        expect(sources.map((s) => [s.fileId, s.checkpoints.length, s.verifications.length])).toEqual([
            ['checkpoints-only', 1, 0],
            ['verifications-only', 0, 1],
        ]);
    });

    it('is empty for no results, or for results without truth points', async () => {
        const truthSourcesOf = await c3('truthSourcesOf');
        expect(truthSourcesOf([])).toEqual([]);
        expect(truthSourcesOf([{fileId: 'generic', brokerId: 7, status: 'done', response: {plugin_code: GENERIC, transactions: [tx(7, '2025-01-01')]}}])).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// resolveTruthAssetId
// ---------------------------------------------------------------------------

describe('resolveTruthAssetId', () => {
    const ctx = (over: Partial<ResolveContext> = {}): ResolveContext => ({fakeRemapByFile: new Map(), survivorOf: new Map(), resolutions: [], ...over});

    it('a real asset id passes through, whatever the context holds', async () => {
        const resolveTruthAssetId = await c3('resolveTruthAssetId');
        const busy = ctx({
            fakeRemapByFile: new Map([['file-a', new Map([[B, B]])]]),
            survivorOf: new Map([[B, B]]),
            resolutions: [{fakeAssetId: B, resolvedAssetId: 501}],
        });

        expect(resolveTruthAssetId('file-a', 42, busy)).toBe(42);
        expect(resolveTruthAssetId('a-file-the-context-does-not-know', 42, busy)).toBe(42);
        expect(resolveTruthAssetId('file-a', 1, ctx())).toBe(1);
    });

    it('per-file remap: the same plugin fake id in two files is two different globals', async () => {
        const resolveTruthAssetId = await c3('resolveTruthAssetId');
        const remap = new Map([
            ['file-a', new Map([[B, B]])],
            ['file-b', new Map([[B, B - 1]])],
        ]);

        // Unresolved: each comes back as its own global fake.
        expect(resolveTruthAssetId('file-a', B, ctx({fakeRemapByFile: remap}))).toBe(B);
        expect(resolveTruthAssetId('file-b', B, ctx({fakeRemapByFile: remap}))).toBe(B - 1);

        // Resolved: each to the asset of its own instrument.
        const resolutions = [
            {fakeAssetId: B, resolvedAssetId: 11},
            {fakeAssetId: B - 1, resolvedAssetId: 22},
        ];
        expect(resolveTruthAssetId('file-a', B, ctx({fakeRemapByFile: remap, resolutions}))).toBe(11);
        expect(resolveTruthAssetId('file-b', B, ctx({fakeRemapByFile: remap, resolutions}))).toBe(22);
    });

    it('folds through the unification: a global folded into another resolves as its survivor', async () => {
        const resolveTruthAssetId = await c3('resolveTruthAssetId');
        const remap = new Map([
            ['file-a', new Map([[B, B]])],
            ['file-b', new Map([[B, B - 1]])],
        ]);
        // The unification step folded file-b's instrument (global B-1) into file-a's (global B).
        const survivorOf = new Map([
            [B, B],
            [B - 1, B],
        ]);

        expect(resolveTruthAssetId('file-b', B, ctx({fakeRemapByFile: remap, survivorOf, resolutions: [{fakeAssetId: B, resolvedAssetId: 501}]}))).toBe(501);
        // The survivor is still unresolved: the position keeps the survivor's fake id.
        expect(resolveTruthAssetId('file-b', B, ctx({fakeRemapByFile: remap, survivorOf, resolutions: [{fakeAssetId: B, resolvedAssetId: null}]}))).toBe(B);
    });

    it('a resolved survivor gives its real asset; an unresolved one stays the global fake', async () => {
        const resolveTruthAssetId = await c3('resolveTruthAssetId');
        const remap = new Map([['file-a', new Map([[B, B - 4]])]]);

        // No survivor recorded: the global is its own survivor.
        expect(resolveTruthAssetId('file-a', B, ctx({fakeRemapByFile: remap, resolutions: [{fakeAssetId: B - 4, resolvedAssetId: 77}]}))).toBe(77);
        expect(resolveTruthAssetId('file-a', B, ctx({fakeRemapByFile: remap, resolutions: [{fakeAssetId: B - 4, resolvedAssetId: null}]}))).toBe(B - 4);
        // No resolution at all for it.
        expect(resolveTruthAssetId('file-a', B, ctx({fakeRemapByFile: remap}))).toBe(B - 4);
    });

    it('a plugin fake id absent from its file’s remap is returned unchanged, never looked up among the globals', async () => {
        const resolveTruthAssetId = await c3('resolveTruthAssetId');
        // file-a's rows got the globals B and B-1. file-b's rows only used its plugin id B (global B-2);
        // its truth position on plugin id B-1 is a title that never moved in file-b's rows. The number
        // B-1 is also file-a's second instrument — resolved, and folded — which file-b's title is not.
        const remap = new Map([
            [
                'file-a',
                new Map([
                    [B, B],
                    [B - 1, B - 1],
                ]),
            ],
            ['file-b', new Map([[B, B - 2]])],
        ]);
        const survivorOf = new Map([
            [B, B],
            [B - 1, B],
            [B - 2, B - 2],
        ]);
        const resolutions = [
            {fakeAssetId: B, resolvedAssetId: 501},
            {fakeAssetId: B - 1, resolvedAssetId: 77},
            {fakeAssetId: B - 2, resolvedAssetId: 88},
        ];
        const full = ctx({fakeRemapByFile: remap, survivorOf, resolutions});

        // Unchanged: the backend skips it with the note `unresolved_asset`.
        expect(resolveTruthAssetId('file-b', B - 1, full)).toBe(B - 1);
        // The same for a file the context has no remap for at all.
        expect(resolveTruthAssetId('file-unknown', B, full)).toBe(B);
        // Contrast, same context: the ids that did appear in the rows resolve.
        expect(resolveTruthAssetId('file-b', B, full)).toBe(88);
        expect(resolveTruthAssetId('file-a', B - 1, full)).toBe(501);
    });
});

// ---------------------------------------------------------------------------
// buildGapFixRequests
// ---------------------------------------------------------------------------

describe('buildGapFixRequests', () => {
    /** What the injected resolver answers, per file and plugin id; any other id comes back as it was. */
    const RESOLVED = new Map<string, number>([
        [`file-a#${B}`, 501],
        [`file-a#${B - 1}`, B - 7],
        [`file-c#${B}`, 502],
        [`file-b#${B - 2}`, 503],
        [`file-d#${B}`, 504],
    ]);
    const resolver = () => vi.fn((fileId: string, assetId: number) => RESOLVED.get(`${fileId}#${assetId}`) ?? assetId);
    const withIds = (checkpoint: Checkpoint, ids: number[]): Checkpoint => ({...checkpoint, positions: checkpoint.positions.map((position, index) => ({...position, asset_id: ids[index]}))});

    const SELECTION = [tx(7, '2020-03-20'), tx(9, '2020-03-21'), tx(7, '2020-03-31', {type: 'FEE', cash: {code: 'EUR', amount: '-3.50'}}), tx(11, '2020-04-01')];
    const PENDING = [tx(9, '2020-01-10'), tx(7, '2020-01-11', {type: 'WITHDRAWAL', cash: {code: 'EUR', amount: '-5.00'}})];
    const DELETES = [601, 602, 603];

    it('one request per broker and plugin, in the order of the first source of each', async () => {
        const buildGapFixRequests = await c3('buildGapFixRequests');
        const sources = [source('file-a', 7, DANSKE, [openingCheckpoint()], []), source('file-b', 9, DANSKE, [gapCheckpoint('2020-08-31', B - 2)], []), source('file-c', 7, DANSKE, [gapCheckpoint('2021-01-04', B)], []), source('file-d', 7, OTHER_SET, [gapCheckpoint('2021-02-01', B)], [])];

        const requests = buildGapFixRequests(sources, SELECTION, PENDING, DELETES, resolver());

        expect(requests.map((r) => [r.broker_id, r.plugin_code])).toEqual([
            [7, DANSKE],
            [9, DANSKE],
            [7, OTHER_SET],
        ]);
    });

    it('scenario 8: two sources of one broker and plugin are one request with the union of their truth points', async () => {
        const buildGapFixRequests = await c3('buildGapFixRequests');
        const sources = [source('file-a', 7, DANSKE, [openingCheckpoint('2020-02-02')], [verification('2020-06-26', '1994.46')]), source('file-c', 7, DANSKE, [gapCheckpoint('2021-01-04', B)], [verification('2021-06-30', '120.00')])];

        const [request, ...others] = buildGapFixRequests(sources, SELECTION, PENDING, DELETES, resolver());

        expect(others).toEqual([]);
        expect(request.checkpoints.map((c) => [c.as_of, c.kind])).toEqual([
            ['2020-02-02', 'opening'],
            ['2021-01-04', 'gap'],
        ]);
        expect(request.verifications).toEqual([verification('2020-06-26', '1994.46'), verification('2021-06-30', '120.00')]);
    });

    it('copies every checkpoint with its positions resolved through resolveAsset(fileId, id) of its own source, the rest unchanged', async () => {
        const buildGapFixRequests = await c3('buildGapFixRequests');
        const resolveAsset = resolver();
        // file-a and file-c both use the plugin id B: two files, two instruments, two answers.
        const sources = [source('file-a', 7, DANSKE, [openingCheckpoint()], []), source('file-c', 7, DANSKE, [gapCheckpoint('2021-01-04', B)], [])];

        const [request] = buildGapFixRequests(sources, SELECTION, PENDING, DELETES, resolveAsset);

        expect(resolveAsset).toHaveBeenCalledWith('file-a', B);
        expect(resolveAsset).toHaveBeenCalledWith('file-a', B - 1);
        expect(resolveAsset).toHaveBeenCalledWith('file-c', B);
        expect(resolveAsset).not.toHaveBeenCalledWith('file-c', B - 1);
        expect(request.checkpoints).toEqual([withIds(openingCheckpoint(), [501, B - 7, 41]), withIds(gapCheckpoint('2021-01-04', B), [502])]);
    });

    it('never rewrites the sources it reads', async () => {
        const buildGapFixRequests = await c3('buildGapFixRequests');
        const sources = [source('file-a', 7, DANSKE, [openingCheckpoint()], [verification('2020-06-26', '1994.46')])];

        buildGapFixRequests(sources, SELECTION, PENDING, DELETES, resolver());

        expect(sources).toEqual([source('file-a', 7, DANSKE, [openingCheckpoint()], [verification('2020-06-26', '1994.46')])]);
    });

    it('filters the selection and the pending creates on the broker of the request; the deletions go to every request whole', async () => {
        const buildGapFixRequests = await c3('buildGapFixRequests');
        const sources = [source('file-a', 7, DANSKE, [openingCheckpoint()], []), source('file-b', 9, DANSKE, [gapCheckpoint('2020-08-31', B - 2)], [])];

        const requests = buildGapFixRequests(sources, SELECTION, PENDING, DELETES, resolver());

        expect(requests).toEqual([
            {
                broker_id: 7,
                plugin_code: DANSKE,
                checkpoints: [withIds(openingCheckpoint(), [501, B - 7, 41])],
                verifications: [],
                selection: [SELECTION[0], SELECTION[2]],
                pending_creates: [PENDING[1]],
                pending_delete_tx_ids: DELETES,
            },
            {
                broker_id: 9,
                plugin_code: DANSKE,
                checkpoints: [withIds(gapCheckpoint('2020-08-31', B - 2), [503])],
                verifications: [],
                selection: [SELECTION[1]],
                pending_creates: [PENDING[0]],
                pending_delete_tx_ids: DELETES,
            },
        ]);
    });

    it('a request of verifications only carries no checkpoint', async () => {
        const buildGapFixRequests = await c3('buildGapFixRequests');
        const [request] = buildGapFixRequests([source('file-a', 7, DANSKE, [], [verification('2020-06-26', '1994.46')])], SELECTION, [], [], resolver());

        expect(request).toEqual({broker_id: 7, plugin_code: DANSKE, checkpoints: [], verifications: [verification('2020-06-26', '1994.46')], selection: [SELECTION[0], SELECTION[2]], pending_creates: [], pending_delete_tx_ids: []});
    });

    it('a source without checkpoints and verifications makes no request', async () => {
        const buildGapFixRequests = await c3('buildGapFixRequests');
        const sources = [source('file-a', 7, DANSKE, [openingCheckpoint()], []), source('file-e', 11, DANSKE, [], [])];

        const requests = buildGapFixRequests(sources, SELECTION, PENDING, DELETES, resolver());

        expect(requests.map((r) => r.broker_id)).toEqual([7]);
        expect(buildGapFixRequests([source('file-e', 11, DANSKE, [], [])], SELECTION, PENDING, DELETES, resolver())).toEqual([]);
    });

    it('no source, no request', async () => {
        const buildGapFixRequests = await c3('buildGapFixRequests');
        const resolveAsset = resolver();

        expect(buildGapFixRequests([], SELECTION, PENDING, DELETES, resolveAsset)).toEqual([]);
        expect(resolveAsset).not.toHaveBeenCalled();
    });
});

// ---------------------------------------------------------------------------
// buildGapFixView
// ---------------------------------------------------------------------------

describe('buildGapFixView', () => {
    it('keys: <broker>:<plugin> per outcome, <group>:cp:<i>, <checkpoint>:p:<j>, <group>:v:<i>', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const view = buildGapFixView(
            [
                {brokerId: 7, pluginCode: DANSKE, response: response7()},
                {brokerId: 9, pluginCode: DANSKE, response: response9()},
            ],
            localize(),
        );

        expect(viewKeys(view)).toEqual([G7, `${G7}:cp:0`, `${G7}:cp:0:p:0`, `${G7}:cp:0:p:1`, `${G7}:cp:0:p:2`, `${G7}:cp:1`, `${G7}:cp:1:p:0`, `${G7}:cp:1:p:1`, `${G7}:v:0`, G9, `${G9}:cp:0`, `${G9}:cp:0:p:0`, `${G9}:v:0`].sort());
    });

    it('attaches each todo to the proposal its tx_index names, inside its own checkpoint, as an ImportTodo', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const selectedGapFixCreates = await c3('selectedGapFixCreates');
        const localizeTodo = localize();
        const view = buildGapFixView([{brokerId: 7, pluginCode: DANSKE, response: response7()}], localizeTodo);
        const todosOf = (key: string) => {
            const creates = selectedGapFixCreates(view, new Set([key]));
            expect(creates, `exactly one create for ${key}`).toHaveLength(1);
            return creates[0].todos;
        };

        expect(todosOf(`${G7}:cp:0:p:0`)).toEqual([]);
        expect(todosOf(`${G7}:cp:0:p:1`)).toEqual([{field: 'cost_basis_override', severity: 'blocker', reasonCode: 'gap_fix_cost', message: `«gap_fix_cost» ${MSG_COST}`, evidence: [], context: undefined}]);
        expect(todosOf(`${G7}:cp:0:p:2`)).toEqual([{field: 'cost_basis_override', severity: 'blocker', reasonCode: 'gap_fix_cost', message: `«gap_fix_cost» ${MSG_COST}`, evidence: [EVIDENCE], context: {asset_id: 42}}]);
        expect(todosOf(`${G7}:cp:1:p:0`)).toEqual([{field: 'cost_basis_override', severity: 'warning', reasonCode: 'gap_fix_check', message: '«gap_fix_check» Check this correction', evidence: [], context: undefined}]);
        expect(todosOf(`${G7}:cp:1:p:1`)).toEqual([{field: 'quantity', severity: 'blocker', reasonCode: 'gap_fix_quantity', message: '«gap_fix_quantity» Confirm the quantity', evidence: [], context: undefined}]);
    });

    it('localizes each todo message through the callback, with its reason code and the backend message', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const localizeTodo = localize();

        buildGapFixView([{brokerId: 7, pluginCode: DANSKE, response: response7()}], localizeTodo);

        expect(localizeTodo).toHaveBeenCalledWith('gap_fix_cost', MSG_COST);
        expect(localizeTodo).toHaveBeenCalledWith('gap_fix_check', 'Check this correction');
        expect(localizeTodo).toHaveBeenCalledWith('gap_fix_quantity', 'Confirm the quantity');
    });

    it('hands the proposal over as the backend proposed it', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const selectedGapFixCreates = await c3('selectedGapFixCreates');
        const view = buildGapFixView([{brokerId: 7, pluginCode: DANSKE, response: response7()}], localize());

        expect(selectedGapFixCreates(view, new Set([`${G7}:cp:0:p:0`])).map((create) => create.tx)).toEqual([proposal('DEPOSIT', {cash: {code: 'EUR', amount: '2699.50'}})]);
    });

    it('needsCost only for a proposal with a blocker todo on cost_basis_override', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const view = buildGapFixView([{brokerId: 7, pluginCode: DANSKE, response: response7()}], localize());

        expect(nodeOf(view, `${G7}:cp:0:p:0`).needsCost, 'no todo').toBe(false);
        expect(nodeOf(view, `${G7}:cp:0:p:1`).needsCost, 'blocker on the cost').toBe(true);
        expect(nodeOf(view, `${G7}:cp:0:p:2`).needsCost, 'blocker on the cost, with evidence').toBe(true);
        expect(nodeOf(view, `${G7}:cp:1:p:0`).needsCost, 'a warning on the cost').toBe(false);
        expect(nodeOf(view, `${G7}:cp:1:p:1`).needsCost, 'a blocker on another field').toBe(false);
    });

    it('an outcome in error is a group with its error and no rows', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const view = buildGapFixView(
            [
                {brokerId: 7, pluginCode: DANSKE, response: response7()},
                {brokerId: 8, pluginCode: DANSKE, error: 'HTTP 500: gap-fix failed'},
            ],
            localize(),
        );

        expect(nodeOf(view, G8).error).toBe('HTTP 500: gap-fix failed');
        expect(viewKeys(view).filter((key) => key.startsWith(`${G8}:`))).toEqual([]);
        // The other group is unaffected.
        expect(viewKeys(view).filter((key) => key.startsWith(`${G7}:`))).toHaveLength(8);
    });
});

// ---------------------------------------------------------------------------
// gapFixHasSomethingToShow
// ---------------------------------------------------------------------------

describe('gapFixHasSomethingToShow', () => {
    it('is false with only matching verifications and notes: an unresolved position does not open the step', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const gapFixHasSomethingToShow = await c3('gapFixHasSomethingToShow');

        expect(gapFixHasSomethingToShow(buildGapFixView([{brokerId: 7, pluginCode: DANSKE, response: quietResponse()}], localize()))).toBe(false);
        expect(gapFixHasSomethingToShow(buildGapFixView([], localize()))).toBe(false);
    });

    it('is true with a proposal', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const gapFixHasSomethingToShow = await c3('gapFixHasSomethingToShow');
        const quiet = quietResponse();
        quiet.checkpoints[0].proposals = [proposal('DEPOSIT', {cash: {code: 'EUR', amount: '0.05'}})];

        expect(gapFixHasSomethingToShow(buildGapFixView([{brokerId: 7, pluginCode: DANSKE, response: quiet}], localize()))).toBe(true);
    });

    it('is true with a verification that does not hold, even without proposals', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const gapFixHasSomethingToShow = await c3('gapFixHasSomethingToShow');
        const quiet = quietResponse();
        quiet.verifications[0] = {as_of: '2020-06-26', ok: false, cash: [cashRow('1994.46', '2010.00', '-15.54')]};

        expect(gapFixHasSomethingToShow(buildGapFixView([{brokerId: 7, pluginCode: DANSKE, response: quiet}], localize()))).toBe(true);
    });

    it('is true with a group in error', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const gapFixHasSomethingToShow = await c3('gapFixHasSomethingToShow');
        const view = buildGapFixView(
            [
                {brokerId: 7, pluginCode: DANSKE, response: quietResponse()},
                {brokerId: 8, pluginCode: DANSKE, error: 'HTTP 500: gap-fix failed'},
            ],
            localize(),
        );

        expect(gapFixHasSomethingToShow(view)).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// Selection: defaultGapFixSelection, selectedGapFixCreates, gapFixSelectedCount
// ---------------------------------------------------------------------------

describe('the selection of the corrections', () => {
    const twoGroups = (): GapFixOutcome[] => [
        {brokerId: 7, pluginCode: DANSKE, response: response7()},
        {brokerId: 9, pluginCode: DANSKE, response: response9()},
    ];
    const ALL_PROPOSALS = [`${G7}:cp:0:p:0`, `${G7}:cp:0:p:1`, `${G7}:cp:0:p:2`, `${G7}:cp:1:p:0`, `${G7}:cp:1:p:1`, `${G9}:cp:0:p:0`];

    it('D-S14: every proposal key is selected by default, and nothing else', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const defaultGapFixSelection = await c3('defaultGapFixSelection');
        const selection = [...defaultGapFixSelection(buildGapFixView(twoGroups(), localize()))];

        expect(new Set(selection)).toEqual(new Set(ALL_PROPOSALS));
        expect(selection).toHaveLength(ALL_PROPOSALS.length);
    });

    it('no proposal, an empty default selection', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const defaultGapFixSelection = await c3('defaultGapFixSelection');
        const view = buildGapFixView(
            [
                {brokerId: 7, pluginCode: DANSKE, response: quietResponse()},
                {brokerId: 8, pluginCode: DANSKE, error: 'HTTP 500: gap-fix failed'},
            ],
            localize(),
        );

        expect([...defaultGapFixSelection(view)]).toEqual([]);
    });

    it('selectedGapFixCreates: the selected proposals only, by group, then checkpoint, then proposal — not in selection order', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const selectedGapFixCreates = await c3('selectedGapFixCreates');
        const view = buildGapFixView(twoGroups(), localize());
        const selected = new Set([`${G9}:cp:0:p:0`, `${G7}:cp:1:p:0`, `${G7}:cp:0:p:2`, `${G7}:cp:0:p:0`]);

        const creates = selectedGapFixCreates(view, selected);

        expect(creates.map((create) => [create.tx.broker_id, create.tx.date, create.tx.type, create.tx.asset_id ?? null])).toEqual([
            [7, '2020-02-02', 'DEPOSIT', null],
            [7, '2020-02-02', 'ADJUSTMENT', 42],
            [7, '2020-08-31', 'WITHDRAWAL', null],
            [9, '2021-03-01', 'DEPOSIT', null],
        ]);
    });

    it('selectedGapFixCreates ignores keys that name no proposal of the view', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const selectedGapFixCreates = await c3('selectedGapFixCreates');
        const view = buildGapFixView(twoGroups(), localize());

        expect(selectedGapFixCreates(view, new Set([G7, `${G7}:cp:0`, `${G7}:v:0`, `${G7}:cp:5:p:0`, '3:broker_gone:cp:0:p:0']))).toEqual([]);
        expect(selectedGapFixCreates(view, new Set())).toEqual([]);
    });

    it('gapFixSelectedCount counts the selected proposals of the view and nothing else', async () => {
        const buildGapFixView = await c3('buildGapFixView');
        const gapFixSelectedCount = await c3('gapFixSelectedCount');
        const view = buildGapFixView(twoGroups(), localize());

        expect(gapFixSelectedCount(view, new Set(ALL_PROPOSALS))).toBe(6);
        expect(gapFixSelectedCount(view, new Set([`${G7}:cp:0:p:1`, `${G9}:cp:0:p:0`, G7, `${G7}:cp:0`, `${G7}:v:0`, '3:broker_gone:cp:0:p:0']))).toBe(2);
        expect(gapFixSelectedCount(view, new Set())).toBe(0);
    });
});
