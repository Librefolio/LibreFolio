/**
 * Shared clipboard writer for the AI export feature — copies text with a
 * secure-context fallback (textarea + execCommand) and shows toast feedback.
 * Used by both the portfolio-level (aiExportClipboard.ts) and asset-level
 * (asset/assetExportClipboard.ts) export flows so the copy/feedback behavior
 * never drifts between the two.
 */

export type ToastFn = {
    success: (msg: string) => void;
    error: (msg: string) => void;
    warning: (msg: string) => void;
};

const PROMPT_SIZE_WARNING_THRESHOLD = 50_000;

/**
 * Writes `text` to the clipboard and shows a success/warning toast with
 * `copiedMessage`. Large exports get the char count appended as a warning
 * instead of a plain success, so the user knows to expect a sizeable paste.
 */
export async function writeExportToClipboard(text: string, toast: ToastFn, copiedMessage: string): Promise<void> {
    // navigator.clipboard requires a secure context, so self-hosted HTTP deployments need a textarea fallback.
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
    } else {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
    }

    if (text.length > PROMPT_SIZE_WARNING_THRESHOLD) {
        const sizeKb = Math.round(text.length / 1000);
        toast.warning(`${copiedMessage} (${sizeKb}K chars)`);
    } else {
        toast.success(copiedMessage);
    }
}
