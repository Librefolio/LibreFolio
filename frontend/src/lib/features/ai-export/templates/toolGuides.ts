/**
 * «Calcolalo in LibreFolio» (plan 78, L4a): the LibreFolio tools an analysis can send the user to.
 *
 * The backend declares only which tool an analysis suggests (`suggested_tools`, a `tool_code`); this table says how to
 * write its path and its inputs. Every label of the tool comes from the tool's own i18n keys, so a label that changes in
 * the tool changes in the prompt too; the AI Export adds only the fixed sentences around them (`aiExport.tool.*`). The
 * block is written in the interface language, like «Additional LibreFolio Data»: the labels must be the ones the user sees.
 */

/** One input of the tool: its step's label, the sentence that says what to enter, and the tool labels that sentence names. */
export interface AiExportToolGuideStep {
    /** The tool's own key for the step's name. */
    readonly labelKey: string;
    /** The AI Export's sentence; each `{name}` placeholder takes a tool label from `values`, quoted. */
    readonly explanationKey: string;
    /** Placeholder → the tool's own i18n key of the label it names. */
    readonly values?: Readonly<Record<string, string>>;
}

export interface AiExportToolGuide {
    readonly toolCode: string;
    /** The tool's own key for its name: the card the user opens in «Tools». */
    readonly nameKey: string;
    readonly whenKey: string;
    readonly returnsKey: string;
    readonly steps: readonly AiExportToolGuideStep[];
}

/** The Tools page in the sidebar (`Sidebar.svelte`). */
export const AI_EXPORT_TOOLS_NAV_KEY = 'tools.title';

const PAC = 'tools.pacAllocator.planner';

/** The PAC allocator (`bozze-AIX.md` §4 bis): its nine steps, in the planner's order. */
const PAC_ALLOCATOR_GUIDE: AiExportToolGuide = {
    toolCode: 'pac_allocator',
    nameKey: 'tools.pacAllocator.name',
    whenKey: 'aiExport.tool.pacAllocator.when',
    returnsKey: 'aiExport.tool.pacAllocator.returns',
    steps: [
        {labelKey: `${PAC}.steps.scenario`, explanationKey: 'aiExport.tool.pacAllocator.steps.scenario', values: {currency: `${PAC}.scenario.currency`}},
        {labelKey: `${PAC}.steps.liquidity`, explanationKey: 'aiExport.tool.pacAllocator.steps.liquidity', values: {contribution: `${PAC}.liquidity.addContribution`}},
        {labelKey: `${PAC}.steps.brokers`, explanationKey: 'aiExport.tool.pacAllocator.steps.brokers'},
        {labelKey: `${PAC}.steps.assets`, explanationKey: 'aiExport.tool.pacAllocator.steps.assets', values: {auto: `${PAC}.mode.auto`}},
        {labelKey: `${PAC}.steps.routing`, explanationKey: 'aiExport.tool.pacAllocator.steps.routing', values: {allowAll: `${PAC}.routing.allowAll`}},
        {labelKey: `${PAC}.steps.targets`, explanationKey: 'aiExport.tool.pacAllocator.steps.targets'},
        {labelKey: `${PAC}.steps.fx`, explanationKey: 'aiExport.tool.pacAllocator.steps.fx', values: {auto: `${PAC}.mode.auto`}},
        {labelKey: `${PAC}.steps.strategy`, explanationKey: 'aiExport.tool.pacAllocator.steps.strategy', values: {proportional: `${PAC}.policies.proportional`}},
        {labelKey: `${PAC}.steps.review`, explanationKey: 'aiExport.tool.pacAllocator.steps.review', values: {calculate: `${PAC}.review.calculate`}},
    ],
};

export const AI_EXPORT_TOOL_GUIDES: Readonly<Record<string, AiExportToolGuide>> = {
    pac_allocator: PAC_ALLOCATOR_GUIDE,
};

/** Whether the frontend can write the block of a tool the backend suggests; an unknown code closes the catalog. */
export function isAiExportToolCode(toolCode: string): boolean {
    return Object.hasOwn(AI_EXPORT_TOOL_GUIDES, toolCode);
}
