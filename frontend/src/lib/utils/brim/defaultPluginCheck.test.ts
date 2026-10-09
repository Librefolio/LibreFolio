/**
 * defaultPluginCheck — the two pure halves of the import wizard's "this file may belong to another
 * broker" prompt (ImportBrokerMismatchModal, raised right after the step-1 upload).
 *
 * `findDefaultPluginMismatch` decides whether a file is questioned at all and where it could go:
 * only a broker that sets a default import plugin is ever questioned, only when that plugin is not
 * among the plugins the upload says read the file (`compatible_plugins`, best match first), and
 * never when a report-set plugin reads it — such a file is read through its set, whatever the
 * broker's default (decision A18). The places it could go are the *other* brokers whose default
 * plugin reads it: best plugin first, brokers of the same plugin in the order of the list, and the
 * brokers of a fallback plugin (the generic CSV) only when no broker of a specific one is there.
 *
 * `resolveParseRefusalMessage` turns the default plugin's refusal
 * (`GET /brokers/import/files/{file_id}/plugin-check`) into the sentence the prompt shows: the
 * translation of `importWizard.parseRefusal.<code>` with the refusal's context, or else the
 * plugin's own English sentence — written lowercase and without a final period — made a sentence.
 *
 * The data mirrors the Scalable Capital pair that motivated the check: `broker_scalable` refuses the
 * overnight account's file, which `broker_scalable_deposit` and the generic CSV read. The browser
 * side is `e2e/transactions/tx-import-broker-mismatch.spec.ts`.
 */

import {describe, expect, it, vi} from 'vitest';
import {findDefaultPluginMismatch, resolveParseRefusalMessage, type MismatchBroker, type MismatchOptions, type ParseRefusal} from './defaultPluginCheck';

const SCALABLE = 'broker_scalable';
const DEPOSIT = 'broker_scalable_deposit';
const GENERIC = 'broker_generic_csv';
const DEGIRO = 'broker_degiro';
const DANSKE = 'broker_danske_bank';
/** A made-up specific plugin, ranked between the overnight account's and the generic CSV. */
const OTHER = 'broker_other_reader';

/** What the upload answers for the overnight account's file: the plugins that read it, best first. */
const DEPOSIT_FILE_READERS: readonly string[] = [DEPOSIT, GENERIC];

/** The options the wizard builds from today's plugin list: Danske Bank is the one report-set plugin, the generic CSV (priority 0) the one fallback. */
const WIZARD_OPTIONS: MismatchOptions = {reportSetPlugins: new Set([DANSKE]), fallbackPlugins: new Set([GENERIC])};

/** A broker of the list the wizard passes (`getEditableBrokers()`); `undefined` leaves the field out. */
function broker(id: number, defaultPlugin?: string | null, name = `Broker ${id}`): MismatchBroker {
    return defaultPlugin === undefined ? {id, name} : {id, name, default_import_plugin: defaultPlugin};
}

/** Deep-freezes the inputs, so a function that writes to what it was given throws (ES modules are strict). */
function frozen<T extends object>(items: T[]): readonly T[] {
    return Object.freeze(items.map((item) => Object.freeze(item)));
}

describe('findDefaultPluginMismatch — no question to ask', () => {
    it.each([
        ['left out', undefined],
        ['null', null],
        ['empty', ''],
    ])('a broker whose default plugin is %s is never questioned, whatever reads the file', (_label, defaultPlugin) => {
        const brokers = [broker(1, defaultPlugin), broker(2, DEPOSIT)];
        expect(findDefaultPluginMismatch(DEPOSIT_FILE_READERS, 1, brokers)).toBeNull();
        expect(findDefaultPluginMismatch([], 1, brokers), 'not even when no plugin reads the file').toBeNull();
        expect(findDefaultPluginMismatch(null, 1, brokers)).toBeNull();
        expect(findDefaultPluginMismatch(undefined, 1, brokers)).toBeNull();
    });

    it('a broker missing from the list has no known default plugin, so it is never questioned', () => {
        expect(findDefaultPluginMismatch(DEPOSIT_FILE_READERS, 99, [broker(1, SCALABLE), broker(2, DEPOSIT)])).toBeNull();
        expect(findDefaultPluginMismatch(DEPOSIT_FILE_READERS, 1, [])).toBeNull();
    });

    it('a file its broker’s default plugin reads raises no question, even when other brokers’ defaults read it too', () => {
        const brokers = [broker(1, GENERIC), broker(2, DEPOSIT), broker(3, SCALABLE)];
        expect(findDefaultPluginMismatch(DEPOSIT_FILE_READERS, 2, brokers), 'the best reader').toBeNull();
        expect(findDefaultPluginMismatch(DEPOSIT_FILE_READERS, 1, brokers), 'any reader, not only the best one').toBeNull();
    });
});

