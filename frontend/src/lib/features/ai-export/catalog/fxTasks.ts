import {defineAiExportTask} from './shared';

export const FX_AI_EXPORT_TASKS = [
    defineAiExportTask({
        domain: 'fx',
        backendTask: 'fx_trend_review',
        icon: 'TrendingUp',
        supportsUserNotes: true,
        supportsWebResearch: true,
    }),
    defineAiExportTask({
        domain: 'fx',
        backendTask: 'fx_exposure_impact',
        icon: 'ArrowLeftRight',
        supportsUserNotes: true,
        supportsWebResearch: true,
    }),
    defineAiExportTask({
        domain: 'fx',
        backendTask: 'fx_conversion_timing_context',
        icon: 'Clock',
        supportsUserNotes: true,
        supportsWebResearch: true,
    }),
] as const;
