<!--
  ModalEscapeLayersHarness — test-only host for the Escape stack inside a modal (Vitest + jsdom).

  A modal is the bottom layer; a row menu, or a select with its list open, is a layer on top of it.
  The harness stacks them the way the app does, each as its consumers mount it:

    - ModalBase as TransactionBulkModal opens it: no focus trap, `onRequestClose` passed straight
      through, so the spec reads the request itself rather than a modal it would have to close;
    - a ContextMenu mounted on demand — here by a button, the ⋮ path of a table row — and unmounted
      by its own `onClose`, as DataTable and AssetGroupStep do. `onMenuClose` reports every close,
      so a spec can prove the menu's own Escape listener ran;
    - a SearchSelect with its search box in the dropdown, and one with the search inline in its
      trigger (the layout of CurrencySearchSelect).

  The ids are the harness's own (`esc-*`), except `context-menu`, which ContextMenu fixes itself.
  Lives under `src/__tests__/`, which `vitest.config.ts` excludes from coverage.
-->
<script lang="ts">
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import ContextMenu, {type ContextMenuItem} from '$lib/components/ui/ContextMenu.svelte';
    import SearchSelect from '$lib/components/ui/select/SearchSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select/types';

    interface Props {
        onRequestClose?: () => void;
        onMenuClose?: () => void;
    }

    let {onRequestClose = () => {}, onMenuClose = () => {}}: Props = $props();

    const menuItems: ContextMenuItem[] = [
        {id: 'edit', label: 'Edit'},
        {id: 'remove', label: 'Remove'},
    ];

    const options: SelectOption[] = [
        {value: 'EUR', label: 'Euro'},
        {value: 'USD', label: 'US Dollar'},
        {value: 'JPY', label: 'Japanese Yen'},
    ];

    let menuOpen = $state(false);

    function closeMenu() {
        onMenuClose();
        menuOpen = false;
    }
</script>

<ModalBase open={true} {onRequestClose} testId="esc-modal" noTransition={true}>
    <div data-testid="esc-modal-body">
        <button type="button" data-testid="esc-menu-opener" onclick={() => (menuOpen = true)}>Actions</button>
        {#if menuOpen}
            <ContextMenu x={40} y={40} items={menuItems} anchorEl={null} onAction={() => {}} onClose={closeMenu} />
        {/if}
        <SearchSelect value="EUR" {options} testId="esc-select" />
        <SearchSelect value="EUR" {options} testId="esc-inline" inlineSearch={true} />
    </div>
</ModalBase>
