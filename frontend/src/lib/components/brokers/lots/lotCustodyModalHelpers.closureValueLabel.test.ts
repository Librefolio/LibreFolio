/**
 * @vitest-environment node
 *
 * CP-16 (decision 47): in a lot's history, an ADJUSTMENT_OUT row that hands units over at their
 * cost shows that value as «Value handed over at cost», not as «Proceeds»: nothing was sold, the
 * units left at the average cost they carried. `closureValueLabelKey` picks the i18n key of a
 * closure row's value for `LotCustodyModal.svelte` (`eventDetailItems`); every other kind (a SELL,
 * a short's BUY cover) keeps «Proceeds». The keys are asserted, never their translations.
 */
import {describe, expect, it} from 'vitest';
import {closureValueLabelKey} from './lotCustodyModalHelpers';

describe('closureValueLabelKey', () => {
    it('labels the value of an ADJUSTMENT_OUT as handed over at cost', () => {
        expect(closureValueLabelKey('ADJUSTMENT_OUT')).toBe('brokers.lots.modal.historyDetail.handedOverAtCost');
    });

    it.each(['SELL', 'BUY'])('labels the value of a %s as proceeds', (kind) => {
        expect(closureValueLabelKey(kind)).toBe('brokers.lots.modal.historyDetail.proceeds');
    });
});
