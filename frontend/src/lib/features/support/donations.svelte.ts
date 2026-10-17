/**
 * The one rule behind every invitation to donate (F05, lot A9 of workstream A): a hosting provider's customers get none.
 *
 * Shown only once the server has said `profile: 'selfhosted'` (`selfHostedConfirmed()`): the defaults the store holds
 * until it answers say self-hosted too, and a managed instance must never flash a donation while its
 * `GET /system/instance` is in flight. A reload that fails after an answer leaves that answer in force. Reactive: read
 * in a template or a `$derived`, it follows the store.
 */
import {selfHostedConfirmed} from '$lib/features/instance/profile';

export function donationsVisible(): boolean {
    return selfHostedConfirmed();
}
