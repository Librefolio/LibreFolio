/**
 * @vitest-environment node
 *
 * fingerMenuPosition — where a context menu opened by a finger goes (85 BTN-0, the developer's phone test).
 *
 * To the LEFT of the finger (its right edge `FINGER_GAP_PX` short of the point) when that leaves at least
 * `VIEWPORT_PAD_PX`; otherwise centred on the finger, clamped to the viewport. ABOVE the finger (its bottom edge a gap
 * short of the point) when it fits; otherwise below, clamped. Numbers only: the geometry is pure.
 */
import {describe, expect, it} from 'vitest';
import {FINGER_GAP_PX, fingerMenuPosition, VIEWPORT_PAD_PX} from './contextMenuPlacement';

const PHONE = {width: 430, height: 932};
const MENU = {width: 200, height: 150};

describe('fingerMenuPosition', () => {
    it('the constants are the ones the placement is specified with', () => {
        expect(FINGER_GAP_PX).toBe(12);
        expect(VIEWPORT_PAD_PX).toBe(8);
    });

    it('left of the finger and above it, with room on both sides', () => {
        // right edge 400 − 12 = 388 → left 188; bottom 600 − 12 = 588 → top 438
        expect(fingerMenuPosition({x: 400, y: 600}, MENU, PHONE)).toEqual({left: 188, top: 438, horizontal: 'left', vertical: 'above'});
    });

    it('the exact boundary: leftOfFinger equal to the pad counts as left', () => {
        // 220 − 12 − 200 = 8
        expect(fingerMenuPosition({x: 220, y: 600}, MENU, PHONE)).toMatchObject({left: 8, horizontal: 'left'});
        // One pixel less: centred on the finger, clamped at the pad (219 − 100 = 119)
        expect(fingerMenuPosition({x: 219, y: 600}, MENU, PHONE)).toMatchObject({left: 119, horizontal: 'centre'});
    });

    it('the exact boundary above: aboveFinger equal to the pad counts as above', () => {
        // 170 − 12 − 150 = 8
        expect(fingerMenuPosition({x: 400, y: 170}, MENU, PHONE)).toMatchObject({top: 8, vertical: 'above'});
        expect(fingerMenuPosition({x: 400, y: 169}, MENU, PHONE)).toMatchObject({top: 181, vertical: 'below'});
    });

    it('centred on the finger when the room on the left is not enough', () => {
        // 150 − 12 − 200 = −62 < 8 → centre: 150 − 100 = 50
        expect(fingerMenuPosition({x: 150, y: 600}, MENU, PHONE)).toEqual({left: 50, top: 438, horizontal: 'centre', vertical: 'above'});
    });

    it('below the finger when the room above is not enough', () => {
        // 100 − 12 − 150 = −62 < 8 → below: 100 + 12 = 112
        expect(fingerMenuPosition({x: 400, y: 100}, MENU, PHONE)).toEqual({left: 188, top: 112, horizontal: 'left', vertical: 'below'});
    });

    it('clamped on both axes: centred near the left edge, below near the bottom', () => {
        // Horizontal: 40 − 100 = −60 → clamped to the pad, 8. Vertical: a tall menu, no room above (100 − 12 − 900 < 8),
        // below at 112 would end past the bottom → clamped to 932 − 8 − 900 = 24.
        expect(fingerMenuPosition({x: 40, y: 100}, {width: 200, height: 900}, PHONE)).toEqual({left: 8, top: 24, horizontal: 'centre', vertical: 'below'});
        // Centred near the right edge with no room on the left: impossible with a gap to the left, so a wide menu: 300 px
        // at x = 300 → 300 − 12 − 300 < 8 → centre 150, clamped to 430 − 8 − 300 = 122.
        expect(fingerMenuPosition({x: 300, y: 600}, {width: 300, height: 150}, PHONE)).toMatchObject({left: 122, horizontal: 'centre'});
    });

    it('a menu wider (or taller) than the viewport sits at the pad', () => {
        expect(fingerMenuPosition({x: 200, y: 50}, {width: 500, height: 1000}, PHONE)).toEqual({left: 8, top: 8, horizontal: 'centre', vertical: 'below'});
    });
});
