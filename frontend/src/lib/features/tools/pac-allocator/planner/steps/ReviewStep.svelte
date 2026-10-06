<script lang="ts">
    import {ChevronDown, ChevronRight, Pencil} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef, EnumOption, RowAction} from '$lib/components/table/types';
    import type {PlannerDraft} from '../draft.svelte';
    import type {ListedIssue} from '../labels';
    import {factOriginState, sectionCounts, snapshotFacts, type FactKind, type FactOriginState, type SnapshotFact} from '../review';
    import type {PlannerStep} from '../types';
    import {BUTTON_PRIMARY, BUTTON_SECONDARY, HINT, NOTICE, SECTION_TITLE} from '../ui';
    import HelpTip from '../shared/HelpTip.svelte';
    import IssueList from '../shared/IssueList.svelte';
    import ReviewCell from '../shared/ReviewCell.svelte';
    import TableColumns from '../shared/TableColumns.svelte';

    interface Props {
        draft: PlannerDraft;
        problems: readonly ListedIssue[];
        busy: boolean;
        hasResult: boolean;
        ongoto: (step: PlannerStep) => void;
        oncalculate: () => void;
        onshowresult: () => void;
    }

    let {draft, problems, busy, hasResult, ongoto, oncalculate, onshowresult}: Props = $props();

    interface SectionRow {
        step: PlannerStep;
        blocked: boolean;
        text: string;
        currencies: string[];
    }

    const KEY = 'tools.pacAllocator.planner.review';
    const PLANNER_KEY = 'tools.pacAllocator.planner';
    const POLICY_FALLBACKS: Record<string, string> = {proportional: 'Proportional'};
    const SECTIONS: PlannerStep[] = ['scenario', 'liquidity', 'brokers', 'assets', 'routing', 'targets', 'fx', 'strategy'];
    const KIND_ORDER: FactKind[] = ['broker', 'cash', 'contribution', 'price', 'fx'];
    const KIND_FALLBACKS: Record<FactKind, string> = {broker: 'Broker', cash: 'Cash', contribution: 'Contribution', price: 'Price', fx: 'Exchange rate'};
    const ORIGIN_ORDER: FactOriginState[] = ['librefolio', 'manual', 'modified'];

    let factsOpen = $state(false);
    let sectionsTable = $state<DataTable<SectionRow>>();
    let factsTable = $state<DataTable<SnapshotFact>>();

    const counts = $derived(sectionCounts(draft));
    const facts = $derived(snapshotFacts(draft));
    const blocked = $derived(new Set(problems.map((problem) => problem.step)));
    /** R9.4: FX is listed only when the scenario needs a rate, or has a problem there. */
    const sections = $derived(SECTIONS.filter((step) => step !== 'fx' || draft.fxNeeded || blocked.has('fx')));

    function summary(step: PlannerStep): {text: string; currencies: string[]} {
        switch (step) {
            case 'scenario':
                return counts.scenario.currency ? {text: '', currencies: [counts.scenario.currency]} : {text: '—', currencies: []};
            case 'liquidity':
                return {text: $t(`${KEY}.sources`, {default: '{count, plural, one {# source} other {# sources}}', values: {count: counts.liquidity.sources}}), currencies: counts.liquidity.currencies};
            case 'brokers':
                return {
                    text: $t(`${KEY}.brokers`, {
                        default: '{operative, plural, one {# Broker} other {# Brokers}}{external, plural, =0 {} one { · # external account} other { · # external accounts}}',
                        values: {operative: counts.brokers.operative, external: counts.brokers.fundingOnly},
                    }),
                    currencies: [],
                };
            case 'assets':
                return {
                    text: $t(`${KEY}.assets`, {
                        default: '{count, plural, one {# Asset} other {# Assets}}{missing, plural, =0 {} other { · # without a price}}{stale, plural, =0 {} one { · # price not of today} other { · # prices not of today}}',
                        values: {count: counts.assets.count, missing: counts.assets.missing, stale: counts.assets.stale},
                    }),
                    currencies: [],
                };
            case 'routing':
                return {text: $t(`${KEY}.routes`, {default: '{assets} of {total, plural, one {# Asset} other {# Assets}} can be bought', values: {assets: counts.routing.assetsWithRoute, total: counts.assets.count}}), currencies: []};
            case 'targets':
                return {text: $t(`${KEY}.targets`, {default: '{count} of {total, plural, one {# Asset} other {# Assets}} with a target', values: {count: counts.targets.count, total: counts.assets.count}}), currencies: []};
            case 'fx':
                return {
                    text: $t(`${KEY}.fxRated`, {
                        default: '{count, plural, one {# exchange rate} other {# exchange rates}}{missing, plural, =0 {} other { · # without a rate}}{stale, plural, =0 {} other { · # not of today}}',
                        values: {count: counts.fx.needed, missing: counts.fx.missing, stale: counts.fx.stale},
                    }),
                    currencies: [],
                };
            case 'strategy':
                return {text: counts.strategy.policy ? $t(`${PLANNER_KEY}.policies.${counts.strategy.policy}`, {default: POLICY_FALLBACKS[counts.strategy.policy] ?? counts.strategy.policy}) : '—', currencies: []};
            default:
                return {text: '', currencies: []};
        }
    }

    const sectionRows = $derived(sections.map((step): SectionRow => ({step, blocked: blocked.has(step), ...summary(step)})));

    const sectionColumns = $derived.by((): ColumnDef<SectionRow>[] => [
        {
            id: 'step',
            header: () => $t(`${KEY}.factStep`, {default: 'Step'}),
            type: 'custom',
            sortable: false,
            filterable: false,
            minWidth: 140,
            cell: (row) => ({type: 'custom', component: ReviewCell, props: {cell: {type: 'step', step: row.step, blocked: row.blocked}}}),
        },
        {
            id: 'summary',
            header: () => $t(`${KEY}.colSummary`, {default: 'Summary'}),
            type: 'custom',
            sortable: false,
            filterable: false,
            minWidth: 200,
            cell: (row) => ({type: 'custom', component: ReviewCell, props: {cell: {type: 'summary', text: row.text, currencies: row.currencies}}}),
        },
    ]);

    const sectionActions = $derived.by((): RowAction<SectionRow>[] => [
        {id: 'edit', icon: Pencil, label: () => $t(`${KEY}.edit`, {default: 'Edit'}), onClick: (row) => ongoto(row.step), testid: 'pac-planner-review-goto'},
    ]);

    function kindLabel(kind: FactKind): string {
        return $t(`${KEY}.kind.${kind}`, {default: KIND_FALLBACKS[kind]});
    }

    function originLabel(origin: FactOriginState): string {
        if (origin === 'librefolio') return $t(`${KEY}.origin.librefolio`, {default: 'LibreFolio'});
        return $t(`${PLANNER_KEY}.origin.${origin}`, {default: origin === 'manual' ? 'Manual' : 'Modified'});
    }

    /** The name plus its currency codes, so the text filter also finds «USD». */
    function searchText(fact: SnapshotFact): string {
        const subject = fact.subject;
        const codes = subject.type === 'cash' || subject.type === 'contribution' ? [subject.currency] : subject.type === 'pair' ? [subject.base, subject.quote] : [];
        return [fact.entity, ...codes].join(' ');
    }

    const kindOptions = $derived.by((): EnumOption[] => {
        const present = new Set(facts.map((fact) => fact.kind));
        return KIND_ORDER.filter((kind) => present.has(kind)).map((kind) => ({value: kind, label: kindLabel(kind)}));
    });
    const originOptions = $derived.by((): EnumOption[] => {
        const present = new Set(facts.map((fact) => factOriginState(fact)));
        return ORIGIN_ORDER.filter((origin) => present.has(origin)).map((origin) => ({value: origin, label: originLabel(origin)}));
    });

    const factColumns = $derived.by((): ColumnDef<SnapshotFact>[] => [
        {
            id: 'entity',
            header: () => $t(`${KEY}.factEntity`, {default: 'Item'}),
            type: 'text',
            minWidth: 180,
            getValue: (fact) => searchText(fact),
            cell: (fact) => ({
                type: 'custom',
                component: ReviewCell,
                props: {
                    cell: {
                        type: 'entity',
                        fact,
                        broker: fact.subject.type === 'broker' || fact.subject.type === 'cash' ? (draft.broker(fact.subject.brokerKey) ?? null) : null,
                        asset: fact.subject.type === 'asset' ? (draft.asset(fact.subject.assetKey) ?? null) : null,
                    },
                },
            }),
        },
        {
            id: 'kind',
            header: () => $t(`${KEY}.colKind`, {default: 'Type'}),
            type: 'enum',
            enumOptions: kindOptions,
            minWidth: 110,
            getValue: (fact) => fact.kind,
            sortFn: (a, b) => KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind),
            cell: (fact) => ({
                type: 'custom',
                component: ReviewCell,
                props: {cell: {type: 'kind', label: kindLabel(fact.kind)}},
            }),
        },
        {
            id: 'value',
            header: () => $t(`${KEY}.factValue`, {default: 'Value'}),
            type: 'custom',
            sortable: false,
            filterable: false,
            minWidth: 160,
            cell: (fact) => ({type: 'custom', component: ReviewCell, props: {cell: {type: 'value', fact}}}),
        },
        {
            id: 'origin',
            header: () => $t(`${KEY}.factOrigin`, {default: 'Origin'}),
            type: 'enum',
            enumOptions: originOptions,
            minWidth: 120,
            getValue: (fact) => factOriginState(fact),
            sortFn: (a, b) => ORIGIN_ORDER.indexOf(factOriginState(a)) - ORIGIN_ORDER.indexOf(factOriginState(b)),
            cell: (fact) => ({type: 'custom', component: ReviewCell, props: {cell: {type: 'origin', fact}}}),
        },
    ]);

    const factActions = $derived.by((): RowAction<SnapshotFact>[] => [
        {id: 'edit', icon: Pencil, label: () => $t(`${KEY}.edit`, {default: 'Edit'}), onClick: (fact) => ongoto(fact.step), testid: 'pac-planner-review-fact-goto'},
    ]);
