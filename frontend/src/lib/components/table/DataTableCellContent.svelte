<script lang="ts">
    /**
     * DataTable — the content of one cell: the switch over the kinds of `CellContent`. The footer reuses it, since
     * `FooterCellContent` (text, number or HTML) is a subset of `CellContent`.
     *
     * Cut out of `DataTable.svelte` (release 1.3, Y2): the markup and its rules moved verbatim. The `td`, its
     * classes, its sticky offset and the row's handlers stay in the parent.
     */
    import {t} from '$lib/i18n';
    import {formatBytes} from '$lib/utils/files/upload';
    import {decimalArrowStep, normalizeDecimalInput} from '$lib/utils/core/parseDecimalInput';
    import {ExternalLink, ImageIcon} from 'lucide-svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import Switch from '$lib/components/ui/input/Switch.svelte';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import type {CellContent} from './types';
    import {formatCellDate} from './dataTableLogic';

    let {cellContent}: {cellContent: CellContent} = $props();

    /** A decimal number written out, as `normalizeDecimalInput` leaves it: what an amount cell hands over. */
    const DECIMAL_TEXT = /^-?\d+(\.\d+)?$/;
    /** The amount typed in an `editable-amount` cell is not a number: nothing is handed over until it is. */
    let amountInvalid = $state(false);

    /** Handle image load error — hide image and show fallback */
    function handleImageError(e: Event) {
        const img = e.currentTarget as HTMLImageElement;
        img.style.display = 'none';
        img.nextElementSibling?.classList.remove('hidden');
    }
</script>

