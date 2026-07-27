import {AxiosError, AxiosHeaders, type InternalAxiosRequestConfig} from 'axios';
import {describe, expect, it} from 'vitest';

import {schemas} from '$lib/api';

import {
    AiExportContractMismatchError,
    AiExportNetworkError,
    AiExportProblemError,
    AiExportUnknownError,
    AiExportValidationError,
    canonicalizeAiExportSnapshotRequest,
    fetchAiExportSnapshot,
    type AiExportAssetSnapshotRequestInput,
    type AiExportBrokerSnapshotRequestInput,
    type AiExportCompatibleCatalogChoice,
    type AiExportFxSnapshotRequestInput,
    type AiExportPortfolioSnapshotRequestInput,
    type AiExportSnapshotRequest,
    type AiExportSnapshotRequestInput,
    type AiExportSnapshotResponse,
    type AiExportSnapshotTransport,
} from '../aiExportClient';
import {AI_EXPORT_LOCAL_CHOICES} from '../catalog/compatibility';
import {AI_EXPORT_SNAPSHOT_SCHEMA_VERSION} from '../catalog/shared';

const EXPORT_STATS = schemas.AiExportExportStats.parse({
    canonical_json: {
        positions: 1,
        technical_assets: 1,
        series_points: 2,
        events: 1,
        serialized_characters: 400,
    },
    token_estimate: {
        method: 'chars_div_4_v1',
        estimated_tokens: 100,
    },
});

const PORTFOLIO_REQUEST = {
    domain: 'portfolio',
    task: 'portfolio_description',
    detail_level: 'standard',
    date_range: {start: '2026-01-01', end: '2026-06-30'},
    target_currency: 'EUR',
    broker_ids: [1, 2],
} satisfies AiExportPortfolioSnapshotRequestInput;

const ASSET_REQUEST = {
    domain: 'asset',
    task: 'asset_snapshot',
    detail_level: 'compact',
    date_range: {start: '2026-02-01', end: '2026-06-30'},
    target_currency: 'EUR',
    asset_id: 42,
    broker_ids: [1],
} satisfies AiExportAssetSnapshotRequestInput;

const FX_REQUEST = {
    domain: 'fx',
    task: 'fx_trend_review',
    detail_level: 'full',
    date_range: {start: '2026-03-01', end: '2026-06-30'},
    target_currency: 'EUR',
    base_currency: 'USD',
    quote_currency: 'EUR',
    broker_ids: null,
} satisfies AiExportFxSnapshotRequestInput;

const BROKER_REQUEST = {
    domain: 'broker',
    task: 'broker_review',
    detail_level: 'standard',
    date_range: {start: '2026-04-01', end: null},
    target_currency: 'EUR',
    broker_id: 7,
} satisfies AiExportBrokerSnapshotRequestInput;

const REQUESTS = [PORTFOLIO_REQUEST, ASSET_REQUEST, FX_REQUEST, BROKER_REQUEST] as const satisfies readonly AiExportSnapshotRequestInput[];

