export function truncateName(name: string, max = 30): string {
    if (name.length <= max) return name;
    if (max <= 0) return '';
    if (max === 1) return '…';
    return `${name.slice(0, max - 1).trimEnd()}…`;
}

/**
 * humanizeKey — turn a machine key into a human-readable label.
 *
 * `foo_bar-baz` → `Foo Bar Baz`: underscores and hyphens become spaces and each
 * word is capitalised. Used as the last-resort label for signal outputs when no
 * i18n string is registered, so a raw output key never reaches the user as-is.
 */
export function humanizeKey(value: string): string {
    return value
        .replaceAll('_', ' ')
        .replaceAll('-', ' ')
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
