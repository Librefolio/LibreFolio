<script lang="ts">
    import {_} from '$lib/i18n';
    import {zxcvbn, zxcvbnOptions} from '@zxcvbn-ts/core';
    import * as zxcvbnCommonPackage from '@zxcvbn-ts/language-common';
    import * as zxcvbnEnPackage from '@zxcvbn-ts/language-en';
    import {Check, X} from 'lucide-svelte';

    export let password: string = '';
    export let showRules: boolean = true;

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

    // Password rules
    interface PasswordRule {
        key: string;
        check: (pwd: string) => boolean;
    }

    const rules: PasswordRule[] = [
        {key: 'minLength', check: (pwd) => pwd.length >= 8},
        {key: 'hasUppercase', check: (pwd) => /[A-Z]/.test(pwd)},
        {key: 'hasLowercase', check: (pwd) => /[a-z]/.test(pwd)},
        {key: 'hasNumber', check: (pwd) => /\d/.test(pwd)},
        {key: 'hasSpecial', check: (pwd) => /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~;']/.test(pwd)},
    ];

    // Calculate strength
    $: strength = password ? zxcvbn(password) : null;
    $: score = strength?.score ?? 0;

    // Check rules
    $: ruleResults = rules.map((rule) => ({
        key: rule.key,
        passed: password ? rule.check(password) : false,
    }));

    $: allRulesPassed = ruleResults.every((r) => r.passed);

    // Strength labels and colours: three states for five scores (decision D-T13). The label says the level in words;
    // the colours of the bar only repeat it.
    const strengthConfig = [
        {label: 'veryWeak', color: 'bg-lf-danger', textColor: 'text-lf-danger'},
        {label: 'weak', color: 'bg-lf-danger', textColor: 'text-lf-danger'},
        {label: 'fair', color: 'bg-lf-warning', textColor: 'text-lf-warning'},
        {label: 'strong', color: 'bg-lf-success', textColor: 'text-lf-success'},
        {label: 'veryStrong', color: 'bg-lf-success', textColor: 'text-lf-success'},
    ];

    $: currentConfig = strengthConfig[score];
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
                                <span class="text-lf-secondary">{$_(`auth.passwordStrength.rules.${rule.key}`)}</span>
                            {:else}
                                <X class="w-3.5 h-3.5 text-lf-muted" />
                                <span class="text-lf-muted">{$_(`auth.passwordStrength.rules.${rule.key}`)}</span>
                            {/if}
                        </div>
                    {/each}
                </div>
            </div>
        {/if}
    </div>
{/if}
