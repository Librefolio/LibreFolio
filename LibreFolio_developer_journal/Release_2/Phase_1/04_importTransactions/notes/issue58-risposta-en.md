Hi @jaska087, thanks for the report and for the clear steps.

We think this may not be a bug, but we want to make sure we are looking at the right place.

**What we think is happening.** In the transaction edit window, the **Save** button (it is called **Apply** when the window was opened from the multi-row editor, "Transactions · N rows") is only enabled while the entry is valid for its type. Every transaction type has its own rules: which amounts are required and which sign the cash and the quantity must have. When you change the type, the amounts already in the form were entered for the old type and may not fit the new one. The form then flags them (for example with a hint like "must be > 0" or "… requires a positive cash amount") and Save stays disabled until they are fixed.

Changing the type is still a change, which is why closing the window asks whether to discard it. So "Save is disabled" and "there are unsaved changes" can both be true at the same time.

**Where.** The Save / Apply button at the bottom right of the transaction edit window, and the amount fields just above it.

Could you confirm that this is the right place?

1. Is it the window for editing one transaction (opened from the transactions table), or the multi-row editor with the **Apply** button?
2. Which type did you change from and to, and does a field turn red or show a hint after the change?
3. If you correct every flagged field, does Save become available?
4. A screenshot of the window right after changing the type would help a lot.

If the button stays disabled while every field is valid and no hint is shown, that is a bug and we will fix it. And if it is just not clear why the button is disabled, we will look at showing the reason next to it.

Thanks again!
