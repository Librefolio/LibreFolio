# Review E - R1 + social refinement R2

**Ready:** 2026-09-09, `http://127.0.0.1:6041`.
**Data:** original TEST database, uploads and sidecars restored; manual CSVs unchanged.
**Build:** debug review build, index SHA256
`ab8b1458c1a49f1b835b3958d745e83e5a44f5d30e7c58d30ed4837941d0a4b6`.

Reload the page to load the new bundle. Sign in again if the old session expired.
Do not use production port 6040 for this review.

## Social sharing

1. Settings > About: coffee action plus X/Reddit icon buttons, without the old
   direct/manual button rows.
2. Click a social icon: a dialog opens with that social's logo and the suggested
   two-paragraph recommendation. No public URL field or separate Open action.
3. Footer: Close on the left, Copy and go on the right.
4. Copy and go copies the message AND the fixed public project link, then opens
   the social composer in another tab. About/the original popup stays open.
5. Denied clipboard: explicit error, no social navigation. Blocked popup after
   copying: explicit warning rather than claiming the site opened.
6. Donation popup uses the same flow; coffee and Maybe later retain their original
   dismissal behavior. On the TEST debug build its existing console hook is
   `window.librefolioDebug.showDonationPopup()`.

## Remaining R1 surfaces

| Route | Action | Expected |
|-------|--------|----------|
| Transactions > Import > file selection | Use a broker with more than five files, select across pages and fold/reopen | Five-row default, standard size choices, selections kept; after upload only recipient brokers start expanded |
| Import review > Create asset | Create a missing asset from the supplied synthetic report | Concise notice, known identifier prefilled as name if no name was extracted, visible required-name hint if cleared |
| Import review > Inspect/edit | Save metadata or confirm a currency change on a synthetic asset with a price | Metadata persists across reopening; confirmation is in front and counts/dates interpolate |
| Bulk workspace | Follow balance row references, change date sort | Complete group highlighted, first currently ordered matching row reached, no extra detail drawer, action header scrolls with its column |
| Brokers | Try a duplicate name; delete a disposable broker | Fully localized recovery message; actual deletion produces a green confirmation |
| Files | Sort/filter the uploader column and switch list/grid | Avatar/name multi-selection, URL/filter retained, unknown and missing uploader remain distinct |
| Long page, desktop/mobile | Scroll down/up; open menu/modal | Header hides/returns without a layout jump and stays pinned for interactions |
| Sidebar version > Check for updates | Run a successful up-to-date check | Green toast with the detected remote version on line two; failures are not called up to date |

Use `E-review-assets.csv` and `E-review-cash.csv` in this same folder. They contain
synthetic examples, not a personal ledger. New subjective refinements belong to
the next feedback round; this checklist does not claim that the developer has
already reviewed the final build.

## Answers from the first review

- Asset metadata disappeared because the inspector used a summary without
  classifications, then sent the apparent empty fields back as a deletion. Full
  edit reads and omission-versus-explicit-clear handling fix the round trip.
- Currency confirmation was behind the inspector. Adding a price in asset detail
  before the test was intentional preparation for that destructive-confirmation path.
- Manual FX could look complete while its hidden destination broker remained unset
  when the broker was picked before switching to FX. Only the shared broker is now
  derived; separate dates and financial checks are preserved.
- Update checks treated missing results from failures/cache/dismissal/image checks
  as “up to date”. These outcomes are now distinct; base-version ordering itself
  was not the demonstrated cause.
- Numbers such as 1a/1b are visual workspace row positions, not transaction IDs.
  Sorting can change those labels without changing IDs, pairing or payload order.
- First-import asset creation is intentionally manual. The original expectation of
  automatic creation was not evidence of a Generic CSV parser failure.
