/**
 * What the FX detail page reads from the bulk conversion (`POST /fx/currencies/convert`).
 *
 * X-R16: the answer is parsed with **signal isolation**, as the asset detail page reads its price query
 * (`components/assets/detail/assetDetailPriceQuery.ts`). The generated client validates the whole answer, signal results
 * included, so a single invalid signal result threw the rates of the answer away too: the chart lost them, and «All»
 * never resolved its start.
 *
 * @module components/fx/fxDetailConvertQuery
 */

import type {z} from 'zod';
import {schemas} from '$lib/api';
import {backendSignalSchemas} from '$lib/charts/signals/backendTypes';

type FxConvertResponse = z.infer<typeof schemas.FXConvertResponse>;
type FxSignalGroup = NonNullable<FxConvertResponse['signal_results']>[number];

/** The answer of the bulk conversion: each signal group carries its raw `signals`, valid or not. */
export type FxConvertAnswer = Omit<FxConvertResponse, 'signal_results'> & {
    signal_results: Array<Omit<FxSignalGroup, 'signals'> & {signals: unknown[]}>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * The answer of the bulk conversion, with signal isolation.
 *
 * - It is validated as `FXConvertResponse` with, in each signal group, only its valid signal results.
 * - Each group is returned with its **raw** `signals`, so the caller can still report the invalid ones.
 * - A missing `signal_results` is an empty list, and a group without `signals` has none.
 * - It throws when the answer, its rates, its `signal_results`, a group or a group's signal collection is malformed: a
 *   broken rate is a real error, never isolated.
 */
export function parseFxConvertWithSignalIsolation(data: unknown): FxConvertAnswer {
    if (!isRecord(data)) {
        throw new Error('Invalid FX convert response');
    }
    const groups = data.signal_results === undefined ? [] : data.signal_results;
    if (!Array.isArray(groups)) {
        throw new Error('Invalid FX signal results');
    }
    const rawSignals = groups.map((group, index): unknown[] => {
        if (!isRecord(group)) {
            throw new Error(`Invalid FX signal group at index ${index}`);
        }
        const signals = group.signals === undefined ? [] : group.signals;
        if (!Array.isArray(signals)) {
            throw new Error(`Invalid FX signal collection at group index ${index}`);
        }
        return signals;
    });

    const parsed = schemas.FXConvertResponse.safeParse({
        ...data,
        signal_results: groups.map((group, index) => ({
            ...(group as Record<string, unknown>),
            signals: rawSignals[index].flatMap((signal) => {
                const result = backendSignalSchemas.result.safeParse(signal);
                return result.success ? [result.data] : [];
            }),
        })),
    });
    if (!parsed.success) {
        throw new Error('Invalid FX convert response');
    }
    return {
        ...parsed.data,
        signal_results: (parsed.data.signal_results ?? []).map((group, index) => ({...group, signals: rawSignals[index]})),
    };
}
