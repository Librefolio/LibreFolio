/**
 * chartShades — the colour arithmetic of the category charts (DV, the designer's round 2, approved by the developer as
 * D-T17): the OKLab mix, the shades of a family (GR4) and the rounds past the end of a sequence (GR5), and the colour a
 * continuous scale draws between two of its stops (GR5.3). The contrast that picks a readable text moved to
 * `./contrast` with its tests (`contrast.test.ts`).
 *
 * - **Golden values.** The shades of the ETF family in both themes and four points of the correlation scale come from
 *   an independent Python implementation (the DV analysis): OKLab as Björn Ottosson defines it, the sRGB transfer
 *   function, channels rounded to bytes. The TypeScript must match them to the byte.
 * - **The poles of GR4**, as the developer chose them: toward white at 15, 30, 45 % in the light theme, toward the card
 *   at 18, 32, 45 % in the dark one, then the same steps toward the opposite pole, and round again.
 * - **The edges**: the endpoints of a mix, a colour that cannot be parsed (the input comes back, never a black), a
 *   value outside a scale, a stop that cannot be parsed.
 *
 * Node env: pure functions, no DOM.
 *
 * @module lib/theme/chartShades.test
 */
import {describe, expect, it} from 'vitest';

import {familyShade, mixOklab, scaleColor, shadePoles, type ShadePoles} from './chartShades';

/** The ETF colour of the designer's type table (round 2), light and dark: the base of the golden shades. */
const ETF_LIGHT = '#1D5BD8';
const ETF_DARK = '#60A5FA';
/** The dark theme's card (`--lf-surface-card`, the designer's round 2): the near pole of the dark shades. */
const DARK_CARD = '#151B19';

/** The channels of a `#rrggbb`. */
function channels(hex: string): [number, number, number] {
    const match = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex);
    if (!match) throw new Error(`${hex} is not #rrggbb`);
    return [parseInt(match[1], 16), parseInt(match[2], 16), parseInt(match[3], 16)];
}

/** The largest difference, channel by channel, between two `#rrggbb` colours. */
function channelGap(first: string, second: string): number {
    const [a, b] = [channels(first), channels(second)];
    return Math.max(...a.map((value, index) => Math.abs(value - b[index])));
}

const LOWER_HEX = /^#[0-9a-f]{6}$/;

describe('shadePoles — where the shades of a family go (GR4, D-T17)', () => {
    it('light theme: toward white at 15, 30, 45 %, then toward the primary text; the card plays no part', () => {
        const expected: ShadePoles = {near: '#FFFFFF', far: '#1C2420', steps: [0.15, 0.3, 0.45]};
        expect(shadePoles(false, DARK_CARD)).toEqual(expected);
        expect(shadePoles(false, '#123456'), 'another card gives the same light poles').toEqual(expected);
    });

    it('dark theme: toward the card at 18, 32, 45 %, so a shade never washes out, then toward white', () => {
        expect(shadePoles(true, DARK_CARD)).toEqual({near: DARK_CARD, far: '#FFFFFF', steps: [0.18, 0.32, 0.45]});
        expect(shadePoles(true, '#123456').near, 'the near pole is the card it is given').toBe('#123456');
    });
});

