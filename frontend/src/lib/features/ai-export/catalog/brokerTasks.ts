import {defineAiExportTask} from './shared';

export const BROKER_AI_EXPORT_TASKS = [
    defineAiExportTask({
        domain: 'broker',
        backendTask: 'broker_review',
        icon: 'Landmark',
        supportsUserNotes: true,
        supportsWebResearch: false,
    }),
    defineAiExportTask({
        domain: 'broker',
        backendTask: 'broker_cost_efficiency',
        icon: 'Receipt',
        supportsUserNotes: true,
        supportsWebResearch: false,
    }),
    defineAiExportTask({
        domain: 'broker',
        backendTask: 'broker_concentration_context',
        icon: 'PieChart',
        supportsUserNotes: true,
        supportsWebResearch: false,
    }),
    defineAiExportTask({
        domain: 'broker',
        backendTask: 'broker_fifo_lot_review',
        icon: 'Layers',
        supportsUserNotes: true,
        supportsWebResearch: false,
    }),
] as const;
