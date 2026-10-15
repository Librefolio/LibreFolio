/**
 * The tabs of the Settings page, as a registry.
 *
 * `routes/(app)/settings/+page.svelte` draws its tab bar and the active tab's body from this list,
 * so adding a tab is one entry here, plus the import of its body:
 *   - `id` is the `?tab=` value that opens the tab and the suffix of its `settings-tab-{id}` test id;
 *   - `order` places it in the bar, left to right; the numbers leave gaps, so a new tab slots in
 *     without renumbering the others;
 *   - `visible(ctx)` hides it from whoever may not see it (absent: everyone sees it). An
 *     administrators-only tab is `visible: (ctx) => ctx.isSuperuser`;
 *   - `props(ctx)` are spread on the body, and follow the context while it is on screen;
 *   - `alignEnd` starts the right-hand group on a wide screen: that tab and every tab after it sit
 *     on the right. One tab carries it.
 */
import type {Component, ComponentType} from 'svelte';
import {Info, Shield, Sliders, User} from 'lucide-svelte';
import {Mail} from 'lucide-svelte';
import ProfileTab from '$lib/features/settings/tabs/ProfileTab.svelte';
import PreferencesTab from '$lib/features/settings/tabs/PreferencesTab.svelte';
import AboutTab from '$lib/features/settings/tabs/AboutTab.svelte';
import GlobalSettingsTab from '$lib/features/settings/tabs/GlobalSettingsTab.svelte';
import EmailSettingsTab from '$lib/features/email/EmailSettingsTab.svelte';

/** What a tab may depend on: who is signed in. */
export interface SettingsTabContext {
    isSuperuser: boolean;
}

export interface SettingsTab {
    id: string;
    labelKey: string;
    icon: ComponentType;
    order: number;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- each body has props of its own
    component: Component<any>;
    visible?: (ctx: SettingsTabContext) => boolean;
    props?: (ctx: SettingsTabContext) => Record<string, unknown>;
    alignEnd?: boolean;
}

export const SETTINGS_TABS: readonly SettingsTab[] = [
    {id: 'profile', labelKey: 'settings.profile', icon: User, order: 10, component: ProfileTab},
    {id: 'preferences', labelKey: 'settings.preferences', icon: Sliders, order: 20, component: PreferencesTab},
    {id: 'about', labelKey: 'settings.about', icon: Info, order: 30, component: AboutTab},
    // Everyone reads the global settings; only an administrator changes them.
    {id: 'admin', labelKey: 'settings.admin', icon: Shield, order: 100, component: GlobalSettingsTab, props: (ctx) => ({canEdit: ctx.isSuperuser}), alignEnd: true},
    // Administrators only: the state of the instance's email and a test email (workstream E).
    {id: 'email', labelKey: 'email.tab.label', icon: Mail, order: 110, component: EmailSettingsTab, visible: (ctx) => ctx.isSuperuser},
];

/** The tabs this context may see, by ascending `order`, as a new array: `tabs` is left as it was. */
export function visibleSettingsTabs(tabs: readonly SettingsTab[], ctx: SettingsTabContext): SettingsTab[] {
    return tabs.filter((tab) => tab.visible?.(ctx) ?? true).sort((a, b) => a.order - b.order);
}
