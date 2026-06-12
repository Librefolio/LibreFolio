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

/**
 * Props shared by dropdown-based select components
 */
export interface BaseDropdownProps {
    /** Disable the dropdown */
    disabled?: boolean;
    /** Position of dropdown relative to trigger */
    dropdownPosition?: 'top' | 'bottom' | 'auto';
}

/**
 * Props for SimpleSelect and SearchSelect
 */
export interface SelectProps extends BaseDropdownProps {
    /** Currently selected value */
    value: string;
    /** Available options */
    options: SelectOption[];
    /** Placeholder when no value selected */
    placeholder?: string;
    /** Show loading state */
    loading?: boolean;
}
