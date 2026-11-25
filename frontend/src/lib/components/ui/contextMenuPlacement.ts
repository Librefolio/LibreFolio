/**
 * Where a context menu opened by a finger goes (85 BTN-0, the developer's phone test of 24/11/2026).
 *
 * A menu opened at the point of a long press, drawn to its right and below, sits under the thumb. A finger's menu goes:
 * - horizontally: to the LEFT of the finger (its right edge a gap short of the point); centred on the finger when the
 *   room on the left is not enough; always inside the viewport;
 * - vertically: ABOVE the finger (its bottom edge a gap short of the point); below only when there is no room above.
 *
 * A mouse keeps the classic placement (to the right and below, flipped at the edges): that path is not here.
 * Pure on purpose: jsdom has no layout, so the geometry is tested here with numbers.
 */

/** Room between the finger's point and the menu, so the fingertip does not cover its edge. */
export const FINGER_GAP_PX = 12;
/** The menu never touches the viewport's edge. */
export const VIEWPORT_PAD_PX = 8;

export interface Size {
    width: number;
    height: number;
}

export interface FingerMenuPosition {
    left: number;
    top: number;
    horizontal: 'left' | 'centre';
    vertical: 'above' | 'below';
}

function clamp(value: number, min: number, max: number): number {
    // A menu wider (or taller) than the viewport starts at the near edge.
    if (max < min) return min;
    return Math.min(Math.max(value, min), max);
}

/** The top-left corner of a menu of size `menu`, opened by a finger at `point`, in a viewport of size `viewport`. */
export function fingerMenuPosition(point: {x: number; y: number}, menu: Size, viewport: Size): FingerMenuPosition {
    const maxLeft = viewport.width - VIEWPORT_PAD_PX - menu.width;
    const maxTop = viewport.height - VIEWPORT_PAD_PX - menu.height;

    const leftOfFinger = point.x - FINGER_GAP_PX - menu.width;
    const horizontal = leftOfFinger >= VIEWPORT_PAD_PX ? 'left' : 'centre';
    const left = horizontal === 'left' ? leftOfFinger : clamp(point.x - menu.width / 2, VIEWPORT_PAD_PX, maxLeft);

    const aboveFinger = point.y - FINGER_GAP_PX - menu.height;
    const vertical = aboveFinger >= VIEWPORT_PAD_PX ? 'above' : 'below';
    const top = vertical === 'above' ? aboveFinger : clamp(point.y + FINGER_GAP_PX, VIEWPORT_PAD_PX, maxTop);

    return {left, top, horizontal, vertical};
}
