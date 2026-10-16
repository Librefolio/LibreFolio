<script lang="ts">
    /**
     * The form of the setup link of the initial administrator (F02): the account's password, twice. The account waits,
     * inactive, for this link; once the password is set it is active and signed in, as after a login.
     *
     * The rules are the app's own, read from PasswordStrength (`bind:valid`): this card keeps no copy of them. The server
     * checks the link again when the form is sent: a link that stopped working meanwhile ends in `oninvalid`. On an
     * instance its hosting provider blocked, the setup is refused (decision P16): the card says so and offers nothing more.
     */
    import {isAxiosError} from 'axios';
    import {Lock} from 'lucide-svelte';
    import {zodiosApi} from '$lib/api';
    import {isInstanceBlockedError} from '$lib/features/instance/instanceBlock.svelte';
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
    /** The hosting provider blocked the instance: the setup waits until it is unblocked. */
    let blocked = $state(false);

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
            await zodiosApi.setup_admin_api_v1_auth_setup_post({token, new_password: newPassword});
            ondone();
        } catch (e: unknown) {
            const response = isAxiosError(e) ? e.response : undefined;
            if (response?.status === 400 && response.data?.detail?.error_code === 'TOKEN_INVALID') {
                oninvalid();
                return;
            }
            // Blocked: an anonymous caller gets a 401, one with a session a 423 (H); either way nothing more can be done here
            if (response?.status === 401 || isInstanceBlockedError(response?.status, response?.data)) {
                blocked = true;
                return;
            }
            const weak = response?.status === 422 || (response?.status === 400 && response.data?.detail?.error_code === 'PASSWORD_TOO_WEAK');
            error = $_(weak ? 'auth.validation.passwordTooWeak' : 'auth.setup.failed');
        } finally {
            loading = false;
        }
    }
</script>

<AuthCard testId="setup-card">
    <form class="space-y-4" data-testid="setup-form" onsubmit={handleSubmit}>
        {#if username}
            <!-- Tells the browser's password manager which saved account the new password belongs to. -->
            <input autocomplete="username" hidden name="username" readonly type="text" value={username} />
        {/if}
        <div class="text-center space-y-1">
            <h1 class="text-lg font-bold text-lf-primary">{$_('auth.setup.title')}</h1>
            <p class="text-sm text-lf-secondary">{$_('auth.setup.intro')}</p>
            {#if username}
                <p class="text-sm text-lf-secondary" data-testid="setup-account">{$_('auth.setup.account')} <span class="font-semibold text-lf-primary">{username}</span></p>
            {/if}
        </div>

        {#if blocked}
            <div data-testid="setup-blocked">
                <InfoBanner message={$_('auth.setup.blocked')} variant="warning" />
            </div>
        {/if}

        {#if error}
            <div data-testid="setup-error">
                <InfoBanner dismissible message={error} ondismiss={() => (error = '')} variant="error" />
            </div>
        {/if}

        <div>
            <label class="sr-only" for="setup-new">{$_('settings.newPassword')}</label>
            <PasswordInput autocomplete="new-password" bind:value={newPassword} disabled={loading} icon={Lock} id="setup-new" name="new-password" placeholder={$_('settings.newPassword')} testId="setup-new" />
            <PasswordStrength bind:valid={rulesMet} password={newPassword} />
        </div>

        <div>
            <label class="sr-only" for="setup-confirm">{$_('auth.confirmPassword')}</label>
            <PasswordInput autocomplete="new-password" bind:value={confirmPassword} disabled={loading} icon={Lock} id="setup-confirm" name="confirm-password" placeholder={$_('auth.confirmPassword')} testId="setup-confirm" />
        </div>

        {#if !blocked}
            <button class="w-full bg-lf-action text-lf-on-action font-bold py-3 rounded-lg shadow-md hover:bg-lf-action-hover transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed mt-2" data-testid="setup-submit" disabled={loading} type="submit">
                {loading ? $_('common.loading') : $_('auth.setup.submit')}
            </button>
        {/if}
    </form>
</AuthCard>
