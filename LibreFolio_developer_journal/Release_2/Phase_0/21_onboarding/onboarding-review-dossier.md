# Onboarding — Developer Review Dossier

> **Status as of writing**: worktree `e-alfy-literate-lamp`, branch `e-alfy-onboarding-foundation`,
> HEAD `580bd504fd1d0d3b7b3ee2a8ac0407ef5187a476`, working tree clean (0 modified / 0 staged /
> 0 untracked / 0 unmerged), `41 behind / 0 ahead` of `dev_release2`, port 6158 free, no owned
> process. The work is **already merged into `dev_release2`** via `3913fe217`
> (`Merge branch 'e-alfy-allocatore-pac' into dev_release2`) — it arrived folded inside the PAC
> branch, which is why it has never been described on its own terms.
>
> **Author**: workstream J (agent). **This document exists because a feature that was explicitly
> backlogged as "do not estimate until the user details it with us" was built anyway.** Everything
> in §2 is a product decision an agent made on the developer's behalf. I am the named owner of
> those decisions.
>
> **This document is written to stand alone.** The session that produced it is being archived and
> its worktree removed; no follow-up question can be asked of its author. Where a reference would
> normally be made to a prior discussion, the substance is written out here instead. The only
> external references are the seven round plans
> (`plan-phase00Onboarding*.prompt.md`, same folder), which are **already committed in
> `dev_release2`** and therefore survive independently of this worktree.

---

## 1. The arc — what was asked, what it became

### 1.1 What was asked

The kickoff scope was **SP11/U8** from
`LibreFolio_developer_journal/Release_2/Phase_0/09_feedbackJobs/01_ux_dashboard.md` and
`06_piano_sprint.md`. The coordinator handed down a short list of already-fixed decisions:

- a dedicated welcome page (not a modal);
- language/currency seeded from admin defaults;
- optional avatar;
- existing theme default (no theme picker);
- a short, skippable overlay tour;
- a contextual import guide following the **real** conditional wizard steps through Bulk/Save All,
  **without automatic writes**;
- no demo financial data;
- welcome/tour/import states versioned **separately**, not inferred from `login_count`;
- permanent skip with manual replay from Settings;
- coordination with refresh/account switching, focus/mobile, Header, donation/update popup.

That is roughly *"a welcome page, one tour, and one import guide"* — **three** surfaces.

### 1.2 What it became

**Fifteen** registered flows, of which two are step-managed with server-persisted per-step progress:

| Family | Flows | Steps |
|---|---|---|
| Setup | `welcome` | — (single page) |
| Core | `intro_tour` | 9 |
| Transactions | `transactions_page_guide`, `transaction_create_guide`, `transaction_bulk_guide`\*, `import_guide`\* | 4 / 4 / 4 / 8 |
| Broker | `broker_page_guide`, `broker_guide`, `broker_detail_guide` | 4 / 3 / 5 |
| FX | `fx_page_guide`, `fx_guide`, `fx_detail_guide` | 4 / 2 / 4 |
| Asset | `asset_page_guide`, `asset_guide`, `asset_detail_guide` | 4 / 3 / 5 |

\* = `completionMode: 'steps'` (per-step rows persisted server-side). `transaction_bulk_guide`
additionally uses `navigationMode: 'checkpoint'`.

Total: **15 flows, 59 steps, 12 of them individually persisted**.

### 1.3 The six rounds, and where each one changed direction

| Round | Plan file | What it was meant to do | **The fork** |
|---|---|---|---|
| 0 | `plan-phase00Onboarding.prompt.md` | Welcome page + intro tour + import guide, DB + API + store | Established the versioned-per-flow model instead of a single `onboarding_completed` boolean. **This is the decision that made everything after it possible — and expensive.** |
| 1 | `…Round1-UXRefinement` | Polish the welcome page and tour copy | Tour moved from a static modal carousel to **anchored coachmarks** over real UI. This is the fork that introduced anchors, and therefore every fragility in §4. |
| 2 | `…Round2-ModularGuides` | Generalise the import guide | **Generalised it to a catalog.** One guide became a registry; the 12 contextual guides were authored here. Scope roughly quadrupled in one round. |
| 3 | `…Round3-TriggeredTours` | Make guides appear at the right moment | Introduced **contextual triggers + a queue + replay tokens**. Guides stopped being "things you launch" and became "things that happen to you". |
| 4 | `…Round4-GeometryMilestones` | Fix coachmark placement | Built a full **geometry settlement engine** (two-frame stability, transition/resize/scroll following, scroll-root detection, header-safe correction). Also made the import guide follow the wizard's **real** milestones rather than a scripted sequence. |
| 5 | `…Round5-StepProgressPolish` | Persist where the user got to | Added `user_onboarding_step_progress` + step endpoints + aggregate rollup. **A developer correction mid-round removed all v1/v2 contract compatibility** — onboarding never shipped in 1.1.0, so only J's local test server had ever seen the intermediate contract. Migration 003 was edited in place; there is no 004. |
| 6 | `…Round6-FinalUX` | Final polish + gates | Developer approved the UX verbatim: *"ok chat, ho visionato un pò tutto e non ho visto problemi! mi piace!"*. Post-OK: docs, full gates, read-only review (one Medium finding fixed), checkpoint. |

