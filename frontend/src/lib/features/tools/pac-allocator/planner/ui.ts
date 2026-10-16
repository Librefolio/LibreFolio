/** Shared Tailwind class sets of the planner UI: one place, so the review changes one file. */

import {STATUS_TONES} from '$lib/theme/toneClasses';

export const BUTTON_PRIMARY =
    'inline-flex items-center justify-center gap-2 rounded-lg bg-lf-action px-4 py-2 text-sm font-semibold text-lf-on-action hover:bg-lf-action-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50';

export const BUTTON_SECONDARY =
    'inline-flex items-center justify-center gap-2 rounded-lg border border-lf-input bg-lf-card px-3 py-2 text-sm font-medium text-lf-secondary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50';

export const BUTTON_DANGER =
    'inline-flex items-center justify-center gap-2 rounded-lg border border-lf-danger-line bg-lf-card px-3 py-2 text-sm font-medium text-lf-danger hover:bg-lf-danger-soft focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-danger disabled:cursor-not-allowed disabled:opacity-50';

/** Confirms a replacement the user must notice (amber, like the shared ConfirmModal warning). */
export const BUTTON_WARNING =
    'inline-flex items-center justify-center gap-2 rounded-lg bg-lf-warning px-4 py-2 text-sm font-semibold text-lf-on-status hover:bg-lf-warning-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-warning disabled:cursor-not-allowed disabled:opacity-50';

export const BUTTON_LINK = 'inline-flex items-center gap-1 rounded text-sm font-medium text-lf-link hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus';

export const CARD = 'rounded-xl border border-lf-subtle bg-lf-card p-4';

/** R11.10: a small box inside a result section (a fact of the Proof, an objective value). */
export const TILE = 'rounded-lg border border-lf-subtle bg-lf-panel p-3';

/** The small title of a `TILE`. */
export const TILE_LABEL = 'text-xs font-medium uppercase tracking-wide text-lf-muted';

/** A card-sized button that starts an action: icon, title, one-line explanation. */
export const CHOICE_CARD =
    'flex h-full w-full flex-col items-start gap-1.5 rounded-xl border border-lf-subtle bg-lf-card p-3 text-left text-sm transition-colors hover:border-lf-link hover:bg-lf-selected/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-lf-subtle disabled:hover:bg-lf-card';

/** Round tinted holder for a lucide icon, sized like a small `BrokerIcon`. */
export const ICON_BUBBLE = 'flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-lf-selected text-lf-link';

/** R9.8: the step number of the operational plan, shared by the steps and the orders. */
export const STEP_NUMBER = 'inline-flex h-6 min-w-6 shrink-0 items-center justify-center rounded-full bg-lf-panel px-1.5 text-xs font-semibold tabular-nums text-lf-secondary';

export const SECTION_TITLE = 'text-sm font-semibold uppercase tracking-wide text-lf-secondary';

export const INPUT = 'w-full rounded-lg border border-lf-input bg-lf-field px-3 py-2 text-sm text-lf-primary placeholder:text-lf-placeholder hover:border-lf-input-hover focus:border-lf-focus focus:outline-none focus:ring-1 focus:ring-lf-focus disabled:opacity-60';

/** A card title the user renames in place: reads as a heading, shows its border on hover and focus. */
export const TITLE_INPUT =
    'w-full min-w-0 truncate rounded-md border border-transparent bg-transparent px-1.5 py-0.5 font-semibold text-lf-primary placeholder:font-normal placeholder:text-lf-placeholder hover:border-lf-input focus:border-lf-focus focus:outline-none focus:ring-1 focus:ring-lf-focus';

export const LABEL = 'block text-xs font-medium text-lf-secondary';

/** A label with a «?» beside it: one fixed height, so the fields of a row line up. */
export const LABEL_ROW = 'mb-1 flex min-h-5 items-center gap-0.5 text-xs font-medium text-lf-secondary';

/** The unit written after an input: `€ 🇪🇺 EUR`, `%`, `units`. One width for all, so the inputs of a row line up. */
export const INPUT_SUFFIX = 'w-20 shrink-0 text-xs text-lf-muted';

/** A unit inside the right edge of an input (`%`, `units`): the input keeps its full width and reserves the room with `pr-*`. */
export const INPUT_ADORNMENT = 'pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-lf-muted';

/** A light Remove inside a row or a card header. */
export const BUTTON_DANGER_SMALL = 'inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-lf-danger hover:bg-lf-danger-soft focus-visible:outline-2 focus-visible:outline-lf-danger';

/** A bulk action over a list («All», «None»): the same pill as the Risk panel. */
export const BUTTON_PILL = 'inline-flex items-center gap-1.5 rounded-lg border border-lf-subtle px-2.5 py-1 text-xs font-medium text-lf-secondary hover:bg-lf-hover disabled:opacity-40';

export const HINT = 'text-xs text-lf-muted';

/** A choice switched on and off by clicking its whole header (a funding source, a Broker for an Asset): tinted green when on. */
export const TOGGLE_CARD = 'overflow-hidden rounded-lg border text-sm transition-colors';
export const TOGGLE_ON = 'border-lf-checked bg-lf-selected';
export const TOGGLE_OFF = 'border-lf-subtle hover:border-lf-input';

/** The small «?» next to a label that opens its explanation in a tooltip. */
export const HELP_BUTTON = 'rounded-sm p-0.5 text-lf-muted hover:text-lf-secondary focus-visible:outline-2 focus-visible:outline-lf-focus';

export const TABLE = 'min-w-full divide-y divide-lf-subtle text-sm';

export const TH = 'px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-lf-muted';

export const TD = 'px-3 py-2 align-top text-lf-primary';

export const TD_NUM = 'px-3 py-2 text-right align-top tabular-nums text-lf-primary';

export const BADGE_BASE = 'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium';

/** Status badges: the layout here, the colours with every other status pattern in `$lib/theme/toneClasses`. */
export const BADGE = {
    neutral: `${BADGE_BASE} ${STATUS_TONES.pacBadge.neutral}`,
    success: `${BADGE_BASE} ${STATUS_TONES.pacBadge.success}`,
    info: `${BADGE_BASE} ${STATUS_TONES.pacBadge.info}`,
    warning: `${BADGE_BASE} ${STATUS_TONES.pacBadge.warning}`,
    danger: `${BADGE_BASE} ${STATUS_TONES.pacBadge.danger}`,
} as const;

const NOTICE_BASE = 'rounded-lg border p-3 text-sm';

/** Notices: the layout here, the colours in `$lib/theme/toneClasses`. */
export const NOTICE = {
    info: `${NOTICE_BASE} ${STATUS_TONES.pacNotice.info}`,
    warning: `${NOTICE_BASE} ${STATUS_TONES.pacNotice.warning}`,
    danger: `${NOTICE_BASE} ${STATUS_TONES.pacNotice.danger}`,
    success: `${NOTICE_BASE} ${STATUS_TONES.pacNotice.success}`,
} as const;
