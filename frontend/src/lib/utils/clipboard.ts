/**
 * Shared clipboard writer with a secure-context fallback (textarea +
 * execCommand) and consistent toast feedback for reusable copy actions.
 */

export type ToastFn = {
    success: (msg: string) => void;
    error: (msg: string) => void;
    warning: (msg: string) => void;
};

const PROMPT_SIZE_WARNING_THRESHOLD = 50_000;

export function writeTextToClipboard(text: string): Promise<void> {
    if (navigator.clipboard?.writeText && window.isSecureContext) {
        return navigator.clipboard.writeText(text);
    }

    const previousFocus = document.activeElement;
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.readOnly = true;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    try {
        textarea.focus({preventScroll: true});
        textarea.select();
        textarea.setSelectionRange(0, text.length);
        if (typeof document.execCommand !== 'function' || !document.execCommand('copy')) {
            throw new Error('Clipboard copy was rejected.');
        }
    } finally {
        textarea.remove();
        if (previousFocus instanceof HTMLElement && previousFocus.isConnected) {
            previousFocus.focus({preventScroll: true});
        }
    }
    return Promise.resolve();
}

/**
 * Writes `text` to the clipboard and shows a success/warning toast with
 * `copiedMessage`. Large exports get the char count appended as a warning
 * instead of a plain success, so the user knows to expect a sizeable paste.
 */
export async function writeExportToClipboard(text: string, toast: ToastFn, copiedMessage: string): Promise<void> {
    await writeTextToClipboard(text);

    if (text.length > PROMPT_SIZE_WARNING_THRESHOLD) {
        const sizeKb = Math.round(text.length / 1000);
        toast.warning(`${copiedMessage} (${sizeKb}K chars)`);
    } else {
        toast.success(copiedMessage);
    }
}
