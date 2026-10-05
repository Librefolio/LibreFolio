/**
 * "Align with the bank" (`gapFix`) in the import wizard: the pure half of the step.
 *
 * A report-set plugin gives its parse the bank's truth points: checkpoints (cash and positions on
 * the eve of a segment) and verifications (cash only). After the review the wizard asks
 * `POST /brokers/import/gap-fix` to compare them with what LibreFolio will know, and shows the
 * corrections that close the difference. This module decides, outside the wizard, which parse
 * results carry truth points, how a truth position's fake asset id becomes the asset the user
 * resolved, how the requests are built (one per broker and plugin), and the view the step renders,
 * with its keys and its default selection (every correction selected, D-S14). The wizard keeps
 * the reactive state and the server calls.
 *
 * The inputs are read structurally: the generated API types widen the nullable fields, and the
 * decimals arrive as strings.
 *
 * Design: `LibreFolio_developer_journal/Release_2/Phase_0/26_brimDanskeBank/design-phase00BrimReportSets.md`, §3.6 and §4.6–§4.7.
 */
import {isFakeAssetId} from '$lib/utils/brim/isFakeAssetId';
import type {BrimEvidence} from '$lib/types/files';
import type {ImportTodo} from '$lib/utils/transactions/txPayloadHelpers';

type Loose = Record<string, unknown>;

/** A truth point as the parse returned it (`BRIMCheckpoint` / `BRIMVerification`): only the positions are rewritten. */
export type TruthPoint = Loose;

/** The parse-result fields the truth sources read (the wizard's `ParsedFileResult`). */
export interface TruthSourceInput {
    fileId: string;
    brokerId: number;
    status: string;
    pluginUsed?: string | null;
    response?: unknown;
}

/** The truth points of one parsed file, with the plugin that produced them. */
export interface TruthSource {
    fileId: string;
    brokerId: number;
    pluginCode: string;
    checkpoints: TruthPoint[];
    verifications: TruthPoint[];
}

/** What turns a truth position's fake asset id into the asset the wizard resolved. */
export interface TruthAssetContext {
    /** Per file: plugin fake id → the global fake id of its rows (`MergeResult.fakeRemapByFile`). */
    fakeRemapByFile: ReadonlyMap<string, ReadonlyMap<number, number>>;
    /** Global fake id → the global fake id of the asset it was unified into. */
    survivorOf: ReadonlyMap<number, number>;
    /** The wizard's asset resolutions, one per surviving fake id. */
    resolutions: ReadonlyArray<{fakeAssetId: number; resolvedAssetId?: number | null}>;
}

/** The body of one `POST /brokers/import/gap-fix`. */
export interface GapFixRequestBody<T> {
    broker_id: number;
    plugin_code: string;
    checkpoints: TruthPoint[];
    verifications: TruthPoint[];
    selection: T[];
    pending_creates: T[];
    pending_delete_tx_ids: number[];
}

/** What one request gave: the response, or the error to show in its group. */
export interface GapFixOutcome {
    brokerId: number;
    pluginCode: string;
    response?: unknown;
    error?: string | null;
}

export interface GapFixAmount {
    currency: string;
    amount: string;
}

export interface GapFixCashRow {
    currency: string;
    bank: string;
    librefolio: string;
    difference: string;
}

export interface GapFixPositionRow {
    assetId: number;
    exactness: 'exact' | 'at_least';
    bank: string;
    librefolio: string;
    difference: string;
}

export interface GapFixNote {
    code: string;
    severity: string;
    message: string;
    context: Loose | null;
}

/** Where a checkpoint's difference comes from. */
export interface GapFixExplanation {
    absorbedCount: number;
    absorbedMissingCount: number;
    absorbedMissingCash: GapFixAmount[];
    openingCash: GapFixAmount[];
    unexplainedCash: GapFixAmount[];
    notes: GapFixNote[];
}

/** One correction, as the backend proposed it, with the fields left for the user. */
export interface GapFixProposal {
    key: string;
    tx: Loose;
    todos: ImportTodo[];
    /** The per-unit cost must be entered in the editor before saving. */
    needsCost: boolean;
}

export interface GapFixCheckpoint {
    key: string;
    asOf: string;
    kind: string;
    cash: GapFixCashRow[];
    positions: GapFixPositionRow[];
    explanation: GapFixExplanation;
    proposals: GapFixProposal[];
}

export interface GapFixVerification {
    key: string;
    asOf: string;
    ok: boolean;
    cash: GapFixCashRow[];
}

/** One request's results: one broker and one plugin. */
export interface GapFixGroup {
    key: string;
    brokerId: number;
    pluginCode: string;
    error: string | null;
    checkpoints: GapFixCheckpoint[];
    verifications: GapFixVerification[];
}

/** What the step renders. Keys: group `<broker>:<plugin>`, `<group>:cp:<i>`, `<checkpoint>:p:<j>`, `<group>:v:<i>`. */
export interface GapFixView {
    groups: GapFixGroup[];
}