</script>

<div class="space-y-4" data-testid="pac-planner-review">
    <div class="flex flex-wrap items-center gap-1">
        <p class="text-sm text-gray-700 dark:text-gray-300">{$t(`${KEY}.lead`, {default: 'Last check before the calculation.'})}</p>
        <HelpTip
            label={$t(`${KEY}.lead`, {default: 'Last check before the calculation.'})}
            help={$t(`${KEY}.help`, {
                default: 'The calculation uses only the data listed here. Just before it, LibreFolio reads again the prices, rates and balances you took from LibreFolio without changing them; the ones you typed or changed stay as they are.',
            })}
            testid="pac-planner-review-help"
        />
        <TableColumns table={sectionsTable} testid="pac-planner-review-sections-columns" />
    </div>

    <div data-testid="pac-planner-review-sections">
        <DataTable
            bind:this={sectionsTable}
            data={sectionRows}
            columns={sectionColumns}
            getRowId={(row) => row.step}
            storageKey="pac-planner-review-sections"
            onRowClick={(row) => ongoto(row.step)}
            enableSorting={false}
            enablePagination={false}
            enableSelection={false}
            selectionMode="none"
            enableColumnVisibility
            enableColumnFilters={false}
            enableColumnResize
            enableContextMenu={false}
            enableActions
            rowActions={sectionActions}
            actionsColumnWidth="64px"
            tableLayout="auto"
        />
    </div>

    {#if problems.length > 0}
        <div class={NOTICE.warning} role="alert" data-testid="pac-planner-review-problems">
            <p class="mb-2 font-medium">{$t(`${KEY}.problems`, {default: 'Complete these fields before calculating:'})}</p>
            <IssueList items={problems} {ongoto} testid="pac-planner-review-problem" />
        </div>
    {/if}

    {#if facts.length > 0}
        <section class="space-y-2">
            <button
                type="button"
                class="flex items-center gap-1 rounded text-left {SECTION_TITLE} focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green"
                aria-expanded={factsOpen}
                aria-controls="pac-planner-review-facts-body"
                data-testid="pac-planner-review-facts-toggle"
                onclick={() => (factsOpen = !factsOpen)}
            >
                {#if factsOpen}<ChevronDown size={16} aria-hidden="true" />{:else}<ChevronRight size={16} aria-hidden="true" />{/if}
                {$t(`${KEY}.factsToggle`, {default: 'Calculation data ({count})', values: {count: facts.length}})}
            </button>
            <div id="pac-planner-review-facts-body" hidden={!factsOpen}>
                {#if factsOpen}
                    <div class="space-y-2" data-testid="pac-planner-review-facts">
                        <TableColumns table={factsTable} testid="pac-planner-review-facts-columns" />
                        <DataTable
                            bind:this={factsTable}
                            data={facts}
                            columns={factColumns}
                            getRowId={(fact) => fact.id}
                            storageKey="pac-planner-review-facts"
                            enableSorting
                            enablePagination={false}
                            enableSelection={false}
                            selectionMode="none"
                            enableColumnVisibility
                            enableColumnFilters
                            enableColumnResize
                            enableContextMenu={false}
                            enableActions
                            rowActions={factActions}
                            actionsColumnWidth="64px"
                            tableLayout="auto"
                            emptyMessage={$t(`${KEY}.factsEmpty`, {default: 'No item matches these filters.'})}
                        />
                    </div>
                {/if}
            </div>
        </section>
    {/if}

    <div class="space-y-2">
        <div class="flex flex-wrap justify-center gap-3">
            {#if hasResult}
                <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-show-result" onclick={onshowresult}>{$t(`${KEY}.showResult`, {default: 'See the last result'})}</button>
            {/if}
            <button type="button" class={BUTTON_PRIMARY} disabled={busy || problems.length > 0} data-testid="pac-planner-calculate" onclick={oncalculate}>
                {$t(`${KEY}.calculate`, {default: 'Calculate plan'})}
            </button>
        </div>
        <p class="text-center {HINT}">{$t(`${KEY}.noOrdersHint`, {default: 'The calculation sends no order to the Brokers.'})}</p>
    </div>
</div>
