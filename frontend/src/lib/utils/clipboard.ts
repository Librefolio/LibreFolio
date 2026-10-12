/**
 * Shared clipboard writer and consistent toast feedback for reusable copy actions.
 *
 * The secure Clipboard API goes first. The legacy copy (readonly textarea + execCommand) runs when
 * the API is missing — a plain-HTTP page outside localhost — or when it refuses the write: permission,
 * focus, policy. Every copy button goes through `writeTextToClipboard`; `clipboardSink.gate.test.ts`
 * keeps it that way.
 */

export type ToastFn = {
    success: (msg: string) => void;
    error: (msg: string) => void;
    warning: (msg: string) => void;
};

const PROMPT_SIZE_WARNING_THRESHOLD = 50_000;

/**
 * Starts the write inside the caller's click, before anything is awaited: a caller that opens a tab
 * in the same gesture (SocialShareModal) relies on it. With no transport at all it throws
 * synchronously; when the secure API refuses and the legacy copy fails too, it rejects with the
 * browser's own refusal.
 */
export function writeTextToClipboard(text: string): Promise<void> {
    if (navigator.clipboard?.writeText && window.isSecureContext) {
        return navigator.clipboard.writeText(text).catch((refusal: unknown) => {
            try {
                legacyCopy(text);
            } catch {
                throw refusal;
            }
        });
    }

    legacyCopy(text);
    return Promise.resolve();
}

/** Copies through a readonly off-screen textarea; throws when the browser rejects the copy. */
function legacyCopy(text: string): void {
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
