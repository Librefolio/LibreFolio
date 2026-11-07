/**
 * amountSentence (P6): the amount is cut out of a translated sentence at its marker, wherever the language puts it.
 */
import {describe, expect, it} from 'vitest';
import {AMOUNT_MARKER, splitAtAmount} from './amountSentence';

describe('splitAtAmount', () => {
    it('cuts at the marker, in the middle of the sentence', () => {
        expect(splitAtAmount(`Make the deposit “X” of ${AMOUNT_MARKER} to the Broker “Y”`)).toEqual({before: 'Make the deposit “X” of ', after: ' to the Broker “Y”'});
    });

    it('lets a language put the amount first or last', () => {
        expect(splitAtAmount(`${AMOUNT_MARKER} to “Y”`)).toEqual({before: '', after: ' to “Y”'});
        expect(splitAtAmount(`Deposit to “Y”: ${AMOUNT_MARKER}`)).toEqual({before: 'Deposit to “Y”: ', after: ''});
    });

    it('ends with the amount when a message has none to place', () => {
        expect(splitAtAmount('Deposit')).toEqual({before: 'Deposit ', after: ''});
    });

    it('keeps a name that looks like markup or like an amount as plain text', () => {
        const text = `Make the deposit «<b>€ 1.200</b> & Co» of ${AMOUNT_MARKER}`;
        expect(splitAtAmount(text)).toEqual({before: 'Make the deposit «<b>€ 1.200</b> & Co» of ', after: ''});
    });
});
