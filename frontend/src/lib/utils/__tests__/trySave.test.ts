/**
 * trySave — unit tests
 *
 * The seam every save in the app passes through: twelve call sites hand it a
 * promise and take back a discriminated result, and these five functions decide
 * what the user *reads* when it fails. That makes them worth pinning far more
 * than their size suggests — a wrong branch here is not a broken feature, it is
 * a sentence the user cannot act on.
 *
 * It has already produced one: `extractErrorMessage` returns `detail` verbatim,
 * and the FX route endpoint used to put a driver traceback there, so the add-pair
 * dialog rendered an `INSERT` statement with its bound parameters. The fix went
 * into the backend, but the reason it reached the screen at all is the priority
 * ladder below, and the ladder had no test.
 *
 * `toasts` is mocked: what these functions promise is *which* message comes out
 * and *whether* a toast is raised, not how the toast store renders it.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {extractErrorMessage, extractStatusCode, extractValidationIssues, formatValidationIssues, trySave, type ValidationIssueExtracted} from '../trySave';

const {errorToast} = vi.hoisted(() => ({errorToast: vi.fn()}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({toasts: {error: errorToast}}));

/** An axios-shaped rejection: the only error shape the backend produces. */
function axiosError(status: number, data: unknown, statusText = 'Bad Request'): unknown {
    return {response: {status, statusText, data}, message: `Request failed with status code ${status}`};
}

beforeEach(() => {
    errorToast.mockClear();
    vi.spyOn(console, 'error').mockImplementation(() => {});
});

describe('extractErrorMessage', () => {
    it('falls back when there is no error at all', () => {
        expect(extractErrorMessage(null, 'nothing happened')).toBe('nothing happened');
    });

    describe('the FastAPI detail, which wins over everything else', () => {
        it('uses a string detail as it stands', () => {
            expect(extractErrorMessage(axiosError(409, {detail: 'Route already exists'}))).toBe('Route already exists');
        });

        it('reads `message` out of an object detail', () => {
            expect(extractErrorMessage(axiosError(400, {detail: {message: 'Validation failed for 2 routes'}}))).toBe('Validation failed for 2 routes');
        });

        it('accepts `error` and `detail` as the object key too', () => {
            expect(extractErrorMessage(axiosError(400, {detail: {error: 'boom'}}))).toBe('boom');
            expect(extractErrorMessage(axiosError(400, {detail: {detail: 'nested'}}))).toBe('nested');
        });

        it('summarises a pydantic issue array through the shared formatter', () => {
            const err = axiosError(422, {detail: [{loc: ['body', 'creates', 0, 'asset_id'], msg: 'BUY requires asset_id', type: 'value_error'}]});
            expect(extractErrorMessage(err)).toBe('asset_id: BUY requires asset_id');
        });

        it('summarises an array of loose messages through the same formatter', () => {
            // `msg ?? message` — the issue extractor accepts either key, so an
            // array that is not pydantic-shaped still goes through it. With no
            // `loc` there is no leaf to prefix, so the messages come out joined
            // and bare.
            const err = axiosError(400, {detail: [{message: 'first thing'}, {message: 'second'}]});
            expect(extractErrorMessage(err)).toBe('first thing · second');
        });

        it('falls past a detail that is neither text nor a structure', () => {
            // `typeof detail === 'object'` is false for a number, so the ladder
            // moves on rather than reading properties off it.
            expect(extractErrorMessage(axiosError(500, {detail: 42}, 'Server Error'))).toBe('HTTP 500 — Server Error');
        });

        it('falls past an array of nothing but junk, rather than inventing a message', () => {
            // Every entry is a non-object, so the issue extractor yields nothing.
            // There used to be a block here that read `detail[0].msg` for this
            // case; it was unreachable by construction — an array whose first
            // element is an object always produces at least one issue — and it
            // has been removed.
            const err = axiosError(500, {detail: ['just', 'strings']}, 'Server Error');
            expect(extractErrorMessage(err)).toBe('HTTP 500 — Server Error');
        });

        it('stringifies a non-string message rather than dropping it', () => {
            expect(extractErrorMessage(axiosError(400, {detail: {message: 500}}))).toBe('500');
        });

        it('falls through an empty detail array rather than returning nothing', () => {
            expect(extractErrorMessage(axiosError(500, {detail: []}, 'Server Error'), 'fb')).toBe('HTTP 500 — Server Error');
        });

        it('yields an empty message for an issue that carries neither key', () => {
            // `msg ?? message ?? ''` — the last rung. The entry is still counted,
            // because a location with no text is more useful than silence.
            const err = axiosError(422, {detail: [{loc: ['body', 'creates', 0, 'asset_id']}]});
            expect(extractValidationIssues(err)[0]).toMatchObject({loc: 'body.creates.0.asset_id', msg: ''});
        });
    });

    describe('the rungs below the detail', () => {
        it('names the status when there is no detail', () => {
            expect(extractErrorMessage(axiosError(503, {}, 'Service Unavailable'))).toBe('HTTP 503 — Service Unavailable');
        });

        it('uses a native Error message when there is no response at all', () => {
            expect(extractErrorMessage(new Error('Network Error'))).toBe('Network Error');
        });

        it('stringifies anything else', () => {
            expect(extractErrorMessage('a bare string')).toBe('a bare string');
        });
    });
});