describe('findDefaultPluginMismatch — a file its broker’s default plugin cannot read', () => {
    it('names the broker, its default plugin, the readers and the one broker whose default plugin reads the file', () => {
        const brokers = frozen([broker(1, SCALABLE, 'Scalable broker'), broker(2, DEPOSIT, 'Scalable overnight')]);
        const readers = Object.freeze([...DEPOSIT_FILE_READERS]);
        expect(findDefaultPluginMismatch(readers, 1, brokers)).toEqual({
            brokerId: 1,
            defaultPlugin: SCALABLE,
            readers: [DEPOSIT, GENERIC],
            targets: [{id: 2, name: 'Scalable overnight', pluginCode: DEPOSIT}],
        });
    });

    it('offers the targets best plugin first — the order of the readers — and the brokers of one plugin in the order of the list', () => {
        // The readers come best match first; the list is in no particular order, and its ids are not sorted either.
        const readers = [DEPOSIT, OTHER, GENERIC];
        const brokers = [broker(6, GENERIC, 'Generic F'), broker(9, OTHER, 'Other'), broker(3, SCALABLE, 'Scalable broker'), broker(5, GENERIC, 'Generic E'), broker(4, null, 'No default'), broker(8, DEPOSIT, 'Overnight H'), broker(7, DEGIRO, 'DEGIRO'), broker(2, DEPOSIT, 'Overnight B')];
        expect(findDefaultPluginMismatch(readers, 3, brokers)?.targets).toEqual([
            {id: 8, name: 'Overnight H', pluginCode: DEPOSIT},
            {id: 2, name: 'Overnight B', pluginCode: DEPOSIT},
            {id: 9, name: 'Other', pluginCode: OTHER},
            {id: 6, name: 'Generic F', pluginCode: GENERIC},
            {id: 5, name: 'Generic E', pluginCode: GENERIC},
        ]);
    });

    it('has no target when no other broker’s default plugin reads the file — without or with another default', () => {
        const brokers = [broker(1, SCALABLE), broker(2, DEGIRO), broker(3), broker(4, null), broker(5, ''), broker(6, SCALABLE)];
        expect(findDefaultPluginMismatch(DEPOSIT_FILE_READERS, 1, brokers)).toEqual({brokerId: 1, defaultPlugin: SCALABLE, readers: [DEPOSIT, GENERIC], targets: []});
    });

    it('never offers a broker without a default plugin, even against a reader list holding an empty code', () => {
        const brokers = [broker(1, SCALABLE), broker(2, ''), broker(3, DEPOSIT)];
        expect(findDefaultPluginMismatch(['', DEPOSIT], 1, brokers)?.targets).toEqual([{id: 3, name: 'Broker 3', pluginCode: DEPOSIT}]);
    });

    it('never offers the broker the file was uploaded to, even through an entry whose default plugin reads it', () => {
        // In a well-formed list the broker's default cannot both read the file and refuse it: only a
        // list naming the broker twice gets here. Its first entry decides the question; no entry of
        // the broker is ever a place to move the file to.
        const brokers = [broker(1, SCALABLE, 'Scalable broker'), broker(2, DEPOSIT, 'Overnight'), broker(1, DEPOSIT, 'Scalable broker, a later entry')];
        expect(findDefaultPluginMismatch(DEPOSIT_FILE_READERS, 1, brokers)).toEqual({
            brokerId: 1,
            defaultPlugin: SCALABLE,
            readers: [DEPOSIT, GENERIC],
            targets: [{id: 2, name: 'Overnight', pluginCode: DEPOSIT}],
        });
    });

    it.each([
        ['null', null],
        ['undefined', undefined],
        ['empty', [] as string[]],
    ])('a %s compatible list means no plugin reads the file: a mismatch with no reader and no target', (_label, compatible) => {
        // Brokers whose default would read anything are still no target: there is nothing they read.
        const brokers = [broker(1, SCALABLE), broker(2, DEPOSIT), broker(3, GENERIC)];
        expect(findDefaultPluginMismatch(compatible, 1, brokers)).toEqual({brokerId: 1, defaultPlugin: SCALABLE, readers: [], targets: []});
    });

    it('returns the readers as a copy, in their order: changing it leaves the upload’s answer alone', () => {
        const compatible = [DEPOSIT, GENERIC];
        const mismatch = findDefaultPluginMismatch(compatible, 1, [broker(1, SCALABLE)]);
        expect(mismatch?.readers).toEqual([DEPOSIT, GENERIC]);
        expect(mismatch?.readers).not.toBe(compatible);
        mismatch?.readers.push('broker_other');
        expect(compatible).toEqual([DEPOSIT, GENERIC]);
    });
});

