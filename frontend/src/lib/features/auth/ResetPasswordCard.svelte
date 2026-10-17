<script lang="ts">
    /**
     * The form of a password-reset link: a new password, twice, for the account the link belongs to.
     *
     * The rules are the app's own, read from PasswordStrength (`bind:valid`): this card keeps no copy of them. The server
     * checks the link again when the form is sent: a link that stopped working meanwhile ends in `oninvalid`.
     */
    import {isAxiosError} from 'axios';
    import {Lock} from 'lucide-svelte';
    import {zodiosApi} from '$lib/api';
    import {_} from '$lib/i18n';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import PasswordInput from '$lib/components/ui/input/PasswordInput.svelte';
    import PasswordStrength from '$lib/components/ui/input/PasswordStrength.svelte';
    import AuthCard from './AuthCard.svelte';

    interface Props {
        token: string;
        username: string | null;
        ondone: () => void;
        oninvalid: () => void;
    }

    let {token, username, ondone, oninvalid}: Props = $props();

    let newPassword = $state('');
    let confirmPassword = $state('');
    let rulesMet = $state(false);
    let error = $state('');
    let loading = $state(false);

    async function handleSubmit(event: SubmitEvent): Promise<void> {
        event.preventDefault();
        error = '';
        if (!rulesMet) {
            error = $_('auth.validation.passwordTooWeak');
            return;
        }
        if (newPassword !== confirmPassword) {
            error = $_('auth.validation.passwordsNoMatch');
            return;
        }
        loading = true;
        try {
            await zodiosApi.reset_password_with_link_api_v1_auth_password_reset_post({token, new_password: newPassword});
            ondone();
        } catch (e: unknown) {
            const response = isAxiosError(e) ? e.response : undefined;
            if (response?.status === 400 && response.data?.detail?.error_code === 'TOKEN_INVALID') {
                oninvalid();
                return;
            }
            const weak = response?.status === 422 || (response?.status === 400 && response.data?.detail?.error_code === 'PASSWORD_TOO_WEAK');
            error = $_(weak ? 'auth.validation.passwordTooWeak' : 'auth.resetPassword.failed');
        } finally {
            loading = false;
        }
    }
</script>

<AuthCard testId="reset-password-modal">
    <form class="space-y-4" data-testid="reset-password-form" onsubmit={handleSubmit}>
        {#if username}
            <!-- Tells the browser's password manager which saved account the new password belongs to. -->
            <input autocomplete="username" hidden name="username" readonly type="text" value={username} />
        {/if}
        <div class="text-center space-y-1">
            <h1 class="text-lg font-bold text-lf-primary">{$_('auth.resetPassword.title')}</h1>
            {#if username}
                <p class="text-sm text-lf-secondary" data-testid="reset-password-account">{$_('auth.resetPassword.account')} <span class="font-semibold text-lf-primary">{username}</span></p>
            {/if}
        </div>

        {#if error}
            <div data-testid="reset-password-error">
                <InfoBanner dismissible message={error} ondismiss={() => (error = '')} variant="error" />
            </div>
        {/if}

        <div>
            <label class="sr-only" for="reset-password-new">{$_('settings.newPassword')}</label>
            <PasswordInput autocomplete="new-password" bind:value={newPassword} disabled={loading} icon={Lock} id="reset-password-new" name="new-password" placeholder={$_('settings.newPassword')} testId="reset-password-new" />
            <PasswordStrength bind:valid={rulesMet} password={newPassword} />
        </div>

        <div>
            <label class="sr-only" for="reset-password-confirm">{$_('auth.confirmPassword')}</label>
            <PasswordInput autocomplete="new-password" bind:value={confirmPassword} disabled={loading} icon={Lock} id="reset-password-confirm" name="confirm-password" placeholder={$_('auth.confirmPassword')} testId="reset-password-confirm" />
        </div>

        <button class="w-full bg-lf-action text-lf-on-action font-bold py-3 rounded-lg shadow-md hover:bg-lf-action-hover transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed mt-2" data-testid="reset-password-submit" disabled={loading} type="submit">
            {loading ? $_('common.loading') : $_('auth.resetPassword.submit')}
        </button>
    </form>
</AuthCard>
