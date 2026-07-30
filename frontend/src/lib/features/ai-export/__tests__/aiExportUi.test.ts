import {describe, expect, it} from 'vitest';

import {AiExportProblemError} from '../aiExportClient';
import {buildAiExportMenuLabels, getAiExportErrorMessage} from '../ui';
import {compatibilityFixture} from './runtimeFixtures';

const t = (key: string) => key;

describe('AI Export UI helpers', () => {
    it('builds labels for every real catalog selection', () => {
        const labels = buildAiExportMenuLabels(t, compatibilityFixture(), 'AI Export', 'Preparing');

        expect(Object.keys(labels.options.selectionLabels)).toHaveLength(35);
        expect(labels.options.categoryLabels).toEqual({dataset: 'aiExport.exportData', analysis: 'aiExport.requestAnalysis'});
    });

    it('maps new typed problem codes', () => {
        const error = new AiExportProblemError(
            422,
            {
                code: 'selection_not_applicable',
                message: 'Not applicable',
                domain: 'asset',
                selection_kind: 'analysis',
                selection_id: 'asset.position_review',
                detail_level: 'standard',
                applicability_code: 'requires_position',
                reason_code: 'no_position',
            },
            null,
        );
        expect(getAiExportErrorMessage(t, error)).toBe('aiExport.selectionNotApplicable');
    });
});
