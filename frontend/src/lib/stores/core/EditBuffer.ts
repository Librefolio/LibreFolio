/**
 * EditBuffer — Bidirectional edit buffer for pending chart modifications.
 *
 * Manages pending edits that haven't been saved to the backend yet.
 * Provides bidirectional sync between chart click-to-edit, CSV textarea, and "+" form.
 *
 * Each pending edit has a unique ID, a data point, a CSV line number, and a source.
 * When saved, all pending edits are sent to the backend in a single bulk operation.
 *
 * Used by FX edit mode (Phase 5) and Asset edit mode (Phase 6).
 *
 * @module stores/EditBuffer
 */

import type {TimeSeriesPoint} from './TimeSeriesStore';

// ============================================================================
// TYPES
// ============================================================================

/** Source of a pending edit */
export type EditSource = 'click' | 'csv' | 'form';

/** A single pending edit in the buffer */
export interface PendingEdit<T extends TimeSeriesPoint> {
    /** Unique identifier for this edit */
    id: string;
    /** The data point (modified or new) */
    point: T;
    /** Corresponding line number in the CSV textarea (1-based, excludes header) */
    csvLineNumber: number;
    /** How this edit was created */
    source: EditSource;
    /** Whether this is a new point (not in the original data) vs modification of existing */
    isNew: boolean;
}

/** Callback for buffer change notifications */
export type BufferChangeCallback<T extends TimeSeriesPoint> = (edits: PendingEdit<T>[]) => void;

// ============================================================================
// HELPERS
// ============================================================================

let nextId = 0;

function generateId(): string {
    return `edit_${++nextId}_${Date.now()}`;
}

// ============================================================================
// BUFFER
// ============================================================================

export class EditBuffer<T extends TimeSeriesPoint> {
    private edits: Map<string, PendingEdit<T>> = new Map(); // keyed by edit ID
    private dateIndex: Map<string, string> = new Map(); // date → edit ID (latest for that date)
    private listeners: Set<BufferChangeCallback<T>> = new Set();
    private nextCsvLine: number = 1;

    /** Number of pending edits */
    get size(): number {
        return this.edits.size;
    }

    /** Whether there are any pending edits */
    get hasChanges(): boolean {
        return this.edits.size > 0;
    }

    /**
     * Subscribe to buffer changes. Returns an unsubscribe function.
     */
    onChange(callback: BufferChangeCallback<T>): () => void {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }

    /**
     * Add a new pending edit.
     * If an edit for the same date already exists, it is replaced.
     *
     * @returns The created PendingEdit
     */
    add(point: T, source: EditSource, isNew: boolean = true): PendingEdit<T> {
        // Remove existing edit for the same date if present
        const existingId = this.dateIndex.get(point.date);
        if (existingId) {
            const existing = this.edits.get(existingId);
            // Reuse the CSV line number
            const csvLine = existing?.csvLineNumber ?? this.nextCsvLine++;
            this.edits.delete(existingId);

            const edit: PendingEdit<T> = {
                id: generateId(),
                point,
                csvLineNumber: csvLine,
                source,
                isNew,
            };
            this.edits.set(edit.id, edit);
            this.dateIndex.set(point.date, edit.id);
            this.notify();
            return edit;
        }

        const edit: PendingEdit<T> = {
            id: generateId(),
            point,
            csvLineNumber: this.nextCsvLine++,
            source,
            isNew,
        };

        this.edits.set(edit.id, edit);
        this.dateIndex.set(point.date, edit.id);
        this.notify();
        return edit;
    }

    /**
     * Update an existing pending edit by ID.
     */
    update(id: string, point: T): boolean {
        const existing = this.edits.get(id);
        if (!existing) return false;

        // If date changed, update the date index
        if (existing.point.date !== point.date) {
            this.dateIndex.delete(existing.point.date);
            this.dateIndex.set(point.date, id);
        }

        existing.point = point;
        this.notify();
        return true;
    }

    /**
     * Remove a pending edit by ID.
     */
    remove(id: string): boolean {
        const existing = this.edits.get(id);
        if (!existing) return false;

        this.dateIndex.delete(existing.point.date);
        this.edits.delete(id);
        this.notify();
        return true;
    }

    /**
     * Get a pending edit by its ID.
     */
    getById(id: string): PendingEdit<T> | undefined {
        return this.edits.get(id);
    }

    /**
     * Get the pending edit for a specific date (if any).
     */
    getByDate(date: string): PendingEdit<T> | undefined {
        const id = this.dateIndex.get(date);
        if (!id) return undefined;
        return this.edits.get(id);
    }

    /**
     * Get all pending edits, sorted by CSV line number.
     */
    getAll(): PendingEdit<T>[] {
        return Array.from(this.edits.values()).sort((a, b) => a.csvLineNumber - b.csvLineNumber);
    }

    /**
     * Get all pending edit points (just the data, sorted by date).
     */
    getAllPoints(): T[] {
        return Array.from(this.edits.values())
            .map((e) => e.point)
            .sort((a, b) => a.date.localeCompare(b.date));
    }

    /**
     * Get the CSV line number for a specific date's pending edit.
     * Returns undefined if no edit exists for that date.
     */
    getCsvLineForDate(date: string): number | undefined {
        const id = this.dateIndex.get(date);
        if (!id) return undefined;
        return this.edits.get(id)?.csvLineNumber;
    }

    /**
     * Replace all edits from CSV parsing.
     * This is called when the user modifies the CSV textarea.
     * Preserves edits from other sources (click, form) that aren't in the CSV.
     *
     * @param csvPoints - Points parsed from CSV, in order of appearance
     */
    replaceFromCsv(csvPoints: T[]): void {
        // Remove all edits that came from CSV
        for (const [id, edit] of this.edits) {
            if (edit.source === 'csv') {
                this.dateIndex.delete(edit.point.date);
                this.edits.delete(id);
            }
        }

        // Add new CSV edits
        let lineNum = 1;
        for (const point of csvPoints) {
            // Check if there's already a click/form edit for this date
            const existingId = this.dateIndex.get(point.date);
            if (existingId) {
                // Update the existing edit with CSV data
                const existing = this.edits.get(existingId);
                if (existing) {
                    existing.point = point;
                    existing.csvLineNumber = lineNum++;
                }
            } else {
                const edit: PendingEdit<T> = {
                    id: generateId(),
                    point,
                    csvLineNumber: lineNum++,
                    source: 'csv',
                    isNew: true,
                };
                this.edits.set(edit.id, edit);
                this.dateIndex.set(point.date, edit.id);
            }
        }

        this.nextCsvLine = lineNum;
        this.notify();
    }

    /**
     * Clear all pending edits. Used by Cancel action.
     */
    clear(): void {
        this.edits.clear();
        this.dateIndex.clear();
        this.nextCsvLine = 1;
        this.notify();
    }

    private notify(): void {
        const all = this.getAll();
        for (const listener of this.listeners) {
            listener(all);
        }
    }
}
