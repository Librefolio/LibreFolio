/**
 * The name and description of a BRIM import plugin, in the UI language.
 *
 * A plugin runs backend-side and writes its `name` and `description` in English. The catalogues
 * carry `brimPlugins.<code>.name` and `brimPlugins.<code>.description` for every plugin (a brand
 * name is the same in all four), so the plugin select, the import wizard and the About page show
 * them in the UI language. A plugin the catalogues do not know yet keeps its own English text.
 *
 * The English catalogue mirrors the plugins: `test_brim_providers.py` checks every registered
 * plugin against the four catalogues.
 */
import {translateOr, type Translate} from '$lib/utils/core/translateOr';

/** What the lookup reads of a plugin: `GET /brokers/import/plugins` fits, and so does a refusal's context. */
export interface BrimPluginText {
    code: string;
    name?: string | null;
    description?: string | null;
}

export function brimPluginName(plugin: BrimPluginText, translate: Translate): string {
    return translateOr(translate, `brimPlugins.${plugin.code}.name`, plugin.name || plugin.code);
}

export function brimPluginDescription(plugin: BrimPluginText, translate: Translate): string {
    return translateOr(translate, `brimPlugins.${plugin.code}.description`, plugin.description ?? '');
}
