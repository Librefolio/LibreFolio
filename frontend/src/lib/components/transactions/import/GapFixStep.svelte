<!--
  GapFixStep.svelte — "Align with the bank", the import wizard's step after the review for report sets.

  Per broker and plugin (one gap-fix request), per truth point: what LibreFolio will have next to
  what the bank states, where the difference comes from, and the corrections that close it,
  selected by default (D-S14). The verifications are only compared, never corrected. A controlled
  component: the wizard owns the selection, and the step only asks to flip a key.

  Plain Svelte text, no {@html}. Money goes through CurrencyAmount (privacy). A position's quantity
  sits next to the bank's figures and is masked (D5′); a correction's quantity is a transaction's,
  and stays visible.

  Design: LibreFolio_developer_journal/Release_2/Phase_0/26_brimDanskeBank/design-phase00BrimReportSets.md, §4.6.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {AlertTriangle, CheckCircle, Info, XCircle} from 'lucide-svelte';
    import CurrencyAmount from '$lib/components/ui/display/CurrencyAmount.svelte';
    import {maskableQuantity} from '$lib/utils/privacy/maskable';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {formatIsoDay} from '$lib/utils/transactions/importReportSets';
    import {gapFixProposalCount, gapFixSelectedCount, type GapFixAmount, type GapFixNote, type GapFixProposal, type GapFixView} from '$lib/utils/transactions/gapFixModel';

    interface Props {
        view: GapFixView;
        selected: ReadonlySet<string>;
        onToggle: (key: string) => void;
        assetName: (assetId: number) => string;
        brokerName: (brokerId: number) => string;
    }

    let {view, selected, onToggle, assetName, brokerName}: Props = $props();

    let proposalCount = $derived(gapFixProposalCount(view));
    let selectedCount = $derived(gapFixSelectedCount(view, selected));

    const P = 'importWizard.reportSet.gapFix.';

    function quantity(value: string): string {
        return formatDecimalForDisplay(value, {minFrac: 0, maxFrac: 8});
    }

    function signedQuantity(value: string): string {
        const formatted = quantity(value);
        return Number(value) > 0 ? `+${formatted}` : formatted;
    }

    function nonZero(list: GapFixAmount[]): GapFixAmount[] {
        return list.filter((item) => Number(item.amount) !== 0);
    }

    function noteText(note: GapFixNote): string {
        const key = `${P}note.${note.code}`;
        const translated = $t(key);
        return translated === key ? note.message : translated;
    }

    function typeLabel(type: string): string {
        const key = `transactions.types.${type}`;
        const translated = $t(key);
        return translated === key ? type : translated;
    }

    function proposalFacts(proposal: GapFixProposal) {
        const tx = proposal.tx;
        const cash = typeof tx.cash === 'object' && tx.cash !== null && !Array.isArray(tx.cash) ? (tx.cash as {code?: unknown; amount?: unknown}) : null;
        return {
            type: String(tx.type ?? ''),
            date: String(tx.date ?? '').slice(0, 10),
            assetId: typeof tx.asset_id === 'number' ? tx.asset_id : null,
            quantity: tx.quantity !== null && tx.quantity !== undefined && Number(tx.quantity) !== 0 ? String(tx.quantity) : null,
            cash: cash && typeof cash.code === 'string' ? {code: cash.code, amount: Number(cash.amount)} : null,
        };
    }
</script>

