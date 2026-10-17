/**
 * @vitest-environment node
 *
 * CP-16 (decision 47) and J-10 (decision N76): in a lot's history an ADJUSTMENT_OUT row hands units
 * over — at the cost it carries (CP-16), each at its own FIFO cost when the day has no price at all,
 * or at the market of its day for a TRANSFER leg leaving the broker scope (J-10) — so its value is
 * «Value handed over», never «Proceeds»: nothing was sold. The label is neutral because the price
 * varies: «Value handed over at cost», CP-16's label, is false for a leg that leaves at market, so
 * J-10 renamed the key with it (decision (a') of the coordinator, 17/10):
 * `…historyDetail.handedOverAtCost` → `…historyDetail.handedOver`.
 *
 * `closureValueLabelKey` picks the i18n key of a closure row's value for `LotCustodyModal.svelte`
 * (`eventDetailItems`); every other kind (a SELL, a short's BUY cover) keeps «Proceeds». The keys
 * are asserted, never their translations.
 */
import {describe, expect, it} from 'vitest';

import {schemas} from '$lib/api';

import {closureValueLabelKey} from './lotCustodyModalHelpers';

const HANDED_OVER = 'brokers.lots.modal.historyDetail.handedOver';
const PROCEEDS = 'brokers.lots.modal.historyDetail.proceeds';
/** CP-16's key, retired by J-10. */
const HANDED_OVER_AT_COST = 'brokers.lots.modal.historyDetail.handedOverAtCost';

/** The oracle of «any kind»: the generated client's copy of the backend's LotTimelineEventKind, read apart from the code under test. */
const EVENT_KINDS: readonly string[] = schemas.LotTimelineEventKind.options;

describe('closureValueLabelKey', () => {
    it('labels the value of an ADJUSTMENT_OUT as handed over, with no claim about its price', () => {
        // Before J-10: 'brokers.lots.modal.historyDetail.handedOverAtCost'.
        expect(closureValueLabelKey('ADJUSTMENT_OUT')).toBe(HANDED_OVER);
    });

    it.each(['SELL', 'BUY'])('labels the value of a %s as proceeds', (kind) => {
        expect(closureValueLabelKey(kind)).toBe(PROCEEDS);
    });

    it('returns the retired key handedOverAtCost for no event kind', () => {
        // Positive control: the oracle holds the kinds this file is about, so an empty or renamed enum cannot pass for a clean answer.
        expect(EVENT_KINDS).toEqual(expect.arrayContaining(['ADJUSTMENT_OUT', 'SELL', 'BUY']));
        // Before J-10: ['ADJUSTMENT_OUT'].
        expect(EVENT_KINDS.filter((kind) => closureValueLabelKey(kind) === HANDED_OVER_AT_COST)).toEqual([]);
    });
});
