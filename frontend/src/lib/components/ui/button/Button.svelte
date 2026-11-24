<!--
  The standard button (project 85, BTN-0): the recipe (`buttonClasses`) and the behaviour (`pressable`) together, with
  the right names for the properties. Tap = action on release; long press = the name, no action; mouse rest = the
  name; Tab = the name. The name shows only when the word is out of view, or with a help or a reason.

  - `label` is mandatory: the name for everyone (`aria-label` when the word is not the label) and the tooltip's text.
  - Disabled without a reason → native `disabled`, except an icon (`display` `icon` or `auto`): `aria-disabled`, and the
    first tap, click or keyboard focus shows its name (an icon's name must reach the finger even while it is off; the
    `display` decides, not the measured width, so tests stay deterministic). Disabled with a `reason` →
    `aria-disabled`, reachable, the reason at the first tap, click or keyboard focus; `reasonCode` is published as
    `data-disabled-reason` for the tests. Either way the click is stopped (`preventDefault`: a `submit` does not send).
  - `busy` → `aria-busy` and `aria-disabled`, never native `disabled` (the focus stays); the icon becomes the spinner
    without changing width, clicks are stopped (a `submit` and the Enter of a field included); `busyLabel`
    replaces the word meanwhile.
  - `pressed` → a toggle (`aria-pressed`); `menu` → `aria-haspopup`, `aria-expanded`, the ▾, the snippet rendered
    right after the button while `open`.
  - `href` → an `<a>` with the same look; its long press stays the browser's (open in a new tab, copy the link).
  - BTN-2·0 (the consultant's C1–C9): `tone` (a state's colour: `ghost` in it, the `chip` of a banner, the `pressed`
    fill), `tint` (on a fill of that state), `pill`, `size="xs"`, `truncate` (the word cuts, and the name shows while it
    is cut), `dense` (24 px target), `expanded` (a disclosure: `aria-expanded` and a turning ▾; never with `menu`),
    `leading` (a logo or a flag instead of the icon) and `children` (a rich word: `label` stays the name, always in
    `aria-label`). Inside a `ButtonGroup` the button is a segment.
  - `class` takes size and position only (`w-full`, `ml-auto`), never a colour: the gate refuses colour roles there.
  - Every `data-*` (the `data-testid` first) lands on the `<button>` itself.
