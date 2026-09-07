<!--
  AssetGroupStep.svelte — import wizard step "Unifica asset".

  Answers one question, before anything else in the wizard looks at instruments: *how many
  distinct securities are actually in these files, and under which code does each one go?*
  The wizard allocates a fake asset id per instrument **per file**, so the same BTP read from a
  holdings report and from a movements report arrives as two unrelated assets. Left alone, that
  becomes two duplicates in the database — and, worse, two indistinguishable entries in the
  correction step's asset picker, where half the rows silently land on half the instrument.

  Why it comes before the correction step and long before the database comparison: every later
  choice is made *on* this list. Unify afterwards and the same question gets asked twice.

  Three visual states, and the difference between them is who decided:
    · solid green  — the engine is sure (same ISIN, same ticker, same name) or the user said so;
    · dashed amber — the engine sees a resemblance it will not act on alone, and asks;
    · plain grey   — alone, nothing to decide.

  Every card is the same rectangle whatever it holds, and the list keeps extraction order: a
  merge must not make the page jump under the hand that caused it.

  Clicking a badge elects it: the leading ISIN is the one the asset will be quoted under, which
  for an Italian retail bond is emphatically *not* the placement (CUM) code it was issued with.
  The codes that lose stay on as other identifiers, so nothing the files knew is thrown away.

  The `⋮` menu is the primary interaction — keyboard-reachable and testable. Drag & drop is an
  accelerator layered on top of it, never the only way to do something.
