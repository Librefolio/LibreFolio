/** The types of `LinkedStackedBar`: one segment of the bar, and the test ids of the parts a caller names. */

export interface LinkedSegment {
    /** Unique among the segments; the link between a bar segment and its legend row. */
    id: string;
    /** The width of the segment, in percent of the bar. */
    percent: number;
    /** A class that fills the segment and its legend dot: a role of the design system, or `bg-transparent`. */
    fill: string;
    /** Any further attribute of the segment in the bar (a `data-*` the caller's tests read). */
    attrs?: Record<string, string | number>;
}

export interface LinkedStackedBarTestIds {
    bar: string;
    segment: (id: string) => string;
    legend?: string;
    item: (id: string) => string;
}

/** A tick on the bar at `percent` (0–100), named by `label`: the part after it is drawn as past it (C9-4). */
export interface LinkedBarMarker {
    percent: number;
    label: string;
}