**The honest summary of the arc**: rounds 0–1 delivered the brief. Rounds 2–5 delivered a *platform*
that nobody asked for, in response to my own judgement that a single import guide would look
arbitrary next to twelve un-guided screens. That judgement may be right. It was not authorised.

---

## 2. The decisions nobody authorised

> Read this section first. Everything here is a place where the brief was silent and I chose.
> Each entry states **what I chose**, **what I rejected**, **why**, and **how to reverse it** if
> the developer disagrees.

### 2.1 Tour vs coachmarks vs welcome page — I chose *all three*, layered

- **Chosen**: a dedicated full-page `/welcome` route for setup; anchored coachmarks over the live
  UI for the intro tour; the same coachmark machinery for 13 contextual guides.
- **Rejected**: a modal carousel with screenshots (cheap, robust, never breaks, but lies about the
  UI as soon as the UI changes); a one-off tooltip on first visit per page (no sequencing, no
  progress, no completion state).
- **Why**: a carousel cannot show the user *their own* empty portfolio, and the brief explicitly
  wanted "no demo financial data". Anchoring to real DOM was the only way to point at real things.
- **Cost**: anchors are the fragile part (§4.3). A carousel would have zero anchor risk.
- **Reverse**: the coachmark layer is isolated in `OnboardingOverlayHost.svelte` +
  `OnboardingCoachmark.svelte`. Replacing it with a static carousel would not touch the backend,
  the store, or the catalog.

### 2.2 What a new user sees first, and in what order

The order is **mine**. Nobody specified it.

1. **`/welcome`** — hard redirect. The app shell is not reachable while `welcome` is `pending`.
   Page order inside: avatar (optional) → language → base currency → theme hint (read-only,
   explains the theme was inherited) → Continue / Skip.
2. **`intro_tour`** — 9 steps, auto-starts on `/dashboard` right after Welcome terminates.
   Order: `intro.scene` (centred, no anchor) → `intro.navigation` (the nav toggle) →
   `intro.dashboard` → then one step per nav entry: transactions → brokers → fx → assets → tools →
   settings. The tour **drives navigation itself** (`goto`) and opens/closes the sidebar.
3. **Contextual guides** — from then on, whenever the user first lands on a guided surface.

**Why this order**: avatar first because it is the only purely cosmetic field and putting it first
makes the page feel like a greeting rather than a form; language before currency because changing
language re-renders the currency labels; theme last as a hint, not a control, because the brief
said "existing theme default".

**Why the tour follows the nav order**: it matches the sidebar top-to-bottom so the user's eye
learns the sidebar, not the tour.

**Objection I would raise if I were the developer**: six of the nine intro steps are "here is a nav
link". That is arguably a nav legend, not a tour. It could be cut to 4 steps without losing much.

### 2.3 When it triggers, when it re-triggers

- **Welcome**: triggers when the `welcome` row is `pending`. Enforced by a **redirect in the layout**,
  not by a popup — it is not dismissable by ignoring it.
- **Intro tour**: triggers automatically once Welcome is terminal and the user is on `/dashboard`.
- **Contextual guides**: trigger the first time the user reaches the host surface, while the flow is
  `pending`.
- **Re-trigger**: **never automatically.** A terminal flow (`completed` or `skipped`) stays terminal.
  The only way back is an explicit replay from Settings.
- **Version bump = re-trigger**: if `ONBOARDING_FLOW_VERSIONS[flow]` is incremented in a future
  release, the flow becomes due again and Settings shows an "update available" marker. All 15 flows
  are currently at **version 1**, so this path has never run in anger. **Untested in production terms.**

### 2.4 Can it be dismissed forever? Yes — and that was a choice

The brief said "permanent skip with manual replay from Settings", so this one *was* authorised.
What was **not** authorised is the granularity:

- Skipping the **intro tour** skips the whole flow.
- Skipping a **step-managed** flow (`import_guide`, `transaction_bulk_guide`) via the X skips
  **only the current step**; the flow stays due until every step is terminal.
- A flow is `skipped` in aggregate **only if every step was skipped**; a mix of skipped and
  completed steps rolls up to `completed`.

That asymmetry (X means "skip flow" in 13 places and "skip this step" in 2) is a real UX
inconsistency I introduced deliberately, because skipping one wizard step should not forfeit the
remaining seven. **It is still an inconsistency and the developer may want it uniform.**

### 2.5 Second device / second browser

- Progress is **server-side per user**, so a second device sees the same terminal state and gets
  **no tour**. That is the behaviour I chose.
- **But replay tokens are `sessionStorage`-only**, keyed `lf_{userId}_onboarding_replay_{flow}_v{n}`.
  So: arming a replay on the desktop and then opening the phone gives you **nothing** on the phone.
  Replay is per-tab, per-session, and dies with the tab.
