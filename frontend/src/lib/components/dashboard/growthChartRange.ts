export interface GrowthLogicalRange {
    startDate: string;
    endDate: string;
}

export function clampGrowthLogicalRange(range: GrowthLogicalRange | null, dates: readonly string[]): GrowthLogicalRange | null {
    if (!range || dates.length === 0) return null;

    const firstDate = dates[0];
    const lastDate = dates[dates.length - 1];
    const startDate = range.startDate <= range.endDate ? range.startDate : range.endDate;
    const endDate = range.startDate <= range.endDate ? range.endDate : range.startDate;
    const clamp = (date: string) => (date < firstDate ? firstDate : date > lastDate ? lastDate : date);

    return {
        startDate: clamp(startDate),
        endDate: clamp(endDate),
    };
}