describe('extractStatusCode', () => {
    it('reads the status off an axios error', () => {
        expect(extractStatusCode(axiosError(409, {}))).toBe(409);
    });

    it('is undefined for an error that never reached the server', () => {
        expect(extractStatusCode(new Error('Network Error'))).toBeUndefined();
        expect(extractStatusCode(null)).toBeUndefined();
    });
});

describe('extractValidationIssues', () => {
    it('is empty for anything that is not a detail array', () => {
        expect(extractValidationIssues(axiosError(500, {detail: 'plain'}))).toEqual([]);
        expect(extractValidationIssues(new Error('nope'))).toEqual([]);
    });

    it('joins the location path with dots', () => {
        const err = axiosError(422, {detail: [{loc: ['body', 'creates', 0, 'cash', 'amount'], msg: 'must be > 0', type: 'greater_than'}]});
        expect(extractValidationIssues(err)[0]).toMatchObject({loc: 'body.creates.0.cash.amount', msg: 'must be > 0', type: 'greater_than', code: 'greater_than'});
    });

    it('strips the "Value error, " that pydantic v2 prefixes', () => {
        const err = axiosError(422, {detail: [{loc: ['body'], msg: 'Value error, BUY requires asset_id'}]});
        expect(extractValidationIssues(err)[0].msg).toBe('BUY requires asset_id');
    });

    it('strips the prefix whatever its casing', () => {
        const err = axiosError(422, {detail: [{loc: ['body'], msg: 'VALUE ERROR, shouted'}]});
        expect(extractValidationIssues(err)[0].msg).toBe('shouted');
    });

    it('carries the structured context through when there is one', () => {
        const err = axiosError(422, {detail: [{loc: ['body'], msg: 'x', type: 'assetRequired', ctx: {type: 'BUY'}}]});
        expect(extractValidationIssues(err)[0]).toMatchObject({code: 'assetRequired', params: {type: 'BUY'}});
    });

    it('leaves params out when the context is not an object', () => {
        const err = axiosError(422, {detail: [{loc: ['body'], msg: 'x', ctx: 'not an object'}]});
        expect(extractValidationIssues(err)[0].params).toBeUndefined();
    });

    it('unpacks a multi-error into one issue per business rule, all sharing the row', () => {
        // The model validator packs every business-rule failure of one row into a
        // single pydantic entry; unpacked, they are what the user has to fix.
        const err = axiosError(422, {
            detail: [
                {
                    loc: ['body', 'creates', 1],
                    type: 'multipleBusinessRuleErrors',
                    ctx: {
                        errors: [
                            {msg: 'BUY requires asset_id', code: 'assetRequired', ctx: {type: 'BUY'}},
                            {msg: 'quantity must be positive', code: 'quantityPositive'},
                        ],
                    },
                },
            ],
        });
        const issues = extractValidationIssues(err);
        expect(issues).toHaveLength(2);
        expect(issues.map((i) => i.code)).toEqual(['assetRequired', 'quantityPositive']);
        expect(new Set(issues.map((i) => i.loc))).toEqual(new Set(['body.creates.1']));
        expect(issues[0].params).toEqual({type: 'BUY'});
        expect(issues[1].params).toBeUndefined();
    });

    it('reads an empty message off a packed business rule without dropping it', () => {
        // `String(sub.msg ?? '')` — a rule that fired with no text is still a
        // rule the user has to satisfy, so it keeps its row.
        const err = axiosError(422, {detail: [{loc: ['body', 'creates', 0], type: 'multipleBusinessRuleErrors', ctx: {errors: [{code: 'silentRule'}]}}]});
        expect(extractValidationIssues(err)).toEqual([expect.objectContaining({code: 'silentRule', msg: ''})]);
    });

    it('treats a multi-error with no error list as an ordinary issue', () => {
        const err = axiosError(422, {detail: [{loc: ['body'], type: 'multipleBusinessRuleErrors', msg: 'packed', ctx: {}}]});
        expect(extractValidationIssues(err)).toEqual([expect.objectContaining({msg: 'packed', code: 'multipleBusinessRuleErrors'})]);
    });

    it('skips entries that are not objects', () => {
        const err = axiosError(422, {detail: [null, 'string', {loc: ['body'], msg: 'real'}]});
        expect(extractValidationIssues(err)).toHaveLength(1);
    });

    it('tolerates a location that is not an array', () => {
        expect(extractValidationIssues(axiosError(422, {detail: [{loc: 'body.x', msg: 'm'}]}))[0].loc).toBe('body.x');
        expect(extractValidationIssues(axiosError(422, {detail: [{msg: 'm'}]}))[0].loc).toBe('');
    });
});