-->
<script lang="ts">
    import type {Component, Snippet} from 'svelte';
    import {ChevronDown, LoaderCircle} from 'lucide-svelte';
    import {buttonClasses, ICON_PX, WORD_HIDDEN_BELOW, type ButtonDisplay, type ButtonSize, type ButtonTone, type ButtonVariant, type WordThreshold} from './buttonClasses';
    import {insideButtonGroup} from './buttonGroup';
    import {pressable, type TipPosition} from './pressable.svelte';

    interface Props {
        /** Mandatory: the name, `aria-label` when the word in view is not it, the tooltip's text. */
        label: string;
        /** A shorter word shown beside the icon (the floating bar of DataTableToolbar); the full name in the tooltip. */
        shortLabel?: string;
        /** A lucide icon. */
        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- lucide-svelte icons are legacy class components
        icon?: Component<any> | (new (...args: any[]) => any);
        /**
         * `text`, `icon-text` (default with an icon), `icon`, `auto` (the word hides below `hideWordBelow`, or while
         * `compact`). `auto` never picks a width of its own and measures nothing: it carries the rule the button already
         * had — the page toolbar's decision (`compact`) or the class it was written with (`hideWordBelow`). With neither,
         * the word always shows.
         */
        display?: ButtonDisplay;
        /** `display="auto"`: the class the button had, as a threshold: `sm` is `hidden sm:inline`, `@2xl` a container under 42rem. */
        hideWordBelow?: WordThreshold;
        /** `display="auto"`: the parent decided the word hides — `compact={!showActionLabels}` of PageToolbar (`createResponsiveLayout`). */
        compact?: boolean;
        variant?: ButtonVariant;
        size?: ButtonSize;
        /** A state's colour: `ghost` in it, the `chip` of a banner (mandatory there), the `pressed` fill. */
        tone?: ButtonTone;
        /** The button stands on a fill of that state (a toast, a banner): the fill's text, the hover a step down. */
        tint?: ButtonTone;
        /** Fully rounded. */
        pill?: boolean;
        /** The word may cut; the name shows (long press, rest, Tab) while it is cut. */
        truncate?: boolean;
        /** Inside a field or beside a neighbour: the finger's target is 24 px, not 40. */
        dense?: boolean;
        /** A disclosure: `aria-expanded` and a ▾ that turns while open. Never with `menu`, which has its own. */
        expanded?: boolean;
        /** What stands before the word instead of an icon: a logo, a flag (hidden from the reader: `label` names it). */
        leading?: Snippet;
        /** A rich word (HTML, flags) instead of the plain one: `label` stays the name, and `aria-label` carries it. */
        children?: Snippet;
        /** An explanation in the tooltip, under the name (plain text; `math` for `$…$`). */
        help?: string;
        math?: boolean;
        /** Disabled without a reason: native `disabled`; an icon (`display` `icon`/`auto`) stays reachable for its name. */
        disabled?: boolean;
        /** Disabled with a reason: `aria-disabled`, the reason shown at the first tap, click or keyboard focus. */
        reason?: string;
        /** A stable code for the reason, published as `data-disabled-reason` (tests read it, never the text). */
        reasonCode?: string;
        busy?: boolean;
        /** The word while busy («Saving…»). */
        busyLabel?: string;
        /** A toggle: `aria-pressed`, drawn as the selected control when true. */
        pressed?: boolean;
        /** A button that opens a menu: the menu, rendered right after the button while `open`. */
        menu?: Snippet<[{close: () => void; anchor: HTMLElement | undefined}]>;
        open?: boolean;
        /** A link: rendered as `<a>`. */
        href?: string;
        target?: string;
        rel?: string;
        type?: 'button' | 'submit' | 'reset';
        onclick?: (event: MouseEvent) => void;
        /** Mouse and keyboard side of the tooltip; a finger always opens it above (below without room). */
        tipPosition?: TipPosition;
        /** Size and position only (`w-full`, `ml-auto`): never a colour. */
        class?: string;
        /** A badge after the word (a count). */
        badge?: Snippet;
        /** The element itself, for a parent that anchors a menu or a focus on it. */
        element?: HTMLElement;
        id?: string;
        form?: string;
        tabindex?: number;
        [key: `data-${string}`]: string | number | boolean | undefined | null;
        [key: `aria-${string}`]: string | number | boolean | undefined | null;
    }

    let {
        label,
        shortLabel,
        icon: Icon,
        display,
        hideWordBelow,
        compact = false,
        variant = 'secondary',
        size = 'md',
        tone,
        tint,
        pill = false,
        truncate = false,
        dense = false,
        expanded,
        leading,
        children,
        help,
        math = false,
        disabled = false,
        reason,
        reasonCode,
        busy = false,
        busyLabel,
        pressed,
        menu,
        open = $bindable(false),
        href,
        target,
        rel,
        type = 'button',
        onclick,
        tipPosition,
        class: className = '',
        badge,
        element = $bindable(),
        ...rest
    }: Props = $props();

    /** Checked once, at mount: a caller passes either a menu or a disclosure, never both, and never switches. */
    function assertMenuOrDisclosure(): void {
        if (menu && expanded !== undefined) throw new Error('Button: `expanded` and `menu` never go together — `menu` has its own aria-expanded');
    }
    assertMenuOrDisclosure();

    /** Inside a `ButtonGroup`: a segment. */
    const segment = insideButtonGroup();
    let shown = $derived<ButtonDisplay>(display ?? (Icon || leading ? 'icon-text' : 'text'));
    /** Disabled with a reason: reachable, never natively disabled. */
    let offWithReason = $derived(!!reason);
    /** Disabled without a reason, but an icon: reachable for its name (decided by `display`, never by the width). */
    let offIcon = $derived(disabled && !reason && (display === 'icon' || display === 'auto'));
    /** Off for the user and still in the tab order: `aria-disabled` instead of the native attribute. */
    let reachableOff = $derived(offWithReason || offIcon || busy);
    let nativeDisabled = $derived(disabled && !reachableOff);
    let word = $derived(busy && busyLabel ? busyLabel : (shortLabel ?? label));
    /** The word's own class: hidden for an icon, below the threshold for `auto`. */
    let hideClass = $derived(shown === 'auto' ? (compact ? 'hidden' : hideWordBelow ? WORD_HIDDEN_BELOW[hideWordBelow] : '') : '');
    let wordClass = $derived(truncate ? `${hideClass} truncate`.trim() : hideClass);
    /** A rich word, unless the busy word takes its place. */
    let richWord = $derived(!!children && !(busy && busyLabel));
    let hasWord = $derived(shown !== 'icon' && !(shown === 'auto' && compact));
    let iconOnly = $derived(shown === 'icon');
    let classes = $derived(`${buttonClasses({variant, size, shape: iconOnly ? 'icon' : 'default', pressed, tone, tint, segment, pill, truncate, dense})} ${className}`.trim());
    let px = $derived(ICON_PX[size]);
    /** The accessible name: given whenever the word in view is not the label, or may be hidden. */
    let ariaLabel = $derived(richWord ? label : shown === 'text' || shown === 'icon-text' ? (word === label ? undefined : label) : label);
    let ariaExpanded = $derived<'true' | 'false' | undefined>(menu ? (open ? 'true' : 'false') : expanded === undefined ? undefined : expanded ? 'true' : 'false');
    /** The ▾ of a menu or a disclosure, turned while open. */
    let chevron = $derived(menu ? open : expanded);

    let wordElement: HTMLSpanElement | undefined = $state(undefined);

    /** Whether the word is in view now (read at the moment the name would open). */
    function wordVisible(): boolean {
        // A cut word does not show the name: the name opens (C7). Measured when the name would open.
        if (truncate && wordElement && wordElement.scrollWidth > wordElement.clientWidth) return false;
        if (shown === 'text' || shown === 'icon-text') return richWord || shortLabel === undefined || shortLabel === label;
        if (!hasWord || !wordElement) return false;
        return wordElement.getClientRects().length > 0;
    }

    function press(event: MouseEvent) {
        if (menu) open = !open;
        onclick?.(event);
    }

    let pressOptions = $derived({
        label,
        help,
        math,
        reason,
        off: offIcon,
        busy,
        tipPosition,
        wordVisible,
        onpress: press,
    });
