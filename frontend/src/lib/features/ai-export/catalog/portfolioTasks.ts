import {defineAiExportTask} from './shared';

export const PORTFOLIO_AI_EXPORT_TASKS = [
    defineAiExportTask({
        domain: 'portfolio',
        backendTask: 'pac_planning',
        icon: 'PiggyBank',
        supportsUserNotes: true,
        supportsWebResearch: true,
    }),
    defineAiExportTask({
        domain: 'portfolio',
        backendTask: 'rebalancing',
        icon: 'Scale',
        supportsUserNotes: true,
        supportsWebResearch: true,
    }),
    defineAiExportTask({
        domain: 'portfolio',
        backendTask: 'performance_attribution',
        icon: 'ChartColumn',
        supportsUserNotes: true,
        supportsWebResearch: false,
    }),
    defineAiExportTask({
        domain: 'portfolio',
        backendTask: 'income_review',
        icon: 'Coins',
        supportsUserNotes: true,
        supportsWebResearch: false,
    }),
    defineAiExportTask({
        domain: 'portfolio',
        backendTask: 'technical_breadth',
        icon: 'Activity',
        supportsUserNotes: false,
        supportsWebResearch: true,
    }),
    defineAiExportTask({
        domain: 'portfolio',
        backendTask: 'portfolio_description',
        icon: 'FileText',
        supportsUserNotes: true,
        supportsWebResearch: false,
    }),
] as const;
