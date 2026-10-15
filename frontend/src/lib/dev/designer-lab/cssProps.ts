/**
 * Designer Lab — the colour properties the element picker reads, and how CSS can declare them.
 *
 * Shared by the picker (app tab), which finds the declarations, and the Lab, which matches them with the catalogue.
 */

/** Properties with one colour. */
export const SINGLE_COLOR_PROPERTIES = ['color', 'background-color', 'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color', 'outline-color', 'text-decoration-color', 'fill', 'stroke'] as const;

/** Properties that can hold several colours: listed with their declaration, never resolved to one source. */
export const MULTI_COLOR_PROPERTIES = ['box-shadow', 'background-image'] as const;

/** Inherited: an element without its own declaration takes the colour of an ancestor. */
export const INHERITED_COLOR_PROPERTIES: ReadonlySet<string> = new Set(['color', 'fill', 'stroke']);

export const BORDER_SIDES = ['top', 'right', 'bottom', 'left'] as const;

const LOGICAL_SIDE: Record<(typeof BORDER_SIDES)[number], [string, string]> = {
    top: ['block', 'start'],
    bottom: ['block', 'end'],
    left: ['inline', 'start'],
    right: ['inline', 'end'],
};

function borderShorthands(side: (typeof BORDER_SIDES)[number]): string[] {
    const [axis, edge] = LOGICAL_SIDE[side];
    return ['border-color', `border-${side}`, 'border', `border-${axis}-${edge}-color`, `border-${axis}-${edge}`, `border-${axis}-color`, `border-${axis}`];
}

/** The shorthands that can set each property (horizontal, left-to-right writing, as in the app). */
export const SHORTHANDS: Readonly<Record<string, readonly string[]>> = {
    'background-color': ['background'],
    'background-image': ['background'],
    'outline-color': ['outline'],
    'text-decoration-color': ['text-decoration'],
    'border-top-color': borderShorthands('top'),
    'border-right-color': borderShorthands('right'),
    'border-bottom-color': borderShorthands('bottom'),
    'border-left-color': borderShorthands('left'),
};

/** What an `element` change may set: the one-colour properties, `border-color` for the four sides, `chart` for a chart colour. */
export const ELEMENT_PROPERTIES: readonly string[] = [...SINGLE_COLOR_PROPERTIES, 'border-color', 'chart'];

/**
 * Whether a declaration of `declared` sets `property`: the property itself or one of its shorthands. `border-color`
 * stands for the four sides. An unknown declared property (null) is not excluded.
 */
export function declares(declared: string | null | undefined, property: string): boolean {
    if (!declared || declared === property) return true;
    if (property === 'border-color') return BORDER_SIDES.some((side) => declares(declared, `border-${side}-color`));
    return (SHORTHANDS[property] ?? []).includes(declared);
}
