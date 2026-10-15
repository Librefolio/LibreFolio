// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
    namespace App {
        // interface Error {}
        // interface Locals {}
        // interface PageData {}
        // interface PageState {}
        // interface Platform {}
    }

    interface Window {
        /** Debug-only helpers, registered when isDebugEnabled() is true. See routes/(app)/+layout.svelte. */
        librefolioDebug?: {
            showDonationPopup: () => void;
            showUpdateModal: () => void;
        };
        /** Designer Lab hook, published by its client in debug builds only. See $lib/dev/designer-lab/client.ts. */
        __lfDesignerLab?: import('$lib/dev/designer-lab/types').LabHook;
    }

    /** Designer Lab switch, replaced at build time (vite.config.ts): true in debug builds and `vite dev`, false in release. */
    const __LF_DESIGNER_LAB__: boolean;
}

export {};
