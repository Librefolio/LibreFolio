/** Shapes of the Users tab (administrators), as `GET /users` and `GET /users/invites` return them. */

export interface AdminAccount {
    id: number;
    username: string;
    email: string;
    is_active: boolean;
    is_superuser: boolean;
    created_at: string;
    /** Nobody may delete, deactivate or demote it (the paying administrator of a managed instance). */
    protected: boolean;
    /** Inactive and waiting for its email verification with a live link: its place is already counted (workstream E). */
    holds_place?: boolean;
    /** The initial administrator of LIBREFOLIO_ADMIN_EMAIL waiting for its setup link (F02): never reactivated here. */
    pending_setup?: boolean;
    /** The account's avatar (an uploaded image or an address), drawn after the row's chevron (N69-4); null without one. */
    avatar_url?: string | null;
}

export interface OpenInvite {
    id: number;
    grants_admin: boolean;
    email?: string | null;
    created_at: string;
    expires_at: string;
}

export interface AccountsUsage {
    used: number;
    max_users?: number | null;
    billing_url?: string | null;
}

export type UserAction = 'deactivate' | 'reactivate' | 'cancel-setup' | 'promote' | 'demote' | 'reset-link' | 'sign-out' | 'restart-guides' | 'delete';
