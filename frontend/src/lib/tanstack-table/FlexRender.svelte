/**
* FlexRender - Componente per il rendering flessibile delle celle TanStack Table
*
* Permette di renderizzare contenuti di celle che possono essere:
* - Stringhe semplici
* - Componenti Svelte
* - Funzioni che ritornano contenuto
*/

<script generics="TProps" lang="ts">
    type Props = {
        /** Il contenuto da renderizzare (stringa, componente, o funzione) */
        content: unknown;
        /** Le props da passare al contenuto se è un componente o funzione */
        props: TProps;
    };

    let {content, props}: Props = $props();
</script>

{#if typeof content === 'string'}
    {content}
{:else if typeof content === 'function'}
    {@const result = content(props)}
    {#if typeof result === 'string'}
        {result}
    {:else if result !== null && result !== undefined}
        <!-- Se è un componente o altro, renderizza come stringa -->
        {String(result)}
    {/if}
{:else if content !== null && content !== undefined}
    {String(content)}
{/if}