- **This is not documented in the UI.** A user who arms a replay, closes the tab, and comes back
  will find it silently gone. See §5.4 — this is on the "plausible but wrong" list.

### 2.6 Welcome "Skip" writes nothing

Skipping Welcome does **not** write language/currency/avatar. The user keeps the admin defaults.
The row goes `skipped`. I chose this because writing settings the user explicitly declined to
confirm is worse than leaving them at the default — but it does mean **"Skip" silently accepts the
admin's language**, which for a non-English admin default could hand an English-speaking user an
Italian UI. Nobody asked me to decide that.

### 2.7 Replay of Welcome does not reset it

Replaying `welcome` from Settings shows the page again but **performs no backend transition** —
neither Continue nor Skip writes onboarding state in replay mode. Continue in replay mode also does
**not** re-write the settings. It is a pure preview. I chose this so a replay can never un-complete
onboarding; the side effect is that **Welcome replay cannot be used to change your language** —
that is what the Preferences tab is for. A user may reasonably expect otherwise.

### 2.8 Guides own the popup lane

While any guide is active (or any modal is open), the donation popup and the update popup are
**suppressed entirely**, not queued-and-shown-after. Donation wins over update when both are due.
Nobody specified this ordering; I chose "onboarding beats everything, donation beats update".

### 2.9 The app shell is `inert` during the intro tour

During `intro_tour` the whole app shell gets `inert`, so the user cannot click anything except the
coachmark. This makes the tour reliable and makes it **feel modal**, which contradicts "short
skippable overlay". It is skippable (the X is always live) but it is not explorable.
This is a deliberate trade I made for geometry stability.

---

## 3. Backend

### 3.1 `backend/app/services/onboarding_service.py` (406 lines)

- **Registries**: `ONBOARDING_FLOW_VERSIONS` (15 flows → version 1) and `ONBOARDING_FLOW_STEPS`
  (2 flows → their step ID tuples). These are the source of truth; the frontend catalog must agree
  with them and nothing enforces that agreement at build time (§5.5).
- **`ensure_onboarding_progress(user)`**: idempotent lazy seeding via SQLite
  `INSERT … ON CONFLICT DO NOTHING`. It **never rewrites persisted progress**. If rows are still
  missing after the upsert it raises `RuntimeError` rather than returning a half-populated view.
- **Transitions**: `complete`/`skip` at flow level and step level. A flow-level transition on a
  step-managed flow **cascades to all its steps**.
- **`_apply_step_flow_aggregate`**: flow is `pending` while any registered current-version step is
  non-terminal; `skipped` only when every step is skipped; otherwise `completed`.
- **`complete_welcome_onboarding`**: writes `language`, `base_currency`, optional avatar; theme
  comes from the admin default `DEFAULT_THEME`; **rolls back the whole transaction on error** so you
  cannot end up marked complete with unsaved settings.

### 3.2 API surface (`backend/app/api/v1/settings.py`, ~lines 109–285)

| Method | Path | Notes |
|---|---|---|
| `GET` | `/settings/onboarding` | Returns `{flows: [...]}`; `steps` omitted for non-step flows (`response_model_exclude_none=True`) |
| `POST` | `/settings/onboarding/{flow}/complete` | Accepts `welcome_settings` **only** for `welcome` |
| `POST` | `/settings/onboarding/{flow}/skip` | |
| `POST` | `/settings/onboarding/{flow}/steps/{step_id}/complete` | Body: `expected_version` only, extra-forbid |
| `POST` | `/settings/onboarding/{flow}/steps/{step_id}/skip` | Same |

- Version mismatch → **409** `{code: 'onboarding_version_mismatch', flow, expected_version, current_version}`.
- `welcome_settings` on any other flow, or on `skip` → **422**.
- There is **no** `contract_version` query parameter and no legacy DTO. That was removed on developer
  instruction in Round 5.

### 3.3 Migration `003_user_onboarding_progress` — **and the upgrade path**

Creates two tables, both `ON DELETE CASCADE` on `user_id`, both with status/version CHECK constraints:

- `user_onboarding_progress` — unique `(user_id, flow)`
- `user_onboarding_step_progress` — unique `(user_id, flow, step_id)`

**What happens to an existing user who upgrades into this:**

- `welcome` → **`completed`**, timestamped at migration time. They are **not** asked for language
  and currency again. Their existing settings are untouched.
- All **14 guides** → **`skipped`**, with `skipped_at` set. All **12 step rows** → **`skipped`**.

**So an existing user is offered nothing: not the welcome page, not the intro tour, not a single
contextual guide.** Onboarding is for genuinely new signups. `skipped` rather than `completed` is
deliberate and it is the truthful record: it distinguishes *"never offered"* from *"did it"*, which
matters the day someone asks why a long-standing user has no tour history.