describe('AI Export snapshot client', () => {
    it('sends and returns generated-schema requests for all four domains', async () => {
        for (const requestInput of REQUESTS) {
            const request = parseSnapshotRequest(requestInput);
            const choice = buildCompatibleChoice(request);
            const response = buildSnapshotResponse(request, choice);
            const received: AiExportSnapshotRequest[] = [];
            const transport: AiExportSnapshotTransport = async (transportRequest) => {
                received.push(transportRequest);
                return response;
            };

            const result = await fetchAiExportSnapshot(requestInput, choice, transport);

            expect(received).toEqual([request]);
            expect(result).toEqual(response);
            expect(result.domain).toBe(request.domain);
            expect(result.task).toBe(request.task);
            expect(result.detail_level).toBe(request.detail_level);
        }
    });

    it('canonicalizes currencies, single-day ranges, and broker order without mutating input', async () => {
        const requestInput = {
            domain: 'fx',
            task: 'fx_trend_review',
            detail_level: 'standard',
            date_range: {start: '2026-07-01'},
            target_currency: ' eur ',
            base_currency: ' usd ',
            quote_currency: ' eur ',
            broker_ids: [2, 1],
        } satisfies AiExportFxSnapshotRequestInput;
        const canonicalRequest = parseSnapshotRequest(requestInput);
        const choice = buildCompatibleChoice(canonicalRequest);
        const received: AiExportSnapshotRequest[] = [];
        const transport: AiExportSnapshotTransport = async (request) => {
            received.push(request);
            return buildSnapshotResponse(request, choice);
        };

        const response = await fetchAiExportSnapshot(requestInput, choice, transport);

        expect(requestInput).toEqual({
            domain: 'fx',
            task: 'fx_trend_review',
            detail_level: 'standard',
            date_range: {start: '2026-07-01'},
            target_currency: ' eur ',
            base_currency: ' usd ',
            quote_currency: ' eur ',
            broker_ids: [2, 1],
        });
        expect(received).toEqual([
            {
                domain: 'fx',
                task: 'fx_trend_review',
                detail_level: 'standard',
                date_range: {start: '2026-07-01', end: '2026-07-01'},
                target_currency: 'EUR',
                base_currency: 'USD',
                quote_currency: 'EUR',
                broker_ids: [1, 2],
            },
        ]);
        expect(response.meta.selected_range).toEqual({start: '2026-07-01', end: '2026-07-01'});
        expect(response.meta.target_currency).toBe('EUR');
    });

    it('rejects duplicate and nonpositive broker IDs before transport', async () => {
        const validRequest = parseSnapshotRequest(PORTFOLIO_REQUEST);
        const choice = buildCompatibleChoice(validRequest);
        let called = false;
        const transport: AiExportSnapshotTransport = async () => {
            called = true;
            return buildSnapshotResponse(validRequest, choice);
        };
        const invalidBrokerIds = [[2, 2], [1, 0], []];

        for (const brokerIds of invalidBrokerIds) {
            const request = {
                ...PORTFOLIO_REQUEST,
                broker_ids: brokerIds,
            } satisfies AiExportPortfolioSnapshotRequestInput;

            await expect(fetchAiExportSnapshot(request, choice, transport)).rejects.toMatchObject({
                kind: 'validation',
                source: 'request',
            });
        }
        expect(called).toBe(false);
    });

    it('keeps malformed request failures normalized after canonicalization', async () => {
        const validRequest = parseSnapshotRequest(PORTFOLIO_REQUEST);
        const choice = buildCompatibleChoice(validRequest);
        let called = false;
        const malformedRequest = {
            ...PORTFOLIO_REQUEST,
            date_range: null,
        } as unknown as AiExportPortfolioSnapshotRequestInput;
        const transport: AiExportSnapshotTransport = async () => {
            called = true;
            return buildSnapshotResponse(validRequest, choice);
        };

        await expect(fetchAiExportSnapshot(malformedRequest, choice, transport)).rejects.toMatchObject({
            kind: 'validation',
            source: 'request',
        });
        expect(called).toBe(false);
    });

    it('keeps date ranges scalar and broker ID arrays flat at compile time', () => {
        const validRequest = {
            domain: 'portfolio',
            task: 'portfolio_description',
            detail_level: 'standard',
            date_range: {start: '2026-01-01', end: null},
            target_currency: 'EUR',
            broker_ids: [1, 2],
        } satisfies AiExportPortfolioSnapshotRequestInput;
        const invalidDateRequest = {
            ...validRequest,
            date_range: {
                start: '2026-01-01',
                // @ts-expect-error AI Export date values are scalar strings.
                end: ['2026-06-30'],
            },
        } satisfies AiExportPortfolioSnapshotRequestInput;
        const invalidBrokerRequest = {
            ...validRequest,
            // @ts-expect-error AI Export broker IDs use one flat numeric array.
            broker_ids: [[1, 2]],
        } satisfies AiExportPortfolioSnapshotRequestInput;

        expect(validRequest.broker_ids).toEqual([1, 2]);
        expect(invalidDateRequest.date_range.end).toEqual(['2026-06-30']);
        expect(invalidBrokerRequest.broker_ids).toEqual([[1, 2]]);
    });

    it('fails closed for every required response mismatch field', async () => {
        const request = parseSnapshotRequest(PORTFOLIO_REQUEST);
        const choice = buildCompatibleChoice(request);
        const baseResponse = schemas.AiExportPortfolioSnapshotResponse.parse(buildSnapshotResponse(request, choice));
        const assetRequest = parseSnapshotRequest(ASSET_REQUEST);
        const assetChoice = buildCompatibleChoice(assetRequest);

        const cases: ReadonlyArray<{field: string; response: AiExportSnapshotResponse}> = [
            {
                field: 'response.domain',
                response: buildSnapshotResponse(assetRequest, assetChoice),
            },
            {
                field: 'response.task',
                response: schemas.AiExportPortfolioSnapshotResponse.parse({...baseResponse, task: 'income_review'}),
            },
            {
                field: 'response.detail_level',
                response: schemas.AiExportPortfolioSnapshotResponse.parse({...baseResponse, detail_level: 'full'}),
            },
            {
                field: 'response.meta.schema_version',
                response: schemas.AiExportPortfolioSnapshotResponse.parse({...baseResponse, meta: {...baseResponse.meta, schema_version: AI_EXPORT_SNAPSHOT_SCHEMA_VERSION + 1}}),
            },
            {
                field: 'response.meta.profile_id',
                response: schemas.AiExportPortfolioSnapshotResponse.parse({...baseResponse, meta: {...baseResponse.meta, profile_id: 'portfolio.portfolio_description.other'}}),
            },
            {
                field: 'response.meta.profile_version',
                response: schemas.AiExportPortfolioSnapshotResponse.parse({...baseResponse, meta: {...baseResponse.meta, profile_version: 2}}),
            },
            {
                field: 'response.meta.frontend_response_contract_id',
                response: schemas.AiExportPortfolioSnapshotResponse.parse({...baseResponse, meta: {...baseResponse.meta, frontend_response_contract_id: 'portfolio.income_review'}}),
            },
            {
                field: 'response.meta.frontend_response_contract_version',
                response: schemas.AiExportPortfolioSnapshotResponse.parse({...baseResponse, meta: {...baseResponse.meta, frontend_response_contract_version: 2}}),
            },
            {
                field: 'response.meta.selected_range.start',
                response: schemas.AiExportPortfolioSnapshotResponse.parse({...baseResponse, meta: {...baseResponse.meta, selected_range: {...baseResponse.meta.selected_range, start: '2025-12-31'}}}),
            },
            {
                field: 'response.meta.selected_range.end',
                response: schemas.AiExportPortfolioSnapshotResponse.parse({...baseResponse, meta: {...baseResponse.meta, selected_range: {...baseResponse.meta.selected_range, end: '2026-06-29'}}}),
            },
            {
                field: 'response.meta.target_currency',
                response: schemas.AiExportPortfolioSnapshotResponse.parse({...baseResponse, meta: {...baseResponse.meta, target_currency: 'USD'}}),
            },
        ];

        for (const mismatchCase of cases) {
            const transport: AiExportSnapshotTransport = async () => mismatchCase.response;

            try {
                await fetchAiExportSnapshot(PORTFOLIO_REQUEST, choice, transport);
                throw new Error(`Expected mismatch for ${mismatchCase.field}`);
            } catch (error) {
                expect(error).toBeInstanceOf(AiExportContractMismatchError);
                if (error instanceof AiExportContractMismatchError) {
                    expect(error.mismatches.map((mismatch) => mismatch.field)).toContain(mismatchCase.field);
                }
            }
        }
    });

    it('rejects a non-compatible catalog choice before transport', async () => {
        const request = parseSnapshotRequest(PORTFOLIO_REQUEST);
        const choice = buildCompatibleChoice(request);
        let called = false;
        const transport: AiExportSnapshotTransport = async () => {
            called = true;
            return buildSnapshotResponse(request, choice);
        };
        const disabledChoice = {
            ...choice,
            status: 'disabled',
            reasonCode: 'profile_version_mismatch',
        } satisfies typeof choice | (Omit<typeof choice, 'status' | 'reasonCode'> & {status: 'disabled'; reasonCode: 'profile_version_mismatch'});

        await expect(fetchAiExportSnapshot(PORTFOLIO_REQUEST, disabledChoice, transport)).rejects.toBeInstanceOf(AiExportContractMismatchError);
        expect(called).toBe(false);
    });

    it('normalizes typed problem, validation, network, and unknown failures', async () => {
        const request = parseSnapshotRequest(PORTFOLIO_REQUEST);
        const choice = buildCompatibleChoice(request);
        const problem = schemas.AiExportProblemResponse.parse({
            detail: {
                message: 'Task is not applicable',
                domain: request.domain,
                task: request.task,
                detail_level: request.detail_level,
                profile_id: choice.profileId,
                code: 'task_not_applicable',
                applicability_code: 'requires_open_position',
            },
        });
        const invalidResponse = schemas.AiExportPortfolioSnapshotResponse.safeParse({});
        if (invalidResponse.success) throw new Error('Invalid response fixture unexpectedly parsed');

        const failures: ReadonlyArray<{
            expectedClass: typeof AiExportProblemError | typeof AiExportValidationError | typeof AiExportNetworkError | typeof AiExportUnknownError;
            error: unknown;
            kind: 'problem' | 'validation' | 'network' | 'unknown';
        }> = [
            {
                expectedClass: AiExportProblemError,
                error: buildAxiosError(409, problem),
                kind: 'problem',
            },
            {
                expectedClass: AiExportValidationError,
                error: invalidResponse.error,
                kind: 'validation',
            },
            {
                expectedClass: AiExportNetworkError,
                error: new AxiosError('Network unavailable', AxiosError.ERR_NETWORK),
                kind: 'network',
            },
            {
                expectedClass: AiExportUnknownError,
                error: new Error('Unexpected transport failure'),
                kind: 'unknown',
            },
        ];

        for (const failure of failures) {
            const transport: AiExportSnapshotTransport = async () => {
                throw failure.error;
            };

            try {
                await fetchAiExportSnapshot(PORTFOLIO_REQUEST, choice, transport);
                throw new Error(`Expected ${failure.kind} error`);
            } catch (error) {
                expect(error).toBeInstanceOf(failure.expectedClass);
                expect(error).toMatchObject({kind: failure.kind});
            }
        }
    });

    it('normalizes FastAPI validation responses separately from typed AI Export problems', async () => {
        const request = parseSnapshotRequest(PORTFOLIO_REQUEST);
        const choice = buildCompatibleChoice(request);
        const validation = schemas.HTTPValidationError.parse({
            detail: [
                {
                    loc: ['body', 'target_currency'],
                    msg: 'Field required',
                    type: 'missing',
                },
            ],
        });
        const transport: AiExportSnapshotTransport = async () => {
            throw buildAxiosError(422, validation);
        };

        try {
            await fetchAiExportSnapshot(PORTFOLIO_REQUEST, choice, transport);
            throw new Error('Expected HTTP validation error');
        } catch (error) {
            expect(error).toBeInstanceOf(AiExportValidationError);
            expect(error).toMatchObject({kind: 'validation', source: 'http', status: 422});
        }
    });
});

