---
title: "In jsdom a dispatched click reaches a disabled button's handlers"
category: problem
status: workaround
date: 2026-10-19
tags: [frontend, testing, vitest, jsdom, svelte5, testing-library]
related: [decisions/no-range-of-a-single-day, problems/testing-library-events-prop-read-as-mount-option]
---

# Problem: In jsdom a dispatched click reaches a disabled button's handlers

## Symptom
A component disables a button to refuse a click, and a Vitest case checks that `fireEvent.click(button)` never
reaches the callback. With `disabled` alone, the callback would still run in the test. Found while writing the
Y-N65 reds for `CalendarMonth`, whose pending day is now disabled.

## Root Cause
jsdom blocks only `HTMLElement.click()` on a disabled control; it does not block a dispatched event. Testing
Library's `fireEvent.click` dispatches a `MouseEvent('click')`. Svelte 5 delegates `onclick` to a listener on
the root, which hears the event as it bubbles.

Probe, jsdom 30.0.1, a `<button disabled>` with a listener on itself and one on its parent:

| How the click arrives | Own listener | Delegated listener (ancestor) |
|---|---|---|
| `button.dispatchEvent(new MouseEvent('click', {bubbles: true}))` (what `fireEvent.click` does) | runs | runs |
| `button.click()` | does not run | does not run |

## Solution
Refuse the click in the handler as well as through the attribute. `CalendarMonth.svelte` already did this for
`disabledDates` (`if (!disabled) onDayClick(…)`), and Y-N65 extends the same check to the pending day:
`disabled={future || disabled || pendingDay}`, and `if (!disabled && !pendingDay) onDayClick(cell.iso)`.

## Prevention
- When a test asserts «a click on a disabled control does nothing», read it as «the handler refuses it», and keep
  the check in the handler.
- Alternatively, assert `toBeDisabled()` and leave the click out. A case that dispatches the click and expects
  silence pins the handler's check, which is what protects synthetic events.

## Impact
No product bug: a real user's click on a disabled button dispatches nothing in a browser. Without the check, the
test would pass or fail on the test harness rather than on the component.

## Source files
| Role | Path |
|------|------|
| The check in the handler | `frontend/src/lib/components/ui/date/CalendarMonth.svelte` |
| The cases that dispatch the click | `frontend/src/lib/components/ui/date/CalendarMonth.test.ts` |
