/**
 * splitRowCharges.ts — carve one imported row's amount into a trade plus its charges.
 *
 * A bank statement often gives a single amount for something that happened in several
 * pieces: a bond bought on the secondary market pays price, accrued interest and
 * commissions in one debit, and the file never separates them. The importer refuses to
 * invent the breakdown, but the user has it on their contract note — so they list the
 * charges they can name and the trade leg is whatever is left.
 *
 * That is the whole point of computing the trade leg instead of asking for it: the legs
 * add back up to the row by construction, so a split can never drift away from the
 * statement it came from. The user can only ever move money *between* legs, never in or
 * out of the import.
 *
 * @module utils/transactions/splitRowCharges
 */

import {normalizeDecimalInput} from '$lib/utils/core/parseDecimalInput';

/** Which way the money moved on the statement row. */
export type RowDirection = 'out' | 'in';

/** The natures a charge can have. Mapped to transaction types by the caller. */
export type ChargeKind = 'fee' | 'tax' | 'accrued';

export interface ChargeDraft {
    kind: ChargeKind;
    /** Raw user input, in any accepted decimal notation. */
    amount: string;
}

export interface ChargeLeg {
    kind: ChargeKind;
    /** Normalised magnitude, always > 0. */
    amount: string;
}

export interface RowSplit {
    /** Magnitude of the row's own amount, at its own scale. */
    total: string;
    /** The charges that parsed to a usable number. */
    charges: ChargeLeg[];
    /** Their sum, as a magnitude. */
    chargesTotal: string;
    /**
     * Magnitude of the remaining trade leg. On a purchase the charges come *out* of the
     * total (you paid less for the security than the account shows); on a sale they were
     * already withheld, so the gross proceeds are *larger* than what was credited.
     */
    main: string;
    /** At least one charge has been typed — errors stay hidden until then. */
    touched: boolean;
    valid: boolean;
    /** Why it is not valid, once touched. */
    error: null | 'nonpositive' | 'exceeds';
}

function decimalsOf(value: string): number {
    const dot = value.indexOf('.');
    return dot < 0 ? 0 : value.length - dot - 1;
}

/**
 * Arithmetic carried out on the scale of its operands rather than in binary floating
 * point, where `50683.13 - 50018.11` yields `665.0199999999968`. Legs that do not add
 * back up to the statement are exactly what this module exists to prevent.
 */
function fixed(values: string[], combine: (units: number[]) => number): {value: string; scale: number} {
    const scale = Math.max(2, ...values.map(decimalsOf));
    const factor = 10 ** scale;
    const units = values.map((v) => Math.round(Number(v) * factor));
    return {value: (combine(units) / factor).toFixed(scale), scale};
}

/**
 * @param rowAmount signed amount of the source row
 * @param direction which way that amount moved — decides on which side the charges land
 * @param drafts    what the user has typed so far, one entry per charge line
 */
export function splitRowCharges(rowAmount: string | number, direction: RowDirection, drafts: ChargeDraft[]): RowSplit | null {
    const raw = String(rowAmount ?? '').trim();
    const amount = Number(raw);
    // `Number('')` is 0, which would read as a perfectly valid row of zero.
    if (raw === '' || !Number.isFinite(amount) || amount === 0) return null;

    const total = Math.abs(amount).toFixed(Math.max(decimalsOf(raw), 2));
    const touched = drafts.some((d) => d.amount.trim() !== '');

    const charges: ChargeLeg[] = [];
    let anyBad = false;
    for (const draft of drafts) {
        if (draft.amount.trim() === '') continue;
        const normalised = normalizeDecimalInput(draft.amount);
        const value = Number(normalised);
        // A leg of zero is not a charge, and a negative one would be money the bank
        // never moved: both mean the line is not answerable yet, not that it is empty.
        if (!Number.isFinite(value) || value <= 0) {
            anyBad = true;
            continue;
        }
        charges.push({kind: draft.kind, amount: normalised});
    }

    const chargesTotal = fixed(charges.map((c) => c.amount).concat(total), (units) => units.slice(0, -1).reduce((sum, u) => sum + u, 0)).value;
    const main = fixed([total, chargesTotal], ([t, c]) => (direction === 'out' ? t - c : t + c)).value;

    // Charges bigger than a purchase would leave nothing bought — or worse, a negative
    // price. On a sale there is no such ceiling: the gross simply exceeds the net.
    const exceeds = direction === 'out' && Number(main) <= 0;
    const error = !touched ? null : anyBad ? 'nonpositive' : exceeds ? 'exceeds' : null;

    return {total, charges, chargesTotal, main, touched, valid: touched && charges.length > 0 && error === null, error};
}