{#if typeof cellContent === 'string' || typeof cellContent === 'number'}
    {cellContent}
{:else if cellContent && typeof cellContent === 'object' && 'type' in cellContent}
    {#if cellContent.type === 'icon-text'}
        <div class="cell-icon-text">
            <div class="cell-icon-box">
                <cellContent.icon size={16} class={cellContent.iconClass || ''} />
            </div>
            <span>{cellContent.text}</span>
        </div>
    {:else if cellContent.type === 'badge'}
        <span class="cell-badge {cellContent.variant}" class:custom-style={cellContent.customStyle} style={cellContent.customStyle || undefined} data-badge-variant={cellContent.variant}>{cellContent.text}</span>
    {:else if cellContent.type === 'date'}
        {formatCellDate(cellContent.value, cellContent.format, {today: $t('date.today') || 'Today', yesterday: $t('date.yesterday') || 'Yesterday'})}
    {:else if cellContent.type === 'size'}
        {formatBytes(cellContent.bytes)}
    {:else if cellContent.type === 'link'}
        <a href={cellContent.href} class="cell-link" target={cellContent.external ? '_blank' : undefined} rel={cellContent.external ? 'noopener noreferrer' : undefined}>
            {cellContent.text}
            {#if cellContent.external}
                <ExternalLink size={12} />
            {/if}
        </a>
    {:else if cellContent.type === 'custom'}
        {@const CustomComponent = cellContent.component}
        <CustomComponent {...cellContent.props} />
    {:else if cellContent.type === 'image'}
        <div class="cell-image-text">
            <div class="cell-image" class:circle={cellContent.circle} style="width:{cellContent.size || 32}px;height:{cellContent.size || 32}px;">
                <img src={cellContent.src} alt={cellContent.alt} width={cellContent.size || 32} height={cellContent.size || 32} loading="lazy" onerror={handleImageError} />
                <span class="image-fallback hidden">
                    {#if cellContent.fallbackIcon}
                        {@const FallbackIcon = cellContent.fallbackIcon}
                        <FallbackIcon size={cellContent.size ? cellContent.size * 0.6 : 20} />
                    {:else}
                        <ImageIcon size={cellContent.size ? cellContent.size * 0.6 : 20} />
                    {/if}
                </span>
            </div>
            {#if cellContent.text}
                <span class="cell-image-label">{cellContent.text}</span>
            {/if}
        </div>
    {:else if cellContent.type === 'editable-number'}
        <!-- type="text" + manual normalisation: a native number input is
             parsed against the browser locale, so "5,9" typed on an Italian
             keyboard arrives here as an empty string and the digits vanish
             as the user types. -->
        <input
            type="text"
            inputmode="decimal"
            autocomplete="off"
            class="cell-editable-number"
            value={cellContent.value ?? ''}
            placeholder={cellContent.placeholder ?? ''}
            oninput={(e) => {
                const typed = e.currentTarget.value;
                if (typed === '') {
                    cellContent.onchange(null);
                    return;
                }
                // Half-typed decimals ("5," / "5.") are left alone: committing
                // them would push a reformatted value back into the input and
                // eat the separator the user just pressed.
                if (typed.includes(',') || typed.endsWith('.')) return;
                let num = Number(normalizeDecimalInput(typed));
                if (!Number.isFinite(num)) return;
                if (cellContent.min !== undefined && num < cellContent.min) num = cellContent.min;
                if (cellContent.max !== undefined && num > cellContent.max) num = cellContent.max;
                cellContent.onchange(num);
            }}
            onblur={(e) => {
                const raw = normalizeDecimalInput(e.currentTarget.value);
                if (raw === '') {
                    cellContent.onchange(null);
                    return;
                }
                let num = Number(raw);
                if (!Number.isFinite(num)) return;
                if (cellContent.min !== undefined && num < cellContent.min) num = cellContent.min;
                if (cellContent.max !== undefined && num > cellContent.max) num = cellContent.max;
                e.currentTarget.value = String(num);
                cellContent.onchange(num);
            }}
            onkeydown={(e) => {
                if (e.key === 'Enter') {
                    e.currentTarget.blur();
                    return;
                }
                const stepped = decimalArrowStep(e, e.currentTarget.value, typeof cellContent.step === 'number' ? cellContent.step : 1);
                if (stepped === null) return;
                let num = Number(stepped);
                if (!Number.isFinite(num)) return;
                if (cellContent.min !== undefined && num < cellContent.min) num = cellContent.min;
                if (cellContent.max !== undefined && num > cellContent.max) num = cellContent.max;
                e.currentTarget.value = String(num);
                cellContent.onchange(num);
            }}
            onclick={(e) => e.stopPropagation()}
        />
    {:else if cellContent.type === 'editable-text'}
        {#snippet textInput()}
            <input
                type="text"
                class="cell-editable-text"
                data-testid="cell-editable-text"
                value={cellContent.value}
                placeholder={cellContent.placeholder ?? ''}
                maxlength={cellContent.maxLength}
                onblur={(e) => cellContent.onchange(e.currentTarget.value)}
                onkeydown={(e) => {
                    if (e.key === 'Enter') e.currentTarget.blur();
                }}
                onclick={(e) => e.stopPropagation()}
            />
        {/snippet}
        {#if cellContent.unit}
            <span class="cell-editable-text-with-unit">
                {@render textInput()}
                <span class="cell-editable-text-unit" data-testid="cell-editable-text-unit">{cellContent.unit}</span>
            </span>
        {:else}
            {@render textInput()}
        {/if}
    {:else if cellContent.type === 'editable-select'}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="cell-editable-select-wrapper" onclick={(e) => e.stopPropagation()}>
            <SimpleSelect
                value={cellContent.value}
                options={cellContent.options}
                placeholder={cellContent.placeholder}
                compact
                showChevron={false}
                dropdownPosition="auto"
                testId={cellContent.testId}
                optionTestId={cellContent.testId ? (option) => `${cellContent.testId}-option-${option.value}` : undefined}
                onchange={(v) => cellContent.onchange(v)}
            />
        </div>
    {:else if cellContent.type === 'editable-checkbox'}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="cell-checkbox-wrapper flex justify-center" onclick={(e) => e.stopPropagation()}>
            <!-- colour: closest role, to review: the on track was emerald-500 (a success green); switch role bg-lf-checked, alt bg-lf-success -->
            <Switch
                size="sm"
                semantics="pressed"
                label="Toggle"
                checked={cellContent.value}
                disabled={cellContent.disabled}
                onchange={(next) => {
                    if (!cellContent.disabled) cellContent.onchange(next);
                }}
            />
        </div>
    {:else if cellContent.type === 'editable-date'}
        <!-- The app's own date field, never a native date input: that one follows the browser's language, not the app's
             (nativeDateInput.gate.test.ts). Future dates allowed: a maturity is one. -->
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="cell-editable-date" onclick={(e) => e.stopPropagation()}>
            <SingleDatePicker value={cellContent.value ?? ''} label="" compact inputStyle clearable allowFuture testid="cell-editable-date" onchange={(date) => cellContent.onchange(date === '' ? null : date)} />
        </div>
    {:else if cellContent.type === 'editable-amount'}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="cell-editable-amount" onclick={(e) => e.stopPropagation()}>
            <!-- type="text" + manual normalisation, as editable-number; the amount stays decimal text, never a float -->
            <input
                type="text"
                inputmode="decimal"
                autocomplete="off"
                class="cell-editable-number"
                value={cellContent.amount ?? ''}
                placeholder={cellContent.placeholder ?? ''}
                aria-label={cellContent.ariaLabel}
                aria-invalid={amountInvalid ? 'true' : undefined}
                data-testid="cell-editable-amount-value"
                oninput={() => (amountInvalid = false)}
                onblur={(e) => {
                    const raw = normalizeDecimalInput(e.currentTarget.value);
                    if (raw === '') {
                        cellContent.onchange({amount: null, currency: cellContent.currency});
                        return;
                    }
                    if (!DECIMAL_TEXT.test(raw)) {
                        amountInvalid = true;
                        return;
                    }
                    e.currentTarget.value = raw;
                    cellContent.onchange({amount: raw, currency: cellContent.currency});
                }}
                onkeydown={(e) => {
                    if (e.key === 'Enter') e.currentTarget.blur();
                }}
            />
            <div class="cell-editable-amount-currency">
                <SimpleSelect
                    value={cellContent.currency ?? ''}
                    options={cellContent.currencies}
                    compact
                    showChevron={false}
                    dropdownPosition="auto"
                    ariaLabel={cellContent.currencyAriaLabel}
                    testId="cell-editable-amount-currency"
                    optionTestId={(option) => `cell-editable-amount-currency-option-${option.value}`}
                    onchange={(v) => cellContent.onchange({amount: cellContent.amount, currency: v || null})}
                />
            </div>
        </div>
    {:else if cellContent.type === 'html'}
        {#if cellContent.tooltip}
            <Tooltip text={cellContent.tooltip.text ?? ''} html={cellContent.tooltip.html ?? ''} position={cellContent.tooltip.position ?? 'top'} maxWidth={cellContent.tooltip.maxWidth ?? '320px'}>
                {#if cellContent.onClick}
                    <button
                        type="button"
                        class="cursor-pointer"
                        data-testid={cellContent.testId}
                        onclick={(event) => {
                            event.stopPropagation();
                            cellContent.onClick?.();
                        }}
                    >
                        {@html cellContent.html}
                    </button>
                {:else}
                    <span>{@html cellContent.html}</span>
                {/if}
            </Tooltip>
        {:else if cellContent.onClick}
            <button
                type="button"
                class="cursor-pointer"
                data-testid={cellContent.testId}
                onclick={(event) => {
                    event.stopPropagation();
                    cellContent.onClick?.();
                }}
            >
                {@html cellContent.html}
            </button>
        {:else}
            {@html cellContent.html}
        {/if}
    {/if}
{/if}

<style>
    /* Image cell */
    .cell-image-text {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        min-width: 0;
    }

    .cell-image-label {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        min-width: 0;
        text-align: left;
    }

    .cell-image {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        border-radius: 0.25rem;
        background: var(--lf-surface-neutral);
        flex-shrink: 0;
        min-width: 0;
    }

    .cell-image.circle {
        border-radius: 50%;
    }

    .cell-image img {
        object-fit: cover;
        display: block;
    }

    .cell-image .image-fallback {
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--lf-text-muted);
    }

    .cell-image :global(.hidden) {
        display: none !important;
    }

    /* Cell content types */
    .cell-icon-text {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        min-width: 0;
    }

    .cell-icon-text :global(svg) {
        flex-shrink: 0;
    }

    /* Fixed-size box for icon, matches .cell-image dimensions for column alignment */
    .cell-icon-box {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        width: 32px;
        height: 32px;
        min-width: 32px;
        color: var(--lf-text-muted);
    }

    .cell-icon-text span {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        min-width: 0;
        text-align: left;
    }

    .cell-badge {
        display: inline-block;
        padding: 0.125rem 0.5rem;
        font-size: 0.75rem;
        font-weight: 500;
        border-radius: 9999px;
    }

    .cell-badge.default {
        background: var(--lf-surface-neutral);
        color: var(--lf-text-secondary);
    }

    .cell-badge.success {
        background: var(--lf-success-soft);
        color: var(--lf-success-on-soft);
    }

    .cell-badge.warning {
        background: var(--lf-warning-soft);
        color: var(--lf-warning-on-soft);
    }

    .cell-badge.error {
        background: var(--lf-danger-soft);
        color: var(--lf-danger-on-soft);
    }

    .cell-badge.info {
        background: var(--lf-info-soft);
        color: var(--lf-info-on-soft);
    }

    /* Custom styled badge (e.g., broker colors) */
    .cell-badge.custom-style {
        background: var(--broker-bg, var(--lf-surface-neutral));
        color: var(--broker-text, var(--lf-text-secondary));
    }

    :global(.dark) .cell-badge.custom-style {
        background: var(--broker-dark-bg, var(--lf-surface-neutral));
        color: var(--broker-dark-text, var(--lf-text-secondary));
    }

    .cell-link {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        color: var(--lf-link);
        text-decoration: none;
    }

    .cell-link:hover {
        text-decoration: underline;
    }

    /* Editable number cell */
    .cell-editable-number {
        width: 100%;
        max-width: 120px;
        padding: 0.25rem 0.375rem;
        font-size: 0.8125rem;
        font-family: ui-monospace, monospace;
        border: 1px solid var(--lf-border-input);
        border-radius: 4px;
        background: var(--lf-surface-field);
        color: var(--lf-text-primary);
        outline: none;
        transition: border-color 0.15s;
    }

    .cell-editable-number:focus {
        border-color: var(--lf-focus);
        box-shadow: 0 0 0 1px color-mix(in oklab, var(--lf-focus) 25%, transparent);
    }

    /* Editable text cell */
    .cell-editable-text {
        width: 100%;
        padding: 0.25rem 0.375rem;
        font-size: 0.8125rem;
        border: 1px solid var(--lf-border-input);
        border-radius: 4px;
        background: var(--lf-surface-field);
        color: var(--lf-text-primary);
        outline: none;
        transition: border-color 0.15s;
    }

    /* A fixed unit beside the field (plan 68, E10c3): «0.19 %», «6.8 years» */
    .cell-editable-text-with-unit {
        display: flex;
        align-items: center;
        gap: 0.375rem;
    }

    .cell-editable-text-unit {
        flex-shrink: 0;
        font-size: 0.8125rem;
        color: var(--lf-text-muted);
        white-space: nowrap;
    }

    .cell-editable-text:focus {
        border-color: var(--lf-focus);
        box-shadow: 0 0 0 1px color-mix(in oklab, var(--lf-focus) 25%, transparent);
    }

    /* Editable date cell (plan 68, E10a): SingleDatePicker in its input style, as wide as a date needs */
    .cell-editable-date {
        min-width: 9.5rem;
        max-width: 12rem;
    }

    /* Editable amount cell (plan 68, E10a): the number cell and a currency choice side by side */
    .cell-editable-amount {
        display: flex;
        align-items: center;
        gap: 0.375rem;
    }

    .cell-editable-amount .cell-editable-number[aria-invalid='true'] {
        border-color: var(--lf-danger);
    }

    .cell-editable-amount-currency {
        min-width: 5.5rem;
        position: relative;
    }

    .cell-editable-number::placeholder,
    .cell-editable-text::placeholder {
        color: var(--lf-text-placeholder);
    }

    /* Editable select cell (SimpleSelect wrapper) */
    .cell-editable-select-wrapper {
        width: 100%;
        position: relative;
        /* No z-index here: avoids creating a stacking context that would
           trap the fixed-positioned dropdown below the sticky actions column */
    }

    /* When the dropdown is actually open (focus-within on the row),
       the row z-index bump in tbody tr:focus-within handles visibility */
</style>