> ⚠️ **Correction, Round 7 Step 1 (2026-09-21) — read this before treating the approval below as a
> confirmation, because it is not one.**
>
> This section originally stated the opposite: that the 14 guides were seeded **`pending`**, and
> therefore that *"an existing user gets the full intro tour and every contextual guide on next
> use"*. **That was accurate for the code this dossier reviewed** (branch head `580bd504f`, where
> migration 003 line 8 read *"Every guide starts pending and appears only at its own trigger"*).
> It stopped being accurate when the migration was changed on the way into `dev_release2`
> (28 insertions / 22 deletions on that file), which is the version described above.
>
> **The consequence is the part worth recording.** The developer read the old paragraph and
> approved the upgrade path with *«va bene che chi era già utente non riceva il tour»* — which is
> exactly what the **new** code does and the **opposite** of what the paragraph they were reading
> described. They said yes to the right behaviour on the strength of a description of a different
> one. The two agree, but by luck, not because the approval was informed.
>
> **So this is not a validated decision. It is an unvalidated decision that happens to be correct.**
> If it is ever revisited, revisit it on its merits — do not cite the 2026-09-21 approval as
> evidence that the behaviour was reviewed and endorsed, because what was endorsed was a sentence,
> not this behaviour.

**Why it was `pending` in the first place**, since the reasoning is worth keeping: I judged that
grandfathering *setup* (which existing users demonstrably already did) while still offering
*education* (which they never had) was the right split. The counter-argument — which is what
prevailed — is that pushing a tour at a user who has been running the app for months is an
interruption they did not ask for, and that the feature's audience is new signups. Both are
defensible. The one now in the target is the second.

`downgrade()` drops both tables only. There is no data preservation on downgrade.

---

## 4. Frontend

### 4.1 `/welcome` route and bootstrap gating

- `appBootstrap.load()` fetches settings / onboarding / global in parallel (`Promise.allSettled`),
  guarded by a sequence number + user ID + client-session generation, so a slow response from a
  previous account can never land on the new one.
- **Settings failure → `blocked`, always.**
- **Onboarding failure → `degraded` only if a cached Welcome row is non-pending**; otherwise
  `blocked`. In other words: if we have never successfully learned whether you need onboarding,
  we refuse to render the app rather than guess.
- `resolveDestination()` redirects to `/welcome?returnTo=<path>` while Welcome is due or replaying;
  once terminal, `/welcome` bounces back to `returnTo`.
- `(app)/+layout.svelte` renders `onboarding-redirecting` while the route has not settled, a bare
  `welcome-shell` on the welcome route, and marks the app shell `inert` during `intro_tour`.

### 4.2 Guide catalog and controller

- `onboardingGuideCatalog.ts` — 15 flows, step ID tuples, trigger/completion/navigation modes.
- `onboardingGuide.svelte.ts` (465 lines) — queueing, replay arming, activation generation,
  terminal-token cleanup. `maybeStartIntro` (~L99), `maybeStartContextual` (~L143).
- `onboarding.svelte.ts` (371 lines) — per-flow request tickets carrying a `loadSequence`, so a
  superseded load cannot resolve onto current state; `transitioningFlow` is owned by an exact ticket
  so a stale account's outcome cannot clear a newer transition.

### 4.3 Anchors — the fragile part

`guideAnchors.svelte.ts` (88 lines) is a plain registry keyed by string ID, populated by a
`use:guideAnchor` action. `get()` self-heals by dropping elements that are no longer `isConnected`.
A `revision` counter drives reactivity. The registry is cleared on client-session reset.

**Answering the question directly — what happens when an anchor is missing, hidden, off-screen, or moves:**

