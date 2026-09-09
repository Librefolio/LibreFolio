// @vitest-environment jsdom
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {writeExportToClipboard, writeTextToClipboard} from './clipboard';

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
