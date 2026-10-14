// @vitest-environment jsdom
import {afterEach, beforeEach, describe, expect, expectTypeOf, it, vi} from 'vitest';
import {writeExportToClipboard, writeTextToClipboard} from './clipboard';

/**
 * What jsdom itself has for the three properties these tests stub — today nothing: it implements
 * neither `navigator.clipboard`, nor `window.isSecureContext`, nor `document.execCommand`. Read once,
 * before any test defines them, so `afterEach` can put the environment back exactly as it found it.
 */
const ORIGINAL_SURFACE = [
    {target: navigator, key: 'clipboard', descriptor: Object.getOwnPropertyDescriptor(navigator, 'clipboard')},
    {target: window, key: 'isSecureContext', descriptor: Object.getOwnPropertyDescriptor(window, 'isSecureContext')},
    {target: document, key: 'execCommand', descriptor: Object.getOwnPropertyDescriptor(document, 'execCommand')},
] as const;

function restoreClipboardSurface() {
    for (const {target, key, descriptor} of ORIGINAL_SURFACE) {
        if (descriptor) Object.defineProperty(target, key, descriptor);
        else Reflect.deleteProperty(target, key);
    }
}

/** The refusal a browser gives when the secure API exists but will not write: permission, focus, policy. */
function secureRefusal() {
    return new DOMException('Write permission denied.', 'NotAllowedError');
}

function focusedOpener() {
    const opener = document.createElement('button');
    opener.type = 'button';
    document.body.appendChild(opener);
    opener.focus();
    return opener;
}

/**
 * A zero-delay timer is a macrotask: when it fires, every microtask queued before it has run —
 * promise reactions, MutationObserver deliveries. It orders the test after them; it waits for nothing.
 */
const drainMicrotasks = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

function setClipboard(writeText?: (text: string) => Promise<void>) {
    Object.defineProperty(navigator, 'clipboard', {
        value: writeText ? {writeText} : undefined,
        configurable: true,
        writable: true,
    });
}

function setSecureContext(value: boolean) {
    Object.defineProperty(window, 'isSecureContext', {
        value,
        configurable: true,
        writable: true,
    });
}

function setExecCommand(fn?: (command: string) => boolean) {
    Object.defineProperty(document, 'execCommand', {
        value: fn,
        configurable: true,
        writable: true,
    });
}

function makeToast() {
    return {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
    };
}

beforeEach(() => {
    document.body.innerHTML = '';
    setClipboard(undefined);
    setSecureContext(true);
    setExecCommand(undefined);
});

afterEach(() => {
    document.body.innerHTML = '';
    vi.restoreAllMocks();
    restoreClipboardSurface();
});

describe('writeTextToClipboard', () => {
    it('prefers navigator.clipboard.writeText in a secure context', async () => {
        const writeText = vi.fn().mockResolvedValue(undefined);
        const execCommand = vi.fn(() => true);
        setClipboard(writeText);
        setSecureContext(true);
        setExecCommand(execCommand);

        await writeTextToClipboard('ReviewSupport copy');

        expect(writeText).toHaveBeenCalledWith('ReviewSupport copy');
        expect(execCommand).not.toHaveBeenCalled();
        expect(document.querySelector('textarea')).toBeNull();
    });

    it('falls back to a hidden readonly textarea, selects all text and restores focus when execCommand succeeds', async () => {
        const opener = document.createElement('button');
        opener.type = 'button';
        document.body.appendChild(opener);
        opener.focus();

        const observed: {textarea: HTMLTextAreaElement | null} = {textarea: null};
        const execCommand = vi.fn((command: string) => {
            observed.textarea = document.querySelector('textarea');
            return command === 'copy';
        });
        setSecureContext(false);
        setExecCommand(execCommand);

        await writeTextToClipboard('ReviewSupport copy');

        expect(execCommand).toHaveBeenCalledWith('copy');
        expect(observed.textarea).not.toBeNull();
        if (!observed.textarea) throw new Error('Legacy fallback textarea was not created.');
        expect(observed.textarea).toHaveProperty('readOnly', true);
        expect(observed.textarea.style.position).toBe('fixed');
        expect(observed.textarea.style.left).toBe('-9999px');
        expect(observed.textarea.selectionStart).toBe(0);
        expect(observed.textarea.selectionEnd).toBe('ReviewSupport copy'.length);
        expect(document.querySelector('textarea')).toBeNull();
        expect(document.activeElement).toBe(opener);
    });

    it('throws synchronously and restores focus when execCommand explicitly reports failure', () => {
        const opener = document.createElement('button');
        opener.type = 'button';
        document.body.appendChild(opener);
        opener.focus();

        setSecureContext(false);
        setExecCommand(vi.fn(() => false));

        expect(() => writeTextToClipboard('ReviewSupport copy')).toThrow('Clipboard copy was rejected.');
        expect(document.querySelector('textarea')).toBeNull();
        expect(document.activeElement).toBe(opener);
    });

    it('throws synchronously when neither modern nor legacy clipboard transport is available', () => {
        setSecureContext(false);
        setExecCommand(undefined);

        expect(() => writeTextToClipboard('ReviewSupport copy')).toThrow('Clipboard copy was rejected.');
        expect(document.querySelector('textarea')).toBeNull();
    });
});

