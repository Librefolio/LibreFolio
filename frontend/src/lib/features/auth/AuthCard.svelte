<script lang="ts">
    /** The frame of an access card: the brand header, then the body. Extra attributes land on the card itself. */
    import type {Snippet} from 'svelte';
    import type {HTMLAttributes} from 'svelte/elements';

    interface Props extends HTMLAttributes<HTMLDivElement> {
        testId: string;
        children: Snippet;
    }

    let {testId, children, ...rest}: Props = $props();
</script>

<div {...rest} class="w-full max-w-lg bg-lf-card text-lf-primary border border-lf-subtle rounded-2xl shadow-2xl overflow-hidden flex flex-col font-sans" data-testid={testId}>
    <!-- Header Section (brand green) -->
    <div class="bg-lf-brand p-8 flex flex-col items-center justify-center space-y-2">
        <div class="flex items-center space-x-3 text-lf-on-brand">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center p-1 bg-lf-logo">
                <img alt="LibreFolio" class="max-w-full max-h-full object-contain" src="/logo.png" />
            </div>
            <span class="text-2xl font-bold tracking-wide">LibreFolio</span>
        </div>
    </div>

    <!-- Body Section -->
    <div class="p-8 pt-6">
        {@render children()}
    </div>
</div>
