/**
 * Locale-safe decimal input normalization for text inputs.
 *
 * Canonical app/backend decimal format uses "." as the decimal separator.
 * Browsers can reinterpret <input type="number"> values by locale, so decimal
 * entry fields use type="text" and normalize here instead.
 */
export function normalizeDecimalInput(value: string): string {
    const trimmed = value.trim();
    if (trimmed === '') return '';

    const commaCount = (trimmed.match(/,/g) ?? []).length;
    const normalized = commaCount === 1 && !trimmed.includes('.') ? trimmed.replace(',', '.') : trimmed;

    if (/^-?(?:\d+\.?\d*|\.\d+)$/.test(normalized)) return normalized;
    return trimmed;
}