-->
<script lang="ts">
    import {t} from 'svelte-i18n';
    import {ChevronsLeftRight, Database, FileText, MoreVertical, Pencil, RotateCcw, Scissors, Check, Star, X} from 'lucide-svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import ContextMenu, {type ContextMenuItem} from '$lib/components/ui/ContextMenu.svelte';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {clusterSignature, groupSignature, isPrimary, memberKey, movePartition, orderedIdentifiers, partitionOf, splitPartition, summariseLinks, type AssetGroup, type ExtractedAsset, type GroupPrimary, type IdentifierKind, type LinkSummary, type PrimaryMap} from '$lib/utils/assetGrouping';

    interface Props {
        groups: AssetGroup[];
        /** Transactions per fake asset id, so a group can show what it actually weighs. */
        txCounts?: Record<number, number>;
        /** Real asset ids already bound to a representative, enabling the inspect pencil. */
        resolvedIds?: Record<number, number>;
        /** The archive's own name for a bound group, which outranks anything the files called it. */
        resolvedNames?: Record<number, string>;
        /** The elected leading code of each kind, per group signature. */
        primaries?: PrimaryMap;
        /** True when the user has taken any decision here, enabling the reset. */
        touched?: boolean;
        /** A new partition to store as the user's override. */
        onpartition: (partition: string[][]) => void;
        /** The user accepted a proposal exactly as it stands. */
        onconfirm: (signature: string) => void;
        /** The user promoted one code to lead its kind. */
        onprimary: (signature: string, kind: IdentifierKind, value: string) => void;
        /** Discard every decision on this step and go back to the engine's proposal. */
        onreset: () => void;
        oninspect?: (realAssetId: number) => void;
    }

    let {groups, txCounts = {}, resolvedIds = {}, resolvedNames = {}, primaries = {}, touched = false, onpartition, onconfirm, onprimary, onreset, oninspect}: Props = $props();

    // =========================================================================
    // Menu
    // =========================================================================

    /**
     * The `⋮` menu runs in two phases: first the verbs, then — for "merge with" — the list of
     * possible destinations. A flat menu listing every target up front would be unreadable on an
     * import with thirty instruments.
     */
    let menuOpen = $state(false);
    let menuX = $state(0);
    let menuY = $state(0);
    let menuMember = $state<ExtractedAsset | null>(null);
    let menuPhase = $state<'verbs' | 'targets'>('verbs');
    let menuAnchor = $state<HTMLElement | null>(null);

    function groupOf(member: ExtractedAsset): AssetGroup | undefined {
        return groups.find((g) => g.members.some((m) => m.fakeAssetId === member.fakeAssetId));
    }

    function openMenu(event: MouseEvent, member: ExtractedAsset) {
        const target = event.currentTarget as HTMLElement;
        const rect = target.getBoundingClientRect();
        menuX = rect.left;
        menuY = rect.bottom + 4;
        menuAnchor = target;
        menuMember = member;
        menuPhase = 'verbs';
        menuOpen = true;
    }

    let menuItems = $derived.by((): ContextMenuItem[] => {
        const member = menuMember;
        if (!member) return [];
        const own = groupOf(member);
        if (menuPhase === 'targets') {
            const items: ContextMenuItem[] = groups
                .filter((g) => g.groupId !== own?.groupId)
                .map((g) => ({
                    id: `target:${memberKey(g.members[0])}`,
                    label: labelOfGroup(g),
                    testid: `asset-group-merge-target-${g.groupId}`,
                }));
            if (items.length === 0) items.push({id: 'noop', label: $t('importWizard.assetUnify.noTargets'), disabled: true});
            return items;
        }
        const items: ContextMenuItem[] = [{id: 'merge', label: $t('importWizard.assetUnify.mergeWith'), icon: ChevronsLeftRight as unknown as ContextMenuItem['icon'], testid: 'asset-group-menu-merge'}];
        if ((own?.members.length ?? 1) > 1) items.push({id: 'extract', label: $t('importWizard.assetUnify.extract'), icon: Scissors as unknown as ContextMenuItem['icon'], testid: 'asset-group-menu-extract'});
        return items;
    });

    function labelOfGroup(group: AssetGroup): string {
        const ids = orderedIdentifiers(group.members, primaries[groupSignature(group)]);
        const head = ids.names[0] ?? ids.isins[0] ?? ids.symbols[0] ?? `#${group.members[0]?.fakeAssetId}`;
        return group.members.length > 1 ? `${head} (${group.members.length})` : head;
    }

    function handleMenuAction(id: string) {
        const member = menuMember;
        if (!member) return;
        if (id === 'merge') {
            // Stay open, swap the list: the user asked "with what?" and answering means showing it.
            menuPhase = 'targets';
            return;
        }
        if (id === 'extract') {
            onpartition(splitPartition(partitionOf(groups), [memberKey(member)]));
            menuOpen = false;
            return;
        }
        if (id.startsWith('target:')) {
            onpartition(movePartition(partitionOf(groups), [memberKey(member)], id.slice('target:'.length)));
            menuOpen = false;
            return;
        }
        menuOpen = false;
    }

    // =========================================================================
    // Group-level actions
    // =========================================================================

    function confirmGroup(group: AssetGroup) {
        onconfirm(clusterSignature(group.members.map(memberKey)));
    }

    function splitGroup(group: AssetGroup) {
        onpartition(splitPartition(partitionOf(groups), group.members.map(memberKey)));
    }

    /**
     * Electing is a toggle only in one direction: a second click on the leader does nothing.
     * There is always exactly one leading code, so "unelect" would have to invent a replacement.
     */
    function elect(group: AssetGroup, kind: IdentifierKind, value: string) {
        onprimary(groupSignature(group), kind, value);
    }

    // =========================================================================
    // Drag & drop — an accelerator over the menu, never the only route
    // =========================================================================

    let draggingKey = $state<string | null>(null);
    let dropTarget = $state<string | null>(null);

    function onDragStart(event: DragEvent, member: ExtractedAsset) {
        draggingKey = memberKey(member);
        event.dataTransfer?.setData('text/plain', draggingKey);
        if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
    }

    function onDragOver(event: DragEvent, targetKey: string) {
        if (!draggingKey || draggingKey === targetKey) return;
        event.preventDefault();
        dropTarget = targetKey;
        if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
    }

    function onDrop(event: DragEvent, targetKey: string) {
        event.preventDefault();
        const source = draggingKey;
        draggingKey = null;
        dropTarget = null;
        if (!source || source === targetKey) return;
        onpartition(movePartition(partitionOf(groups), [source], targetKey));
    }

    function onDragEnd() {
        draggingKey = null;
        dropTarget = null;
    }

    // =========================================================================
    // Presentation helpers
    // =========================================================================

    function txCountOf(group: AssetGroup): number {
        return group.members.reduce((sum, m) => sum + (txCounts[m.fakeAssetId] ?? 0), 0);
    }

    function reasonLabel(reason: string): string {
        if (reason === 'isin') return $t('importWizard.assetUnify.reasonIsin');
        if (reason === 'ticker') return $t('importWizard.assetUnify.reasonTicker');
        if (reason === 'nameSuffix') return $t('importWizard.assetUnify.reasonNameSuffix');
        if (reason === 'nameNoIsin') return $t('importWizard.assetUnify.reasonNameNoIsin');
        return $t('importWizard.assetUnify.reasonName');
    }

    /**
     * How a member is named in a link explanation.
     *
     * Deliberately not the name: when the reason *is* "same name", labelling both sides with it
     * produces "BTP X ↔ BTP X", which explains nothing. The code, or failing that the file, is
     * what actually tells the two apart — and it is the same vocabulary as the rows below.
     */
    function memberLabel(group: AssetGroup, fakeAssetId: number): string {
        const member = group.members.find((m) => m.fakeAssetId === fakeAssetId);
        if (!member) return `#${fakeAssetId}`;
        return member.isin ?? member.symbol ?? member.fileName;
    }

    /** Badge palette, one hue per kind, so "which of these is an ISIN" needs no reading. */
    const badgeTone: Record<IdentifierKind, string> = {
        isin: 'border-sky-300 bg-sky-100 text-sky-900 dark:border-sky-700 dark:bg-sky-900/40 dark:text-sky-100',
        symbol: 'border-violet-300 bg-violet-100 text-violet-900 dark:border-violet-700 dark:bg-violet-900/40 dark:text-violet-100',
        name: 'border-slate-300 bg-slate-100 text-slate-800 dark:border-slate-600 dark:bg-slate-700/60 dark:text-slate-100',
    };

    /** The kind's name as it appears in the tooltip. Literal `$t` calls so the audit sees them. */
    function kindLabel(kind: IdentifierKind): string {
        if (kind === 'isin') return $t('importWizard.assetUnify.kindIsin');
        if (kind === 'symbol') return $t('importWizard.assetUnify.kindSymbol');
        return $t('importWizard.assetUnify.kindName');
    }

    interface Badge {
        kind: IdentifierKind;
        value: string;
        primary: boolean;
        /** Only a contested kind offers a choice: one candidate is already the answer. */
        electable: boolean;
    }

    function badgesOf(group: AssetGroup): Badge[] {
        const primary: GroupPrimary | undefined = primaries[groupSignature(group)];
        const ids = orderedIdentifiers(group.members, primary);
        const out: Badge[] = [];
        const push = (kind: IdentifierKind, values: string[]) => {
            for (const value of values) out.push({kind, value, primary: isPrimary(primary, kind, value) || (!primary?.[kind] && value === values[0]), electable: values.length > 1});
        };
        push('isin', ids.isins);
        push('symbol', ids.symbols);
        push('name', ids.names);
        return out;
    }

    function badgeTitle(badge: Badge): string {
        if (!badge.electable && !badge.primary) return `${kindLabel(badge.kind)}: ${badge.value}`;
        if (!badge.primary) return $t('importWizard.assetUnify.electPrimary', {values: {kind: kindLabel(badge.kind)}});
        // A code decides how the instrument is quoted; a name decides only how it reads. Saying
        // "quoted under" of a name would be a lie the user has no way to check.
        return badge.kind === 'name' ? $t('importWizard.assetUnify.primaryIsName') : $t('importWizard.assetUnify.primaryIsCode', {values: {kind: kindLabel(badge.kind)}});
    }

    /** True once any badge on the card offers a choice — the caption is noise otherwise. */
    function hasChoice(badges: Badge[]): boolean {
        return badges.some((b) => b.electable);
    }

    // =========================================================================
    // Naming
    // =========================================================================

    /**
     * What the card is called.
     *
     * Once the group is bound to an archived asset the archive wins: that is the name the user
     * will live with, and showing a file's spelling instead would make the same instrument look
     * like two. Unbound, the elected name leads — including one the user typed here.
     */
    function displayNameOf(group: AssetGroup): string {
        const bound = resolvedNames[group.members[0].fakeAssetId];
        if (bound && bound.trim() !== '') return bound;
        const ids = orderedIdentifiers(group.members, primaries[groupSignature(group)]);
        return ids.names[0] ?? ids.isins[0] ?? ids.symbols[0] ?? `#${group.members[0]?.fakeAssetId}`;
    }

    /** A bound group takes its name from the archive: renaming it here would be a lie. */
    function canRename(group: AssetGroup): boolean {
        const bound = resolvedNames[group.members[0].fakeAssetId];
        return !(bound && bound.trim() !== '');
    }

    let renamingId = $state<string | null>(null);
    let renameDraft = $state('');

    function startRename(group: AssetGroup) {
        renamingId = group.groupId;
        renameDraft = displayNameOf(group);
    }

    function commitRename(group: AssetGroup) {
        const value = renameDraft.trim();
        renamingId = null;
        if (value === '' || value === displayNameOf(group)) return;
        onprimary(groupSignature(group), 'name', value);
    }

    function onRenameKey(event: KeyboardEvent, group: AssetGroup) {
        if (event.key === 'Enter') {
            event.preventDefault();
            commitRename(group);
        } else if (event.key === 'Escape') {
            event.preventDefault();
            renamingId = null;
        }
    }

    /**
     * One line per reason instead of one per pair.
     *
     * Four reports of the same bond produce six links and six identical sentences; the one line
     * that differs — the extraction without a code, the suffix that changed — drowns in them.
     */
    function linkText(group: AssetGroup, summary: LinkSummary): string {
        const reason = reasonLabel(summary.reason);
        if (summary.coversAll) return $t('importWizard.assetUnify.linkAll', {values: {reason, n: group.members.length}});
        return $t('importWizard.assetUnify.linkSome', {values: {reason, members: summary.members.map((id) => memberLabel(group, id)).join(' ↔ ')}});
    }