describe('findDefaultPluginMismatch — a file a report-set plugin reads (decision A18)', () => {
    it('is never questioned, even on a broker whose default plugin does not read it', () => {
        // The bank's custody export on a broker that imports with the generic CSV: only the set plugin reads it.
        const brokers = [broker(1, GENERIC), broker(2, DANSKE)];
        expect(findDefaultPluginMismatch([DANSKE], 1, brokers, {reportSetPlugins: new Set([DANSKE])})).toBeNull();
        expect(findDefaultPluginMismatch([DANSKE], 1, brokers, WIZARD_OPTIONS), 'with the options the wizard builds').toBeNull();
        expect(findDefaultPluginMismatch([DANSKE], 1, brokers), 'the exemption is the option’s: without it the same file is questioned').toEqual({
            brokerId: 1,
            defaultPlugin: GENERIC,
            readers: [DANSKE],
            targets: [{id: 2, name: 'Broker 2', pluginCode: DANSKE}],
        });
    });

    it('is exempt whichever reader the set plugin is, not only the best one', () => {
        expect(findDefaultPluginMismatch([OTHER, DANSKE, GENERIC], 1, [broker(1, SCALABLE), broker(2, OTHER)], {reportSetPlugins: new Set([DANSKE])})).toBeNull();
    });

    it('exempts nothing when no reader is a report-set plugin', () => {
        const brokers = [broker(1, SCALABLE), broker(2, DEPOSIT)];
        const expected = {brokerId: 1, defaultPlugin: SCALABLE, readers: [DEPOSIT, GENERIC], targets: [{id: 2, name: 'Broker 2', pluginCode: DEPOSIT}]};
        expect(findDefaultPluginMismatch(DEPOSIT_FILE_READERS, 1, brokers, {reportSetPlugins: new Set([DANSKE])})).toEqual(expected);
        expect(findDefaultPluginMismatch(DEPOSIT_FILE_READERS, 1, brokers, {reportSetPlugins: new Set<string>()}), 'an empty set exempts nothing').toEqual(expected);
    });
});

