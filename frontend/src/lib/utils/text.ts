export function truncateName(name: string, max = 30): string {
    if (name.length <= max) return name;
    if (max <= 0) return '';
    if (max === 1) return '…';
    return `${name.slice(0, max - 1).trimEnd()}…`;
}