describe('familyShade — the golden shades of the ETF family, from an independent implementation', () => {
    const LIGHT_GOLDEN = ['#4076e0', '#6190e8', '#82a8ee', '#1d54ba', '#1e4c9d', '#1e4480'];
    const DARK_GOLDEN = ['#528acd', '#4775ab', '#3d638c', '#7eb6fc', '#94c3fe', '#a9cfff'];
    const RANKS = [1, 2, 3, 4, 5, 6];

    it(`light theme, base ${ETF_LIGHT}: ranks 1–6 to the byte, whatever the card`, () => {
        expect(RANKS.map((rank) => familyShade(ETF_LIGHT, rank, shadePoles(false, DARK_CARD)))).toEqual(LIGHT_GOLDEN);
        expect(
            RANKS.map((rank) => familyShade(ETF_LIGHT, rank, shadePoles(false, '#000000'))),
            'the light shades read no card',
        ).toEqual(LIGHT_GOLDEN);
    });

    it(`dark theme, base ${ETF_DARK} on the card ${DARK_CARD}: ranks 1–6 to the byte`, () => {
        expect(RANKS.map((rank) => familyShade(ETF_DARK, rank, shadePoles(true, DARK_CARD)))).toEqual(DARK_GOLDEN);
    });

    it('gives seven distinct members, base included, in both themes', () => {
        const light = [ETF_LIGHT.toLowerCase(), ...LIGHT_GOLDEN];
        const dark = [ETF_DARK.toLowerCase(), ...DARK_GOLDEN];
        expect(new Set(light).size, 'light').toBe(7);
        expect(new Set(dark).size, 'dark').toBe(7);
    });
});

describe('familyShade — the ranks', () => {
    const poles = shadePoles(false, DARK_CARD);

    it('hands back the base itself, exactly as written, at rank 0 and below', () => {
        for (const rank of [0, -1, -7]) expect(familyShade(ETF_LIGHT, rank, poles), `rank ${rank}`).toBe(ETF_LIGHT);
        expect(familyShade('not a colour', 0, poles), 'even a base it could not mix').toBe('not a colour');
    });

    it('takes ranks 1–3 toward the near pole and 4–6 toward the far one, step by step', () => {
        const expected = [
            mixOklab(ETF_LIGHT, poles.near, poles.steps[0]),
            mixOklab(ETF_LIGHT, poles.near, poles.steps[1]),
            mixOklab(ETF_LIGHT, poles.near, poles.steps[2]),
            mixOklab(ETF_LIGHT, poles.far, poles.steps[0]),
            mixOklab(ETF_LIGHT, poles.far, poles.steps[1]),
            mixOklab(ETF_LIGHT, poles.far, poles.steps[2]),
        ];
        expect([1, 2, 3, 4, 5, 6].map((rank) => familyShade(ETF_LIGHT, rank, poles))).toEqual(expected);
    });

    it('starts the cycle again past the sixth: rank 7 is rank 1, 12 is 6, 13 is 1 again', () => {
        const firstRound = [1, 2, 3, 4, 5, 6].map((rank) => familyShade(ETF_LIGHT, rank, poles));
        expect(new Set(firstRound).size, 'barrier: the six shades differ, or a repeat would prove nothing').toBe(6);

        expect([7, 8, 9, 10, 11, 12].map((rank) => familyShade(ETF_LIGHT, rank, poles))).toEqual(firstRound);
        expect(familyShade(ETF_LIGHT, 13, poles)).toBe(firstRound[0]);
    });

    it('cycles over twice the steps, whatever their number', () => {
        const oneStep: ShadePoles = {near: '#ffffff', far: '#000000', steps: [0.5]};
        const [near, far] = [mixOklab(ETF_LIGHT, '#ffffff', 0.5), mixOklab(ETF_LIGHT, '#000000', 0.5)];
        expect(near, 'barrier: the two poles give two shades').not.toBe(far);

        expect([1, 2, 3, 4].map((rank) => familyShade(ETF_LIGHT, rank, oneStep))).toEqual([near, far, near, far]);
    });
});

