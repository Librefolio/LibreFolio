/**
 * Designer Lab — colour-vision deficiency simulation over the whole page.
 *
 * An SVG `feColorMatrix` filter on `<html>`: the root element is the one place where `filter` does not turn the
 * element into the containing block of its fixed descendants, so modals and sticky headers keep their place.
 * Matrices: Machado, Oliveira & Fernandes (2009), severity 1, applied in linear RGB; achromatopsia uses the Rec. 709
 * luminance weights.
 */

import type {CvdMode} from '../types';
import {OWN_ATTR} from './vars';

const FILTER_ID = 'lf-designer-lab-cvd';
const SVG_ID = 'lf-designer-lab-cvd-svg';
const STYLE_ID = 'lf-designer-lab-cvd-style';
const SVG_NS = 'http://www.w3.org/2000/svg';

export const CVD_MATRICES: Record<Exclude<CvdMode, 'none'>, number[]> = {
    protanopia: [0.152286, 1.052583, -0.204868, 0, 0, 0.114503, 0.786281, 0.099216, 0, 0, -0.003882, -0.048116, 1.051998, 0, 0, 0, 0, 0, 1, 0],
    deuteranopia: [0.367322, 0.860646, -0.227968, 0, 0, 0.280085, 0.672501, 0.047413, 0, 0, -0.01182, 0.04294, 0.968881, 0, 0, 0, 0, 0, 1, 0],
    tritanopia: [1.255528, -0.076749, -0.178779, 0, 0, -0.078411, 0.930809, 0.147602, 0, 0, 0.004733, 0.691367, 0.3039, 0, 0, 0, 0, 0, 1, 0],
    achromatopsia: [0.2126, 0.7152, 0.0722, 0, 0, 0.2126, 0.7152, 0.0722, 0, 0, 0.2126, 0.7152, 0.0722, 0, 0, 0, 0, 0, 1, 0],
};

export function applyCvd(mode: CvdMode): void {
    document.getElementById(SVG_ID)?.remove();
    document.getElementById(STYLE_ID)?.remove();
    if (mode === 'none') return;
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.id = SVG_ID;
    svg.setAttribute(OWN_ATTR, '');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('style', 'position:absolute;width:0;height:0;overflow:hidden');
    const filter = document.createElementNS(SVG_NS, 'filter');
    filter.id = FILTER_ID;
    filter.setAttribute('color-interpolation-filters', 'linearRGB');
    const matrix = document.createElementNS(SVG_NS, 'feColorMatrix');
    matrix.setAttribute('type', 'matrix');
    matrix.setAttribute('values', CVD_MATRICES[mode].join(' '));
    filter.appendChild(matrix);
    svg.appendChild(filter);
    document.body.appendChild(svg);
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.setAttribute(OWN_ATTR, '');
    style.textContent = `html { filter: url(#${FILTER_ID}) !important; }`;
    document.head.appendChild(style);
}
