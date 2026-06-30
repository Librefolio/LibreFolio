<!--
  ContributionTable — Per-asset period P&L contribution table.

  Columns: Asset, Type, Broker, Period P&L, Impact.
  Sorted by |period_pnl| descending.
  Includes "Unallocated" row(s) for fees/income without asset_id.

  Pattern: Svelte 5 Runes, data-testid, dark mode.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {getAssetInfo} from '$lib/stores/reference/assetStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {getBrokerIconUrlById} from '$lib/utils/broker/brokerHelpers';
    import {getBrokerInfo} from '$lib/stores/reference/brokerStore';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';

    interface Position {
        asset_id: number;
        asset_name: string;
        asset_ticker?: string | (string | null)[] | null;
        asset_type: string;
        broker_id: number;
        broker_name: string;
        period_pnl?: string | (string | null)[] | null;
        period_pnl_percent?: string | (string | null)[] | null;
        is_fully_sold?: boolean;
    }

    interface Unallocated {
        broker_id: number;
        broker_name: string;
        unallocated_income?: string | (string | null)[] | null;
        unallocated_fees_taxes?: string | (string | null)[] | null;
    }

    interface Props {
        positions: Position[];
        unallocated: Unallocated[];
        displayCurrency?: string;
    }

    let {positions = [], unallocated = [], displayCurrency = 'EUR'}: Props = $props();

    function safeNum(v: string | (string | null)[] | null | undefined): number | null {
        const s = Array.isArray(v) ? (v[0] ?? null) : v;
        if (s == null) return null;
        const n = parseFloat(s);
        return isNaN(n) ? null : n;
    }

    // Build unified rows: positions + unallocated
    interface DisplayRow {
        key: string;
        assetName: string;
        assetType: string;
        brokerId: number;
        brokerName: string;
        pnl: number | null;
        isUnallocated: boolean;
        isFullySold: boolean;
        assetId?: number;
    }

    let displayRows = $derived.by(() => {
        const rows: DisplayRow[] = [];

        // Position rows
        for (const p of positions) {
            const pnl = safeNum(p.period_pnl);
            rows.push({
                key: `pos-${p.broker_id}-${p.asset_id}`,
                assetName: p.asset_name,
                assetType: p.asset_type,
                brokerId: p.broker_id,
                brokerName: p.broker_name,
                pnl,
                isUnallocated: false,
                isFullySold: p.is_fully_sold ?? false,
                assetId: p.asset_id,
            });
        }

        // Unallocated rows
        for (const u of unallocated) {
            const income = safeNum(u.unallocated_income) ?? 0;
            const fees = safeNum(u.unallocated_fees_taxes) ?? 0;
            const pnl = income - fees;
            if (pnl === 0 && income === 0 && fees === 0) continue;
            rows.push({
                key: `unalloc-${u.broker_id}`,
                assetName: $_('dashboard.unallocated'),
                assetType: '—',
                brokerId: u.broker_id,
                brokerName: u.broker_name,
                pnl,
                isUnallocated: true,
                isFullySold: false,
            });
        }

        // Sort by |pnl| descending
        rows.sort((a, b) => Math.abs(b.pnl ?? 0) - Math.abs(a.pnl ?? 0));

        return rows;
    });

    // Compute impact labels: Gain #N / Loss #N
    let impactLabels = $derived.by(() => {
        const labels = new Map<string, string>();
        let gainRank = 0;
        let lossRank = 0;

        // Sort by pnl descending for gain ranking, ascending for loss ranking
        const gainsSorted = displayRows.filter((r) => r.pnl != null && r.pnl > 0).sort((a, b) => (b.pnl ?? 0) - (a.pnl ?? 0));
        const lossesSorted = displayRows.filter((r) => r.pnl != null && r.pnl < 0).sort((a, b) => (a.pnl ?? 0) - (b.pnl ?? 0));

        for (const r of gainsSorted) {
            gainRank++;
            labels.set(r.key, `${$_('dashboard.gains')} #${gainRank}`);
        }
        for (const r of lossesSorted) {
            lossRank++;
            labels.set(r.key, `${$_('dashboard.losses')} #${lossRank}`);
        }
        return labels;
    });

    function fmtPnl(pnl: number | null): string {
        if (pnl == null) return '—';
        return formatCurrencyAmountPlain(pnl, displayCurrency, {showSign: true});
    }

    function pnlClass(pnl: number | null): string {
        if (pnl == null) return 'text-gray-400 dark:text-gray-500';
        return pnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400';
    }

    function assetIconSrc(r: DisplayRow): string | null {
        if (r.isUnallocated || !r.assetId) return null;
        const info = getAssetInfo(r.assetId);
        return info?.icon_url || getAssetTypeIconUrl(r.assetType) || null;
    }

    function brokerIconSrc(r: DisplayRow): string | null {
        return getBrokerIconUrlById(r.brokerId, [getBrokerInfo(r.brokerId)].filter(Boolean) as any[]);
    }
