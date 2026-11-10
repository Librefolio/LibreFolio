/** Shapes of the Users tab (administrators), as `GET /users` and `GET /users/account-links` return them. */

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
    /** Inactive and waiting for its email verification, its link live or expired (E-7): badged instead of «Deactivated». */
    pending_verification?: boolean;
    /** The account's avatar (an uploaded image or an address), drawn after the row's chevron (N69-4); null without one. */
    avatar_url?: string | null;
}

export type AccountLinkPurpose = 'invite' | 'password_reset' | 'email_verification' | 'admin_setup' | 'email_change';
export type AccountLinkState = 'open' | 'used' | 'expired' | 'revoked';

/** One account link (lot UA3): never its token. The backend decides its state and whether it can be revoked here. */
export interface AccountLink {
    id: number;
    purpose: AccountLinkPurpose;
    state: AccountLinkState;
    revocable: boolean;
    user_id?: number | null;
    username?: string | null;
    email?: string | null;
    grants_admin: boolean;
    created_by_user_id?: number | null;
    created_by_username?: string | null;
    created_at: string;
    expires_at: string;
    used_at?: string | null;
    used_by_user_id?: number | null;
    used_by_username?: string | null;
    revoked_at?: string | null;
}

export interface AccountsUsage {
    used: number;
    max_users?: number | null;
    billing_url?: string | null;
}

export type UserAction = 'deactivate' | 'reactivate' | 'cancel-setup' | 'promote' | 'demote' | 'reset-link' | 'sign-out' | 'restart-guides' | 'delete';
