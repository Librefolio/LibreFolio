/** Shared Tailwind class sets of the planner UI: one place, so the review changes one file. */

export const BUTTON_PRIMARY =
    'inline-flex items-center justify-center gap-2 rounded-lg bg-libre-green px-4 py-2 text-sm font-semibold text-white hover:bg-libre-green/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:cursor-not-allowed disabled:opacity-50 dark:bg-green-600 dark:hover:bg-green-500';

export const BUTTON_SECONDARY =
    'inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700';

export const BUTTON_DANGER =
    'inline-flex items-center justify-center gap-2 rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-red-800 dark:bg-gray-800 dark:text-red-300 dark:hover:bg-red-950/40';

export const BUTTON_LINK = 'inline-flex items-center gap-1 rounded text-sm font-medium text-libre-green hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green dark:text-green-400';

export const CARD = 'rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800';

export const SECTION_TITLE = 'text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300';

export const INPUT = 'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-libre-green focus:outline-none focus:ring-1 focus:ring-libre-green disabled:opacity-60 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100';

export const LABEL = 'block text-xs font-medium text-gray-600 dark:text-gray-300';

export const HINT = 'text-xs text-gray-500 dark:text-gray-400';

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
