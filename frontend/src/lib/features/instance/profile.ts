/**
 * The profile the server has confirmed (F05): the one test for whatever depends on it.
 *
 * `instanceConfig.config` holds `DEFAULT_INSTANCE_CONFIG`, a self-hosted instance, until `GET /system/instance`
 * answers, and keeps the last answer when a later request fails. So `config.profile === 'selfhosted'` alone is true
 * also while the request is in flight and when it never succeeded: what a managed instance must never show (an
 * invitation to donate, an update probe, a public issue link) waits for `selfHostedConfirmed()`, and what only a managed
 * instance shows waits for `managedConfirmed()`. Neither is true before the server has answered.
 *
 * A module of its own, not a getter of the store: the tests that replace the store with `vi.mock` keep working, since
 * these read only `loaded` and `config`. Reactive: read in a template or a `$derived`, they follow the store. The gate
 * `src/instanceProfile.gate.test.ts` keeps every other source from comparing a profile by hand.
 */
import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';

/** True once the server has answered on this page load and said `selfhosted`. */
export function selfHostedConfirmed(): boolean {
    return instanceConfig.loaded && instanceConfig.config.profile === 'selfhosted';
}

/** True once the server has answered on this page load and said `managed`. */
export function managedConfirmed(): boolean {
    return instanceConfig.loaded && instanceConfig.config.profile === 'managed';
}
