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
        };
    }
}

export {};