function parseSnapshotRequest(request: AiExportSnapshotRequestInput): AiExportSnapshotRequest {
    return schemas.build_ai_export_snapshot_api_v1_ai_export_snapshot_post_Body.parse(canonicalizeAiExportSnapshotRequest(request)) as AiExportSnapshotRequest;
}

function buildCompatibleChoice(request: AiExportSnapshotRequest): AiExportCompatibleCatalogChoice {
    const localChoice = AI_EXPORT_LOCAL_CHOICES.find((choice) => choice.domain === request.domain && choice.backendTask === request.task && choice.detailLevel === request.detail_level);
    if (!localChoice) throw new Error(`Missing local choice for ${request.domain}.${request.task}.${request.detail_level}`);

    const backendEntry = schemas.AiExportCatalogEntry.parse({
        domain: localChoice.domain,
        task: localChoice.backendTask,
        detail_level: localChoice.detailLevel,
        profile_id: localChoice.profileId,
        profile_version: localChoice.profileVersion,
        frontend_response_contract_id: localChoice.frontendResponseContractId,
        frontend_response_contract_version: localChoice.frontendResponseContractVersion,
        applicability_code: 'always',
        supports_user_notes: localChoice.supportsUserNotes,
        supports_web_research: localChoice.supportsWebResearch,
    });

    return {
        ...localChoice,
        status: 'compatible',
        reasonCode: null,
        backendEntry,
    };
}

