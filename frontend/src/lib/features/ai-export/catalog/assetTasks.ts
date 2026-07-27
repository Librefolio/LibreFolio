import {defineAiExportTask} from './shared';

export const ASSET_AI_EXPORT_TASKS = [
    defineAiExportTask({
        domain: 'asset',
        backendTask: 'asset_snapshot',
        icon: 'Camera',
        supportsUserNotes: true,
        supportsWebResearch: true,
    }),
    defineAiExportTask({
        domain: 'asset',
        backendTask: 'asset_trend_analysis',
        icon: 'TrendingUp',
        supportsUserNotes: true,
        supportsWebResearch: true,
    }),
    defineAiExportTask({
        domain: 'asset',
        backendTask: 'position_review',
        icon: 'Briefcase',
        supportsUserNotes: true,
        supportsWebResearch: false,
    }),
    defineAiExportTask({
        domain: 'asset',
        backendTask: 'asset_pac_timing_context',
        icon: 'CalendarClock',
        supportsUserNotes: true,
        supportsWebResearch: true,
    }),
    defineAiExportTask({
        domain: 'asset',
        backendTask: 'drawdown_recovery',
        icon: 'ChartNoAxesCombined',
        supportsUserNotes: true,
        supportsWebResearch: true,
    }),
] as const;
