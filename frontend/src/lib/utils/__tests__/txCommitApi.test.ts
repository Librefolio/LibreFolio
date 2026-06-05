/**
 * Unit tests for txCommitApi — API wrapper with mocked zodiosApi and trySave.
 */
import {describe, expect, it, vi, beforeEach} from 'vitest';

// Mock modules BEFORE importing the module under test
vi.mock('$lib/api', () => ({
    zodiosApi: {
        commit_transactions_api_v1_transactions_commit_post: vi.fn(),
        validate_transactions_api_v1_transactions_validate_post: vi.fn(),
    },
}));

vi.mock('$lib/utils/trySave', () => ({
    trySave: vi.fn(),
    extractValidationIssues: vi.fn(() => []),
}));

import {commitTransactions, validateTransactions} from '../transactions/txCommitApi';
import {trySave, extractValidationIssues} from '$lib/utils/trySave';

const mockedTrySave = vi.mocked(trySave);
const mockedExtract = vi.mocked(extractValidationIssues);

describe('txCommitApi', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    // =========================================================================
    //  commitTransactions
    // =========================================================================

    describe('commitTransactions', () => {
        it('returns committed=true on successful commit', async () => {
            mockedTrySave.mockResolvedValueOnce({
                status: 'success',
                data: {committed: true, results: [{ids: [1, 2]}]},
            } as any);

            const result = await commitTransactions({creates: [{type: 'BUY'}]});
            expect(result.committed).toBe(true);
            expect(result.issues).toEqual([]);
            expect(result.networkError).toBeUndefined();
        });

        it('returns committed=false with user issues', async () => {
            mockedTrySave.mockResolvedValueOnce({
                status: 'success',
                data: {
                    committed: false,
                    issues: [{operation: 'create', index: 0, error: 'Balance negative', code: 'balanceCashNegative'}],
                },
            } as any);

            const result = await commitTransactions({creates: [{type: 'SELL'}]});
            expect(result.committed).toBe(false);
            expect(result.issues).toHaveLength(1);
            expect(result.issues[0].code).toBe('balanceCashNegative');
        });

        it('filters extra_forbidden issues and logs them', async () => {
            const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
            mockedTrySave.mockResolvedValueOnce({
                status: 'success',
                data: {
                    committed: false,
                    issues: [
                        {operation: 'update', index: 0, error: 'Extra field', code: 'extra_forbidden'},
                        {operation: 'create', index: 1, error: 'Real issue', code: 'missing_field'},
                    ],
                },
            } as any);

            const result = await commitTransactions({updates: [{id: 1}]});
            expect(result.committed).toBe(false);
            expect(result.issues).toHaveLength(1);
            expect(result.issues[0].code).toBe('missing_field');
            expect(consoleSpy).toHaveBeenCalled();
            consoleSpy.mockRestore();
        });

        it('returns networkError on trySave error status', async () => {
            mockedTrySave.mockResolvedValueOnce({
                status: 'error',
                message: 'Server unreachable',
                error: new Error('ECONNREFUSED'),
            } as any);
            mockedExtract.mockReturnValueOnce([]);

            const result = await commitTransactions({creates: [{type: 'BUY'}]}, {fallback: 'Fallback'});
            expect(result.committed).toBe(false);
            expect(result.networkError).toBe('Server unreachable');
        });

        it('extracts validation issues from 422 on network error', async () => {
            const err = new Error('422');
            mockedTrySave.mockResolvedValueOnce({
                status: 'error',
                message: '422 error',
                error: err,
            } as any);
            mockedExtract.mockReturnValueOnce([{msg: 'Field required', code: 'missing', loc: 'body.creates.0.type', params: {}}]);

            const result = await commitTransactions({creates: [{}]});
            expect(result.committed).toBe(false);
            expect(result.issues).toHaveLength(1);
            expect(result.issues[0].error).toBe('Field required');
        });

        it('passes toast=false by default', async () => {
            mockedTrySave.mockResolvedValueOnce({status: 'success', data: {committed: true}} as any);
            await commitTransactions({creates: []});
            expect(mockedTrySave).toHaveBeenCalledWith(expect.any(Function), expect.objectContaining({toast: false}));
        });

        it('passes custom fallback', async () => {
            mockedTrySave.mockResolvedValueOnce({status: 'success', data: {committed: true}} as any);
            await commitTransactions({creates: []}, {fallback: 'Custom error'});
            expect(mockedTrySave).toHaveBeenCalledWith(expect.any(Function), expect.objectContaining({fallback: 'Custom error'}));
        });

        it('exposes rawResponse for callers needing extra fields', async () => {
            const rawResp = {committed: true, results: [{ids: [5]}], extra: 'data'};
            mockedTrySave.mockResolvedValueOnce({status: 'success', data: rawResp} as any);
            const result = await commitTransactions({});
            expect(result.rawResponse).toEqual(rawResp);
        });
    });

    // =========================================================================
    //  validateTransactions
    // =========================================================================

    describe('validateTransactions', () => {
        it('returns committed=true with no issues for valid payload', async () => {
            mockedTrySave.mockResolvedValueOnce({
                status: 'success',
                data: {committed: true, issues: []},
            } as any);

            const result = await validateTransactions({creates: [{type: 'BUY'}]});
            expect(result.committed).toBe(true);
            expect(result.issues).toEqual([]);
        });

        it('returns issues from validate endpoint', async () => {
            mockedTrySave.mockResolvedValueOnce({
                status: 'success',
                data: {committed: false, issues: [{error: 'Required field', code: 'missing'}]},
            } as any);

            const result = await validateTransactions({creates: [{type: 'BUY'}]});
            expect(result.committed).toBe(false);
            expect(result.issues).toHaveLength(1);
        });

        it('returns networkError on trySave error', async () => {
            mockedTrySave.mockResolvedValueOnce({
                status: 'error',
                message: 'Timeout',
                error: new Error('timeout'),
            } as any);
            mockedExtract.mockReturnValueOnce([]);

            const result = await validateTransactions({creates: []});
            expect(result.committed).toBe(false);
            expect(result.networkError).toBe('Timeout');
        });

        it('defaults committed=true when response omits the field', async () => {
            mockedTrySave.mockResolvedValueOnce({
                status: 'success',
                data: {issues: []},
            } as any);

            const result = await validateTransactions({});
            expect(result.committed).toBe(true);
        });
    });
});
