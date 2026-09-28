<!--
  LabPopover — the dropdown shell of the laboratory's selection card.

  One shell for the card's menus (the holdings preset, the two filters, the "+"
  picker), so they open, close and look the same.

  The trigger lives inside the same root as the panel, and the outside press is
  measured against that root. A listener that only knows the panel closes it on
  the press that lands on the trigger, and the click that follows opens it
  again: the menu could not be closed from the button that opened it.

  It closes on a **completed click** outside — not on the press. Closing on
  `pointerdown` removed the panel between the press and the release: the page
  got shorter and scrolled back, the release landed on whatever slid under the
  pointer, and no click reached the button that was pressed. Moving from one
  open filter menu to the other took two presses (F-6, `risk-lab.spec.ts`). A
  click whose press began inside the panel — a text selection dragged out of the
  search box — is not an outside click either.

  It also closes on Escape, and through the `close` the content receives. It
  opens under the trigger, and moves to the trigger's right edge when it would
  cross the viewport's.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';

    interface Props {
        open?: boolean;
        trigger: Snippet<[{open: boolean; toggle: () => void}]>;
        children: Snippet<[{close: () => void}]>;
        panelClass?: string;
        testId?: string;
    }

    let {open = $bindable(false), trigger, children, panelClass = '', testId}: Props = $props();

    let root = $state<HTMLDivElement>();
    let panel = $state<HTMLDivElement>();
    let alignEnd = $state(false);
    /** Where the press that the next click completes began: inside this popover, or not. */
    let pressStartedInside = false;

    function toggle(): void {
        open = !open;
    }

    function close(): void {
        open = false;
    }

    $effect(() => {
        if (!open || !panel) {
            alignEnd = false;
            return;
        }
        const rect = panel.getBoundingClientRect();
        alignEnd = rect.right > window.innerWidth - 8;
    });

    function handlePointerDown(event: PointerEvent): void {
        pressStartedInside = !!root && root.contains(event.target as Node);
    }

    /**
     * Captured, so it runs before the target's own handler and a `stopPropagation`
     * there cannot hide the click from an open menu. A click made from the keyboard
     * (`detail` 0) completes no press, so the press flag does not apply to it.
     */
    function handleClick(event: MouseEvent): void {
        const startedInside = event.detail !== 0 && pressStartedInside;
        pressStartedInside = false;
        if (!open || !root || startedInside) return;
        if (!root.contains(event.target as Node)) open = false;
    }

    function handleKeydown(event: KeyboardEvent): void {
        if (open && event.key === 'Escape') open = false;
    }
</script>

<svelte:window onpointerdowncapture={handlePointerDown} onclickcapture={handleClick} onkeydown={handleKeydown} />

<div class="relative inline-flex" bind:this={root}>
    {@render trigger({open, toggle})}
    {#if open}
        <div bind:this={panel} class="absolute top-full z-40 mt-1 rounded-lg border border-gray-200 bg-white shadow-lg dark:border-slate-600 dark:bg-slate-800 {alignEnd ? 'right-0' : 'left-0'} {panelClass}" data-testid={testId}>
            {@render children({close})}
        </div>
    {/if}
</div>
