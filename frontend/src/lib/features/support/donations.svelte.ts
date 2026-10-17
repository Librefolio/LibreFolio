/**
 * The one rule behind every invitation to donate (F05, lot A9 of workstream A): a hosting provider's customers get none.
 *
 * Shown only once the server has answered (`instanceConfig.loaded`) and said `profile: 'selfhosted'`: the defaults the
 * store holds until then say self-hosted too, and a managed instance must never flash a donation while its
 * `GET /system/instance` is in flight. A reload that fails after an answer leaves that answer in force. Reactive: read
 * in a template or a `$derived`, it follows the store.
 */
import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';

export function donationsVisible(): boolean {
    return instanceConfig.loaded && instanceConfig.config.profile === 'selfhosted';
}