{#snippet amountList(list: GapFixAmount[])}
    {#each list as item, index (index)}
        <span class="whitespace-nowrap font-mono"
            >{#if index > 0}·{/if}
            <CurrencyAmount amount={Number(item.amount)} code={item.currency} /></span
        >
    {/each}
{/snippet}

<div class="space-y-4" data-testid="import-wizard-gapfix" data-proposal-count={proposalCount} data-selected-count={selectedCount}>
    <p class="text-sm text-gray-600 dark:text-gray-300">{$t(`${P}intro`)}</p>

    {#each view.groups as group (group.key)}
        <section class="rounded-lg border border-gray-200 dark:border-slate-700" data-testid="gapfix-group" data-broker-id={group.brokerId} data-plugin-code={group.pluginCode}>
            <header class="border-b border-gray-200 bg-gray-50 px-4 py-2 text-sm font-semibold text-gray-800 dark:border-slate-700 dark:bg-slate-800/60 dark:text-gray-100">{brokerName(group.brokerId)}</header>

            {#if group.error !== null}
                <div role="alert" class="m-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300" data-testid="gapfix-error">
                    <p class="flex items-center gap-1.5 font-medium"><AlertTriangle size={14} /> {$t(`${P}error`)}</p>
                    <p class="mt-1 break-words font-mono text-xs">{group.error}</p>
                    <p class="mt-1 text-xs">{$t(`${P}errorContinue`)}</p>
                </div>
            {:else}
                <div class="space-y-3 p-4">
                    {#each group.checkpoints as checkpoint (checkpoint.key)}
                        {@const explanation = checkpoint.explanation}
                        {@const openingCash = nonZero(explanation.openingCash)}
                        <div class="rounded-lg border border-gray-200 dark:border-slate-700" data-testid="gapfix-checkpoint" data-as-of={checkpoint.asOf} data-kind={checkpoint.kind}>
                            <h4 class="border-b border-gray-100 px-3 py-2 text-sm font-medium text-gray-800 dark:border-slate-700 dark:text-gray-100">
                                {$t(checkpoint.kind === 'opening' ? `${P}checkpointOpening` : `${P}checkpointGap`, {values: {date: formatIsoDay(checkpoint.asOf)}})}
                            </h4>

                            {#if checkpoint.cash.length > 0 || checkpoint.positions.length > 0}
                                <div class="overflow-x-auto px-3 py-2">
                                    <table class="w-full text-sm">
                                        <thead>
                                            <tr class="text-xs text-gray-500 dark:text-gray-400">
                                                <th class="py-1 text-left font-normal"></th>
                                                <th class="py-1 text-right font-normal">LibreFolio</th>
                                                <th class="py-1 text-right font-normal">{$t(`${P}bank`)}</th>
                                                <th class="py-1 text-right font-normal">{$t(`${P}difference`)}</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {#each checkpoint.cash as row, index (index)}
                                                <tr data-testid="gapfix-cash-row" data-currency={row.currency} data-difference={row.difference}>
                                                    <td class="py-1 pr-3 text-gray-700 dark:text-gray-200">{$t(`${P}cashLabel`, {values: {currency: row.currency}})}</td>
                                                    <td class="py-1 text-right font-mono"><CurrencyAmount amount={Number(row.librefolio)} code={row.currency} /></td>
                                                    <td class="py-1 text-right font-mono"><CurrencyAmount amount={Number(row.bank)} code={row.currency} /></td>
                                                    <td class="py-1 text-right font-mono"><CurrencyAmount amount={Number(row.difference)} code={row.currency} options={{showSign: true}} /></td>
                                                </tr>
                                            {/each}
                                            {#each checkpoint.positions as position, index (index)}
                                                <tr data-testid="gapfix-position-row" data-asset-id={position.assetId} data-exactness={position.exactness}>
                                                    <td class="py-1 pr-3 text-gray-700 dark:text-gray-200">{assetName(position.assetId)}</td>
                                                    <td class="py-1 text-right font-mono">{maskableQuantity(quantity(position.librefolio))}</td>
                                                    <td class="py-1 text-right font-mono">
                                                        {#if position.exactness === 'at_least'}
                                                            {$t(`${P}atLeast`, {values: {quantity: maskableQuantity(quantity(position.bank))}})}
                                                        {:else}
                                                            {maskableQuantity(quantity(position.bank))}
                                                        {/if}
                                                    </td>
                                                    <td class="py-1 text-right font-mono">{maskableQuantity(signedQuantity(position.difference))}</td>
                                                </tr>
                                            {/each}
                                        </tbody>
                                    </table>
                                </div>
                            {/if}

                            {#if explanation.absorbedCount > 0 || openingCash.length > 0 || explanation.unexplainedCash.length > 0 || explanation.notes.length > 0}
                                <div class="space-y-1 border-t border-gray-100 px-3 py-2 text-xs text-gray-600 dark:border-slate-700 dark:text-gray-300" data-testid="gapfix-explanation">
                                    {#if explanation.absorbedCount > 0}
                                        <p>
                                            {$t(`${P}absorbed`, {values: {n: explanation.absorbedCount}})}
                                            {#if explanation.absorbedMissingCount > 0}
                                                {$t(`${P}absorbedMissing`, {values: {n: explanation.absorbedMissingCount}})}
                                                {@render amountList(explanation.absorbedMissingCash)}
                                            {/if}
                                        </p>
                                    {/if}
                                    {#if openingCash.length > 0}
                                        <p>{$t(`${P}openingCash`)} {@render amountList(openingCash)}</p>
                                    {/if}
                                    {#if explanation.unexplainedCash.length > 0}
                                        <p>{$t(`${P}unexplained`)} {@render amountList(explanation.unexplainedCash)}</p>
                                    {/if}
                                    {#each explanation.notes as note, index (index)}
                                        <p class="flex items-start gap-1.5 text-amber-700 dark:text-amber-300" data-testid="gapfix-note" data-code={note.code}><AlertTriangle size={12} class="mt-0.5 shrink-0" /> {noteText(note)}</p>
                                    {/each}
                                </div>
                            {/if}

                            {#if checkpoint.proposals.length > 0}
                                <ul class="divide-y divide-gray-100 border-t border-gray-100 dark:divide-slate-700 dark:border-slate-700">
                                    {#each checkpoint.proposals as proposal (proposal.key)}
                                        {@const facts = proposalFacts(proposal)}
                                        {@const isSelected = selected.has(proposal.key)}
                                        <li class="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-sm {isSelected ? '' : 'opacity-60'}" data-testid="gapfix-proposal" data-key={proposal.key} data-type={facts.type} data-date={facts.date} data-selected={String(isSelected)}>
                                            <input type="checkbox" class="h-4 w-4 rounded border-gray-300 text-libre-green focus:ring-libre-green dark:border-slate-600" checked={isSelected} onchange={() => onToggle(proposal.key)} aria-label={$t(`${P}toggle`)} data-testid="gapfix-proposal-toggle" />
                                            <span class="font-medium text-gray-800 dark:text-gray-100">{typeLabel(facts.type)}</span>
                                            <span class="text-gray-500 dark:text-gray-400">{formatIsoDay(facts.date)}</span>
                                            {#if facts.assetId !== null}
                                                <span class="text-gray-700 dark:text-gray-200">{assetName(facts.assetId)}</span>
                                            {/if}
                                            {#if facts.quantity !== null}
                                                <span class="font-mono">{signedQuantity(facts.quantity)}</span>
                                            {/if}
                                            {#if facts.cash !== null}
                                                <span class="font-mono"><CurrencyAmount amount={facts.cash.amount} code={facts.cash.code} options={{showSign: true}} /></span>
                                            {/if}
                                            {#if proposal.needsCost}
                                                <span class="rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">{$t(`${P}costToEnter`)}</span>
                                            {/if}
                                            <span class="ml-auto rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[10px] text-gray-600 dark:bg-slate-700 dark:text-gray-300">gap_fix</span>
                                        </li>
                                    {/each}
                                </ul>
                            {/if}
                        </div>
                    {/each}

                    {#each group.verifications as verification (verification.key)}
                        <div class="rounded-lg border px-3 py-2 text-sm {verification.ok ? 'border-emerald-200 dark:border-emerald-900/60' : 'border-red-200 dark:border-red-900/60'}" data-testid="gapfix-verification" data-as-of={verification.asOf} data-ok={String(verification.ok)}>
                            <div class="flex flex-wrap items-center justify-between gap-2">
                                <span class="text-gray-800 dark:text-gray-100">{$t(`${P}verificationTitle`, {values: {date: formatIsoDay(verification.asOf)}})}</span>
                                {#if verification.ok}
                                    <span class="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300"><CheckCircle size={14} /> {$t(`${P}verificationOk`)}</span>
                                {:else}
                                    <span class="inline-flex items-center gap-1 text-xs font-semibold text-red-700 dark:text-red-300"><XCircle size={14} /> {$t(`${P}verificationKo`)}</span>
                                {/if}
                            </div>
                            {#if !verification.ok}
                                <table class="mt-2 w-full text-sm">
                                    <tbody>
                                        {#each verification.cash as row, index (index)}
                                            <tr data-testid="gapfix-verification-cash-row" data-currency={row.currency} data-difference={row.difference}>
                                                <td class="py-1 pr-3 text-gray-700 dark:text-gray-200">{$t(`${P}cashLabel`, {values: {currency: row.currency}})}</td>
                                                <td class="py-1 text-right font-mono">LibreFolio <CurrencyAmount amount={Number(row.librefolio)} code={row.currency} /></td>
                                                <td class="py-1 text-right font-mono">{$t(`${P}bank`)} <CurrencyAmount amount={Number(row.bank)} code={row.currency} /></td>
                                                <td class="py-1 text-right font-mono"><CurrencyAmount amount={Number(row.difference)} code={row.currency} options={{showSign: true}} /></td>
                                            </tr>
                                        {/each}
                                    </tbody>
                                </table>
                                <p class="mt-1 text-xs text-gray-600 dark:text-gray-300">{$t(`${P}verificationKoHint`)}</p>
                            {/if}
                        </div>
                    {/each}
                </div>
            {/if}
        </section>
    {/each}

    <p class="flex items-start gap-1.5 text-xs text-gray-500 dark:text-gray-400" data-testid="gapfix-info-hidden-titles"><Info size={14} class="mt-0.5 shrink-0" /> {$t(`${P}hiddenTitles`)}</p>
</div>
