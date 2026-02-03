<script lang="ts">
    import { _ } from '$lib/i18n';
    import { zxcvbn, zxcvbnOptions } from '@zxcvbn-ts/core';
    import * as zxcvbnCommonPackage from '@zxcvbn-ts/language-common';
    import * as zxcvbnEnPackage from '@zxcvbn-ts/language-en';
    import { Check, X } from 'lucide-svelte';

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
        { key: 'minLength', check: (pwd) => pwd.length >= 8 },
        { key: 'hasUppercase', check: (pwd) => /[A-Z]/.test(pwd) },
        { key: 'hasLowercase', check: (pwd) => /[a-z]/.test(pwd) },
        { key: 'hasNumber', check: (pwd) => /\d/.test(pwd) },
        { key: 'hasSpecial', check: (pwd) => /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~;']/.test(pwd) },
    ];

    // Calculate strength
    $: strength = password ? zxcvbn(password) : null;
    $: score = strength?.score ?? 0;

    // Check rules
    $: ruleResults = rules.map(rule => ({
        key: rule.key,
        passed: password ? rule.check(password) : false,
    }));

    $: allRulesPassed = ruleResults.every(r => r.passed);

    // Strength labels and colors
    const strengthConfig = [
        { label: 'veryWeak', color: 'bg-red-500', textColor: 'text-red-600' },
        { label: 'weak', color: 'bg-orange-500', textColor: 'text-orange-600' },
        { label: 'fair', color: 'bg-yellow-500', textColor: 'text-yellow-600' },
        { label: 'strong', color: 'bg-lime-500', textColor: 'text-lime-600' },
        { label: 'veryStrong', color: 'bg-green-500', textColor: 'text-green-600' },
    ];

    $: currentConfig = strengthConfig[score];
</script>

{#if password.length > 0}
    <div class="mt-2 space-y-2" data-testid="password-strength-meter">
        <!-- Strength Bar -->
        <div class="flex items-center gap-2">
            <div class="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden flex gap-0.5" data-testid="password-strength-bar" data-strength={score}>
                {#each [0, 1, 2, 3, 4] as i}
                    <div
                        class="flex-1 h-full transition-all duration-300 rounded-full"
                        class:bg-gray-200={i > score}
                        class:bg-red-500={i <= score && score === 0}
                        class:bg-orange-500={i <= score && score === 1}
                        class:bg-yellow-500={i <= score && score === 2}
                        class:bg-lime-500={i <= score && score === 3}
                        class:bg-green-500={i <= score && score === 4}
                    ></div>
                {/each}
            </div>
            <span class="text-xs font-medium {currentConfig.textColor} min-w-20 text-right">
                {$_(`auth.passwordStrength.${currentConfig.label}`)}
            </span>
        </div>

        <!-- Rules Checklist -->
        {#if showRules}
            <div class="bg-gray-50 rounded-lg p-3 border border-gray-200">
                <p class="text-xs font-medium text-gray-700 mb-2">
                    {$_('auth.passwordStrength.requirements')}
                </p>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-1">
                    {#each ruleResults as rule}
                        <div class="flex items-center gap-1.5 text-xs">
                            {#if rule.passed}
                                <Check class="w-3.5 h-3.5 text-green-600" />
                                <span class="text-green-700">{$_(`auth.passwordStrength.rules.${rule.key}`)}</span>
                            {:else}
                                <X class="w-3.5 h-3.5 text-gray-400" />
                                <span class="text-gray-500">{$_(`auth.passwordStrength.rules.${rule.key}`)}</span>
                            {/if}
                        </div>
                    {/each}
                </div>
            </div>
        {/if}
    </div>
{/if}

