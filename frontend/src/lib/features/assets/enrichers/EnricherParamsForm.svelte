<!--
  EnricherParamsForm — the parameters of one enricher's binding, drawn from its `params_schema` (plan 68, E7b2): the
  plugin describes the fields, as a price provider does, and the form draws itself. Labels come from the plugin's own
  i18n fragment (`x-i18n-key`), else from the label it declares. A field left empty is not sent (`withParams`).
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';

    interface ParamField {
        key: string;
        type?: string;
        label?: string;
        options?: string[];
        default?: unknown;
        required?: boolean;
        'x-i18n-key'?: string;
    }

    interface Props {
        code: string;
        schema: Array<Record<string, unknown>>;
        /** The binding's current parameters (the fields beside type and identifier). */
        values: Record<string, unknown>;
        onchange: (params: Record<string, unknown>) => void;
    }

    let {code, schema, values, onchange}: Props = $props();

    let fields = $derived((schema as unknown as ParamField[]).filter((field) => field.key && field.type !== 'ui_component'));

    function label(field: ParamField): string {
        const key = field['x-i18n-key'];
        if (key) {
            const translated = $t(key);
            if (translated !== key) return translated;
        }
        return field.label ?? field.key;
    }

    function text(value: unknown): string {
        return value === null || value === undefined ? '' : String(value);
    }

    function set(key: string, value: string): void {
        onchange({...values, [key]: value});
    }
</script>

{#if fields.length}
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-2" data-testid="enricher-params-{code}">
        {#each fields as field (field.key)}
            <label class="block text-xs text-lf-secondary">
                <span class="block mb-1">{label(field)}</span>
                {#if field.type === 'select' && field.options}
                    <SimpleSelect
                        value={text(values[field.key] ?? field.default)}
                        options={field.options.map((option) => ({value: option, label: option}))}
                        testId="enricher-param-{code}-{field.key}"
                        optionTestId={(option) => `enricher-param-${code}-${field.key}-option-${option.value}`}
                        onchange={(value) => set(field.key, value)}
                    />
                {:else}
                    <input
                        type="text"
                        class="w-full px-2 py-1.5 text-sm rounded-md border border-lf-input bg-lf-field text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:border-lf-focus"
                        value={text(values[field.key])}
                        placeholder={text(field.default)}
                        data-testid="enricher-param-{code}-{field.key}"
                        onchange={(event) => set(field.key, event.currentTarget.value)}
                    />
                {/if}
            </label>
        {/each}
    </div>
{/if}