function isRecord(value: unknown): value is Loose {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function records(value: unknown): Loose[] {
    return Array.isArray(value) ? value.filter(isRecord) : [];
}

function text(value: unknown): string {
    return value === null || value === undefined ? '' : String(value);
}

function count(value: unknown): number {
    return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

/** The parse results that carry truth points, in input order. */
export function truthSourcesOf(parseResults: ReadonlyArray<TruthSourceInput>): TruthSource[] {
    const sources: TruthSource[] = [];
    for (const result of parseResults) {
        if (result.status !== 'done' || !isRecord(result.response)) continue;
        const response = result.response;
        const checkpoints = records(response.checkpoints);
        const verifications = records(response.verifications);
        if (checkpoints.length === 0 && verifications.length === 0) continue;
        // The truth points belong to the plugin that produced them, not to the wizard's pick.
        const pluginCode = typeof response.plugin_code === 'string' ? response.plugin_code : (result.pluginUsed ?? '');
        sources.push({fileId: result.fileId, brokerId: result.brokerId, pluginCode, checkpoints, verifications});
    }
    return sources;
}

/**
 * The asset a truth position points at: plugin fake id → the global fake id of its file → the
 * asset it was unified into → the real asset the user resolved, when there is one.
 *
 * A plugin fake id that none of its file's rows used is returned unchanged: plugin and global
 * fakes share one range, so looking it up among the globals would bind the position to another
 * instrument. Unchanged, it stays fake, and the backend leaves it out with an `unresolved_asset` note.
 */
export function resolveTruthAssetId(fileId: string, assetId: number, ctx: TruthAssetContext): number {
    if (!isFakeAssetId(assetId)) return assetId;
    const global = ctx.fakeRemapByFile.get(fileId)?.get(assetId);
    if (global === undefined) return assetId;
    const survivor = ctx.survivorOf.get(global) ?? global;
    const resolved = ctx.resolutions.find((resolution) => resolution.fakeAssetId === survivor)?.resolvedAssetId;
    return typeof resolved === 'number' ? resolved : survivor;
}

function withResolvedPositions(checkpoint: TruthPoint, fileId: string, resolveAsset: (fileId: string, assetId: number) => number): TruthPoint {
    if (!Array.isArray(checkpoint.positions)) return {...checkpoint};
    return {
        ...checkpoint,
        positions: checkpoint.positions.map((position: unknown) => (isRecord(position) && typeof position.asset_id === 'number' ? {...position, asset_id: resolveAsset(fileId, position.asset_id)} : position)),
    };
}

/**
 * One request per broker and plugin, in the order of their first source. Two sources of one broker
 * and plugin (two sets imported together, scenario 8) are one request with the union of their truth
 * points. The selection and the editor's unsaved rows are those of the request's broker; the
 * editor's deletions go to every request whole.
 */
export function buildGapFixRequests<T extends {broker_id?: unknown}>(sources: ReadonlyArray<TruthSource>, selection: ReadonlyArray<T>, pendingCreates: ReadonlyArray<T>, pendingDeleteTxIds: ReadonlyArray<number>, resolveAsset: (fileId: string, assetId: number) => number): GapFixRequestBody<T>[] {
    const groups = new Map<string, {brokerId: number; pluginCode: string; checkpoints: TruthPoint[]; verifications: TruthPoint[]}>();
    for (const source of sources) {
        if (source.checkpoints.length === 0 && source.verifications.length === 0) continue;
        const key = `${source.brokerId}:${source.pluginCode}`;
        let group = groups.get(key);
        if (!group) {
            group = {brokerId: source.brokerId, pluginCode: source.pluginCode, checkpoints: [], verifications: []};
            groups.set(key, group);
        }
        for (const checkpoint of source.checkpoints) group.checkpoints.push(withResolvedPositions(checkpoint, source.fileId, resolveAsset));
        group.verifications.push(...source.verifications);
    }
    return [...groups.values()].map((group) => ({
        broker_id: group.brokerId,
        plugin_code: group.pluginCode,
        checkpoints: group.checkpoints,
        verifications: group.verifications,
        selection: selection.filter((tx) => tx.broker_id === group.brokerId),
        pending_creates: pendingCreates.filter((tx) => tx.broker_id === group.brokerId),
        pending_delete_tx_ids: [...pendingDeleteTxIds],
    }));
}

function amounts(value: unknown): GapFixAmount[] {
    return records(value).map((item) => ({currency: text(item.currency), amount: text(item.amount)}));
}

function cashRows(value: unknown): GapFixCashRow[] {
    return records(value).map((row) => ({currency: text(row.currency), bank: text(row.bank), librefolio: text(row.librefolio), difference: text(row.difference)}));
}

function toImportTodo(todo: Loose, localizeTodo: (reasonCode: string, message: string) => string): ImportTodo {
    const reasonCode = text(todo.reason_code);
    return {
        field: text(todo.field),
        severity: todo.severity === 'blocker' ? 'blocker' : 'warning',
        reasonCode,
        message: localizeTodo(reasonCode, text(todo.message)),
        evidence: Array.isArray(todo.evidence) ? (todo.evidence as BrimEvidence[]) : [],
        context: isRecord(todo.context) ? todo.context : undefined,
    };
}

function checkpointView(checkpoint: Loose, key: string, localizeTodo: (reasonCode: string, message: string) => string): GapFixCheckpoint {
    // A todo's tx_index counts inside its own checkpoint's proposals.
    const todosByProposal = new Map<number, ImportTodo[]>();
    for (const todo of records(checkpoint.todos)) {
        const index = typeof todo.tx_index === 'number' ? todo.tx_index : -1;
        const list = todosByProposal.get(index) ?? [];
        list.push(toImportTodo(todo, localizeTodo));
        todosByProposal.set(index, list);
    }
    const explanation = isRecord(checkpoint.explanation) ? checkpoint.explanation : {};
    return {
        key,
        asOf: text(checkpoint.as_of).slice(0, 10),
        kind: text(checkpoint.kind),
        cash: cashRows(checkpoint.cash),
        positions: records(checkpoint.positions).map((position) => ({
            assetId: Number(position.asset_id),
            exactness: position.exactness === 'at_least' ? 'at_least' : 'exact',
            bank: text(position.bank),
            librefolio: text(position.librefolio),
            difference: text(position.difference),
        })),
        explanation: {
            absorbedCount: count(explanation.absorbed_count),
            absorbedMissingCount: count(explanation.absorbed_missing_count),
            absorbedMissingCash: amounts(explanation.absorbed_missing_cash),
            openingCash: amounts(explanation.opening_cash),
            unexplainedCash: amounts(explanation.unexplained_cash),
            notes: records(explanation.notes).map((note) => ({code: text(note.code), severity: text(note.severity), message: text(note.message), context: isRecord(note.context) ? note.context : null})),
        },
        proposals: records(checkpoint.proposals).map((tx, index) => {
            const todos = todosByProposal.get(index) ?? [];
            return {key: `${key}:p:${index}`, tx, todos, needsCost: todos.some((todo) => todo.severity === 'blocker' && todo.field === 'cost_basis_override')};
        }),
    };
}

/** The view of the step: one group per request, in order. The todo messages go through `localizeTodo`. */
export function buildGapFixView(outcomes: ReadonlyArray<GapFixOutcome>, localizeTodo: (reasonCode: string, message: string) => string): GapFixView {
    return {
        groups: outcomes.map((outcome) => {
            const key = `${outcome.brokerId}:${outcome.pluginCode}`;
            const base = {key, brokerId: outcome.brokerId, pluginCode: outcome.pluginCode};
            if (outcome.error !== undefined && outcome.error !== null) return {...base, error: outcome.error, checkpoints: [], verifications: []};
            const response = isRecord(outcome.response) ? outcome.response : {};
            return {
                ...base,
                error: null,
                checkpoints: records(response.checkpoints).map((checkpoint, index) => checkpointView(checkpoint, `${key}:cp:${index}`, localizeTodo)),
                verifications: records(response.verifications).map((verification, index) => ({key: `${key}:v:${index}`, asOf: text(verification.as_of).slice(0, 10), ok: verification.ok === true, cash: cashRows(verification.cash)})),
            };
        }),
    };
}

function proposalsOf(view: GapFixView): GapFixProposal[] {
    return view.groups.flatMap((group) => group.checkpoints.flatMap((checkpoint) => checkpoint.proposals));
}

/** The step opens only for a correction to propose, a verification that does not hold, or a failed request. Notes alone do not open it. */
export function gapFixHasSomethingToShow(view: GapFixView): boolean {
    return view.groups.some((group) => group.error !== null || group.checkpoints.some((checkpoint) => checkpoint.proposals.length > 0) || group.verifications.some((verification) => !verification.ok));
}

/** Every correction, selected by default (D-S14). */
export function defaultGapFixSelection(view: GapFixView): string[] {
    return proposalsOf(view).map((proposal) => proposal.key);
}

/** How many corrections the view proposes. */
export function gapFixProposalCount(view: GapFixView): number {
    return proposalsOf(view).length;
}

/** How many of the view's corrections are selected; keys of anything else do not count. */
export function gapFixSelectedCount(view: GapFixView, selected: ReadonlySet<string>): number {
    return proposalsOf(view).filter((proposal) => selected.has(proposal.key)).length;
}

/** The selected corrections with their todos, by group, then checkpoint, then proposal: what the editor receives. */
export function selectedGapFixCreates(view: GapFixView, selected: ReadonlySet<string>): Array<{tx: Loose; todos: ImportTodo[]}> {
    return proposalsOf(view)
        .filter((proposal) => selected.has(proposal.key))
        .map((proposal) => ({tx: {...proposal.tx}, todos: proposal.todos.map((todo) => ({...todo}))}));
}
