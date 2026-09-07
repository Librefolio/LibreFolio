import type {SignalColorRole, SignalStyle, SignalVisualStyle} from './ChartSignal';

const ROLE_COLORS: Record<Exclude<SignalColorRole, 'primary'>, string> = {
    secondary: '#f59e0b',
    positive: '#16a34a',
    negative: '#dc2626',
    neutral: '#64748b',
    accent: '#8b5cf6',
};

export function resolveSignalColor(baseColor: string, role: SignalColorRole): string {
    return role === 'primary' ? baseColor : ROLE_COLORS[role];
}

export function defaultSignalVisualStyle(): SignalVisualStyle {
    return {
        colorRole: 'primary',
        lineWidthDelta: 0,
        opacity: 1,
        fillOpacity: 0.2,
    };
}

export function resolveVisualSignalStyle(baseStyle: SignalStyle, visualStyle: SignalVisualStyle, includeMarkers = false): SignalStyle {
    return {
        color: resolveSignalColor(baseStyle.color, visualStyle.colorRole),
        lineWidth: Math.max(1, Math.min(8, baseStyle.lineWidth + visualStyle.lineWidthDelta)),
        lineType: visualStyle.lineType ?? baseStyle.lineType,
        markerStart: includeMarkers ? baseStyle.markerStart : null,
        markerEnd: includeMarkers ? baseStyle.markerEnd : null,
    };
}
