<script lang="ts">
    import {_} from '$lib/i18n';
    import {zxcvbn, zxcvbnOptions} from '@zxcvbn-ts/core';
    import * as zxcvbnCommonPackage from '@zxcvbn-ts/language-common';
    import * as zxcvbnEnPackage from '@zxcvbn-ts/language-en';
    import {Check, X} from 'lucide-svelte';
    import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';
    import {DEFAULT_PASSWORD_RULES, RULE_UI_KEYS, ruleMet, type PasswordRule} from '$lib/features/auth/passwordRules';

    interface Props {
        password?: string;
        showRules?: boolean;
        /** Every rule is met. A form that needs a valid password binds to it (`bind:valid`) instead of keeping its own copy of the rules. */
        valid?: boolean;
        /**
         * Rules a server published for another password than an account's, such as a secure backup's (lot B4, P12: the
         * same rules, a longer minimum), drawn and checked instead of `GET /system/instance`'s. Absent or `null`: the
         * accounts' rules; an empty list: no rule, as `rules=[]` in the server's policy.
         */
        rules?: readonly PasswordRule[] | null;
    }

    let {password = '', showRules = true, valid = $bindable(false), rules: givenRules = null}: Props = $props();

    // Initialize zxcvbn with dictionaries
    const options = {
        translations: zxcvbnEnPackage.translations,
        graphs: zxcvbnCommonPackage.adjacencyGraphs,
        dictionary: {
            ...zxcvbnCommonPackage.dictionary,
            ...zxcvbnEnPackage.dictionary,
        },
    };
    zxcvbnOptions.setOptions(options);

    // The rules come from the server (`GET /system/instance`, decision 37), or those a caller got from it for another
    // password; until it answers, or if it sends none, the rules of release 1.3. A rule this app does not know is neither
    // drawn nor checked: the server decides.
    const rules: PasswordRule[] = $derived.by(() => {
        // Given rules, even an empty list, are the server's answer for that password, as `rules=` is in the policy.
        if (givenRules != null) return givenRules.filter((rule) => Object.hasOwn(RULE_UI_KEYS, rule.code));
        // The generated type widens an optional integer to `number | null | Array<…>`; the schema allows a number or null.
        const served = instanceConfig.config.accounts.password_rules?.map(({code, value}) => ({code, value: typeof value === 'number' ? value : null}));
        return (served?.length ? served : DEFAULT_PASSWORD_RULES).filter((rule) => Object.hasOwn(RULE_UI_KEYS, rule.code));
    });

    // Calculate strength
    const strength = $derived(password ? zxcvbn(password) : null);
    const score = $derived(strength?.score ?? 0);

    // Check rules
    const ruleResults = $derived(
        rules.map((rule) => ({
            key: RULE_UI_KEYS[rule.code],
            value: rule.value ?? null,
            passed: password ? ruleMet(rule, password) === true : false,
        })),
    );

    $effect.pre(() => {
        valid = ruleResults.every((r) => r.passed);
    });

    // Strength labels and colours: three states for five scores (decision D-T13). The label says the level in words;
    // the colours of the bar only repeat it.
    const strengthConfig = [
        {label: 'veryWeak', color: 'bg-lf-danger', textColor: 'text-lf-danger'},
        {label: 'weak', color: 'bg-lf-danger', textColor: 'text-lf-danger'},
        {label: 'fair', color: 'bg-lf-warning', textColor: 'text-lf-warning'},
        {label: 'strong', color: 'bg-lf-success', textColor: 'text-lf-success'},
        {label: 'veryStrong', color: 'bg-lf-success', textColor: 'text-lf-success'},
    ];

    const currentConfig = $derived(strengthConfig[score]);
</script>

{#if password.length > 0}
    <div class="mt-2 space-y-2" data-testid="password-strength-meter">
        <!-- Strength Bar -->
        <div class="flex items-center gap-2">
            <div class="flex-1 h-2 bg-lf-neutral rounded-full overflow-hidden flex gap-0.5" data-testid="password-strength-bar" data-strength={score}>
                {#each [0, 1, 2, 3, 4] as i}
                    <div class="flex-1 h-full transition-all duration-300 rounded-full {i <= score ? currentConfig.color : 'bg-lf-neutral'}"></div>
                {/each}
            </div>
            <span class="text-xs font-medium {currentConfig.textColor} min-w-20 text-right">
                {$_(`auth.passwordStrength.${currentConfig.label}`)}
            </span>
        </div>

        <!-- Rules Checklist: ✓ and ✗ say which rule holds, the colour only repeats it -->
        {#if showRules}
            <div class="bg-lf-panel rounded-lg p-3 border border-lf-subtle" data-testid="password-requirements">
                <p class="text-xs font-medium text-lf-primary mb-2">
                    {$_('auth.passwordStrength.requirements')}
                </p>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-1">
                    {#each ruleResults as rule}
                        <div class="flex items-center gap-1.5 text-xs" data-passed={rule.passed} data-testid="password-rule-{rule.key}">
                            {#if rule.passed}
                                <Check class="w-3.5 h-3.5 text-lf-success" />
                                <span class="text-lf-secondary">{rule.value === null ? $_(`auth.passwordStrength.rules.${rule.key}`) : $_(`auth.passwordStrength.rules.${rule.key}`, {values: {value: rule.value}})}</span>
                            {:else}
                                <X class="w-3.5 h-3.5 text-lf-muted" />
                                <span class="text-lf-muted">{rule.value === null ? $_(`auth.passwordStrength.rules.${rule.key}`) : $_(`auth.passwordStrength.rules.${rule.key}`, {values: {value: rule.value}})}</span>
                            {/if}
                        </div>
                    {/each}
                </div>
            </div>
        {/if}
    </div>
{/if}