describe('mixOklab — a mix in OKLab, as #rrggbb', () => {
    const COLOURS = ['#1D5BD8', '#60A5FA', '#C25E00', '#94A09B', '#151B19', '#ffffff', '#000000', '#2D6A54'];

    it.each(COLOURS)('amount 0 gives back %s, amount 1 the other end, within one unit per channel', (colour) => {
        const other = colour.toLowerCase() === '#ffffff' ? '#1c2420' : '#ffffff';
        expect(channelGap(mixOklab(colour, other, 0), colour), 'amount 0').toBeLessThanOrEqual(1);
        expect(channelGap(mixOklab(colour, other, 1), other), 'amount 1').toBeLessThanOrEqual(1);
    });

    it('writes lower-case #rrggbb, whatever the case or notation it reads', () => {
        for (const [from, to] of [
            ['#1D5BD8', '#FFFFFF'],
            ['#FFF', '#000'],
            ['rgb(29, 91, 216)', 'hsl(0, 0%, 100%)'],
        ]) {
            expect(mixOklab(from, to, 0.3), `${from} → ${to}`).toMatch(LOWER_HEX);
        }
        expect(mixOklab('rgb(29, 91, 216)', '#ffffff', 0.15), 'rgb() is the same colour as its hex').toBe(mixOklab('#1D5BD8', '#ffffff', 0.15));
    });

    it('clips the channels a mix past its ends would push out of sRGB', () => {
        expect(mixOklab('#000000', '#ffffff', 2)).toBe('#ffffff');
        expect(mixOklab('#ffffff', '#000000', 2)).toBe('#000000');
        expect(mixOklab(ETF_LIGHT, '#ffffff', 1.5)).toMatch(LOWER_HEX);
    });

    it('hands back `from` unchanged, as written, when either colour cannot be parsed — never a black', () => {
        expect(mixOklab('not a colour', '#ffffff', 0.5)).toBe('not a colour');
        expect(mixOklab(ETF_LIGHT, 'oklch(0.6 0.1 200)', 0.5)).toBe(ETF_LIGHT);
        expect(mixOklab('var(--lf-surface-card)', '#000000', 1)).toBe('var(--lf-surface-card)');
        expect(mixOklab(ETF_LIGHT, '', 0.5)).toBe(ETF_LIGHT);
    });
});

describe('scaleColor — a continuous scale, as ECharts visualMap draws it', () => {
    /** The correlation scale of GR5.3 in the light theme: danger, panel, info. */
    const CORRELATION = ['#C82838', '#E8ECE9', '#155EEF'];

    it('draws the golden points of the independent implementation: the three stops and halfway to the third', () => {
        expect(scaleColor(CORRELATION, -1, -1, 1)).toBe('#c82838');
        expect(scaleColor(CORRELATION, 0, -1, 1)).toBe('#e8ece9');
        expect(scaleColor(CORRELATION, 1, -1, 1)).toBe('#155eef');
        expect(scaleColor(CORRELATION, 0.5, -1, 1)).toBe('#7fa5ec');
    });

    it('interpolates each channel in sRGB between the two nearest stops: halfway to the first, rounded', () => {
        // (200+232)/2 = 216, (40+236)/2 = 138, (56+233)/2 = 144.5 → 145: #d88a91.
        expect(scaleColor(CORRELATION, -0.5, -1, 1)).toBe('#d88a91');
    });

    it('spaces its stops evenly over the range, whatever the range', () => {
        expect(scaleColor(CORRELATION, 5, 0, 10)).toBe('#e8ece9');
        expect(scaleColor(['#000000', '#ffffff'], 25, 0, 100)).toBe('#404040');
    });

    it('clamps a value outside the range to the stop at its end', () => {
        expect(scaleColor(CORRELATION, -5, -1, 1)).toBe('#c82838');
        expect(scaleColor(CORRELATION, 5, -1, 1)).toBe('#155eef');
        expect(scaleColor(CORRELATION, Number.POSITIVE_INFINITY, -1, 1)).toBe('#155eef');
    });

    it('hands back the nearest stop, as written, when a stop cannot be parsed', () => {
        const stops = ['#000000', 'var(--lf-info)'];
        expect(scaleColor(stops, 0.9, 0, 1)).toBe('var(--lf-info)');
        expect(scaleColor(stops, 0.2, 0, 1)).toBe('#000000');
    });
});