/**
 * A secure context does not promise a write: the API can exist and still refuse it — a permission
 * policy, a document without focus, an embedding frame. The helper then tries the legacy copy before
 * giving up, and when that fails too the caller gets the browser's own refusal, not a generic one.
 */
describe('writeTextToClipboard — the secure API refuses the write', () => {
    it('falls back to the readonly textarea + execCommand path, and resolves', async () => {
        const opener = focusedOpener();
        const refusal = secureRefusal();
        const writeText = vi.fn().mockRejectedValue(refusal);
        const atCopy: {value: string; readOnly: boolean; position: string; selectionStart: number | null; selectionEnd: number | null}[] = [];
        const execCommand = vi.fn((command: string) => {
            const textarea = document.querySelector('textarea');
            if (textarea) atCopy.push({value: textarea.value, readOnly: textarea.readOnly, position: textarea.style.position, selectionStart: textarea.selectionStart, selectionEnd: textarea.selectionEnd});
            return command === 'copy';
        });
        setClipboard(writeText);
        setSecureContext(true);
        setExecCommand(execCommand);

        await expect(writeTextToClipboard('ReviewSupport copy')).resolves.toBeUndefined();

        expect(writeText).toHaveBeenCalledTimes(1);
        expect(writeText).toHaveBeenCalledWith('ReviewSupport copy');
        expect(execCommand).toHaveBeenCalledTimes(1);
        expect(execCommand).toHaveBeenCalledWith('copy');
        // What the legacy copy saw when it ran: the text, in a readonly fixed textarea, fully selected.
        expect(atCopy).toEqual([{value: 'ReviewSupport copy', readOnly: true, position: 'fixed', selectionStart: 0, selectionEnd: 'ReviewSupport copy'.length}]);
        expect(document.querySelector('textarea')).toBeNull();
        expect(document.activeElement).toBe(opener);
    });

    it('rejects with the original refusal — the same object — when execCommand reports failure', async () => {
        const opener = focusedOpener();
        const refusal = secureRefusal();
        const copied: string[] = [];
        const execCommand = vi.fn(() => {
            copied.push(document.querySelector('textarea')?.value ?? '<no textarea>');
            return false;
        });
        setClipboard(vi.fn().mockRejectedValue(refusal));
        setSecureContext(true);
        setExecCommand(execCommand);

        await expect(writeTextToClipboard('ReviewSupport copy')).rejects.toBe(refusal);

        // The legacy copy was really attempted, on the text, before the refusal was passed on.
        expect(execCommand).toHaveBeenCalledTimes(1);
        expect(execCommand).toHaveBeenCalledWith('copy');
        expect(copied).toEqual(['ReviewSupport copy']);
        expect(document.querySelector('textarea')).toBeNull();
        expect(document.activeElement).toBe(opener);
    });

    it('rejects with the original refusal when there is no legacy transport either', async () => {
        const opener = focusedOpener();
        const refusal = secureRefusal();
        setClipboard(vi.fn().mockRejectedValue(refusal));
        setSecureContext(true);
        setExecCommand(undefined);

        await expect(writeTextToClipboard('ReviewSupport copy')).rejects.toBe(refusal);

        expect(document.querySelector('textarea')).toBeNull();
        expect(document.activeElement).toBe(opener);
    });
});