describe('findDefaultPluginMismatch — brokers of a fallback plugin (the generic CSV)', () => {
    const fallback = {fallbackPlugins: new Set([GENERIC])};

    it('are dropped when a broker of a specific plugin that reads the file is there', () => {
        // The overnight account's file on the broker account, next to two brokers that import with the generic CSV.
        const brokers = [broker(5, GENERIC, 'Generic E'), broker(1, SCALABLE, 'Scalable broker'), broker(2, DEPOSIT, 'Overnight'), broker(6, GENERIC, 'Generic F')];
        const expected = {brokerId: 1, defaultPlugin: SCALABLE, readers: [DEPOSIT, GENERIC], targets: [{id: 2, name: 'Overnight', pluginCode: DEPOSIT}]};
        expect(findDefaultPluginMismatch(DEPOSIT_FILE_READERS, 1, brokers, fallback)).toEqual(expected);
        expect(findDefaultPluginMismatch(DEPOSIT_FILE_READERS, 1, brokers, WIZARD_OPTIONS), 'with the options the wizard builds').toEqual(expected);
        expect(
            findDefaultPluginMismatch(DEPOSIT_FILE_READERS, 1, brokers)?.targets.map((target) => target.id),
            'the drop is the option’s: without it they are offered after the specific one',
        ).toEqual([2, 5, 6]);
    });

    it('are dropped for being a fallback, not for their rank: a fallback ranked first among the readers is dropped too', () => {
        const brokers = [broker(1, SCALABLE), broker(5, GENERIC), broker(2, DEPOSIT)];
        expect(findDefaultPluginMismatch([GENERIC, DEPOSIT], 1, brokers, fallback)?.targets).toEqual([{id: 2, name: 'Broker 2', pluginCode: DEPOSIT}]);
    });

    it('are kept, in the order of the list, when they are the only brokers whose default plugin reads the file', () => {
        const brokers = [broker(6, GENERIC, 'Generic F'), broker(1, SCALABLE, 'Scalable broker'), broker(7, DEGIRO), broker(5, GENERIC, 'Generic E')];
        expect(findDefaultPluginMismatch(DEPOSIT_FILE_READERS, 1, brokers, fallback)?.targets).toEqual([
            {id: 6, name: 'Generic F', pluginCode: GENERIC},
            {id: 5, name: 'Generic E', pluginCode: GENERIC},
        ]);
    });

    it('apply to the targets only: a broker whose own default is a fallback that does not read the file is still questioned', () => {
        // An XLSX the generic CSV cannot read, on a broker that imports with it, read by a specific plugin.
        expect(findDefaultPluginMismatch([OTHER], 1, [broker(1, GENERIC), broker(2, OTHER)], fallback)).toEqual({
            brokerId: 1,
            defaultPlugin: GENERIC,
            readers: [OTHER],
            targets: [{id: 2, name: 'Broker 2', pluginCode: OTHER}],
        });
    });
});

/** Fake `$t`: a known key interpolates `{token}`s from its values; an unknown key comes back as itself, as svelte-i18n answers a missing key. */
function makeT(known: Record<string, string> = {}) {
    return vi.fn((key: string, opts?: {values?: Record<string, unknown>}): string => {
        const template = known[key];
        if (template === undefined) return key;
        const values = opts?.values ?? {};
        return template.replace(/\{(\w+)\}/g, (token, name: string) => (values[name] !== undefined ? String(values[name]) : token));
    });
}

const DEPOSIT_FILE_KEY = 'importWizard.parseRefusal.scalable_deposit_file';
const DEPOSIT_FILE_TEMPLATE = 'This is the export of the Scalable overnight account: read it with the {plugin_name} plugin.';
const DEPOSIT_PLUGIN_CONTEXT = {plugin_code: DEPOSIT, plugin_name: 'Scalable Capital overnight account'};
/** What `broker_scalable` answers about the overnight account's file (backend `_scalable.refusal`). */
const DEPOSIT_FILE_REFUSAL: ParseRefusal = {
    code: 'scalable_deposit_file',
    message: 'this is the export of the Scalable overnight account: read it with the Scalable Capital overnight account plugin',
    context: DEPOSIT_PLUGIN_CONTEXT,
};

