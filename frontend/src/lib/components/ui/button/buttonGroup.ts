/**
 * The context a `ButtonGroup` gives its buttons (85 BTN-2·0, C2): inside a group, a `Button` draws as a segment
 * (`buttonClasses({segment: true})`). A module of its own, so `Button` reads the key without importing the group.
 */
import {getContext, setContext} from 'svelte';

const BUTTON_GROUP_KEY = Symbol('lf-button-group');

/** Called by `ButtonGroup`: its buttons are segments. */
export function provideButtonGroup(): void {
    setContext(BUTTON_GROUP_KEY, true);
}

/** Read by `Button`: whether it stands inside a `ButtonGroup`. */
export function insideButtonGroup(): boolean {
    return getContext<boolean | undefined>(BUTTON_GROUP_KEY) === true;
}