function buildSnapshotResponse(request: AiExportSnapshotRequest, choice: AiExportCompatibleCatalogChoice): AiExportSnapshotResponse {
    const common = {
        domain: request.domain,
        task: request.task,
        detail_level: request.detail_level,
        meta: {
            schema_version: AI_EXPORT_SNAPSHOT_SCHEMA_VERSION,
            profile_id: choice.profileId,
            profile_version: choice.profileVersion,
            frontend_response_contract_id: choice.frontendResponseContractId,
            frontend_response_contract_version: choice.frontendResponseContractVersion,
            generated_at: '2026-07-26T12:00:00Z',
            snapshot_as_of: '2026-06-30',
            selected_range: request.date_range,
            target_currency: request.target_currency,
        },
        methodology: {},
        states: [],
        events: [],
        coverage: {},
        semantics: {},
        domain_notes: [],
        export_stats: EXPORT_STATS,
    };

    switch (request.domain) {
        case 'portfolio':
            return schemas.AiExportPortfolioSnapshotResponse.parse({
                ...common,
                facts: {
                    summary: {
                        base_currency: request.target_currency,
                        nav: money(request.target_currency, '1000'),
                        market_value: money(request.target_currency, '900'),
                        cash: money(request.target_currency, '100'),
                        book_value: money(request.target_currency, '800'),
                    },
                },
            });
        case 'asset':
            return schemas.AiExportAssetSnapshotResponse.parse({
                ...common,
                facts: {
                    identity: {
                        asset_id: request.asset_id,
                        name: 'Example Asset',
                        trading_currency: 'USD',
                        valuation_currency: request.target_currency,
                    },
                },
            });
        case 'fx':
            return schemas.AiExportFxSnapshotResponse.parse({
                ...common,
                facts: {
                    identity: {
                        base_currency: request.base_currency,
                        quote_currency: request.quote_currency,
                    },
                    current_rate: {
                        date: '2026-06-30',
                        rate: '0.92',
                        provider: 'ECB',
                    },
                },
            });
        case 'broker':
            return schemas.AiExportBrokerSnapshotResponse.parse({
                ...common,
                facts: {
                    summary: {
                        broker_id: request.broker_id,
                        name: 'Example Broker',
                        base_currency: request.target_currency,
                        nav: money(request.target_currency, '1000'),
                        market_value: money(request.target_currency, '900'),
                        cash: money(request.target_currency, '100'),
                    },
                },
            });
    }
}

function money(code: string, amount: string): {code: string; amount: string} {
    return {code, amount};
}

function buildAxiosError(status: number, data: unknown): AxiosError<unknown> {
    const config: InternalAxiosRequestConfig = {
        headers: new AxiosHeaders(),
    };
    return new AxiosError('Request failed', AxiosError.ERR_BAD_RESPONSE, config, undefined, {
        config,
        data,
        headers: new AxiosHeaders(),
        status,
        statusText: 'Request failed',
    });
}