describe('resolveParseRefusalMessage — a refusal with a code', () => {
    it('is translated as importWizard.parseRefusal.<code>, its context as the values', () => {
        const t = makeT({[DEPOSIT_FILE_KEY]: DEPOSIT_FILE_TEMPLATE});
        expect(resolveParseRefusalMessage(DEPOSIT_FILE_REFUSAL, t)).toBe('This is the export of the Scalable overnight account: read it with the Scalable Capital overnight account plugin.');
        expect(t).toHaveBeenCalledTimes(1);
        expect(t).toHaveBeenCalledWith(DEPOSIT_FILE_KEY, {values: DEPOSIT_PLUGIN_CONTEXT});
    });

    it('gets the translation as written: no capital letter, no period added', () => {
        const t = makeT({'importWizard.parseRefusal.scalable_mixed_file': 'two accounts in one file, export them apart'});
        expect(resolveParseRefusalMessage({code: 'scalable_mixed_file', message: 'the file mixes the broker and the overnight account'}, t)).toBe('two accounts in one file, export them apart');
    });

    it.each([
        ['null', null],
        ['left out', undefined],
    ])('is translated with no values when its context is %s', (_label, context) => {
        const t = makeT({'importWizard.parseRefusal.scalable_mixed_file': 'The file mixes the two accounts.'});
        const refusal: ParseRefusal = context === undefined ? {code: 'scalable_mixed_file', message: 'fallback'} : {code: 'scalable_mixed_file', message: 'fallback', context};
        expect(resolveParseRefusalMessage(refusal, t)).toBe('The file mixes the two accounts.');
        expect(t).toHaveBeenCalledWith('importWizard.parseRefusal.scalable_mixed_file', {values: {}});
    });

    it('without a translation falls back to the plugin’s message, made a sentence', () => {
        const t = makeT();
        expect(resolveParseRefusalMessage(DEPOSIT_FILE_REFUSAL, t)).toBe('This is the export of the Scalable overnight account: read it with the Scalable Capital overnight account plugin.');
        expect(t, 'the code was looked up first').toHaveBeenCalledWith(DEPOSIT_FILE_KEY, {values: DEPOSIT_PLUGIN_CONTEXT});
    });
});

describe('resolveParseRefusalMessage — the plugin’s own sentence', () => {
    it.each([
        ['null', null],
        ['left out', undefined],
        ['empty', ''],
    ])('a refusal whose code is %s is the message made a sentence, and nothing is translated', (_label, code) => {
        const t = makeT({'importWizard.parseRefusal.': 'never shown', 'importWizard.parseRefusal.null': 'never shown', 'importWizard.parseRefusal.undefined': 'never shown'});
        const refusal: ParseRefusal = code === undefined ? {message: 'the Generic CSV reads only .csv files'} : {code, message: 'the Generic CSV reads only .csv files'};
        expect(resolveParseRefusalMessage(refusal, t)).toBe('The Generic CSV reads only .csv files.');
        expect(t).not.toHaveBeenCalled();
    });

    it.each([
        ['a period', 'the file has no header row.', 'The file has no header row.'],
        ['an exclamation mark', 'the file has no header row!', 'The file has no header row!'],
        ['a question mark', 'is this the overnight account?', 'Is this the overnight account?'],
    ])('a message that already ends with %s gets no second mark', (_label, message, expected) => {
        expect(resolveParseRefusalMessage({message}, makeT())).toBe(expected);
    });

    it('a message already capitalised only gets its period', () => {
        expect(resolveParseRefusalMessage({message: 'Required column date not found in the CSV header'}, makeT())).toBe('Required column date not found in the CSV header.');
    });

    it('a message is trimmed before it is made a sentence', () => {
        expect(resolveParseRefusalMessage({message: '  the file could not be read \n'}, makeT())).toBe('The file could not be read.');
    });

    it('a message that does not start with a letter keeps its first character', () => {
        expect(resolveParseRefusalMessage({message: '«x» is not a Scalable export'}, makeT())).toBe('«x» is not a Scalable export.');
        expect(resolveParseRefusalMessage({message: '2 columns are missing'}, makeT())).toBe('2 columns are missing.');
    });

    it.each([
        ['empty', ''],
        ['blank', '  \t '],
    ])('an %s message stays empty — no lone period, with or without an untranslated code', (_label, message) => {
        expect(resolveParseRefusalMessage({message}, makeT())).toBe('');
        expect(resolveParseRefusalMessage({code: 'scalable_unknown', message}, makeT())).toBe('');
    });
});
