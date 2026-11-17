/**
 * enricherCalls (plan 68, E7b2): a test's answer, and a refused test or search, as the state a row shows.
 */
import {describe, expect, it} from 'vitest';
import {refusalOutcome, testOutcome} from './enricherCalls';
import type {EnricherRecognition} from './enrichersEditState';

const answer = (status: string, name: string | null = null) => ({code: 'x', identifier_type: 'ISIN', identifier: 'X', status, name, page_url: null, identifiers: {}, conflicts: {}, error: null}) as EnricherRecognition;

describe('a test answered', () => {
    it('found keeps the name; not found and conflict say so; anything else is an error', () => {
        expect(testOutcome(answer('found', 'Vanguard'))).toEqual({status: 'found', name: 'Vanguard'});
        expect(testOutcome(answer('not_found'))).toEqual({status: 'not_found', name: null});
        expect(testOutcome(answer('conflict', 'Other'))).toEqual({status: 'conflict', name: null});
        expect(testOutcome(answer('error'))).toEqual({status: 'error', name: null});
    });
});

describe('a call refused', () => {
    it('the coded 422 NOT_CONFIGURED, 404 (turned off), 429 (too many), anything else', () => {
        expect(refusalOutcome({status: 422, data: {detail: {error_code: 'NOT_CONFIGURED', missing: ['k']}}}).status).toBe('not_configured');
        expect(refusalOutcome({response: {status: 404, data: {detail: 'No enricher'}}}).status).toBe('off');
        expect(refusalOutcome({status: 429, data: {detail: {error_code: 'RATE_LIMITED'}}}).status).toBe('rate_limited');
        expect(refusalOutcome(new Error('network')).status).toBe('error');
        expect(refusalOutcome(undefined).status).toBe('error');
    });
});
