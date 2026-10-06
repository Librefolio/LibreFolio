<!--
  R9.4: one card per pair the scenario needs, nothing else. «Auto» is the rate LibreFolio stores,
  read when the step opens and again just before the calculation; «Manual» is the user's rate,
  used as typed. The step leaves the wizard when no pair is needed (`draft.visibleSteps`).
-->
<script lang="ts">
    import {onDestroy, onMount} from 'svelte';
    import {Download, ExternalLink, LoaderCircle, Plus} from 'lucide-svelte';
    import {t, locale} from '$lib/i18n';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import FxSyncModal from '$lib/components/fx/FxSyncModal.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import type {FxPairCreatedDetail} from '$lib/services/fxCreationSync';
    import {createPairSlug} from '$lib/stores/fxStoreRegistry';
    import {fxRoutesVersion} from '$lib/stores/reference/fxRoutesStore';
    import {addDays} from '$lib/utils/dateOnly';
    import {setRateManual} from '../copies';
    import {defaultAsOf} from '../defaults';
    import type {DraftFx, PlannerDraft} from '../draft.svelte';
    import {formatPlannerDate, formatPlannerFxRate} from '../format';
    import {FxRateReader} from '../fxRead.svelte';
    import {loadPairSetups, pairSetup, type PairSetup} from '../fxSetup';
    import {BADGE, BUTTON_LINK, BUTTON_SECONDARY, CARD, HINT, INPUT, INPUT_ADORNMENT, LABEL_ROW, NOTICE} from '../ui';
    import AutoManualToggle from '../shared/AutoManualToggle.svelte';
    import CurrencyCode from '../shared/CurrencyCode.svelte';
    import HelpTip from '../shared/HelpTip.svelte';

    const KEY = 'tools.pacAllocator.planner.fx';

    type Use = 'valuation' | 'conversion';
    type ReadState = 'reading' | 'not-stored' | 'ownerless' | 'idle';

    interface Props {
        draft: PlannerDraft;
        accountGeneration: number;
    }

    let {draft, accountGeneration}: Props = $props();

    const ids = $props.id();
    const reader = new FxRateReader();
    onDestroy(() => reader.stop());

    // Pairs never read in this session (a restored draft, a step left mid-read) are read once here.
    onMount(() => {
        const pending = reader.pending(draft);
        if (pending.length > 0) void reader.read(draft, pending, accountGeneration);
    });

    function sides(pair: string): [string, string] {
        const [base, quote] = pair.split('/');
        return [base ?? '', quote ?? ''];
    }

    function uses(pair: string): Use[] {
        const purpose = draft.fxPurpose(pair);
        return purpose === 'both' ? ['valuation', 'conversion'] : [purpose];
    }

    function readState(pair: string): ReadState {
        if (reader.isReading(pair)) return 'reading';
        if (reader.ownerless(draft, pair)) return 'ownerless';
        if (reader.notStored(draft, pair)) return 'not-stored';
        return 'idle';
    }

    function pairLabel(pair: string): string {
        return $t(`${KEY}.pairMode`, {default: 'Rate {pair}', values: {pair}});
    }

    function useText(use: Use): string {
        return use === 'valuation' ? $t(`${KEY}.purpose.valuation`, {default: 'Valuation'}) : $t(`${KEY}.purpose.conversion`, {default: 'Conversion'});
    }

    function useHelp(use: Use): string {
        if (use === 'valuation') {
            return $t(`${KEY}.purpose.valuationHelp`, {
                default: 'Expresses in {currency} the cash, prices and contributions in the other currency, so that weights and totals can be compared. The official rate is used, without spread.',
                values: {currency: draft.data.valuationCurrency},
            });
        }
        return $t(`${KEY}.purpose.conversionHelp`, {
            default: 'A Broker can pay for an Asset priced in one of these currencies with cash in the other: the calculation may convert at this rate, with the conversion spread.',
        });
    }

    function rateHelp(fx: DraftFx): string {
        return $t(`${KEY}.rateHelp`, {
            default: 'Rate stored in LibreFolio, dated {date}{hasSource, select, yes { (source: {source})} other {}}. It is read again just before the calculation.',
            values: {date: formatPlannerDate(fx.referenceDate, $locale), hasSource: fx.source ? 'yes' : 'no', source: fx.source ?? ''},
        });
    }

    function manualHelp(fx: DraftFx | undefined): string {
        const copied = fx?.copiedRate ?? null;
        return $t(`${KEY}.manualHelp`, {
            default: 'Your rate: the calculation uses it as typed and never reads it again. {hasCopy, select, yes {LibreFolio has {rate}, dated {date}: «Auto» brings it back.} other {In «Auto» the calculation uses the rate stored in LibreFolio, when there is one.}}',
            values: {hasCopy: copied ? 'yes' : 'no', rate: formatPlannerFxRate(copied), date: formatPlannerDate(fx?.referenceDate, $locale)},
        });
    }

    function switchMode(pair: string, manual: boolean): void {
        setRateManual(draft, pair, manual);
        // Back to Auto with nothing stored yet: try the read again now, not only at «Calcola».
        if (!manual && (draft.fx(pair)?.rate.trim() ?? '') === '') void reader.read(draft, [pair], accountGeneration);
    }

    function setRate(pair: string, value: string): void {
        draft.ensureFx(pair).rate = value;
    }

    // -- R13.2: a pair with no stored rate is added, or its rates downloaded, here --------------

    /**
     * Days of rates «Download the rates» asks for, ending today: enough to cover a long weekend
     * or a holiday of the source. The dialog shows the dates. «Add the pair» downloads the
     * pair's whole history instead (`fxCreationSync`).
     */
    const SYNC_WINDOW_DAYS = 7;

    interface PairAction {
        pair: string;
        base: string;
        quote: string;
        start: string;
        end: string;
    }

    /** How LibreFolio is set up for each pair: read only while a pair has no stored rate. */
    let setups = $state<ReadonlyMap<string, PairSetup> | null>(null);
    let setupSequence = 0;
    let adding = $state<PairAction | null>(null);
    let addOpen = $state(false);
    let syncing = $state<PairAction | null>(null);
    let syncOpen = $state(false);

    const anyNotStored = $derived(draft.requiredPairs.some((pair) => reader.notStored(draft, pair)));

    // Read again when a pair is created, here or elsewhere (`invalidateFxRoutes` bumps the version).
    // A failed read offers «Add the pair»: the dialog itself says when the pair already exists.
    $effect(() => {
        void $fxRoutesVersion;
        if (!anyNotStored) return;
        const sequence = ++setupSequence;
        loadPairSetups().then(
            (loaded) => {
                if (sequence === setupSequence) setups = loaded;
            },
            () => {
                if (sequence === setupSequence) setups = new Map();
            },
        );
    });

    function pairAction(pair: string): PairAction {
        const [base, quote] = sides(pair);
        const end = defaultAsOf();
        return {pair, base, quote, start: addDays(end, -SYNC_WINDOW_DAYS), end};
    }

    function openAdd(pair: string): void {
        adding = pairAction(pair);
        addOpen = true;
    }

    function openSync(pair: string): void {
        syncing = pairAction(pair);
        syncOpen = true;
    }

    /** The step reads the pair again once its rates are in LibreFolio. */
    function readAgain(pair: string): void {
        void reader.read(draft, [pair], accountGeneration);
    }

    // The dialogs keep these callbacks past their own closing (the download ends later), so
    // each one holds its pair rather than reading `adding`/`syncing` when it runs.
    function afterCreation(pair: string): (detail: FxPairCreatedDetail) => void {
        return (detail) => {
            // MANUAL as the only provider: nothing is downloaded, so read now.
            if (!detail.autoSyncStarted) readAgain(pair);
        };
    }

    function afterDownload(pair: string): () => void {
        return () => readAgain(pair);
    }

    function setupText(setup: PairSetup | null): string {
        if (setup === 'absent') return $t(`${KEY}.pairAbsent`, {default: 'LibreFolio does not track this pair yet: add it here, or switch to «Manual» and type the rate.'});
        if (setup === 'provider') return $t(`${KEY}.pairNoRates`, {default: 'LibreFolio tracks this pair but has no rate up to today: download the rates here, or switch to «Manual» and type the rate.'});
        if (setup === 'manual') return $t(`${KEY}.pairManualOnly`, {default: 'LibreFolio tracks this pair with manual rates only, and has none up to today: add one on the pair’s page, or switch to «Manual» and type it here.'});
        return $t(`${KEY}.pairMissing`, {default: 'LibreFolio has no stored rate for this pair.'});
    }

    function setupHelp(setup: PairSetup): string {
        if (setup === 'absent') {
            return $t(`${KEY}.pairAbsentHelp`, {
                default:
                    '«Add the pair» opens the window of the FX page, with the two currencies already chosen. With a provider, LibreFolio then downloads the pair’s whole rate history and this step reads the latest; with «Manual» as the only provider nothing is downloaded, and the rates are typed on the pair’s page.',
            });
        }
        if (setup === 'provider') {
            return $t(`${KEY}.pairNoRatesHelp`, {
                default: '«Download the rates» opens the download window of the FX page for this pair, set to the last {days} days; when the download ends, this step reads the latest rate. No provider is called until you start the download.',
                values: {days: SYNC_WINDOW_DAYS},
            });
        }
        return $t(`${KEY}.pairManualOnlyHelp`, {
            default: 'The only provider of this pair is «Manual»: LibreFolio downloads nothing for it and keeps the rates typed on the pair’s page. «Auto» reads the latest of them, when there is one.',
        });
    }
