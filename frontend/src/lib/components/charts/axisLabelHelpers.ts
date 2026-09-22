import type {ConfigurableAxisDescriptor} from './chartCoreHelpers';

export type AxisLabelTranslator = (key: string, values?: Record<string, string>) => string;

function translateOrFallback(translate: AxisLabelTranslator, key: string, values: Record<string, string>, fallback: string): string {
    const translated = translate(key, values);
    return translated === key ? fallback : translated;
}

export function priceAxisLabel(translate: AxisLabelTranslator, currency: string): string {
    return translateOrFallback(translate, 'chartSettings.axes.price', {currency}, `Price axis (${currency})`);
}

export function percentageAxisLabel(translate: AxisLabelTranslator): string {
    return translateOrFallback(translate, 'chartSettings.axes.percentage', {}, 'Percentage axis');
}

export function exchangeRateAxisLabel(translate: AxisLabelTranslator, pair: string): string {
    return translateOrFallback(translate, 'chartSettings.axes.exchangeRate', {pair}, `Exchange-rate axis (${pair})`);
}

export function secondaryAxisLabel(translate: AxisLabelTranslator, axis: ConfigurableAxisDescriptor): string {
    if (axis.unit === 'volume' || axis.key.startsWith('volume:')) {
        return translateOrFallback(translate, 'chartSettings.axes.volume', {}, 'Volume axis');
    }
    return translateOrFallback(translate, 'chartSettings.axes.signal', {name: axis.label}, `${axis.label} axis`);
}
