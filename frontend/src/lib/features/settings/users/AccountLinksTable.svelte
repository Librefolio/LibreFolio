<!--
AccountLinksTable — one table of account links (lot UA3), on the shared DataTable: sorting, Excel-style column
filters, column visibility and widths (kept per table), pagination and, for the open links, the row actions menu.

The Users tab shows two: the open links, and the closed ones (used, expired, revoked) inside a folded panel. A link is
never shown itself: it is shown once, when it is created. Which link can be revoked is the backend's `revocable`.

Published state: `data-testid={testId}` on the root, with `data-count`; each row is `data-row-id={link.id}` (DataTable).
-->
<script lang="ts">
    import {X} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import type {ColumnDef, EnumOption, RowAction} from '$lib/components/table/types';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import AccountLinkTypeBadge from './AccountLinkTypeBadge.svelte';
    import AccountLinkStateCell from './AccountLinkStateCell.svelte';
    import type {AccountLink, AccountLinkPurpose, AccountLinkState} from './types';

    interface Props {
        links: AccountLink[];
        /** `open`: the links still usable, with their row actions; `closed`: used, expired or revoked. */
        variant: 'open' | 'closed';
        testId: string;
        isLoading?: boolean;
        onRevoke?: (link: AccountLink) => void;
    }

    let {links, variant, testId, isLoading = false, onRevoke}: Props = $props();

    let tableRef: DataTable<AccountLink> | undefined = $state();

    const PURPOSES: AccountLinkPurpose[] = ['invite', 'password_reset', 'email_verification', 'admin_setup', 'email_change'];
    const STATES = $derived<AccountLinkState[]>(variant === 'open' ? ['open'] : ['used', 'expired', 'revoked']);

    const purposeLabel = (purpose: AccountLinkPurpose) => $_(`settings.usersTab.links.purpose.${purpose}`);
    const stateLabel = (state: AccountLinkState) => $_(`settings.usersTab.links.state.${state}`);

    /** Whom the link is for: the account it acts on, else the address it carries, else anyone holding it (an invitation without an address). */
    function targetText(link: AccountLink): string {
        if (link.username) return link.email && link.purpose === 'email_change' ? `${link.username} → ${link.email}` : link.username;
        return link.email || $_('settings.usersTab.links.anyone');
    }

    function targetHtml(link: AccountLink): string {
        const nameHtml = `<span class="truncate" data-testid="account-link-target">${escapeHtml(targetText(link))}</span>`;
        const adminBadge = link.grants_admin ? `<span class="inline-flex shrink-0 items-center rounded-full border border-lf-info-line bg-lf-info-soft px-2 py-0.5 text-xs text-lf-info-on-soft" data-testid="account-link-admin">${escapeHtml($_('settings.usersTab.badges.admin'))}</span>` : '';
        return `<span class="flex min-w-0 items-center gap-1.5">${nameHtml}${adminBadge}</span>`;
    }

    const createdByText = (link: AccountLink) => link.created_by_username ?? '—';

    let columns = $derived.by<ColumnDef<AccountLink>[]>(() => [
        {
            id: 'type',
            header: () => $_('settings.usersTab.links.columns.type'),
            type: 'enum',
            enumOptions: PURPOSES.map<EnumOption>((purpose) => ({value: purpose, label: purposeLabel(purpose)})),
            width: 200,
            minWidth: 140,
            getValue: (link) => link.purpose,
            sortFn: (a, b) => purposeLabel(a.purpose).localeCompare(purposeLabel(b.purpose)),
            cell: (link) => ({type: 'custom', component: AccountLinkTypeBadge, props: {purpose: link.purpose}}),
        },
        {
            id: 'target',
            header: () => $_('settings.usersTab.links.columns.target'),
            type: 'text',
            width: 240,
            minWidth: 140,
            getValue: (link) => targetText(link),
            cell: (link) => ({type: 'html', html: targetHtml(link)}),
        },
        {
            id: 'createdBy',
            header: () => $_('settings.usersTab.links.columns.createdBy'),
            type: 'text',
            width: 150,
            minWidth: 100,
            getValue: (link) => createdByText(link),
            cell: (link) => createdByText(link),
        },
        {
            id: 'created',
            header: () => $_('settings.usersTab.links.columns.created'),
            type: 'date',
            width: 170,
            minWidth: 130,
            getValue: (link) => link.created_at,
            cell: (link) => ({type: 'date', value: link.created_at, format: 'datetime'}),
        },
        {
            id: 'expires',
            header: () => $_('settings.usersTab.links.columns.expires'),
            type: 'date',
            width: 170,
            minWidth: 130,
            getValue: (link) => link.expires_at,
            cell: (link) => ({type: 'date', value: link.expires_at, format: 'datetime'}),
        },
        {
            id: 'state',
            header: () => $_('settings.usersTab.links.columns.state'),
            type: 'enum',
            enumOptions: STATES.map<EnumOption>((state) => ({value: state, label: stateLabel(state)})),
            width: variant === 'open' ? 120 : 260,
            minWidth: 100,
            getValue: (link) => link.state,
            sortFn: (a, b) => stateLabel(a.state).localeCompare(stateLabel(b.state)),
            cell: (link) => ({type: 'custom', component: AccountLinkStateCell, props: {link}}),
        },
    ]);

    let rowActions = $derived<RowAction<AccountLink>[]>(
        variant === 'open' && onRevoke
            ? [
                  {
                      id: 'revoke',
                      icon: X,
                      label: () => $_('settings.usersTab.links.revoke'),
                      variant: 'danger',
                      visible: (link) => link.revocable,
                      testid: 'account-link-revoke',
                      onClick: (link) => onRevoke?.(link),
                  },
              ]
            : [],
    );
</script>

<div class="space-y-2" data-count={links.length} data-testid={testId}>
    <div class="flex justify-end">
        <ColumnVisibilityToggle {tableRef} />
    </div>
    <DataTable
        bind:this={tableRef}
        {columns}
        data={links}
        defaultPageSize={10}
        emptyMessage={variant === 'open' ? $_('settings.usersTab.links.empty') : $_('settings.usersTab.links.closedEmpty')}
        enableActions={variant === 'open'}
        enableSelection={false}
        getRowId={(link) => String(link.id)}
        {isLoading}
        {rowActions}
        storageKey={`settings.users.accountLinks.${variant}`}
    />
</div>
