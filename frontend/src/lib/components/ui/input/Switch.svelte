<!--
  Switch — the app's one on/off lever: a track and a round knob, drawn with the colour roles of the switch (the track
  `bg-lf-switch-off` / `bg-lf-checked`, the knob `bg-lf-switch-knob-off` with its `border-lf-input` edge when off, and
  `bg-lf-switch-knob-on` when on). It replaces the copies that DataEditor, SettingToggle, the asset modal, the import
  compare modal, the chart settings, the table cell, the scheduled-investment editor and the gap-fix step each carried.

  It is controlled: `checked` is the state, `onchange(next, event)` says what the user asked for, and the caller decides
  (a locked or saving state simply does not apply it).

  Two sizes: `md` (`h-6 w-11`, a form row) and `sm` (`h-5 w-9`, a table cell or a toolbar).

  Two ways to tell assistive technology what it is: `semantics="switch"` (the default) is `role="switch"` with
  `aria-checked`; `semantics="pressed"` keeps a plain toggle button with `aria-pressed`, for the screens whose tests and
  specs read that attribute.

  Three states, for a switch that stands for several others: pass `mixed` (true: some of them are on). It is then a
  `role="checkbox"` (`aria-checked="mixed"`: the role `switch` has no third state), its knob rests in the middle with a dash,
  and a click from the mixed state asks for `true`.

  A disabled switch is dimmed and shows the not-allowed cursor; `dim={false}` keeps it undimmed, for a caller whose
  surroundings already dim it (a disabled row).

  Anything else goes straight to the `<button>` (`data-*`, `aria-describedby`, `id`, `onclick`…); the `data-testid` is
  `testId`. The name is `label` or `labelledby`: an `aria-label` passed any other way is overridden by them.
-->
<script lang="ts">
    import type {HTMLButtonAttributes} from 'svelte/elements';

    interface Props extends Omit<HTMLButtonAttributes, 'onchange' | 'class' | 'type' | 'role'> {
        /** The state shown. */
        checked: boolean;
        /** The switch stands for several: true when only some are on (`checked` is then ignored). Absent: two states. */
        mixed?: boolean;
        /** The user asked for `next`; `event` is the click, for a caller that must stop it. */
        onchange?: (next: boolean, event: MouseEvent) => void;
        /** `md`: `h-6 w-11`. `sm`: `h-5 w-9`. */
        size?: 'sm' | 'md';
        /** `switch`: `role="switch"` + `aria-checked`. `pressed`: `aria-pressed` on a plain button. */
        semantics?: 'switch' | 'pressed';
        /** The accessible name, when no visible label points at the switch through `labelledby`. */
        label?: string;
        /** The id of the visible label. */
        labelledby?: string;
        testId?: string;
        /** Dim the switch when disabled (default). `false` for a caller whose surroundings already dim it. */
        dim?: boolean;
        /** Extra classes for the track: a layout concern (a margin), never a colour. */
        class?: string;
    }

    let {checked, mixed, onchange, size = 'md', semantics = 'switch', label, labelledby, testId, dim = true, disabled = false, class: extra = '', onclick, ...rest}: Props = $props();

    // Both sizes keep the knob centred on its track: 4 px from each end in `md`, 3 px / 4 px in `sm` (a 14 px knob on 36 px).
    let knobPosition = $derived(mixed ? (size === 'sm' ? 'translate-x-[11px]' : 'translate-x-3.5') : size === 'sm' ? (checked ? 'translate-x-[18px]' : 'translate-x-[3px]') : checked ? 'translate-x-6' : 'translate-x-1');
</script>

<button
    {...rest}
    type="button"
    role={semantics === 'switch' ? (mixed === undefined ? 'switch' : 'checkbox') : undefined}
    aria-checked={semantics === 'switch' ? (mixed ? 'mixed' : checked) : undefined}
    aria-pressed={semantics === 'pressed' ? checked : undefined}
    aria-label={label}
    aria-labelledby={labelledby}
    {disabled}
    data-testid={testId}
    onclick={(event) => {
        if (disabled) return;
        onclick?.(event);
        if (!event.defaultPrevented) onchange?.(mixed ? true : !checked, event);
    }}
    class="relative inline-flex shrink-0 items-center rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus {size === 'sm' ? 'h-5 w-9' : 'h-6 w-11'} {checked || mixed ? 'bg-lf-checked' : 'bg-lf-switch-off'} {disabled
        ? dim
            ? 'cursor-not-allowed opacity-50'
            : 'cursor-not-allowed'
        : 'cursor-pointer'} {extra}"
>
    <span class="relative inline-block transform rounded-full transition-transform {size === 'sm' ? 'h-3.5 w-3.5 shadow-sm' : 'h-4 w-4'} {knobPosition} {checked || mixed ? 'bg-lf-switch-knob-on' : 'border border-lf-input bg-lf-switch-knob-off'}">
        {#if mixed}<span class="absolute inset-x-1 top-1/2 h-0.5 -translate-y-1/2 rounded-full bg-lf-checked"></span>{/if}
    </span>
</button>