</script>

{#snippet content()}
    {#if busy}
        <LoaderCircle size={px} class="lf-btn-spin shrink-0" aria-hidden="true" />
    {:else if leading}
        <span class="inline-flex shrink-0 items-center" aria-hidden="true" data-lf-leading>{@render leading()}</span>
    {:else if Icon}
        <Icon size={px} class="shrink-0" aria-hidden="true" />
    {/if}
    {#if shown !== 'icon'}
        <span bind:this={wordElement} class={wordClass} data-lf-word>
            {#if richWord && children}{@render children()}{:else}{word}{/if}
        </span>
    {/if}
    {#if badge}
        {@render badge()}
    {/if}
    {#if chevron !== undefined}
        <ChevronDown size={px - 2} class="shrink-0 transition-transform {chevron ? 'rotate-180' : ''}" aria-hidden="true" data-lf-chevron />
    {/if}
{/snippet}

{#if href}
    <a bind:this={element} {href} {target} {rel} class={classes} aria-label={ariaLabel} aria-disabled={reachableOff ? 'true' : undefined} data-disabled-reason={offWithReason ? reasonCode : undefined} use:pressable={pressOptions} {...rest}>
        {@render content()}
    </a>
{:else}
    <button
        bind:this={element}
        {type}
        class={classes}
        disabled={nativeDisabled}
        aria-disabled={reachableOff ? 'true' : undefined}
        aria-busy={busy ? 'true' : undefined}
        aria-pressed={pressed === undefined ? undefined : pressed ? 'true' : 'false'}
        aria-haspopup={menu ? 'menu' : undefined}
        aria-expanded={ariaExpanded}
        aria-label={ariaLabel}
        data-disabled-reason={offWithReason ? reasonCode : undefined}
        use:pressable={pressOptions}
        {...rest}
    >
        {@render content()}
    </button>
    {#if menu && open}
        {@render menu({close: () => (open = false), anchor: element})}
    {/if}
{/if}
