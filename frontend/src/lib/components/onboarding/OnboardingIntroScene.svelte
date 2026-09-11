<script lang="ts">
    import {onMount} from 'svelte';
    import {_, locale} from '$lib/i18n';
    import {Play, X} from 'lucide-svelte';

    interface Props {
        open?: boolean;
        durationMs?: number;
        busy?: boolean;
        error?: string | null;
        skipLabel?: string;
        closeLabel?: string;
        onstart: () => void;
        onskip?: () => void;
        onclose: () => void;
    }

    let {open = false, durationMs = 10_000, busy = false, error = null, closeLabel = '', onstart, onclose}: Props = $props();

    let phase = $state(0);
    let phraseMotion = $state<'enter' | 'hold' | 'exit'>('enter');
    let autoStartAt = $state(0);
    let reducedMotion = $state(false);
    let runId = 0;

    const phaseKeys = ['onboarding.intro.line1', 'onboarding.intro.line2', 'onboarding.intro.line3'] as const;

    let activeLocale = $derived($locale);
    let phaseName = $derived(['welcome', 'aboard', 'tour'][phase] ?? 'tour');
    let phrase = $derived.by(() => {
        void activeLocale;
        return reducedMotion ? phaseKeys.map((key) => $_(key)).join(' ') : $_(phaseKeys[phase] ?? phaseKeys[2]);
    });

    function start() {
        if (!open || busy) return;
        runId += 1;
        onstart();
    }

    function close() {
        if (!open || busy) return;
        runId += 1;
        onclose();
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key !== 'Escape') return;
        event.stopPropagation();
        close();
    }

    onMount(() => {
        const media = window.matchMedia('(prefers-reduced-motion: reduce)');
        const update = () => (reducedMotion = media.matches);
        update();
        media.addEventListener('change', update);
        return () => media.removeEventListener('change', update);
    });

    $effect(() => {
        if (!open) return;
        const thisRun = ++runId;
        phase = 0;
        phraseMotion = reducedMotion ? 'hold' : 'enter';
        autoStartAt = Date.now() + durationMs;
        const phaseStarts = [0, Math.round(durationMs * 0.32), Math.round(durationMs * 0.64)];
        const phaseEnds = [phaseStarts[1], phaseStarts[2], Math.round(durationMs * 0.94)];
        const timers: number[] = [];
        if (!reducedMotion) {
            phaseStarts.forEach((startAt, index) => {
                if (index > 0) {
                    timers.push(
                        window.setTimeout(() => {
                            if (runId !== thisRun) return;
                            phase = index;
                            phraseMotion = 'enter';
                        }, startAt),
                    );
                }
                timers.push(
                    window.setTimeout(() => {
                        if (runId === thisRun) phraseMotion = 'hold';
                    }, startAt + 400),
                );
                timers.push(
                    window.setTimeout(
                        () => {
                            if (runId === thisRun) phraseMotion = 'exit';
                        },
                        Math.max(phaseEnds[index] - 450, startAt + 500),
                    ),
                );
            });
        }
        timers.push(
            window.setTimeout(() => {
                if (runId === thisRun) start();
            }, durationMs),
        );
        return () => {
            for (const timer of timers) window.clearTimeout(timer);
        };
    });
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
    <div
        class="fixed inset-0 z-[80] flex items-center justify-center bg-libre-beige/95 p-4 backdrop-blur-sm dark:bg-slate-950/95"
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-intro-title"
        data-testid="onboarding-intro-scene"
        data-state="intro-scene"
        data-phase={phaseName}
        data-auto-start-at={autoStartAt}
    >
        <div class="relative w-full max-w-2xl rounded-3xl border border-white/70 bg-white p-6 text-center shadow-2xl dark:border-slate-700 dark:bg-slate-900 sm:p-10">
            <div class="mb-8 flex items-start justify-end">
                <button
                    type="button"
                    class="rounded-lg p-2 text-gray-500 hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green dark:text-gray-300 dark:hover:bg-slate-800"
                    aria-label={closeLabel || $_('onboarding.actions.close')}
                    onclick={close}
                    disabled={busy}
                    data-testid="onboarding-intro-close"
                >
                    <X size={20} />
                </button>
            </div>

            <div class="flex min-h-52 flex-col items-center justify-center">
                <div class="flex flex-col items-center gap-4 sm:flex-row">
                    <span class="flex h-16 w-16 items-center justify-center rounded-2xl bg-white p-2 shadow-md ring-1 ring-gray-200 dark:ring-slate-700">
                        <img src="/logo.png" alt="" class="h-full w-full object-contain" />
                    </span>
                    <h1 id="onboarding-intro-title" class="text-3xl font-bold text-libre-green dark:text-emerald-300 sm:text-4xl">LibreFolio</h1>
                </div>
                {#if error}
                    <div class="mt-5 w-full rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="onboarding-intro-error">
                        {error}
                    </div>
                {/if}
                {#key reducedMotion ? 'reduced' : phase}
                    <p
                        class="mt-6 max-w-xl text-lg leading-8 text-gray-600 transition-all duration-500 ease-out dark:text-gray-300 motion-reduce:transform-none motion-reduce:transition-none"
                        class:opacity-100={reducedMotion || phraseMotion === 'hold'}
                        class:opacity-0={!reducedMotion && phraseMotion !== 'hold'}
                        class:translate-y-3={!reducedMotion && phraseMotion === 'enter'}
                        class:-translate-y-2={!reducedMotion && phraseMotion === 'exit'}
                        class:blur-sm={!reducedMotion && phraseMotion !== 'hold'}
                        aria-live="polite"
                        data-testid="onboarding-intro-phrase"
                        data-motion={phraseMotion}
                    >
                        {phrase}
                    </p>
                {/key}
            </div>

            <button
                type="button"
                class="mt-8 inline-flex items-center gap-2 rounded-xl bg-libre-green px-6 py-3 font-semibold text-white hover:bg-libre-green/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green"
                onclick={start}
                disabled={busy}
                data-testid="onboarding-intro-start"
            >
                <Play size={18} />
                {$_('onboarding.intro.start')}
            </button>
            <p class="mt-3 text-xs text-gray-500 dark:text-gray-400">
                {$_('onboarding.intro.autoStartHint')}
            </p>
        </div>
    </div>
{/if}
