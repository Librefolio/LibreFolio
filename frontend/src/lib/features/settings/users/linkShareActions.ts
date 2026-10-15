/**
 * Extra actions shown next to a shared link (invitation, password reset), one registry line each. Workstream E adds
 * «Send by email» here; the share dialogs never change for it.
 */

import type {Component} from 'svelte';
import type {LinkPurpose} from '$lib/features/auth/linkToken';

/** What the dialog knows about the person the link is for. */
export interface LinkShareContext {
    username?: string;
    email?: string | null;
    userId?: number;
}

export interface LinkShareActionProps {
    link: string;
    purpose: LinkPurpose;
    context: LinkShareContext;
}

export interface LinkShareAction {
    id: string;
    component: Component<LinkShareActionProps>;
    visible?: (ctx: {purpose: LinkPurpose; context: LinkShareContext}) => boolean;
}

export const LINK_SHARE_ACTIONS: LinkShareAction[] = [];

/** The registered actions to show for this link, in registry order. */
export function visibleLinkShareActions(purpose: LinkPurpose, context: LinkShareContext): LinkShareAction[] {
    return LINK_SHARE_ACTIONS.filter((action) => action.visible?.({purpose, context}) ?? true);
}