describe('formatValidationIssues', () => {
    const issue = (loc: string, msg: string): ValidationIssueExtracted => ({loc, msg});

    it('is empty for no issues', () => {
        expect(formatValidationIssues([])).toBe('');
    });

    describe('the leaf it puts in front of the message', () => {
        it('drops the "body" and the operation, keeping the field', () => {
            expect(formatValidationIssues([issue('body.creates.0.asset_id', 'required')])).toBe('asset_id: required');
        });

        it('keeps a nested field path whole, without its row index', () => {
            expect(formatValidationIssues([issue('body.updates.2.cash.amount', 'must be > 0')])).toBe('cash.amount: must be > 0');
        });

        it('names the row, counting from one, when pydantic stopped at the index', () => {
            // `body.creates.0` is the *first* row as the user sees it.
            expect(formatValidationIssues([issue('body.creates.0', 'bad row')])).toBe('row 1: bad row');
        });

        it('shows the message alone when nothing is left of the path', () => {
            expect(formatValidationIssues([issue('body', 'whole batch refused')])).toBe('whole batch refused');
            expect(formatValidationIssues([issue('', 'no location')])).toBe('no location');
        });

        it('handles the deletes operation like the other two', () => {
            expect(formatValidationIssues([issue('body.deletes.0.id', 'unknown')])).toBe('id: unknown');
        });
    });

    it('joins several issues with a separator', () => {
        const out = formatValidationIssues([issue('body.creates.0.asset_id', 'required'), issue('body.creates.0.quantity', 'must be > 0')]);
        expect(out).toBe('asset_id: required · quantity: must be > 0');
    });

    describe('truncation', () => {
        const many = (n: number) => Array.from({length: n}, (_, i) => issue(`body.creates.${i}.f${i}`, `m${i}`));

        it('says how many it did not show', () => {
            const out = formatValidationIssues(many(8));
            expect(out).toContain('… +3 more');
            expect(out).toContain('f0: m0');
            expect(out).not.toContain('f5: m5');
        });

        it('says nothing extra when everything fits', () => {
            expect(formatValidationIssues(many(5))).not.toContain('more');
        });

        it('honours a caller-chosen limit', () => {
            expect(formatValidationIssues(many(4), 2)).toContain('… +2 more');
        });
    });
});