| Situation | Behaviour | Verdict |
|---|---|---|
| **Anchor never registers** (element doesn't exist) | `anchorRect = null` → `targetStable = false` → `guideState = 'waiting'` → the panel renders `busyLabel` instead of the step description. **The tour waits. Indefinitely.** | ⚠️ **It does not break and it does not skip — it hangs, politely.** The X is still live, so the user can always escape, but a user who waits will wait forever. **This is the single most important fragility in the feature.** |
| **Anchor element is removed while the step is live** | `isConnected` check drops it on next `get()` → same `waiting` state | Same as above |
| **Anchor is hidden or off-screen** | `scrollPolicy: 'nearest-if-hidden'` scrolls the nearest scrollable ancestor (explicit `data-guide-scroll-root`, else computed); a target entirely above the viewport gets a **header-safe correction** so the sticky header doesn't cover it | ✅ Handled, and E2E-covered for the broker header case |
| **Anchor moves** (transition, resize, scroll) | Geometry re-settles: `waiting → revalidating → stable`, requiring **two consecutive matching frames**; follows `transitionrun`/`transitionend`/`transitioncancel`, a `ResizeObserver`, and window + scroll-root scroll | ✅ Handled |
| **A modal opens over the step** | `suspended = modalDepth > step.allowedModalDepth`, where `modalDepth` reads `document.body.dataset.modalScrollLockCount`. Suspended coachmarks become `invisible` + `aria-hidden` — **they do not close**, they come back when the modal closes | ✅ Deliberate |
| **User navigates off the guide's host route** | `dismissHost({restartAtFirst: true})` then re-queue — the guide **restarts at step 1** next time | ⚠️ Deliberate but surprising: leaving a page mid-guide loses your place |

Cosmetic: the panel fades to subdued after 3,000 ms; hover/focus restores full opacity without
restarting the timer.

### 4.4 Deferred popups

`DeferredAppPopups.svelte` suppresses donation and update popups entirely while a guide is active
or `modalDepth > 0`. Donation takes precedence over update.

### 4.5 Route settlement

The layout will not render app content until the onboarding destination resolves. This is why a
slow/failing onboarding GET manifests as a spinner rather than a flash of the dashboard followed by
a yank to `/welcome`.

---

## 5. Simplifications and boundaries

### 5.1 i18n — **measured, not assumed**

`onboarding.*` keys: **EN 226 / IT 226 / FR 226 / ES 226**, and the four key *sets* are byte-identical.
Values identical to English (a proxy for "not actually translated"): **IT 0, FR 1, ES 0**.
The single FR case is `onboarding.settings.groups.transactions` = `"Transactions"`, which is the
correct French word — a true cognate, not a gap.

**So onboarding i18n is complete across all four locales.** (The repo-wide audit was 3167/3167 with
0 incomplete; the 226/226/226/226 figure above is the onboarding-specific slice, measured directly
from the catalogs, because a green repo total proves the *set* has no orphans, not that my namespace
is in it.)

### 5.2 Mobile vs desktop — **two different breakpoints, deliberately**

- `OnboardingCoachmark.svelte` uses `(max-width: 640px)` to switch panel layout.
- `OnboardingOverlayHost.svelte` uses `(max-width: 1023px)` to decide **which element to anchor to**:
  `intro.navigation` targets `nav.toggle.mobile` below 1024px and `nav.toggle.desktop` above.

Steps may declare `mobilePanelPlacement` to override `panelPlacement`. Scroll uses `behavior: 'auto'`
when `prefers-reduced-motion` is set.

**The 640/1023 split is intentional** (layout vs anchor identity) but it means there is a band
between 641px and 1023px where the coachmark uses desktop panel layout and mobile anchor targeting.
That band is covered by neither E2E viewport. **It is the most likely place for a visual oddity.**

### 5.3 Empty portfolio vs populated

- The intro tour anchors on nav/sidebar chrome, which exists regardless of data → **works on an
  empty portfolio**.
- Contextual guides anchor on page chrome (headers, filter bars, add buttons) rather than on rows →
  mostly data-independent.
- **`transaction_bulk_guide` and `import_guide` are the exceptions**: they follow real wizard
  milestones. They only appear when the user actually does an import/bulk operation, and
  `import_guide` explicitly performs **no automatic writes** — it watches the wizard, it does not
  drive it. With a conditional wizard step that never appears (e.g. no duplicates found), the
  corresponding guide step is never reached and the flow simply stays due.

### 5.4 Things that produce a plausible-but-wrong result instead of failing visibly

> **This is the most valuable list in the document.**

1. **A missing anchor makes the tour wait forever, showing a busy label.** It looks like loading.
   It is not loading. Nothing will ever arrive. (§4.3) — *highest severity*
2. **An armed replay silently disappears** when the tab closes or the user switches device, because
   the token is `sessionStorage`. The Settings UI gave positive confirmation ("armed at next
   trigger") that is no longer true. (§2.5)
3. **Welcome "Skip" silently accepts the admin's language.** A user who skips because they're in a
   hurry inherits a language they never chose. (§2.6)
4. **Welcome replay looks like a settings editor but writes nothing.** Change your language in a
   replayed Welcome and press Continue: the UI accepts it, nothing persists. (§2.7)
5. **Leaving a guide's host route restarts it at step 1** rather than resuming. The user sees "1 of 5"
   again and may reasonably think the guide reset itself by mistake. (§4.3)
6. **Frontend catalog and backend registry agree by convention only.** If a step ID is added to
   `onboardingGuideCatalog.ts` and not to `ONBOARDING_FLOW_STEPS`, the step-complete call returns an
   error at runtime; there is no build-time check binding them. (§5.5)
7. **A version bump re-triggers a flow for every user at once.** Correct by design, never exercised —
   all flows are at version 1.

### 5.5 Known structural simplification

There is **no shared source of truth** between `ONBOARDING_FLOW_STEPS` (Python) and
`ONBOARDING_GUIDE_CATALOG` (TypeScript). They are kept in sync by review, and the API tests assert
the backend side. A drift would be caught by the step-transition 422/409 path at runtime, not at
build time.

---

## 6. What is not done

| # | Item | Severity |
|---|---|---|
| 1 | **No timeout or visible failure for an unresolvable anchor.** A guide can wait indefinitely (§4.3). A "this step can't be shown — skip it?" escape after N seconds is the obvious fix and was not built. | **High** — this is the one I would fix first |
| 2 | **Replay tokens are session-scoped and this is not surfaced in the UI.** No "this will only apply in this tab" hint. | Medium |
| 3 | **No E2E coverage for 9 of the 15 flows** — all Broker modal/detail, all FX, all Asset guides (§8). | Medium |
| 4 | **No build-time contract check** between the TS catalog and the Python step registry (§5.5). | Medium |
| 5 | **Version-bump re-trigger path never exercised** end to end; all flows at version 1. | Medium |
| 6 | **641–1023px viewport band untested** (§5.2). | Low |
| 7 | **No admin/CLI reset.** Resetting a user to not-yet-onboarded requires SQL (§7.2). | Low, but it's what makes review hard |
| 8 | **No analytics/telemetry** on completion vs skip rates. Never requested; noting it because "did anyone finish the tour" is unanswerable today. | Low |
| 9 | **Intro tour is arguably 5 steps too long** (§2.2). Not a defect; a design opinion I'd like overruled or confirmed. | Design |

No known defects are open. The one Medium finding from the final read-only review — a
`transaction_create_guide` left queued after the Add Transaction form was closed or destroyed, able
to reopen later with no anchors present — was fixed via `releaseCreateGuideHost()` in
`TransactionFormModal.svelte` (on close and in `onDestroy`) and covered by 3 strict regressions.

---

## 7. How to review this by hand

### 7.1 The click path to onboarding from a fresh login

> **Do not start a server.** `D - Allocatore PAC` owns the review lane (6152 +
> `/tmp/librefolio-r2-d-review`) and it serves the whole merged target, so onboarding is already
> reachable there. Ask the coordinator to route you in.

1. Log in as a user whose `welcome` row is `pending` (see §7.2 for how to make one).
2. **You do not need to click anything** — the layout redirects you to `/welcome?returnTo=/dashboard`.
   `data-testid="welcome-form"`.
3. Fill or skip: `welcome-avatar-choose` / `welcome-language` / `welcome-currency`, then
   `welcome-continue` or `welcome-skip`.
4. You land on `/dashboard`. The **intro tour starts by itself** — 9 coachmarks, the app shell is
   `inert`, the X is `onboarding.actions.skipCurrentTour`.
5. After the tour, visit Transactions / Brokers / FX / Assets. Each first visit fires its
   contextual guide.
6. **Replay surface**: Settings → **Preferences** tab → scroll to
   `data-testid="onboarding-replay-section"`. Per-flow replay buttons plus
   `data-testid="onboarding-replay-all"`.

### 7.2 How to reset a user to not-yet-onboarded

**Option A — the honest full reset (SQL).** This is the only way to see the Welcome page and a true
first-login again. The service re-seeds every flow as `pending` lazily on the next `GET`, so
deleting is sufficient — you do not need to insert anything.

```sql
-- against the review lane DB: /tmp/librefolio-r2-d-review/sqlite/app.db
-- replace <USER_ID> with the target user's id
DELETE FROM user_onboarding_step_progress WHERE user_id = '<USER_ID>';
DELETE FROM user_onboarding_progress      WHERE user_id = '<USER_ID>';
```

Then **hard-reload the browser tab** (or open a new one). The next `GET /settings/onboarding`
re-creates all 15 flows as `pending`, and the layout redirects to `/welcome`.

> I did **not** run this. The DB at `/tmp/librefolio-r2-d-review/sqlite/app.db` belongs to D's
> review lane and I did not touch it. The statements above are written against migration `003`'s
> actual schema, not against a live inspection.

**Also clear stale replay tokens** if you have been experimenting — `sessionStorage`, keys matching
`lf_{userId}_onboarding_replay_*`. Closing the tab does this for you.

**Option B — partial, in-app, no SQL.** Settings → Preferences → Replay all. This re-shows the
guides but does **not** reset backend status, and replayed Welcome writes nothing (§2.7). Good for
looking at the visuals; useless for testing the real first-login path.

### 7.3 Test scenarios — ordered, each with an expected result

> Confidence flags are mine and honest. **⚠️ = I am least confident about this one.**

**Happy path**

| # | Do this | Correct result |
|---|---|---|
| H1 | Reset per §7.2, log in | Redirected to `/welcome` without clicking; no flash of the dashboard first |
| H2 | Pick a language ≠ default on `/welcome` | Page copy switches language **live**, before submitting |
| H3 | Set avatar + language + currency, press Continue | Lands on `/dashboard`; Settings → Preferences shows exactly those values; avatar visible in the header |
| H4 | Watch the intro tour to the end | 9 steps; the sidebar opens/closes as the tour moves; each coachmark is **anchored to the element it describes**, not floating; after the last step the shell stops being `inert` |
| H5 | Go to Transactions | `transactions_page_guide` starts by itself, 4 steps, X available |
| H6 | Finish it, then reload the page | The guide **does not** come back |

**Most likely to break**

| # | Do this | Correct result |
|---|---|---|
| B1 | During any coachmark, **resize the window** slowly | The coachmark tracks the element continuously; it must not detach, overlap the header, or sit off-screen |
| B2 | During the intro tour, **scroll** a long page | Same — tracking, and a target above the viewport gets scrolled clear of the sticky header |
| B3 | Start the **import guide**, then open a modal from inside the wizard | The coachmark **disappears while the modal is up and returns when it closes** — it must not close permanently ⚠️ |
| B4 | Start a contextual guide, then **navigate away** mid-guide and come back | The guide restarts **at step 1** (§4.3). This is intended; confirm you're happy with it ⚠️ |
| B5 | Run the import guide through a file that produces **no duplicates** | The duplicates step is skipped by the real wizard; the guide must follow, not stall on a step that will never appear ⚠️ |
| B6 | In `transaction_bulk_guide`, press **X** on step 2 | Only step 2 is skipped; steps 3–4 still appear later; the flow is still due (§2.4) |
| B7 | Open Add Transaction, start its guide, **close the modal mid-guide**, then reopen it later | The guide must not reappear orphaned with no anchors. *(This was a real bug, found in review and fixed — worth re-confirming by hand)* |
| B8 | Arm a replay in Settings, **close the tab**, reopen the app | The replay is **gone**. This is current behaviour, not a bug — decide whether it is acceptable (§5.4 item 2) ⚠️ |

**Edges**

| # | Do this | Correct result |
|---|---|---|
| E1 | **Already-onboarded path**: log in as a user with all flows terminal | Straight to `/dashboard`, no redirect, no tour, no coachmark — **different code path from H1, test it separately** |
| E2 | **Existing-user upgrade**: a user created before migration 003 | `welcome` is already complete (no welcome page) **and no tour or guide appears either** — all 14 guides are seeded `skipped` (§3.3). Correct result is that nothing is offered at all. If you see a tour, the migration did not run as expected |
| E3 | Switch account (log out → log in as another user) mid-tour | The new account's state applies immediately; no coachmark from the previous account survives |
| E4 | Kill the network, then load the app for a user who has never loaded onboarding | The app **blocks** with an error rather than rendering the dashboard or guessing (§4.1) ⚠️ |
| E5 | Kill the network for a user whose Welcome is known-complete (cached) | The app renders **degraded** — usable, no guides |
| E6 | Resize to a **mobile** viewport and run the intro tour | `intro.navigation` anchors to the **mobile nav toggle**, not the desktop sidebar; panels use mobile placement |
| E7 | Resize to **~800px wide** and run a guide | ⚠️ **Lowest confidence of anything here** — this band uses desktop panel layout with mobile anchor targeting and is covered by no automated test (§5.2) |
| E8 | Trigger the intro tour while a **donation or update popup** would be due | The popup does not appear until the guide ends (§4.4) |
| E9 | Switch language in Settings while a guide is active | Coachmark copy re-translates in place, without restarting the guide |
| E10 | Enable `prefers-reduced-motion` and run a guide | Scrolling is instant rather than smooth; no animation-driven jitter |

---

## 8. Automated coverage — what exists, what it asserts, what it misses

**Measured file by file, not reported as a suite total.**

### Frontend unit / component (Vitest)

| File | `it`/`test` blocks | What it actually asserts |
|---|---|---|
| `lib/stores/app/onboarding.test.ts` | **107** | Request tickets, load supersession, ticket-owned `transitioningFlow`, replay storage (arm/clear/version-pruning), stale-account isolation, 409 handling |
| `lib/components/onboarding/OnboardingCoachmark.test.ts` | **48** | Geometry settlement, two-frame stability, scroll-root detection, header-safe correction, suspension, fade timer, pointer/pulse |
| `lib/components/onboarding/WelcomePage.test.ts` | **17** | Page states, outcome rendering, bootstrap-loading state |
| `lib/components/onboarding/OnboardingReplaySection.test.ts` | **16** | Per-flow replay/cancel, armed state, busy/error, group counts |
| `lib/features/onboarding/guideAnchors.test.ts` | **16** | Registry add/remove, `isConnected` self-heal, revision bumps, session reset |
| `lib/components/onboarding/WelcomeForm.test.ts` | **14** | Field binding, skip vs submit, avatar set/clear |
| `lib/components/onboarding/OnboardingIntroScene.test.ts` | **12** | Centred scene, no-anchor path |
| `lib/features/onboarding/onboardingTourSurfaces.test.ts` | **6** | Surface/step registry consistency |
| `lib/components/transactions/modals/TransactionFormModal.test.ts` | 3 (onboarding-relevant) | Close/destroy releases the queued create guide |

**Total onboarding-specific frontend unit blocks: 236+**, inside a `component-unit` suite that runs
**1,811 passed / 68 files** (also verified at `--workers 4`), and a core-unit suite at
**2,085 passed / 83 files**.

### Backend (pytest)

- `test_scripts/test_api/test_settings_api.py` — 39 tests, **13** onboarding/welcome/step-named:
  the flow and step transition ladders, `welcome_settings` 422 guard, 409 version mismatch, step DTO
  extra-forbid.
- `test_scripts/test_services/test_settings_service.py` — 23 tests, **5** onboarding-named:
  idempotent ensure, aggregate rollup, cascade, welcome rollback.
- Schema is additionally covered by `db validate` (17) and `db referential-integrity` (15).

### E2E (Playwright) — `frontend/e2e/onboarding-tour.spec.ts`

**5 test blocks × desktop + mobile = 10 runs.** They are:

1. Global Asset Abs/% propagates to every rendered card
2. Core order and Transactions overview preserve geometry
3. Broker views preserve scroll; a header-obscured Add receives only its precise clearance scroll
4. Import preempts real Bulk milestones and resumes overview → validation → selection → save
5. Bulk selection stays due across host cleanup, then X skips only that current step

Plus `auth.spec.ts` (24) covering the blocking-bootstrap contract, and `tx-import-flow` (10),
`tx-asset-identity` (9), `asset-list` (26) exercising the surfaces the guides attach to.

### **The gaps — named, not hidden behind a green total**

Measured by step-ID family references inside the E2E spec:

| Flow family | E2E step references | Covered in browser? |
|---|---|---|
| `intro.*` | 12 | ✅ |
| `transaction.bulk.*` | 19 | ✅ |
| `transaction.create.*` | 4 | ✅ |
| `broker.page.*` | 4 | ✅ |
| `import.*` | 3 | ✅ |
| `transactions.page.*` | 2 | ✅ |
| `broker.overview` / `broker.plugin` / `broker.icon` | **0** | ❌ |
| `broker.detail.*` | **0** | ❌ |
| `fx.page.*`, `fx.currencies`, `fx.providers`, `fx.detail.*` | **0** | ❌ |
| `asset.page.*`, `asset.search`, `asset.identity`, `asset.provider`, `asset.detail.*` | **0** | ❌ |

**9 of the 15 flows have no browser-level coverage at all.** They are referenced in unit tests
(12–16 references each for the detail guides, via the catalog/surface registries) so their step
tuples and presentation maps are asserted — **but no test has ever resolved their anchors against a
real rendered page.** Given §4.3, an anchor that never registers is exactly the failure mode that
unit tests cannot see and that manifests as an indefinite wait.

**Other named gaps:**

- No test for the 641–1023px viewport band (§5.2).
- No test for a version bump re-triggering a terminal flow.
- No test for the multi-device replay case — by construction, `sessionStorage` cannot be tested
  across contexts in the current harness.
- No test asserting the TS catalog and the Python registry agree.

---

## 9. Files

**Backend**
- `backend/app/services/onboarding_service.py`
- `backend/app/api/v1/settings.py` (onboarding endpoints, ~L109–285)
- `backend/alembic/versions/003_user_onboarding_progress.py`
- `backend/app/db/models.py`, `backend/app/db/base.py`, `backend/app/db/__init__.py`
  (`UserOnboardingProgress` / step-progress models)
- `backend/app/schemas/settings.py` (onboarding DTOs)

**Frontend**
- `frontend/src/routes/(app)/welcome/+page.svelte`
- `frontend/src/routes/(app)/+layout.svelte` (gating, welcome shell, inert shell, overlay mount)
- `frontend/src/lib/features/onboarding/appBootstrap.svelte.ts`
- `frontend/src/lib/features/onboarding/onboardingGuide.svelte.ts`
- `frontend/src/lib/features/onboarding/onboardingGuideCatalog.ts`
- `frontend/src/lib/features/onboarding/guideAnchors.svelte.ts`
- `frontend/src/lib/features/onboarding/onboardingTourSurfaces.svelte.ts`
- `frontend/src/lib/features/onboarding/onboardingApi.ts`, `welcome.ts`
- `frontend/src/lib/stores/app/onboarding.svelte.ts`
- `frontend/src/lib/components/onboarding/OnboardingOverlayHost.svelte`
- `frontend/src/lib/components/onboarding/OnboardingCoachmark.svelte`
- `frontend/src/lib/components/onboarding/OnboardingIntroScene.svelte`
- `frontend/src/lib/components/onboarding/OnboardingReplaySection.svelte`
- `frontend/src/lib/components/onboarding/WelcomePage.svelte`, `WelcomeForm.svelte`
- `frontend/src/lib/components/onboarding/DeferredAppPopups.svelte`
- `frontend/src/lib/components/settings/tabs/PreferencesTab.svelte` (L352 — replay mount)
- `frontend/src/lib/components/transactions/modals/TransactionFormModal.svelte` (guide release)
- `frontend/src/lib/i18n/{en,it,fr,es}.json` (`onboarding.*`, 226 keys each)

**Plans** — `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/plan-phase00Onboarding*.prompt.md`
(7 files: base + Rounds 1–6, each carrying its own detours and evidence).

---

*Written by workstream J at HEAD `580bd504f`. Not committed. No server started, no port bound,
no Git history operation performed.*
