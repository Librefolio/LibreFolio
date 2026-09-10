/**
 * Regression tests for the Tools generated-codec and compute-request wire contracts.
 *
 * Codegen prerequisite: Vite must be able to resolve `$lib/api/generated-tools`
 * and `$lib/api/tool-contract-map.generated`, so their gitignored artifacts
 * must exist before Vitest collects this file. Runtime exports are mocked below
 * to keep these tests independent of the currently generated tool catalogue.
 */
import {afterAll, afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

// ---------------------------------------------------------------------------
// Hoisted shared fixtures. `vi.mock` factories are hoisted above ordinary
// `const` declarations, so anything a factory below needs to reference must
// itself be declared through `vi.hoisted` (plain `vi.fn()` mocks as well as
// plain data) — see e.g. `frontend/src/lib/stores/app/auth.test.ts`.
// ---------------------------------------------------------------------------
const {axiosGet, axiosPost} = vi.hoisted(() => ({axiosGet: vi.fn(), axiosPost: vi.fn()}));

/** Identity of the permissive compiled tool used by the transport-contract cases. */
const DEMO = vi.hoisted(() => {
    return {
        toolCode: 'demo_tool',
        contractVersion: 'v1',
        implementationVersion: 'impl-1',
        schemaFingerprint: 'fp-demo-v1',
        componentKey: 'DemoToolPanel',
        uiContractVersion: 1,
        operation: 'compute',
    } as const;
});

/** Identity of a strict compiled tool used to prove pre-flight input validation sees the snapshot. */
const STRICT = vi.hoisted(() => {
    return {
        toolCode: 'strict_snapshot_tool',
        contractVersion: 'v1',
        implementationVersion: 'impl-1',
        schemaFingerprint: 'fp-strict-v1',
        componentKey: 'StrictSnapshotToolPanel',
        uiContractVersion: 1,
        operation: 'compute',
    } as const;
});

// client.ts imports only `axiosInstance` from '$lib/api'. The real module
// re-exports from './generated' (gitignored codegen output), so an unmocked
// import would fail resolution in a fresh checkout — replaced wholesale here,
// same as txCommitApi.test.ts / auth.test.ts.
vi.mock('$lib/api', () => ({
    axiosInstance: {get: axiosGet, post: axiosPost},
}));

// Generated-module runtime mock. The source artifact must still exist so Vite
// can resolve the import during collection.
vi.mock('$lib/api/generated-tools', async () => {
    const {z} = await import('zod');

    const toolOperationSchema = z.object({operation: z.string()});
    const toolUiSchema = z.object({
        kind: z.literal('custom'),
        component_key: z.string(),
        ui_contract_version: z.number(),
    });
    const toolDescriptorSchema = z.object({
        tool_code: z.string(),
        contract_version: z.string(),
        implementation_version: z.string(),
        schema_fingerprint: z.string(),
        ui: toolUiSchema,
        operations: z.array(toolOperationSchema),
    });
    const toolUnavailableSchema = z.object({
        tool_code: z.string().nullable(),
        reason: z.string(),
    });
    const toolPolicySchema = z.object({client_timeout_ms: z.number()});
    const catalogSchema = z.object({
        items: z.array(toolDescriptorSchema),
        unavailable: z.array(toolUnavailableSchema),
        policy: toolPolicySchema,
    });
    const diagnosticsSchema = z.object({
        loaded: z.array(z.object({tool_code: z.string()})),
    });
    const computeItemSchema = z.object({
        correlation_id: z.string(),
        tool_code: z.string(),
        contract_version: z.string(),
        implementation_version: z.string(),
        schema_fingerprint: z.string(),
        parameters: z.unknown(),
    });
    const computeRequestSchema = z.object({
        request_id: z.string(),
        items: z.array(computeItemSchema),
        // Optional-with-default on purpose: this field is what the "parser
        // expanded defaults are never sent" test proves never reaches the wire.
        // client.ts never sets it, so parsing back the raw request would add
        // it — unless the wire body really is the pre-parse snapshot.
        protocol_hint: z.string().default('v1'),
    });
    const metricsSchema = z.object({duration_ms: z.number()}).nullable().optional();
    const wireResultBaseSchema = z.object({
        correlation_id: z.string(),
        tool_code: z.string(),
        contract_version: z.string(),
        implementation_version: z.string(),
        schema_fingerprint: z.string(),
        execution_id: z.string().nullable(),
        metrics: metricsSchema,
    });
    const wireResultSuccessSchema = wireResultBaseSchema.extend({
        status: z.literal('success'),
        result: z.unknown(),
    });
    const wireResultErrorSchema = wireResultBaseSchema.extend({
        status: z.literal('error'),
        error: z.object({
            issue_count: z.number(),
            issues: z.array(z.unknown()),
        }),
    });
    const computeResponseSchema = z.object({
        request_id: z.string(),
        results: z.array(z.discriminatedUnion('status', [wireResultSuccessSchema, wireResultErrorSchema])),
        success_count: z.number(),
        failed_count: z.number(),
        metrics: metricsSchema,
    });

    return {
        toolTransportSchemas: {
            catalog: catalogSchema,
            diagnostics: diagnosticsSchema,
            computeRequest: computeRequestSchema,
            computeResponse: computeResponseSchema,
        },
    };
});

// Two compiled contracts: one permissive harness tool for the transport-level
// adversarial cases, and one strict input contract that proves validation sees
// the post-snapshot plain JSON rather than the original object graph.
vi.mock('$lib/api/tool-contract-map.generated', async () => {
    const {z} = await import('zod');
    return {
        toolContractMap: {
            [DEMO.toolCode]: {
                [DEMO.contractVersion]: {
                    toolCode: DEMO.toolCode,
                    contractVersion: DEMO.contractVersion,
                    schemaFingerprint: DEMO.schemaFingerprint,
                    componentKey: DEMO.componentKey,
                    uiContractVersion: DEMO.uiContractVersion,
                    input: z.any(),
                    output: z.any(),
                    operations: [DEMO.operation],
                },
            },
            [STRICT.toolCode]: {
                [STRICT.contractVersion]: {
                    toolCode: STRICT.toolCode,
                    contractVersion: STRICT.contractVersion,
                    schemaFingerprint: STRICT.schemaFingerprint,
                    componentKey: STRICT.componentKey,
                    uiContractVersion: STRICT.uiContractVersion,
                    input: z
                        .object({
                            mode: z.literal('plain'),
                            nested: z.object({value: z.string()}),
                        })
                        .strict(),
                    output: z.any(),
                    operations: [STRICT.operation],
                },
            },
        },
    };
});

import {toolTransportSchemas} from '$lib/api/generated-tools';
import {toolContractMap} from '$lib/api/tool-contract-map.generated';
import {getClientSessionUserId, transitionClientSession} from '$lib/stores/app/clientSession';
import {ToolClientError, fetchToolCatalog, runTool} from './client';
import {verifyToolDescriptor} from './contracts';

type DemoResult = {status: 'success'; correlation_id: string; result: unknown} | {status: 'error'; correlation_id: string};

const verifyDescriptorForTest = verifyToolDescriptor as unknown as (catalog: unknown, code: string, version: string) => unknown;
const runToolForTest = runTool as unknown as (code: string, version: string, options: {descriptor: unknown; correlationId: string; parameters: unknown}) => Promise<DemoResult>;
const toolContractMapForTest = toolContractMap as unknown as Record<
    string,
    Record<
        string,
        {
            input: {safeParse: (value: unknown) => {success: boolean}};
        }
    >
>;

/** Raw `/api/v1/tools/catalog` payload describing the compatible tools exercised in this file. */
function rawCatalog() {
    return {
        items: [
            {
                tool_code: DEMO.toolCode,
                contract_version: DEMO.contractVersion,
                implementation_version: DEMO.implementationVersion,
                schema_fingerprint: DEMO.schemaFingerprint,
                ui: {
                    kind: 'custom' as const,
                    component_key: DEMO.componentKey,
                    ui_contract_version: DEMO.uiContractVersion,
                },
                operations: [{operation: DEMO.operation}],
            },
            {
                tool_code: STRICT.toolCode,
                contract_version: STRICT.contractVersion,
                implementation_version: STRICT.implementationVersion,
                schema_fingerprint: STRICT.schemaFingerprint,
                ui: {
                    kind: 'custom' as const,
                    component_key: STRICT.componentKey,
                    ui_contract_version: STRICT.uiContractVersion,
                },
                operations: [{operation: STRICT.operation}],
            },
        ],
        unavailable: [],
        policy: {client_timeout_ms: 5_000},
    };
}

/**
 * Queues one successful `/api/v1/tools/compute` response that echoes back
 * whatever identity fields were actually posted (the real `request_id` is
 * generated at random inside `runTool`, so it cannot be known up front).
 */
function mockSuccessfulCompute(resultPayload: unknown): void {
    axiosPost.mockImplementationOnce(async (_url: string, data: {request_id: string; items: Array<Record<string, unknown>>}) => {
        const item = data.items[0];
        return {
            data: {
                request_id: data.request_id,
                results: [
                    {
                        correlation_id: item.correlation_id,
                        tool_code: item.tool_code,
                        contract_version: item.contract_version,
                        implementation_version: item.implementation_version,
                        schema_fingerprint: item.schema_fingerprint,
                        execution_id: 'exec-1',
                        status: 'success',
                        result: resultPayload,
                    },
                ],
                success_count: 1,
                failed_count: 0,
            },
        };
    });
}

describe('tools client — generated codec regressions', () => {
    it('adapts a recursive integer schema through the real .safe() chain without breaking recursive type projection', async () => {
        const {adaptGeneratedToolSchemas} = await import('../../../../scripts/tools-codec-ast.mjs');

        const source = [
            'import { z } from "zod";',
            'export const RecursiveIntNode = z.lazy(() => z.object({',
            'count: z.number(),',
            'next: RecursiveIntNode.optional(),',
            '}));',
            'export const ToolCatalogResponse = z.object({items: z.array(z.string())});',
            'export const ToolComputeRequest = z.object({items: z.array(RecursiveIntNode)});',
            'export const ToolComputeResponse = z.object({results: z.array(RecursiveIntNode)});',
            'export const ToolDiagnosticsResponse = z.object({loaded: z.array(z.string())});',
        ].join('\n');
        const prepared = {
            schemas: {
                RecursiveIntNode: {
                    type: 'object',
                    properties: {
                        count: {type: 'integer'},
                        next: {$ref: '#/components/schemas/RecursiveIntNode'},
                    },
                    required: ['count'],
                    additionalProperties: false,
                },
                ToolCatalogResponse: {
                    type: 'object',
                    properties: {items: {type: 'array', items: {type: 'string'}}},
                    required: ['items'],
                    additionalProperties: false,
                },
                ToolComputeRequest: {
                    type: 'object',
                    properties: {items: {type: 'array', items: {$ref: '#/components/schemas/RecursiveIntNode'}}},
                    required: ['items'],
                    additionalProperties: false,
                },
                ToolComputeResponse: {
                    type: 'object',
                    properties: {results: {type: 'array', items: {$ref: '#/components/schemas/RecursiveIntNode'}}},
                    required: ['results'],
                    additionalProperties: false,
                },
                ToolDiagnosticsResponse: {
                    type: 'object',
                    properties: {loaded: {type: 'array', items: {type: 'string'}}},
                    required: ['loaded'],
                    additionalProperties: false,
                },
            },
            manifest: {
                transport: {
                    catalog: {schema: '#/components/schemas/ToolCatalogResponse'},
                    computeRequest: {schema: '#/components/schemas/ToolComputeRequest'},
                    computeResponse: {schema: '#/components/schemas/ToolComputeResponse'},
                    diagnostics: {schema: '#/components/schemas/ToolDiagnosticsResponse'},
                },
            },
            discriminatorOptions: new Map(),
        };
        const recordRuntime = [
            'function toolRecordCodec<Value extends z.ZodType<unknown, z.ZodTypeDef, unknown>>(',
            'record: z.ZodRecord<z.ZodString, Value>,',
            '): z.ZodType<z.output<typeof record>, z.ZodTypeDef, z.input<typeof record>> {',
            'return record as z.ZodType<z.output<typeof record>, z.ZodTypeDef, z.input<typeof record>>;',
            '}',
        ].join('\n');

        expect(source).not.toContain('.safe()');
        const adapted = adaptGeneratedToolSchemas(source, prepared, 'recursive-safe-regression', recordRuntime);

        expect(adapted).toContain('z.number().finite().int().safe()');
        expect(adapted).toContain('export type RecursiveIntNode = { "count": number; "next"?: (RecursiveIntNode | undefined) };');
        expect(adapted).toContain('export type RecursiveIntNodeInput = { "count": number; "next"?: (RecursiveIntNodeInput | undefined) };');
        expect(adapted).toContain('export const RecursiveIntNode: z.ZodType<RecursiveIntNode, z.ZodTypeDef, RecursiveIntNodeInput> =');
    });
});

describe('tools client — compute request wire contract', () => {
    // Populated once in beforeAll: a real, branded CompatibleToolDescriptor.
    // Its branding symbol is private to contracts.ts, so it must come from the
    // real fetchToolCatalog()/verifyToolDescriptor() path.
    const previousSession = getClientSessionUserId();
    let demoDescriptor: unknown;
    let strictDescriptor: unknown;

    beforeAll(async () => {
        transitionClientSession('demo-user');
        axiosGet.mockResolvedValueOnce({data: rawCatalog()});
        const catalog = await fetchToolCatalog();
        demoDescriptor = verifyDescriptorForTest(catalog, DEMO.toolCode, DEMO.contractVersion);
        strictDescriptor = verifyDescriptorForTest(catalog, STRICT.toolCode, STRICT.contractVersion);
    });

    afterEach(() => {
        axiosPost.mockReset();
    });

    afterAll(() => {
        transitionClientSession(previousSession);
    });

    /**
     * Runs `runTool` with the shared descriptor and asserts it rejects with a
     * `validation`/`invalid_request` `ToolClientError` *before* axios.post is
     * ever invoked — the defining behaviour of every case below.
     */
    function runDemo(parameters: unknown, correlationId: string): Promise<DemoResult> {
        return runToolForTest(DEMO.toolCode, DEMO.contractVersion, {descriptor: demoDescriptor, correlationId, parameters});
    }

    function runStrict(parameters: unknown, correlationId: string): Promise<DemoResult> {
        return runToolForTest(STRICT.toolCode, STRICT.contractVersion, {descriptor: strictDescriptor, correlationId, parameters});
    }

    async function expectRejectedBeforeAxios(parameters: unknown, correlationId: string): Promise<void> {
        let error: unknown;
        try {
            await runDemo(parameters, correlationId);
        } catch (caught) {
            error = caught;
        }

        expect(error).toBeInstanceOf(ToolClientError);
        expect(error).toMatchObject({kind: 'validation', code: 'invalid_request'});
        expect(axiosPost).not.toHaveBeenCalled();
    }

    it('baseline: resolves with the decoded result when parameters are ordinary — establishes the harness works before the negative-path tests', async () => {
        mockSuccessfulCompute({echoed: true});

        const result = await runDemo({label: 'ok'}, 'corr-baseline');

        expect(axiosPost).toHaveBeenCalledTimes(1);
        expect(result.status).toBe('success');
        expect(result.correlation_id).toBe('corr-baseline');
        if (result.status === 'success') {
            expect(result.result).toEqual({echoed: true});
        }
    });

    // -------------------------------------------------------------------
    // Rejected before axios: getter, toJSON, Proxy/non-plain object, cycle,
    // lone surrogate, unsafe integer, symbol.
    // -------------------------------------------------------------------

    it('rejects a getter-valued parameter before axios is ever called', async () => {
        const parameters: Record<string, unknown> = {visible: 1};
        const getter = vi.fn(() => 'leaked');
        Object.defineProperty(parameters, 'secret', {get: getter, enumerable: true, configurable: true});

        await expectRejectedBeforeAxios(parameters, 'corr-getter');
        expect(getter).not.toHaveBeenCalled();
    });

    it('rejects a parameter object exposing its own toJSON before axios is ever called', async () => {
        // A plain object with an own `toJSON` would silently substitute this
        // payload if the request were ever handed to the native JSON.stringify
        // path instead of clonePlainJson's manual walk.
        const toJSON = vi.fn(() => ({tampered: true}));
        const parameters = {toJSON};

        await expectRejectedBeforeAxios(parameters, 'corr-tojson');
        expect(toJSON).not.toHaveBeenCalled();
    });

    it('rejects a Proxy that spoofs a plain-object prototype before axios is ever called', async () => {
        // The target is plain; the reflective trap makes the observed object
        // non-plain and must fail closed.
        const proxy = new Proxy({value: 1}, {getPrototypeOf: () => ({})});

        await expectRejectedBeforeAxios(proxy, 'corr-proxy');
    });

    it('rejects a non-plain object instance before axios is ever called', async () => {
        // A built-in class instance (prototype !== Object.prototype), no Proxy
        // involved — the plain "this isn't a JSON-object" rejection.
        await expectRejectedBeforeAxios(new Date(), 'corr-nonplain');
    });

    it('rejects a circular parameter structure before axios is ever called', async () => {
        const cyclic: Record<string, unknown> = {name: 'loop'};
        cyclic.self = cyclic;

        await expectRejectedBeforeAxios(cyclic, 'corr-cycle');
    });

    it.each([
        ['a lone high surrogate', '\uD800'],
        ['a lone low surrogate', '\uDC00'],
    ])('rejects %s before axios is ever called', async (_label, text) => {
        await expectRejectedBeforeAxios({text}, 'corr-surrogate');
    });

    it.each([
        ['an unsafe integer beyond Number.MAX_SAFE_INTEGER', Number.MAX_SAFE_INTEGER + 1],
        ['NaN', NaN],
        ['Infinity', Infinity],
    ])('rejects %s before axios is ever called', async (_label, value) => {
        await expectRejectedBeforeAxios({value}, 'corr-number');
    });

    it('rejects a parameter object carrying an own symbol-keyed property before axios is ever called', async () => {
        // Confirms the current contract really does check for symbol keys
        // (clonePlainJson: `Object.getOwnPropertySymbols(value).length`) before
        // exercising the rejection.
        const parameters: Record<PropertyKey, unknown> = {visible: 1};
        parameters[Symbol('hidden')] = 'nope';

        await expectRejectedBeforeAxios(parameters, 'corr-symbol');
    });

    it('validates the descriptor-snapshotted plain parameters, not the original Proxy, before axios is ever called', async () => {
        const strictInput = toolContractMapForTest[STRICT.toolCode]?.[STRICT.contractVersion]?.input;
        expect(strictInput).toBeDefined();
        if (!strictInput) throw new Error('Strict test contract missing from toolContractMap mock');

        const target = {
            mode: 'plain',
            nested: {value: 'kept-from-get-trap'},
        };
        const snapshottedParameters = {mode: 'plain', nested: 7};
        const parameters = new Proxy(target, {
            get: (current, key, receiver) => Reflect.get(current, key, receiver),
            getOwnPropertyDescriptor(current, key) {
                if (key === 'nested') {
                    return {
                        value: snapshottedParameters.nested,
                        enumerable: true,
                        configurable: true,
                        writable: true,
                    };
                }
                return Reflect.getOwnPropertyDescriptor(current, key);
            },
        });

        expect(strictInput.safeParse(parameters).success).toBe(true);
        expect(strictInput.safeParse(snapshottedParameters).success).toBe(false);

        const safeParseInput = vi.spyOn(strictInput, 'safeParse');
        try {
            let error: unknown;
            try {
                await runStrict(parameters, 'corr-snapshot-contract');
            } catch (caught) {
                error = caught;
            }

            expect(error).toBeInstanceOf(ToolClientError);
            expect(error).toMatchObject({kind: 'validation', code: 'invalid_parameters'});
            expect(safeParseInput).toHaveBeenCalledTimes(1);
            expect(safeParseInput.mock.calls[0]?.[0]).toEqual(snapshottedParameters);
            expect(safeParseInput.mock.calls[0]?.[0]).not.toBe(parameters);
            expect(axiosPost).not.toHaveBeenCalled();
        } finally {
            safeParseInput.mockRestore();
        }
    });

    // -------------------------------------------------------------------
    // Wire-body semantics: one exact JSON body reused for transport and
    // validation; omission/null/raw-text preserved; defaults never sent.
    // -------------------------------------------------------------------

    it('sends exactly one JSON body reused for both axios transport and its own validation, preserving null and raw-text parameter values exactly', async () => {
        const parseRequest = vi.spyOn(toolTransportSchemas.computeRequest, 'safeParse');
        try {
            mockSuccessfulCompute({ok: true});
            const parameters = {
                nullableField: null,
                rawText: 'quote:" backslash:\\ newline:\n unicode:\u03c0 emoji:\ud83d\ude80',
                // 'omittedField' is intentionally never set at all.
            };

            const result = await runDemo(parameters, 'corr-body');

            expect(axiosPost).toHaveBeenCalledTimes(1);
            expect(parseRequest).toHaveBeenCalledTimes(1);
            expect(result.status).toBe('success');
            const [url, data, config] = axiosPost.mock.calls[0];
            expect(url).toBe('/api/v1/tools/compute');
            expect(data).toBe(parseRequest.mock.calls[0][0]);
            expect(typeof config.transformRequest[0]).toBe('function');

            // The literal string real axios would put on the wire — client.ts's
            // transformRequest ignores its own (data, headers) arguments and
            // returns the pre-parse snapshot unconditionally.
            const wireBody: string = config.transformRequest[0]();
            expect(typeof wireBody).toBe('string');
            const parsedWire = JSON.parse(wireBody);

            // Transport and validation share one snapshot, while the transform
            // reuses the bytes encoded before any asynchronous interceptor.
            expect(wireBody).toBe(JSON.stringify(data));
            expect(parsedWire).toEqual(data);

            const sentParameters = parsedWire.items[0].parameters;
            expect(sentParameters).toEqual(parameters);
            expect(sentParameters.nullableField).toBeNull();
            expect(sentParameters.rawText).toBe(parameters.rawText);
            expect(Object.hasOwn(sentParameters, 'omittedField')).toBe(false);
        } finally {
            parseRequest.mockRestore();
        }
    });

    it('never lets a schema-expanded default leak onto the wire, even for a field the mocked schema would fill in', async () => {
        // First prove the schema really does expand a default for the omitted
        // `protocol_hint` field — otherwise this test would pass for the wrong
        // reason (there being no default to leak in the first place).
        const directlyParsed = toolTransportSchemas.computeRequest.parse({
            request_id: 'probe-request',
            items: [
                {
                    correlation_id: 'probe-item',
                    tool_code: DEMO.toolCode,
                    contract_version: DEMO.contractVersion,
                    implementation_version: DEMO.implementationVersion,
                    schema_fingerprint: DEMO.schemaFingerprint,
                    parameters: {},
                },
            ],
        });
        expect(Reflect.get(directlyParsed, 'protocol_hint')).toBe('v1');

        mockSuccessfulCompute({ok: true});
        await runDemo({}, 'corr-default');

        const [, data, config] = axiosPost.mock.calls[0];
        const wireBody: string = config.transformRequest[0]();
        const parsedWire = JSON.parse(wireBody);
        expect(Object.hasOwn(data, 'protocol_hint')).toBe(false);
        expect(Object.hasOwn(parsedWire, 'protocol_hint')).toBe(false);
    });
});
