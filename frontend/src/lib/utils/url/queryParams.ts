export function getOptionalQueryParam(searchParams: URLSearchParams, key: string): string | undefined {
    const value = searchParams.get(key);
    if (value == null || value === '') return undefined;
    return value;
}

export function getOptionalNumberParam(searchParams: URLSearchParams, key: string): number | undefined {
    const value = getOptionalQueryParam(searchParams, key);
    if (value == null) return undefined;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
}

export function getCsvStringParam(searchParams: URLSearchParams, key: string): string[] | undefined {
    const value = getOptionalQueryParam(searchParams, key);
    if (!value) return undefined;
    const items = value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);
    return items.length > 0 ? items : undefined;
}

export function getCsvNumberParam(searchParams: URLSearchParams, key: string): number[] | undefined {
    const items = getCsvStringParam(searchParams, key);
    if (!items) return undefined;
    const numbers = items.map(Number).filter(Number.isFinite);
    return numbers.length > 0 ? numbers : undefined;
}

export function setOptionalQueryParam(params: URLSearchParams, key: string, value: string | undefined | null, opts: {omitIf?: string} = {}): void {
    if (value == null || value === '' || value === opts.omitIf) return;
    params.set(key, value);
}

export function setOptionalNumberParam(params: URLSearchParams, key: string, value: number | undefined | null, opts: {omitIf?: number} = {}): void {
    if (value == null || value === opts.omitIf) return;
    params.set(key, String(value));
}

export function setCsvParam(params: URLSearchParams, key: string, values: readonly (string | number)[] | undefined | null): void {
    if (!values || values.length === 0) return;
    params.set(
        key,
        values
            .map((value) => String(value).trim())
            .filter(Boolean)
            .join(','),
    );
}