</script>

<div class="space-y-4" data-testid="asset-group-step">
    <!-- The banner takes the full width: squeezing it to make room for a button reflowed the
         explanation into a narrow column for no gain. The reset sits on its own line, next to the
         legend that decodes the borders. -->
    <InfoBanner variant="info" message={$t('importWizard.assetUnify.intro')} />
    <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-gray-500 dark:text-gray-400">
            <span class="inline-flex items-center gap-1"><span class="h-3 w-5 rounded border-2 border-solid border-emerald-400 dark:border-emerald-600/60"></span>{$t('importWizard.assetUnify.legendConfirmed')}</span>
            <span class="inline-flex items-center gap-1"><span class="h-3 w-5 rounded border-2 border-dashed border-amber-400 dark:border-amber-500/60"></span>{$t('importWizard.assetUnify.legendProposed')}</span>
            <span class="inline-flex items-center gap-1"><span class="h-3 w-5 rounded border border-gray-300 dark:border-gray-600"></span>{$t('importWizard.assetUnify.legendSingle')}</span>
            <span class="inline-flex items-center gap-1"><Star class="h-3 w-3 fill-amber-400 text-amber-500" />{$t('importWizard.assetUnify.legendPrimary')}</span>
        </div>
        <button
            type="button"
            class="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            disabled={!touched}
            onclick={onreset}
            title={$t('importWizard.assetUnify.resetHint')}
            data-testid="asset-group-reset"
        >
            <RotateCcw class="h-3.5 w-3.5" />
            {$t('importWizard.assetUnify.reset')}
        </button>
    </div>

    {#if groups.length === 0}
        <p class="text-sm text-gray-500 dark:text-gray-400" data-testid="asset-group-empty">{$t('importWizard.assetUnify.empty')}</p>
    {:else}
        <!-- Uniform cards, extraction order. Same rectangle for one member or five: the eye can
             then compare them without re-measuring each one. -->
        <div class="grid grid-cols-1 items-stretch gap-3 md:grid-cols-2 2xl:grid-cols-3">
            {#each groups as group (group.groupId)}
                {@const proposed = group.state === 'proposed'}
                {@const united = group.members.length > 1}
                {@const anchorKey = memberKey(group.members[0])}
                {@const badges = badgesOf(group)}
                <div
                    class="flex h-full min-h-[9.5rem] flex-col rounded-lg p-3 transition-colors {proposed
                        ? 'border-2 border-dashed border-amber-400 bg-amber-50/60 dark:border-amber-500/60 dark:bg-amber-900/10'
                        : united
                          ? 'border-2 border-solid border-emerald-400 bg-emerald-50/50 dark:border-emerald-600/60 dark:bg-emerald-900/10'
                          : 'border border-gray-300 bg-white dark:border-gray-600 dark:bg-gray-800'} {dropTarget === anchorKey ? 'ring-2 ring-blue-400' : ''}"
                    role="group"
                    ondragover={(e) => onDragOver(e, anchorKey)}
                    ondrop={(e) => onDrop(e, anchorKey)}
                    data-testid="asset-group-{group.groupId}"
                    data-state={group.state}
                >
                    <!-- Header: what this is, and how firmly we believe it -->
                    <div class="flex items-start justify-between gap-2">
                        {#if renamingId === group.groupId}
                            <!-- svelte-ignore a11y_autofocus -->
                            <input
                                type="text"
                                bind:value={renameDraft}
                                autofocus
                                class="min-w-0 flex-1 rounded border border-blue-400 bg-white px-1.5 py-0.5 text-sm font-semibold text-gray-800 focus:ring-1 focus:ring-blue-400 focus:outline-none dark:bg-gray-900 dark:text-gray-100"
                                onkeydown={(e) => onRenameKey(e, group)}
                                onblur={() => commitRename(group)}
                                data-testid="asset-group-rename-input-{group.groupId}"
                            />
                            <button type="button" class="shrink-0 rounded p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" title={$t('common.cancel')} onclick={() => (renamingId = null)} data-testid="asset-group-rename-cancel-{group.groupId}">
                                <X class="h-3.5 w-3.5" />
                            </button>
                        {:else}
                            <span use:scrollOnOverflow class="{overflowScrollTextClass} text-sm font-semibold text-gray-800 dark:text-gray-100" data-testid="asset-group-name-{group.groupId}">
                                {displayNameOf(group)}
                            </span>
                        {/if}
                        <div class="flex shrink-0 items-center gap-1">
                            {#if renamingId !== group.groupId && canRename(group)}
                                <!-- Unbound, the name is nobody's but the files': the user must be
                                     able to settle on one, or write the one they actually use. -->
                                <button
                                    type="button"
                                    class="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-700 dark:hover:bg-gray-700 dark:hover:text-gray-200"
                                    title={$t('importWizard.assetUnify.rename')}
                                    onclick={() => startRename(group)}
                                    data-testid="asset-group-rename-{group.groupId}"
                                >
                                    <Pencil class="h-3.5 w-3.5" />
                                </button>
                            {/if}
                            {#if !canRename(group)}
                                <span class="inline-flex items-center gap-1 rounded bg-gray-200 px-1.5 py-0.5 text-[11px] font-medium whitespace-nowrap text-gray-700 dark:bg-gray-700 dark:text-gray-200" title={$t('importWizard.assetUnify.fromDbHint')}>
                                    <Database class="h-3 w-3" />
                                    {$t('importWizard.assetUnify.fromDb')}
                                </span>
                            {/if}
                            {#if united}
                                <span class="rounded px-1.5 py-0.5 text-[11px] font-medium whitespace-nowrap {proposed ? 'bg-amber-200 text-amber-900 dark:bg-amber-800/60 dark:text-amber-100' : 'bg-emerald-200 text-emerald-900 dark:bg-emerald-800/60 dark:text-emerald-100'}">
                                    {proposed ? $t('importWizard.assetUnify.stateProposed') : $t('importWizard.assetUnify.stateConfirmed')}
                                </span>
                            {/if}
                            {#if resolvedIds[group.members[0].fakeAssetId] !== undefined && oninspect}
                                <button
                                    type="button"
                                    class="rounded p-1 text-gray-500 hover:bg-gray-200 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200"
                                    title={$t('importWizard.assetUnify.inspect')}
                                    onclick={() => oninspect?.(resolvedIds[group.members[0].fakeAssetId])}
                                    data-testid="asset-group-inspect-{group.groupId}"
                                >
                                    <Pencil class="h-3.5 w-3.5" />
                                </button>
                            {/if}
                        </div>
                    </div>

                    <!-- Identifiers. Every code the group carries, colour-coded by kind; a click
                         promotes one to lead. The star marks what the asset will be quoted under. -->
                    {#if hasChoice(badges)}
                        <p class="mt-2 text-[10px] text-gray-500 dark:text-gray-400">{$t('importWizard.assetUnify.idsHint')}</p>
                    {/if}
                    <div class="mt-1 flex flex-wrap gap-1" data-testid="asset-group-ids-{group.groupId}">
                        {#each badges as badge (badge.kind + badge.value)}
                            {#if badge.electable}
                                <button
                                    type="button"
                                    class="inline-flex max-w-full cursor-pointer items-center gap-1 rounded border px-1.5 py-0.5 text-[11px] {badgeTone[badge.kind]} {badge.primary ? 'ring-2 ring-amber-400 ring-offset-1 dark:ring-offset-gray-900' : 'opacity-70 hover:opacity-100'}"
                                    onclick={() => elect(group, badge.kind, badge.value)}
                                    title={badgeTitle(badge)}
                                    data-testid="asset-group-badge-{group.groupId}-{badge.value}"
                                    data-primary={badge.primary}
                                >
                                    <!-- The hollow star is the affordance: without it the runner-up
                                         badges look decorative and nobody discovers the choice. -->
                                    <Star class="h-2.5 w-2.5 shrink-0 {badge.primary ? 'fill-amber-400 text-amber-500' : 'text-current opacity-50'}" />
                                    <span class="truncate {badge.kind === 'name' ? '' : 'font-mono'}">{badge.value}</span>
                                </button>
                            {:else}
                                <span class="inline-flex max-w-full items-center gap-1 rounded border px-1.5 py-0.5 text-[11px] {badgeTone[badge.kind]}" title={badgeTitle(badge)} data-testid="asset-group-badge-{group.groupId}-{badge.value}" data-primary={badge.primary}>
                                    {#if badge.primary && hasChoice(badges)}<Star class="h-2.5 w-2.5 shrink-0 fill-amber-400 text-amber-500" />{/if}
                                    <span class="truncate {badge.kind === 'name' ? '' : 'font-mono'}">{badge.value}</span>
                                </span>
                            {/if}
                        {/each}
                    </div>

                    <!-- Members: one row per file the security was read from -->
                    <div class="mt-2 grow space-y-1">
                        {#each group.members as member (memberKey(member))}
                            <div
                                class="flex items-center gap-1.5 rounded border border-gray-200 bg-white/70 px-1.5 py-1 dark:border-gray-700 dark:bg-gray-900/40 {draggingKey === memberKey(member) ? 'opacity-50' : ''} {dropTarget === memberKey(member) ? 'ring-1 ring-blue-400' : ''}"
                                draggable="true"
                                role="listitem"
                                ondragstart={(e) => onDragStart(e, member)}
                                ondragend={onDragEnd}
                                ondragover={(e) => onDragOver(e, memberKey(member))}
                                ondrop={(e) => onDrop(e, memberKey(member))}
                                data-testid={united ? `asset-group-member-${member.fakeAssetId}` : `asset-group-single-${member.fakeAssetId}`}
                            >
                                <FileText class="h-3 w-3 shrink-0 text-gray-400" />
                                <span use:scrollOnOverflow class="{overflowScrollTextClass} grow text-[11px] text-gray-600 dark:text-gray-300">{member.fileName}</span>
                                <span class="shrink-0 font-mono text-[10px] text-gray-500 dark:text-gray-400">{member.isin ?? member.symbol ?? $t('importWizard.assetUnify.noIsin')}</span>
                                <button
                                    type="button"
                                    class="shrink-0 rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-200"
                                    onclick={(e) => openMenu(e, member)}
                                    title={$t('importWizard.assetUnify.actions')}
                                    data-testid={united ? `asset-group-member-menu-${member.fakeAssetId}` : `asset-group-single-menu-${member.fakeAssetId}`}
                                >
                                    <MoreVertical class="h-3.5 w-3.5" />
                                </button>
                            </div>
                        {/each}
                    </div>

                    <!-- Why the engine linked these. Naming both sides matters: "same name, 100%"
                         under a card with four codes says nothing about *which* two it means. -->
                    {#if group.links.length > 0}
                        <div class="mt-2 space-y-0.5 border-t border-dashed border-gray-300 pt-1.5 dark:border-gray-600" data-testid="asset-group-links-{group.groupId}">
                            {#each summariseLinks(group) as summary (summary.reason)}
                                <p class="text-[10px] text-gray-500 dark:text-gray-400">
                                    {linkText(group, summary)}{#if summary.score < 1}<span> · {$t('importWizard.assetUnify.linkScore', {values: {score: Math.round(summary.score * 100)}})}</span>{/if}
                                </p>
                            {/each}
                        </div>
                    {/if}

                    <!-- Footer: weight, and the two verbs that act on the whole group -->
                    <div class="mt-2 flex items-center justify-between gap-2 border-t border-gray-200 pt-2 dark:border-gray-700">
                        <span class="text-[11px] text-gray-500 dark:text-gray-400">{$t('importWizard.assetUnify.txCount', {values: {count: txCountOf(group)}})}</span>
                        <div class="flex shrink-0 items-center gap-1.5">
                            {#if proposed}
                                <button type="button" class="inline-flex items-center gap-1 rounded bg-emerald-600 px-2 py-1 text-xs font-medium text-white hover:bg-emerald-700" onclick={() => confirmGroup(group)} data-testid="asset-group-confirm-{group.groupId}">
                                    <Check class="h-3.5 w-3.5" />
                                    {$t('importWizard.assetUnify.confirm')}
                                </button>
                            {/if}
                            {#if united}
                                <button
                                    type="button"
                                    class="inline-flex items-center gap-1 rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
                                    onclick={() => splitGroup(group)}
                                    data-testid="asset-group-split-{group.groupId}"
                                >
                                    <Scissors class="h-3.5 w-3.5" />
                                    {$t('importWizard.assetUnify.split')}
                                </button>
                            {/if}
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>

{#if menuOpen}
    <ContextMenu x={menuX} y={menuY} items={menuItems} anchorEl={menuAnchor} onAction={handleMenuAction} onClose={() => (menuOpen = false)} />
{/if}
