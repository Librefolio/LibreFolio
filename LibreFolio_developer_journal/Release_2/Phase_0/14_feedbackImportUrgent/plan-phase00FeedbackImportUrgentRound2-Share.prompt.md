# Round 2 - Social icons and Copy and go

**Date:** 2026-09-09.
**Previous round:** [Operational review R1](plan-phase00FeedbackImportUrgentRound1-Review.prompt.md).
**Follow-up:** [Round 3 - feedback social, broker e aggiornamenti](plan-phase00FeedbackImportUrgentRound3-SocialFeedback.prompt.md).
**Authorization:** direct developer feedback while reviewing About. This is the
approved U7 refinement; other R1 fixes remain unchanged.
**State:** completed 2026-09-09; original TEST data restored, R2 build serving on port 6041.

## Approved layout

```text
About / donation popup
  [ Buy me a coffee ]
       Or share
       [ X ] [ Reddit icon ]

Social dialog
  [ social icon ] Share on X / Reddit                 [x]
  Suggested message
  [ Friendly call to action                           ]
  [ Open-source / self-hosted / data-security note     ]

  [ Close ]                              [ Copy and go ]
```

No public URL field or separate Open action. The fixed public project URL is
always included in the copied content, never an instance URL or user data.

## 1. Shared social icons - completed 2026-09-09

Replace direct/manual rows with accessible social-icon buttons opening the dialog.
Use the same brand glyph in its header. Preserve coffee/later behavior and keep
social controls out of the global header/public login.

> **Note implementazione (2026-09-09):** native Svelte SVG component uses the X and
> Reddit paths from Simple Icons (CC0), with attribution and no new dependency.
> Shared About/popup callback is now `onShare`.

## 2. Copy and go - completed 2026-09-09

Copy the complete public message first, then navigate a new tab to the social
composer. Keep the origin open. Clipboard failure must not navigate; blocked or
closed tabs must report copied-but-not-opened honestly. Cancel owned pending blank
tabs on close/platform/session/unmount, without closing a social tab already handed off.

> **Note implementazione (2026-09-09):** clipboard starts before reserving a blank
> tab within the same click gesture; navigation waits for copy success. The reserved
> tab has no opener and a no-referrer policy. Shared clipboard primitive supports
> insecure self-hosted HTTP with checked `execCommand` success and focus restoration.
> Failed copies no longer produce false success through that shared fallback.

## 3. Copy and localization - completed 2026-09-09

Use a friendly first-person recommendation followed by a separate short paragraph
about open source, self-hosting and protecting data. No absolute security claims.
Translate Copy and go, feedback and message through the CLI in EN/IT/FR/ES.

> **Note implementazione (2026-09-09):** all four locales contain the new two-paragraph
> recommendation and Copy and go labels. Removed obsolete manual-share, URL-field and
> separate-Open keys. Both clipboard text and composer URL now fix the public project
> address in their builders; callers cannot substitute an instance URL.

## 4. Verification and restore - completed 2026-09-09

Test-author owns only support/clipboard tests; E alone executes commands. Cover
copy payload/order, icons and footer, removed URL/Open controls, blocked/failed
navigation, failure and stale cleanup. Rebuild, check the real browser flow, then
stop temporary processes and restore the original TEST directory, retaining the
new build. Update the operational checklist and notify the coordinator.

> **Note implementazione (2026-09-09):** support/clipboard component contracts pass,
> including the corrected 22-case subset; public-link builders (5), tab helper (4),
> and existing sync/scheduler copy consumers (29) pass. Real native-popup success
> and denied-copy scenarios pass on desktop and mobile. All test files are registered
> and reachable; four locale catalogues complete. Build/typecheck: zero errors/warnings.
>
> **⚠️ Fuori pista:** native browser evidence showed that parent-driven
> `location.replace` on a reserved blank tab still carried the parent's referrer,
> despite a no-referrer meta tag in the child. Navigation now uses a child-owned,
> hidden hyperlink with `rel="noopener noreferrer"` and `referrerPolicy="no-referrer"`.
> The real request has no Referer; no assertion was weakened and no private URL is
> inserted into either the copied message or the composer URL.
>
> **Note implementazione (2026-09-09):** temporary server stopped and port/DB handles
> checked before restoring the original TEST directory. Its database SHA256 matched
> the preserved original before restart; manual CSVs are unchanged. Temporary results
> and the independent WAL-aware backup remain private outside the repository.
> The old frontend backup was not restored.
>
> **Review runtime:** `http://127.0.0.1:6041`, PID `68600`, E worktree,
> HEAD `4a73f5f63447e01b51993afb2e3c73e2c22a9a28`.
> Served and on-disk `index.html` SHA256:
> `ab8b1458c1a49f1b835b3958d745e83e5a44f5d30e7c58d30ed4837941d0a4b6`.
> No scheduler/reloader, commits, staging, production access or C integration.