describe('writeTextToClipboard — a secure write in flight', () => {
    it('starts the secure write inside the call, and never touches the legacy path while it is pending or once it resolved', async () => {
        let resolveWrite: () => void = () => undefined;
        const writeText = vi.fn(
            () =>
                new Promise<void>((resolve) => {
                    resolveWrite = resolve;
                }),
        );
        const execCommand = vi.fn(() => true);
        setClipboard(writeText);
        setSecureContext(true);
        setExecCommand(execCommand);
        // Every textarea attached anywhere in the document, even one removed again in the same tick.
        const attached: Node[] = [];
        const observer = new MutationObserver((records) => {
            for (const record of records) for (const node of record.addedNodes) if (node instanceof Element && (node.matches('textarea') || node.querySelector('textarea'))) attached.push(node);
        });
        observer.observe(document.documentElement, {childList: true, subtree: true});

        try {
            // The observer's presence barrier: it does report a textarea attached and removed in one tick.
            const probe = document.body.appendChild(document.createElement('textarea'));
            probe.remove();
            await drainMicrotasks();
            expect(attached).toEqual([probe]);
            attached.length = 0;

            const pending = writeTextToClipboard('ReviewSupport copy');

            // Before anything is awaited: a caller that opens a tab in the same click
            // (SocialShareModal) relies on the write having started inside the user gesture.
            expect(writeText).toHaveBeenCalledTimes(1);
            expect(writeText).toHaveBeenCalledWith('ReviewSupport copy');

            await drainMicrotasks();
            expect(execCommand).not.toHaveBeenCalled();
            expect(attached).toEqual([]);

            resolveWrite();
            await expect(pending).resolves.toBeUndefined();
            await drainMicrotasks();
            expect(execCommand).not.toHaveBeenCalled();
            expect(attached).toEqual([]);
            expect(document.querySelector('textarea')).toBeNull();
        } finally {
            observer.disconnect();
        }
    });

    it('keeps its signature: one string in, a Promise<void> out', () => {
        expectTypeOf(writeTextToClipboard).toEqualTypeOf<(text: string) => Promise<void>>();
        expect(writeTextToClipboard).toHaveLength(1);
    });
});

describe('writeExportToClipboard', () => {
    it('keeps the success-toast contract for smaller payloads', async () => {
        const writeText = vi.fn().mockResolvedValue(undefined);
        const toast = makeToast();
        setClipboard(writeText);
        setSecureContext(true);

        await writeExportToClipboard('short export', toast, 'Copied');

        expect(writeText).toHaveBeenCalledWith('short export');
        expect(toast.success).toHaveBeenCalledWith('Copied');
        expect(toast.warning).not.toHaveBeenCalled();
        expect(toast.error).not.toHaveBeenCalled();
    });

    it('keeps the size-warning contract for larger payloads', async () => {
        const writeText = vi.fn().mockResolvedValue(undefined);
        const toast = makeToast();
        setClipboard(writeText);
        setSecureContext(true);
        const largeExport = 'x'.repeat(50_500);

        await writeExportToClipboard(largeExport, toast, 'Copied');

        expect(writeText).toHaveBeenCalledWith(largeExport);
        expect(toast.warning).toHaveBeenCalledWith('Copied (51K chars)');
        expect(toast.success).not.toHaveBeenCalled();
        expect(toast.error).not.toHaveBeenCalled();
    });

    it('does not emit a false-green toast when the legacy clipboard fallback rejects the copy', async () => {
        const toast = makeToast();
        setSecureContext(false);
        setExecCommand(vi.fn(() => false));

        await expect(writeExportToClipboard('short export', toast, 'Copied')).rejects.toThrow('Clipboard copy was rejected.');

        expect(toast.success).not.toHaveBeenCalled();
        expect(toast.warning).not.toHaveBeenCalled();
        expect(toast.error).not.toHaveBeenCalled();
    });
});

describe('writeExportToClipboard — the secure API refuses the write', () => {
    it('confirms the copy the legacy path made: the success toast, not a false red', async () => {
        const toast = makeToast();
        const writeText = vi.fn().mockRejectedValue(secureRefusal());
        const execCommand = vi.fn(() => true);
        setClipboard(writeText);
        setSecureContext(true);
        setExecCommand(execCommand);

        await expect(writeExportToClipboard('short export', toast, 'Copied')).resolves.toBeUndefined();

        expect(writeText).toHaveBeenCalledWith('short export');
        expect(execCommand).toHaveBeenCalledTimes(1);
        expect(execCommand).toHaveBeenCalledWith('copy');
        expect(toast.success).toHaveBeenCalledTimes(1);
        expect(toast.success).toHaveBeenCalledWith('Copied');
        expect(toast.warning).not.toHaveBeenCalled();
        expect(toast.error).not.toHaveBeenCalled();
    });

    it('rejects with the original refusal, and shows no toast at all, when the legacy copy fails too', async () => {
        const toast = makeToast();
        const refusal = secureRefusal();
        const execCommand = vi.fn(() => false);
        setClipboard(vi.fn().mockRejectedValue(refusal));
        setSecureContext(true);
        setExecCommand(execCommand);

        await expect(writeExportToClipboard('short export', toast, 'Copied')).rejects.toBe(refusal);

        expect(execCommand).toHaveBeenCalledTimes(1);
        expect(execCommand).toHaveBeenCalledWith('copy');
        expect(toast.success).not.toHaveBeenCalled();
        expect(toast.warning).not.toHaveBeenCalled();
        expect(toast.error).not.toHaveBeenCalled();
        expect(document.querySelector('textarea')).toBeNull();
    });
});