describe('trySave', () => {
    it('passes the value through on success, and raises nothing', async () => {
        const result = await trySave(async () => ({id: 7}));
        expect(result).toEqual({status: 'success', data: {id: 7}});
        expect(errorToast).not.toHaveBeenCalled();
    });

    it('reports the failure with the extracted message and the status', async () => {
        const err = axiosError(409, {detail: 'conflict'});
        const result = await trySave(async () => {
            throw err;
        });
        expect(result).toEqual({status: 'error', message: 'conflict', error: err, status_code: 409});
    });

    it('raises a toast by default', async () => {
        await trySave(async () => {
            throw axiosError(500, {detail: 'boom'}, 'Server Error');
        });
        expect(errorToast).toHaveBeenCalledWith('boom');
    });

    it('stays silent when the caller renders the error itself', async () => {
        const result = await trySave(
            async () => {
                throw axiosError(400, {detail: 'inline please'});
            },
            {toast: false},
        );
        expect(errorToast).not.toHaveBeenCalled();
        expect(result.status === 'error' && result.message).toBe('inline please');
    });

    it('puts the prefix in front of both the result and the toast', async () => {
        const result = await trySave(
            async () => {
                throw axiosError(400, {detail: 'no'});
            },
            {prefix: 'Apple Inc.'},
        );
        expect(result.status === 'error' && result.message).toBe('Apple Inc.: no');
        expect(errorToast).toHaveBeenCalledWith('Apple Inc.: no');
    });

    it('reaches the caller fallback whenever the error says nothing useful', async () => {
        const result = await trySave(
            async () => {
                throw undefined;
            },
            {fallback: 'Impossibile salvare'},
        );
        expect(result.status === 'error' && result.message).toBe('Impossibile salvare');
    });

    describe('a message that exists and reports nothing', () => {
        // `fallback` is the caller's own translated sentence, and it used to be
        // nearly unreachable: the ladder ends at `String(err)`, which always
        // produces *something*, so `new Error('')` reached the user as the word
        // "Error" while twelve call sites held a good message in four languages.
        it.each([
            ['an Error with no text', new Error(''), 'Error'],
            ['a subclass with no text', new TypeError(''), 'TypeError'],
            ['a bare object', {}, '[object Object]'],
            ['an empty array', [], ''],
            ['an axios error with neither detail nor statusText', {response: {status: 500, data: {}}}, '[object Object]'],
        ])('prefers the fallback over %s', (_label, thrown, wouldHaveBeen) => {
            expect(String(thrown)).toBe(wouldHaveBeen);
            expect(extractErrorMessage(thrown, 'Impossibile salvare')).toBe('Impossibile salvare');
        });

        it.each([
            ['a real Error message', new Error('Network Error'), 'Network Error'],
            ['a message that merely contains the word', new Error('Error while parsing row 3'), 'Error while parsing row 3'],
            ['a detail the server chose', {response: {status: 409, data: {detail: 'Route already exists'}}}, 'Route already exists'],
        ])('keeps %s', (_label, thrown, expected) => {
            expect(extractErrorMessage(thrown, 'Impossibile salvare')).toBe(expected);
        });
    });

    describe('the pre-handler', () => {
        it('sees the raw error, and suppresses the toast when it claims it', async () => {
            const err = axiosError(409, {detail: 'needs a modal'});
            const onError = vi.fn(() => true);
            const result = await trySave(
                async () => {
                    throw err;
                },
                {onError},
            );
            expect(onError).toHaveBeenCalledWith(err);
            expect(errorToast).not.toHaveBeenCalled();
            // Consumed is about the *toast*, not about the result: the caller
            // still gets the message and the status it needs to act on.
            expect(result.status === 'error' && result.message).toBe('needs a modal');
            expect(result.status === 'error' && result.status_code).toBe(409);
        });

        it.each([
            ['false', false],
            ['nothing', undefined],
        ])('falls through to the toast when it returns %s', async (_label, verdict) => {
            await trySave(
                async () => {
                    throw axiosError(400, {detail: 'unhandled'});
                },
                {onError: () => verdict as boolean | void},
            );
            expect(errorToast).toHaveBeenCalledWith('unhandled');
        });
    });

    it('logs every failure, even the ones it does not announce', async () => {
        // The toast is optional; the stack trace in DevTools is not.
        const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
        await trySave(
            async () => {
                throw axiosError(400, {detail: 'quiet'});
            },
            {toast: false},
        );
        expect(spy).toHaveBeenCalled();
    });
});
