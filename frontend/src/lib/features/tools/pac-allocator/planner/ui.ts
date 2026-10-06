/** Shared Tailwind class sets of the planner UI: one place, so the review changes one file. */

export const BUTTON_PRIMARY =
    'inline-flex items-center justify-center gap-2 rounded-lg bg-libre-green px-4 py-2 text-sm font-semibold text-white hover:bg-libre-green/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:cursor-not-allowed disabled:opacity-50 dark:bg-green-600 dark:hover:bg-green-500';

export const BUTTON_SECONDARY =
    'inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700';

export const BUTTON_DANGER =
    'inline-flex items-center justify-center gap-2 rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-red-800 dark:bg-gray-800 dark:text-red-300 dark:hover:bg-red-950/40';

/** Confirms a replacement the user must notice (amber, like the shared ConfirmModal warning). */
export const BUTTON_WARNING =
    'inline-flex items-center justify-center gap-2 rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500 disabled:cursor-not-allowed disabled:opacity-50';

export const BUTTON_LINK = 'inline-flex items-center gap-1 rounded text-sm font-medium text-libre-green hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green dark:text-green-400';

export const CARD = 'rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800';

/** R11.10: a small box inside a result section (a fact of the Proof, an objective value). */
export const TILE = 'rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-900/40';

/** The small title of a `TILE`. */
export const TILE_LABEL = 'text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400';

/** A card-sized button that starts an action: icon, title, one-line explanation. */
export const CHOICE_CARD =
    'flex h-full w-full flex-col items-start gap-1.5 rounded-xl border border-gray-200 bg-white p-3 text-left text-sm transition-colors hover:border-libre-green hover:bg-libre-green/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-gray-200 disabled:hover:bg-white dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-libre-green/10 dark:disabled:hover:border-gray-700 dark:disabled:hover:bg-gray-800';

/** Round tinted holder for a lucide icon, sized like a small `BrokerIcon`. */
export const ICON_BUBBLE = 'flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-libre-green/10 text-libre-green dark:bg-libre-green/20 dark:text-green-400';

/** R9.8: the step number of the operational plan, shared by the steps and the orders. */
export const STEP_NUMBER = 'inline-flex h-6 min-w-6 shrink-0 items-center justify-center rounded-full bg-gray-100 px-1.5 text-xs font-semibold tabular-nums text-gray-700 dark:bg-gray-700 dark:text-gray-200';

export const SECTION_TITLE = 'text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300';

export const INPUT = 'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-libre-green focus:outline-none focus:ring-1 focus:ring-libre-green disabled:opacity-60 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100';

/** A card title the user renames in place: reads as a heading, shows its border on hover and focus. */
export const TITLE_INPUT =
    'w-full min-w-0 truncate rounded-md border border-transparent bg-transparent px-1.5 py-0.5 font-semibold text-gray-900 placeholder:font-normal placeholder:text-gray-400 hover:border-gray-300 focus:border-libre-green focus:outline-none focus:ring-1 focus:ring-libre-green dark:text-gray-100 dark:hover:border-gray-600';

export const LABEL = 'block text-xs font-medium text-gray-600 dark:text-gray-300';

/** A label with a «?» beside it: one fixed height, so the fields of a row line up. */
export const LABEL_ROW = 'mb-1 flex min-h-5 items-center gap-0.5 text-xs font-medium text-gray-600 dark:text-gray-300';

/** The unit written after an input: `€ 🇪🇺 EUR`, `%`, `units`. One width for all, so the inputs of a row line up. */
export const INPUT_SUFFIX = 'w-20 shrink-0 text-xs text-gray-500 dark:text-gray-400';

/** A unit inside the right edge of an input (`%`, `units`): the input keeps its full width and reserves the room with `pr-*`. */
export const INPUT_ADORNMENT = 'pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-gray-500 dark:text-gray-400';

/** A light Remove inside a row or a card header. */
export const BUTTON_DANGER_SMALL =
    'inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-red-500 dark:text-red-300 dark:hover:bg-red-950/40';

/** A bulk action over a list («All», «None»): the same pill as the Risk panel. */
export const BUTTON_PILL =
    'inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40 dark:border-slate-600 dark:text-gray-300 dark:hover:bg-slate-700';

export const HINT = 'text-xs text-gray-500 dark:text-gray-400';

/** A choice switched on and off by clicking its whole header (a funding source, a Broker for an Asset): tinted green when on. */
export const TOGGLE_CARD = 'overflow-hidden rounded-lg border text-sm transition-colors';
export const TOGGLE_ON = 'border-libre-green bg-libre-green/10 dark:bg-libre-green/20';
export const TOGGLE_OFF = 'border-gray-200 hover:border-gray-300 dark:border-gray-700 dark:hover:border-gray-600';

/** The small «?» next to a label that opens its explanation in a tooltip. */
export const HELP_BUTTON = 'rounded-sm p-0.5 text-gray-400 hover:text-gray-600 focus-visible:outline-2 focus-visible:outline-libre-green dark:hover:text-gray-300';

export const TABLE = 'min-w-full divide-y divide-gray-200 text-sm dark:divide-gray-700';

export const TH = 'px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400';

export const TD = 'px-3 py-2 align-top text-gray-800 dark:text-gray-200';

export const TD_NUM = 'px-3 py-2 text-right align-top tabular-nums text-gray-800 dark:text-gray-200';

export const BADGE_BASE = 'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium';

export const BADGE = {
    neutral: `${BADGE_BASE} bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200`,
    success: `${BADGE_BASE} bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200`,
    info: `${BADGE_BASE} bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200`,
    warning: `${BADGE_BASE} bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200`,
    danger: `${BADGE_BASE} bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200`,
} as const;

export const NOTICE = {
    info: 'rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900 dark:border-sky-900 dark:bg-sky-950/30 dark:text-sky-100',
    warning: 'rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100',
    danger: 'rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/30 dark:text-red-100',
    success: 'rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-100',
} as const;
