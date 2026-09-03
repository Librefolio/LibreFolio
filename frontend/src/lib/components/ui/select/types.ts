/**
 * Common types for Select components family
 */

/**
 * Base option interface for all Select components
 */
export interface SelectOption {
    /** Unique value/key for the option */
    value: string;
    /** Display text for the option */
    label: string;
    /**
     * Render as a non-selectable section title rather than an option.
     *
     * A header answers "why is this here" without the user having to choose it, which is what a
     * list mixing things and places to look cannot do. It is skipped by the keyboard, ignored by
     * Enter, and — crucially — dropped from the results when the search empties its section: a
     * title standing over nothing is worse than no title at all.
     *
     * Still needs a unique `value`, since the list is keyed by it (e.g. `__section:archive`).
     */
    header?: boolean;
    /** Optional text for search matching (combined with label and value) */
    searchText?: string;
    /** Disable this option */
    disabled?: boolean;
    /** Optional icon (emoji, symbol, or icon name) */
    icon?: string;
    /** Custom data payload for rendering via snippet */
    data?: unknown;
    /** Optional badge text to show alongside the label in the dropdown */
    badge?: string;
    /** Tailwind classes for the badge */
    badgeClass?: string;
    /** Tooltip text shown on hover over the badge */
    badgeTooltip?: string;
}