</script>

<div class="space-y-4" data-testid="pac-planner-fx" aria-busy={reader.busy} data-busy={reader.busy ? 'true' : 'false'}>
    <p class="flex flex-wrap items-center gap-1 text-sm text-gray-700 dark:text-gray-300">
        {$t(`${KEY}.intro`, {default: 'The rates the calculation needs, one for each pair of currencies in play. «Auto» uses the rate stored in LibreFolio, «Manual» a rate of your own.'})}
        <HelpTip
            label={$t('tools.pacAllocator.planner.mode.auto', {default: 'Auto'})}
            help={$t(`${KEY}.autoHelp`, {
                default: '«Auto» reads the latest rate LibreFolio already has, when this step opens and again just before the calculation: no provider is called. «Manual» uses your rate as typed and never reads it again. The calculation decides by itself whether and how much to convert.',
            })}
            testid="pac-planner-fx-auto-help"
        />
    </p>

    {#if reader.error}
        <div class="{NOTICE.warning} flex flex-wrap items-start justify-between gap-2" role="alert" data-testid="pac-planner-fx-read-error">
            <p>{$t(reader.error.key, {default: reader.error.fallback})}</p>
            <div class="flex shrink-0 gap-3">
                {#if reader.canRetry}
                    <button type="button" class={BUTTON_LINK} data-testid="pac-planner-fx-read-retry" onclick={() => reader.retry(draft, accountGeneration)}>{$t('common.retry', {default: 'Retry'})}</button>
                {/if}
                <button type="button" class={BUTTON_LINK} data-testid="pac-planner-fx-read-dismiss" onclick={() => reader.dismiss()}>{$t('common.close', {default: 'Close'})}</button>
            </div>
        </div>
    {/if}

    {#if draft.requiredPairs.length === 0}
        <p class={HINT} data-testid="pac-planner-fx-empty">{$t(`${KEY}.none`, {default: 'No conversion needed: every currency in play is the valuation currency.'})}</p>
    {:else}
        <div class="grid gap-3 lg:grid-cols-2">
            {#each draft.requiredPairs as pair (pair)}
                {@const fx = draft.fx(pair)}
                {@const [base, quote] = sides(pair)}
                {@const manual = fx?.manual ?? false}
                {@const rate = fx?.rate.trim() ?? ''}
                {@const status = readState(pair)}
                <section
                    class={CARD}
                    data-testid="pac-planner-fx-pair"
                    data-pair={pair}
                    data-purpose={draft.fxPurpose(pair)}
                    data-mode={manual ? 'manual' : 'auto'}
                    data-rate={rate === '' ? 'missing' : 'set'}
                    data-read={status}
                >
                    <div class="flex flex-wrap items-center justify-between gap-2">
                        <h3 class="flex flex-wrap items-center gap-1.5 font-semibold text-gray-900 dark:text-gray-100" data-testid="pac-planner-fx-pair-title">
                            <CurrencyCode code={base} />
                            <span class="text-sm font-normal text-gray-400 dark:text-gray-500" aria-hidden="true">→</span>
                            <CurrencyCode code={quote} />
                        </h3>
                        <AutoManualToggle {manual} label={pairLabel(pair)} testid="pac-planner-fx-mode" onchange={(next) => switchMode(pair, next)} />
                    </div>

                    <p class="mt-1 flex flex-wrap items-center gap-1">
                        {#each uses(pair) as use (use)}
                            <span class={use === 'valuation' ? BADGE.info : BADGE.neutral} data-testid="pac-planner-fx-purpose" data-purpose={use}>{useText(use)}</span>
                            <HelpTip label={useText(use)} help={useHelp(use)} testid="pac-planner-fx-purpose-help" />
                        {/each}
                    </p>

                    <div class="mt-3 text-sm">
                        {#if manual}
                            <div class="flex flex-wrap items-center gap-2" data-testid="pac-planner-fx-rate-manual">
                                <label for="{ids}-{pair}" class="flex items-center gap-1 whitespace-nowrap tabular-nums">1 <CurrencyCode code={base} testid="pac-planner-fx-rate-base" /> =</label>
                                <span class="w-40">
                                    <ExactDecimalInput id="{ids}-{pair}" value={fx?.rate ?? ''} step="0.0001" className={INPUT} testid="pac-planner-fx-rate" onchange={(value) => setRate(pair, value)} />
                                </span>
                                <CurrencyCode code={quote} testid="pac-planner-fx-rate-quote" />
                                <HelpTip label={pairLabel(pair)} help={manualHelp(fx)} testid="pac-planner-fx-rate-help" />
                            </div>
                        {:else if rate !== '' && fx}
                            <p class="flex flex-wrap items-center gap-2" data-testid="pac-planner-fx-rate-value">
                                <span class="flex flex-wrap items-center gap-1 tabular-nums text-gray-900 dark:text-gray-100">
                                    1 <CurrencyCode code={base} testid="pac-planner-fx-rate-base" /> = <span class="font-semibold">{formatPlannerFxRate(rate)}</span>
                                    <CurrencyCode code={quote} testid="pac-planner-fx-rate-quote" />
                                </span>
                                {#if fx.stamp}
                                    <HelpTip label={pairLabel(pair)} help={rateHelp(fx)} testid="pac-planner-fx-rate-help" />
                                {/if}
                            </p>
                        {:else if status === 'reading'}
                            <span class="flex items-center gap-2 {HINT}" role="status" data-testid="pac-planner-fx-reading">
                                <LoaderCircle class="h-4 w-4 motion-safe:animate-spin" aria-hidden="true" />{$t(`${KEY}.reading`, {default: 'Reading the rate stored in LibreFolio…'})}
                            </span>
                        {:else if status === 'ownerless'}
                            <p class="text-amber-800 dark:text-amber-200" data-testid="pac-planner-fx-no-rate">
                                {$t(`${KEY}.ownerless`, {default: 'LibreFolio reads its stored rates through a Broker you own, and you own none: switch to «Manual» and type the rate.'})}
                            </p>
                        {:else if status === 'not-stored'}
                            {@const setup = setups ? pairSetup(setups, base, quote) : null}
                            <div class="space-y-2" data-testid="pac-planner-fx-no-rate" data-setup={setup ?? 'loading'}>
                                <p class="flex flex-wrap items-center gap-1 text-amber-800 dark:text-amber-200">
                                    {setupText(setup)}
                                    {#if setup}
                                        <HelpTip label={pairLabel(pair)} help={setupHelp(setup)} testid="pac-planner-fx-no-rate-help" />
                                    {/if}
                                </p>
                                {#if setup === 'absent'}
                                    <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-fx-add-pair" onclick={() => openAdd(pair)}>
                                        <Plus class="h-4 w-4" aria-hidden="true" />{$t(`${KEY}.addPair`, {default: 'Add the pair'})}
                                    </button>
                                {:else if setup === 'provider'}
                                    <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-fx-sync" onclick={() => openSync(pair)}>
                                        <Download class="h-4 w-4" aria-hidden="true" />{$t(`${KEY}.syncRates`, {default: 'Download the rates'})}
                                    </button>
                                {:else if setup === 'manual'}
                                    <a class={BUTTON_LINK} href="/fx/{createPairSlug(base, quote)}" target="_blank" rel="noopener noreferrer" data-testid="pac-planner-fx-open-pair">
                                        {$t(`${KEY}.openPair`, {default: 'Open the pair'})}<ExternalLink class="h-3.5 w-3.5" aria-hidden="true" />
                                    </a>
                                {/if}
                            </div>
                        {:else}
                            <p class={HINT} data-testid="pac-planner-fx-no-rate">{$t(`${KEY}.readLater`, {default: 'Read from LibreFolio just before the calculation.'})}</p>
                        {/if}
                    </div>
                </section>
            {/each}
        </div>
    {/if}

    {#if draft.conversionPairs.length > 0}
        <div class="max-w-xs" data-testid="pac-planner-fx-spread-field">
            <div class={LABEL_ROW}>
                <label for="{ids}-spread">{$t(`${KEY}.spread`, {default: 'Conversion spread *'})}</label>
                <HelpTip
                    label={$t(`${KEY}.spread`, {default: 'Conversion spread *'})}
                    help={$t(`${KEY}.spreadHint`, {
                        default: 'A margin surcharge, as a percentage of the amount converted, to cover possible changes in the official rate or Broker fees.',
                    })}
                    testid="pac-planner-fx-spread-help"
                />
            </div>
            <div class="relative">
                <ExactDecimalInput id="{ids}-spread" bind:value={draft.data.fxSpreadPercent} step="0.01" max="100" className="{INPUT} pr-10" testid="pac-planner-fx-spread" />
                <span class={INPUT_ADORNMENT} aria-hidden="true">%</span>
            </div>
        </div>
    {/if}
</div>

{#if adding}
    <FxPairAddModal
        bind:open={addOpen}
        initialBase={adding.base}
        initialQuote={adding.quote}
        oncreated={afterCreation(adding.pair)}
        onsynced={afterDownload(adding.pair)}
        onclose={() => (adding = null)}
    />
{/if}

{#if syncing}
    <FxSyncModal
        bind:open={syncOpen}
        dateStart={syncing.start}
        dateEnd={syncing.end}
        pairs={[createPairSlug(syncing.base, syncing.quote)]}
        onsynced={afterDownload(syncing.pair)}
        onclose={() => {
            syncOpen = false;
            syncing = null;
        }}
    />
{/if}