</script>

<table class="w-full text-xs" data-testid="contribution-table">
    <thead>
        <tr class="text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-slate-700">
            <th class="text-left pb-2 pr-2 font-medium">{$_('common.asset')}</th>
            <th class="text-left pb-2 pr-2 font-medium">{$_('common.type')}</th>
            <th class="text-left pb-2 pr-2 font-medium">{$_('brokers.title')}</th>
            <th class="text-right pb-2 pr-2 font-medium">{$_('dashboard.periodPnl')}</th>
            <th class="text-right pb-2 font-medium">{$_('dashboard.impact')}</th>
        </tr>
    </thead>
    <tbody>
        {#each displayRows as row (row.key)}
            {@const iconSrc = assetIconSrc(row)}
            {@const bIconSrc = brokerIconSrc(row)}
            <tr
                class="border-b border-gray-50 dark:border-slate-700/50 hover:bg-gray-50 dark:hover:bg-slate-700/30 transition-colors {row.isUnallocated ? 'opacity-70' : ''} {row.isFullySold ? 'italic' : ''}"
                data-testid="contribution-row"
            >
                <!-- Asset -->
                <td class="py-2 pr-2">
                    <div class="flex items-center gap-1.5 min-w-0">
                        {#if iconSrc}
                            <img src={iconSrc} alt="" class="w-5 h-5 rounded-full object-cover shrink-0" onerror={(e) => { (e.target as HTMLElement).style.display = 'none'; }} />
                        {:else if !row.isUnallocated}
                            <div class="w-5 h-5 rounded-full bg-libre-green/10 flex items-center justify-center shrink-0 text-[10px] text-libre-green font-bold">
                                {(row.assetName ?? '?')[0].toUpperCase()}
                            </div>
                        {/if}
                        <span class="truncate max-w-[120px] text-gray-700 dark:text-gray-200 font-medium">
                            {row.assetName}
                            {#if row.isFullySold}
                                <span class="text-[9px] text-gray-400 dark:text-gray-500 ml-1">(sold)</span>
                            {/if}
                        </span>
                    </div>
                </td>
                <!-- Type -->
                <td class="py-2 pr-2">
                    {#if row.assetType !== '—'}
                        <span class="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300">
                            {row.assetType}
                        </span>
                    {:else}
                        <span class="text-gray-400">—</span>
                    {/if}
                </td>
                <!-- Broker -->
                <td class="py-2 pr-2">
                    <div class="flex items-center gap-1 min-w-0">
                        {#if bIconSrc}
                            <img src={bIconSrc} alt="" class="w-4 h-4 rounded-sm object-contain shrink-0" onerror={(e) => { (e.target as HTMLElement).style.display = 'none'; }} />
                        {/if}
                        <span class="truncate text-gray-500 dark:text-gray-400 max-w-[80px]">{row.brokerName}</span>
                    </div>
                </td>
                <!-- Period P&L -->
                <td class="py-2 pr-2 text-right font-medium whitespace-nowrap {pnlClass(row.pnl)}">
                    {fmtPnl(row.pnl)}
                </td>
                <!-- Impact -->
                <td class="py-2 text-right text-[10px] text-gray-500 dark:text-gray-400 whitespace-nowrap">
                    {impactLabels.get(row.key) ?? '—'}
                </td>
            </tr>
        {/each}
    </tbody>
</table>
