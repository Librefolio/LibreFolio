"""
Users Admin API — release 1.3, workstream A, lot A5a (plan phase01Accounts, A5.1, contract point 5, the administrator's part).

An administrator manages the accounts from the API. Every route below sits behind ``require_admin`` in
``api/v1/users.py``, its static routes declared before ``{user_id}``:

1. ``GET /users/invites`` → ``{items: [{id, grants_admin, email, created_at, expires_at, created_by_user_id}], usage:
   {used, max_users, billing_url}}``: the live invitations only (neither consumed, nor revoked, nor expired), whoever
   issued them. ``used`` counts the active accounts plus the live invitations; ``max_users`` is ``LIBREFOLIO_MAX_USERS``
   (null without a limit, 0 when the variable is not valid: a bad limit closes); ``billing_url`` is
   ``LIBREFOLIO_BILLING_URL``, null when unset.
2. ``POST /users/invites`` ``{grants_admin=false, email?}`` → 201 ``{invite, token, path, url}``: ``invite`` as listed,
   ``token`` the plaintext shown once, ``path`` its page with the token in the URL fragment (``/invite#token=…``: a
   browser never sends a fragment, so the token stays out of the access log and of proxy logs), ``url`` the public URL
   plus the path, null
   without ``LIBREFOLIO_PUBLIC_URL``. An invitation lives 7 days and only its hash is stored. 409 ``USER_LIMIT_REACHED``
   with ``limit``, ``used`` and ``billing_url`` when ``used >= max_users`` (the caller is an administrator: the counts and
   the subscription link are for them); 409 ``REGISTRATION_DISABLED`` while registration is ``disabled``, by the row or
   by ``LIBREFOLIO_REGISTRATION``. A refusal issues nothing.
3. ``DELETE /users/invites/{invite_id}`` → 204, and the invitation opens nothing any more; 404 when the id is not a live
   invitation: revoked, consumed, expired, never issued, or a token of another purpose (which stays as it was).
4. ``GET /users`` → ``{items: [{id, username, email, is_active, is_superuser, created_at, protected}], usage}``: every
   account, active or not; no hash, no secret. ``protected`` is added by lot A6a (point 12).
5. ``PATCH /users/{user_id}`` ``{is_active?, is_superuser?}`` → 200 with the account as ``GET /users`` lists it; 404; 409
   ``LAST_ADMIN`` to deactivate or demote the last active administrator; 409 ``USER_LIMIT_REACHED`` (with the counts) to
   reactivate an account over the limit, which blocks nothing else. Deactivation and demotion end the account's sessions
   (A4b); activation and promotion end none, and a reactivation does not bring the old sessions back.
6. ``POST /users/{user_id}/password-reset-link`` → 201 ``{token, path, url, expires_at}``, ``path`` being
   ``/reset-password#token=…``, 30 minutes, after revoking the account's other live reset links (another account's
   stay); the link works once with ``POST /auth/password-reset``. 404.
7. ``POST /users/{user_id}/sessions/revoke`` → 204: every session of that account ends, no other one; 404.
8. ``POST /users/{user_id}/onboarding/reset`` ``{flow?}`` → 204: every flow, steps included, or only the one named, back
   to ``pending``, as the account itself reads it from ``GET /settings/onboarding`` (21-5); an unknown flow is a 422 that
   resets nothing; 404.
9. Every action writes a structured log event, and no log carries a token. The plaintext (hence neither the path nor the
   URL) appears in no structlog event and no stdlib record, whatever the logger. Its hash appears in no structlog event
   and in no record of the application's loggers. The third-party loggers that ``configure_logging`` silences to WARNING
   (``aiosqlite``, ``sqlalchemy.engine``, …) are excluded: they log every statement with its parameters, the stored
   hash included, so a running server never emits those records.

Lot A6a (plan phase01Accounts §A6.1) adds:

10. ``GET /users/{user_id}/deletion-preview`` → 200 ``{user_id, username, brokers_deleted: [{id, name, transactions}],
    brokers_left: [{id, name, role}], transfers_unpaired}``, both lists by broker id, ``role`` the UserRole value: what
    deleting the account would take, by the rule ``delete_user`` applies (``BrokerService.leave_broker``); it writes
    nothing. 404 for an account that does not exist.
11. ``DELETE /users/{user_id}`` → 204 with no body: the account is gone, its sessions answer 401, its brokers follow the
    preview — those of ``brokers_deleted`` gone with their transactions, those of ``brokers_left`` still there without
    its access, the transfer half it leaves alone unlinked. 404 for an account that does not exist; 409
    ``SELF_DELETION`` for the caller's own id (one's own account is deleted from the profile); 409 ``DEMOTE_FIRST`` for
    an administrator, active or not; 409 ``ACCOUNT_PROTECTED`` from the hook; a technical failure → 500 «nothing was
    deleted», and nothing is. One structured event, «Account deleted by an administrator», with ``user_id``,
    ``username``, ``admin_id``, ``brokers_deleted`` and ``files_removed``; no session token and no password in any log.
12. The hook of lot A7, ``user_service.account_protection(user) -> Optional[str]``, a plain function: ``PATCH`` refuses
    to deactivate or demote an account it gives a reason for, ``DELETE`` refuses to delete it, both 409
    ``ACCOUNT_PROTECTED``, changing nothing; ``GET /users`` and ``PATCH`` answer ``protected: bool`` (a reason exists).
    Until lot A5-1 it protects nobody; since, on a managed instance the account of ``LIBREFOLIO_ADMIN_EMAIL`` is the one
    it protects (``TestPayingAdministratorProtection``, in-process). The lane is not managed: every account of it is
    ``protected: false``.

Lot A7b (plan phase01Accounts, «A7b — Analisi e contratto», contract C5, its backend part) adds:

13. ``pending_setup: bool`` on every account ``GET /users`` lists and ``PATCH /users/{user_id}`` answers, false by
    default in ``AdminUserRead``. True exactly for an account waiting for its F02 setup, by the notion of
    ``registration_service.pending_admin_filter()`` — the one ``user_usage`` counts (A7a, C4) and ``pending_admin``
    reads (BOOT-016, ``test_admin_bootstrap.py``): inactive, with at least one ``admin_setup`` token and none of them
    consumed; those tokens live, expired or revoked alike, the account an administrator or not. False for every other
    account: an active one, its setup link live or spent; an inactive one whose setup link was spent (deactivated after
    its setup); an inactive one without a setup link, with no token or with a token of another purpose; one waiting for
    its email verification, for which ``holds_place`` stays workstream E's own flag — false, in turn, for the pending
    administrator. The ``PATCH`` answer carries the flag of the account as it returns it, the one ``GET /users`` lists
    right after. Nothing else changes in either answer: an account is exactly its nine fields, ``usage`` counts as before.
14. ``PATCH /users/{user_id}`` refuses to activate that account (decision of the coordinator, 16/10): a body with
    ``is_active: true`` — alone, or with ``is_superuser`` either way — is 409 ``PENDING_SETUP``, ``detail: {error_code,
    message}``, and changes nothing, all or nothing: its password is a secret nobody knows, and the way in is a setup
    link. Its link live or expired, alike. Every other inactive account is activated as before, and a ``PATCH`` that
    leaves the pending administrator waiting still answers 200.

Lot A7b-2 (plan phase01Accounts, «A7b-2 — Analisi e contratto», C1 and C2: A-32; decision N60) adds:

15. An account set up another way than its setup link waits for it no more. At every activation (``PATCH``, through
    ``user_service.update_user_status``; ``./dev.py user activate``) and at every password set (``./dev.py user
    reset``; a reset link — which ``POST /users/{user_id}/password-reset-link`` issues for the pending administrator
    too —; ``POST /auth/change-password``) its unconsumed ``admin_setup`` links are retired, revoked and consumed in the
    same transaction (``token_service.retire_tokens``); and so are they when ``POST /auth/setup`` refuses the link of
    an account already active (night decision 6, completed). Its old link then inspects ``revoked``, ``POST
    /auth/setup`` with it is 400 ``TOKEN_INVALID`` and changes nothing, and the account, inactive again, is listed
    ``pending_setup: false`` and reactivated by ``PATCH {is_active: true}`` (200, not point 14's 409). What leaves it
    waiting — nothing done, a reset link issued and not spent, a refused demotion (point 16) — keeps both its link and
    point 14's refusal.

Lot A-42 + A-43 (the setup link's lifecycle; contract approved by the coordinator, 17/10) adds:

16. ``PATCH /users/{user_id}`` refuses to demote the account waiting for its setup: a body with ``is_superuser: false`` —
    alone, or with ``is_active: false`` — is 409 with point 14's detail exactly, ``{error_code: PENDING_SETUP,
    message}``, the same message as the refused activation, and changes nothing, all or nothing. Any other administrator
    is demoted as before. ``{is_active: false}`` on that account, already inactive, still answers 200 with its row
    (``pending_setup: true``), and now revokes its live setup links: its link inspects ``revoked``, ``POST /auth/setup``
    with it is 400 ``TOKEN_INVALID``, and the account still waits — a new link of ``./dev.py user setup-link`` sets it
    up. Unless the hook of lot A7 protects it (coordinator, 17/10, after the review): then that cancellation is refused
    as a deactivation is (point 12), 409 ``ACCOUNT_PROTECTED`` with the hook's ``reason``, and changes nothing — its
    link live, the account still waiting, the link still setting it up; ``./dev.py user deactivate`` stays above the
    protection, as for every protection. On an account that does not wait — an active one, or an inactive one set up
    before — the deactivation (the ``PATCH``, ``./dev.py user deactivate``) retires its never-consumed setup links:
    inspected ``revoked``, the account listed ``pending_setup: false``, reactivated by ``PATCH {is_active: true}``, and
    the link sets nothing.
17. ``DELETE /users/{user_id}`` deletes the account waiting for its setup directly (coordinator, 17/10 11:45: its
    demotion refused, there is nothing to demote first): 204 with no body, not 409 ``DEMOTE_FIRST``, whichever state
    its setup links are in — live, expired, revoked by a cancellation, or re-armed by ``./dev.py user setup-link``. The
    account and its tokens go as with any deletion (``user_service.delete_account``: the row, and with it, by the
    schema's cascade, its ``account_tokens``), and nothing else changes: its links then inspect ``unknown`` and set up
    nothing, its place is free, and nobody waits any more. Any other administrator — active or not, holding a stray
    setup link or set up before — is still 409 ``DEMOTE_FIRST``, nothing deleted; and a protected account is still 409
    ``ACCOUNT_PROTECTED`` before any other answer (point 12), the waiting administrator included.

Lot A-51 (the setup completed while the Users tab acts; cure approved by the coordinator, 17/10) adds:

18. ``PATCH /users/{user_id}`` takes an optional ``cancel_setup: bool``, false by default, allowed only beside
    ``is_active: false``: with ``is_active`` absent, null or true it is a 422 that changes nothing. ``{is_active: false,
    cancel_setup: true}`` is point 16's cancellation and nothing else: on the account still waiting for its setup, 200
    with its row (``pending_setup: true``), its setup link revoked, the account still waiting; on an account that no
    longer waits — set up since the tab listed it, or in the very window between the route's reads and its first write
    — 409 ``{error_code: SETUP_COMPLETED, message}``, and nothing changes: the administrator active, an administrator,
    its sessions alive. A plain ``{is_active: false}`` keeps its meaning, a deactivation, decided on what the database
    holds under SQLite's write lock: in that window it deactivates the administrator just set up — the caller, another
    active administrator, keeps it from being the last —, its sessions end, and its answer is what the database holds.
    ``DELETE /users/{user_id}`` reads «waiting» again under the same lock before point 17's direct deletion: in that
    window, 409 ``DEMOTE_FIRST``, nothing deleted.

Lot A-54 + A-55 + A-56 (decide under the write lock; reviewer E, through the coordinator, 17/10) adds:

19. ``PATCH /users/{user_id}``, ``DELETE /users/{user_id}``, ``POST /users/invites`` and the three routes that act on an
    account — ``POST /users/{user_id}/password-reset-link``, ``/sessions/revoke`` and ``/onboarding/reset`` — decide on
    what the database holds under SQLite's write lock, not on the reads before it: between those reads and the first
    write nothing holds the rows (pysqlite defers BEGIN to the first write), and another administrator may act there. An
    account deleted in that window: the ``PATCH`` — whatever it asks —, the ``DELETE`` — the pending administrator's as a
    plain account's — and the three routes answer ``_user_or_404``'s 404 word for word, ``{"detail": "User not
    found"}``, and change nothing — no reset link issued, no onboarding row created or changed (A-54). A plain account
    promoted in that window is an administrator's deletion: 409 ``DEMOTE_FIRST``, nothing deleted (A-55). The last place
    taken in that window — another account reactivated, an invitation created —: the reactivation and the invitation are
    point 5's and point 2's 409 ``USER_LIMIT_REACHED``, their counts the database's (``used`` the limit), nothing
    written, the instance at its limit and not one over it (A-56). With nobody acting in the window, each request answers
    as before.

Lot N69-4 (N69 point 4, decision D8 (a): each account's avatar in the Users tab) adds:

20. ``avatar_url`` on every account ``GET /users`` lists and ``PATCH /users/{user_id}`` answers: the account's avatar
    from its user settings (``UserSettings.avatar_url``: an image uploaded to the app, ``/api/v1/uploads/file/<id>``, or
    an address, 500 characters at most), as it is stored; null when it has none — no settings row, or a row without an
    avatar. Each account carries its own, whoever calls and whatever the ids of the settings rows. The ``PATCH`` answer
    carries it as the list does: the answer replaces the account's row in the Users tab. Nothing else changes in either
    answer: an account is exactly its ten fields, A7b's nine and ``avatar_url``; ``usage`` counts as before.

Lot E-7 (the Users tab tells the account waiting for its email verification from a deactivated one; the developer's
decision of 21/10/2026, Q1 yes) adds:

21. ``pending_verification: bool`` on every account ``GET /users`` lists and ``PATCH /users/{user_id}`` answers, false by
    default in ``AdminUserRead``. True exactly when the account is inactive and holds at least one token of purpose
    ``email_verification`` neither consumed nor revoked — that link live or already expired: the badge stays once the link
    expired —, the criterion of ``email_verification.awaiting_verification``, which the sign-in's 403 EMAIL_NOT_VERIFIED
    reads. ``holds_place`` stays its own flag, whether the place is still held: true only with a live link, so an account
    whose link expired is ``pending_verification`` true and ``holds_place`` false. False for every other account: an
    active one — a stray unspent verification token changes nothing, an active account never waits —; an inactive one
    with no token, with a token of another purpose (a reset link; a setup link: the initial administrator waiting for its
    setup is ``pending_setup`` true and ``pending_verification`` false), or whose verification links were all revoked —
    what an administrator's deactivation of a waiting account leaves, an ordinary deactivated account — or consumed. It
    is decided account by account: another account's link counts for nothing. A «send the link again» — a revoked link,
    then a live one — leaves the account waiting. The ``PATCH`` answer carries the flag of the account as it returns it,
    the one ``GET /users`` lists right after: a waiting account with a live link, promoted, stays inactive and waiting
    (``pending_verification`` and ``holds_place`` true); ``{is_active: false}`` on it ends the wait, its links revoked, and
    the answer says false and false; an account whose link expired, reactivated on an instance with a free place, is
    active and not pending. Nothing else changes in either answer: an account is exactly its eleven fields, A7b's nine,
    ``avatar_url`` and ``pending_verification``; ``usage`` counts as before.

Coded refusals are read from ``detail.error_code``, the shape ``POST /auth/login`` gives ``ACCOUNT_DISABLED`` and
``test_registration_api.py`` reads; the administrator's ``USER_LIMIT_REACHED`` carries ``limit``, ``used`` and
``billing_url`` in the same ``detail``.

Where each case runs, and why. The lane is shared: its registration mode is one row on which every unit's
registrations depend, the ``LIBREFOLIO_*`` variables are read by the lane's server (another process), and «the last
active administrator» depends on every account of the lane's database. So:

- **on the lane's server** run only the cases that hold whatever the neighbours do. Each test registers its own accounts
  (its administrator promoted through ``user_service``, never a shared E2E user), acts only on them and on the tokens
  they hold or issue, finds every row by id, and never counts the lane: ``used`` is only bounded below by the test's own
  active accounts. Deactivating or demoting one of its accounts is deterministic there, because the caller is an active
  administrator who is never the target. The lane must be ``open``, as every unit that registers its users needs it;
  nothing here writes a setting. Teardown deletes the test's tokens (by id, issuer, consumer and marker e-mail), then its
  accounts, after a red too;
- **in-process**, on a private SQLite file under ``tmp_path``, run the cases that need a mode, a limit, a public or
  billing URL, «the last administrator», an expired token or exact counts: the real routers of auth, users and settings,
  mounted as ``api/v1/router.py`` mounts them, in an app of this test whose ``get_session_generator`` opens sessions on
  that file. The variables are set with ``monkeypatch`` in this process only. Two assumptions follow: the endpoints take
  their session from ``get_session_generator``, as every handler does, and the accessors of ``config/accounts.py`` read
  the environment at each call.

A6a's cases follow the same split. On the lane: the deletion and its preview on accounts and brokers the case writes
(brokers and transactions straight into the lane's database, recorded once committed and deleted at teardown by id),
the refusals that hold whatever the neighbours do (``SELF_DELETION``, ``DEMOTE_FIRST``), and «nobody is protected
today». In-process: the hook (``user_service.account_protection``, replaced with ``monkeypatch``), the log, the technical
failure. Their private database is not built by ``create_all`` but taken to head by the real migrations — in a child
process, once for the module, then copied per test —: the models do not declare the ``ON DELETE CASCADE`` that
``broker_user_access`` has in ``001_initial``, and a deletion relies on it. The BRIM report directory moves under
``tmp_path`` there, because private broker ids start at 1 like the lane's, and ``delete_files_for_brokers`` is replaced
by a spy. Assumed: the routes reach the hook as ``user_service.account_protection`` and the report cleanup as
``brim_provider.delete_files_for_brokers`` or a name ``user_service`` imported, the two names the spy replaces.

A7b's cases run in-process only, on the private instance of ``create_all``. A pending administrator is an inactive
superuser that ``pending_admin``, ``issue_setup_link`` and ``user_usage`` read: in the lane's database every concurrent
unit would see it, and a run killed mid-test would leave it behind (the reason ``test_admin_setup_api.py`` gives). There
the bootstrap itself makes it — ``run_admin_bootstrap`` on the instance still empty, the configuration handed to the
service with a token the test holds, so that ``POST /auth/setup`` can spend it; run the link's lifetime and a minute
ago when the case wants that link expired —, and every other state of a setup link is a row and tokens of the token
service, an expired link issued the same way, never waited for. Its cleanup is the private file's. On the lane, the
field is read by UADM-003, UADM-007 and UADM-008: false on every account they own. A7b-2's cases run there too, for the
same reason; ``./dev.py user activate`` and ``./dev.py user reset`` are the calls the commands make
(``user_service.set_user_active``, ``user_service.reset_password``), on the private file. So are A-42/A-43's: ``./dev.py
user deactivate`` is ``user_service.set_user_active(…, False)`` and ``./dev.py user setup-link`` is
``bootstrap_admin_service.issue_setup_link``, committed; what the commands themselves answer and print is pinned in
``test_admin_setup_api.py`` (SETUP-016, SETUP-017) and ``test_admin_bootstrap.py`` (A42-002, A43-004). The deletion of
the pending administrator (UADM-076 to UADM-078) runs on the migrated schema instead (``private_head``), as A6a's
deletions do: a deletion relies on the production schema's cascades.

The unit is therefore write-scoped (the ``api`` category's default), with no ``exclusive_because``. bcrypt runs at its
lowest cost in this process (``auth_service.BCRYPT_ROUNDS = 4``, as in ``test_registration_api.py``); the lane's server
keeps its own.

Red until A5a: the routes do not exist. Red until A6a: the two routes UADM-001 now also covers, UADM-040 to UADM-043,
UADM-050 to UADM-054, and the ``protected`` field UADM-003, UADM-007, UADM-008 and UADM-028 now expect on every account.
Red until A7b: UADM-060 to UADM-065, on the missing ``pending_setup`` and the missing refusal; and UADM-003, UADM-007,
UADM-008 and UADM-028 again, whose accounts must now be exactly nine fields. UADM-066 and UADM-067 are the guards of
UADM-065, green today: what the refusal must not reach.

Red until A7b-2: UADM-068, UADM-070 and UADM-071 — nothing retires a setup link today: the old link takes the account
over (``POST /auth/setup`` answers 200), and an account set up another way waits again once deactivated
(``pending_setup`` true, the reactivation 409) —. UADM-069 is their guard, green today: what must retire nothing.

Red until A-42/A-43 (label ``# red until A-42/A-43``): UADM-072 — the demotion of the pending administrator answers 200
today —, UADM-074 and UADM-075 — a deactivation moves no setup link today —; and, changed by construction, UADM-062 (its
demotion now 409; its deactivation now revokes the link), UADM-067 (its demotion now 409; its deactivation still 200,
the guard it was) and UADM-069 (root's demotion now refused at its first step, the link still working; its
``{is_active: false}`` variant left it for UADM-074, the link revoked). UADM-073 is the guard of UADM-072, green today:
any other administrator is demoted as before. UADM-076 — the deletion of the pending administrator, 409
``DEMOTE_FIRST`` today — is red too (added 17/10, 11:45); UADM-077 and UADM-078 are its guards, green today: any other
administrator must still be demoted first, and the hook of lot A7 still answers before anything else. UADM-079 — the
cancellation of the setup link of a pending administrator the hook protects, 200 today and its link revoked: the route
asks the hook about an active account's deactivation only — is red too (added 17/10, after the review); its positive
control is UADM-074 (``patch-by-root``), the same ``PATCH`` on the pending administrator nobody protects.

Red until A-51 (label ``# red until A-51``; point 18): A51-001 to A51-003 — ``cancel_setup`` is no field today, 422 —,
A51-005 — in the window the plain ``{is_active: false}`` answers 200 with the account inactive, as the route loaded it
before the setup, while the database holds it active: a stale answer, nothing deactivated — and A51-006 — in the window
the ``DELETE`` deletes the administrator just set up, 204. A51-004 is their guard, green today (no such field) and after
(the validation): ``cancel_setup`` without ``is_active: false`` is refused whole. They run in-process, as A-43's; the
deletion on ``private_head``, as UADM-076. The window is played without threads. For the ``PATCH`` (A51-002, A51-005),
``_setup_lands_after_the_first_read``: the route's first ``registration_service.is_pending_admin`` reads the account
still waiting, then the setup completes on another connection — ``complete_admin_setup``, what ``POST /auth/setup``
runs, committed — before the route goes on; every later reading, the service's included, reads afresh. For the
``DELETE`` (A51-006), which since A-55 reads «waiting» under the lock only, the window of the UADM-LOCK cases
(``_window``): the route has loaded the account still waiting, and the setup — ``POST /auth/setup``, served on the
instance's own engine — lands right before the route's first write. The cancellation and the deletion of an
administrator still waiting keep their guards, unchanged: UADM-062 and UADM-074 (``{is_active: false}``), UADM-076
(``DELETE``).

Red until A-54/A-55/A-56 (labels ``# red until A-54``, ``# red until A-55``, ``# red until A-56``; point 19):
UADM-LOCK-01 — a ``PATCH`` on an account deleted in its window: today ``update_user_status`` takes the lock, then
``session.refresh`` raises ``InvalidRequestError`` on the row gone, a 500 whose exception reaches the call in-process —,
UADM-LOCK-02 — a ``DELETE`` of an account deleted in its window: that exception for the pending administrator, 204 for a
plain account although its own ``DELETE`` matched no row —, UADM-LOCK-03 — a ``DELETE`` of a plain account promoted in
its window: 204, the administrator just promoted deleted with its broker —, UADM-LOCK-04 and UADM-LOCK-05 — a
reactivation and an invitation whose last place is taken in their window: 200 and 201, the instance one over its limit —,
and UADM-LOCK-10 to UADM-LOCK-12 — a reset link, a sessions revoke and an onboarding reset of an account deleted in their
window (A-54, added by the coordinator, 17/10 20:41): today ``IntegrityError`` (the link's INSERT, on the foreign key)
and ``NoResultFound`` (``end_sessions``' UPDATE … RETURNING), 500s whose exceptions reach the call, and 204 for the
onboarding reset of an account that no longer exists. UADM-LOCK-06 to UADM-LOCK-09 and UADM-LOCK-13 to UADM-LOCK-15 are
their guards, green today and after: the same requests on the same scenes, served the same way, nobody acting in the
window — or what the rival does done before the request. «Nothing changed» reads every row of users and account_tokens,
every account's settings and onboarding rows, every account, broker, grant and transaction (``_lock_state``). They run
in-process on the migrated schema (``private_head``, as A51-006: a deletion relies on its cascades), with fresh login
limiters. The window is A-42's (``_rival_before_the_first_write``, ``test_admin_bootstrap.py``), played without threads
and without assuming which reads the route makes: the request under test is served on an engine of its own on the
private file (``_route_of``), and the rival — another administrator's request (peer's), served on the instance's own
engine as another worker serves it, committed by its route — runs right before that engine's first write statement
(``_window``). The listener is armed for that request alone, so neither the setup nor the rival can be «the first
write»; each race's barrier says where the rival landed — right before the request's first write (the statement, in the
verdict), after the request had read the account it decides on (for an invitation, after its authentication read the
caller) — and that the rival's own request was served. A cure reads again under the lock: its first write,
``begin_writes``, comes before its decisions, so the rival lands before the lock and the decisions see it.

Red until N69-4 (label ``# red until N69-4``; point 20): UADM-AV-01 to UADM-AV-04 — ``avatar_url`` is no field of
``AdminUserRead`` today, and no item carries it —; and, by construction, every case that reads an account through
``_user_item_violations`` or ``USER_ITEM_KEYS`` — UADM-003, 007, 008, 028, 052, 060 to 064, 068 to 071, 073 to 075, 079,
A51-001, A51-003 and UADM-LOCK-06 —: an account is now exactly ten fields, its ``avatar_url`` null for every account of
theirs, none of which has an avatar (their docstrings, older than point 20, still say nine). Left alone, those cases
would turn red the day ``avatar_url`` lands. UADM-AV-01 and UADM-AV-02 run on the lane: an account of the case sets its
avatar as it does from its profile, ``PUT /settings/user`` with its own session — the only setting written there, a row
of the case's own account, which goes with it at teardown by the schema's cascade. That route takes any address of 500
characters at most and checks no file, so an uploaded avatar is an address of that shape, never a file. UADM-AV-03 runs
in-process, on the private instance of ``create_all``: every account and settings row there is the test's, so the whole
list is asserted, and each settings row is written with the id of another account. UADM-AV-04 reads the schema.

Red until E-7 (label ``# red until E-7``; point 21): UADM-VER-01 to UADM-VER-05 — ``pending_verification`` is no field of
``AdminUserRead`` today, and no item carries it —; and, by construction, every case that reads an account through
``_user_item_violations`` or ``USER_ITEM_KEYS`` — UADM-003, 007, 008, 028, 052, 060 to 064, 068 to 071, 073 to 075, 079,
A51-001, A51-003, UADM-LOCK-06 and UADM-AV-01 to UADM-AV-04 —: an account is now exactly eleven fields, its
``pending_verification`` false for every account of theirs, none of which waits for a verification link (their
docstrings, older than point 21, still say nine or ten). Left alone, those cases would turn red the day
``pending_verification`` lands. The cases of E-7 run in-process only, on the private instance of ``create_all`` — none on
the lane: every account and token row there is the test's, so the whole list is asserted; a lane's neighbours cannot
make an account of theirs wait, and a run killed mid-test leaves nothing behind. Every state of a verification link is a
token of the token service (``_private_link``: live, expired — issued its lifetime and a minute ago, never waited for —,
revoked, consumed), and each scene first reads the service's own criterion (``email_verification.awaiting_verification``
and ``holds_place``) so that its premise is the scene, not an assumption: that reading is green today, only the field is
missing. UADM-VER-01 is one scene per state, the initial administrator waiting for its setup included; UADM-VER-02 reads
five accounts beside each other, one of them waiting; UADM-VER-03 promotes a waiting account and then ends its wait with
a ``PATCH``; UADM-VER-04 reactivates an account whose link expired, on an instance with one free place; UADM-VER-05 reads
the schema.
"""

import ast
import contextlib
import inspect
import logging
import re
import sqlite3
import textwrap
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from secrets import token_urlsafe
from typing import Any, Optional, Union
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import pytest_asyncio
import structlog
from fastapi import FastAPI
from sqlalchemy import delete, event, func, or_, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.util import await_only
from structlog.testing import capture_logs

from backend.app import logging_config
from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1 import settings as settings_api
from backend.app.api.v1 import users as users_api
from backend.app.config import API_V1_PREFIX, get_settings
from backend.app.config.accounts import AdminBootstrapConfig
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import AccountToken, AccountTokenPurpose, Broker, BrokerUserAccess, GlobalSetting, OnboardingFlow, Transaction, TransactionType, User, UserOnboardingProgress, UserOnboardingStepProgress, UserRole, UserSettings
from backend.app.db.session import get_async_engine, get_session_generator
from backend.app.schemas.brokers import BRDeleteItem
from backend.app.schemas.users import AdminUserRead
from backend.app.services.accounts import auth_service, login_throttle, registration_service, user_service
from backend.app.services.accounts.bootstrap_admin_service import BootstrapAction, complete_admin_setup, issue_setup_link, run_admin_bootstrap
from backend.app.services.accounts.onboarding_service import ONBOARDING_FLOW_STEPS, ONBOARDING_FLOW_VERSIONS
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import DEFAULT_TTL, IssuedToken, TokenStatus, consume_token, hash_token, inspect_token, issue_token, revoke_tokens
from backend.app.services.brim import brim_provider
from backend.app.services.brokers.broker_service import BrokerService
from backend.app.services.email import verification as email_verification
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.test_db.test_autoincrement_schema import _alembic_upgrade_head
from backend.test_scripts.test_db_config import verify_test_database
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
COOKIE = auth_api.SESSION_COOKIE_NAME

INVITE = AccountTokenPurpose.INVITE
PASSWORD_RESET = AccountTokenPurpose.PASSWORD_RESET
ADMIN_SETUP = AccountTokenPurpose.ADMIN_SETUP
EMAIL_VERIFICATION = AccountTokenPurpose.EMAIL_VERIFICATION

REGISTRATION_VARIABLE = "LIBREFOLIO_REGISTRATION"
MAX_USERS_VARIABLE = "LIBREFOLIO_MAX_USERS"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
BILLING_URL_VARIABLE = "LIBREFOLIO_BILLING_URL"
ACCOUNTS_VARIABLES = (REGISTRATION_VARIABLE, MAX_USERS_VARIABLE, PUBLIC_URL_VARIABLE, BILLING_URL_VARIABLE)
MODE_KEY = "registration_mode"

#: Set with a trailing slash on purpose: a link is the URL without it, then the path.
PUBLIC_URL = "https://librefolio.example.test/base/"
PUBLIC_ORIGIN = "https://librefolio.example.test/base"
BILLING_LINK = "https://billing.example.test/plans/family"

#: An account as GET /users lists it and PATCH /users/{user_id} answers it; ``avatar_url`` is lot N69-4's (point 20), ``pending_verification`` lot E-7's (point 21).
USER_ITEM_KEYS = frozenset({"id", "username", "email", "is_active", "is_superuser", "created_at", "protected", "holds_place", "pending_setup", "pending_verification", "avatar_url"})
INVITE_ITEM_KEYS = frozenset({"id", "grants_admin", "email", "created_at", "expires_at", "created_by_user_id"})
USAGE_KEYS = frozenset({"used", "max_users", "billing_url"})
ISSUED_INVITE_KEYS = frozenset({"invite", "token", "path", "url"})
RESET_LINK_KEYS = frozenset({"token", "path", "url", "expires_at"})
#: secrets.token_urlsafe(32): 43 URL-safe characters.
TOKEN_SHAPE = re.compile(r"[A-Za-z0-9_-]{43}")
#: The page of each kind of link; the token follows in the fragment, ``#token=…``.
LINK_PAGES = {INVITE: "/invite", PASSWORD_RESET: "/reset-password"}
#: GET /auth/me's answer to a cookie whose session was ended.
SESSION_EXPIRED = (401, {"detail": "Session expired or invalid"})

PRIVATE_PASSWORD = "Users-Admin-Api-2026"
NEW_PASSWORD = "Reset-By-Link-2026"
THIRD_PASSWORD = "Reset-Again-2026"
#: Far above any id a private database of a few rows reaches.
NEVER_ISSUED_ID = 987_654_321
CANARY = "canary: the capture sees the events of the admin endpoints' logger"

STEP_FLOWS = {flow.value: tuple(steps) for flow, steps in ONBOARDING_FLOW_STEPS.items()}

# Lot A6a: the deletion of an account by an administrator, and the hook of lot A7.
#: The one event an administrator's deletion logs, word for word, and the fields it carries.
ADMIN_DELETION_EVENT = "Account deleted by an administrator"
ADMIN_DELETION_FIELDS = ("user_id", "username", "admin_id", "brokers_deleted", "files_removed")
#: What the in-process stand-in of the hook answers for an account it protects.
PROTECTION_REASON = "the paying administrator of this managed instance"
#: What the spy of delete_files_for_brokers answers: a count no real call on an empty directory could give.
FILES_REMOVED = 2
TRANSACTION_DATE = date(2026, 1, 5)
NOTHING_WAS_DELETED = "nothing was deleted"

# Lot A7b: the pending administrator in the Users tab (contract C5).
#: The F02 administrator the configuration of a private instance names (LIBREFOLIO_ADMIN_USERNAME, LIBREFOLIO_ADMIN_EMAIL), handed to the bootstrap.
F02_USERNAME = "f02_admin"
F02_EMAIL = "f02-admin@example.com"
#: The password the pending administrator chooses through its setup link: it meets the rules (decision 37).
SETUP_PASSWORD = "Setup-Admin-Pass-2026"


@pytest.fixture(scope="module")
def test_server():
    """The lane's server, for the lane cases only (attaches to the runner's shared backend)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# SHARED HELPERS
# ============================================================================


@dataclass(frozen=True)
class _Account:
    """An account one test created."""

    user_id: int
    username: str
    email: str
    password: str


@dataclass(frozen=True)
class _Signed:
    """An account with the session cookie of one device."""

    account: _Account
    cookie: str


def _expect(violations: list[str], ok: bool, message: str) -> None:
    """Record a broken expectation instead of stopping at the first one: the red lists them all."""
    if not ok:
        violations.append(message)


def _verdict(violations: list[str]) -> str:
    return "\n- " + "\n- ".join(violations)


def _detail(response: httpx.Response) -> dict[str, Any]:
    """``detail`` of a coded refusal as a mapping; {} when the body carries none."""
    try:
        body = response.json()
    except ValueError:
        return {}
    detail = body.get("detail") if isinstance(body, dict) else None
    return detail if isinstance(detail, dict) else {}


def _refusal(response: httpx.Response) -> tuple[int, Optional[str]]:
    """(status, ``detail.error_code``): (201, None) for a success."""
    return response.status_code, _detail(response).get("error_code")


def _counts(response: httpx.Response) -> dict[str, Any]:
    """What the administrator's ``USER_LIMIT_REACHED`` says, read from ``detail``: the code, the limit, the seats used, the billing link."""
    detail = _detail(response)
    return {key: detail.get(key) for key in ("error_code", "limit", "used", "billing_url")}


def _answer(response: httpx.Response) -> tuple[int, Any]:
    """The status and the JSON body (the text when it is not JSON)."""
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text


def _session_cookie(response: httpx.Response) -> Optional[str]:
    """The value of the response's ``session`` Set-Cookie, parsed by name; None when there is none."""
    for header in response.headers.get_list("set-cookie"):
        name, _, value = header.split(";", 1)[0].partition("=")
        if name.strip() == COOKIE and value:
            return value
    return None


def _instant(text: Any) -> Optional[datetime]:
    """An API timestamp as an aware UTC datetime (a naive one is UTC); None when it is not a timestamp."""
    if not isinstance(text, str):
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _comparable(item: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """An item with its timestamps as instants: two serialisations of the same moment compare equal."""
    if item is None:
        return None
    return {key: _instant(value) if key.endswith("_at") else value for key, value in item.items()}


def _user_item_violations(item: Any, account: _Account, *, active: bool, superuser: bool, protected: bool = False, holds_place: bool = False, pending_setup: bool = False, pending_verification: bool = False, avatar_url: Optional[str] = None) -> list[str]:
    """What is wrong with an account as GET /users lists it, and PATCH answers it: exactly its eleven fields, with these values.

    ``protected`` is False unless the test replaced the hook: today the hook protects nobody (lot A6a).
    ``holds_place`` is workstream E's flag, true only for an inactive account whose live verification link holds its place (``api email-verification-hooks``, EVH-006…012); false unless the case wrote such a link (UADM-060).
    ``pending_setup`` is lot A7b's flag (C5), true only for the account waiting for its F02 setup (UADM-060 to UADM-064); false unless the case made one.
    ``pending_verification`` is lot E-7's flag (point 21), true only for an inactive account holding a verification link neither consumed nor revoked, live or expired (UADM-VER-01 to UADM-VER-04); false unless the case made one. ``holds_place`` is then its own: true only with a live link.
    ``avatar_url`` is lot N69-4's field (point 20), the account's avatar as its user settings store it; None — null — unless the case gave the account one (UADM-AV-01 to UADM-AV-03).
    """
    if not isinstance(item, dict) or set(item) != USER_ITEM_KEYS:
        return [f"{account.username}: an account must be exactly {sorted(USER_ITEM_KEYS)}, no hash and no secret: {item}"]
    expected = {
        "id": account.user_id,
        "username": account.username,
        "email": account.email,
        "is_active": active,
        "is_superuser": superuser,
        "protected": protected,
        "holds_place": holds_place,
        "pending_setup": pending_setup,
        "pending_verification": pending_verification,
        "avatar_url": avatar_url,
    }
    found = {key: item[key] for key in expected}
    violations = [] if found == expected else [f"{account.username}: expected {expected}, got {found}"]
    _expect(violations, _instant(item["created_at"]) is not None, f"{account.username}: created_at is not a timestamp: {item['created_at']!r}")
    return violations


def _link_path_violations(path: Any, purpose: AccountTokenPurpose, token: str) -> list[str]:
    """What is wrong with a link's ``path``: the purpose's page, no query, and the token alone in the URL fragment (``#token=…``).

    The fragment because a browser never sends it: the token stays out of the access log and of every proxy's log.
    """
    if not isinstance(path, str):
        return [f"path: a string expected, got {path!r}"]
    parts = urlparse(path)
    found = {"page": (parts.scheme, parts.netloc, parts.path), "query": parts.query, "fragment": parse_qs(parts.fragment)}
    expected = {"page": ("", "", LINK_PAGES[purpose]), "query": "", "fragment": {"token": [token]}}
    return [] if found == expected else [f"path: expected {LINK_PAGES[purpose]}#token=<the token>, nothing in the query; got {path!r}, read as {found}"]


def _issued_invite_violations(issued: Any, *, grants_admin: bool, email: Optional[str], created_by: int) -> list[str]:
    """What is wrong with the 201 of POST /users/invites: its keys, the token, its path, the invitation and its seven days."""
    if not isinstance(issued, dict) or set(issued) != ISSUED_INVITE_KEYS:
        return [f"the 201 body must be exactly {sorted(ISSUED_INVITE_KEYS)}: {issued}"]
    token, invite = str(issued["token"]), issued["invite"]
    violations: list[str] = []
    _expect(violations, TOKEN_SHAPE.fullmatch(token) is not None, f"token: 43 URL-safe characters expected, got {token!r}")
    violations += _link_path_violations(issued["path"], INVITE, token)
    if not isinstance(invite, dict) or set(invite) != INVITE_ITEM_KEYS:
        return [*violations, f"invite: exactly {sorted(INVITE_ITEM_KEYS)} expected, got {invite}"]
    found = (invite["grants_admin"], invite["email"], invite["created_by_user_id"])
    _expect(violations, found == (grants_admin, email, created_by), f"invite: (grants_admin, email, created_by_user_id) must be {(grants_admin, email, created_by)}, got {found}")
    created, expires = _instant(invite["created_at"]), _instant(invite["expires_at"])
    lives = None if created is None or expires is None else expires - created
    _expect(violations, lives == DEFAULT_TTL[INVITE], f"invite: an invitation lives {DEFAULT_TTL[INVITE]} from its creation, this one {lives}: {invite}")
    return violations


def _reset_link_violations(link: Any) -> list[str]:
    """What is wrong with the 201 of POST /users/{id}/password-reset-link: its keys, the token, its path, its expiry."""
    if not isinstance(link, dict) or set(link) != RESET_LINK_KEYS:
        return [f"the 201 body must be exactly {sorted(RESET_LINK_KEYS)}: {link}"]
    token = str(link["token"])
    violations: list[str] = []
    _expect(violations, TOKEN_SHAPE.fullmatch(token) is not None, f"token: 43 URL-safe characters expected, got {token!r}")
    violations += _link_path_violations(link["path"], PASSWORD_RESET, token)
    _expect(violations, _instant(link["expires_at"]) is not None, f"expires_at is not a timestamp: {link['expires_at']!r}")
    return violations


def _url_violations(body: dict[str, Any], public_origin: Optional[str]) -> list[str]:
    """``url`` is the public URL (its trailing slash dropped) plus ``path``, the token still in the fragment; or null without a public URL."""
    expected = None if public_origin is None else f"{public_origin}{body.get('path')}"
    if body.get("url") != expected:
        return [f"url: expected {expected!r}, got {body.get('url')!r} (path {body.get('path')!r})"]
    url_parts = urlparse(expected) if expected else None
    in_the_fragment = url_parts is None or (url_parts.query == "" and parse_qs(url_parts.fragment) == {"token": [str(body.get("token"))]})
    return [] if in_the_fragment else [f"url: the token must travel in the fragment, not in the query: {expected!r}"]


def _onboarding_reading(body: Any) -> dict[str, tuple[str, dict[str, str]]]:
    """GET /settings/onboarding as {flow: (status, {step: status})}, steps empty for a flow without them."""
    return {item["flow"]: (item["status"], {step["step_id"]: step["status"] for step in item.get("steps") or []}) for item in body["flows"]}


def _pending(flow: str) -> tuple[str, dict[str, str]]:
    """A flow as a never-touched account reads it: pending, and every step of it pending."""
    return "pending", dict.fromkeys(STEP_FLOWS.get(flow, ()), "pending")


# ============================================================================
# THE LANE: ITS SERVER AND ITS DATABASE
# ============================================================================


def _lane_engine() -> AsyncEngine:
    """The lane's test database, the one its server serves: the lane cases read and delete their own rows there, nowhere else."""
    is_test_db, database_url = verify_test_database()
    assert is_test_db, f"Refusing to touch a database that is not the lane's test database: {database_url}"
    return get_async_engine()


@dataclass
class _LaneRows:
    """What a lane case wrote: accounts by name (even one a red let through), tokens by id, the marker e-mails of invitations, brokers by id (recorded once committed)."""

    usernames: list[str] = field(default_factory=list)
    token_ids: list[int] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    broker_ids: list[int] = field(default_factory=list)

    def new_username(self, prefix: str) -> str:
        username = f"{prefix}_{uuid.uuid4().hex[:12]}"
        self.usernames.append(username)
        return username

    def new_email(self, prefix: str) -> str:
        email = f"{prefix}_{uuid.uuid4().hex[:12]}@example.com"
        self.emails.append(email)
        return email


async def _delete_lane_brokers(engine: AsyncEngine, broker_ids: list[int]) -> list[str]:
    """Delete the case's brokers still there, with their transactions, whoever holds them now (no access check); what failed.

    Only ids recorded after their commit reach here: brokers have AUTOINCREMENT, so such an id was never anyone else's.
    """
    if not broker_ids:
        return []
    async with AsyncSession(engine) as session:
        try:
            surviving = sorted((await session.execute(select(Broker.id).where(Broker.id.in_(broker_ids)))).scalars().all())
            response = await BrokerService(session).delete_bulk([BRDeleteItem(id=broker_id, force=True) for broker_id in surviving], user_id=0, as_user_id="all")
            await session.commit()
        except Exception as exc:  # the accounts still get their attempt; every failure is reported together
            return [f"brokers {broker_ids}: {exc!r}"]
    return [f"broker {result.id}: {result.message}" for result in response.results if not result.success]


async def _delete_lane_rows(rows: _LaneRows) -> list[str]:
    """Delete the case's tokens (by id, issued or consumed by its accounts, or to its marker e-mails), then its brokers, then its accounts; what failed."""
    errors: list[str] = []
    engine = _lane_engine()
    async with AsyncSession(engine) as session:
        user_ids = list((await session.execute(select(User.id).where(User.username.in_(rows.usernames)))).scalars().all())
        mine = or_(AccountToken.id.in_(rows.token_ids), AccountToken.email.in_(rows.emails), AccountToken.created_by_user_id.in_(user_ids), AccountToken.consumed_by_user_id.in_(user_ids))
        try:
            await session.execute(delete(AccountToken).where(mine))
            await session.commit()
        except Exception as exc:  # the accounts still get their attempt; every failure is reported together
            errors.append(f"tokens: {exc!r}")
    errors += await _delete_lane_brokers(engine, rows.broker_ids)
    for user_id in user_ids:
        async with AsyncSession(engine) as session:
            try:
                await user_service.delete_user(session, user_id)
            except Exception as exc:
                errors.append(f"user {user_id}: {exc!r}")
    return errors


@pytest_asyncio.fixture
async def lane(test_server) -> AsyncIterator[_LaneRows]:
    """The lane's server, in its own mode (open); what the case writes there is deleted at teardown, after a red too."""
    rows = _LaneRows()
    try:
        yield rows
    finally:
        errors = await _delete_lane_rows(rows)
        assert not errors, f"Teardown: could not delete what this test wrote in the lane: {errors}"


async def _live(method: str, path: str, *, cookie: Optional[str] = None, json: Any = None) -> httpx.Response:
    """One request to the lane's server from a client of its own: no cookie jar, the session (if any) sent explicitly."""
    headers = {"Cookie": f"{COOKIE}={cookie}"} if cookie else {}
    async with httpx.AsyncClient() as client:
        return await client.request(method, f"{API_BASE}{path}", json=json, headers=headers, timeout=TIMEOUT)


async def _live_register(lane: _LaneRows, prefix: str) -> _Account:
    """A regular account of this case, registered over HTTP in the lane's own mode, which must be open."""
    username = lane.new_username(prefix)
    email, password = f"{username}@example.com", f"Initial-{uuid.uuid4().hex[:12]}1"
    response = await _live("POST", "/auth/register", json={"username": username, "email": email, "password": password})
    assert response.status_code == 201, f"Setup: registering {username} on the lane failed; its mode must be open, as every unit registering its own users needs it: {response.status_code} {response.text}"
    user = response.json()["user"]
    assert user["is_superuser"] is False, f"Precondition: {username} registered as the lane's first account, hence its administrator: the api setup (db populate) did not run on this lane"
    return _Account(user_id=user["id"], username=username, email=email, password=password)


async def _live_login(account: _Account, password: Optional[str] = None) -> httpx.Response:
    """POST /auth/login from a client of its own: a new device."""
    return await _live("POST", "/auth/login", json={"username": account.username, "password": password or account.password})


async def _live_sign_in(account: _Account, password: Optional[str] = None) -> str:
    """A new device of ``account``: a login, and the session cookie it sets."""
    response = await _live_login(account, password)
    cookie = _session_cookie(response)
    assert response.status_code == 200 and cookie, f"Login as {account.username} failed: {response.status_code} {response.text}"
    return cookie


async def _live_member(lane: _LaneRows, prefix: str) -> _Signed:
    """A regular account of this case, signed in on one device."""
    account = await _live_register(lane, prefix)
    return _Signed(account, await _live_sign_in(account))


async def _lane_set(username: str, *, admin: Optional[bool] = None, active: Optional[bool] = None) -> None:
    """Promote, demote, activate or deactivate one of this case's accounts through user_service, in the lane's database."""
    async with AsyncSession(_lane_engine()) as session:
        if admin is not None:
            done, error = await user_service.set_user_admin(session, username, admin)
            assert done, f"Setup: set_user_admin({username!r}, {admin}) failed: {error}"
        if active is not None:
            done, error = await user_service.set_user_active(session, username, active)
            assert done, f"Setup: set_user_active({username!r}, {active}) failed: {error}"


async def _live_admin(lane: _LaneRows) -> _Signed:
    """An administrator of this case: registered, promoted through user_service, then signed in."""
    account = await _live_register(lane, "uadm_admin")
    await _lane_set(account.username, admin=True)
    cookie = await _live_sign_in(account)
    status, body = await _live_me(cookie)
    assert status == 200 and body["user"]["is_superuser"] is True, f"Setup: {account.username} must be signed in as an administrator: {status} {body}"
    return _Signed(account, cookie)


async def _live_me(cookie: str) -> tuple[int, Any]:
    """GET /auth/me with this session cookie only."""
    return _answer(await _live("GET", "/auth/me", cookie=cookie))


async def _live_me_id(cookie: str) -> Optional[int]:
    """The id of the account this cookie is a session of; None when GET /auth/me refuses it."""
    status, body = await _live_me(cookie)
    return body["user"]["id"] if status == 200 else None


async def _listed(cookie: str, path: str, item_id: int) -> Optional[dict[str, Any]]:
    """The item of id ``item_id`` in GET ``path`` (/users or /users/invites) as this administrator sees it, found by id; None when absent."""
    response = await _live("GET", path, cookie=cookie)
    assert response.status_code == 200, f"GET {path} as an administrator: expected 200, got {response.status_code} {response.text}"
    return next((item for item in response.json()["items"] if item.get("id") == item_id), None)


async def _live_register_with(lane: _LaneRows, prefix: str, invite_token: str) -> tuple[str, httpx.Response]:
    """POST /auth/register with ``invite_token``, for a new username of this case."""
    username = lane.new_username(prefix)
    body = {"username": username, "email": f"{username}@example.com", "password": f"Invited-{uuid.uuid4().hex[:12]}1", "invite_token": invite_token}
    return username, await _live("POST", "/auth/register", json=body)


async def _live_reset_password(token: str, new_password: str) -> httpx.Response:
    """POST /auth/password-reset, anonymous: whoever holds the link."""
    return await _live("POST", "/auth/password-reset", json={"token": token, "new_password": new_password})


async def _admin_reset_link(admin: _Signed, user_id: int) -> str:
    """A reset link for ``user_id``, issued by ``admin`` through the API: its token."""
    response = await _live("POST", f"/users/{user_id}/password-reset-link", cookie=admin.cookie)
    assert response.status_code == 201, f"POST /users/{user_id}/password-reset-link: expected 201, got {response.status_code} {response.text}"
    return response.json()["token"]


async def _live_onboarding(cookie: str) -> dict[str, tuple[str, dict[str, str]]]:
    """The account's own onboarding, read from GET /settings/onboarding with its session."""
    response = await _live("GET", "/settings/onboarding", cookie=cookie)
    assert response.status_code == 200, f"GET /settings/onboarding: {response.status_code} {response.text}"
    return _onboarding_reading(response.json())


async def _live_onboarding_move(cookie: str, flow: OnboardingFlow, action: str, step: Optional[str] = None) -> None:
    """Complete or skip a flow, or one of its steps, as the account itself does from the app."""
    path = f"/settings/onboarding/{flow.value}/{action}" if step is None else f"/settings/onboarding/{flow.value}/steps/{step}/{action}"
    response = await _live("POST", path, cookie=cookie, json={"expected_version": ONBOARDING_FLOW_VERSIONS[flow]})
    assert response.status_code == 200, f"Setup: POST {path}: {response.status_code} {response.text}"


async def _lane_user(user_id: int) -> tuple[bool, bool, int]:
    """(is_active, is_superuser, session_version) of one of this case's accounts, read fresh from the lane's database."""
    async with AsyncSession(_lane_engine()) as session:
        row = (await session.execute(select(User.is_active, User.is_superuser, User.session_version).where(User.id == user_id))).one()
    return bool(row[0]), bool(row[1]), int(row[2])


async def _lane_user_id(username: str) -> Optional[int]:
    async with AsyncSession(_lane_engine()) as session:
        return (await session.execute(select(User.id).where(User.username == username))).scalar_one_or_none()


async def _lane_issue(lane: _LaneRows, purpose: AccountTokenPurpose, **arguments: Any) -> IssuedToken:
    """A token issued by token_service directly in the lane's database, committed, and recorded for the teardown."""
    async with AsyncSession(_lane_engine(), expire_on_commit=False) as session:
        issued = await issue_token(session, purpose, **arguments)
        await session.commit()
    lane.token_ids.append(issued.record.id)
    return issued


async def _lane_consume(token: str, purpose: AccountTokenPurpose, consumed_by_user_id: int) -> None:
    async with AsyncSession(_lane_engine()) as session:
        record = await consume_token(session, token, purpose, consumed_by_user_id=consumed_by_user_id)
        await session.commit()
    assert record is not None, "Setup: the token must be consumed"


async def _lane_token_of(token: str) -> Optional[AccountToken]:
    """The lane's row of a plaintext token, found by its hash as stored."""
    async with AsyncSession(_lane_engine(), expire_on_commit=False) as session:
        return (await session.execute(select(AccountToken).where(AccountToken.token_hash == hash_token(token)))).scalars().first()


async def _lane_token_state(token_id: int) -> tuple[Any, Any, Any]:
    """(purpose, consumed_at, revoked_at) of one of this case's tokens."""
    async with AsyncSession(_lane_engine()) as session:
        row = (await session.execute(select(AccountToken.purpose, AccountToken.consumed_at, AccountToken.revoked_at).where(AccountToken.id == token_id))).one()
    return row[0], row[1], row[2]


async def _lane_reset_links(user_id: int) -> int:
    """How many reset links this case's account has ever had: it owns them all."""
    async with AsyncSession(_lane_engine()) as session:
        statement = select(func.count()).select_from(AccountToken).where(AccountToken.user_id == user_id, AccountToken.purpose == PASSWORD_RESET.value)
        return int((await session.execute(statement)).scalar_one())


# ============================================================================
# LANE: ONLY AN ADMINISTRATOR, AND A REFUSED CALL CHANGES NOTHING
# ============================================================================


@dataclass(frozen=True)
class _Scene:
    """An administrator, an ordinary account (the refused caller), a target account signed in with intro_tour completed, a live invitation, and an e-mail no invitation carries yet."""

    admin: _Signed
    member: _Signed
    target: _Signed
    invite_id: int
    marker_email: str


async def _scene(lane: _LaneRows) -> _Scene:
    admin = await _live_admin(lane)
    member = await _live_member(lane, "uadm_member")
    target = await _live_member(lane, "uadm_target")
    await _live_onboarding_move(target.cookie, OnboardingFlow.INTRO_TOUR, "complete")
    invite = await _lane_issue(lane, INVITE, created_by_user_id=admin.account.user_id)
    return _Scene(admin=admin, member=member, target=target, invite_id=invite.record.id, marker_email=lane.new_email("uadm_marker"))


async def _footprint(scene: _Scene) -> dict[str, Any]:
    """Everything an admin route could change in the scene, read fresh from the lane's database; the target None once it is gone."""
    target_id = scene.target.account.user_id
    async with AsyncSession(_lane_engine()) as session:
        target = (await session.execute(select(User.is_active, User.is_superuser, User.session_version).where(User.id == target_id))).one_or_none()
        invite = (await session.execute(select(AccountToken.consumed_at, AccountToken.revoked_at).where(AccountToken.id == scene.invite_id))).one()
        marker = (await session.execute(select(func.count()).select_from(AccountToken).where(AccountToken.email == scene.marker_email))).scalar_one()
        tour = (await session.execute(select(UserOnboardingProgress.status).where(UserOnboardingProgress.user_id == target_id, UserOnboardingProgress.flow == OnboardingFlow.INTRO_TOUR.value))).scalar_one_or_none()
    return {
        "the target (is_active, is_superuser, session_version)": None if target is None else tuple(target),
        "the scene's invitation (consumed_at, revoked_at)": tuple(invite),
        "invitations to the marker e-mail": marker,
        "reset links of the target": await _lane_reset_links(target_id),
        "the target's intro_tour": tour,
    }


@dataclass(frozen=True)
class _Route:
    """An admin route as the matrix calls it, with the status an administrator gets."""

    method: str
    path: Callable[[_Scene], str]
    body: Callable[[_Scene], Any]
    success: int


def _on_target(suffix: str) -> Callable[[_Scene], str]:
    return lambda scene: f"/users/{scene.target.account.user_id}{suffix}"


def _no_body(scene: _Scene) -> None:
    return None


ADMIN_ROUTES = [
    pytest.param(_Route("GET", lambda scene: "/users/invites", _no_body, 200), id="list-invites"),
    pytest.param(_Route("POST", lambda scene: "/users/invites", lambda scene: {"grants_admin": True, "email": scene.marker_email}, 201), id="create-invite"),
    pytest.param(_Route("DELETE", lambda scene: f"/users/invites/{scene.invite_id}", _no_body, 204), id="revoke-invite"),
    pytest.param(_Route("GET", lambda scene: "/users", _no_body, 200), id="list-users"),
    pytest.param(_Route("PATCH", _on_target(""), lambda scene: {"is_active": False}, 200), id="deactivate-user"),
    pytest.param(_Route("POST", _on_target("/password-reset-link"), _no_body, 201), id="reset-link"),
    pytest.param(_Route("POST", _on_target("/sessions/revoke"), _no_body, 204), id="revoke-sessions"),
    pytest.param(_Route("POST", _on_target("/onboarding/reset"), lambda scene: {}, 204), id="reset-onboarding"),
    # Lot A6a. In every case the administrator's call comes last: after the 204 the target is gone, and nothing reads the scene again.
    pytest.param(_Route("GET", _on_target("/deletion-preview"), _no_body, 200), id="deletion-preview"),
    pytest.param(_Route("DELETE", _on_target(""), _no_body, 204), id="delete-user"),
]


class TestOnlyAnAdministrator:
    """Every admin route on the lane's server: anonymous 401, an ordinary account 403, neither changes anything; the administrator gets through."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("route", ADMIN_ROUTES)
    async def test_anonymous_401_ordinary_403_nothing_changes_and_the_administrator_gets_through(self, lane: _LaneRows, route: _Route) -> None:
        """UADM-001: no session → 401, an ordinary account's session → 403, and after each the scene is as it was (the target's state and sessions, the invitation, no invitation issued, no reset link, the onboarding); then the administrator gets the route's success status.

        Each call acts on what a wrongly open route would visibly change: the deactivation of the target, an invitation to a
        marker e-mail, the revocation of a live invitation, the target's sessions, reset links and completed intro_tour, and
        (lot A6a) the target itself, which a wrongly open DELETE would remove. The preview of its deletion changes nothing
        whoever calls it: there only the status codes speak.
        """
        scene = await _scene(lane)
        path, body = route.path(scene), route.body(scene)
        print_section(f"UADM-001: {route.method} {path} is for administrators only")
        before = await _footprint(scene)

        anonymous = await _live(route.method, path, json=body)
        after_anonymous = await _footprint(scene)
        ordinary = await _live(route.method, path, cookie=scene.member.cookie, json=body)
        after_ordinary = await _footprint(scene)
        admin = await _live(route.method, path, cookie=scene.admin.cookie, json=body)

        violations: list[str] = []
        _expect(violations, anonymous.status_code == 401, f"anonymous: expected 401, got {anonymous.status_code} {anonymous.text}")
        _expect(violations, after_anonymous == before, f"the anonymous call changed the lane: {before} → {after_anonymous}")
        _expect(violations, ordinary.status_code == 403, f"an ordinary account: expected 403, got {ordinary.status_code} {ordinary.text}")
        _expect(violations, after_ordinary == before, f"the ordinary account's call changed the lane: {before} → {after_ordinary}")
        _expect(violations, admin.status_code == route.success, f"the administrator: expected {route.success}, got {admin.status_code} {admin.text}")
        assert not violations, f"{route.method} {path} must be an administrator's route only:{_verdict(violations)}"
        print_success(f"{route.method} {path}: 401, 403, nothing changed, then {route.success} for the administrator")

    @pytest.mark.asyncio
    async def test_an_ordinary_account_cannot_make_itself_an_administrator_nor_mint_its_own_reset_link(self, lane: _LaneRows) -> None:
        """UADM-002: an ordinary account aiming the routes at itself — PATCH {is_superuser: true}, POST its own reset link — gets 403 for both, and is still an ordinary account with no reset link."""
        print_section("UADM-002: no route makes an ordinary account an administrator of itself")
        member = await _live_member(lane, "uadm_climber")
        user_id = member.account.user_id
        before = await _lane_user(user_id)

        promote = await _live("PATCH", f"/users/{user_id}", cookie=member.cookie, json={"is_superuser": True})
        link = await _live("POST", f"/users/{user_id}/password-reset-link", cookie=member.cookie)

        violations: list[str] = []
        _expect(violations, promote.status_code == 403, f"PATCH /users/{{self}} {{is_superuser: true}}: expected 403, got {promote.status_code} {promote.text}")
        _expect(violations, link.status_code == 403, f"POST /users/{{self}}/password-reset-link: expected 403, got {link.status_code} {link.text}")
        _expect(violations, await _lane_user(user_id) == before, f"the account changed: {before} → {await _lane_user(user_id)}")
        _expect(violations, await _lane_reset_links(user_id) == 0, "a reset link was issued to the account that asked for it")
        assert not violations, f"An ordinary account must not reach the admin routes, not even about itself:{_verdict(violations)}"
        print_success("403 twice, still an ordinary account, no reset link")


# ============================================================================
# LANE: THE ACCOUNTS AND THE INVITATIONS
# ============================================================================


class TestAccountsListOnTheLane:
    @pytest.mark.asyncio
    async def test_lists_this_cases_accounts_with_their_flags_and_the_usage(self, lane: _LaneRows) -> None:
        """UADM-003: GET /users → {items, usage}; this case's four accounts are there, found by id — the caller, an ordinary account, a second administrator, an inactive account — each exactly {id, username, email, is_active, is_superuser, created_at, protected} with the right flags, protected false (A6a: the hook protects nobody today); usage is {used, max_users, billing_url}, and used counts at least this case's three active accounts."""
        print_section("UADM-003: GET /users")
        admin = await _live_admin(lane)
        member = await _live_register(lane, "uadm_listed")
        second_admin = await _live_register(lane, "uadm_listed_admin")
        inactive = await _live_register(lane, "uadm_listed_off")
        await _lane_set(second_admin.username, admin=True)
        await _lane_set(inactive.username, active=False)

        response = await _live("GET", "/users", cookie=admin.cookie)

        assert response.status_code == 200, f"GET /users as an administrator: {response.status_code} {response.text}"
        body = response.json()
        assert isinstance(body, dict) and set(body) == {"items", "usage"}, f"GET /users must answer exactly {{items, usage}}: {body}"
        items = {item.get("id"): item for item in body["items"]}
        violations: list[str] = []
        for account, active, superuser in ((admin.account, True, True), (member, True, False), (second_admin, True, True), (inactive, False, False)):
            violations += _user_item_violations(items.get(account.user_id), account, active=active, superuser=superuser)
        usage = body["usage"]
        _expect(violations, isinstance(usage, dict) and set(usage) == USAGE_KEYS, f"usage must be exactly {sorted(USAGE_KEYS)}: {usage}")
        _expect(violations, isinstance(usage, dict) and isinstance(usage.get("used"), int) and usage["used"] >= 3, f"usage.used counts the active accounts, this case's three at least: {usage}")
        assert not violations, f"GET /users broke its contract:{_verdict(violations)}"
        print_success("four accounts of this case listed with their flags, usage present")


class TestInvitationsOnTheLane:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("grants_admin", "with_email"), [pytest.param(False, False, id="user-invitation"), pytest.param(True, True, id="admin-invitation-with-email")])
    async def test_an_invitation_is_listed_opens_one_account_in_its_role_then_is_gone(self, lane: _LaneRows, grants_admin: bool, with_email: bool) -> None:
        """UADM-004: POST /users/invites → 201 {invite, token, path, url}; GET /users/invites lists exactly that invitation; its token registers one account through POST /auth/register, in the invitation's role; then the invitation is no longer listed, its row is consumed by that account, and the same token registers nobody else (400 INVITE_INVALID)."""
        print_section(f"UADM-004: the life of an invitation, grants_admin={grants_admin}")
        admin = await _live_admin(lane)
        email = lane.new_email("uadm_invitee") if with_email else None
        request = {"grants_admin": grants_admin, **({"email": email} if email else {})}

        created = await _live("POST", "/users/invites", cookie=admin.cookie, json=request)

        assert created.status_code == 201, f"POST /users/invites: expected 201, got {created.status_code} {created.text}"
        issued = created.json()
        violations = _issued_invite_violations(issued, grants_admin=grants_admin, email=email, created_by=admin.account.user_id)
        assert not violations, f"POST /users/invites answered a 201 that breaks its contract:{_verdict(violations)}"
        token, invite = issued["token"], issued["invite"]
        lane.token_ids.append(invite["id"])
        _expect(violations, issued["url"] is None or issued["url"].endswith(issued["path"]), f"url must be null or end with the path: {issued}")
        listed = await _listed(admin.cookie, "/users/invites", invite["id"])
        _expect(violations, _comparable(listed) == _comparable(invite), f"GET /users/invites must list the invitation as it was created: listed {listed}, created {invite}")
        row = await _lane_token_of(token)
        _expect(violations, row is not None and row.id == invite["id"] and row.purpose == INVITE.value and row.consumed_at is None, f"the token must be the stored hash of the live invitation {invite['id']}: {row}")
        assert not violations, f"the new invitation is not what was asked:{_verdict(violations)}"

        _, registered = await _live_register_with(lane, "uadm_invited", token)

        assert registered.status_code == 201, f"POST /auth/register with the invitation: expected 201, got {registered.status_code} {registered.text}"
        user = registered.json()["user"]
        _expect(violations, user["is_superuser"] is grants_admin, f"the account must take the invitation's role, is_superuser={grants_admin}: {user}")
        _expect(violations, await _listed(admin.cookie, "/users/invites", invite["id"]) is None, "a consumed invitation must no longer be listed")
        row = await _lane_token_of(token)
        _expect(violations, row is not None and row.consumed_by_user_id == user["id"], f"the invitation must be consumed by the account it opened: {row}")
        again_username, again = await _live_register_with(lane, "uadm_invited_again", token)
        _expect(violations, _refusal(again) == (400, "INVITE_INVALID"), f"a consumed invitation must register nobody else: {again.status_code} {again.text}")
        _expect(violations, await _lane_user_id(again_username) is None, f"{again_username} was created with a consumed invitation")
        assert not violations, f"An invitation must open one account, in its role, once:{_verdict(violations)}"
        print_success(f"listed, opened {user['username']} (is_superuser={grants_admin}), then gone and spent")

    @pytest.mark.asyncio
    async def test_a_revoked_invitation_is_gone_and_opens_nothing(self, lane: _LaneRows) -> None:
        """UADM-005: DELETE /users/invites/{id} → 204 with no body; the invitation is no longer listed and its row is revoked; a second DELETE → 404; its token → 400 INVITE_INVALID at POST /auth/register, and no account."""
        print_section("UADM-005: a revoked invitation")
        admin = await _live_admin(lane)
        created = await _live("POST", "/users/invites", cookie=admin.cookie, json={"grants_admin": False})
        assert created.status_code == 201, f"POST /users/invites: expected 201, got {created.status_code} {created.text}"
        invite_id, token = created.json()["invite"]["id"], created.json()["token"]
        lane.token_ids.append(invite_id)

        revoked = await _live("DELETE", f"/users/invites/{invite_id}", cookie=admin.cookie)
        again = await _live("DELETE", f"/users/invites/{invite_id}", cookie=admin.cookie)
        username, registered = await _live_register_with(lane, "uadm_revoked_invitee", token)

        violations: list[str] = []
        _expect(violations, (revoked.status_code, revoked.content) == (204, b""), f"DELETE: expected 204 with no body, got {revoked.status_code} {revoked.text}")
        _expect(violations, await _listed(admin.cookie, "/users/invites", invite_id) is None, "a revoked invitation must no longer be listed")
        purpose, consumed_at, revoked_at = await _lane_token_state(invite_id)
        _expect(violations, revoked_at is not None and consumed_at is None, f"the row must be revoked, not consumed: consumed_at={consumed_at}, revoked_at={revoked_at}")
        _expect(violations, again.status_code == 404, f"a second DELETE: expected 404, got {again.status_code} {again.text}")
        _expect(violations, _refusal(registered) == (400, "INVITE_INVALID"), f"a revoked invitation must register nobody: {registered.status_code} {registered.text}")
        _expect(violations, await _lane_user_id(username) is None, f"{username} was created with a revoked invitation")
        assert not violations, f"A revoked invitation must be gone:{_verdict(violations)}"
        print_success("204, unlisted, 404 the second time, its token opens nothing")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ["consumed-invitation", "live-reset-link"])
    async def test_what_is_not_a_live_invitation_cannot_be_revoked_and_stays_as_it_was(self, lane: _LaneRows, kind: str) -> None:
        """UADM-006: DELETE /users/invites/{id} of a consumed invitation, or of the id of a live password-reset link → 404, and the row is untouched: the reset link stays live.

        Presence barrier first: a live invitation of this case is revoked with 204. A route that does not exist answers 404 too.
        """
        print_section(f"UADM-006: DELETE /users/invites/{{id}} of a {kind}")
        admin = await _live_admin(lane)
        holder = await _live_register(lane, "uadm_holder")
        barrier = await _lane_issue(lane, INVITE, created_by_user_id=admin.account.user_id)
        revoked = await _live("DELETE", f"/users/invites/{barrier.record.id}", cookie=admin.cookie)
        assert revoked.status_code == 204, f"Presence barrier: DELETE of a live invitation of this case must answer 204, or the 404 below proves nothing: {revoked.status_code} {revoked.text}"
        if kind == "live-reset-link":
            issued = await _lane_issue(lane, PASSWORD_RESET, user_id=holder.user_id)
        else:
            issued = await _lane_issue(lane, INVITE, created_by_user_id=admin.account.user_id)
            await _lane_consume(issued.token, INVITE, holder.user_id)
        before = await _lane_token_state(issued.record.id)

        response = await _live("DELETE", f"/users/invites/{issued.record.id}", cookie=admin.cookie)

        assert response.status_code == 404, f"only a live invitation can be revoked: expected 404 for a {kind}, got {response.status_code} {response.text}"
        assert await _lane_token_state(issued.record.id) == before, f"the {kind} changed: {before} → {await _lane_token_state(issued.record.id)}"
        print_success(f"{kind}: 404, untouched")


# ============================================================================
# LANE: STATE AND ROLE OF AN ACCOUNT
# ============================================================================


UNKNOWN_ACCOUNT_ROUTES = [
    pytest.param("PATCH", "", {"is_active": False}, 200, id="patch"),
    pytest.param("POST", "/password-reset-link", None, 201, id="reset-link"),
    pytest.param("POST", "/sessions/revoke", None, 204, id="revoke-sessions"),
    pytest.param("POST", "/onboarding/reset", {}, 204, id="reset-onboarding"),
]


class TestAccountStateOnTheLane:
    """PATCH /users/{id} on this case's own accounts. The caller is an active administrator and never the target, so the last-administrator guard never applies here, whatever the lane holds."""

    @pytest.mark.asyncio
    async def test_deactivation_ends_the_sessions_and_reactivation_does_not_bring_them_back(self, lane: _LaneRows) -> None:
        """UADM-007: PATCH {is_active: false} → 200 with the account; its cookie is refused (401), its password gets 403 ACCOUNT_DISABLED, its session version rose by one. PATCH {is_active: true} → 200; the old cookie stays refused (401 «Session expired or invalid»), the version does not move, a new login works."""
        print_section("UADM-007: deactivate, then reactivate")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_paused")
        account, user_id = member.account, member.account.user_id
        _, _, version = await _lane_user(user_id)

        off = await _live("PATCH", f"/users/{user_id}", cookie=admin.cookie, json={"is_active": False})
        assert off.status_code == 200, f"PATCH {{is_active: false}}: expected 200, got {off.status_code} {off.text}"
        violations = _user_item_violations(off.json(), account, active=False, superuser=False)
        old_cookie_while_off = await _live_me(member.cookie)
        login_while_off = await _live_login(account)
        state_while_off = await _lane_user(user_id)
        on = await _live("PATCH", f"/users/{user_id}", cookie=admin.cookie, json={"is_active": True})

        _expect(violations, old_cookie_while_off[0] == 401, f"a deactivated account's cookie must be refused: GET /auth/me {old_cookie_while_off}")
        _expect(violations, _refusal(login_while_off) == (403, "ACCOUNT_DISABLED"), f"the right password of a deactivated account: expected 403 ACCOUNT_DISABLED, got {login_while_off.status_code} {login_while_off.text}")
        _expect(violations, state_while_off == (False, False, version + 1), f"deactivation must end the sessions, version + 1: {state_while_off}, version before {version}")
        assert on.status_code == 200, f"PATCH {{is_active: true}}: expected 200, got {on.status_code} {on.text}" + (" — the lane's server runs with LIBREFOLIO_MAX_USERS, which no unit may set" if _refusal(on) == (409, "USER_LIMIT_REACHED") else "")
        violations += _user_item_violations(on.json(), account, active=True, superuser=False)
        _expect(violations, await _live_me(member.cookie) == SESSION_EXPIRED, f"reactivation must not bring the old session back: GET /auth/me {await _live_me(member.cookie)}")
        _expect(violations, await _lane_user(user_id) == (True, False, version + 1), f"reactivation must not move the version: {await _lane_user(user_id)}")
        _expect(violations, await _live_me_id(await _live_sign_in(account)) == user_id, "a new login after the reactivation must work")
        assert not violations, f"Deactivation and reactivation broke their contract:{_verdict(violations)}"
        print_success("deactivated: sessions ended, login refused; reactivated: old cookie still refused, new login works")

    @pytest.mark.asyncio
    async def test_promotion_keeps_the_session_and_demotion_ends_it(self, lane: _LaneRows) -> None:
        """UADM-008: PATCH {is_superuser: true} → 200; the same cookie now reaches GET /users, the version unchanged. PATCH {is_superuser: false} → 200; that cookie is refused (401 «Session expired or invalid»), the version rose by one, and a new login gets 403 from GET /users."""
        print_section("UADM-008: promote, then demote")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_promoted")
        account, user_id = member.account, member.account.user_id
        _, _, version = await _lane_user(user_id)
        before = await _live("GET", "/users", cookie=member.cookie)

        up = await _live("PATCH", f"/users/{user_id}", cookie=admin.cookie, json={"is_superuser": True})
        assert up.status_code == 200, f"PATCH {{is_superuser: true}}: expected 200, got {up.status_code} {up.text}"
        violations = _user_item_violations(up.json(), account, active=True, superuser=True)
        promoted = await _live("GET", "/users", cookie=member.cookie)
        state_promoted = await _lane_user(user_id)
        down = await _live("PATCH", f"/users/{user_id}", cookie=admin.cookie, json={"is_superuser": False})

        _expect(violations, before.status_code == 403, f"Precondition: an ordinary account gets 403 from GET /users, got {before.status_code}")
        _expect(violations, promoted.status_code == 200, f"promotion ends no session: the same cookie must now reach GET /users, got {promoted.status_code} {promoted.text}")
        _expect(violations, state_promoted == (True, True, version), f"promotion must not move the version: {state_promoted}, before {version}")
        assert down.status_code == 200, f"PATCH {{is_superuser: false}}: expected 200, got {down.status_code} {down.text}"
        violations += _user_item_violations(down.json(), account, active=True, superuser=False)
        _expect(violations, await _live_me(member.cookie) == SESSION_EXPIRED, f"demotion must end the sessions: GET /auth/me {await _live_me(member.cookie)}")
        _expect(violations, await _lane_user(user_id) == (True, False, version + 1), f"demotion: version + 1: {await _lane_user(user_id)}")
        fresh = await _live_sign_in(account)
        _expect(violations, (await _live("GET", "/users", cookie=fresh)).status_code == 403, "after the demotion a new login must be an ordinary account again (403 from GET /users)")
        assert not violations, f"Promotion and demotion broke their contract:{_verdict(violations)}"
        print_success("promoted: same session, admin routes open; demoted: session ended, routes closed")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("method", "suffix", "body", "success"), UNKNOWN_ACCOUNT_ROUTES)
    async def test_an_account_that_does_not_exist_is_404(self, lane: _LaneRows, method: str, suffix: str, body: Any, success: int) -> None:
        """UADM-009: the id of an account this case created and deleted (ids of users are never reused: AUTOINCREMENT) → 404.

        Presence barrier first: the same call on an existing account of this case gets the route's success status. A route
        that does not exist answers 404 too.
        """
        print_section(f"UADM-009: {method} /users/{{gone}}{suffix}")
        admin = await _live_admin(lane)
        present = await _live_register(lane, "uadm_present")
        barrier = await _live(method, f"/users/{present.user_id}{suffix}", cookie=admin.cookie, json=body)
        assert barrier.status_code == success, f"Presence barrier: {method} /users/{{id}}{suffix} on an existing account must answer {success}, or the 404 below proves nothing: {barrier.status_code} {barrier.text}"
        gone = await _live_register(lane, "uadm_gone")
        async with AsyncSession(_lane_engine()) as session:
            assert await user_service.delete_user(session, gone.user_id) is not None, f"Setup: {gone.username} must be deleted"

        response = await _live(method, f"/users/{gone.user_id}{suffix}", cookie=admin.cookie, json=body)

        assert response.status_code == 404, f"{method} /users/{gone.user_id}{suffix} of a deleted account: expected 404, got {response.status_code} {response.text}"
        print_success("404")


# ============================================================================
# LANE: RESET LINKS, SESSIONS, ONBOARDING
# ============================================================================


class TestResetLinksOnTheLane:
    @pytest.mark.asyncio
    async def test_a_reset_link_works_once(self, lane: _LaneRows) -> None:
        """UADM-010: POST /users/{id}/password-reset-link → 201 {token, path, url, expires_at}, the stored hash of a reset link of that account; POST /auth/password-reset with it → 200, the new password signs in and the old one no longer does; the same link again → 400 TOKEN_INVALID, and the password stays."""
        print_section("UADM-010: a reset link, once")
        admin = await _live_admin(lane)
        holder = await _live_register(lane, "uadm_forgetful")

        created = await _live("POST", f"/users/{holder.user_id}/password-reset-link", cookie=admin.cookie)

        assert created.status_code == 201, f"POST /users/{{id}}/password-reset-link: expected 201, got {created.status_code} {created.text}"
        link = created.json()
        violations = _reset_link_violations(link)
        assert not violations, f"the 201 breaks its contract:{_verdict(violations)}"
        _expect(violations, link["url"] is None or link["url"].endswith(link["path"]), f"url must be null or end with the path: {link}")
        row = await _lane_token_of(link["token"])
        _expect(violations, row is not None and (row.purpose, row.user_id, row.consumed_at, row.revoked_at) == (PASSWORD_RESET.value, holder.user_id, None, None), f"the token must be the stored hash of a live reset link of {holder.username}: {row}")
        used = await _live_reset_password(link["token"], NEW_PASSWORD)
        _expect(violations, used.status_code == 200, f"POST /auth/password-reset: expected 200, got {used.status_code} {used.text}")
        _expect(violations, (await _live_login(holder, NEW_PASSWORD)).status_code == 200, "the new password must sign in")
        _expect(violations, (await _live_login(holder)).status_code == 401, "the old password must no longer sign in")
        reused = await _live_reset_password(link["token"], THIRD_PASSWORD)
        _expect(violations, _refusal(reused) == (400, "TOKEN_INVALID"), f"a used link: expected 400 TOKEN_INVALID, got {reused.status_code} {reused.text}")
        _expect(violations, (await _live_login(holder, NEW_PASSWORD)).status_code == 200, "a refused second use must leave the password as it was")
        assert not violations, f"A reset link must work once:{_verdict(violations)}"
        print_success("201, used once, refused the second time")

    @pytest.mark.asyncio
    async def test_a_new_link_revokes_the_accounts_earlier_links_and_only_those(self, lane: _LaneRows) -> None:
        """UADM-011: a link for a bystander, then two for the holder: the holder's first is revoked (400 TOKEN_INVALID, the password unchanged), the second works; the bystander's link was not revoked and works."""
        print_section("UADM-011: a new link revokes the account's earlier ones, only those")
        admin = await _live_admin(lane)
        holder = await _live_register(lane, "uadm_reset_holder")
        bystander = await _live_register(lane, "uadm_reset_bystander")
        theirs = await _admin_reset_link(admin, bystander.user_id)
        first = await _admin_reset_link(admin, holder.user_id)
        second = await _admin_reset_link(admin, holder.user_id)

        violations: list[str] = []
        first_row, their_row = await _lane_token_of(first), await _lane_token_of(theirs)
        _expect(violations, first_row is not None and first_row.revoked_at is not None, f"the holder's earlier link must be revoked by the new one: {first_row}")
        _expect(violations, their_row is not None and their_row.revoked_at is None, f"another account's link must not be revoked: {their_row}")
        used_first = await _live_reset_password(first, NEW_PASSWORD)
        _expect(violations, _refusal(used_first) == (400, "TOKEN_INVALID"), f"the revoked link: expected 400 TOKEN_INVALID, got {used_first.status_code} {used_first.text}")
        _expect(violations, (await _live_login(holder)).status_code == 200, "a refused link must leave the password as it was")
        _expect(violations, (await _live_reset_password(second, NEW_PASSWORD)).status_code == 200, "the newest link must work")
        _expect(violations, (await _live_login(holder, NEW_PASSWORD)).status_code == 200, "the newest link must set the password")
        _expect(violations, (await _live_reset_password(theirs, NEW_PASSWORD)).status_code == 200, "the bystander's link must still work")
        _expect(violations, (await _live_login(bystander, NEW_PASSWORD)).status_code == 200, "the bystander's link must set the bystander's password")
        assert not violations, f"Only the newest link of an account may work, and only that account's are revoked:{_verdict(violations)}"
        print_success("earlier link revoked, newest works, the bystander's untouched")


class TestSessionsAndOnboardingOnTheLane:
    @pytest.mark.asyncio
    async def test_sessions_revoke_ends_every_session_of_the_account_and_no_other(self, lane: _LaneRows) -> None:
        """UADM-012: POST /users/{id}/sessions/revoke → 204 with no body; both devices of the account get 401 «Session expired or invalid», its version rose by one, it stays active and can sign in again; another account's session and version do not move."""
        print_section("UADM-012: sessions revoke")
        admin = await _live_admin(lane)
        holder = await _live_register(lane, "uadm_signed_out")
        bystander = await _live_member(lane, "uadm_signed_in")
        device_a, device_b = await _live_sign_in(holder), await _live_sign_in(holder)
        holder_before, bystander_before = await _lane_user(holder.user_id), await _lane_user(bystander.account.user_id)

        response = await _live("POST", f"/users/{holder.user_id}/sessions/revoke", cookie=admin.cookie)

        violations: list[str] = []
        _expect(violations, (response.status_code, response.content) == (204, b""), f"expected 204 with no body, got {response.status_code} {response.text}")
        for label, cookie in (("device A", device_a), ("device B", device_b)):
            _expect(violations, await _live_me(cookie) == SESSION_EXPIRED, f"{label} of the account must be refused with {SESSION_EXPIRED}: {await _live_me(cookie)}")
        _expect(violations, await _lane_user(holder.user_id) == (holder_before[0], holder_before[1], holder_before[2] + 1), f"the account's version must rise by one, nothing else: {holder_before} → {await _lane_user(holder.user_id)}")
        _expect(violations, await _live_me_id(bystander.cookie) == bystander.account.user_id, "another account's session must not notice")
        _expect(violations, await _lane_user(bystander.account.user_id) == bystander_before, "another account's version must not move")
        _expect(violations, await _live_me_id(await _live_sign_in(holder)) == holder.user_id, "the account must be able to sign in again")
        assert not violations, f"POST /users/{{id}}/sessions/revoke broke its contract:{_verdict(violations)}"
        print_success("204: both devices out, the bystander in, a new login works")

    @pytest.mark.asyncio
    async def test_onboarding_reset_puts_every_flow_and_step_back_to_pending(self, lane: _LaneRows) -> None:
        """UADM-013: an account completed intro_tour and import_guide (with its steps), skipped fx_guide and one step of transaction_bulk_guide; POST /users/{id}/onboarding/reset {} → 204, and the account, signing in again, reads every flow and every step pending."""
        print_section("UADM-013: onboarding reset, every flow")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_onboarded")
        bulk_step = STEP_FLOWS[OnboardingFlow.TRANSACTION_BULK_GUIDE.value][0]
        await _live_onboarding_move(member.cookie, OnboardingFlow.INTRO_TOUR, "complete")
        await _live_onboarding_move(member.cookie, OnboardingFlow.FX_GUIDE, "skip")
        await _live_onboarding_move(member.cookie, OnboardingFlow.IMPORT_GUIDE, "complete")
        await _live_onboarding_move(member.cookie, OnboardingFlow.TRANSACTION_BULK_GUIDE, "skip", step=bulk_step)
        before = await _live_onboarding(member.cookie)
        assert before[OnboardingFlow.INTRO_TOUR.value][0] == "completed" and before[OnboardingFlow.FX_GUIDE.value][0] == "skipped", f"Precondition: {before}"
        assert before[OnboardingFlow.IMPORT_GUIDE.value][1] and set(before[OnboardingFlow.IMPORT_GUIDE.value][1].values()) == {"completed"}, f"Precondition: {before}"
        assert before[OnboardingFlow.TRANSACTION_BULK_GUIDE.value][1][bulk_step] == "skipped", f"Precondition: {before}"

        response = await _live("POST", f"/users/{member.account.user_id}/onboarding/reset", cookie=admin.cookie, json={})

        assert (response.status_code, response.content) == (204, b""), f"expected 204 with no body, got {response.status_code} {response.text}"
        after = await _live_onboarding(await _live_sign_in(member.account))
        expected = {flow.value: _pending(flow.value) for flow in ONBOARDING_FLOW_VERSIONS}
        assert after == expected, f"every flow and step must be back to pending: {after}"
        print_success("every flow and every step pending")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("flow", [OnboardingFlow.INTRO_TOUR.value, OnboardingFlow.IMPORT_GUIDE.value])
    async def test_onboarding_reset_of_one_flow_leaves_the_others_as_they_were(self, lane: _LaneRows, flow: str) -> None:
        """UADM-014: intro_tour and import_guide completed, fx_guide skipped; {flow} → 204, that flow (with its steps, when it has any) back to pending, every other flow as it was."""
        print_section(f"UADM-014: onboarding reset of {flow}")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_one_flow")
        await _live_onboarding_move(member.cookie, OnboardingFlow.INTRO_TOUR, "complete")
        await _live_onboarding_move(member.cookie, OnboardingFlow.IMPORT_GUIDE, "complete")
        await _live_onboarding_move(member.cookie, OnboardingFlow.FX_GUIDE, "skip")
        before = await _live_onboarding(member.cookie)
        assert before[flow][0] == "completed", f"Precondition: {flow} completed: {before}"

        response = await _live("POST", f"/users/{member.account.user_id}/onboarding/reset", cookie=admin.cookie, json={"flow": flow})

        assert (response.status_code, response.content) == (204, b""), f"expected 204 with no body, got {response.status_code} {response.text}"
        after = await _live_onboarding(await _live_sign_in(member.account))
        assert after == {**before, flow: _pending(flow)}, f"only {flow} must be back to pending: before {before}, after {after}"
        print_success(f"{flow} pending, the others untouched")

    @pytest.mark.asyncio
    async def test_onboarding_reset_of_an_unknown_flow_is_refused_and_resets_nothing(self, lane: _LaneRows) -> None:
        """UADM-015: {flow: "no_such_flow"} → 422, and the account's onboarding is as it was."""
        print_section("UADM-015: onboarding reset of an unknown flow")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_unknown_flow")
        await _live_onboarding_move(member.cookie, OnboardingFlow.INTRO_TOUR, "complete")
        before = await _live_onboarding(member.cookie)

        response = await _live("POST", f"/users/{member.account.user_id}/onboarding/reset", cookie=admin.cookie, json={"flow": "no_such_flow"})

        assert response.status_code == 422, f"an unknown flow: expected 422, got {response.status_code} {response.text}"
        assert await _live_onboarding(await _live_sign_in(member.account)) == before, "a refused reset must reset nothing"
        print_success("422, nothing reset")


# ============================================================================
# LANE: DELETING AN ACCOUNT, AND WHAT IT WOULD TAKE (lot A6a)
# ============================================================================


def _deposit(broker_id: int) -> Transaction:
    return Transaction(broker_id=broker_id, type=TransactionType.DEPOSIT, date=TRANSACTION_DATE, amount=Decimal("100"), currency="EUR")


def _cash_leg(broker_id: int, amount: str) -> Transaction:
    return Transaction(broker_id=broker_id, type=TransactionType.CASH_TRANSFER, date=TRANSACTION_DATE, amount=Decimal(amount), currency="EUR")


def _grant(user_id: int, broker_id: int, role: UserRole) -> BrokerUserAccess:
    return BrokerUserAccess(user_id=user_id, broker_id=broker_id, role=role, share_percentage=Decimal("0"))


@dataclass(frozen=True)
class _DeletionScene:
    """An administrator, the target (signed in), its partner, and four brokers this case wrote in the lane's database.

    - ``sole``: the target its only OWNER; two DEPOSITs and the outgoing leg of a cash transfer to ``co_owned`` → deleted;
    - ``last_owner``: the target OWNER, the partner EDITOR, so the target is its last owner; a DEPOSIT → deleted;
    - ``co_owned``: the target and the partner both OWNER; the incoming leg → left, the target an OWNER there;
    - ``viewed``: the partner OWNER, the target VIEWER → left, the target a VIEWER there.

    The incoming leg is the one transfer half the deletion leaves alone.
    """

    admin: _Signed
    target: _Signed
    partner: _Account
    brokers: dict[str, int]
    names: dict[int, str]
    transactions: dict[int, int]

    @property
    def deleted(self) -> list[int]:
        return sorted(self.brokers[key] for key in ("sole", "last_owner"))

    @property
    def left(self) -> dict[int, str]:
        """The brokers left, with the target's role there as the API spells it."""
        return {self.brokers["co_owned"]: UserRole.OWNER.value, self.brokers["viewed"]: UserRole.VIEWER.value}

    def preview(self) -> dict[str, Any]:
        """What GET /users/{target}/deletion-preview must answer, exactly: both lists by broker id."""
        return {
            "user_id": self.target.account.user_id,
            "username": self.target.account.username,
            "brokers_deleted": [{"id": broker_id, "name": self.names[broker_id], "transactions": self.transactions[broker_id]} for broker_id in self.deleted],
            "brokers_left": [{"id": broker_id, "name": self.names[broker_id], "role": role} for broker_id, role in sorted(self.left.items())],
            "transfers_unpaired": 1,
        }


@dataclass(frozen=True)
class _LaneHoldings:
    """What the lane holds of the target and of this case's four brokers, read fresh: every read scoped to them."""

    target: bool
    brokers: frozenset[int]
    grants: frozenset[tuple[int, int, str]]
    transactions: frozenset[tuple[int, int, Optional[int]]]


async def _deletion_scene(lane: _LaneRows) -> _DeletionScene:
    """Register the administrator, the target and the partner; write the four brokers with their grants and transactions; record the brokers once committed."""
    admin = await _live_admin(lane)
    target = await _live_member(lane, "uadm_leaver")
    partner = await _live_register(lane, "uadm_partner")
    t, p = target.account.user_id, partner.user_id
    marker = uuid.uuid4().hex[:12]
    async with AsyncSession(_lane_engine(), expire_on_commit=False) as session:
        rows = {key: Broker(name=f"UADM {key} {marker}") for key in ("sole", "last_owner", "co_owned", "viewed")}
        session.add_all(rows.values())
        await session.flush()
        b = {key: broker.id for key, broker in rows.items()}
        grants = ((t, "sole", UserRole.OWNER), (t, "last_owner", UserRole.OWNER), (p, "last_owner", UserRole.EDITOR), (t, "co_owned", UserRole.OWNER), (p, "co_owned", UserRole.OWNER), (p, "viewed", UserRole.OWNER), (t, "viewed", UserRole.VIEWER))
        session.add_all([_grant(user_id, b[key], role) for user_id, key, role in grants])
        outgoing, incoming = _cash_leg(b["sole"], "-25"), _cash_leg(b["co_owned"], "25")
        session.add_all([_deposit(b["sole"]), _deposit(b["sole"]), _deposit(b["last_owner"]), outgoing, incoming])
        await session.flush()
        outgoing.related_transaction_id, incoming.related_transaction_id = incoming.id, outgoing.id
        await session.commit()
    # Recorded only now: an id flushed then rolled back could be handed to a neighbour, and the teardown deletes by id.
    lane.broker_ids.extend(b.values())
    counts = {b["sole"]: 3, b["last_owner"]: 1, b["co_owned"]: 1, b["viewed"]: 0}
    return _DeletionScene(admin=admin, target=target, partner=partner, brokers=b, names={broker.id: broker.name for broker in rows.values()}, transactions=counts)


async def _lane_holdings(scene: _DeletionScene) -> _LaneHoldings:
    broker_ids = list(scene.brokers.values())
    async with AsyncSession(_lane_engine()) as session:
        target = await session.scalar(select(User.id).where(User.id == scene.target.account.user_id))
        brokers = (await session.execute(select(Broker.id).where(Broker.id.in_(broker_ids)))).scalars().all()
        grants = (await session.execute(select(BrokerUserAccess.broker_id, BrokerUserAccess.user_id, BrokerUserAccess.role).where(BrokerUserAccess.broker_id.in_(broker_ids)))).all()
        transactions = (await session.execute(select(Transaction.id, Transaction.broker_id, Transaction.related_transaction_id).where(Transaction.broker_id.in_(broker_ids)))).all()
    return _LaneHoldings(
        target=target is not None,
        brokers=frozenset(brokers),
        grants=frozenset((broker_id, user_id, UserRole(role).value) for broker_id, user_id, role in grants),
        transactions=frozenset((tx_id, broker_id, related) for tx_id, broker_id, related in transactions),
    )


def _after_deleting(before: _LaneHoldings, scene: _DeletionScene) -> _LaneHoldings:
    """What deleting the target must leave: the deleted brokers gone with their grants and transactions, the target and its grants gone, the half left alone unlinked; nothing else."""
    deleted, target_id = set(scene.deleted), scene.target.account.user_id
    gone = {tx_id for tx_id, broker_id, _ in before.transactions if broker_id in deleted}
    return _LaneHoldings(
        target=False,
        brokers=before.brokers - deleted,
        grants=frozenset(grant for grant in before.grants if grant[0] not in deleted and grant[1] != target_id),
        transactions=frozenset((tx_id, broker_id, None if related in gone else related) for tx_id, broker_id, related in before.transactions if broker_id not in deleted),
    )


async def _lane_account(user_id: int) -> Optional[tuple[bool, bool, int]]:
    """(is_active, is_superuser, session_version) of one of this case's accounts, read fresh; None once it is gone."""
    async with AsyncSession(_lane_engine()) as session:
        row = (await session.execute(select(User.is_active, User.is_superuser, User.session_version).where(User.id == user_id))).one_or_none()
    return None if row is None else (bool(row[0]), bool(row[1]), int(row[2]))


class TestAccountDeletionOnTheLane:
    """GET /users/{id}/deletion-preview and DELETE /users/{id} on this case's own accounts and brokers. The caller is an active administrator, never the target unless the case says so."""

    @pytest.mark.asyncio
    async def test_the_preview_says_what_would_go_and_what_would_stay_and_writes_nothing(self, lane: _LaneRows) -> None:
        """UADM-040: GET /users/{target}/deletion-preview → 200, exactly {user_id, username, brokers_deleted: [sole (3 transactions), last_owner (1)], brokers_left: [co_owned OWNER, viewed VIEWER], transfers_unpaired: 1}, both lists by id; the target, the four brokers, their grants and transactions are as before, and the target's session still works."""
        print_section("UADM-040: the preview of a deletion")
        scene = await _deletion_scene(lane)
        target_id = scene.target.account.user_id
        before = await _lane_holdings(scene)

        response = await _live("GET", f"/users/{target_id}/deletion-preview", cookie=scene.admin.cookie)

        after = await _lane_holdings(scene)
        violations: list[str] = []
        _expect(violations, _answer(response) == (200, scene.preview()), f"expected 200 with exactly {scene.preview()}, got {_answer(response)}")
        _expect(violations, after == before, f"the preview must write nothing: before {before}, after {after}")
        _expect(violations, await _live_me_id(scene.target.cookie) == target_id, "the preview must end no session of the target")
        assert not violations, f"GET /users/{{id}}/deletion-preview broke its contract:{_verdict(violations)}"
        print_success("two brokers would go, two would stay, one transfer half left alone; nothing written")

    @pytest.mark.asyncio
    async def test_the_deletion_takes_what_the_preview_said_and_ends_the_sessions(self, lane: _LaneRows) -> None:
        """UADM-041: after a preview (200, the presence barrier of the 404s below), DELETE /users/{target} → 204 with no body; the target and its grants are gone, sole and last_owner are gone with their transactions and grants, co_owned and viewed stay with the partner's grants, the incoming leg stays unlinked — exactly what the preview said, nothing else; the target's session answers 401; the preview and a second DELETE of it → 404; the administrator's session does not notice."""
        print_section("UADM-041: DELETE /users/{id}")
        scene = await _deletion_scene(lane)
        target_id, cookie = scene.target.account.user_id, scene.admin.cookie
        preview = await _live("GET", f"/users/{target_id}/deletion-preview", cookie=cookie)
        assert preview.status_code == 200, f"Presence barrier: the preview of an existing account must answer 200, or the 404 below proves nothing: {preview.status_code} {preview.text}"
        assert await _live_me_id(scene.target.cookie) == target_id, "Presence barrier: the target's session must work before the deletion"
        before = await _lane_holdings(scene)

        response = await _live("DELETE", f"/users/{target_id}", cookie=cookie)

        after = await _lane_holdings(scene)
        previewed = preview.json()
        previewed_deleted = {item.get("id") for item in previewed.get("brokers_deleted", [])}
        previewed_left = {item.get("id") for item in previewed.get("brokers_left", [])}
        violations: list[str] = []
        _expect(violations, (response.status_code, response.content) == (204, b""), f"expected 204 with no body, got {response.status_code} {response.text}")
        _expect(violations, previewed == scene.preview(), f"the preview: expected {scene.preview()}, got {previewed}")
        _expect(violations, not after.brokers & previewed_deleted and previewed_left <= after.brokers, f"the brokers must follow the preview: deleted {sorted(previewed_deleted)}, left {sorted(previewed_left)}, still there {sorted(after.brokers)}")
        _expect(violations, after == _after_deleting(before, scene), f"the deletion must take the target, its grants and the brokers it was the last owner of, unlinking the half left alone, and nothing else: expected {_after_deleting(before, scene)}, found {after}")
        _expect(violations, (await _live_me(scene.target.cookie))[0] == 401, f"the deleted account's session must answer 401: {await _live_me(scene.target.cookie)}")
        _expect(violations, (await _live("GET", f"/users/{target_id}/deletion-preview", cookie=cookie)).status_code == 404, "the preview of a deleted account must answer 404")
        _expect(violations, (await _live("DELETE", f"/users/{target_id}", cookie=cookie)).status_code == 404, "deleting a deleted account must answer 404")
        _expect(violations, await _live_me_id(scene.admin.cookie) == scene.admin.account.user_id, "the administrator's session must not notice")
        assert not violations, f"DELETE /users/{{id}} broke its contract:{_verdict(violations)}"
        print_success("204: the account and the two brokers it was the last owner of gone, the other two left, the session 401, then 404")

    @pytest.mark.asyncio
    async def test_an_administrator_deletes_neither_itself_nor_another_administrator(self, lane: _LaneRows) -> None:
        """UADM-042: DELETE of the caller's own id → 409 SELF_DELETION (one's own account is deleted from the profile); of an active administrator, and of an inactive one → 409 DEMOTE_FIRST; each of the three is as it was, version included, and the caller is still signed in as an administrator.

        Presence barrier first: an ordinary account of this case is deleted with 204, so the route exists and refuses
        only these. Deterministic on the lane: the caller is an active administrator, and the others are this case's.
        """
        print_section("UADM-042: SELF_DELETION and DEMOTE_FIRST")
        admin = await _live_admin(lane)
        ordinary = await _live_register(lane, "uadm_deletable")
        active_admin = await _live_register(lane, "uadm_other_admin")
        dormant_admin = await _live_register(lane, "uadm_dormant_admin")
        await _lane_set(active_admin.username, admin=True)
        await _lane_set(dormant_admin.username, admin=True)
        await _lane_set(dormant_admin.username, active=False)
        barrier = await _live("DELETE", f"/users/{ordinary.user_id}", cookie=admin.cookie)
        assert barrier.status_code == 204, f"Presence barrier: DELETE of an ordinary account of this case must answer 204, or the 409s below prove nothing: {barrier.status_code} {barrier.text}"
        accounts = {"the caller": admin.account.user_id, "an active administrator": active_admin.user_id, "an inactive administrator": dormant_admin.user_id}
        before = {label: await _lane_account(user_id) for label, user_id in accounts.items()}

        answers = {label: _refusal(await _live("DELETE", f"/users/{user_id}", cookie=admin.cookie)) for label, user_id in accounts.items()}

        after = {label: await _lane_account(user_id) for label, user_id in accounts.items()}
        expected = {"the caller": (409, "SELF_DELETION"), "an active administrator": (409, "DEMOTE_FIRST"), "an inactive administrator": (409, "DEMOTE_FIRST")}
        violations: list[str] = []
        _expect(violations, answers == expected, f"expected {expected}, got {answers}")
        _expect(violations, after == before, f"a refused deletion must change nothing, the version included: before {before}, after {after}")
        _expect(violations, (await _live("GET", "/users", cookie=admin.cookie)).status_code == 200, "the caller must still be signed in as an administrator")
        assert not violations, f"An administrator must delete neither itself nor another administrator:{_verdict(violations)}"
        print_success("409 SELF_DELETION, 409 DEMOTE_FIRST twice, nothing changed")

    @pytest.mark.asyncio
    async def test_every_account_of_the_lane_is_listed_unprotected_today(self, lane: _LaneRows) -> None:
        """UADM-043: GET /users → every account carries ``protected: false``: today the hook of lot A7 protects nobody, whatever the neighbours registered. Presence barrier: this case's two accounts are listed."""
        print_section("UADM-043: nobody is protected today")
        admin = await _live_admin(lane)
        member = await _live_register(lane, "uadm_unprotected")

        response = await _live("GET", "/users", cookie=admin.cookie)

        assert response.status_code == 200, f"GET /users as an administrator: {response.status_code} {response.text}"
        items = response.json()["items"]
        assert {admin.account.user_id, member.user_id} <= {item.get("id") for item in items}, "Presence barrier: this case's two accounts must be listed"
        flagged = [(item.get("username"), item.get("protected", "<missing>")) for item in items if item.get("protected") is not False]
        assert flagged == [], f"every account must be listed with protected false today: {flagged}"
        print_success(f"{len(items)} accounts, none protected")


# ============================================================================
# THE PRIVATE INSTANCE: THE REAL ROUTERS ON A DATABASE OF THIS TEST
# ============================================================================


@dataclass(frozen=True)
class _Private:
    """An instance of one test: the routers of auth, users and settings, every session on ``engine``."""

    engine: AsyncEngine
    app: FastAPI


def _private_app(engine: AsyncEngine) -> FastAPI:
    """The real routers, mounted under the API prefix as ``api/v1/router.py`` mounts them; ``get_session_generator`` opens sessions on ``engine``."""
    app = FastAPI()
    for router in (auth_api.router, users_api.router, settings_api.router):
        app.include_router(router, prefix=API_V1_PREFIX)

    async def private_session() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session_generator] = private_session
    return app


@pytest_asyncio.fixture
async def private(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_Private]:
    """A private SQLite file under tmp_path, schema and default settings as a new install starts with; no accounts variable; bcrypt at cost 4. Disposed at teardown."""
    for name in ACCOUNTS_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'instance.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield _Private(engine=engine, app=_private_app(engine))
    finally:
        await engine.dispose()


async def _call(private: _Private, method: str, path: str, *, cookie: Optional[str] = None, json: Any = None) -> httpx.Response:
    """One request to the private instance, from a client of its own: no cookie jar, the session (if any) sent explicitly."""
    headers = {"Cookie": f"{COOKIE}={cookie}"} if cookie else {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=private.app), base_url="http://test", timeout=TIMEOUT) as client:
        return await client.request(method, f"{API_V1_PREFIX}{path}", json=json, headers=headers)


async def _add_user(private: _Private, username: str, *, admin: bool = False, active: bool = True) -> _Account:
    """An account written as a row, with a real bcrypt hash of PRIVATE_PASSWORD (cost 4), so that it can sign in."""
    email = f"{username}@example.com"
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        user = User(username=username, email=email, hashed_password=auth_service.hash_password(PRIVATE_PASSWORD), is_active=active, is_superuser=admin)
        session.add(user)
        await session.commit()
    return _Account(user_id=user.id, username=username, email=email, password=PRIVATE_PASSWORD)


async def _sign_in(private: _Private, account: _Account) -> str:
    """A session of ``account`` on the private instance, through its POST /auth/login."""
    response = await _call(private, "POST", "/auth/login", json={"username": account.username, "password": account.password})
    cookie = _session_cookie(response)
    assert response.status_code == 200 and cookie, f"Setup: {account.username} could not sign in to the private instance: {response.status_code} {response.text}"
    return cookie


async def _admin(private: _Private, username: str = "root") -> tuple[_Account, str]:
    """An active administrator of the private instance, signed in."""
    account = await _add_user(private, username, admin=True)
    return account, await _sign_in(private, account)


async def _private_user(private: _Private, user_id: int) -> tuple[bool, bool, int]:
    """(is_active, is_superuser, session_version) of an account, read fresh."""
    async with AsyncSession(private.engine) as session:
        row = (await session.execute(select(User.is_active, User.is_superuser, User.session_version).where(User.id == user_id))).one()
    return bool(row[0]), bool(row[1]), int(row[2])


async def _private_issue(private: _Private, purpose: AccountTokenPurpose = INVITE, **arguments: Any) -> IssuedToken:
    """A token issued by token_service directly, committed."""
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        issued = await issue_token(session, purpose, **arguments)
        await session.commit()
    return issued


async def _private_consume(private: _Private, token: str, consumed_by_user_id: int) -> None:
    async with AsyncSession(private.engine) as session:
        record = await consume_token(session, token, INVITE, consumed_by_user_id=consumed_by_user_id)
        await session.commit()
    assert record is not None, "Setup: the invitation must be consumed"


async def _private_tokens(private: _Private) -> list[AccountToken]:
    """Every token row of the private instance: this test owns them all."""
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        return list((await session.execute(select(AccountToken).order_by(AccountToken.id))).scalars().all())


async def _private_token_columns(private: _Private) -> list[dict[str, Any]]:
    """Every token row of the private instance as its raw column values, read from the table without the model: what the database holds."""
    async with AsyncSession(private.engine) as session:
        return [dict(row) for row in (await session.execute(select(AccountToken.__table__))).mappings().all()]


async def _invitation_count(private: _Private) -> int:
    return sum(1 for row in await _private_tokens(private) if row.purpose == INVITE.value)


async def _set_mode_row(private: _Private, mode: str) -> None:
    """The ``registration_mode`` row says ``mode``: the seeded row updated, or created when missing."""
    async with AsyncSession(private.engine) as session:
        row = await session.get(GlobalSetting, MODE_KEY)
        if row is None:
            row = GlobalSetting(key=MODE_KEY, value=mode, value_type="string", updated_at=utcnow())
        row.value = mode
        session.add(row)
        await session.commit()


# ============================================================================
# IN-PROCESS: THE LAST ACTIVE ADMINISTRATOR
# ============================================================================


class TestLastActiveAdministrator:
    """«The last active administrator» depends on every account of the instance: a real state only on a private one."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("change", [pytest.param({"is_active": False}, id="deactivate"), pytest.param({"is_superuser": False}, id="demote")])
    async def test_the_last_active_administrator_is_neither_deactivated_nor_demoted(self, private: _Private, change: dict[str, bool]) -> None:
        """UADM-020: root is the only active administrator (another administrator exists, inactive: it does not count); PATCH /users/{root} with the change → 409 LAST_ADMIN; root is as it was, version included, and its session still works."""
        print_section(f"UADM-020: {change} on the last active administrator")
        root, cookie = await _admin(private)
        dormant = await _add_user(private, "dormant", admin=True, active=False)
        await _add_user(private, "member")
        before = await _private_user(private, root.user_id)

        response = await _call(private, "PATCH", f"/users/{root.user_id}", cookie=cookie, json=change)

        violations: list[str] = []
        _expect(violations, _refusal(response) == (409, "LAST_ADMIN"), f"expected 409 LAST_ADMIN, got {response.status_code} {response.text}")
        _expect(violations, await _private_user(private, root.user_id) == before, f"a refused change must change nothing, the version included: {before} → {await _private_user(private, root.user_id)}")
        _expect(violations, (await _call(private, "GET", "/users", cookie=cookie)).status_code == 200, "a refused change must end no session: root must still be signed in as an administrator")
        _expect(violations, await _private_user(private, dormant.user_id) == (False, True, 0), "the inactive administrator must be untouched")
        assert not violations, f"The last active administrator must stay:{_verdict(violations)}"
        print_success("409 LAST_ADMIN, nothing changed")

    @pytest.mark.asyncio
    async def test_the_guard_follows_the_active_administrators(self, private: _Private) -> None:
        """UADM-021: root is the only active administrator. Demoting the inactive administrator → 200 (it removes no active one); promoting the member → 200; deactivating root → 200, the member remains; the member, now the last active administrator, demoting itself → 409 LAST_ADMIN."""
        print_section("UADM-021: the guard counts the active administrators")
        root, cookie = await _admin(private)
        dormant = await _add_user(private, "dormant", admin=True, active=False)
        member = await _add_user(private, "member")

        steps = {
            "demote the inactive administrator": (await _call(private, "PATCH", f"/users/{dormant.user_id}", cookie=cookie, json={"is_superuser": False})).status_code,
            "promote the member": (await _call(private, "PATCH", f"/users/{member.user_id}", cookie=cookie, json={"is_superuser": True})).status_code,
            "deactivate root while the member is an active administrator": (await _call(private, "PATCH", f"/users/{root.user_id}", cookie=cookie, json={"is_active": False})).status_code,
        }
        last = await _call(private, "PATCH", f"/users/{member.user_id}", cookie=await _sign_in(private, member), json={"is_superuser": False})

        flags = {name: (await _private_user(private, account.user_id))[:2] for name, account in (("root", root), ("dormant", dormant), ("member", member))}
        violations: list[str] = []
        _expect(violations, steps == dict.fromkeys(steps, 200), f"each step must be allowed: {steps}")
        _expect(violations, _refusal(last) == (409, "LAST_ADMIN"), f"the member is now the last active administrator: expected 409 LAST_ADMIN, got {last.status_code} {last.text}")
        _expect(violations, flags == {"root": (False, True), "dormant": (False, False), "member": (True, True)}, f"(is_active, is_superuser) afterwards: {flags}")
        assert not violations, f"The guard must count the active administrators, and only them:{_verdict(violations)}"
        print_success("allowed while another active administrator remains, refused for the last one")


# ============================================================================
# IN-PROCESS: THE USER LIMIT AND THE REGISTRATION MODE
# ============================================================================


REACTIVATION_CASES = [
    pytest.param("2", 0, True, id="at-the-limit"),
    pytest.param("3", 1, True, id="an-invitation-holds-the-last-seat"),
    pytest.param("3", 0, False, id="a-seat-left"),
]

INVITATION_LIMIT_CASES = [
    pytest.param("2", 0, BILLING_LINK, (409, 2, 2), id="at-the-limit"),
    pytest.param("1", 0, BILLING_LINK, (409, 1, 2), id="over-the-limit"),
    pytest.param("3", 1, None, (409, 3, 3), id="invitations-hold-the-seats"),
    pytest.param("not-a-number", 0, None, (409, 0, 2), id="an-invalid-limit-closes"),
    pytest.param("3", 0, BILLING_LINK, (201, None, None), id="a-seat-left"),
]

MODE_CASES = [
    pytest.param("open", "row", 201, id="open-by-the-row"),
    pytest.param("invite", "row", 201, id="invite-by-the-row"),
    pytest.param("disabled", "row", 409, id="disabled-by-the-row"),
    pytest.param("open", "variable", 201, id="open-by-the-variable"),
    pytest.param("invite", "variable", 201, id="invite-by-the-variable"),
    pytest.param("disabled", "variable", 409, id="disabled-by-the-variable"),
]


class TestUserLimitAndRegistrationMode:
    """LIBREFOLIO_MAX_USERS, LIBREFOLIO_BILLING_URL, LIBREFOLIO_REGISTRATION and the registration_mode row, on a private instance. Every instance has root (an active administrator) and a member (active): two seats used; an inactive account takes none."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("max_users", "live_invitations", "refused"), REACTIVATION_CASES)
    async def test_a_reactivation_over_the_limit_is_refused_with_the_counts(self, private: _Private, monkeypatch: pytest.MonkeyPatch, max_users: str, live_invitations: int, refused: bool) -> None:
        """UADM-022: PATCH {is_active: true} of an inactive account with no seat left (the live invitations hold seats) → 409 USER_LIMIT_REACHED with limit, used and billing_url, and the account stays inactive; with a seat left → 200, active."""
        print_section(f"UADM-022: reactivation, LIBREFOLIO_MAX_USERS={max_users}, {live_invitations} live invitation(s)")
        root, cookie = await _admin(private)
        await _add_user(private, "member")
        dormant = await _add_user(private, "dormant", active=False)
        for _ in range(live_invitations):
            await _private_issue(private, INVITE, created_by_user_id=root.user_id)
        monkeypatch.setenv(MAX_USERS_VARIABLE, max_users)
        monkeypatch.setenv(BILLING_URL_VARIABLE, BILLING_LINK)

        response = await _call(private, "PATCH", f"/users/{dormant.user_id}", cookie=cookie, json={"is_active": True})

        is_active = (await _private_user(private, dormant.user_id))[0]
        if refused:
            expected = {"error_code": "USER_LIMIT_REACHED", "limit": int(max_users), "used": 2 + live_invitations, "billing_url": BILLING_LINK}
            assert (response.status_code, _counts(response)) == (409, expected), f"expected 409 with {expected}, got {response.status_code} {response.text}"
            assert is_active is False, "a refused reactivation must leave the account inactive"
        else:
            assert (response.status_code, is_active) == (200, True), f"with a seat left the reactivation goes through: {response.status_code} {response.text}, is_active={is_active}"
        print_success(f"{response.status_code}")

    @pytest.mark.asyncio
    async def test_the_limit_blocks_neither_a_promotion_nor_a_deactivation(self, private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-023: two seats used, LIBREFOLIO_MAX_USERS=1 (over the limit): promoting the member → 200, then deactivating it → 200."""
        print_section("UADM-023: over the limit, promotion and deactivation still go through")
        _, cookie = await _admin(private)
        member = await _add_user(private, "member")
        monkeypatch.setenv(MAX_USERS_VARIABLE, "1")

        promote = await _call(private, "PATCH", f"/users/{member.user_id}", cookie=cookie, json={"is_superuser": True})
        deactivate = await _call(private, "PATCH", f"/users/{member.user_id}", cookie=cookie, json={"is_active": False})

        assert (promote.status_code, deactivate.status_code) == (200, 200), f"the limit blocks invitations, open registration and reactivations only: promote {promote.status_code} {promote.text}, deactivate {deactivate.status_code} {deactivate.text}"
        assert (await _private_user(private, member.user_id))[:2] == (False, True), "the member must end up an inactive administrator"
        print_success("200, 200")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("max_users", "live_invitations", "billing", "outcome"), INVITATION_LIMIT_CASES)
    async def test_an_invitation_at_the_limit_is_refused_with_the_counts_and_the_billing_link(self, private: _Private, monkeypatch: pytest.MonkeyPatch, max_users: str, live_invitations: int, billing: Optional[str], outcome: tuple[int, Optional[int], Optional[int]]) -> None:
        """UADM-024: POST /users/invites with no seat left (an invalid LIBREFOLIO_MAX_USERS closes: limit 0) → 409 USER_LIMIT_REACHED with limit, used and billing_url (null without LIBREFOLIO_BILLING_URL), and no invitation issued; with a seat left → 201."""
        print_section(f"UADM-024: an invitation, LIBREFOLIO_MAX_USERS={max_users}, {live_invitations} live invitation(s)")
        root, cookie = await _admin(private)
        await _add_user(private, "member")
        await _add_user(private, "dormant", active=False)
        for _ in range(live_invitations):
            await _private_issue(private, INVITE, created_by_user_id=root.user_id)
        monkeypatch.setenv(MAX_USERS_VARIABLE, max_users)
        if billing:
            monkeypatch.setenv(BILLING_URL_VARIABLE, billing)
        before = await _invitation_count(private)

        response = await _call(private, "POST", "/users/invites", cookie=cookie, json={"grants_admin": False})

        status, limit, used = outcome
        issued = await _invitation_count(private) - before
        if status == 201:
            assert (response.status_code, issued) == (201, 1), f"with a seat left the invitation is issued: {response.status_code} {response.text}, {issued} issued"
            return
        expected = {"error_code": "USER_LIMIT_REACHED", "limit": limit, "used": used, "billing_url": billing}
        assert (response.status_code, _counts(response)) == (409, expected), f"expected 409 with {expected}, got {response.status_code} {response.text}"
        assert issued == 0, f"a refused invitation must issue nothing: {issued} issued"
        print_success(f"409 with {expected}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("mode", "source", "status"), MODE_CASES)
    async def test_an_invitation_is_refused_while_registration_is_disabled(self, private: _Private, monkeypatch: pytest.MonkeyPatch, mode: str, source: str, status: int) -> None:
        """UADM-025: registration disabled — by the row, or by LIBREFOLIO_REGISTRATION over a row that says open — → POST /users/invites 409 REGISTRATION_DISABLED and nothing issued; open or invite (the variable over a disabled row too) → 201."""
        print_section(f"UADM-025: an invitation while registration is {mode}, by the {source}")
        _, cookie = await _admin(private)
        if source == "row":
            await _set_mode_row(private, mode)
        else:
            await _set_mode_row(private, "open" if mode == "disabled" else "disabled")
            monkeypatch.setenv(REGISTRATION_VARIABLE, mode)
        before = await _invitation_count(private)

        response = await _call(private, "POST", "/users/invites", cookie=cookie, json={"grants_admin": True})

        expected = (201, None) if status == 201 else (409, "REGISTRATION_DISABLED")
        assert _refusal(response) == expected, f"registration {mode} by the {source}: expected {expected}, got {response.status_code} {response.text}"
        assert await _invitation_count(private) - before == (1 if status == 201 else 0), "a refused invitation must issue nothing, an accepted one exactly one"
        print_success(f"{expected}")


# ============================================================================
# IN-PROCESS: LINKS, LIFETIMES, WHAT IS LISTED AND COUNTED
# ============================================================================


class TestLinksAndInvitationsInProcess:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("public_url", [pytest.param(None, id="without-a-public-url"), pytest.param(PUBLIC_URL, id="with-a-public-url")])
    async def test_links_carry_the_public_url_when_it_is_set(self, private: _Private, monkeypatch: pytest.MonkeyPatch, public_url: Optional[str]) -> None:
        """UADM-026: the 201 of an invitation and of a reset link: ``path`` is the page with the token, ``url`` is LIBREFOLIO_PUBLIC_URL without its trailing slash plus the path, or null without the variable."""
        print_section(f"UADM-026: links, LIBREFOLIO_PUBLIC_URL={public_url}")
        _, cookie = await _admin(private)
        member = await _add_user(private, "member")
        if public_url:
            monkeypatch.setenv(PUBLIC_URL_VARIABLE, public_url)

        invitation = await _call(private, "POST", "/users/invites", cookie=cookie, json={})
        link = await _call(private, "POST", f"/users/{member.user_id}/password-reset-link", cookie=cookie)

        assert (invitation.status_code, link.status_code) == (201, 201), f"invitation {invitation.status_code} {invitation.text}; reset link {link.status_code} {link.text}"
        origin = PUBLIC_ORIGIN if public_url else None
        violations: list[str] = []
        for label, body, purpose in (("invitation", invitation.json(), INVITE), ("reset link", link.json(), PASSWORD_RESET)):
            violations += [f"{label}: {problem}" for problem in _link_path_violations(body.get("path"), purpose, str(body.get("token")))]
            violations += [f"{label}: {problem}" for problem in _url_violations(body, origin)]
        assert not violations, f"The links must follow LIBREFOLIO_PUBLIC_URL:{_verdict(violations)}"
        print_success(f"url {'built on the public URL' if public_url else 'null'}")

    @pytest.mark.asyncio
    async def test_an_invitation_lives_seven_days_a_reset_link_thirty_minutes_and_only_hashes_are_stored(self, private: _Private) -> None:
        """UADM-027: the invitation is created now and lives 7 days, as asked (admin role, e-mail, its issuer); the reset link expires 30 minutes after it was asked for; each row holds the token's SHA-256, of its purpose and owner, and no column of any token row holds a plaintext."""
        print_section("UADM-027: lifetimes and hashes")
        root, cookie = await _admin(private)
        member = await _add_user(private, "member")

        started = utcnow()
        invitation = await _call(private, "POST", "/users/invites", cookie=cookie, json={"grants_admin": True, "email": "guest@example.com"})
        link = await _call(private, "POST", f"/users/{member.user_id}/password-reset-link", cookie=cookie)
        finished = utcnow()

        assert (invitation.status_code, link.status_code) == (201, 201), f"invitation {invitation.status_code} {invitation.text}; reset link {link.status_code} {link.text}"
        issued, reset = invitation.json(), link.json()
        violations = _issued_invite_violations(issued, grants_admin=True, email="guest@example.com", created_by=root.user_id) + _reset_link_violations(reset)
        assert not violations, f"the 201 bodies break their contract:{_verdict(violations)}"
        created, expires = _instant(issued["invite"]["created_at"]), _instant(reset["expires_at"])
        ttl = DEFAULT_TTL[PASSWORD_RESET]
        _expect(violations, created is not None and started <= created <= finished, f"the invitation must be created now, between {started} and {finished}: {created}")
        _expect(violations, expires is not None and started + ttl <= expires <= finished + ttl, f"the reset link must expire {ttl} after it was asked for, between {started + ttl} and {finished + ttl}: {expires}")
        rows = {row.token_hash: row for row in await _private_tokens(private)}
        invite_row, reset_row = rows.get(hash_token(issued["token"])), rows.get(hash_token(reset["token"]))
        _expect(violations, invite_row is not None and (invite_row.id, invite_row.purpose, invite_row.user_id) == (issued["invite"]["id"], INVITE.value, None), f"the invitation's row must hold its hash: {invite_row}")
        _expect(violations, reset_row is not None and (reset_row.purpose, reset_row.user_id) == (PASSWORD_RESET.value, member.user_id), f"the reset link's row must hold its hash, for the member: {reset_row}")
        stored = [f"{row['id']}.{column}" for row in await _private_token_columns(private) for column, value in row.items() if any(secret in str(value) for secret in (issued["token"], reset["token"]))]
        _expect(violations, stored == [], f"a plaintext token is stored in {stored}")
        assert not violations, f"Lifetimes and storage broke their contract:{_verdict(violations)}"
        print_success("7 days, 30 minutes, hashes only")

    @pytest.mark.asyncio
    async def test_only_live_invitations_are_listed_and_counted_and_every_account_is_listed(self, private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-028: two administrators, a member, an inactive account; invitations live (one from the API, one by the other administrator), revoked, consumed and expired, and a reset link. GET /users/invites lists exactly the two live ones; GET /users exactly the four accounts with their flags; both say usage {used: 3 active + 2 live = 5, max_users: 10, billing_url}; without the variables {used: 5, max_users: null, billing_url: null}."""
        print_section("UADM-028: what is listed and what is counted")
        root, cookie = await _admin(private)
        other = await _add_user(private, "other_admin", admin=True)
        member = await _add_user(private, "member")
        dormant = await _add_user(private, "dormant", active=False)
        live = await _call(private, "POST", "/users/invites", cookie=cookie, json={})
        revoked = await _call(private, "POST", "/users/invites", cookie=cookie, json={})
        assert (live.status_code, revoked.status_code) == (201, 201), f"Setup: {live.status_code} {live.text}; {revoked.status_code} {revoked.text}"
        assert (await _call(private, "DELETE", f"/users/invites/{revoked.json()['invite']['id']}", cookie=cookie)).status_code == 204, "Setup: revoke"
        live_by_other = await _private_issue(private, INVITE, created_by_user_id=other.user_id)
        consumed = await _private_issue(private, INVITE, created_by_user_id=other.user_id)
        await _private_consume(private, consumed.token, member.user_id)
        await _private_issue(private, INVITE, created_by_user_id=other.user_id, now=utcnow() - DEFAULT_TTL[INVITE] - timedelta(minutes=1))
        await _private_issue(private, PASSWORD_RESET, user_id=member.user_id)
        monkeypatch.setenv(MAX_USERS_VARIABLE, "10")
        monkeypatch.setenv(BILLING_URL_VARIABLE, BILLING_LINK)

        invitations = await _call(private, "GET", "/users/invites", cookie=cookie)
        accounts = await _call(private, "GET", "/users", cookie=cookie)
        monkeypatch.delenv(MAX_USERS_VARIABLE)
        monkeypatch.delenv(BILLING_URL_VARIABLE)
        unlimited = await _call(private, "GET", "/users/invites", cookie=cookie)

        assert (invitations.status_code, accounts.status_code, unlimited.status_code) == (200, 200, 200), f"{invitations.text}; {accounts.text}; {unlimited.text}"
        usage = {"used": 5, "max_users": 10, "billing_url": BILLING_LINK}
        violations: list[str] = []
        listed = sorted(item["id"] for item in invitations.json()["items"])
        _expect(violations, listed == sorted([live.json()["invite"]["id"], live_by_other.record.id]), f"GET /users/invites must list the two live invitations only, whoever issued them: {listed}")
        _expect(violations, invitations.json()["usage"] == usage, f"GET /users/invites usage: expected {usage}, got {invitations.json()['usage']}")
        items = {item["id"]: item for item in accounts.json()["items"]}
        _expect(violations, sorted(items) == sorted(account.user_id for account in (root, other, member, dormant)), f"GET /users must list every account, active or not: {sorted(items)}")
        for account, active, superuser in ((root, True, True), (other, True, True), (member, True, False), (dormant, False, False)):
            violations += _user_item_violations(items.get(account.user_id), account, active=active, superuser=superuser)
        _expect(violations, accounts.json()["usage"] == usage, f"GET /users usage: expected {usage}, got {accounts.json()['usage']}")
        _expect(violations, unlimited.json()["usage"] == {"used": 5, "max_users": None, "billing_url": None}, f"without the variables: {unlimited.json()['usage']}")
        assert not violations, f"Listing and usage broke their contract:{_verdict(violations)}"
        print_success("two live invitations listed, four accounts, used 5")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ["expired", "never-issued"])
    async def test_an_expired_or_never_issued_invitation_cannot_be_revoked(self, private: _Private, kind: str) -> None:
        """UADM-029: DELETE /users/invites/{id} of an expired invitation, or of an id never issued → 404, and nothing else is revoked.

        Presence barrier first: a live invitation is revoked with 204. A route that does not exist answers 404 too.
        """
        print_section(f"UADM-029: DELETE an {kind} invitation")
        root, cookie = await _admin(private)
        live = await _private_issue(private, INVITE, created_by_user_id=root.user_id)
        barrier = await _call(private, "DELETE", f"/users/invites/{live.record.id}", cookie=cookie)
        assert barrier.status_code == 204, f"Presence barrier: DELETE of a live invitation must answer 204, or the 404 below proves nothing: {barrier.status_code} {barrier.text}"
        invite_id = NEVER_ISSUED_ID
        if kind == "expired":
            invite_id = (await _private_issue(private, INVITE, created_by_user_id=root.user_id, now=utcnow() - DEFAULT_TTL[INVITE] - timedelta(minutes=1))).record.id
        revoked_before = {row.id for row in await _private_tokens(private) if row.revoked_at is not None}

        response = await _call(private, "DELETE", f"/users/invites/{invite_id}", cookie=cookie)

        assert response.status_code == 404, f"an {kind} invitation is not live: expected 404, got {response.status_code} {response.text}"
        assert {row.id for row in await _private_tokens(private) if row.revoked_at is not None} == revoked_before, "a refused revocation must revoke nothing"
        print_success("404")


# ============================================================================
# IN-PROCESS: STRUCTURED LOGS, AND NO TOKEN IN THEM
# ============================================================================


#: The SQL loggers: they print every statement with its parameters, the stored token_hash included.
SQL_LOGGERS = frozenset({"aiosqlite", "sqlalchemy.engine", "sqlalchemy.pool"})


def _warning_target(node: ast.AST) -> Optional[ast.expr]:
    """The argument of ``logging.getLogger(<argument>).setLevel(logging.WARNING)`` when ``node`` is that call; None otherwise."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "setLevel" and node.args):
        return None
    level, getter = node.args[0], node.func.value
    if not (isinstance(level, ast.Attribute) and level.attr == "WARNING" and isinstance(getter, ast.Call) and getter.args):
        return None
    return getter.args[0] if isinstance(getter.func, ast.Attribute) and getter.func.attr == "getLogger" else None


def _silenced_by_the_app() -> frozenset[str]:
    """The third-party loggers that ``configure_logging`` (``backend/app/logging_config.py``) sets to WARNING, read from its source so that this list cannot drift from it.

    Two forms: ``logging.getLogger("name").setLevel(logging.WARNING)``, and the same call on the variable of a ``for``
    loop over a literal tuple of names.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(logging_config.configure_logging)))
    loops = {node.target.id: [item.value for item in node.iter.elts if isinstance(item, ast.Constant)] for node in ast.walk(tree) if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and isinstance(node.iter, (ast.Tuple, ast.List))}
    names: set[str] = set()
    for node in ast.walk(tree):
        target = _warning_target(node)
        if isinstance(target, ast.Constant) and isinstance(target.value, str):
            names.add(target.value)
        elif isinstance(target, ast.Name):
            names.update(str(name) for name in loops.get(target.id, ()))
    return frozenset(names)


def _is_silenced(logger_name: str, silenced: frozenset[str]) -> bool:
    """Whether a logger is one of ``silenced`` or a child of one: a child inherits the WARNING level."""
    return any(logger_name == name or logger_name.startswith(f"{name}.") for name in silenced)


def _carries(record: logging.LogRecord, secrets: list[str]) -> bool:
    """Whether a stdlib record shows one of ``secrets``, in its message or anywhere among its attributes."""
    shown = record.getMessage() + repr(vars(record))
    return any(secret in shown for secret in secrets)


class TestStructuredLogs:
    @pytest.mark.asyncio
    async def test_every_admin_action_writes_a_structured_event_and_no_log_carries_a_token(self, private: _Private, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """UADM-030: each admin action — an invitation issued and revoked, two reset links, deactivation, reactivation, promotion, demotion, sessions revoked, onboarding reset (all, then one flow) — emits at least one structlog event with a field besides its message. No structlog event and no stdlib record carries a token's plaintext (hence neither its path nor its URL), whatever the logger. No structlog event, and no record of the application's own loggers, carries its hash.

        The hash is the value of the ``token_hash`` column, so the SQL loggers print it among the parameters of the INSERT.
        ``configure_logging`` silences them to WARNING (``backend/app/logging_config.py``), so a running server never emits
        those records: caplog sees them only because it lowers the level. Their names are read from that function's source
        (``_silenced_by_the_app``), and a record of one of them or of a child is left out of the hash check only.

        Barriers first: a canary through the users module's logger name reaches both captures, or a capture that sees
        nothing would pass for endpoints that log nothing.
        """
        print_section("UADM-030: structured logs without tokens")
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
        _, cookie = await _admin(private)
        member = await _add_user(private, "member")
        monkeypatch.setattr(logging.getLogger(users_api.__name__), "disabled", False)
        caplog.set_level(logging.DEBUG)
        caplog.set_level(logging.DEBUG, logger=users_api.__name__)
        actions: dict[str, list[dict[str, Any]]] = {}
        bodies: list[Any] = []

        with capture_logs() as events:
            structlog.get_logger(users_api.__name__).info(CANARY)
            logging.getLogger(users_api.__name__).info(CANARY)

            async def act(label: str, method: str, path: str, body: Any = None, status: int = 200) -> Any:
                start = len(events)
                response = await _call(private, method, path, cookie=cookie, json=body)
                assert response.status_code == status, f"{label}: expected {status}, got {response.status_code} {response.text}"
                actions[label] = list(events[start:])
                bodies.append(response.json() if response.content else None)
                return bodies[-1]

            invitation = await act("issue an invitation", "POST", "/users/invites", {"grants_admin": True, "email": "guest@example.com"}, 201)
            await act("revoke the invitation", "DELETE", f"/users/invites/{invitation['invite']['id']}", None, 204)
            first = await act("issue a reset link", "POST", f"/users/{member.user_id}/password-reset-link", None, 201)
            second = await act("issue another reset link", "POST", f"/users/{member.user_id}/password-reset-link", None, 201)
            await act("deactivate", "PATCH", f"/users/{member.user_id}", {"is_active": False})
            await act("reactivate", "PATCH", f"/users/{member.user_id}", {"is_active": True})
            await act("promote", "PATCH", f"/users/{member.user_id}", {"is_superuser": True})
            await act("demote", "PATCH", f"/users/{member.user_id}", {"is_superuser": False})
            await act("revoke the sessions", "POST", f"/users/{member.user_id}/sessions/revoke", None, 204)
            await act("reset the onboarding", "POST", f"/users/{member.user_id}/onboarding/reset", {}, 204)
            await act("reset one flow", "POST", f"/users/{member.user_id}/onboarding/reset", {"flow": OnboardingFlow.INTRO_TOUR.value}, 204)
            reads = [await _call(private, "GET", path, cookie=cookie) for path in ("/users/invites", "/users")]

        assert any(event.get("event") == CANARY for event in events), "barrier: structlog events of the users module's logger do not reach capture_logs"
        assert any(record.getMessage() == CANARY for record in caplog.records), "barrier: stdlib records of the users module's logger do not reach caplog"
        assert [read.status_code for read in reads] == [200, 200], f"the reads inside the capture: {[read.text for read in reads]}"
        silenced = _silenced_by_the_app()
        assert SQL_LOGGERS <= silenced, f"premise: configure_logging silences the SQL loggers {sorted(SQL_LOGGERS)} to WARNING, as read from its source: {sorted(silenced)}"
        silent = [label for label, captured in actions.items() if not any(set(event) - {"event", "log_level"} for event in captured)]
        tokens = [invitation["token"], first["token"], second["token"]]
        hashes = [hash_token(token) for token in tokens]
        plaintext_events = [event for event in events if any(token in repr(event) for token in tokens)]
        plaintext_records = [f"{record.name}: {record.getMessage()}" for record in caplog.records if _carries(record, tokens)]
        hash_events = [event for event in events if any(digest in repr(event) for digest in hashes)]
        hash_records = [f"{record.name}: {record.getMessage()}" for record in caplog.records if not _is_silenced(record.name, silenced) and _carries(record, hashes)]
        violations: list[str] = []
        _expect(violations, silent == [], f"these actions wrote no structured event: {silent}")
        _expect(violations, plaintext_events == [], f"structlog events carrying a plaintext token: {plaintext_events}")
        _expect(violations, plaintext_records == [], f"stdlib records carrying a plaintext token, whatever the logger: {plaintext_records}")
        _expect(violations, hash_events == [], f"structlog events carrying a token's hash: {hash_events}")
        _expect(violations, hash_records == [], f"records of the application's loggers carrying a token's hash: {hash_records}")
        assert not violations, f"Every admin action logs, and no log carries a token:{_verdict(violations)}"
        print_success(f"{len(actions)} actions logged; {len(events)} events and {len(caplog.records)} records without a plaintext, no hash outside {sorted(SQL_LOGGERS)}")


# ============================================================================
# IN-PROCESS, ON THE MIGRATED SCHEMA: THE HOOK OF LOT A7, THE LOG, A FAILURE (lot A6a)
# ============================================================================


@pytest.fixture(scope="module")
def head_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database taken to head by the real migrations, in a child process, once for the module. Read-only: each test works on a copy."""
    data_dir = tmp_path_factory.mktemp("users-admin-head") / "data"
    db = data_dir / "sqlite" / "app.db"
    _alembic_upgrade_head(db, data_dir)
    return db


@pytest_asyncio.fixture
async def private_head(head_template: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_Private]:
    """A private instance with the schema production has — a copy of the migrated template — and the default settings; no accounts variable; bcrypt at cost 4. Disposed at teardown.

    The BRIM report directory moves under tmp_path: private broker ids start at 1 like the lane's, and the cleanup of a
    deleted private broker would otherwise remove a neighbour's reports.
    """
    for name in ACCOUNTS_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    reports = tmp_path / "broker_reports"
    monkeypatch.setattr(brim_provider, "get_broker_reports_dir", lambda: reports)
    database = tmp_path / "instance.db"
    with contextlib.closing(sqlite3.connect(head_template)) as source, contextlib.closing(sqlite3.connect(database)) as copy:
        source.backup(copy)
    engine = create_async_engine(f"sqlite+aiosqlite:///{database}", poolclass=NullPool)
    try:
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield _Private(engine=engine, app=_private_app(engine))
    finally:
        await engine.dispose()


def _protect(monkeypatch: pytest.MonkeyPatch, *user_ids: int) -> None:
    """Replace the hook of lot A7, a plain function: a reason for the accounts ``user_ids``, None for every other one.

    ``raising=False``: before A6a the hook does not exist, and the red is then the route's answer, not this setup.
    """
    protected = frozenset(user_ids)

    def account_protection(user: User) -> Optional[str]:
        return PROTECTION_REASON if user.id in protected else None

    monkeypatch.setattr(user_service, "account_protection", account_protection, raising=False)


def _spy_on_report_cleanup(monkeypatch: pytest.MonkeyPatch) -> list[list[int]]:
    """Replace delete_files_for_brokers, under both names a caller may reach, by a spy answering FILES_REMOVED; the broker ids of each call."""
    calls: list[list[int]] = []

    def delete_files_for_brokers(broker_ids: Any) -> int:
        calls.append([int(broker_id) for broker_id in broker_ids])
        return FILES_REMOVED

    monkeypatch.setattr(brim_provider, "delete_files_for_brokers", delete_files_for_brokers)
    monkeypatch.setattr(user_service, "delete_files_for_brokers", delete_files_for_brokers, raising=False)
    return calls


async def _private_broker(private: _Private, name: str, grants: list[tuple[int, UserRole]], *, deposits: int = 0) -> int:
    """A broker of the private instance with these grants and DEPOSITs, committed; its id."""
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        broker = Broker(name=name)
        session.add(broker)
        await session.flush()
        session.add_all([_grant(user_id, broker.id, role) for user_id, role in grants])
        session.add_all([_deposit(broker.id) for _ in range(deposits)])
        await session.commit()
    return broker.id


async def _private_holdings(private: _Private) -> dict[str, Any]:
    """Every account (flags and session version), broker, grant and transaction of the private instance: the test owns them all."""
    async with AsyncSession(private.engine) as session:
        accounts = (await session.execute(select(User.username, User.is_active, User.is_superuser, User.session_version))).all()
        brokers = (await session.execute(select(Broker.id, Broker.name))).all()
        grants = (await session.execute(select(BrokerUserAccess.broker_id, BrokerUserAccess.user_id, BrokerUserAccess.role))).all()
        transactions = (await session.execute(select(Transaction.id, Transaction.broker_id, Transaction.related_transaction_id))).all()
    return {
        "accounts": sorted(tuple(row) for row in accounts),
        "brokers": sorted(tuple(row) for row in brokers),
        "grants": sorted((broker_id, user_id, UserRole(role).value) for broker_id, user_id, role in grants),
        "transactions": sorted(tuple(row) for row in transactions),
    }


def _logged(event: dict[str, Any]) -> dict[str, Any]:
    """The fields of an administrator's deletion an event carries, a sequence read as a list."""
    return {key: list(value) if isinstance(value, (list, tuple)) else value for key, value in event.items() if key in ADMIN_DELETION_FIELDS}


async def _failing_delete_bulk(self: BrokerService, *args: Any, **kwargs: Any) -> Any:
    raise RuntimeError("injected technical failure while deleting a broker")


class TestAccountProtectionInProcess:
    """The hook of lot A7, replaced in this process: a reason for one account. root, the caller, is an active administrator the hook never protects."""

    @pytest.mark.asyncio
    async def test_a_protected_account_is_neither_deactivated_nor_demoted(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-050: boss, an active administrator the hook protects: PATCH {is_active: false} and PATCH {is_superuser: false} → 409 ACCOUNT_PROTECTED, and boss is as it was, version included.

        Barrier: the same two calls on peer, an administrator the hook does not protect, → 200. root stays an active
        administrator throughout, so LAST_ADMIN never applies: only the hook can refuse.
        """
        print_section("UADM-050: PATCH on a protected account")
        _, cookie = await _admin(private_head)
        boss = await _add_user(private_head, "boss", admin=True)
        peer = await _add_user(private_head, "peer", admin=True)
        _protect(monkeypatch, boss.user_id)
        before = await _private_user(private_head, boss.user_id)

        deactivate = await _call(private_head, "PATCH", f"/users/{boss.user_id}", cookie=cookie, json={"is_active": False})
        demote = await _call(private_head, "PATCH", f"/users/{boss.user_id}", cookie=cookie, json={"is_superuser": False})
        after = await _private_user(private_head, boss.user_id)
        peer_demoted = await _call(private_head, "PATCH", f"/users/{peer.user_id}", cookie=cookie, json={"is_superuser": False})
        peer_deactivated = await _call(private_head, "PATCH", f"/users/{peer.user_id}", cookie=cookie, json={"is_active": False})

        violations: list[str] = []
        _expect(violations, _refusal(deactivate) == (409, "ACCOUNT_PROTECTED"), f"deactivating a protected account: expected 409 ACCOUNT_PROTECTED, got {deactivate.status_code} {deactivate.text}")
        _expect(violations, _refusal(demote) == (409, "ACCOUNT_PROTECTED"), f"demoting a protected account: expected 409 ACCOUNT_PROTECTED, got {demote.status_code} {demote.text}")
        _expect(violations, after == before, f"a refused change must change nothing, the version included: {before} → {after}")
        _expect(violations, (peer_demoted.status_code, peer_deactivated.status_code) == (200, 200), f"Barrier: the same changes on an administrator the hook does not protect go through: {peer_demoted.status_code} {peer_demoted.text}; {peer_deactivated.status_code} {peer_deactivated.text}")
        _expect(violations, (await _private_user(private_head, peer.user_id))[:2] == (False, False), "the unprotected administrator must end up inactive and demoted")
        assert not violations, f"The hook must stop the deactivation and the demotion of the account it protects:{_verdict(violations)}"
        print_success("409 ACCOUNT_PROTECTED twice, the protected account untouched; the unprotected one changed")

    @pytest.mark.asyncio
    async def test_a_protected_account_is_not_deleted(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-051: patron, an ordinary account the hook protects and the only OWNER of a broker with a DEPOSIT: DELETE → 409 ACCOUNT_PROTECTED; every account, broker, grant and transaction as before, and no report file touched. Barrier: DELETE of other, an ordinary account the hook does not protect, → 204, gone."""
        print_section("UADM-051: DELETE of a protected account")
        _, cookie = await _admin(private_head)
        patron = await _add_user(private_head, "patron")
        other = await _add_user(private_head, "other")
        await _private_broker(private_head, "Patron's broker", [(patron.user_id, UserRole.OWNER)], deposits=1)
        _protect(monkeypatch, patron.user_id)
        calls = _spy_on_report_cleanup(monkeypatch)
        before = await _private_holdings(private_head)

        refused = await _call(private_head, "DELETE", f"/users/{patron.user_id}", cookie=cookie)
        after = await _private_holdings(private_head)
        calls_after_refusal = list(calls)
        allowed = await _call(private_head, "DELETE", f"/users/{other.user_id}", cookie=cookie)
        usernames = [row[0] for row in (await _private_holdings(private_head))["accounts"]]

        violations: list[str] = []
        _expect(violations, _refusal(refused) == (409, "ACCOUNT_PROTECTED"), f"deleting a protected account: expected 409 ACCOUNT_PROTECTED, got {refused.status_code} {refused.text}")
        _expect(violations, after == before, f"a refused deletion must change nothing: before {before}, after {after}")
        _expect(violations, calls_after_refusal == [], f"a refused deletion must touch no report file: {calls_after_refusal}")
        _expect(violations, allowed.status_code == 204 and other.username not in usernames, f"Barrier: an account the hook does not protect is deleted: {allowed.status_code} {allowed.text}, accounts now {usernames}")
        assert not violations, f"The hook must stop the deletion of the account it protects:{_verdict(violations)}"
        print_success("409 ACCOUNT_PROTECTED, everything in place; the unprotected account deleted")

    @pytest.mark.asyncio
    async def test_protected_says_whether_the_hook_gives_a_reason(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-052: the hook protects boss: GET /users lists root, boss and member with exactly their eight fields, ``protected`` true for boss alone; PATCH promoting member answers it with ``protected`` false."""
        print_section("UADM-052: the protected field")
        root, cookie = await _admin(private_head)
        boss = await _add_user(private_head, "boss", admin=True)
        member = await _add_user(private_head, "member")
        _protect(monkeypatch, boss.user_id)

        listed = await _call(private_head, "GET", "/users", cookie=cookie)
        promoted = await _call(private_head, "PATCH", f"/users/{member.user_id}", cookie=cookie, json={"is_superuser": True})

        assert (listed.status_code, promoted.status_code) == (200, 200), f"GET /users {listed.status_code} {listed.text}; PATCH {promoted.status_code} {promoted.text}"
        items = {item.get("id"): item for item in listed.json()["items"]}
        violations = _user_item_violations(items.get(root.user_id), root, active=True, superuser=True)
        violations += _user_item_violations(items.get(boss.user_id), boss, active=True, superuser=True, protected=True)
        violations += _user_item_violations(items.get(member.user_id), member, active=True, superuser=False)
        violations += [f"PATCH: {problem}" for problem in _user_item_violations(promoted.json(), member, active=True, superuser=True)]
        assert not violations, f"protected must say whether the hook gives a reason:{_verdict(violations)}"
        print_success("protected true for the account the hook protects, false for the others")


PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
ADMIN_EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
#: A5-1: the reason the real hook gives for the paying administrator, as ``detail.reason`` carries it: a stable word, written out.
PAYING_ADMINISTRATOR = "paying_administrator"


def _instance(monkeypatch: pytest.MonkeyPatch, *, profile: Optional[str], admin_email: Optional[str]) -> None:
    """Set the profile (None: unset) and ``LIBREFOLIO_ADMIN_EMAIL`` (None: unset) of THIS process, and check that ``get_settings()`` reads the profile.

    Set after the accounts have signed in: only the requests under test see the instance. The real hook is not replaced.
    """
    monkeypatch.delenv(PROFILE_VARIABLE, raising=False)
    monkeypatch.delenv(ADMIN_EMAIL_VARIABLE, raising=False)
    if profile is not None:
        monkeypatch.setenv(PROFILE_VARIABLE, profile)
    if admin_email is not None:
        monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, admin_email)
    expected = profile or "selfhosted"
    resolved = get_settings().LIBREFOLIO_PROFILE
    assert resolved == expected, f"barrier: with {PROFILE_VARIABLE}={profile!r}, get_settings() reads the profile {resolved!r}, not {expected!r}"


async def _listed_protection(private: _Private, cookie: str) -> dict[str, Any]:
    """``username → protected`` for every account GET /users lists (the private instance holds only this case's accounts)."""
    response = await _call(private, "GET", "/users", cookie=cookie)
    assert response.status_code == 200, f"GET /users: {response.status_code} {response.text}"
    return {item["username"]: item.get("protected", "<missing>") for item in response.json()["items"]}


class TestPayingAdministratorProtection:
    """A5-1: the REAL hook (``user_service.account_protection``, not replaced) on a private instance: on a managed instance the account of ``LIBREFOLIO_ADMIN_EMAIL`` is protected. root, the caller, and peer, another administrator, are never the owner's address."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("typed", [pytest.param(None, id="same-case"), pytest.param("upper", id="variable-in-upper-case")])
    async def test_the_paying_administrator_is_neither_deactivated_demoted_nor_deleted(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, typed: Optional[str]) -> None:
        """UADM-A51-01: managed, ``LIBREFOLIO_ADMIN_EMAIL`` = owner's address (also in another A–Z case): PATCH {is_active: false}, PATCH {is_superuser: false} and DELETE on owner, an active administrator → 409 ACCOUNT_PROTECTED, ``detail.reason`` ``paying_administrator``, and owner is as it was, version included, and still signed in. Barrier: GET /users says protected for owner before the calls."""
        print_section(f"UADM-A51-01: the owner is protected ({typed or 'same case'})")
        root, cookie = await _admin(private_head)
        owner = await _add_user(private_head, "a51_owner", admin=True)
        owner_cookie = await _sign_in(private_head, owner)
        written = owner.email.upper() if typed == "upper" else owner.email
        _instance(monkeypatch, profile="managed", admin_email=written)
        assert (await _listed_protection(private_head, cookie)).get(owner.username) is True, "Barrier: the owner must be listed as protected, or the 409s below prove nothing"
        before = await _private_user(private_head, owner.user_id)
        holdings = await _private_holdings(private_head)

        answers = {
            "deactivate": await _call(private_head, "PATCH", f"/users/{owner.user_id}", cookie=cookie, json={"is_active": False}),
            "demote": await _call(private_head, "PATCH", f"/users/{owner.user_id}", cookie=cookie, json={"is_superuser": False}),
            "delete": await _call(private_head, "DELETE", f"/users/{owner.user_id}", cookie=cookie),
        }
        after = await _private_user(private_head, owner.user_id)

        violations: list[str] = []
        for label, response in answers.items():
            _expect(violations, _refusal(response) == (409, "ACCOUNT_PROTECTED"), f"{label}: expected 409 ACCOUNT_PROTECTED, got {response.status_code} {response.text}")
            _expect(violations, _detail(response).get("reason") == PAYING_ADMINISTRATOR, f"{label}: detail.reason must be {PAYING_ADMINISTRATOR!r}: {_detail(response)}")
        _expect(violations, after == before, f"a refused change must change nothing, the version included: {before} → {after}")
        _expect(violations, await _private_holdings(private_head) == holdings, "a refused change must change no account, broker, grant or transaction")
        _expect(violations, (await _call(private_head, "GET", "/users", cookie=owner_cookie)).status_code == 200, "the owner must still be signed in as an administrator")
        assert not violations, f"The paying administrator must stay:{_verdict(violations)}"
        print_success("409 ACCOUNT_PROTECTED × 3 with the reason; the owner untouched")

    @pytest.mark.asyncio
    async def test_protection_is_by_email_alone_an_ordinary_account_too(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-A51-02: managed, the variable = the address of keeper, an ORDINARY (non-administrator) account: DELETE → 409 ACCOUNT_PROTECTED, PATCH {is_active: false} → 409; keeper is as it was. Barrier: the same two calls on member, another ordinary account, go through (200, 204)."""
        print_section("UADM-A51-02: by email, administrator or not")
        _, cookie = await _admin(private_head)
        keeper = await _add_user(private_head, "a51_keeper")
        member = await _add_user(private_head, "a51_member")
        _instance(monkeypatch, profile="managed", admin_email=keeper.email)
        before = await _private_user(private_head, keeper.user_id)

        deactivate = await _call(private_head, "PATCH", f"/users/{keeper.user_id}", cookie=cookie, json={"is_active": False})
        delete = await _call(private_head, "DELETE", f"/users/{keeper.user_id}", cookie=cookie)
        after = await _private_user(private_head, keeper.user_id)
        member_deactivated = await _call(private_head, "PATCH", f"/users/{member.user_id}", cookie=cookie, json={"is_active": False})
        member_deleted = await _call(private_head, "DELETE", f"/users/{member.user_id}", cookie=cookie)

        violations: list[str] = []
        _expect(violations, _refusal(deactivate) == (409, "ACCOUNT_PROTECTED"), f"deactivate: expected 409 ACCOUNT_PROTECTED, got {deactivate.status_code} {deactivate.text}")
        _expect(violations, _refusal(delete) == (409, "ACCOUNT_PROTECTED"), f"delete: expected 409 ACCOUNT_PROTECTED, got {delete.status_code} {delete.text}")
        _expect(violations, after == before, f"nothing may change: {before} → {after}")
        _expect(violations, (member_deactivated.status_code, member_deleted.status_code) == (200, 204), f"Barrier: another ordinary account is deactivated and deleted: {member_deactivated.status_code} {member_deactivated.text}; {member_deleted.status_code} {member_deleted.text}")
        assert not violations, f"The protection is by email alone:{_verdict(violations)}"
        print_success("an ordinary account protected too; the neighbour removable")

    @pytest.mark.asyncio
    async def test_only_the_paying_administrator_is_listed_protected_and_the_answer_says_so(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-A51-03: managed: GET /users lists owner with ``protected`` true and root, peer and member with false, exactly their fields; a PATCH that changes nothing on owner ({is_active: true}) → 200 with ``protected`` true; PATCH promoting member → 200 with ``protected`` false."""
        print_section("UADM-A51-03: the protected field")
        root, cookie = await _admin(private_head)
        owner = await _add_user(private_head, "a51_owner", admin=True)
        peer = await _add_user(private_head, "a51_peer", admin=True)
        member = await _add_user(private_head, "a51_member")
        _instance(monkeypatch, profile="managed", admin_email=owner.email)

        listed = await _call(private_head, "GET", "/users", cookie=cookie)
        harmless = await _call(private_head, "PATCH", f"/users/{owner.user_id}", cookie=cookie, json={"is_active": True})
        promoted = await _call(private_head, "PATCH", f"/users/{member.user_id}", cookie=cookie, json={"is_superuser": True})

        assert (listed.status_code, harmless.status_code, promoted.status_code) == (200, 200, 200), f"GET /users {listed.status_code} {listed.text}; harmless PATCH {harmless.status_code} {harmless.text}; promote {promoted.status_code} {promoted.text}"
        items = {item.get("id"): item for item in listed.json()["items"]}
        violations = _user_item_violations(items.get(root.user_id), root, active=True, superuser=True)
        violations += _user_item_violations(items.get(owner.user_id), owner, active=True, superuser=True, protected=True)
        violations += _user_item_violations(items.get(peer.user_id), peer, active=True, superuser=True)
        violations += _user_item_violations(items.get(member.user_id), member, active=True, superuser=False)
        violations += [f"harmless PATCH: {problem}" for problem in _user_item_violations(harmless.json(), owner, active=True, superuser=True, protected=True)]
        violations += [f"promote PATCH: {problem}" for problem in _user_item_violations(promoted.json(), member, active=True, superuser=True)]
        assert not violations, f"protected must be true for the paying administrator alone:{_verdict(violations)}"
        print_success("protected true for the owner alone, in the list and in the answer of a PATCH")

    @pytest.mark.asyncio
    async def test_another_administrator_is_still_removable(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-A51-04: managed, the variable = owner's address: peer, an administrator of another address, is demoted (200), deactivated (200) and deleted (204), as without protection; the owner is untouched throughout."""
        print_section("UADM-A51-04: another administrator is removable")
        _, cookie = await _admin(private_head)
        owner = await _add_user(private_head, "a51_owner", admin=True)
        peer = await _add_user(private_head, "a51_peer", admin=True)
        _instance(monkeypatch, profile="managed", admin_email=owner.email)
        owner_before = await _private_user(private_head, owner.user_id)

        demoted = await _call(private_head, "PATCH", f"/users/{peer.user_id}", cookie=cookie, json={"is_superuser": False})
        deactivated = await _call(private_head, "PATCH", f"/users/{peer.user_id}", cookie=cookie, json={"is_active": False})
        deleted = await _call(private_head, "DELETE", f"/users/{peer.user_id}", cookie=cookie)
        usernames = await _listed_protection(private_head, cookie)

        violations: list[str] = []
        _expect(violations, (demoted.status_code, deactivated.status_code, deleted.status_code) == (200, 200, 204), f"expected 200, 200, 204, got {demoted.status_code} {demoted.text}; {deactivated.status_code} {deactivated.text}; {deleted.status_code} {deleted.text}")
        _expect(violations, peer.username not in usernames, f"peer must be gone: {sorted(usernames)}")
        _expect(violations, await _private_user(private_head, owner.user_id) == owner_before, "the owner must be untouched")
        assert not violations, f"Only the paying administrator is protected:{_verdict(violations)}"
        print_success("peer demoted, deactivated and deleted")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("profile", [pytest.param(None, id="profile-unset"), pytest.param("selfhosted", id="selfhosted")])
    async def test_another_profile_protects_nobody_with_the_same_variable(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, profile: Optional[str]) -> None:
        """UADM-A51-05: regression zero — the default (selfhosted) profile with ``LIBREFOLIO_ADMIN_EMAIL`` = owner's address: GET /users lists every account ``protected`` false, and owner is demoted (200), deactivated (200) and deleted (204) like any other (root stays the active administrator)."""
        print_section(f"UADM-A51-05: profile {profile or 'unset'}, same variable")
        _, cookie = await _admin(private_head)
        owner = await _add_user(private_head, "a51_owner", admin=True)
        _instance(monkeypatch, profile=profile, admin_email=owner.email)

        listed = await _listed_protection(private_head, cookie)
        demoted = await _call(private_head, "PATCH", f"/users/{owner.user_id}", cookie=cookie, json={"is_superuser": False})
        deactivated = await _call(private_head, "PATCH", f"/users/{owner.user_id}", cookie=cookie, json={"is_active": False})
        deleted = await _call(private_head, "DELETE", f"/users/{owner.user_id}", cookie=cookie)

        violations: list[str] = []
        _expect(violations, owner.username in listed, f"Barrier: the owner must be listed: {sorted(listed)}")
        _expect(violations, [name for name, flag in listed.items() if flag is not False] == [], f"nobody is protected outside the managed profile: {listed}")
        _expect(violations, (demoted.status_code, deactivated.status_code, deleted.status_code) == (200, 200, 204), f"expected 200, 200, 204, got {demoted.status_code} {demoted.text}; {deactivated.status_code} {deactivated.text}; {deleted.status_code} {deleted.text}")
        assert not violations, f"Outside the managed profile nothing changes:{_verdict(violations)}"
        print_success("nobody protected, the owner removable")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("written", [pytest.param(None, id="unset"), pytest.param("", id="empty"), pytest.param("   ", id="blank"), pytest.param("not-an-address", id="not-an-address")])
    async def test_managed_without_a_usable_variable_protects_nobody(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, written: Optional[str]) -> None:
        """UADM-A51-06: managed, ``LIBREFOLIO_ADMIN_EMAIL`` unset, blank or not an address: GET /users answers 200 (the hook raises nothing) with every account ``protected`` false, and an administrator of any address is demoted (200)."""
        print_section(f"UADM-A51-06: managed, the variable {written!r}")
        _, cookie = await _admin(private_head)
        peer = await _add_user(private_head, "a51_peer", admin=True)
        _instance(monkeypatch, profile="managed", admin_email=written)

        listed = await _listed_protection(private_head, cookie)
        demoted = await _call(private_head, "PATCH", f"/users/{peer.user_id}", cookie=cookie, json={"is_superuser": False})

        assert peer.username in listed, f"Barrier: peer must be listed: {sorted(listed)}"
        assert [name for name, flag in listed.items() if flag is not False] == [], f"managed with {written!r}: nobody is protected: {listed}"
        assert demoted.status_code == 200, f"demoting peer: {demoted.status_code} {demoted.text}"
        print_success("nobody protected, nothing raised")


#: A5-1 extension (developer decision, 23/10): the four more paths the paying administrator is protected on, and what each answers.
PROTECTED_ELSEWHERE_MESSAGE = "This account is protected: ask the host of this instance if something has to change"
PROTECTED_DELETION_MESSAGE = "This account cannot be deleted from here: ask the host of this instance"
PROTECTED_EMAIL_MESSAGE = "The email address of this account can only be changed by the host of this instance"
OWNER_NEW_PASSWORD = "Owner-Changed-2026"


@dataclass(frozen=True)
class _A51Scene:
    """root (an administrator, the caller), owner (the paying administrator, an administrator), peer (another administrator) and member (an ordinary account) of one private instance, all signed in, the instance already set to its profile and variable."""

    root: _Account
    root_cookie: str
    owner: _Account
    owner_cookie: str
    peer: _Account
    peer_cookie: str
    member: _Account
    member_cookie: str


async def _a51_scene(private: _Private, monkeypatch: pytest.MonkeyPatch, profile: Optional[str]) -> _A51Scene:
    """The four accounts signed in, then the profile ``profile`` (None: unset) and ``LIBREFOLIO_ADMIN_EMAIL`` = owner's address set in this process."""
    root, root_cookie = await _admin(private)
    owner = await _add_user(private, "a51_owner", admin=True)
    peer = await _add_user(private, "a51_peer", admin=True)
    member = await _add_user(private, "a51_member")
    cookies = [await _sign_in(private, account) for account in (owner, peer, member)]
    _instance(monkeypatch, profile=profile, admin_email=owner.email)
    return _A51Scene(root, root_cookie, owner, cookies[0], peer, cookies[1], member, cookies[2])


def _protected_refusal_violations(response: httpx.Response, message: str, label: str) -> list[str]:
    """409 with ``error_code`` ACCOUNT_PROTECTED, the reason of the paying administrator and exactly ``message``."""
    detail = _detail(response)
    violations: list[str] = []
    _expect(violations, response.status_code == 409 and detail.get("error_code") == "ACCOUNT_PROTECTED", f"{label}: expected 409 ACCOUNT_PROTECTED, got {response.status_code} {response.text}")
    _expect(violations, detail.get("reason") == PAYING_ADMINISTRATOR, f"{label}: detail.reason must be {PAYING_ADMINISTRATOR!r}: {detail}")
    _expect(violations, detail.get("message") == message, f"{label}: detail.message must be {message!r}: {detail}")
    return violations


async def _profile_of(private: _Private, user_id: int) -> tuple[str, str, int]:
    """(username, email, session_version) of an account, read fresh."""
    async with AsyncSession(private.engine) as session:
        row = (await session.execute(select(User.username, User.email, User.session_version).where(User.id == user_id))).one()
    return str(row[0]), str(row[1]), int(row[2])


NOT_MANAGED = [pytest.param(None, id="profile-unset"), pytest.param("selfhosted", id="selfhosted")]


class TestPayingAdministratorOtherPaths:
    """A5-1 extension: the REAL hook on four more paths — an administrator's reset link and sessions revoke for the owner, the owner's own deletion and email change. Managed: refused with 409 ACCOUNT_PROTECTED. Anyone else, and any other profile: as today."""

    @pytest.mark.asyncio
    async def test_nobody_creates_a_reset_link_for_the_paying_administrator(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-A51-10: managed: root POST /users/{owner}/password-reset-link → 409 ACCOUNT_PROTECTED (reason, message), and every token row is as it was: none issued, the live reset link the owner already had not revoked. Barrier: the same call for peer and for member → 201."""
        print_section("UADM-A51-10: no reset link for the owner")
        private = private_head
        scene = await _a51_scene(private, monkeypatch, "managed")
        await _private_issue(private, PASSWORD_RESET, user_id=scene.owner.user_id)
        before = await _private_token_columns(private)

        refused = await _call(private, "POST", f"/users/{scene.owner.user_id}/password-reset-link", cookie=scene.root_cookie)
        after = await _private_token_columns(private)
        allowed = [await _call(private, "POST", f"/users/{account.user_id}/password-reset-link", cookie=scene.root_cookie) for account in (scene.peer, scene.member)]

        violations = _protected_refusal_violations(refused, PROTECTED_ELSEWHERE_MESSAGE, "reset link for the owner")
        _expect(violations, after == before, f"a refused link must change no token row: {before} → {after}")
        _expect(violations, [response.status_code for response in allowed] == [201, 201], f"Barrier: peer and member get their link: {[(r.status_code, r.text) for r in allowed]}")
        assert not violations, f"The owner's password is not reset by another administrator:{_verdict(violations)}"
        print_success("409, no token touched; peer and member 201")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("profile", NOT_MANAGED)
    async def test_outside_managed_the_reset_link_for_that_address_is_issued(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, profile: Optional[str]) -> None:
        """UADM-A51-11: regression zero — selfhosted (or unset) with the variable = owner's address: POST /users/{owner}/password-reset-link → 201."""
        scene = await _a51_scene(private_head, monkeypatch, profile)
        response = await _call(private_head, "POST", f"/users/{scene.owner.user_id}/password-reset-link", cookie=scene.root_cookie)
        assert response.status_code == 201, f"outside managed the link is issued: {response.status_code} {response.text}"

    @pytest.mark.asyncio
    async def test_nobody_ends_the_sessions_of_the_paying_administrator(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-A51-12: managed: root POST /users/{owner}/sessions/revoke → 409 ACCOUNT_PROTECTED (reason, message); the owner's session_version is as it was and its session still works. Barrier: the same call for peer → 204 and its version rises, its old session is refused."""
        print_section("UADM-A51-12: no sessions revoke for the owner")
        private = private_head
        scene = await _a51_scene(private, monkeypatch, "managed")
        before = await _private_user(private, scene.owner.user_id)

        refused = await _call(private, "POST", f"/users/{scene.owner.user_id}/sessions/revoke", cookie=scene.root_cookie)
        after = await _private_user(private, scene.owner.user_id)
        still = await _call(private, "GET", "/users", cookie=scene.owner_cookie)
        peer_before = await _private_user(private, scene.peer.user_id)
        allowed = await _call(private, "POST", f"/users/{scene.peer.user_id}/sessions/revoke", cookie=scene.root_cookie)
        peer_after = await _private_user(private, scene.peer.user_id)

        violations = _protected_refusal_violations(refused, PROTECTED_ELSEWHERE_MESSAGE, "sessions revoke for the owner")
        _expect(violations, after == before, f"no session_version may change: {before} → {after}")
        _expect(violations, still.status_code == 200, f"the owner's session must still work: {still.status_code}")
        _expect(violations, allowed.status_code == 204 and peer_after[2] > peer_before[2], f"Barrier: peer's sessions end: {allowed.status_code} {allowed.text}, version {peer_before[2]} → {peer_after[2]}")
        assert not violations, f"The owner's sessions are not closed by another administrator:{_verdict(violations)}"
        print_success("409, version unchanged; peer 204")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("profile", NOT_MANAGED)
    async def test_outside_managed_the_sessions_of_that_address_end(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, profile: Optional[str]) -> None:
        """UADM-A51-13: regression zero — selfhosted (or unset): POST /users/{owner}/sessions/revoke → 204 and the version rises."""
        scene = await _a51_scene(private_head, monkeypatch, profile)
        before = await _private_user(private_head, scene.owner.user_id)
        response = await _call(private_head, "POST", f"/users/{scene.owner.user_id}/sessions/revoke", cookie=scene.root_cookie)
        after = await _private_user(private_head, scene.owner.user_id)
        assert response.status_code == 204 and after[2] > before[2], f"outside managed the sessions end: {response.status_code} {response.text}, version {before[2]} → {after[2]}"

    @pytest.mark.asyncio
    async def test_the_paying_administrator_does_not_delete_its_own_account(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-A51-14: managed: DELETE /auth/users/me by the owner → 409 ACCOUNT_PROTECTED (reason, message) BEFORE the last-administrator rule: the owner is made the only active administrator (root and peer deactivated), where an unprotected one would hear 400 LAST_ADMIN; the account is still there and its session works. Barrier: member DELETE /auth/users/me → 200."""
        print_section("UADM-A51-14: the owner does not delete itself")
        private = private_head
        scene = await _a51_scene(private, monkeypatch, "managed")
        for account in (scene.root, scene.peer):
            async with AsyncSession(private.engine) as session:
                row = await session.get(User, account.user_id)
                row.is_active = False
                session.add(row)
                await session.commit()
        before = await _private_holdings(private)

        refused = await _call(private, "DELETE", "/auth/users/me", cookie=scene.owner_cookie)
        after = await _private_holdings(private)
        still = await _call(private, "GET", "/auth/me", cookie=scene.owner_cookie)
        allowed = await _call(private, "DELETE", "/auth/users/me", cookie=scene.member_cookie)

        violations = _protected_refusal_violations(refused, PROTECTED_DELETION_MESSAGE, "own deletion of the owner")
        _expect(violations, after == before, "a refused deletion must change nothing")
        _expect(violations, still.status_code == 200, f"the owner's session must be intact: {still.status_code} {still.text}")
        _expect(violations, allowed.status_code == 200, f"Barrier: an ordinary account deletes itself: {allowed.status_code} {allowed.text}")
        assert not violations, f"The paying administrator cannot delete itself:{_verdict(violations)}"
        print_success("409 before LAST_ADMIN; member 200")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("profile", NOT_MANAGED)
    async def test_outside_managed_that_address_deletes_itself(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, profile: Optional[str]) -> None:
        """UADM-A51-15: regression zero — selfhosted (or unset), the variable = owner's address: DELETE /auth/users/me by the owner (root is another active administrator) → 200, gone."""
        scene = await _a51_scene(private_head, monkeypatch, profile)
        response = await _call(private_head, "DELETE", "/auth/users/me", cookie=scene.owner_cookie)
        usernames = [row[0] for row in (await _private_holdings(private_head))["accounts"]]
        assert response.status_code == 200 and scene.owner.username not in usernames, f"outside managed the owner deletes itself: {response.status_code} {response.text}, accounts {usernames}"

    @pytest.mark.asyncio
    async def test_the_paying_administrator_does_not_change_its_email(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-A51-16: managed: PUT /auth/profile by the owner with a NEW email → 409 ACCOUNT_PROTECTED (reason, message) whatever the password — none given, a wrong one, the right one —, before the password is looked at: no failure recorded in the login throttle, no 400 CURRENT_PASSWORD_*; with a new username as well → 409 and the username unchanged; nothing changed on the server (username, email, session_version). Then, allowed: the username alone → 200; the same address in another case → 200 (no change of address); an unchanged email with a new username → 200."""
        print_section("UADM-A51-16: the owner does not change its email")
        private = private_head
        scene = await _a51_scene(private, monkeypatch, "managed")
        failures: list[tuple[Any, ...]] = []
        monkeypatch.setattr(auth_api.login_throttle, "record_failure", lambda *arguments: failures.append(arguments))
        before = await _profile_of(private, scene.owner.user_id)
        new_email = "a51_owner_moved@example.com"
        bodies = {
            "no password": {"email": new_email},
            "a wrong password": {"email": new_email, "current_password": "Not-The-Password-1"},
            "the right password": {"email": new_email, "current_password": PRIVATE_PASSWORD},
            "a new username too": {"username": "a51_owner_renamed", "email": new_email, "current_password": PRIVATE_PASSWORD},
        }

        answers = {label: await _call(private, "PUT", "/auth/profile", cookie=scene.owner_cookie, json=body) for label, body in bodies.items()}
        after = await _profile_of(private, scene.owner.user_id)

        violations: list[str] = []
        for label, response in answers.items():
            violations += _protected_refusal_violations(response, PROTECTED_EMAIL_MESSAGE, f"email change with {label}")
        _expect(violations, after == before, f"a refused change must change nothing: {before} → {after}")
        _expect(violations, failures == [], f"the owner must not be counted against the password limit: {failures}")
        renamed = await _call(private, "PUT", "/auth/profile", cookie=scene.owner_cookie, json={"username": "a51_owner_renamed"})
        recased = await _call(private, "PUT", "/auth/profile", cookie=scene.owner_cookie, json={"email": scene.owner.email.upper()})
        unchanged = await _call(private, "PUT", "/auth/profile", cookie=scene.owner_cookie, json={"username": "a51_owner_again", "email": scene.owner.email})
        _expect(
            violations,
            (renamed.status_code, recased.status_code, unchanged.status_code) == (200, 200, 200),
            f"the username alone, the same address in another case and a new username with the same email are allowed: {renamed.status_code} {renamed.text}; {recased.status_code} {recased.text}; {unchanged.status_code} {unchanged.text}",
        )
        _expect(violations, (await _profile_of(private, scene.owner.user_id))[0] == "a51_owner_again", "the username must have changed")
        assert not violations, f"The paying administrator's email is the host's to change:{_verdict(violations)}"
        print_success("409 four times before the password; username, case and unchanged email 200")

    @pytest.mark.asyncio
    async def test_another_account_still_changes_its_email_in_managed(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-A51-17: managed: peer (an administrator of another address) and member change their email with the right password → 200, and the address is the new one."""
        scene = await _a51_scene(private_head, monkeypatch, "managed")
        results = {}
        for account, cookie in ((scene.peer, scene.peer_cookie), (scene.member, scene.member_cookie)):
            new_email = f"moved_{account.username}@example.com"
            response = await _call(private_head, "PUT", "/auth/profile", cookie=cookie, json={"email": new_email, "current_password": PRIVATE_PASSWORD})
            results[account.username] = (response.status_code, (await _profile_of(private_head, account.user_id))[1] == new_email)
        assert results == {"a51_peer": (200, True), "a51_member": (200, True)}, f"others change their email as before: {results}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("profile", NOT_MANAGED)
    async def test_outside_managed_that_address_changes_its_email(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, profile: Optional[str]) -> None:
        """UADM-A51-18: regression zero — selfhosted (or unset): the owner changes its email with the right password → 200; without a password → 400 CURRENT_PASSWORD_REQUIRED, as today."""
        scene = await _a51_scene(private_head, monkeypatch, profile)
        new_email = "a51_owner_moved@example.com"
        missing = await _call(private_head, "PUT", "/auth/profile", cookie=scene.owner_cookie, json={"email": new_email})
        changed = await _call(private_head, "PUT", "/auth/profile", cookie=scene.owner_cookie, json={"email": new_email, "current_password": PRIVATE_PASSWORD})
        assert (missing.status_code, _detail(missing).get("error_code")) == (400, "CURRENT_PASSWORD_REQUIRED"), f"without a password: {missing.status_code} {missing.text}"
        assert changed.status_code == 200 and (await _profile_of(private_head, scene.owner.user_id))[1] == new_email, f"with it the address changes: {changed.status_code} {changed.text}"

    @pytest.mark.asyncio
    async def test_the_paying_administrator_still_changes_and_recovers_its_password(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-A51-19: managed: the owner changes its password (POST /auth/change-password → 200) and, holding a reset link (the forgotten-password flow, issued by the service), sets a new one with POST /auth/password-reset → 200, and signs in with it."""
        print_section("UADM-A51-19: change-password and password-reset stay open")
        private = private_head
        scene = await _a51_scene(private, monkeypatch, "managed")
        assert (await _listed_protection(private, scene.root_cookie)).get(scene.owner.username) is True, "Barrier: the owner is protected"

        changed = await _call(private, "POST", "/auth/change-password", cookie=scene.owner_cookie, json={"current_password": PRIVATE_PASSWORD, "new_password": OWNER_NEW_PASSWORD})
        link = await _private_issue(private, PASSWORD_RESET, user_id=scene.owner.user_id)
        reset = await _call(private, "POST", "/auth/password-reset", json={"token": link.token, "new_password": NEW_PASSWORD})
        signed = await _call(private, "POST", "/auth/login", json={"username": scene.owner.username, "password": NEW_PASSWORD})

        assert (changed.status_code, reset.status_code, signed.status_code) == (200, 200, 200), f"change-password {changed.status_code} {changed.text}; password-reset {reset.status_code} {reset.text}; sign-in {signed.status_code} {signed.text}"


class TestAccountDeletionInProcess:
    """DELETE /users/{id} on a private instance with the production schema: what only this process can see — its log, an injected failure."""

    @pytest.mark.asyncio
    async def test_the_deletion_logs_one_structured_event_and_no_token_nor_password(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """UADM-053: root deletes leaver, the only OWNER of one broker and a co-OWNER of another with partner: 204; exactly one structlog event «Account deleted by an administrator» with user_id, username, admin_id, brokers_deleted [leaver's own broker] and files_removed (what the report cleanup answered); the cleanup ran once, for that broker; no structlog event and no stdlib record, whatever the logger, carries a session token (root's or leaver's) or the password; leaver and its own broker are gone, the shared broker stays.

        Barriers first, as UADM-030: a canary through the users module's logger name reaches both captures.
        """
        print_section("UADM-053: the administrator's deletion, in the log")
        root, root_cookie = await _admin(private_head)
        leaver = await _add_user(private_head, "leaver")
        partner = await _add_user(private_head, "partner")
        leaver_cookie = await _sign_in(private_head, leaver)
        sole = await _private_broker(private_head, "Leaver's broker", [(leaver.user_id, UserRole.OWNER)], deposits=1)
        shared = await _private_broker(private_head, "Shared broker", [(leaver.user_id, UserRole.OWNER), (partner.user_id, UserRole.OWNER)], deposits=1)
        calls = _spy_on_report_cleanup(monkeypatch)
        monkeypatch.setattr(logging.getLogger(users_api.__name__), "disabled", False)
        caplog.set_level(logging.DEBUG)
        caplog.set_level(logging.DEBUG, logger=users_api.__name__)

        with capture_logs() as events:
            structlog.get_logger(users_api.__name__).info(CANARY)
            logging.getLogger(users_api.__name__).info(CANARY)
            response = await _call(private_head, "DELETE", f"/users/{leaver.user_id}", cookie=root_cookie)

        assert any(event.get("event") == CANARY for event in events), "barrier: structlog events of the users module's logger do not reach capture_logs"
        assert any(record.getMessage() == CANARY for record in caplog.records), "barrier: stdlib records of the users module's logger do not reach caplog"
        holdings = await _private_holdings(private_head)
        deletions = [_logged(event) for event in events if event.get("event") == ADMIN_DELETION_EVENT]
        expected = {"user_id": leaver.user_id, "username": leaver.username, "admin_id": root.user_id, "brokers_deleted": [sole], "files_removed": FILES_REMOVED}
        secrets = [root_cookie, leaver_cookie, PRIVATE_PASSWORD]
        secret_events = [event for event in events if any(secret in repr(event) for secret in secrets)]
        secret_records = [f"{record.name}: {record.getMessage()}" for record in caplog.records if _carries(record, secrets)]
        violations: list[str] = []
        _expect(violations, (response.status_code, response.content) == (204, b""), f"expected 204 with no body, got {response.status_code} {response.text}")
        _expect(violations, deletions == [expected], f"exactly one «{ADMIN_DELETION_EVENT}» event with {expected}: {deletions}")
        _expect(violations, calls == [[sole]], f"the report files of the deleted broker must be removed once: {calls}")
        _expect(violations, secret_events == [], f"structlog events carrying a session token or the password: {secret_events}")
        _expect(violations, secret_records == [], f"stdlib records carrying a session token or the password: {secret_records}")
        _expect(violations, leaver.username not in [row[0] for row in holdings["accounts"]] and [row[0] for row in holdings["brokers"]] == [shared], f"leaver and its own broker must be gone, the shared broker left: {holdings}")
        assert not violations, f"The administrator's deletion must log one event, without secrets:{_verdict(violations)}"
        print_success("one structured event with the five fields, no token, no password")

    @pytest.mark.asyncio
    async def test_a_technical_failure_answers_500_and_deletes_nothing(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-054: BrokerService.delete_bulk raises when the deletion reaches leaver's own broker — the shared broker, of a lower id, is already left inside the transaction: DELETE → 500 «nothing was deleted», as for one's own account; every account, broker, grant and transaction as before, and no report file touched."""
        print_section("UADM-054: a technical failure deletes nothing")
        _, cookie = await _admin(private_head)
        leaver = await _add_user(private_head, "leaver")
        partner = await _add_user(private_head, "partner")
        await _private_broker(private_head, "Shared broker", [(leaver.user_id, UserRole.OWNER), (partner.user_id, UserRole.OWNER)], deposits=1)
        await _private_broker(private_head, "Leaver's broker", [(leaver.user_id, UserRole.OWNER)], deposits=1)
        calls = _spy_on_report_cleanup(monkeypatch)
        monkeypatch.setattr(BrokerService, "delete_bulk", _failing_delete_bulk)
        before = await _private_holdings(private_head)

        response = await _call(private_head, "DELETE", f"/users/{leaver.user_id}", cookie=cookie)

        after = await _private_holdings(private_head)
        status, body = _answer(response)
        violations: list[str] = []
        _expect(violations, status == 500 and NOTHING_WAS_DELETED in str(body), f"expected 500 saying «{NOTHING_WAS_DELETED}», got {status} {body}")
        _expect(violations, after == before, f"a failed deletion must change nothing: before {before}, after {after}")
        _expect(violations, calls == [], f"a failed deletion must touch no report file: {calls}")
        assert not violations, f"A technical failure must delete nothing:{_verdict(violations)}"
        print_success("500, nothing deleted, no file touched")


# ============================================================================
# IN-PROCESS: THE PENDING ADMINISTRATOR IN THE USERS TAB (lot A7b, C5)
# ============================================================================


#: What a token in each state of ``_private_link`` reads as, once the scene is built.
LINK_STATUSES = {"live": TokenStatus.VALID, "expired": TokenStatus.EXPIRED, "revoked": TokenStatus.REVOKED, "consumed": TokenStatus.CONSUMED}


@dataclass(frozen=True)
class _PendingAdmin:
    """The F02 administrator the bootstrap made on a private instance, and the token of its setup link (live, unless the case asked for it expired)."""

    account: _Account
    token: str


async def _bootstrap_pending_admin(private: _Private, *, expired: bool = False) -> _PendingAdmin:
    """The pending administrator F02 makes: ``run_admin_bootstrap`` on the still empty private instance, for F02_USERNAME and F02_EMAIL, the token of its setup link given by the configuration so that the test holds the link; committed by the service. ``expired``: the bootstrap ran the link's lifetime and a minute ago, so the link has expired — never waited for — and the account waits all the same.

    Run it first: the bootstrap creates its administrator on an instance without accounts only. It ends on what it
    promises — ``CREATED``, the account an inactive superuser, the token an ``admin_setup`` link of that account, live or
    expired as asked. ``account.password`` is the one its setup would choose, SETUP_PASSWORD; until then nobody knows it.
    """
    token = token_urlsafe(32)
    moment = utcnow() - DEFAULT_TTL[ADMIN_SETUP] - timedelta(minutes=1) if expired else utcnow()
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        result = await run_admin_bootstrap(session, AdminBootstrapConfig(email=F02_EMAIL, username=F02_USERNAME, token=token), now=moment)
    assert result.action == BootstrapAction.CREATED and result.user_id is not None, f"Setup: on an empty instance the bootstrap creates the pending administrator: {result!r}"
    async with AsyncSession(private.engine) as session:
        link = await inspect_token(session, token, ADMIN_SETUP)
    owner = link.record.user_id if link.record is not None else None
    expected = TokenStatus.EXPIRED if expired else TokenStatus.VALID
    assert (link.status, owner) == (expected, result.user_id), f"Setup: the configuration's token must be a setup link of the new account {result.user_id}, {expected.value}: {link.status.value}, owner {owner}"
    flags = (await _private_user(private, result.user_id))[:2]
    assert flags == (False, True), f"Setup: the pending administrator is an inactive superuser: (is_active, is_superuser) {flags}"
    return _PendingAdmin(account=_Account(user_id=result.user_id, username=F02_USERNAME, email=F02_EMAIL, password=SETUP_PASSWORD), token=token)


async def _private_link(private: _Private, user_id: int, purpose: AccountTokenPurpose, state: str) -> None:
    """A token of ``purpose`` for the account, through the token service: ``live`` (issued now), ``expired`` (issued its lifetime and a minute ago, never waited for), ``revoked``, or ``consumed`` by the account itself, as its setup or a reset spends it.

    It ends on what it promises: the token reads as that state (LINK_STATUSES).
    """
    issued_at = utcnow() - DEFAULT_TTL[purpose] - timedelta(minutes=1) if state == "expired" else utcnow()
    issued = await _private_issue(private, purpose, user_id=user_id, now=issued_at)
    async with AsyncSession(private.engine) as session:
        if state == "revoked":
            await revoke_tokens(session, token_id=issued.record.id)
        elif state == "consumed":
            await consume_token(session, issued.token, purpose, consumed_by_user_id=user_id)
        await session.commit()
        status = (await inspect_token(session, issued.token, purpose)).status
    assert status == LINK_STATUSES[state], f"Setup: a {state} {purpose.value} token must read {LINK_STATUSES[state].value}, it reads {status.value}"


async def _pending_admin_ids(private: _Private) -> set[int]:
    """The accounts ``registration_service.pending_admin_filter()`` selects in the private database: A7a's notion of the account waiting for its setup, the one C5 reuses."""
    async with AsyncSession(private.engine) as session:
        return set((await session.execute(select(User.id).where(*registration_service.pending_admin_filter()))).scalars().all())


async def _private_listed(private: _Private, cookie: str) -> dict[int, dict[str, Any]]:
    """GET /users as this administrator: the listed accounts by id, after a 200."""
    response = await _call(private, "GET", "/users", cookie=cookie)
    assert response.status_code == 200, f"GET /users as an administrator: {response.status_code} {response.text}"
    return {item["id"]: item for item in response.json()["items"]}


async def _private_view(private: _Private, cookie: str, user_id: int) -> tuple[Optional[dict[str, Any]], Any]:
    """GET /users as this administrator: the account's item, found by id (None when absent), and the usage."""
    response = await _call(private, "GET", "/users", cookie=cookie)
    assert response.status_code == 200, f"GET /users as an administrator: {response.status_code} {response.text}"
    body = response.json()
    return next((item for item in body["items"] if item.get("id") == user_id), None), body.get("usage")


async def _private_snapshot(private: _Private) -> dict[str, list[dict[str, Any]]]:
    """Every row of ``users`` and ``account_tokens`` in the private database, as raw column values read from the tables: what a refused PATCH may not change. The test owns them all."""
    async with AsyncSession(private.engine) as session:
        users = (await session.execute(select(User.__table__).order_by(User.__table__.c.id))).mappings().all()
        tokens = (await session.execute(select(AccountToken.__table__).order_by(AccountToken.__table__.c.id))).mappings().all()
    return {"users": [dict(row) for row in users], "account_tokens": [dict(row) for row in tokens]}


def _snapshot_changes(before: dict[str, list[dict[str, Any]]], after: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """The rows of each table that are not the same before and after, as ``{table: {"before": […], "after": […]}}``; empty when nothing changed."""
    changes: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for table in sorted(before.keys() | after.keys()):
        gone = [row for row in before.get(table, []) if row not in after.get(table, [])]
        new = [row for row in after.get(table, []) if row not in before.get(table, [])]
        if gone or new:
            changes[table] = {"before": gone, "after": new}
    return changes


@dataclass(frozen=True)
class _SetupScene:
    """An account of the private instance: whether it is active and an administrator, its tokens as ``(purpose, state)`` in the order they are issued (``_private_link``), and the ``pending_setup`` C5 expects for it."""

    active: bool
    superuser: bool
    tokens: tuple[tuple[AccountTokenPurpose, str], ...]
    pending_setup: bool


#: The scenes of BOOT-016 (``pending_admin``, ``test_admin_bootstrap.py``) as accounts of the Users tab, and three more:
#: a re-armed link (what ``./dev.py user setup-link`` leaves), an account no longer an administrator, and an inactive
#: administrator without a setup link — with no token, or with a reset link.
PENDING_SETUP_SCENES = [
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "live"),), pending_setup=True), id="inactive-with-a-live-setup-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "expired"),), pending_setup=True), id="inactive-with-an-expired-setup-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "revoked"),), pending_setup=True), id="inactive-with-a-revoked-setup-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "revoked"), (ADMIN_SETUP, "live")), pending_setup=True), id="inactive-re-armed"),
    pytest.param(_SetupScene(active=False, superuser=False, tokens=((ADMIN_SETUP, "live"),), pending_setup=True), id="inactive-not-an-administrator-with-a-live-setup-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "consumed"),), pending_setup=False), id="inactive-with-a-consumed-setup-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "consumed"), (ADMIN_SETUP, "live")), pending_setup=False), id="inactive-with-a-consumed-and-a-live-setup-link"),
    pytest.param(_SetupScene(active=True, superuser=True, tokens=((ADMIN_SETUP, "live"),), pending_setup=False), id="active-with-a-live-setup-link"),
    pytest.param(_SetupScene(active=True, superuser=True, tokens=((ADMIN_SETUP, "consumed"), (ADMIN_SETUP, "revoked")), pending_setup=False), id="active-after-its-setup"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((PASSWORD_RESET, "live"),), pending_setup=False), id="inactive-administrator-with-a-reset-link-only"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=(), pending_setup=False), id="inactive-administrator-without-any-link"),
]

#: What an administrator may ask of the pending administrator besides its activation, and what lot A-43 answers: (the body,
#: the status, ``detail.error_code``, how its setup link inspects afterwards). Changed in A-42/A-43, by construction: the
#: demotion — 200 until A-43, the account a superuser no more — is refused whole now (UADM-072); {is_active: false} on the
#: account already inactive still answers 200, and now revokes its live setup link, the account still waiting (UADM-074).
PENDING_ADMIN_CHANGES = [
    pytest.param({"is_superuser": False}, 409, "PENDING_SETUP", "valid", id="demoted-refused"),
    pytest.param({"is_active": False}, 200, None, "revoked", id="deactivated-while-already-inactive"),
]

#: The detail of the refusal to activate the pending administrator carries exactly these keys (UADM-065); the wording of its message is not pinned.
PENDING_SETUP_KEYS = frozenset({"error_code", "message"})

#: PATCH bodies that would activate the pending administrator: refused whole, whatever else they ask.
ACTIVATIONS = [
    pytest.param({"is_active": True}, id="activate"),
    pytest.param({"is_active": True, "is_superuser": True}, id="activate-as-an-administrator"),
    pytest.param({"is_active": True, "is_superuser": False}, id="activate-and-demote"),
]

#: The pending administrator's setup link, live or expired: the account waits all the same (pending_admin_filter()).
PENDING_LINKS = [pytest.param(False, id="its-link-live"), pytest.param(True, id="its-link-expired")]

#: Inactive accounts that do not wait for a setup: an ordinary member, an administrator without any link, and an
#: administrator whose setup link was spent — deactivated after its setup, its password known.
NOT_PENDING_INACTIVE = [
    pytest.param(_SetupScene(active=False, superuser=False, tokens=(), pending_setup=False), id="a-member-without-any-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=(), pending_setup=False), id="an-administrator-without-any-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "consumed"),), pending_setup=False), id="an-administrator-whose-setup-link-was-spent"),
]


class TestThePendingAdministratorInTheUsersTab:
    """Lot A7b, C5: the Users tab tells the account waiting for its F02 setup from a deactivated one, and the PATCH refuses to activate it. In-process only: a pending administrator never enters the lane's database."""

    @pytest.mark.asyncio
    async def test_the_pending_administrator_is_listed_pending_setup_and_nobody_else(self, private: _Private) -> None:
        """UADM-060: the bootstrap made the pending administrator; root (the caller), a member, a deactivated account and an account waiting for its email verification (a live verification link, written directly) are there too. GET /users → pending_setup true for the pending administrator only, false for every other account; holds_place true for the waiting account only — false for the pending administrator, whose place another rule counts —, and since E-7 (point 21) pending_verification true for it only; each account exactly its nine fields; usage as before: used 4 (root, the member, the waiting account, the pending administrator), no limit, no billing link."""
        print_section("UADM-060: GET /users with the pending administrator")
        pending = await _bootstrap_pending_admin(private)
        root, cookie = await _admin(private)
        member = await _add_user(private, "member")
        dormant = await _add_user(private, "dormant", active=False)
        waiting = await _add_user(private, "waiting", active=False)
        await _private_link(private, waiting.user_id, EMAIL_VERIFICATION, "live")

        response = await _call(private, "GET", "/users", cookie=cookie)

        assert response.status_code == 200, f"GET /users as an administrator: {response.status_code} {response.text}"
        body = response.json()
        items = {item["id"]: item for item in body["items"]}
        # (account, is_active, is_superuser, holds_place, pending_setup)
        expected = [(pending.account, False, True, False, True), (root, True, True, False, False), (member, True, False, False, False), (dormant, False, False, False, False), (waiting, False, False, True, False)]
        flags = {item.get("username"): item.get("pending_setup", "<missing>") for item in body["items"]}
        violations: list[str] = []
        _expect(violations, sorted(items) == sorted(row[0].user_id for row in expected), f"GET /users must list every account of the instance: {sorted(items)}")
        _expect(violations, flags == {F02_USERNAME: True, "root": False, "member": False, "dormant": False, "waiting": False}, f"pending_setup must be true for the pending administrator only: {flags}")
        for account, active, superuser, holds_place, pending_setup in expected:
            # The waiting account is also lot E-7's (point 21): an inactive account with a live verification link waits for it
            violations += _user_item_violations(items.get(account.user_id), account, active=active, superuser=superuser, holds_place=holds_place, pending_setup=pending_setup, pending_verification=account is waiting)
        _expect(violations, body["usage"] == {"used": 4, "max_users": None, "billing_url": None}, f"usage must count as before — root, the member, the waiting account and the pending administrator: {body['usage']}")
        assert not violations, f"GET /users must tell the pending administrator apart, and only it:{_verdict(violations)}"
        print_success("pending_setup true for the pending administrator only; holds_place its own flag; usage unchanged")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scene", PENDING_SETUP_SCENES)
    async def test_pending_setup_is_the_notion_of_pending_admin_filter(self, private: _Private, scene: _SetupScene) -> None:
        """UADM-061: an account in one state of its setup links, beside root, the caller. GET /users → its pending_setup is true exactly when it is inactive with an admin_setup token and none of them consumed — live, expired or revoked alike, an administrator or not —: the notion of registration_service.pending_admin_filter(), which user_usage counts. Root's is false; both are exactly their nine fields.

        Premise first: the filter selects the account exactly when the scene says it waits. If it no longer does, A7a's
        notion has moved, and this expectation moves with it, not the flag.
        """
        print_section(f"UADM-061: pending_setup of an account active={scene.active}, administrator={scene.superuser}, tokens {[(purpose.value, state) for purpose, state in scene.tokens]}")
        root, cookie = await _admin(private)
        subject = await _add_user(private, "subject", admin=scene.superuser, active=scene.active)
        for purpose, state in scene.tokens:
            await _private_link(private, subject.user_id, purpose, state)
        selected = subject.user_id in await _pending_admin_ids(private)
        assert selected is scene.pending_setup, f"premise: pending_admin_filter() selects this account: {selected}; C5 expects pending_setup {scene.pending_setup} because it is the same notion — if the filter moved, this expectation moves with it"

        items = await _private_listed(private, cookie)

        violations = _user_item_violations(items.get(subject.user_id), subject, active=scene.active, superuser=scene.superuser, pending_setup=scene.pending_setup)
        violations += _user_item_violations(items.get(root.user_id), root, active=True, superuser=True)
        assert not violations, f"pending_setup must be the notion of pending_admin_filter():{_verdict(violations)}"
        print_success(f"pending_setup {scene.pending_setup}, as the filter says; root false")

    # red until A-42/A-43 — changed by construction: its demotion is refused now, its deactivation now revokes the link
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("change", "status", "code", "link"), PENDING_ADMIN_CHANGES)
    async def test_the_patch_answer_carries_pending_setup_as_the_list_does(self, private: _Private, change: dict[str, bool], status: int, code: Optional[str], link: str) -> None:
        """UADM-062: PATCH /users/{the pending administrator} with a change that leaves it waiting for its setup. {is_active: false} on the account already inactive → 200, the account exactly its nine fields, still inactive, still an administrator, pending_setup true: the answer replaces its row in the Users tab, it is the item GET /users lists right after. Whatever the PATCH, the account still waits — the filter selects it, the list says pending_setup true. The flag is the one of the account the PATCH returns, as ``holds_place`` is.

        Changed in A-42/A-43, by construction: that deactivation now revokes the account's live setup link — inspected,
        ``revoked`` —, the account still waiting (until A-43 the link stayed valid); the demotion, 200 until A-43 with the
        account a superuser no more, is refused now — 409 PENDING_SETUP, UADM-072 —, and the list still says inactive, an
        administrator, pending_setup true, its link valid.
        """
        print_section(f"UADM-062: PATCH {change} on the pending administrator")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)

        response = await _call(private, "PATCH", f"/users/{pending.account.user_id}", cookie=cookie, json=change)

        listed = (await _private_listed(private, cookie)).get(pending.account.user_id)
        inspected = _inspected(await _inspect_setup_link(private, pending.token))
        violations: list[str] = []
        _expect(violations, _refusal(response) == (status, code), f"PATCH {change} on the pending administrator: expected {status} {code or ''}, got {response.status_code} {response.text}")
        _expect(violations, pending.account.user_id in await _pending_admin_ids(private), f"after PATCH {change} the account must still wait for its setup: pending_admin_filter() no longer selects it")
        violations += [f"listed after the PATCH: {violation}" for violation in _user_item_violations(listed, pending.account, active=False, superuser=True, pending_setup=True)]
        if response.status_code == 200:
            answer = response.json()
            violations += [f"the PATCH's answer: {violation}" for violation in _user_item_violations(answer, pending.account, active=False, superuser=True, pending_setup=True)]
            _expect(violations, _comparable(answer) == _comparable(listed), f"the answer must be the account as GET /users lists it right after: answered {answer}, listed {listed}")
        _expect(violations, inspected[1].get("status") == link, f"after PATCH {change} its setup link must inspect {link}: {inspected}")
        assert not violations, f"red until A-43: the PATCH must answer as lot A-43 says, the account still waiting for its setup:{_verdict(violations)}"
        print_success(f"{status}, pending_setup true, its link {link}")

    @pytest.mark.asyncio
    async def test_once_set_up_the_administrator_is_pending_no_more_even_deactivated(self, private: _Private) -> None:
        """UADM-063: the pending administrator, listed with pending_setup true, spends its setup link through POST /auth/setup (200): GET /users then lists it active, pending_setup false. Deactivated afterwards by root — PATCH {is_active: false} → 200 —, it is an ordinary inactive account, whose password is known: the answer, and the list after it, say pending_setup false.

        Premise: once its link was spent, the filter no longer selects the account.
        """
        print_section("UADM-063: set up, then deactivated — pending no more")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id
        before = (await _private_listed(private, cookie)).get(user_id)

        setup = await _call(private, "POST", "/auth/setup", json={"token": pending.token, "new_password": SETUP_PASSWORD})
        assert setup.status_code == 200, f"Setup: POST /auth/setup with the live link: expected 200, got {setup.status_code} {setup.text}"
        set_up = (await _private_listed(private, cookie)).get(user_id)
        off = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json={"is_active": False})
        assert off.status_code == 200, f"PATCH {{is_active: false}} after the setup: expected 200, got {off.status_code} {off.text}"
        listed_off = (await _private_listed(private, cookie)).get(user_id)

        assert user_id not in await _pending_admin_ids(private), "premise: once its link was spent, pending_admin_filter() no longer selects the account"
        answer = off.json()
        violations = _user_item_violations(before, pending.account, active=False, superuser=True, pending_setup=True)
        violations += _user_item_violations(set_up, pending.account, active=True, superuser=True)
        violations += _user_item_violations(answer, pending.account, active=False, superuser=True)
        _expect(violations, _comparable(answer) == _comparable(listed_off), f"the answer must be the account as GET /users lists it right after: answered {answer}, listed {listed_off}")
        assert not violations, f"An administrator set up is pending no more, even deactivated:{_verdict(violations)}"
        print_success("pending before its setup; not after it, nor after a deactivation")

    def test_admin_user_read_declares_pending_setup_false_by_default(self) -> None:
        """UADM-064: AdminUserRead declares ``pending_setup: bool``, false by default — an AdminUserRead built without it is not pending —, and nothing else changes: its fields are exactly the nine an account is listed with."""
        print_section("UADM-064: AdminUserRead.pending_setup")
        declared = AdminUserRead.model_fields.get("pending_setup")
        assert declared is not None, f"AdminUserRead must declare pending_setup (lot A7b, C5); it declares {sorted(AdminUserRead.model_fields)}"
        built = AdminUserRead(id=1, username="built", email="built@example.com", is_active=False, is_superuser=True, created_at=utcnow(), protected=False)

        violations: list[str] = []
        _expect(violations, declared.annotation is bool, f"pending_setup must be a bool: {declared.annotation!r}")
        _expect(violations, not declared.is_required() and declared.default is False, f"pending_setup must default to false: required {declared.is_required()}, default {declared.default!r}")
        _expect(violations, built.pending_setup is False, f"an account built without it must not be pending: {built.pending_setup!r}")
        _expect(violations, set(AdminUserRead.model_fields) == USER_ITEM_KEYS, f"AdminUserRead must be exactly {sorted(USER_ITEM_KEYS)}: {sorted(AdminUserRead.model_fields)}")
        assert not violations, f"AdminUserRead.pending_setup broke its contract:{_verdict(violations)}"
        print_success("a bool, false by default, nine fields")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("expired", PENDING_LINKS)
    @pytest.mark.parametrize("change", ACTIVATIONS)
    async def test_activating_the_pending_administrator_is_refused_and_changes_nothing(self, private: _Private, change: dict[str, bool], expired: bool) -> None:
        """UADM-065: PATCH /users/{the pending administrator} with a body that activates it — {is_active: true}, alone or with is_superuser true or false — → 409, detail exactly {error_code: PENDING_SETUP, message}, the message a sentence whose wording is not pinned. All or nothing, as the route's other refusals: nothing changes — the account still inactive and an administrator, its session version and password hash as they were (every row of users and account_tokens as it was); its setup link neither consumed nor revoked; its row in GET /users and the usage identical. Its link live or expired: it waits all the same (pending_admin_filter()), its password a secret nobody knows; the way in is a setup link, not an activation.

        Premise: the filter selects the account. No LIBREFOLIO_MAX_USERS in this process: the limit cannot refuse first.
        """
        print_section(f"UADM-065: PATCH {change} on the pending administrator, its link {'expired' if expired else 'live'}")
        pending = await _bootstrap_pending_admin(private, expired=expired)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id
        assert user_id in await _pending_admin_ids(private), "premise: pending_admin_filter() selects the pending administrator"
        listed_before, usage_before = await _private_view(private, cookie, user_id)
        assert listed_before is not None, "Presence barrier: GET /users must list the pending administrator, or «its row identical» below proves nothing"
        before = await _private_snapshot(private)

        response = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json=change)

        after = await _private_snapshot(private)
        listed_after, usage_after = await _private_view(private, cookie, user_id)
        detail = _detail(response)
        account = next(row for row in after["users"] if row["id"] == user_id)
        links = [(row["id"], row["consumed_at"], row["revoked_at"]) for row in after["account_tokens"] if row["user_id"] == user_id and row["purpose"] == ADMIN_SETUP]
        changes = _snapshot_changes(before, after)
        violations: list[str] = []
        _expect(violations, _refusal(response) == (409, "PENDING_SETUP"), f"expected 409 PENDING_SETUP, got {response.status_code} {response.text}")
        _expect(violations, set(detail) == PENDING_SETUP_KEYS and isinstance(detail.get("message"), str) and detail["message"].strip() != "", f"detail must be exactly {sorted(PENDING_SETUP_KEYS)}, the message a sentence: {detail}")
        _expect(violations, not account["is_active"], f"the pending administrator must still be inactive: is_active {account['is_active']!r}")
        _expect(violations, links != [] and all(consumed is None and revoked is None for _, consumed, revoked in links), f"its setup link must be neither consumed nor revoked: (id, consumed_at, revoked_at) {links}")
        _expect(violations, changes == {}, f"a refused PATCH must change nothing, all or nothing — rows that changed: {changes}")
        _expect(violations, (_comparable(listed_after), usage_after) == (_comparable(listed_before), usage_before), f"its row in GET /users and the usage must be identical: before {listed_before} {usage_before}, after {listed_after} {usage_after}")
        assert not violations, f"Activating the pending administrator must be refused, and change nothing:{_verdict(violations)}"
        print_success("409 PENDING_SETUP, nothing changed")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scene", NOT_PENDING_INACTIVE)
    async def test_an_inactive_account_that_does_not_wait_for_its_setup_is_still_activated(self, private: _Private, scene: _SetupScene) -> None:
        """UADM-066, guard of UADM-065 (green today): the pending administrator waits on the instance, and PATCH {is_active: true} on another inactive account, which does not wait for its setup — an ordinary member, an administrator without any link, an administrator whose setup link was spent (deactivated after its setup) — → 200, active in the answer and in the database, an administrator or not as before. The refusal is the pending administrator's alone: not the instance's while one waits, not every inactive administrator's, not every account that ever had a setup link.

        Premise: the filter selects the pending administrator, and only it.
        """
        print_section(f"UADM-066: PATCH {{is_active: true}} on an inactive account that does not wait, administrator={scene.superuser}, tokens {[(purpose.value, state) for purpose, state in scene.tokens]}")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        subject = await _add_user(private, "subject", admin=scene.superuser, active=False)
        for purpose, state in scene.tokens:
            await _private_link(private, subject.user_id, purpose, state)
        assert await _pending_admin_ids(private) == {pending.account.user_id}, "premise: pending_admin_filter() selects the pending administrator, and only it"

        response = await _call(private, "PATCH", f"/users/{subject.user_id}", cookie=cookie, json={"is_active": True})

        assert response.status_code == 200, f"PATCH {{is_active: true}} on an inactive account that does not wait for its setup: expected 200, got {response.status_code} {response.text}"
        answer = response.json()
        state = (await _private_user(private, subject.user_id))[:2]
        violations: list[str] = []
        _expect(violations, (answer.get("is_active"), answer.get("is_superuser")) == (True, scene.superuser), f"the answer must be the account active, is_superuser {scene.superuser}: {answer}")
        _expect(violations, state == (True, scene.superuser), f"the account must be active in the database, is_superuser {scene.superuser}: (is_active, is_superuser) {state}")
        assert not violations, f"An inactive account that does not wait for its setup must still be activated:{_verdict(violations)}"
        print_success("200, active")

    # red until A-42/A-43 — its demotion is refused now (changed by construction); its deactivation stays the guard it was
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("change", "status", "code", "link"), PENDING_ADMIN_CHANGES)
    async def test_only_the_activation_and_the_demotion_of_the_pending_administrator_are_refused(self, private: _Private, change: dict[str, bool], status: int, code: Optional[str], link: str) -> None:
        """UADM-067, guard of UADM-065: not every change to the pending administrator is refused, nor every body that names is_active — {is_active: false} on the account already inactive still answers 200, green today and after —; the answer and the database say inactive, still an administrator, and the account still waits: the filter selects it. Its pending_setup and its link are UADM-062's to read: here only the status and the two states.

        Changed in A-42/A-43, by construction (until A-43 «still answers 200» for both): the demotion is refused now, as
        the activation is — 409 PENDING_SETUP, nothing changed (UADM-072) —, the account an administrator still.
        """
        print_section(f"UADM-067: PATCH {change} on the pending administrator")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id

        response = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json=change)

        state = (await _private_user(private, user_id))[:2]
        violations: list[str] = []
        _expect(violations, _refusal(response) == (status, code), f"PATCH {change} on the pending administrator: expected {status} {code or ''}, got {response.status_code} {response.text}")
        if response.status_code == 200:
            answer = response.json()
            _expect(violations, (answer.get("is_active"), answer.get("is_superuser")) == (False, True), f"the answer must be the account inactive, still an administrator: {answer}")
        _expect(violations, state == (False, True), f"in the database: (is_active, is_superuser) {state}, expected (False, True)")
        _expect(violations, user_id in await _pending_admin_ids(private), "the account must still wait for its setup: pending_admin_filter() no longer selects it")
        assert not violations, f"Only the activation and the demotion of the pending administrator are refused:{_verdict(violations)}"
        print_success(f"{status}, still waiting")


# ============================================================================
# IN-PROCESS: THE SETUP LINK OF AN ACCOUNT SET UP ANOTHER WAY (lot A7b-2, A-32)
# ============================================================================


#: The password ``./dev.py user reset`` gives the pending administrator (UADM-068); it meets the rules.
COMMAND_PASSWORD = "Reset-By-Command-2026"
#: What POST /auth/tokens/inspect shows of a retired setup link (``_inspected``): revoked, its purpose, nothing more.
RETIRED = (200, {"status": "revoked", "purpose": "admin_setup"})
#: How the pending administrator is set up without its link (A-32), ending inactive as it began (``_set_up_another_way``).
SET_UP_ANOTHER_WAY = ["a-reset-link-from-the-users-tab", "user-reset", "user-activate-then-deactivated-by-root"]
#: What root does that leaves the pending administrator waiting (UADM-069): the method, the path after /users/{id}, the body, the status it answers.
#: Changed in A-42/A-43, by construction: root's demotion answered 200 until A-43 — the setup then made an ordinary member
#: —; it is refused now, 409 PENDING_SETUP, and changes nothing (UADM-072). Root's {is_active: false} on the account
#: already inactive now revokes its link: «the link still works» no longer holds for it, and it left for UADM-074.
WAITING_ACTIONS: dict[str, tuple[str, str, Optional[dict[str, bool]], int]] = {
    "a-reset-link-issued-not-spent": ("POST", "/password-reset-link", None, 201),
    "demotion-refused": ("PATCH", "", {"is_superuser": False}, 409),
}
#: UADM-069's cases — WAITING_ACTIONS, and nothing done —, with whether the account is an administrator afterwards.
LEAVE_IT_WAITING = [
    pytest.param("nothing-done", True, id="nothing-done"),
    pytest.param("a-reset-link-issued-not-spent", True, id="a-reset-link-issued-not-spent"),
    pytest.param("demotion-refused", True, id="demoted-by-root-refused"),
]


async def _cli_set_active(private: _Private, username: str, active: bool) -> None:
    """``./dev.py user activate`` or ``deactivate``: the call the command makes, ``user_service.set_user_active``. It ends on its promise: done, the account active or not as asked."""
    async with AsyncSession(private.engine) as session:
        done = await user_service.set_user_active(session, username, active)
        is_active = (await session.execute(select(User.is_active).where(User.username == username))).scalar_one()
    assert (done, bool(is_active)) == ((True, None), active), f"Setup: user_service.set_user_active({username!r}, {active}) must succeed and leave the account so: answered {done}, is_active {is_active}"


async def _cli_reset_password(private: _Private, username: str, password: str) -> None:
    """``./dev.py user reset``: the call the command makes, ``user_service.reset_password``. It ends on its promise: done, ``password`` the account's."""
    async with AsyncSession(private.engine) as session:
        done = await user_service.reset_password(session, username, password)
        hashed = (await session.execute(select(User.hashed_password).where(User.username == username))).scalar_one()
    assert done == (True, None) and auth_service.verify_password(password, hashed), f"Setup: user_service.reset_password({username!r}) must succeed and set the password: answered {done}"


async def _inspect_setup_link(private: _Private, token: str) -> httpx.Response:
    """POST /auth/tokens/inspect with ``purpose: admin_setup``, from a client without a session: whoever holds the link."""
    return await _call(private, "POST", "/auth/tokens/inspect", json={"token": token, "purpose": "admin_setup"})


def _inspected(response: httpx.Response) -> tuple[int, dict[str, Any]]:
    """What an inspection shows: its status code, and the fields of its answer that carry a value (the body whole, under ``body``, when it is not an object)."""
    status, body = _answer(response)
    shown = {key: value for key, value in body.items() if value is not None} if isinstance(body, dict) else {"body": body}
    return status, shown


async def _setup_with(private: _Private, token: str) -> httpx.Response:
    """POST /auth/setup with ``token`` and SETUP_PASSWORD, from a client without a session: whoever holds the link."""
    return await _call(private, "POST", "/auth/setup", json={"token": token, "new_password": SETUP_PASSWORD})


async def _set_up_another_way(private: _Private, cookie: str, pending: _PendingAdmin, way: str) -> Optional[str]:
    """The pending administrator set up another way than its link, as ``way`` says, root acting with ``cookie``: the password that way set, None when it sets none. It ends on its promise: the account inactive, as it began.

    ``a-reset-link-from-the-users-tab``: root's ``POST /users/{id}/password-reset-link``, spent through ``POST
    /auth/password-reset``. ``user-reset``: ``./dev.py user reset``. ``user-activate-then-deactivated-by-root``:
    ``./dev.py user activate``, then root's ``PATCH {is_active: false}``.
    """
    assert way in SET_UP_ANOTHER_WAY, f"no such way: {way!r}"
    user_id = pending.account.user_id
    password: Optional[str] = None
    if way == "a-reset-link-from-the-users-tab":
        created = await _call(private, "POST", f"/users/{user_id}/password-reset-link", cookie=cookie)
        assert created.status_code == 201, f"Setup: root's POST /users/{{the pending administrator}}/password-reset-link: {created.status_code} {created.text}"
        spent = await _call(private, "POST", "/auth/password-reset", json={"token": created.json()["token"], "new_password": NEW_PASSWORD})
        assert spent.status_code == 200, f"Setup: POST /auth/password-reset with that link: {spent.status_code} {spent.text}"
        password = NEW_PASSWORD
    elif way == "user-reset":
        await _cli_reset_password(private, F02_USERNAME, COMMAND_PASSWORD)
        password = COMMAND_PASSWORD
    else:
        await _cli_set_active(private, F02_USERNAME, True)
        off = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json={"is_active": False})
        assert off.status_code == 200, f"Setup: root's PATCH {{is_active: false}} after ./dev.py user activate: {off.status_code} {off.text}"
    assert not (await _private_user(private, user_id))[0], f"Setup: set up another way ({way}), the account must end inactive, as it began"
    return password


async def _leave_it_waiting(private: _Private, cookie: str, user_id: int, action: str) -> Optional[httpx.Response]:
    """Root's ``action`` on the pending administrator (WAITING_ACTIONS; ``nothing-done``: none): the answer to its request — its status is the case's to read —, None for nothing done. It ends on its promise: the account still inactive."""
    response = None
    if action != "nothing-done":
        method, suffix, body, _expected = WAITING_ACTIONS[action]
        response = await _call(private, method, f"/users/{user_id}{suffix}", cookie=cookie, json=body)
    assert not (await _private_user(private, user_id))[0], f"Setup: after {action} the pending administrator must still be inactive"
    return response


class TestTheSetupLinkOfAnAccountSetUpAnotherWay:
    """Lot A7b-2 (A-32, decision N60): set up another way than its link — activated, or given a password —, an account waits for its setup no more, and its old link sets nothing, the account deactivated again too. In-process only, as A7b's: a pending administrator never enters the lane's database."""

    # red until A7b-2
    @pytest.mark.asyncio
    @pytest.mark.parametrize("way", SET_UP_ANOTHER_WAY)
    async def test_an_account_set_up_another_way_waits_no_more_and_its_old_link_sets_nothing(self, private: _Private, way: str) -> None:
        """UADM-068 (A-32): the bootstrap's pending administrator set up another way than its link, inactive at the end as it began — root's reset link (POST /users/{id}/password-reset-link) spent through POST /auth/password-reset, ``./dev.py user reset``, or ``./dev.py user activate`` then root's PATCH {is_active: false} —: its setup link is retired (decision N60). Inspected → revoked, nothing more; GET /users lists it inactive, pending_setup false, exactly its nine fields; PATCH {is_active: true} → 200, the account active in the answer (pending_setup false) and in the database — not point 14's 409 —, and the password the other way set signs it in. Deactivated again by root, the old link with a password that meets the rules → 400 TOKEN_INVALID, every row of users and account_tokens as it was, and the list still says pending_setup false: whoever holds the link — it was in the log too — no longer takes the account over."""
        print_section(f"UADM-068: the pending administrator set up another way ({way})")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id
        password = await _set_up_another_way(private, cookie, pending, way)

        inspected = await _inspect_setup_link(private, pending.token)
        listed = (await _private_listed(private, cookie)).get(user_id)
        on = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json={"is_active": True})
        active = (await _private_user(private, user_id))[0]
        signed_in = None if password is None else await _call(private, "POST", "/auth/login", json={"username": F02_USERNAME, "password": password})
        off = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json={"is_active": False})
        assert off.status_code == 200, f"Setup: root deactivates the account again: {off.status_code} {off.text}"
        before = await _private_snapshot(private)
        setup = await _setup_with(private, pending.token)
        changes = _snapshot_changes(before, await _private_snapshot(private))
        relisted = (await _private_listed(private, cookie)).get(user_id)

        violations: list[str] = []
        _expect(violations, _refusal(setup) == (400, "TOKEN_INVALID"), f"POST /auth/setup with the old link, the account inactive again: expected 400 TOKEN_INVALID, got {setup.status_code} {setup.text} — its holder takes the account over")
        _expect(violations, changes == {}, f"the refused setup must change nothing — rows that changed: {changes}")
        _expect(violations, _inspected(inspected) == RETIRED, f"the old link must be retired: inspected, {RETIRED}; got {_inspected(inspected)}")
        violations += [f"listed once set up another way: {violation}" for violation in _user_item_violations(listed, pending.account, active=False, superuser=True)]
        _expect(violations, (on.status_code, active) == (200, True), f"PATCH {{is_active: true}} must reactivate it, not refuse it: {on.status_code} {on.text}; active in the database: {active}")
        if on.status_code == 200:
            violations += [f"the PATCH's answer: {violation}" for violation in _user_item_violations(on.json(), pending.account, active=True, superuser=True)]
        if signed_in is not None:
            _expect(violations, signed_in.status_code == 200, f"reactivated, the account must sign in with the password set another way ({way}): {signed_in.status_code} {signed_in.text}")
        violations += [f"listed after root deactivated it again: {violation}" for violation in _user_item_violations(relisted, pending.account, active=False, superuser=True)]
        assert not violations, f"An account set up another way must wait no more, and its old link must set nothing:{_verdict(violations)}"
        print_success("retired: pending no more, reactivated by the PATCH, the old link refused")

    # red until A-42/A-43 — its demoted-by-root-refused variant, changed by construction; its two others stay guards
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("action", "superuser_after"), LEAVE_IT_WAITING)
    async def test_what_leaves_the_pending_administrator_waiting_keeps_the_refusal_and_the_link(self, private: _Private, action: str, superuser_after: bool) -> None:
        """UADM-069, guard of UADM-068: what leaves the pending administrator waiting — nothing done, root's reset link issued and not spent, root's demotion, refused — retires nothing: root's request answers as WAITING_ACTIONS says; GET /users lists it inactive, pending_setup true; PATCH {is_active: true} → 409 PENDING_SETUP (UADM-065); its link inspects valid, for its username, and POST /auth/setup with it → 200, the account active and still an administrator. Complements UADM-062 and UADM-067: the retirement is an activation's and a new password's only.

        Changed in A-42/A-43, by construction: root's demotion answered 200 until A-43, and the setup then made an
        ordinary member; it is refused now (409 PENDING_SETUP, UADM-072) and changes nothing, so the link still works —
        red until A-43, on its first step. Root's {is_active: false} on the account already inactive left this guard
        for UADM-074: it now revokes the link.
        """
        print_section(f"UADM-069: {action}, and the pending administrator still waits")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id
        acted = await _leave_it_waiting(private, cookie, user_id, action)

        listed = (await _private_listed(private, cookie)).get(user_id)
        refused = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json={"is_active": True})
        status, shown = _inspected(await _inspect_setup_link(private, pending.token))
        setup = await _setup_with(private, pending.token)
        state = (await _private_user(private, user_id))[:2]

        violations: list[str] = []
        if acted is not None:
            expected = WAITING_ACTIONS[action][3]
            _expect(violations, acted.status_code == expected, f"{action}: root's request must answer {expected} (a demotion of the pending administrator is refused since A-43), got {acted.status_code} {acted.text}")
        violations += _user_item_violations(listed, pending.account, active=False, superuser=superuser_after, pending_setup=True)
        _expect(violations, _refusal(refused) == (409, "PENDING_SETUP"), f"PATCH {{is_active: true}} on the account still waiting: expected 409 PENDING_SETUP, got {refused.status_code} {refused.text}")
        _expect(violations, (status, shown.get("status"), shown.get("username")) == (200, "valid", F02_USERNAME), f"its link must still be valid, for {F02_USERNAME}: {status} {shown}")
        _expect(violations, setup.status_code == 200, f"its link must still set the account up: POST /auth/setup answered {setup.status_code} {setup.text}")
        _expect(violations, state == (True, superuser_after), f"set up, the account is active, an administrator or not as {action} left it: (is_active, is_superuser) {state}")
        assert not violations, f"What leaves the pending administrator waiting must keep both the refusal and its link:{_verdict(violations)}"
        print_success("still waiting: pending_setup true, 409 PENDING_SETUP, the link valid and working")

    # red until A7b-2
    @pytest.mark.asyncio
    async def test_an_activation_by_the_patch_retires_the_setup_links_too(self, private: _Private) -> None:
        """UADM-070 (A-32, defense in depth): an inactive administrator whose setup link was spent holds another one, live (rows of the token service): it does not wait for its setup (UADM-061), so PATCH {is_active: true} activates it (200, UADM-066). That activation retires the live link: inspected, revoked and nothing more; deactivated again by root, POST /auth/setup with it → 400 TOKEN_INVALID, every row of users and account_tokens as it was, the account listed inactive, pending_setup false. ``update_user_status`` retires at every activation, whatever the route checked before it."""
        print_section("UADM-070: the PATCH's activation retires the account's setup links")
        _, cookie = await _admin(private)
        veteran = await _add_user(private, "veteran", admin=True, active=False)
        await _private_link(private, veteran.user_id, ADMIN_SETUP, "consumed")
        live = await _private_issue(private, ADMIN_SETUP, user_id=veteran.user_id)
        assert veteran.user_id not in await _pending_admin_ids(private), "premise: an account whose setup link was spent does not wait for its setup, a live link besides (UADM-061)"
        on = await _call(private, "PATCH", f"/users/{veteran.user_id}", cookie=cookie, json={"is_active": True})
        assert on.status_code == 200, f"Setup: PATCH {{is_active: true}} on an inactive account that does not wait for its setup (UADM-066): {on.status_code} {on.text}"

        inspected = await _inspect_setup_link(private, live.token)
        off = await _call(private, "PATCH", f"/users/{veteran.user_id}", cookie=cookie, json={"is_active": False})
        assert off.status_code == 200, f"Setup: root deactivates it again: {off.status_code} {off.text}"
        before = await _private_snapshot(private)
        setup = await _setup_with(private, live.token)
        changes = _snapshot_changes(before, await _private_snapshot(private))
        listed = (await _private_listed(private, cookie)).get(veteran.user_id)

        violations: list[str] = []
        _expect(violations, _refusal(setup) == (400, "TOKEN_INVALID"), f"POST /auth/setup with the link the activation left live, the account inactive again: expected 400 TOKEN_INVALID, got {setup.status_code} {setup.text} — its holder takes the account over")
        _expect(violations, changes == {}, f"the refused setup must change nothing — rows that changed: {changes}")
        _expect(violations, _inspected(inspected) == RETIRED, f"the PATCH's activation must retire the account's live setup link: inspected, {RETIRED}; got {_inspected(inspected)}")
        violations += _user_item_violations(listed, veteran, active=False, superuser=True)
        assert not violations, f"An activation by the PATCH must retire the account's setup links:{_verdict(violations)}"
        print_success("the live link retired by the activation, refused afterwards")

    # red until A7b-2
    @pytest.mark.asyncio
    async def test_the_refused_link_of_an_active_account_retires_its_setup_links(self, private: _Private) -> None:
        """UADM-071 (A-32; night decision 6, completed by the coordinator): an active administrator (a row) holds two live setup links (the token service). POST /auth/setup with one of them → 400 TOKEN_INVALID, as today (SETUP-009, kept as it is) — and the refusal retires every setup link of the account, revoked and consumed, not only the one presented: both inspect revoked. Root deactivates it (200): GET /users lists it inactive, pending_setup false — it waits for no setup, it had one already —, and PATCH {is_active: true} → 200, active again, not 409 PENDING_SETUP; the refused setup changed no password, its own signs it in."""
        print_section("UADM-071: the link of an account already active, refused, retires every setup link of it")
        _, cookie = await _admin(private)
        veteran = await _add_user(private, "veteran", admin=True)
        presented = await _private_issue(private, ADMIN_SETUP, user_id=veteran.user_id)
        other = await _private_issue(private, ADMIN_SETUP, user_id=veteran.user_id)

        setup = await _setup_with(private, presented.token)
        inspected = {"the link presented": _inspected(await _inspect_setup_link(private, presented.token)), "its other link": _inspected(await _inspect_setup_link(private, other.token))}
        off = await _call(private, "PATCH", f"/users/{veteran.user_id}", cookie=cookie, json={"is_active": False})
        assert off.status_code == 200, f"Setup: root deactivates the account: {off.status_code} {off.text}"
        listed = (await _private_listed(private, cookie)).get(veteran.user_id)
        on = await _call(private, "PATCH", f"/users/{veteran.user_id}", cookie=cookie, json={"is_active": True})
        state = (await _private_user(private, veteran.user_id))[:2]
        signed_in = await _call(private, "POST", "/auth/login", json={"username": veteran.username, "password": veteran.password})

        violations: list[str] = []
        _expect(violations, _refusal(setup) == (400, "TOKEN_INVALID"), f"POST /auth/setup with the link of an account already active: expected 400 TOKEN_INVALID, as today (SETUP-009), got {setup.status_code} {setup.text}")
        _expect(violations, inspected == dict.fromkeys(inspected, RETIRED), f"every setup link of the account must be retired, not only the one presented: inspected {inspected}")
        violations += _user_item_violations(listed, veteran, active=False, superuser=True)
        _expect(violations, (on.status_code, state) == (200, (True, True)), f"PATCH {{is_active: true}} must reactivate it, not refuse it: {on.status_code} {on.text}; (is_active, is_superuser) {state}")
        _expect(violations, signed_in.status_code == 200, f"the refused setup changed no password: reactivated, the account signs in with its own: {signed_in.status_code} {signed_in.text}")
        assert not violations, f"The refused link of an account already active must retire its setup links, so that a deactivation leaves it waiting for nothing:{_verdict(violations)}"
        print_success("both links retired; deactivated, pending no more; reactivated by the PATCH")


# ============================================================================
# IN-PROCESS: THE SETUP LINK'S LIFECYCLE IN THE USERS TAB (lot A-42 + A-43)
# ============================================================================


#: What POST /auth/tokens/inspect shows of a revoked setup link (``_inspected``) — only revoked, or retired alike: revoked, its purpose, nothing more.
INSPECTED_REVOKED = (200, {"status": "revoked", "purpose": "admin_setup"})
#: PATCH bodies that demote the pending administrator: refused whole (UADM-072), whatever else they ask.
DEMOTIONS = [
    pytest.param({"is_superuser": False}, id="demote"),
    pytest.param({"is_active": False, "is_superuser": False}, id="deactivate-and-demote"),
]
#: Administrators beside the pending one, demoted as before (UADM-073): an active one, an inactive one without any link,
#: an inactive one whose setup link was spent — deactivated after its setup.
OTHER_ADMINISTRATORS = [
    pytest.param(_SetupScene(active=True, superuser=True, tokens=(), pending_setup=False), id="an-active-administrator"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=(), pending_setup=False), id="an-inactive-administrator-without-any-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "consumed"),), pending_setup=False), id="an-inactive-administrator-whose-setup-link-was-spent"),
]
#: How an account is deactivated (UADM-074, UADM-075): root's PATCH {is_active: false}, or ``./dev.py user deactivate`` —
#: the call the command makes, ``user_service.set_user_active(…, False)``.
DEACTIVATIONS = [pytest.param("patch-by-root", id="patch-by-root"), pytest.param("user-deactivate", id="user-deactivate")]
#: Administrators that do not wait for their setup and hold a stray live setup link (UADM-075): (active, whether set up
#: before — its first setup link consumed by itself).
NOT_WAITING_WITH_A_STRAY_LINK = [
    pytest.param(True, False, id="an-active-administrator-with-a-stray-link"),
    pytest.param(False, True, id="an-inactive-administrator-set-up-before-with-a-stray-link"),
]


async def _deactivate(private: _Private, cookie: str, account: _Account, way: str) -> Optional[httpx.Response]:
    """``account`` deactivated ``way`` (DEACTIVATIONS): root's PATCH — its answer, the case's to read — or ``./dev.py user deactivate`` — None. It ends on its promise: the account inactive."""
    response = None
    if way == "patch-by-root":
        response = await _call(private, "PATCH", f"/users/{account.user_id}", cookie=cookie, json={"is_active": False})
    else:
        assert way == "user-deactivate", f"no such way: {way!r}"
        await _cli_set_active(private, account.username, False)
    assert not (await _private_user(private, account.user_id))[0], f"Setup: deactivated ({way}), the account must be inactive"
    return response


async def _a_new_setup_link(private: _Private) -> Optional[str]:
    """``./dev.py user setup-link``: the call the command makes, ``bootstrap_admin_service.issue_setup_link``, committed — the new link's token, None when nobody waits."""
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        issued = await issue_setup_link(session)
        await session.commit()
    return issued.token if issued is not None else None


class TestTheSetupLinkLifecycleInTheUsersTab:
    """Lot A-42 + A-43 (contract approved by the coordinator, 17/10): the Users tab refuses to demote the pending administrator as it refuses to activate it; a deactivation revokes the pending administrator's setup link — it still waits, for a new one; the hook of lot A7 refuses it for the pending administrator it protects (UADM-079) — and retires those of an account that does not wait. In-process only, as A7b's: a pending administrator never enters the lane's database."""

    # red until A-42/A-43
    @pytest.mark.asyncio
    @pytest.mark.parametrize("expired", PENDING_LINKS)
    @pytest.mark.parametrize("change", DEMOTIONS)
    async def test_demoting_the_pending_administrator_is_refused_as_its_activation_is(self, private: _Private, change: dict[str, bool], expired: bool) -> None:
        """UADM-072 (A-43; decision 4a of the coordinator): PATCH /users/{the pending administrator} with a body that demotes it — {is_superuser: false}, alone or with {is_active: false} — → 409 with the detail of its refused activation word for word: {error_code: PENDING_SETUP, message}, the message the two refusals share — read here from PATCH {is_active: true} on the same account (UADM-065), so its wording is not pinned. All or nothing: every row of users and account_tokens as it was — its setup link neither consumed nor revoked, the deactivation the second body also asks not applied —; its row in GET /users and the usage identical. Its link live or expired: it waits all the same. Its link live, it still sets the account up afterwards: 200, the account active and still an administrator."""
        print_section(f"UADM-072: PATCH {change} on the pending administrator, its link {'expired' if expired else 'live'}")
        pending = await _bootstrap_pending_admin(private, expired=expired)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id
        activation = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json={"is_active": True})
        assert _refusal(activation) == (409, "PENDING_SETUP"), f"Premise (UADM-065): the activation of the pending administrator is refused: {activation.status_code} {activation.text}"
        listed_before, usage_before = await _private_view(private, cookie, user_id)
        assert listed_before is not None, "Presence barrier: GET /users must list the pending administrator, or «its row identical» below proves nothing"
        before = await _private_snapshot(private)

        response = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json=change)

        changes = _snapshot_changes(before, await _private_snapshot(private))
        listed_after, usage_after = await _private_view(private, cookie, user_id)
        setup = None if expired else await _setup_with(private, pending.token)
        state = (await _private_user(private, user_id))[:2]
        detail = _detail(response)
        violations: list[str] = []
        _expect(violations, _refusal(response) == (409, "PENDING_SETUP"), f"red until A-43: PATCH {change} on the pending administrator must be refused, 409 PENDING_SETUP: got {response.status_code} {response.text}")
        _expect(violations, set(detail) == PENDING_SETUP_KEYS and detail == _detail(activation), f"the detail must be exactly the refused activation's, {_detail(activation)}: got {detail}")
        _expect(violations, changes == {}, f"a refused PATCH must change nothing, all or nothing — rows that changed: {changes}")
        _expect(violations, (_comparable(listed_after), usage_after) == (_comparable(listed_before), usage_before), f"its row in GET /users and the usage must be identical: before {listed_before} {usage_before}, after {listed_after} {usage_after}")
        if setup is not None:
            _expect(violations, (setup.status_code, state) == (200, (True, True)), f"its link must still set it up, an administrator: POST /auth/setup answered {setup.status_code} {setup.text}; (is_active, is_superuser) {state}")
        assert not violations, f"Demoting the pending administrator must be refused as its activation is, and change nothing:{_verdict(violations)}"
        print_success("409 PENDING_SETUP, the activation's detail; nothing changed")

    # guard
    @pytest.mark.asyncio
    @pytest.mark.parametrize("scene", OTHER_ADMINISTRATORS)
    async def test_any_other_administrator_is_demoted_as_before(self, private: _Private, scene: _SetupScene) -> None:
        """UADM-073, guard of UADM-072 (green today and after): the refusal is the pending administrator's alone — not the instance's while one waits, nor every inactive administrator's, nor every account that ever had a setup link. Beside it, PATCH {is_superuser: false} on another administrator — active, inactive without any link, inactive with its setup link spent — → 200, the answer and the database an administrator no more, as active as before; the pending administrator still waits, its link valid.

        Premise: the filter selects the pending administrator, and only it.
        """
        print_section(f"UADM-073: PATCH {{is_superuser: false}} on another administrator, active={scene.active}, tokens {[(purpose.value, state) for purpose, state in scene.tokens]}")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        subject = await _add_user(private, "subject", admin=True, active=scene.active)
        for purpose, link_state in scene.tokens:
            await _private_link(private, subject.user_id, purpose, link_state)
        assert await _pending_admin_ids(private) == {pending.account.user_id}, "premise: pending_admin_filter() selects the pending administrator, and only it"

        response = await _call(private, "PATCH", f"/users/{subject.user_id}", cookie=cookie, json={"is_superuser": False})

        state = (await _private_user(private, subject.user_id))[:2]
        inspected = _inspected(await _inspect_setup_link(private, pending.token))
        violations: list[str] = []
        _expect(violations, response.status_code == 200, f"PATCH {{is_superuser: false}} on another administrator: expected 200, got {response.status_code} {response.text}")
        if response.status_code == 200:
            violations += [f"the PATCH's answer: {violation}" for violation in _user_item_violations(response.json(), subject, active=scene.active, superuser=False)]
        _expect(violations, state == (scene.active, False), f"in the database: (is_active, is_superuser) {state}, expected {(scene.active, False)}")
        _expect(violations, await _pending_admin_ids(private) == {pending.account.user_id}, "the pending administrator must still wait, and only it")
        _expect(violations, (inspected[0], inspected[1].get("status")) == (200, "valid"), f"the pending administrator's link must stay valid: {inspected}")
        assert not violations, f"Any other administrator must be demoted as before:{_verdict(violations)}"
        print_success("200, demoted; the pending administrator untouched")

    # red until A-42/A-43
    @pytest.mark.asyncio
    @pytest.mark.parametrize("way", DEACTIVATIONS)
    async def test_deactivating_the_pending_administrator_revokes_its_link_and_a_new_one_sets_it_up(self, private: _Private, way: str) -> None:
        """UADM-074 (A-43, the cancellation; UADM-069's «deactivated by root» variant until A-43, the old link still working): the pending administrator, already inactive, deactivated — root's PATCH {is_active: false}, which answers 200 with its row, pending_setup true (UADM-062), or ./dev.py user deactivate —: its live setup link is revoked, not retired. Inspected → revoked, nothing more; POST /auth/setup with it → 400 TOKEN_INVALID, every row of users and account_tokens as it was. The account still waits: GET /users lists it inactive, an administrator, pending_setup true, and PATCH {is_active: true} is still 409 PENDING_SETUP (UADM-065). ./dev.py user setup-link — the call the command makes — gives it a new link, and POST /auth/setup with that one → 200: the account active, an administrator, listed pending_setup false."""
        print_section(f"UADM-074: the pending administrator deactivated ({way})")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id

        off = await _deactivate(private, cookie, pending.account, way)

        inspected = _inspected(await _inspect_setup_link(private, pending.token))
        before = await _private_snapshot(private)
        old = await _setup_with(private, pending.token)
        changes = _snapshot_changes(before, await _private_snapshot(private))
        listed = (await _private_listed(private, cookie)).get(user_id)
        refused = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json={"is_active": True})
        token = await _a_new_setup_link(private)
        new = await _setup_with(private, token) if token else None
        relisted = (await _private_listed(private, cookie)).get(user_id)

        violations: list[str] = []
        if off is not None:
            _expect(violations, off.status_code == 200, f"root's PATCH {{is_active: false}} must answer 200: {off.status_code} {off.text}")
            if off.status_code == 200:
                violations += [f"the PATCH's answer: {violation}" for violation in _user_item_violations(off.json(), pending.account, active=False, superuser=True, pending_setup=True)]
        _expect(violations, inspected == INSPECTED_REVOKED, f"red until A-43: the deactivation must revoke the pending administrator's live setup link: inspected, {INSPECTED_REVOKED}; got {inspected}")
        _expect(violations, _refusal(old) == (400, "TOKEN_INVALID"), f"POST /auth/setup with the revoked link: expected 400 TOKEN_INVALID, got {old.status_code} {old.text}")
        _expect(violations, changes == {}, f"the refused setup must change nothing — rows that changed: {changes}")
        violations += [f"listed after the deactivation: {violation}" for violation in _user_item_violations(listed, pending.account, active=False, superuser=True, pending_setup=True)]
        _expect(violations, _refusal(refused) == (409, "PENDING_SETUP"), f"the account still waits: PATCH {{is_active: true}} must still be refused, 409 PENDING_SETUP: got {refused.status_code} {refused.text}")
        _expect(violations, new is not None and new.status_code == 200, f"./dev.py user setup-link must give the account still waiting a new link, which sets it up: {'a link' if token else 'no link'}, POST /auth/setup {new.status_code if new is not None else None}")
        violations += [f"listed once set up through the new link: {violation}" for violation in _user_item_violations(relisted, pending.account, active=True, superuser=True)]
        assert not violations, f"Deactivating the pending administrator must revoke its link, and leave it waiting for a new one:{_verdict(violations)}"
        print_success("revoked; still waiting; a new link sets it up")

    # red until A-42/A-43
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("active", "set_up_before"), NOT_WAITING_WITH_A_STRAY_LINK)
    @pytest.mark.parametrize("way", DEACTIVATIONS)
    async def test_deactivating_an_account_that_does_not_wait_retires_its_setup_links(self, private: _Private, way: str, active: bool, set_up_before: bool) -> None:
        """UADM-075 (A-43): veteran, an administrator that does not wait for its setup — active, or inactive and set up before, its first setup link consumed by itself —, holds a stray live setup link (rows of the token service: the race of A-42, or an earlier 1.3 build). Deactivated — root's PATCH {is_active: false} (200) or ./dev.py user deactivate —, its never-consumed setup link is retired: inspected → revoked, nothing more; offered at once to POST /auth/setup → 400 TOKEN_INVALID, every row of users and account_tokens as it was; GET /users lists it inactive, pending_setup false; and PATCH {is_active: true} → 200, active again — not 409 PENDING_SETUP —, its own password signing it in. Today the stray link stays valid: an active administrator so deactivated waits — inactive, a setup link, none consumed —, listed pending_setup true, its reactivation refused, and the link sets its password."""
        print_section(f"UADM-075: an administrator that does not wait, active={active}, set up before={set_up_before}, deactivated ({way})")
        _, cookie = await _admin(private)
        veteran = await _add_user(private, "veteran", admin=True, active=active)
        if set_up_before:
            await _private_link(private, veteran.user_id, ADMIN_SETUP, "consumed")
        stray = await _private_issue(private, ADMIN_SETUP, user_id=veteran.user_id)
        assert veteran.user_id not in await _pending_admin_ids(private), "premise: veteran does not wait for a setup — active, or its setup link spent (UADM-061)"

        off = await _deactivate(private, cookie, veteran, way)

        inspected = _inspected(await _inspect_setup_link(private, stray.token))
        before = await _private_snapshot(private)
        setup = await _setup_with(private, stray.token)
        changes = _snapshot_changes(before, await _private_snapshot(private))
        listed = (await _private_listed(private, cookie)).get(veteran.user_id)
        on = await _call(private, "PATCH", f"/users/{veteran.user_id}", cookie=cookie, json={"is_active": True})
        state = (await _private_user(private, veteran.user_id))[:2]
        signed_in = await _call(private, "POST", "/auth/login", json={"username": veteran.username, "password": veteran.password})

        violations: list[str] = []
        if off is not None:
            _expect(violations, off.status_code == 200, f"root's PATCH {{is_active: false}} must answer 200: {off.status_code} {off.text}")
        _expect(violations, inspected == INSPECTED_REVOKED, f"red until A-43: deactivating an account that does not wait must retire its never-consumed setup link: inspected, {INSPECTED_REVOKED}; got {inspected}")
        _expect(violations, _refusal(setup) == (400, "TOKEN_INVALID"), f"POST /auth/setup with the stray link: expected 400 TOKEN_INVALID, got {setup.status_code} {setup.text} — its holder takes the account over")
        _expect(violations, changes == {}, f"the refused setup must change nothing — rows that changed: {changes}")
        violations += [f"listed after the deactivation: {violation}" for violation in _user_item_violations(listed, veteran, active=False, superuser=True)]
        _expect(violations, (on.status_code, state) == (200, (True, True)), f"PATCH {{is_active: true}} must reactivate it, not refuse it: {on.status_code} {on.text}; (is_active, is_superuser) {state}")
        _expect(violations, signed_in.status_code == 200, f"reactivated, the account must sign in with its own password: {signed_in.status_code} {signed_in.text}")
        assert not violations, f"Deactivating an account that does not wait must retire its setup links:{_verdict(violations)}"
        print_success("the stray link retired; pending no more; reactivated by the PATCH")

    # red until A-42/A-43
    @pytest.mark.asyncio
    async def test_a_protected_pending_administrator_refuses_the_cancellation_and_keeps_its_link(self, private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-079 (A-43; coordinator 17/10, after the review — today 200 and its link revoked: the route asks the hook about an active account's deactivation only, and the pending administrator is inactive already): the hook of lot A7 protects the pending administrator (replaced in this process, ``_protect``), and root cancels its setup link — PATCH {is_active: false} on it —: 409 ACCOUNT_PROTECTED, ``detail.reason`` the hook's reason (point 12), and nothing changes, all or nothing — every row of users and account_tokens as it was, the setup link the bootstrap handed over neither revoked nor consumed; its row in GET /users (protected true, pending_setup true) and the usage identical. The account still waits — the filter selects it —, its link inspects valid, and it still sets the account up afterwards: POST /auth/setup → 200, the account active and an administrator.

        Positive control: UADM-074 (``patch-by-root``; UADM-062 too) — the same PATCH on the pending administrator the hook
        does not protect → 200, its link revoked, the account still waiting. Root stays an active administrator the hook
        never protects, so LAST_ADMIN never applies: only the hook can refuse. ``./dev.py user deactivate`` stays above the
        protection, as for every protection: not this case's subject.
        """
        print_section("UADM-079: PATCH {is_active: false} on a protected pending administrator")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id
        _protect(monkeypatch, user_id)
        assert user_id in await _pending_admin_ids(private), "premise: pending_admin_filter() selects the pending administrator"
        listed_before, usage_before = await _private_view(private, cookie, user_id)
        assert listed_before is not None, "Presence barrier: GET /users must list the pending administrator, or «its row identical» below proves nothing"
        before = await _private_snapshot(private)

        response = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json={"is_active": False})

        after = await _private_snapshot(private)
        listed_after, usage_after = await _private_view(private, cookie, user_id)
        waiting = user_id in await _pending_admin_ids(private)
        inspected = _inspected(await _inspect_setup_link(private, pending.token))
        setup = await _setup_with(private, pending.token)
        state = (await _private_user(private, user_id))[:2]
        detail = _detail(response)
        handed_over = [(row["user_id"], row["purpose"], row["consumed_at"], row["revoked_at"]) for row in after["account_tokens"] if row["token_hash"] == hash_token(pending.token)]
        changes = _snapshot_changes(before, after)
        violations: list[str] = []
        _expect(violations, _refusal(response) == (409, "ACCOUNT_PROTECTED"), f"red until A-43: the cancellation of a protected pending administrator's setup link must be refused, 409 ACCOUNT_PROTECTED: got {response.status_code} {response.text}")
        _expect(violations, detail.get("reason") == PROTECTION_REASON, f"the refusal must carry the hook's reason, {PROTECTION_REASON!r}: detail {detail}")
        _expect(violations, handed_over == [(user_id, ADMIN_SETUP.value, None, None)], f"the setup link handed over must still be live, neither revoked nor consumed: (user_id, purpose, consumed_at, revoked_at) {handed_over}")
        _expect(violations, changes == {}, f"a refused PATCH must change nothing, all or nothing — rows that changed: {changes}")
        violations += [f"listed after the PATCH: {violation}" for violation in _user_item_violations(listed_after, pending.account, active=False, superuser=True, protected=True, pending_setup=True)]
        _expect(violations, (_comparable(listed_after), usage_after) == (_comparable(listed_before), usage_before), f"its row in GET /users and the usage must be identical: before {listed_before} {usage_before}, after {listed_after} {usage_after}")
        _expect(violations, waiting, "the account must still wait for its setup: pending_admin_filter() no longer selects it")
        _expect(violations, (inspected[0], inspected[1].get("status")) == (200, "valid"), f"its setup link must still inspect valid: {inspected}")
        _expect(violations, (setup.status_code, state) == (200, (True, True)), f"its link must still set it up, an administrator: POST /auth/setup answered {setup.status_code} {setup.text}; (is_active, is_superuser) {state}")
        assert not violations, f"A protected pending administrator must refuse the cancellation of its setup link, and change nothing:{_verdict(violations)}"
        print_success("409 ACCOUNT_PROTECTED with the hook's reason; nothing changed; its link still sets it up")


# ============================================================================
# IN-PROCESS, ON THE MIGRATED SCHEMA: DELETING THE PENDING ADMINISTRATOR (lot A-43, coordinator 17/10 11:45)
# ============================================================================


#: The states in which the pending administrator waits, for its deletion (UADM-076): its setup link live, expired,
#: revoked — as the cancellation of A-43 leaves it —, or revoked and a new one live — as ``./dev.py user setup-link`` leaves it.
WAITING_STATES = [
    pytest.param("live", id="its-link-live"),
    pytest.param("expired", id="its-link-expired"),
    pytest.param("revoked", id="its-link-revoked"),
    pytest.param("re-armed", id="re-armed-by-setup-link"),
]
#: How its setup links read in each of WAITING_STATES, oldest first.
WAITING_LINK_STATUSES = {
    "live": [TokenStatus.VALID],
    "expired": [TokenStatus.EXPIRED],
    "revoked": [TokenStatus.REVOKED],
    "re-armed": [TokenStatus.REVOKED, TokenStatus.VALID],
}
#: Administrators that do not wait for their setup, beside the pending one (UADM-077): still to be demoted first — active
#: or not, holding a stray setup link or set up before.
ADMINISTRATORS_NOT_WAITING = [
    pytest.param(_SetupScene(active=True, superuser=True, tokens=(), pending_setup=False), id="an-active-administrator"),
    pytest.param(_SetupScene(active=True, superuser=True, tokens=((ADMIN_SETUP, "live"),), pending_setup=False), id="an-active-administrator-with-a-stray-setup-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=(), pending_setup=False), id="an-inactive-administrator-without-any-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "consumed"),), pending_setup=False), id="an-inactive-administrator-whose-setup-link-was-spent"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "consumed"), (ADMIN_SETUP, "live")), pending_setup=False), id="an-inactive-administrator-set-up-before-with-a-stray-link"),
]


async def _setup_link_status(private: _Private, token: str) -> TokenStatus:
    """How ``token`` reads as an ``admin_setup`` link, read fresh: ``unknown`` once its row is gone."""
    async with AsyncSession(private.engine) as session:
        return (await inspect_token(session, token, ADMIN_SETUP)).status


async def _waiting_in_state(private: _Private, state: str) -> tuple[_PendingAdmin, list[str]]:
    """The pending administrator the bootstrap makes (run it first: the instance must hold no account), brought to ``state`` (WAITING_STATES) by the services, never by the route under test: ``revoked`` by ``token_service.revoke_tokens``, ``re-armed`` by ``issue_setup_link`` — the call ``./dev.py user setup-link`` makes. With the tokens of its setup links, oldest first.

    It ends on its promise: the account waits for its setup (``pending_admin_filter()`` selects it), and its links read
    as WAITING_LINK_STATUSES says.
    """
    pending = await _bootstrap_pending_admin(private, expired=state == "expired")
    tokens = [pending.token]
    if state in ("revoked", "re-armed"):
        async with AsyncSession(private.engine, expire_on_commit=False) as session:
            if state == "revoked":
                revoked = await revoke_tokens(session, user_id=pending.account.user_id, purpose=ADMIN_SETUP)
                assert revoked == 1, f"Setup: the cancellation revokes the one live setup link: {revoked}"
            else:
                issued = await issue_setup_link(session)
                assert issued is not None, "Setup: ./dev.py user setup-link must give the pending administrator a new link"
                tokens.append(issued.token)
            await session.commit()
    statuses = [await _setup_link_status(private, token) for token in tokens]
    assert statuses == WAITING_LINK_STATUSES[state], f"Setup: its setup links must read {WAITING_LINK_STATUSES[state]}, they read {statuses}"
    assert pending.account.user_id in await _pending_admin_ids(private), f"Setup: its links {state}, the account must still wait for its setup"
    return pending, tokens


class TestDeletingThePendingAdministrator:
    """Lot A-43 (coordinator, 17/10 11:45): its demotion refused, the pending administrator is deleted directly — no DEMOTE_FIRST —, the account and its tokens gone as any deletion removes them; every other administrator is still to be demoted first, and the hook of lot A7 still answers first. In-process, on the migrated schema (``private_head``), as A6a's deletions: a deletion relies on the production schema's cascades."""

    # red until A-42/A-43
    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", WAITING_STATES)
    async def test_the_pending_administrator_is_deleted_directly(self, private_head: _Private, state: str) -> None:
        """UADM-076 (A-43, coordinator 17/10 11:45; today 409 DEMOTE_FIRST, and nothing deleted): root deletes the pending administrator — the bootstrap's, its setup links live, expired, revoked as a cancellation leaves them, or re-armed by ``./dev.py user setup-link`` (``_waiting_in_state``) —: DELETE /users/{it} → 204 with no body, as any deletion. Exactly what ``user_service.delete_account`` removes, and nothing else: its row of ``users``, and every row of ``account_tokens`` of it — its setup links — by the schema's cascade; every other row of both tables as it was. Afterwards GET /users no longer lists it and the usage frees its place (used 2 → 1: root and it, then root); nobody waits any more — ``pending_admin_filter()`` selects nobody, and ``./dev.py user setup-link`` (``issue_setup_link``) finds nobody to give a link to —; each of its links inspects ``unknown``, and POST /auth/setup with it → 400 TOKEN_INVALID.

        Presence barrier: GET /users lists it before the deletion, so «no longer listed» proves something.
        """
        print_section(f"UADM-076: DELETE of the pending administrator, its links {state}")
        pending, links = await _waiting_in_state(private_head, state)
        _, cookie = await _admin(private_head)
        user_id = pending.account.user_id
        listed_before, usage_before = await _private_view(private_head, cookie, user_id)
        assert listed_before is not None, "Presence barrier: GET /users must list the pending administrator before its deletion, or «no longer listed» below proves nothing"
        before = await _private_snapshot(private_head)
        gone = {
            "users": {"before": [row for row in before["users"] if row["id"] == user_id], "after": []},
            "account_tokens": {"before": [row for row in before["account_tokens"] if row["user_id"] == user_id], "after": []},
        }
        assert len(gone["account_tokens"]["before"]) == len(links), f"Setup: the pending administrator's tokens must be its {len(links)} setup link(s): {gone['account_tokens']['before']}"

        response = await _call(private_head, "DELETE", f"/users/{user_id}", cookie=cookie)

        changes = _snapshot_changes(before, await _private_snapshot(private_head))
        listed_after, usage_after = await _private_view(private_head, cookie, user_id)
        waiting = await _pending_admin_ids(private_head)
        new_link = await _a_new_setup_link(private_head)
        statuses = [await _setup_link_status(private_head, token) for token in links]
        setups = [_refusal(await _setup_with(private_head, token)) for token in links]
        violations: list[str] = []
        _expect(violations, (response.status_code, response.content) == (204, b""), f"red until A-43: the pending administrator is deleted directly — its demotion is refused, there is nothing to demote first —: expected 204 with no body, got {response.status_code} {response.text}")
        _expect(violations, changes == gone, f"the deletion must remove its row and its tokens, and nothing else: expected the rows that change to be {gone}; rows that changed: {changes}")
        _expect(violations, listed_after is None, f"GET /users must no longer list it: {listed_after}")
        _expect(violations, (usage_before.get("used"), usage_after.get("used")) == (2, 1), f"its place must be free: used, before and after, expected (2, 1): before {usage_before}, after {usage_after}")
        _expect(violations, waiting == set() and new_link is None, f"nobody must wait any more: pending_admin_filter() selects {waiting}, ./dev.py user setup-link {'issued a link' if new_link else 'found nobody'}")
        _expect(violations, statuses == [TokenStatus.UNKNOWN] * len(links), f"each of its setup links must inspect unknown, its row gone: {statuses}")
        _expect(violations, setups == [(400, "TOKEN_INVALID")] * len(links), f"POST /auth/setup with each of its links must answer 400 TOKEN_INVALID: {setups}")
        assert not violations, f"The pending administrator must be deleted directly, as any deletion removes an account:{_verdict(violations)}"
        print_success("204: the account and its setup links gone, its place free, nobody waiting")

    # guard
    @pytest.mark.asyncio
    @pytest.mark.parametrize("scene", ADMINISTRATORS_NOT_WAITING)
    async def test_any_other_administrator_must_still_be_demoted_first(self, private_head: _Private, scene: _SetupScene) -> None:
        """UADM-077, guard of UADM-076 (green today and after): the direct deletion is the pending administrator's alone — not the instance's while one waits, nor every inactive administrator's, nor every account that ever had a setup link. Beside it, another administrator — active or not, holding a stray setup link or set up before, the only OWNER of a broker with a DEPOSIT —: DELETE → 409 DEMOTE_FIRST, and nothing deleted — every row of users and account_tokens, every broker, grant and transaction as it was.

        Premise: the filter selects the pending administrator, and only it.
        """
        print_section(f"UADM-077: DELETE of another administrator, active={scene.active}, tokens {[(purpose.value, state) for purpose, state in scene.tokens]}")
        pending = await _bootstrap_pending_admin(private_head)
        _, cookie = await _admin(private_head)
        subject = await _add_user(private_head, "subject", admin=True, active=scene.active)
        for purpose, link_state in scene.tokens:
            await _private_link(private_head, subject.user_id, purpose, link_state)
        await _private_broker(private_head, "Subject's broker", [(subject.user_id, UserRole.OWNER)], deposits=1)
        assert await _pending_admin_ids(private_head) == {pending.account.user_id}, "premise: pending_admin_filter() selects the pending administrator, and only it"
        before = (await _private_snapshot(private_head), await _private_holdings(private_head))

        response = await _call(private_head, "DELETE", f"/users/{subject.user_id}", cookie=cookie)

        after = (await _private_snapshot(private_head), await _private_holdings(private_head))
        violations: list[str] = []
        _expect(violations, _refusal(response) == (409, "DEMOTE_FIRST"), f"DELETE of an administrator that does not wait for its setup: expected 409 DEMOTE_FIRST, got {response.status_code} {response.text}")
        _expect(violations, _snapshot_changes(before[0], after[0]) == {}, f"a refused deletion must change no account and no token — rows that changed: {_snapshot_changes(before[0], after[0])}")
        _expect(violations, after[1] == before[1], f"a refused deletion must delete nothing: before {before[1]}, after {after[1]}")
        assert not violations, f"Any other administrator must still be demoted before it can be deleted:{_verdict(violations)}"
        print_success("409 DEMOTE_FIRST, nothing deleted")

    # guard
    @pytest.mark.asyncio
    async def test_the_hook_still_answers_first_for_the_pending_administrator(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-078, guard of UADM-076 (green today and after): the hook of lot A7 still answers before any other answer (point 12, UADM-051), the new deletion path included: the pending administrator, protected by the hook (replaced in this process, ``_protect``) → DELETE → 409 ACCOUNT_PROTECTED, and nothing deleted — every row of users and account_tokens as it was —; it still waits."""
        print_section("UADM-078: DELETE of a protected pending administrator")
        pending = await _bootstrap_pending_admin(private_head)
        _, cookie = await _admin(private_head)
        user_id = pending.account.user_id
        _protect(monkeypatch, user_id)
        before = await _private_snapshot(private_head)

        response = await _call(private_head, "DELETE", f"/users/{user_id}", cookie=cookie)

        changes = _snapshot_changes(before, await _private_snapshot(private_head))
        violations: list[str] = []
        _expect(violations, _refusal(response) == (409, "ACCOUNT_PROTECTED"), f"DELETE of the pending administrator the hook protects: expected 409 ACCOUNT_PROTECTED, got {response.status_code} {response.text}")
        _expect(violations, changes == {}, f"a refused deletion must change nothing — rows that changed: {changes}")
        _expect(violations, user_id in await _pending_admin_ids(private_head), "the pending administrator must still wait for its setup")
        assert not violations, f"The hook must still answer first, for the pending administrator too:{_verdict(violations)}"
        print_success("409 ACCOUNT_PROTECTED, nothing deleted, still waiting")


# ============================================================================
# IN-PROCESS: THE SETUP COMPLETED WHILE THE USERS TAB ACTS (lot A-51)
# ============================================================================


#: The Users tab's cancellation of a setup (A-51): the deactivation of the account waiting for its setup, and nothing else.
CANCEL_SETUP = {"is_active": False, "cancel_setup": True}
#: Bodies asking ``cancel_setup`` without ``is_active: false`` (A51-004): refused whole, 422, whatever else they ask.
CANCEL_SETUP_WITHOUT_A_DEACTIVATION = [
    pytest.param({"cancel_setup": True}, id="is-active-absent"),
    pytest.param({"cancel_setup": True, "is_active": None}, id="is-active-null"),
    pytest.param({"cancel_setup": True, "is_superuser": False}, id="is-active-absent-beside-a-demotion"),
    pytest.param({"cancel_setup": True, "is_active": True}, id="beside-an-activation"),
]
#: The database as the rival's setup left it, appended once that setup committed (``_setup_completed_meanwhile``): what a refused request must leave as it is.
Landed = list[dict[str, list[dict[str, Any]]]]


async def _setup_completed_meanwhile(private: _Private, token: str, landed: Landed) -> None:
    """The rival of A-51: the pending administrator's setup completed through ``token`` with SETUP_PASSWORD — ``complete_admin_setup``, what POST /auth/setup runs — on a connection of its own, as another worker serves it, committed; the database as it leaves it appended to ``landed``."""
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        user = await complete_admin_setup(session, token, SETUP_PASSWORD)
    assert user is not None and user.is_active, f"Setup: the rival's setup must complete: {user!r}"
    landed.append(await _private_snapshot(private))


def _setup_lands_after_the_first_read(monkeypatch: pytest.MonkeyPatch, private: _Private, token: str, landed: Landed) -> list[bool]:
    """The window of A-51, played without threads: ``registration_service.is_pending_admin`` replaced. Its first call reads the database — the account still waits: True —, then the setup lands (``_setup_completed_meanwhile``) before the call answers what it read; every later call reads afresh. What each call answered, in order: the barrier.

    The route loads the account and reads whether it waits before its first write, and pysqlite defers BEGIN to that
    write: nothing holds the account meanwhile. The setup landing right after those reads leaves the route an account it
    loaded inactive and «waiting» true, while the database holds the administrator active. The service's reading is a
    later call: ``user_service._is_pending_admin`` imports the function when it runs. The rival writes on its own
    connection while the request holds no lock: the cure keeps the route's first reading before the lock, and reads
    «waiting» again under it (the coordinator's contract, 17/10). The PATCH's window (A51-002, A51-005): since A-55 the
    DELETE reads «waiting» under the lock only, where a setup landing would wait for the request's own lock, and A51-006
    plays its window with ``_window``.
    """
    real = registration_service.is_pending_admin
    answers: list[bool] = []

    async def is_pending_admin(session: AsyncSession, user: User) -> bool:
        answer = await real(session, user)
        answers.append(answer)
        if len(answers) == 1:
            await _setup_completed_meanwhile(private, token, landed)
        return answer

    monkeypatch.setattr(registration_service, "is_pending_admin", is_pending_admin)
    return answers


def _account_row(snapshot: dict[str, list[dict[str, Any]]], user_id: int) -> Optional[dict[str, Any]]:
    """The ``users`` row of ``user_id`` in a ``_private_snapshot``; None when it is not there."""
    return next((row for row in snapshot["users"] if row["id"] == user_id), None)


class TestTheSetupCompletedWhileTheUsersTabActs:
    """Lot A-51 (cure approved by the coordinator, 17/10): the Users tab acts on the account waiting for its setup while that setup completes — the tab's row stale for minutes, or the very window between the route's reads and its first write. ``cancel_setup`` cancels a setup still waiting and nothing else, refused 409 SETUP_COMPLETED once the setup is done; a plain deactivation answers what the database holds; a deletion asks to demote first. In-process only, as A-43's: a pending administrator never enters the lane's database; the deletion on the migrated schema (``private_head``), as UADM-076. The guards of the cancellation and the deletion of an administrator still waiting are UADM-062 and UADM-074 (``{is_active: false}``), UADM-076 (``DELETE``): not repeated here."""

    # red until A-51
    @pytest.mark.asyncio
    async def test_a_stale_tab_does_not_cancel_a_setup_completed_since(self, private: _Private) -> None:
        """A51-001 — NEW, red until A-51 (today 422: ``cancel_setup`` is no field; the tab's {is_active: false} alone deactivates the new owner): GET /users listed the pending administrator pending_setup true, then the administrator completed its setup through its link (POST /auth/setup: 200, signed in) — the tab's row is stale. Root cancels from it, PATCH {is_active: false, cancel_setup: true} → 409 SETUP_COMPLETED, and nothing changes: every row of users and account_tokens as it was — the administrator active, an administrator, its session version —; its own session still answers GET /auth/me; GET /users lists it active, pending_setup false, exactly its nine fields."""
        print_section("A51-001: the cancellation from a stale tab, the setup completed since")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id
        stale_row = (await _private_listed(private, cookie)).get(user_id)
        assert stale_row is not None and stale_row.get("pending_setup") is True, f"Setup: the tab's row offers the cancellation — listed pending_setup true before the setup: {stale_row}"
        setup = await _setup_with(private, pending.token)
        owner_cookie = _session_cookie(setup)
        assert setup.status_code == 200 and owner_cookie, f"Setup: the administrator completes its setup through its link, and is signed in: {setup.status_code} {setup.text}"
        before = await _private_snapshot(private)

        response = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json=CANCEL_SETUP)

        changes = _snapshot_changes(before, await _private_snapshot(private))
        me = _answer(await _call(private, "GET", "/auth/me", cookie=owner_cookie))
        listed = (await _private_listed(private, cookie)).get(user_id)
        violations: list[str] = []
        _expect(violations, _refusal(response) == (409, "SETUP_COMPLETED"), f"red until A-51: the setup was completed since the tab listed it, so its cancellation must be refused, 409 SETUP_COMPLETED: got {response.status_code} {response.text}")
        _expect(violations, changes == {}, f"a refused cancellation must change nothing, all or nothing — rows that changed: {changes}")
        _expect(violations, me[0] == 200 and me[1]["user"]["id"] == user_id, f"the administrator's own session must still be valid: GET /auth/me with the cookie its setup gave answered {me}")
        violations += [f"listed after the refusal: {violation}" for violation in _user_item_violations(listed, pending.account, active=True, superuser=True)]
        assert not violations, f"A stale tab must not cancel a setup completed since:{_verdict(violations)}"
        print_success("409 SETUP_COMPLETED; nothing changed; the new owner still signed in")

    # red until A-51
    @pytest.mark.asyncio
    async def test_the_cancellation_refuses_a_setup_completed_in_its_window(self, private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """A51-002 — NEW, red until A-51 (today 422: ``cancel_setup`` is no field; the same window with {is_active: false} alone is A51-005): root cancels the pending administrator's setup, PATCH {is_active: false, cancel_setup: true}, and the setup completes in the request's window — after the route read the account waiting, before its first write (``_setup_lands_after_the_first_read``). The cancellation is decided under the lock: → 409 SETUP_COMPLETED, and nothing changes since the setup landed — every row of users and account_tokens as the setup left them: the administrator active, an administrator, its session version, so its sessions alive.

        Barrier: the route's first reading answered True, and the setup landed once, in the window.
        """
        print_section("A51-002: the cancellation, the setup completed in the request's window")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id
        landed: Landed = []
        answers = _setup_lands_after_the_first_read(monkeypatch, private, pending.token, landed)

        response = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json=CANCEL_SETUP)

        changes = _snapshot_changes(landed[0], await _private_snapshot(private)) if landed else "the setup never landed"
        state = (await _private_user(private, user_id))[:2]
        violations: list[str] = []
        _expect(violations, _refusal(response) == (409, "SETUP_COMPLETED"), f"red until A-51: the setup completed between the route's reading and its first write, so the cancellation must be refused under the lock, 409 SETUP_COMPLETED: got {response.status_code} {response.text}")
        _expect(violations, answers[:1] == [True] and len(landed) == 1, f"barrier: the route must read the account waiting, then the setup land once — the window of A-51: is_pending_admin answered {answers}, the setup landed {len(landed)} time(s)")
        _expect(violations, changes == {}, f"a refused cancellation must change nothing since the setup landed, all or nothing — rows that changed: {changes}")
        _expect(violations, state == (True, True), f"the administrator just set up must stay active, an administrator: (is_active, is_superuser) {state}")
        assert not violations, f"The cancellation must refuse a setup completed in its window, and change nothing:{_verdict(violations)}"
        print_success("409 SETUP_COMPLETED; nothing changed since the setup")

    # red until A-51
    @pytest.mark.asyncio
    async def test_cancel_setup_cancels_the_setup_of_the_pending_administrator(self, private: _Private) -> None:
        """A51-003 — NEW, red until A-51 (today 422: ``cancel_setup`` is no field): on the pending administrator, still waiting, PATCH {is_active: false, cancel_setup: true} is the cancellation of A-43, as {is_active: false} is (UADM-062, UADM-074): 200 with its row — inactive, an administrator, pending_setup true, exactly its nine fields —; its setup link revoked — inspected, revoked and nothing more —; and the account still waits — the filter selects it —, inactive, an administrator."""
        print_section("A51-003: cancel_setup on the pending administrator, still waiting")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id

        response = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json=CANCEL_SETUP)

        inspected = _inspected(await _inspect_setup_link(private, pending.token))
        waiting = user_id in await _pending_admin_ids(private)
        state = (await _private_user(private, user_id))[:2]
        violations: list[str] = []
        _expect(violations, response.status_code == 200, f"red until A-51: {{is_active: false, cancel_setup: true}} on the administrator still waiting is the cancellation of A-43: expected 200, got {response.status_code} {response.text}")
        if response.status_code == 200:
            violations += [f"the PATCH's answer: {violation}" for violation in _user_item_violations(response.json(), pending.account, active=False, superuser=True, pending_setup=True)]
        _expect(violations, inspected == INSPECTED_REVOKED, f"the cancellation must revoke its setup link: inspected, {INSPECTED_REVOKED}; got {inspected}")
        _expect(violations, waiting and state == (False, True), f"the account must still wait for its setup, inactive, an administrator: the filter selects it {waiting}; (is_active, is_superuser) {state}")
        assert not violations, f"cancel_setup must cancel the setup of the administrator still waiting:{_verdict(violations)}"
        print_success("200; its link revoked; still waiting")

    # guard
    @pytest.mark.asyncio
    @pytest.mark.parametrize("body", CANCEL_SETUP_WITHOUT_A_DEACTIVATION)
    async def test_cancel_setup_without_a_deactivation_is_refused_whole(self, private: _Private, body: dict[str, Any]) -> None:
        """A51-004 — GUARD, green today (``cancel_setup`` is no field) and after (allowed only beside is_active: false): PATCH /users/{the pending administrator} with cancel_setup: true and ``is_active`` absent, null or true — alone, beside a demotion, beside an activation — → 422, and nothing changes: every row of users and account_tokens as it was, its setup link still valid."""
        print_section(f"A51-004: PATCH {body} on the pending administrator")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id
        before = await _private_snapshot(private)

        response = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json=body)

        changes = _snapshot_changes(before, await _private_snapshot(private))
        status, shown = _inspected(await _inspect_setup_link(private, pending.token))
        violations: list[str] = []
        _expect(violations, response.status_code == 422, f"PATCH {body}: cancel_setup goes only beside is_active: false — expected 422, got {response.status_code} {response.text}")
        _expect(violations, changes == {}, f"a refused PATCH must change nothing — rows that changed: {changes}")
        _expect(violations, (status, shown.get("status")) == (200, "valid"), f"its setup link must stay valid: {status} {shown}")
        assert not violations, f"cancel_setup without is_active: false must be refused whole:{_verdict(violations)}"
        print_success("422; nothing changed")

    # red until A-51
    @pytest.mark.asyncio
    async def test_a_deactivation_in_the_setups_window_answers_what_the_database_holds(self, private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """A51-005 — NEW, red until A-51 (today 200 with the account inactive — as the route loaded it, before the setup — beside a fresh pending_setup false, while the database holds it active: a stale answer, nothing deactivated): root's plain PATCH {is_active: false} on the pending administrator, the setup completing in the request's window (A51-002's). A plain deactivation keeps its meaning, decided on what the database holds under the lock: → 200; the answer's is_active and pending_setup are the database's right after; the account is active no more — deactivated, still an administrator —, and its sessions ended: its session version above the one the setup left. Root, another active administrator, keeps it from being the last.

        Barrier: the route's first reading answered True, and the setup landed once, in the window.
        """
        print_section("A51-005: a plain deactivation, the setup completed in the request's window")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id
        landed: Landed = []
        answers = _setup_lands_after_the_first_read(monkeypatch, private, pending.token, landed)

        response = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json={"is_active": False})

        state = await _private_user(private, user_id)
        held = {"is_active": state[0], "pending_setup": user_id in await _pending_admin_ids(private)}
        answer = response.json() if response.status_code == 200 else {}
        told = {key: answer.get(key) for key in held}
        set_up = _account_row(landed[0], user_id) if landed else None
        violations: list[str] = []
        _expect(violations, response.status_code == 200, f"a plain deactivation must still answer 200: got {response.status_code} {response.text}")
        _expect(violations, told == held, f"red until A-51: the answer must be what the database holds right after — it answered {told}, the database holds {held}: {answer}")
        _expect(violations, state[:2] == (False, True), f"red until A-51: decided on what the database holds, the deactivation must deactivate the administrator just set up — root keeps it from being the last —, still an administrator: (is_active, is_superuser) {state[:2]}")
        _expect(violations, set_up is not None and state[2] > set_up["session_version"], f"a deactivation must end its sessions: its session version must rise above the one its setup left ({set_up['session_version'] if set_up else None}): {state[2]}")
        _expect(violations, answers[:1] == [True] and len(landed) == 1, f"barrier: the route must read the account waiting, then the setup land once — the window of A-51: is_pending_admin answered {answers}, the setup landed {len(landed)} time(s)")
        assert not violations, f"A deactivation in the setup's window must answer what the database holds:{_verdict(violations)}"
        print_success("200, the answer the database's: deactivated, its sessions ended")

    # red until A-51
    @pytest.mark.asyncio
    async def test_a_deletion_in_the_setups_window_asks_to_demote_first(self, private_head: _Private) -> None:
        """A51-006 — NEW, red until A-51 (today 204: the route read «waiting» before the deletion's writes, so it deletes the administrator just set up, never asked to demote it first): root deletes the pending administrator, DELETE /users/{it}, and the setup completes in the request's window — after the route loaded the account, still waiting, and right before its first write: POST /auth/setup through the account's link, served on the instance's own engine as another worker serves it (``_setup_completes``, in the window of the UADM-LOCK cases, ``_window``). Decided under the lock, on the account as it then is: → 409 DEMOTE_FIRST, and nothing deleted — every row of users, account_tokens and the accounts' settings and onboarding, every account, broker, grant and transaction as the setup left them: the account there, active, an administrator. On the migrated schema, as UADM-076: a deletion relies on its cascades.

        Since A-55 the route reads «waiting» under the lock only: A51-002's window (``_setup_lands_after_the_first_read``, the setup landing inside the route's first ``is_pending_admin``) would land it while the request holds its own write lock, the setup's write waiting for the request that waits for it — «database is locked». The window this case means — the route holding an account it loaded still waiting, while nothing holds the row — ends at the route's first write: the setup lands there.

        Barrier (``_landing_violations``): the setup landed once, right before the request's first write, after the request read the account; the account still waited when the setup began — so when the route read it, nothing writing in between —; POST /auth/setup answered 200.
        """
        print_section("A51-006: the deletion, the setup completed in the request's window")
        pending = await _bootstrap_pending_admin(private_head)
        _, cookie = await _admin(private_head)
        user_id = pending.account.user_id
        waited: list[bool] = []

        outcome, window = await _in_the_window(private_head, _setup_completes(private_head, pending.token, user_id, waited), "DELETE", f"/users/{user_id}", cookie=cookie)

        after = await _lock_state(private_head)
        changes = _since_the_rival(window, after)
        row = _account_row(after[0], user_id)
        violations = _landing_violations(window, user_id, 200)
        _expect(violations, waited == [True], f"barrier: the account must still wait for its setup when the setup begins — so when the route read it —: the filter selected it {waited}")
        _expect(violations, _coded(outcome) == (409, "DEMOTE_FIRST"), f"red until A-51: the setup completed between the route's read and the deletion's first write; decided under the lock, the administrator just set up must be demoted first, 409 DEMOTE_FIRST: got {_shown(outcome)}")
        _expect(violations, changes == {}, f"a refused deletion must delete nothing: the database as the setup left it — what changed: {changes}")
        _expect(violations, row is not None and (row["is_active"], row["is_superuser"]) == (True, True), f"the account must be there, active, an administrator: {row}")
        assert not violations, f"A deletion in the setup's window must ask to demote first, and delete nothing:{_verdict(violations)}"
        print_success(f"409 DEMOTE_FIRST; nothing deleted; the setup landed before «{_first_write(window)}»")


# ============================================================================
# IN-PROCESS, ON THE MIGRATED SCHEMA: DECIDED UNDER THE WRITE LOCK (lot A-54 + A-55 + A-56)
# ============================================================================


#: The first word of the statements that open a write in SQLite: the rival commits right before the first of them. A-42's
#: ``WRITE_STATEMENTS`` (``test_admin_bootstrap.py``), copied: that module is written in parallel, and a red of its own at
#: import would take this one down with it.
WRITE_STATEMENTS = frozenset({"INSERT", "UPDATE", "DELETE", "REPLACE", "BEGIN", "SAVEPOINT"})
#: ``_user_or_404``'s answer, word for word: the answer to a request on an account deleted in its window (A-54).
USER_NOT_FOUND = (404, {"detail": "User not found"})
#: The limit of A-56's scenes: root and peer, active administrators, take two places; one is left.
LOCK_LIMIT = 3
#: The status each rival's own request is served with — its barrier —: the target deleted or promoted by peer, sleeper
#: reactivated by peer, peer's invitation created.
RIVAL_STATUSES = {"deletion": 204, "promotion": 200, "reactivation": 200, "invitation": 201}
#: (is_active, is_superuser) of the target of each kind of ``_lock_scene``; ``pending`` is the bootstrap's administrator, waiting for its setup.
TARGET_FLAGS = {"active": (True, False), "inactive": (False, False), "admin": (True, True), "pending": (False, True)}
#: A-54's PATCHes (UADM-LOCK-01, guarded by UADM-LOCK-06): the target's kind, the body, and the target's (is_active,
#: is_superuser) once the PATCH is served with nobody acting in its window.
PATCH_CASES: dict[str, tuple[str, dict[str, Any], tuple[bool, bool]]] = {
    "deactivate-an-active-account": ("active", {"is_active": False}, (False, False)),
    "promote-an-active-account": ("active", {"is_superuser": True}, (True, True)),
    "reactivate-an-inactive-account": ("inactive", {"is_active": True}, (True, False)),
    "cancel-the-setup-of-the-pending-administrator": ("pending", CANCEL_SETUP, (False, True)),
}
PATCHES = [pytest.param(case, id=case) for case in PATCH_CASES]
#: A-54's deletions (UADM-LOCK-02): the pending administrator — the path that reads «waiting» again under the lock (A-51)
#: — and a plain account — the path that reads nothing again.
DELETED_IN_THE_WINDOW = [pytest.param("pending", id="the-pending-administrator"), pytest.param("active", id="a-plain-account")]
#: A-55's targets (UADM-LOCK-03): a plain account, active or not; promoted, an administrator, active or not, to be demoted first (point 11).
PROMOTED_IN_THE_WINDOW = [pytest.param("active", id="an-active-account"), pytest.param("inactive", id="an-inactive-account")]
#: A-56's rivals (UADM-LOCK-04, UADM-LOCK-05): what takes the last place in the window — sleeper reactivated, an invitation created.
LAST_PLACE_TAKERS = [pytest.param("reactivation", id="another-account-reactivated"), pytest.param("invitation", id="an-invitation-created")]
#: A-56's guards (UADM-LOCK-08, UADM-LOCK-09): who took the last place before the request — nobody, or a rival of
#: LAST_PLACE_TAKERS, its request served first.
TAKEN_BEFORE = [
    pytest.param(None, id="a-place-left"),
    pytest.param("reactivation", id="the-last-place-taken-before-by-a-reactivation"),
    pytest.param("invitation", id="the-last-place-taken-before-by-an-invitation"),
]
#: The deletions with nobody acting in the window (UADM-LOCK-07): the target's kind, whether it is the only OWNER of a
#: broker with a DEPOSIT, and (status, ``detail.error_code``). The administrator owning a broker is the state
#: UADM-LOCK-03's promotion leads to, there before the request.
DELETIONS_WITHOUT_A_RIVAL = [
    pytest.param("pending", False, (204, None), id="the-pending-administrator"),
    pytest.param("active", False, (204, None), id="a-plain-account"),
    pytest.param("active", True, (204, None), id="an-active-account-owning-a-broker"),
    pytest.param("inactive", True, (204, None), id="an-inactive-account-owning-a-broker"),
    pytest.param("admin", True, (409, "DEMOTE_FIRST"), id="an-administrator-owning-a-broker"),
]
#: The onboarding resets of A-54 (UADM-LOCK-12, guarded by UADM-LOCK-15): every flow — the request without a body —, or
#: one flow, ``import_guide``, with its steps.
ONBOARDING_RESETS = [pytest.param(None, id="every-flow-without-a-body"), pytest.param(OnboardingFlow.IMPORT_GUIDE.value, id="one-flow-import-guide")]
#: An account's own rows besides users and account_tokens — its settings, its onboarding flows and steps, which go with
#: it by the schema's cascade —: «nothing changed» reads them too (``_lock_state``).
ACCOUNT_TABLES = (UserSettings.__table__, UserOnboardingProgress.__table__, UserOnboardingStepProgress.__table__)
#: The tables of an account's onboarding: what an onboarding reset writes.
ONBOARDING_TABLES = frozenset({UserOnboardingProgress.__tablename__, UserOnboardingStepProgress.__tablename__})

#: The private database as «nothing changed» compares it: every row of users and account_tokens (``_private_snapshot``)
#: and of ACCOUNT_TABLES, by table; every account, broker, grant and transaction (``_private_holdings``).
_State = tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]


@dataclass(frozen=True)
class _RivalOutcome:
    """What a rival left once its request was served: that request's outcome (``_shown``), and the database right after."""

    answer: tuple[Any, Any]
    state: _State


@dataclass
class _Window:
    """The request under test as its own engine ran it: every statement, in order, as (SQL, parameters); ``landed_before``, the index of the write the rival ran right before — None when it never ran —; ``rival``, what the rival left."""

    statements: list[tuple[str, Any]] = field(default_factory=list)
    landed_before: Optional[int] = None
    rival: list[_RivalOutcome] = field(default_factory=list)


@dataclass(frozen=True)
class _LockScene:
    """A private instance for a race of A-54/A-55/A-56: root — the caller — and peer — the other administrator, whose requests are the rivals —, active administrators signed in; the target, of a kind of TARGET_FLAGS; sleeper, an inactive plain account that holds no place; the target's broker, when the case gives it one."""

    root: _Account
    cookie: str
    peer: _Account
    peer_cookie: str
    target: _Account
    sleeper: _Account
    broker_id: Optional[int]


@pytest.fixture
def fresh_login_limiters(monkeypatch: pytest.MonkeyPatch) -> None:
    """The sign-in's two limiters replaced by fresh ones of the shipped size (as ``test_username_rules_api.py``): no sign-in of another in-process test counts against these."""
    for name in ("LOGIN_BY_IDENTIFIER", "LOGIN_BY_ADDRESS"):
        shipped = getattr(login_throttle, name)
        monkeypatch.setattr(login_throttle, name, SlidingWindowLimiter(shipped.limit, shipped.window_seconds))


async def _lock_scene(private: _Private, kind: str, *, broker: bool = False) -> _LockScene:
    """The scene, written before the request: the pending administrator by the bootstrap — first, on the instance still empty —, every other account as a row, the target's broker with its OWNER grant and a DEPOSIT. It ends on its promise: the target as TARGET_FLAGS says, waiting for its setup when ``pending`` and only then; sleeper inactive."""
    target = (await _bootstrap_pending_admin(private)).account if kind == "pending" else None
    root, cookie = await _admin(private)
    peer, peer_cookie = await _admin(private, "peer")
    if target is None:
        target = await _add_user(private, "target", admin=kind == "admin", active=kind != "inactive")
    sleeper = await _add_user(private, "sleeper", active=False)
    broker_id = await _private_broker(private, "Target's broker", [(target.user_id, UserRole.OWNER)], deposits=1) if broker else None
    flags = (await _private_user(private, target.user_id))[:2]
    waiting = target.user_id in await _pending_admin_ids(private)
    assert (flags, waiting) == (TARGET_FLAGS[kind], kind == "pending"), f"Setup: the {kind} target must be (is_active, is_superuser) {TARGET_FLAGS[kind]}, waiting for its setup {kind == 'pending'}: {flags}, waiting {waiting}"
    assert not (await _private_user(private, sleeper.user_id))[0], "Setup: sleeper must be inactive"
    return _LockScene(root=root, cookie=cookie, peer=peer, peer_cookie=peer_cookie, target=target, sleeper=sleeper, broker_id=broker_id)


@contextlib.asynccontextmanager
async def _route_of(private: _Private) -> AsyncIterator[_Private]:
    """The instance as another worker serves it: the same routers on the same private file, through an engine of its own, which only the request under test uses. Disposed at the end."""
    engine = create_async_engine(private.engine.url, poolclass=NullPool)
    try:
        yield _Private(engine=engine, app=_private_app(engine))
    finally:
        await engine.dispose()


def _is_write(statement: str) -> bool:
    """Whether ``statement`` opens a write in SQLite: its first word is one of WRITE_STATEMENTS."""
    words = statement.split(None, 1)
    return bool(words) and words[0].upper() in WRITE_STATEMENTS


@contextlib.contextmanager
def _window(route: _Private, rival: Optional[Callable[[], Awaitable[_RivalOutcome]]]) -> Iterator[_Window]:
    """Every statement of ``route``'s engine recorded, and ``rival`` run right before the first write among them; no rival for a guard.

    A-42's ``_rival_before_the_first_write`` (``test_admin_bootstrap.py``), recording the statements besides: a
    ``before_cursor_execute`` listener on the engine of the request under test alone, armed for that request alone — the
    setup and the rival run on the instance's own engine, so neither can be «the first write». When the first INSERT,
    UPDATE, DELETE, REPLACE, BEGIN or SAVEPOINT is about to run, it awaits the rival from the request's own greenlet
    (``await_only``, as SQLAlchemy's asyncio layer awaits), then lets the statement go. pysqlite defers BEGIN to the
    first write, and in WAL a reader holds nothing once its statement is done: the request holds no lock yet, so the
    rival writes and commits on its own connection, and the transaction the request's write opens sees that commit. No
    thread and no sleep: one interleaving, every time.
    """
    window = _Window()

    def before_cursor_execute(_connection: Any, _cursor: Any, statement: str, parameters: Any, _context: Any, _executemany: bool) -> None:
        window.statements.append((statement, parameters))
        if rival is None or window.landed_before is not None or not _is_write(statement):
            return
        window.landed_before = len(window.statements) - 1
        window.rival.append(await_only(rival()))

    event.listen(route.engine.sync_engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield window
    finally:
        event.remove(route.engine.sync_engine, "before_cursor_execute", before_cursor_execute)


async def _attempt(private: _Private, method: str, path: str, *, cookie: str, json: Any = None) -> Union[httpx.Response, Exception]:
    """``_call``, or the exception it raised: in-process, an exception the route lets escape reaches the call, where a server would answer 500."""
    try:
        return await _call(private, method, path, cookie=cookie, json=json)
    except Exception as exc:  # today's red of A-54 is that exception: the verdict shows it instead of stopping at it
        return exc


def _shown(outcome: Union[httpx.Response, Exception]) -> tuple[Any, Any]:
    """An outcome as a verdict shows it: (status, the JSON body — or the text) for an answer; (the exception's type, its message) when the route raised."""
    if isinstance(outcome, httpx.Response):
        return _answer(outcome)
    return type(outcome).__name__, str(outcome)


def _coded(outcome: Union[httpx.Response, Exception]) -> tuple[Any, Optional[str]]:
    """(status, ``detail.error_code``) of an answer (``_refusal``); (the exception's type, None) when the route raised."""
    return _refusal(outcome) if isinstance(outcome, httpx.Response) else (type(outcome).__name__, None)


def _limit_answer(outcome: Union[httpx.Response, Exception]) -> tuple[Any, dict[str, Any]]:
    """(status, the code, ``limit`` and ``used`` of ``detail``): what an administrator's USER_LIMIT_REACHED says of the places; (the exception's type, {}) when the route raised."""
    if not isinstance(outcome, httpx.Response):
        return type(outcome).__name__, {}
    detail = _detail(outcome)
    return outcome.status_code, {key: detail.get(key) for key in ("error_code", "limit", "used")}


async def _in_the_window(private: _Private, rival: Optional[Callable[[], Awaitable[_RivalOutcome]]], method: str, path: str, *, cookie: str, json: Any = None) -> tuple[Union[httpx.Response, Exception], _Window]:
    """The request under test, served on an engine of its own (``_route_of``), ``rival`` landing right before that engine's first write (``_window``) — None for a guard: nobody acts meanwhile. Its outcome (``_attempt``) and its window."""
    async with _route_of(private) as route:
        with _window(route, rival) as window:
            outcome = await _attempt(route, method, path, cookie=cookie, json=json)
    return outcome, window


async def _lock_state(private: _Private) -> _State:
    """The private database now, as ``_State`` reads it."""
    snapshot = await _private_snapshot(private)
    async with AsyncSession(private.engine) as session:
        for table in ACCOUNT_TABLES:
            snapshot[table.name] = [dict(row) for row in (await session.execute(select(table).order_by(table.c.id))).mappings().all()]
    return snapshot, await _private_holdings(private)


def _state_changes(before: _State, after: _State) -> dict[str, Any]:
    """What differs between two states: the rows of users and account_tokens (``_snapshot_changes``), and the holdings when they differ; empty when nothing changed."""
    changes: dict[str, Any] = dict(_snapshot_changes(before[0], after[0]))
    if before[1] != after[1]:
        changes["holdings"] = {"before": before[1], "after": after[1]}
    return changes


def _since_the_rival(window: _Window, after: _State) -> Any:
    """What changed since the rival's request was served (``_state_changes``); a sentence when the rival never ran."""
    return _state_changes(window.rival[0].state, after) if window.rival else "the rival never ran"


def _peer_request(private: _Private, cookie: str, method: str, path: str, json: Any = None) -> Callable[[], Awaitable[_RivalOutcome]]:
    """A rival: the other administrator's request (``cookie``) served on the instance's own engine — another connection than the request under test's, as another worker serves it — and committed by its route; what it answered, and the database right after."""

    async def rival() -> _RivalOutcome:
        answer = _shown(await _attempt(private, method, path, cookie=cookie, json=json))
        return _RivalOutcome(answer=answer, state=await _lock_state(private))

    return rival


def _rival(private: _Private, scene: _LockScene, action: str) -> Callable[[], Awaitable[_RivalOutcome]]:
    """Peer's ``action`` (RIVAL_STATUSES): the target deleted, the target promoted, sleeper reactivated, an invitation created."""
    requests: dict[str, tuple[str, str, Optional[dict[str, Any]]]] = {
        "deletion": ("DELETE", f"/users/{scene.target.user_id}", None),
        "promotion": ("PATCH", f"/users/{scene.target.user_id}", {"is_superuser": True}),
        "reactivation": ("PATCH", f"/users/{scene.sleeper.user_id}", {"is_active": True}),
        "invitation": ("POST", "/users/invites", {"grants_admin": False}),
    }
    method, path, body = requests[action]
    return _peer_request(private, scene.peer_cookie, method, path, body)


def _setup_completes(private: _Private, token: str, user_id: int, waited: list[bool]) -> Callable[[], Awaitable[_RivalOutcome]]:
    """The rival of A51-006: whether account ``user_id`` still waits for its setup, appended to ``waited`` — what the request read, as nothing writes between its reads and this rival —; then that setup completed through ``token`` — POST /auth/setup with SETUP_PASSWORD (``_setup_with``), whoever holds the link — served on the instance's own engine as another worker serves it, committed by its route; what it answered, and the database right after."""

    async def rival() -> _RivalOutcome:
        waited.append(user_id in await _pending_admin_ids(private))
        answer = _shown(await _setup_with(private, token))
        return _RivalOutcome(answer=answer, state=await _lock_state(private))

    return rival


async def _usage(private: _Private) -> tuple[int, Optional[int]]:
    """``registration_service.user_usage`` of the private instance, read fresh: (places used, the limit)."""
    async with AsyncSession(private.engine) as session:
        usage = await registration_service.user_usage(session)
    return usage.used, usage.max_users


async def _live_invitations(private: _Private) -> list[Optional[int]]:
    """Who created each live invitation of the private instance (``list_pending_invites``), oldest first."""
    async with AsyncSession(private.engine) as session:
        return [invite.created_by_user_id for invite in await registration_service.list_pending_invites(session)]


def _short(statement: str) -> str:
    """A statement on one line, cut at 120 characters: what a verdict shows of it."""
    flat = " ".join(statement.split())
    return flat if len(flat) <= 120 else f"{flat[:117]}..."


def _first_write(window: _Window) -> str:
    """The request's first write statement (``_short``), «none» when it wrote nothing: where its window ends."""
    return next((_short(sql) for sql, _ in window.statements if _is_write(sql)), "none")


def _reads_account(statement: str, parameters: Any, user_id: int) -> bool:
    """Whether ``statement`` reads the users row of ``user_id`` by its id: ``SELECT … FROM users WHERE users.id = ?``, that id its first parameter."""
    flat = " ".join(statement.split()).upper()
    first = parameters[0] if isinstance(parameters, (tuple, list)) and parameters else None
    return flat.startswith("SELECT ") and " FROM USERS WHERE USERS.ID = ?" in flat and first == user_id


def _landing_violations(window: _Window, account_id: int, rival_status: int) -> list[str]:
    """The barrier of a race: the rival ran once, right before the request's first write — the statement it preceded —, after the request had read the account ``account_id``, and its own request was served with ``rival_status``. A red is then about the window, not about the setup."""
    if window.landed_before is None:
        return [f"barrier: the request never wrote, so the rival never ran in its window — the request's statements: {[_short(sql) for sql, _ in window.statements]}"]
    preceded = _short(window.statements[window.landed_before][0])
    if not window.rival:
        return [f"barrier: the rival raised right before «{preceded}»: the request's outcome carries its exception"]
    before = window.statements[: window.landed_before]
    read_first = any(_reads_account(sql, parameters, account_id) for sql, parameters in before)
    violations: list[str] = []
    _expect(violations, read_first, f"barrier: the rival ran right before «{preceded}», but the request had not read account {account_id} yet — not the window between its reads and its first write: {[_short(sql) for sql, _ in before]}")
    _expect(violations, window.rival[0].answer[0] == rival_status, f"barrier: the rival's own request must be served, {rival_status}: {window.rival[0].answer}")
    return violations


def _served_violations(window: _Window, account_id: int) -> list[str]:
    """The barrier of a guard: the request was served on its own engine and read the account ``account_id`` there — the race's request, nobody acting in its window."""
    if any(_reads_account(sql, parameters, account_id) for sql, parameters in window.statements):
        return []
    return [f"barrier: the request must read account {account_id} on its own engine: {[_short(sql) for sql, _ in window.statements]}"]


def _deletion_violations(before: _State, after: _State, user_id: int, broker_id: Optional[int]) -> list[str]:
    """What is wrong with a deletion served: the account's row and its tokens must be gone, its broker too when it had one, and every other account as it was."""
    others = [row for row in before[0]["users"] if row["id"] != user_id]
    brokers = [broker for broker, _name in after[1]["brokers"]]
    violations: list[str] = []
    _expect(violations, after[0]["users"] == others, f"the account must be gone, every other row of users as it was: ids before {[row['id'] for row in before[0]['users']]}, after {[row['id'] for row in after[0]['users']]}")
    _expect(violations, all(row["user_id"] != user_id for row in after[0]["account_tokens"]), f"its tokens must be gone: {after[0]['account_tokens']}")
    _expect(violations, broker_id is None or broker_id not in brokers, f"its broker {broker_id} must be gone with it: {after[1]['brokers']}")
    return violations


async def _onboarding_of(private: _Private, cookie: str) -> dict[str, tuple[str, dict[str, str]]]:
    """The account's own onboarding, read from GET /settings/onboarding with its session: ``_live_onboarding``, in-process."""
    response = await _call(private, "GET", "/settings/onboarding", cookie=cookie)
    assert response.status_code == 200, f"GET /settings/onboarding: {response.status_code} {response.text}"
    return _onboarding_reading(response.json())


async def _onboarded(private: _Private, account: _Account) -> tuple[str, dict[str, tuple[str, dict[str, str]]]]:
    """``account`` signed in, its onboarding moved as UADM-013's — intro_tour and import_guide (its steps with it) completed, fx_guide skipped, the first step of transaction_bulk_guide skipped — as the account itself does from the app: its session, and its onboarding as it then reads it. It ends on its promise: the moves read as made."""
    cookie = await _sign_in(private, account)
    bulk_step = STEP_FLOWS[OnboardingFlow.TRANSACTION_BULK_GUIDE.value][0]
    moves = [(OnboardingFlow.INTRO_TOUR, "complete", None), (OnboardingFlow.FX_GUIDE, "skip", None), (OnboardingFlow.IMPORT_GUIDE, "complete", None), (OnboardingFlow.TRANSACTION_BULK_GUIDE, "skip", bulk_step)]
    for flow, action, step in moves:
        path = f"/settings/onboarding/{flow.value}/{action}" if step is None else f"/settings/onboarding/{flow.value}/steps/{step}/{action}"
        response = await _call(private, "POST", path, cookie=cookie, json={"expected_version": ONBOARDING_FLOW_VERSIONS[flow]})
        assert response.status_code == 200, f"Setup: POST {path} as {account.username}: {response.status_code} {response.text}"
    reading = await _onboarding_of(private, cookie)
    moved = (reading[OnboardingFlow.INTRO_TOUR.value][0], reading[OnboardingFlow.FX_GUIDE.value][0], set(reading[OnboardingFlow.IMPORT_GUIDE.value][1].values()), reading[OnboardingFlow.TRANSACTION_BULK_GUIDE.value][1].get(bulk_step))
    assert moved == ("completed", "skipped", {"completed"}, "skipped"), f"Setup: {account.username}'s onboarding must read as moved: {reading}"
    return cookie, reading


async def _reset_link_of(private: _Private, token: Optional[str]) -> tuple[Optional[TokenStatus], Optional[int]]:
    """How ``token`` inspects as a password-reset link, and whose account it resets; (None, None) without a token."""
    if not token:
        return None, None
    async with AsyncSession(private.engine) as session:
        inspection = await inspect_token(session, token, PASSWORD_RESET)
    return inspection.status, inspection.record.user_id if inspection.record is not None else None


@pytest.mark.usefixtures("fresh_login_limiters")
class TestDecidedUnderTheWriteLock:
    """Lot A-54 + A-55 + A-56 (reviewer E, through the coordinator, 17/10): ``PATCH /users/{id}``, ``DELETE /users/{id}``, ``POST /users/invites`` and the three routes that act on an account — its reset link, its sessions, its onboarding — decide on what the database holds under SQLite's write lock, not on the reads before it, where another administrator may act — the account deleted, the account promoted, the last place taken. In-process only, on the migrated schema (``private_head``): a pending administrator never enters the lane's database, and a deletion relies on the production schema's cascades. Each race (``_window``) has its guard: the same request on the same scene, served the same way, nobody acting in its window."""

    # red until A-54
    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", PATCHES)
    async def test_a_patch_on_an_account_deleted_in_its_window_answers_404(self, private_head: _Private, case: str) -> None:
        """UADM-LOCK-01 — NEW, red until A-54 (today ``update_user_status`` takes the lock, then ``session.refresh`` raises ``InvalidRequestError`` on the row gone: a 500, the exception reaching the call in-process): root's PATCH /users/{target} — deactivating an active account, promoting it, reactivating an inactive one, cancelling the pending administrator's setup — while peer, another administrator, deletes the target in the request's window, after the route read it and before its first write. Decided under the lock, on the account as it then is — none —: 404 with ``_user_or_404``'s answer word for word, ``{"detail": "User not found"}``, and nothing changed since peer's deletion: every row of users and account_tokens, every account, broker, grant and transaction as it left them.

        Barrier (``_landing_violations``): the rival ran once, right before the request's first write, after the request read the target; peer's DELETE was served, 204.
        """
        kind, body, _flags = PATCH_CASES[case]
        print_section(f"UADM-LOCK-01: PATCH {body} on the {kind} target, deleted by peer in the request's window")
        scene = await _lock_scene(private_head, kind)
        target = scene.target.user_id

        outcome, window = await _in_the_window(private_head, _rival(private_head, scene, "deletion"), "PATCH", f"/users/{target}", cookie=scene.cookie, json=body)

        changes = _since_the_rival(window, await _lock_state(private_head))
        violations = _landing_violations(window, target, RIVAL_STATUSES["deletion"])
        _expect(violations, _shown(outcome) == USER_NOT_FOUND, f"red until A-54: the target was deleted between the route's reads and its first write; decided under the lock, the PATCH must answer {USER_NOT_FOUND}: got {_shown(outcome)}")
        _expect(violations, changes == {}, f"nothing may change since peer's deletion — what changed: {changes}")
        assert not violations, f"A PATCH on an account deleted in its window must answer 404 and change nothing:{_verdict(violations)}"
        print_success(f"404 User not found, nothing changed; the deletion landed before «{_first_write(window)}»")

    # red until A-54
    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", DELETED_IN_THE_WINDOW)
    async def test_a_deletion_of_an_account_deleted_in_its_window_answers_404(self, private_head: _Private, kind: str) -> None:
        """UADM-LOCK-02 — NEW, red until A-54 (today, for the pending administrator, the route takes the lock and ``session.refresh`` raises ``InvalidRequestError``: a 500, the exception reaching the call; for a plain account, which the route reads nowhere again, 204 — although its own DELETE matched no row and deleted nothing): root's DELETE /users/{target} — the pending administrator, or a plain account — while peer deletes the target in the request's window. On both paths → 404 ``{"detail": "User not found"}``, and nothing else deleted: every row of users and account_tokens, every account, broker, grant and transaction as peer's deletion left them.

        Barrier: the rival ran once, right before the request's first write, after the request read the target; peer's DELETE was served, 204.
        """
        print_section(f"UADM-LOCK-02: DELETE of the {kind} target, deleted by peer in the request's window")
        scene = await _lock_scene(private_head, kind)
        target = scene.target.user_id

        outcome, window = await _in_the_window(private_head, _rival(private_head, scene, "deletion"), "DELETE", f"/users/{target}", cookie=scene.cookie)

        changes = _since_the_rival(window, await _lock_state(private_head))
        violations = _landing_violations(window, target, RIVAL_STATUSES["deletion"])
        _expect(violations, _shown(outcome) == USER_NOT_FOUND, f"red until A-54: the target was deleted between the route's reads and its first write; decided under the lock, the DELETE must answer {USER_NOT_FOUND}: got {_shown(outcome)}")
        _expect(violations, changes == {}, f"nothing else may be deleted, nothing changed since peer's deletion — what changed: {changes}")
        assert not violations, f"A DELETE of an account deleted in its window must answer 404 and delete nothing else:{_verdict(violations)}"
        print_success(f"404 User not found, nothing else deleted; the deletion landed before «{_first_write(window)}»")

    # red until A-55
    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", PROMOTED_IN_THE_WINDOW)
    async def test_a_deletion_of_an_account_promoted_in_its_window_asks_to_demote_first(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
        """UADM-LOCK-03 — NEW, red until A-55 (today 204: the route decided «not an administrator» on its reads and reads again only the pending administrator under the lock, so it deletes the administrator just promoted, its broker with it): the target, a plain account — active or not — and the only OWNER of a broker with a DEPOSIT; root's DELETE /users/{target} while peer promotes it — PATCH {is_superuser: true} — in the request's window. Decided under the lock, an administrator's deletion: → 409 with ``detail.error_code`` DEMOTE_FIRST (the message is the existing one, not pinned), and nothing deleted — every row of users and account_tokens, every account, broker, grant and transaction as the promotion left them: the target there, an administrator, its broker and its DEPOSIT there —; no report file touched.

        Barrier: the rival ran once, right before the request's first write, after the request read the target; peer's PATCH was served, 200.
        """
        print_section(f"UADM-LOCK-03: DELETE of the {kind} target, promoted by peer in the request's window")
        scene = await _lock_scene(private_head, kind, broker=True)
        calls = _spy_on_report_cleanup(monkeypatch)
        target = scene.target.user_id

        outcome, window = await _in_the_window(private_head, _rival(private_head, scene, "promotion"), "DELETE", f"/users/{target}", cookie=scene.cookie)

        after = await _lock_state(private_head)
        changes = _since_the_rival(window, after)
        row = _account_row(after[0], target)
        violations = _landing_violations(window, target, RIVAL_STATUSES["promotion"])
        _expect(violations, _coded(outcome) == (409, "DEMOTE_FIRST"), f"red until A-55: the target was promoted between the route's reads and its first write; decided under the lock, its deletion is an administrator's, 409 DEMOTE_FIRST: got {_shown(outcome)}")
        _expect(violations, changes == {}, f"nothing may be deleted, nothing changed since the promotion — what changed: {changes}")
        _expect(violations, row is not None and (row["is_active"], row["is_superuser"]) == (TARGET_FLAGS[kind][0], True), f"the target must be there, an administrator, active {TARGET_FLAGS[kind][0]}: {row}")
        _expect(violations, calls == [], f"no report file may be touched: cleanups {calls}")
        assert not violations, f"A DELETE of an account promoted in its window must ask to demote it first, and delete nothing:{_verdict(violations)}"
        print_success(f"409 DEMOTE_FIRST, nothing deleted; the promotion landed before «{_first_write(window)}»")

    # red until A-56
    @pytest.mark.asyncio
    @pytest.mark.parametrize("taker", LAST_PLACE_TAKERS)
    async def test_a_reactivation_whose_last_place_is_taken_in_its_window_is_refused(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, taker: str) -> None:
        """UADM-LOCK-04 — NEW, red until A-56 (today 200: the route counts the places before its first write and nothing counts them again under the lock — the instance ends one over its limit, 4 places for 3): LIBREFOLIO_MAX_USERS=3 and one place left — root and peer active, the target and sleeper inactive plain accounts holding none —; root's PATCH {is_active: true} of the target while peer takes the last place in the request's window, reactivating sleeper or creating an invitation. Counted under the lock: → 409 USER_LIMIT_REACHED, its counts the database's — limit 3, used 3 (point 5, as UADM-022) —; the target still inactive and nothing changed since peer's request; ``user_usage()`` used 3, the limit — not one over it.

        Barrier: the rival ran once, right before the request's first write, after the request read the target; peer's request was served (200 or 201).
        """
        print_section(f"UADM-LOCK-04: a reactivation with one place left, the place taken in its window ({taker})")
        scene = await _lock_scene(private_head, "inactive")
        target = scene.target.user_id
        monkeypatch.setenv(MAX_USERS_VARIABLE, str(LOCK_LIMIT))
        assert await _usage(private_head) == (LOCK_LIMIT - 1, LOCK_LIMIT), "Setup: one place left — root and peer active, the target and sleeper holding none"

        outcome, window = await _in_the_window(private_head, _rival(private_head, scene, taker), "PATCH", f"/users/{target}", cookie=scene.cookie, json={"is_active": True})

        after = await _lock_state(private_head)
        changes = _since_the_rival(window, after)
        row = _account_row(after[0], target)
        usage = await _usage(private_head)
        refused = (409, {"error_code": "USER_LIMIT_REACHED", "limit": LOCK_LIMIT, "used": LOCK_LIMIT})
        violations = _landing_violations(window, target, RIVAL_STATUSES[taker])
        _expect(violations, _limit_answer(outcome) == refused, f"red until A-56: the last place was taken between the route's count and its first write; counted under the lock, the reactivation must be refused {refused}: got {_shown(outcome)}")
        _expect(violations, row is not None and not row["is_active"], f"the target must still be inactive: {row}")
        _expect(violations, changes == {}, f"nothing may change since peer's request — what changed: {changes}")
        _expect(violations, usage == (LOCK_LIMIT, LOCK_LIMIT), f"the instance must end at its limit, not over it: user_usage() (used, limit) {usage}")
        assert not violations, f"A reactivation whose last place is taken in its window must be refused, the instance at its limit:{_verdict(violations)}"
        print_success(f"409 USER_LIMIT_REACHED, used {usage[0]} of {usage[1]}; the {taker} landed before «{_first_write(window)}»")

    # red until A-56
    @pytest.mark.asyncio
    @pytest.mark.parametrize("taker", LAST_PLACE_TAKERS)
    async def test_an_invitation_whose_last_place_is_taken_in_its_window_is_refused(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, taker: str) -> None:
        """UADM-LOCK-05 — NEW, red until A-56 (today 201: ``create_invite`` counts the places, then ``issue_token`` INSERTs, and nothing holds the count in between — root's invitation beside the place peer took, one over the limit): LIBREFOLIO_MAX_USERS=3 and one place left; root's POST /users/invites while peer takes the last place in the request's window — its own invitation, or reactivating sleeper. Counted under the lock: → 409 USER_LIMIT_REACHED, limit 3 and used 3 (point 2, as UADM-024); no invitation of root's — the live invitations exactly the rival's: peer's one, or none —; nothing changed since peer's request; ``user_usage()`` used 3.

        Barrier: the rival ran once, right before the request's first write, after the request's authentication read root; peer's request was served (201 or 200).
        """
        print_section(f"UADM-LOCK-05: an invitation with one place left, the place taken in its window ({taker})")
        scene = await _lock_scene(private_head, "inactive")
        monkeypatch.setenv(MAX_USERS_VARIABLE, str(LOCK_LIMIT))
        assert await _usage(private_head) == (LOCK_LIMIT - 1, LOCK_LIMIT), "Setup: one place left — root and peer active, the target and sleeper holding none"
        assert await _live_invitations(private_head) == [], "Setup: no live invitation"

        outcome, window = await _in_the_window(private_head, _rival(private_head, scene, taker), "POST", "/users/invites", cookie=scene.cookie, json={"grants_admin": False})

        changes = _since_the_rival(window, await _lock_state(private_head))
        live = await _live_invitations(private_head)
        rivals = [scene.peer.user_id] if taker == "invitation" else []
        usage = await _usage(private_head)
        refused = (409, {"error_code": "USER_LIMIT_REACHED", "limit": LOCK_LIMIT, "used": LOCK_LIMIT})
        violations = _landing_violations(window, scene.root.user_id, RIVAL_STATUSES[taker])
        _expect(violations, _limit_answer(outcome) == refused, f"red until A-56: the last place was taken between the invitation's count and its first write; counted under the lock, the invitation must be refused {refused}: got {_shown(outcome)}")
        _expect(violations, live == rivals, f"the live invitations must be exactly the rival's — by creator, {rivals}: {live}")
        _expect(violations, changes == {}, f"nothing may change since peer's request — what changed: {changes}")
        _expect(violations, usage == (LOCK_LIMIT, LOCK_LIMIT), f"the instance must end at its limit, not over it: user_usage() (used, limit) {usage}")
        assert not violations, f"An invitation whose last place is taken in its window must be refused, the instance at its limit:{_verdict(violations)}"
        print_success(f"409 USER_LIMIT_REACHED, used {usage[0]} of {usage[1]}; the {taker} landed before «{_first_write(window)}»")

    # guard
    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", PATCHES)
    async def test_a_patch_with_nobody_in_its_window_is_served_as_before(self, private_head: _Private, case: str) -> None:
        """UADM-LOCK-06 — GUARD of UADM-LOCK-01, green today and after: its PATCH on its scene, served the same way — an engine of its own, the window recorded —, nobody acting in the window: 200 with the target's row, exactly its nine fields, as the change leaves it — deactivated, promoted, reactivated; the cancellation leaves the pending administrator inactive, an administrator, still waiting (pending_setup true) —, and the database holds the same.

        Barrier: the request read the target on its own engine.
        """
        kind, body, flags = PATCH_CASES[case]
        print_section(f"UADM-LOCK-06: PATCH {body} on the {kind} target, nobody in the window")
        scene = await _lock_scene(private_head, kind)
        target = scene.target.user_id

        outcome, window = await _in_the_window(private_head, None, "PATCH", f"/users/{target}", cookie=scene.cookie, json=body)

        status, answer = _shown(outcome)
        held = ((await _private_user(private_head, target))[:2], target in await _pending_admin_ids(private_head))
        violations = _served_violations(window, target)
        _expect(violations, status == 200, f"PATCH {body} with nobody in its window: expected 200, got {status} {answer}")
        violations += [f"the PATCH's answer: {violation}" for violation in _user_item_violations(answer, scene.target, active=flags[0], superuser=flags[1], pending_setup=kind == "pending")]
        _expect(violations, held == (flags, kind == "pending"), f"the database must hold the target as the change leaves it — (is_active, is_superuser) {flags}, waiting {kind == 'pending'}: {held}")
        assert not violations, f"A PATCH with nobody in its window must be served as before:{_verdict(violations)}"
        print_success(f"200, (is_active, is_superuser) {flags}; first write «{_first_write(window)}»")

    # guard
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("kind", "broker", "expected"), DELETIONS_WITHOUT_A_RIVAL)
    async def test_a_deletion_with_nobody_in_its_window_is_served_as_before(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, kind: str, broker: bool, expected: tuple[int, Optional[str]]) -> None:
        """UADM-LOCK-07 — GUARD of UADM-LOCK-02 and UADM-LOCK-03, green today and after: their DELETE on their scenes, served the same way, nobody acting in the window — and an administrator owning a broker, the state UADM-LOCK-03's promotion leads to, there before the request. The pending administrator, or a plain account — active or not, the only OWNER of a broker with a DEPOSIT or of none — → 204: the account and its tokens gone, its broker with it and that broker's report files cleaned once, every other account as it was. An administrator → 409 DEMOTE_FIRST, nothing changed, no report file touched.

        Barrier: the request read the target on its own engine.
        """
        print_section(f"UADM-LOCK-07: DELETE of the {kind} target{' owning a broker' if broker else ''}, nobody in the window")
        scene = await _lock_scene(private_head, kind, broker=broker)
        calls = _spy_on_report_cleanup(monkeypatch)
        target = scene.target.user_id
        before = await _lock_state(private_head)

        outcome, window = await _in_the_window(private_head, None, "DELETE", f"/users/{target}", cookie=scene.cookie)

        after = await _lock_state(private_head)
        violations = _served_violations(window, target)
        _expect(violations, _coded(outcome) == expected, f"DELETE of the {kind} target with nobody in its window: expected {expected}, got {_shown(outcome)}")
        if expected[0] == 204:
            violations += _deletion_violations(before, after, target, scene.broker_id)
            _expect(violations, calls == ([[scene.broker_id]] if broker else []), f"the report files of its broker, and only them, must be cleaned once: cleanups {calls}")
        else:
            _expect(violations, _state_changes(before, after) == {}, f"a refused deletion must change nothing — what changed: {_state_changes(before, after)}")
            _expect(violations, calls == [], f"a refused deletion must touch no report file: cleanups {calls}")
        assert not violations, f"A DELETE with nobody in its window must be served as before:{_verdict(violations)}"
        print_success(f"{expected}; first write «{_first_write(window)}»")

    # guard
    @pytest.mark.asyncio
    @pytest.mark.parametrize("taker", TAKEN_BEFORE)
    async def test_a_reactivation_with_nobody_in_its_window_counts_the_places_as_before(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, taker: Optional[str]) -> None:
        """UADM-LOCK-08 — GUARD of UADM-LOCK-04, green today and after: LIBREFOLIO_MAX_USERS=3, root and peer active; the last place left free, or taken BEFORE the request by UADM-LOCK-04's rivals — peer's request served first —; then its PATCH {is_active: true} of the target, served the same way, nobody acting in the window. A place left → 200, the target active; none → 409 USER_LIMIT_REACHED (limit 3, used 3), nothing changed, the target inactive. Either way ``user_usage()`` ends at used 3.

        Barrier: the request read the target on its own engine.
        """
        print_section(f"UADM-LOCK-08: a reactivation, nobody in its window — the last place {f'taken before ({taker})' if taker else 'left'}")
        scene = await _lock_scene(private_head, "inactive")
        target = scene.target.user_id
        monkeypatch.setenv(MAX_USERS_VARIABLE, str(LOCK_LIMIT))
        if taker is not None:
            taken = await _rival(private_head, scene, taker)()
            assert taken.answer[0] == RIVAL_STATUSES[taker], f"Setup: peer's {taker} must be served first, {RIVAL_STATUSES[taker]}: {taken.answer}"
        before = await _lock_state(private_head)

        outcome, window = await _in_the_window(private_head, None, "PATCH", f"/users/{target}", cookie=scene.cookie, json={"is_active": True})

        after = await _lock_state(private_head)
        row = _account_row(after[0], target)
        usage = await _usage(private_head)
        violations = _served_violations(window, target)
        if taker is None:
            _expect(violations, _coded(outcome) == (200, None), f"with a place left the reactivation goes through: expected 200, got {_shown(outcome)}")
            _expect(violations, row is not None and row["is_active"], f"the target must be active: {row}")
        else:
            refused = (409, {"error_code": "USER_LIMIT_REACHED", "limit": LOCK_LIMIT, "used": LOCK_LIMIT})
            _expect(violations, _limit_answer(outcome) == refused, f"with no place left the reactivation is refused {refused}: got {_shown(outcome)}")
            _expect(violations, _state_changes(before, after) == {}, f"a refused reactivation must change nothing — what changed: {_state_changes(before, after)}")
        _expect(violations, usage == (LOCK_LIMIT, LOCK_LIMIT), f"the instance must end at its limit: user_usage() (used, limit) {usage}")
        assert not violations, f"A reactivation with nobody in its window must count the places as before:{_verdict(violations)}"
        print_success(f"{_coded(outcome)}, used {usage[0]} of {usage[1]}; first write «{_first_write(window)}»")

    # guard
    @pytest.mark.asyncio
    @pytest.mark.parametrize("taker", TAKEN_BEFORE)
    async def test_an_invitation_with_nobody_in_its_window_counts_the_places_as_before(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, taker: Optional[str]) -> None:
        """UADM-LOCK-09 — GUARD of UADM-LOCK-05, green today and after: LIBREFOLIO_MAX_USERS=3, root and peer active; the last place left free, or taken BEFORE the request by UADM-LOCK-05's rivals — peer's request served first —; then its POST /users/invites, served the same way, nobody acting in the window. A place left → 201, root's invitation the one live; none → 409 USER_LIMIT_REACHED (limit 3, used 3), nothing changed — the live invitations peer's one, or none. Either way ``user_usage()`` ends at used 3.

        Barrier: the request read root, its caller, on its own engine.
        """
        print_section(f"UADM-LOCK-09: an invitation, nobody in its window — the last place {f'taken before ({taker})' if taker else 'left'}")
        scene = await _lock_scene(private_head, "inactive")
        monkeypatch.setenv(MAX_USERS_VARIABLE, str(LOCK_LIMIT))
        if taker is not None:
            taken = await _rival(private_head, scene, taker)()
            assert taken.answer[0] == RIVAL_STATUSES[taker], f"Setup: peer's {taker} must be served first, {RIVAL_STATUSES[taker]}: {taken.answer}"
        before = await _lock_state(private_head)

        outcome, window = await _in_the_window(private_head, None, "POST", "/users/invites", cookie=scene.cookie, json={"grants_admin": False})

        after = await _lock_state(private_head)
        live = await _live_invitations(private_head)
        usage = await _usage(private_head)
        violations = _served_violations(window, scene.root.user_id)
        if taker is None:
            _expect(violations, (_coded(outcome), live) == ((201, None), [scene.root.user_id]), f"with a place left the invitation is issued: expected 201 and root's invitation the one live, got {_coded(outcome)}, live invitations by creator {live}")
        else:
            refused = (409, {"error_code": "USER_LIMIT_REACHED", "limit": LOCK_LIMIT, "used": LOCK_LIMIT})
            rivals = [scene.peer.user_id] if taker == "invitation" else []
            _expect(violations, _limit_answer(outcome) == refused, f"with no place left the invitation is refused {refused}: got {_shown(outcome)}")
            _expect(violations, (_state_changes(before, after), live) == ({}, rivals), f"a refused invitation must change nothing, the live invitations the rival's {rivals}: what changed {_state_changes(before, after)}; live by creator {live}")
        _expect(violations, usage == (LOCK_LIMIT, LOCK_LIMIT), f"the instance must end at its limit: user_usage() (used, limit) {usage}")
        assert not violations, f"An invitation with nobody in its window must count the places as before:{_verdict(violations)}"
        print_success(f"{_coded(outcome)}, used {usage[0]} of {usage[1]}; first write «{_first_write(window)}»")

    # red until A-54
    @pytest.mark.asyncio
    async def test_a_reset_link_for_an_account_deleted_in_its_window_answers_404(self, private_head: _Private) -> None:
        """UADM-LOCK-10 — NEW, red until A-54 (today the route's first write — ``create_password_reset`` revoking the account's earlier reset links — comes after the deletion and matches nothing, then ``issue_token``'s INSERT fails on the foreign key: ``IntegrityError``, a 500, the exception reaching the call in-process): root's POST /users/{target}/password-reset-link while peer deletes the target in the request's window, after the route read it and before its first write. Read again under the lock — none —: 404 with ``_user_or_404``'s answer word for word, ``{"detail": "User not found"}``; no reset link issued — no password_reset row in account_tokens, and no row of the target —; and nothing else changed since peer's deletion: every row of users and account_tokens, every account's settings and onboarding, every account, broker, grant and transaction as it left them.

        Barrier (``_landing_violations``): the rival ran once, right before the request's first write, after the request read the target; peer's DELETE was served, 204.
        """
        print_section("UADM-LOCK-10: a reset link for the target, deleted by peer in the request's window")
        scene = await _lock_scene(private_head, "active")
        target = scene.target.user_id

        outcome, window = await _in_the_window(private_head, _rival(private_head, scene, "deletion"), "POST", f"/users/{target}/password-reset-link", cookie=scene.cookie)

        after = await _lock_state(private_head)
        changes = _since_the_rival(window, after)
        links = [row for row in after[0]["account_tokens"] if row["purpose"] == PASSWORD_RESET.value or row["user_id"] == target]
        violations = _landing_violations(window, target, RIVAL_STATUSES["deletion"])
        _expect(violations, _shown(outcome) == USER_NOT_FOUND, f"red until A-54: the target was deleted between the route's read and its first write; read again under the lock, the reset link must answer {USER_NOT_FOUND}: got {_shown(outcome)}")
        _expect(violations, links == [], f"no reset link may be issued — no password_reset token, no token of the target: {links}")
        _expect(violations, changes == {}, f"nothing may change since peer's deletion — what changed: {changes}")
        assert not violations, f"A reset link for an account deleted in its window must answer 404 and issue nothing:{_verdict(violations)}"
        print_success(f"404 User not found, no link issued; the deletion landed before «{_first_write(window)}»")

    # red until A-54
    @pytest.mark.asyncio
    async def test_a_sessions_revoke_of_an_account_deleted_in_its_window_answers_404(self, private_head: _Private) -> None:
        """UADM-LOCK-11 — NEW, red until A-54 (today the route's first write — ``end_sessions``' UPDATE … RETURNING of the session version — comes after the deletion and matches no row: ``scalar_one`` raises ``NoResultFound``, a 500, the exception reaching the call in-process): the target signed in; root's POST /users/{target}/sessions/revoke while peer deletes the target in the request's window. Read again under the lock — none —: 404 ``{"detail": "User not found"}``, and nothing changed since peer's deletion.

        Barrier: the rival ran once, right before the request's first write, after the request read the target; peer's DELETE was served, 204.
        """
        print_section("UADM-LOCK-11: a sessions revoke of the target, deleted by peer in the request's window")
        scene = await _lock_scene(private_head, "active")
        await _sign_in(private_head, scene.target)
        target = scene.target.user_id

        outcome, window = await _in_the_window(private_head, _rival(private_head, scene, "deletion"), "POST", f"/users/{target}/sessions/revoke", cookie=scene.cookie)

        changes = _since_the_rival(window, await _lock_state(private_head))
        violations = _landing_violations(window, target, RIVAL_STATUSES["deletion"])
        _expect(violations, _shown(outcome) == USER_NOT_FOUND, f"red until A-54: the target was deleted between the route's read and its first write; read again under the lock, the sessions revoke must answer {USER_NOT_FOUND}: got {_shown(outcome)}")
        _expect(violations, changes == {}, f"nothing may change since peer's deletion — what changed: {changes}")
        assert not violations, f"A sessions revoke of an account deleted in its window must answer 404 and change nothing:{_verdict(violations)}"
        print_success(f"404 User not found, nothing changed; the deletion landed before «{_first_write(window)}»")

    # red until A-54
    @pytest.mark.asyncio
    @pytest.mark.parametrize("flow", ONBOARDING_RESETS)
    async def test_an_onboarding_reset_of_an_account_deleted_in_its_window_answers_404(self, private_head: _Private, flow: Optional[str]) -> None:
        """UADM-LOCK-12 — NEW, red until A-54 (today 204: the route's first write — ``reset_onboarding_progress``'s UPDATE — comes after the deletion, whose cascade took the account's onboarding rows; the UPDATEs match nothing, and the route answers 204 for an account that no longer exists): the target signed in, its onboarding moved (``_onboarded``: flows completed and skipped, a step skipped); root's POST /users/{target}/onboarding/reset — without a body (every flow), or ``{flow: import_guide}`` — while peer deletes the target in the request's window. Read again under the lock — none —: 404 ``{"detail": "User not found"}``; no onboarding row created or changed for that id — no row of user_onboarding_progress or user_onboarding_step_progress of the target —; and nothing changed since peer's deletion.

        Barrier: the rival ran once, right before the request's first write, after the request read the target; peer's DELETE was served, 204.
        """
        print_section(f"UADM-LOCK-12: an onboarding reset ({flow or 'every flow'}) of the target, deleted by peer in the request's window")
        scene = await _lock_scene(private_head, "active")
        await _onboarded(private_head, scene.target)
        target = scene.target.user_id

        outcome, window = await _in_the_window(private_head, _rival(private_head, scene, "deletion"), "POST", f"/users/{target}/onboarding/reset", cookie=scene.cookie, json=None if flow is None else {"flow": flow})

        after = await _lock_state(private_head)
        changes = _since_the_rival(window, after)
        rows = {table: [row for row in after[0][table] if row["user_id"] == target] for table in sorted(ONBOARDING_TABLES)}
        violations = _landing_violations(window, target, RIVAL_STATUSES["deletion"])
        _expect(violations, _shown(outcome) == USER_NOT_FOUND, f"red until A-54: the target was deleted between the route's read and its first write; read again under the lock, the onboarding reset must answer {USER_NOT_FOUND}: got {_shown(outcome)}")
        _expect(violations, rows == dict.fromkeys(sorted(ONBOARDING_TABLES), []), f"no onboarding row of the target may be created or changed: {rows}")
        _expect(violations, changes == {}, f"nothing may change since peer's deletion — what changed: {changes}")
        assert not violations, f"An onboarding reset of an account deleted in its window must answer 404 and write nothing:{_verdict(violations)}"
        print_success(f"404 User not found, no onboarding row; the deletion landed before «{_first_write(window)}»")

    # guard
    @pytest.mark.asyncio
    async def test_a_reset_link_with_nobody_in_its_window_is_issued_as_before(self, private_head: _Private) -> None:
        """UADM-LOCK-13 — GUARD of UADM-LOCK-10, green today and after: its POST /users/{target}/password-reset-link on its scene, served the same way, nobody acting in the window: 201 with the link — ``{token, path, url, expires_at}`` as UADM-010 reads it (``_reset_link_violations``) —, its token a live reset link of the target (inspected valid); and the one change, a new row of account_tokens: the stored hash of that token, a password_reset of the target issued by root, neither consumed nor revoked.

        Barrier: the request read the target on its own engine.
        """
        print_section("UADM-LOCK-13: a reset link for the target, nobody in the window")
        scene = await _lock_scene(private_head, "active")
        target = scene.target.user_id
        before = await _lock_state(private_head)

        outcome, window = await _in_the_window(private_head, None, "POST", f"/users/{target}/password-reset-link", cookie=scene.cookie)

        changes = _state_changes(before, await _lock_state(private_head))
        status, link = _shown(outcome)
        token = link.get("token") if isinstance(link, dict) else None
        inspected = await _reset_link_of(private_head, token)
        new_rows = changes.get("account_tokens", {}).get("after", [])
        issued = [(row["purpose"], row["user_id"], row["created_by_user_id"], row["token_hash"], row["consumed_at"], row["revoked_at"]) for row in new_rows]
        expected = [(PASSWORD_RESET.value, target, scene.root.user_id, hash_token(token or ""), None, None)]
        violations = _served_violations(window, target)
        _expect(violations, status == 201, f"a reset link with nobody in its window: expected 201, got {status} {link}")
        violations += _reset_link_violations(link) if status == 201 else []
        _expect(violations, inspected == (TokenStatus.VALID, target), f"its token must be a live reset link of the target: inspected (status, user_id) {inspected}")
        _expect(violations, set(changes) == {"account_tokens"} and changes["account_tokens"]["before"] == [] and issued == expected, f"the one change must be the new link's row {expected}: what changed {changes}")
        assert not violations, f"A reset link with nobody in its window must be issued as before:{_verdict(violations)}"
        print_success(f"201, a live link of the target; first write «{_first_write(window)}»")

    # guard
    @pytest.mark.asyncio
    async def test_a_sessions_revoke_with_nobody_in_its_window_ends_the_sessions_as_before(self, private_head: _Private) -> None:
        """UADM-LOCK-14 — GUARD of UADM-LOCK-11, green today and after: its POST /users/{target}/sessions/revoke on its scene — the target signed in —, served the same way, nobody acting in the window: 204 with no body; the target's session refused — GET /auth/me → 401 «Session expired or invalid» —; and the one change, the target's session version one higher, every other column and row as it was.

        Barrier: the request read the target on its own engine.
        """
        print_section("UADM-LOCK-14: a sessions revoke of the target, nobody in the window")
        scene = await _lock_scene(private_head, "active")
        target_cookie = await _sign_in(private_head, scene.target)
        target = scene.target.user_id
        before = await _lock_state(private_head)
        # The state the revoke must leave: the one before, the target's session version one higher — in its row, and in
        # the holdings, which carry every account's version
        rows, holdings = before
        users = [{**row, "session_version": row["session_version"] + 1} if row["id"] == target else row for row in rows["users"]]
        accounts = sorted((name, active, admin, version + 1 if name == scene.target.username else version) for name, active, admin, version in holdings["accounts"])
        expected = ({**rows, "users": users}, {**holdings, "accounts": accounts})
        assert _state_changes(before, expected) != {}, "Setup: the expected state must raise the target's session version"

        outcome, window = await _in_the_window(private_head, None, "POST", f"/users/{target}/sessions/revoke", cookie=scene.cookie)

        unexpected = _state_changes(expected, await _lock_state(private_head))
        me = _answer(await _call(private_head, "GET", "/auth/me", cookie=target_cookie))
        violations = _served_violations(window, target)
        _expect(violations, _shown(outcome) == (204, ""), f"a sessions revoke with nobody in its window: expected 204 with no body, got {_shown(outcome)}")
        _expect(violations, me == SESSION_EXPIRED, f"the target's session must be refused with {SESSION_EXPIRED}: {me}")
        _expect(violations, unexpected == {}, f"the one change must be the target's session version, one higher — what differs from that (expected, then found): {unexpected}")
        assert not violations, f"A sessions revoke with nobody in its window must end the sessions as before:{_verdict(violations)}"
        print_success(f"204, the target's session ended; first write «{_first_write(window)}»")

    # guard
    @pytest.mark.asyncio
    @pytest.mark.parametrize("flow", ONBOARDING_RESETS)
    async def test_an_onboarding_reset_with_nobody_in_its_window_resets_as_before(self, private_head: _Private, flow: Optional[str]) -> None:
        """UADM-LOCK-15 — GUARD of UADM-LOCK-12, green today and after: its POST /users/{target}/onboarding/reset on its scene — the target signed in, its onboarding moved —, served the same way, nobody acting in the window: 204 with no body; the target reads every flow and every step pending (without a body, as UADM-013), or import_guide and its steps pending and every other flow as it was (``{flow: import_guide}``, as UADM-014); and nothing changed but the target's onboarding rows.

        Barrier: the request read the target on its own engine.
        """
        print_section(f"UADM-LOCK-15: an onboarding reset ({flow or 'every flow'}) of the target, nobody in the window")
        scene = await _lock_scene(private_head, "active")
        target_cookie, onboarding = await _onboarded(private_head, scene.target)
        target = scene.target.user_id
        before = await _lock_state(private_head)

        outcome, window = await _in_the_window(private_head, None, "POST", f"/users/{target}/onboarding/reset", cookie=scene.cookie, json=None if flow is None else {"flow": flow})

        changes = _state_changes(before, await _lock_state(private_head))
        reading = await _onboarding_of(private_head, target_cookie)
        expected = {name.value: _pending(name.value) for name in ONBOARDING_FLOW_VERSIONS} if flow is None else {**onboarding, flow: _pending(flow)}
        strays = {table: change for table, change in changes.items() if table not in ONBOARDING_TABLES or any(row["user_id"] != target for row in change["before"] + change["after"])}
        violations = _served_violations(window, target)
        _expect(violations, _shown(outcome) == (204, ""), f"an onboarding reset with nobody in its window: expected 204 with no body, got {_shown(outcome)}")
        _expect(violations, reading == expected, f"the target must read {'every flow and step' if flow is None else f'only {flow}'} back to pending: before {onboarding}, after {reading}")
        _expect(violations, strays == {}, f"nothing may change but the target's onboarding rows — what else changed: {strays}")
        assert not violations, f"An onboarding reset with nobody in its window must reset as before:{_verdict(violations)}"
        print_success(f"204, {'every flow' if flow is None else flow} pending; first write «{_first_write(window)}»")


# ============================================================================
# N69-4: EVERY ACCOUNT'S AVATAR (point 20)
# ============================================================================


def _uploaded_avatar() -> str:
    """An avatar uploaded to the app as the profile stores it, ``/api/v1/uploads/file/<id>``, a fresh id each time: the address only — PUT /settings/user checks no file."""
    return f"/api/v1/uploads/file/{uuid.uuid4()}"


def _linked_avatar() -> str:
    """An avatar at an address outside the app, with a query of its own, a fresh one each time."""
    return f"https://example.org/uadm-av/{uuid.uuid4().hex[:12]}.png?size=2"


def _avatar_of(item: Any) -> Any:
    """``avatar_url`` of an account as listed or answered; ``<missing>`` when the item lacks the field (before N69-4), ``<not listed>`` when there is no item."""
    if not isinstance(item, dict):
        return "<not listed>"
    return item.get("avatar_url", "<missing>")


async def _live_set_avatar(member: _Signed, avatar_url: Optional[str]) -> None:
    """``member`` sets its own avatar — or clears it, with None — as its profile does: PUT /settings/user with its own session. Ends on what it promises: the settings it is answered carry that avatar."""
    response = await _live("PUT", "/settings/user", cookie=member.cookie, json={"avatar_url": avatar_url})
    assert response.status_code == 200 and _avatar_of(response.json()) == avatar_url, f"Setup: PUT /settings/user {{avatar_url: {avatar_url!r}}} as {member.account.username}: {response.status_code} {response.text}"


async def _private_settings_rows(private: _Private, rows: list[tuple[int, _Account, Optional[str]]]) -> None:
    """Settings rows written directly, each ``(its id, its account, its avatar)``: the ids are the case's choice, which no route offers."""
    async with AsyncSession(private.engine) as session:
        session.add_all([UserSettings(id=row_id, user_id=account.user_id, avatar_url=avatar) for row_id, account, avatar in rows])
        await session.commit()


def _patch_answer_violations(change: dict[str, bool], response: httpx.Response, listed: Optional[dict[str, Any]], account: _Account, *, superuser: bool, avatar_url: Optional[str]) -> list[str]:
    """What is wrong with the answer of PATCH ``change`` on ``account``, an active account: a 200, exactly its ten fields with its own ``avatar_url`` — null without one —, and the item GET /users listed right after (``listed``)."""
    if response.status_code != 200:
        return [f"PATCH {change} on {account.username}: expected 200, got {response.status_code} {response.text}"]
    answer = response.json()
    violations = [f"PATCH {change}, its answer: {problem}" for problem in _user_item_violations(answer, account, active=True, superuser=superuser, avatar_url=avatar_url)]
    _expect(violations, _avatar_of(answer) == avatar_url, f"PATCH {change} on {account.username}: its answer must carry the account's avatar_url {avatar_url!r}, got {_avatar_of(answer)!r}")
    _expect(violations, _comparable(answer) == _comparable(listed), f"PATCH {change} on {account.username}: its answer must be the account as GET /users lists it right after: answered {answer}, listed {listed}")
    return violations


class TestAccountAvatarsOnTheLane:
    """Lot N69-4 (point 20) on the lane's server: the case's accounts set their own avatars, and are found by id among whatever the neighbours registered."""

    # red until N69-4
    @pytest.mark.asyncio
    async def test_the_list_carries_each_accounts_own_avatar_and_null_without_one(self, lane: _LaneRows) -> None:
        """UADM-AV-01: GET /users → each of this case's five accounts, found by id, carries its own avatar_url as stored: the uploaded image of one (``/api/v1/uploads/file/<id>``), the address of another (with a query of its own); null for an account that set one and cleared it (a settings row without an avatar), for one that never wrote its settings (no row), and for the caller, the administrator. Each exactly its ten fields, every other value as before.

        Each avatar is set by its account through PUT /settings/user, as its profile does; the two differ, and the caller
        has none: an avatar read from the wrong account shows.
        """
        print_section("UADM-AV-01: GET /users carries each account's avatar")
        admin = await _live_admin(lane)
        uploaded = await _live_member(lane, "uadm_av_file")
        linked = await _live_member(lane, "uadm_av_link")
        cleared = await _live_member(lane, "uadm_av_cleared")
        bare = await _live_register(lane, "uadm_av_bare")
        file_avatar, link_avatar = _uploaded_avatar(), _linked_avatar()
        await _live_set_avatar(uploaded, file_avatar)
        await _live_set_avatar(linked, link_avatar)
        await _live_set_avatar(cleared, _uploaded_avatar())
        await _live_set_avatar(cleared, None)

        response = await _live("GET", "/users", cookie=admin.cookie)

        assert response.status_code == 200, f"GET /users as an administrator: {response.status_code} {response.text}"
        items = {item.get("id"): item for item in response.json()["items"]}
        # (account, is_superuser, avatar_url)
        expected = [(admin.account, True, None), (uploaded.account, False, file_avatar), (linked.account, False, link_avatar), (cleared.account, False, None), (bare, False, None)]
        wanted = {account.username: avatar for account, _, avatar in expected}
        found = {account.username: _avatar_of(items.get(account.user_id)) for account, _, _ in expected}
        violations: list[str] = []
        _expect(violations, found == wanted, f"avatar_url must be each account's own, null without one: expected {wanted}, got {found}")
        for account, superuser, avatar in expected:
            violations += _user_item_violations(items.get(account.user_id), account, active=True, superuser=superuser, avatar_url=avatar)
        assert not violations, f"GET /users must carry every account's own avatar (lot N69-4):{_verdict(violations)}"
        print_success("an uploaded image and an address listed as stored; null without one, with a settings row or without")

    # red until N69-4
    @pytest.mark.asyncio
    async def test_the_patch_answer_carries_the_accounts_avatar(self, lane: _LaneRows) -> None:
        """UADM-AV-02: PATCH /users/{id} answers the account as GET /users lists it, avatar_url included: the answer replaces its row in the Users tab. Two accounts of this case, each promoted then demoted — PATCH {is_superuser: true}, then {is_superuser: false}, each 200 —: the one that set an uploaded avatar answers it both times, the one without an avatar answers null; each answer exactly its ten fields, and the item GET /users lists right after. The caller has no avatar: an answer that read the caller's settings shows."""
        print_section("UADM-AV-02: the PATCH answer carries the account's avatar")
        admin = await _live_admin(lane)
        pictured = await _live_member(lane, "uadm_av_patched")
        avatar = _uploaded_avatar()
        await _live_set_avatar(pictured, avatar)
        bare = await _live_register(lane, "uadm_av_patched_bare")

        violations: list[str] = []
        for account, expected in ((pictured.account, avatar), (bare, None)):
            for superuser in (True, False):
                change = {"is_superuser": superuser}
                response = await _live("PATCH", f"/users/{account.user_id}", cookie=admin.cookie, json=change)
                listed = await _listed(admin.cookie, "/users", account.user_id)
                violations += _patch_answer_violations(change, response, listed, account, superuser=superuser, avatar_url=expected)
        assert not violations, f"The PATCH answer must carry the account's avatar, as the list does (lot N69-4):{_verdict(violations)}"
        print_success("promoted, then demoted: each answer carries the account's avatar, or null, as listed right after")


class TestAccountAvatarsInProcess:
    """Lot N69-4 (point 20) on a private instance: every account and every settings row are the test's, so the whole list is asserted, and the settings rows take the ids of other accounts."""

    # red until N69-4
    @pytest.mark.asyncio
    async def test_every_account_carries_its_own_avatar_whatever_the_ids_of_the_settings_rows(self, private: _Private) -> None:
        """UADM-AV-03: root (the caller) with an avatar at an address, ana with an uploaded one, ben with one at another address, cleo with a settings row and no avatar, dan with no settings row. Each row is written with the id of another account — ana's with ben's id, ben's with ana's, root's with dan's, cleo's with root's —: an avatar looked up by anything but the account's id lands on another account. GET /users → the instance's five accounts, each with its own avatar_url, null for cleo and dan, each exactly its ten fields; PATCH {is_superuser: true} on ana, then on dan → 200, each answer with its own avatar_url (ana's, null) and the item GET /users lists right after.

        Premise first: no settings row has the id of its own account.
        """
        print_section("UADM-AV-03: each account's own avatar, the ids of the settings rows crossed")
        root, cookie = await _admin(private)
        ana, ben, cleo, dan = [await _add_user(private, name) for name in ("ana", "ben", "cleo", "dan")]
        avatars = {root: _linked_avatar(), ana: _uploaded_avatar(), ben: _linked_avatar(), cleo: None, dan: None}
        rows = [(ben.user_id, ana), (ana.user_id, ben), (dan.user_id, root), (root.user_id, cleo)]
        assert all(row_id != account.user_id for row_id, account in rows), f"premise: each settings row takes the id of another account: {[(row_id, account.username, account.user_id) for row_id, account in rows]}"
        await _private_settings_rows(private, [(row_id, account, avatars[account]) for row_id, account in rows])

        items = await _private_listed(private, cookie)

        wanted = {account.username: avatar for account, avatar in avatars.items()}
        found = {account.username: _avatar_of(items.get(account.user_id)) for account in avatars}
        violations: list[str] = []
        _expect(violations, sorted(items) == sorted(account.user_id for account in avatars), f"GET /users must list every account of the instance, these five: {sorted(items)}")
        _expect(violations, found == wanted, f"avatar_url must be each account's own, null without one: expected {wanted}, got {found}")
        for account, avatar in avatars.items():
            violations += _user_item_violations(items.get(account.user_id), account, active=True, superuser=account == root, avatar_url=avatar)
        for account in (ana, dan):
            change = {"is_superuser": True}
            response = await _call(private, "PATCH", f"/users/{account.user_id}", cookie=cookie, json=change)
            listed = (await _private_listed(private, cookie)).get(account.user_id)
            violations += _patch_answer_violations(change, response, listed, account, superuser=True, avatar_url=avatars[account])
        assert not violations, f"Each account must carry its own avatar, whatever the ids of the settings rows (lot N69-4):{_verdict(violations)}"
        print_success("five accounts, each its own avatar or null, in the list and in the PATCH answers")

    # red until N69-4
    def test_admin_user_read_declares_avatar_url_null_by_default(self) -> None:
        """UADM-AV-04: AdminUserRead declares ``avatar_url: Optional[str]``, null by default — an AdminUserRead built without it, as UADM-064 builds one, has no avatar —, and nothing else changes: its fields are exactly the ten an account is listed with."""
        print_section("UADM-AV-04: AdminUserRead.avatar_url")
        declared = AdminUserRead.model_fields.get("avatar_url")
        assert declared is not None, f"AdminUserRead must declare avatar_url (lot N69-4, point 20); it declares {sorted(AdminUserRead.model_fields)}"
        built = AdminUserRead(id=1, username="built", email="built@example.com", is_active=True, is_superuser=False, created_at=utcnow(), protected=False)

        violations: list[str] = []
        _expect(violations, declared.annotation == Optional[str], f"avatar_url must be an Optional[str]: {declared.annotation!r}")
        _expect(violations, not declared.is_required() and declared.default is None, f"avatar_url must default to null: required {declared.is_required()}, default {declared.default!r}")
        _expect(violations, getattr(built, "avatar_url", "<missing>") is None, f"an account built without it must have no avatar: {getattr(built, 'avatar_url', '<missing>')!r}")
        _expect(violations, set(AdminUserRead.model_fields) == USER_ITEM_KEYS, f"AdminUserRead must be exactly {sorted(USER_ITEM_KEYS)}: {sorted(AdminUserRead.model_fields)}")
        assert not violations, f"AdminUserRead.avatar_url broke its contract:{_verdict(violations)}"
        print_success("an Optional[str], null by default, ten fields")


# ============================================================================
# E-7: THE ACCOUNT WAITING FOR ITS EMAIL VERIFICATION IN THE USERS TAB (point 21)
# ============================================================================


@dataclass(frozen=True)
class _VerificationScene:
    """An account of the private instance: whether it is active and an administrator, its tokens as ``(purpose, state)`` in the order they are issued (``_private_link``), and what point 21 expects of it in GET /users: ``pending_verification`` (it waits for its verification link), ``holds_place`` (a live link holds its place) and ``pending_setup`` (the initial administrator waiting for its F02 setup, which waits for no verification)."""

    active: bool
    tokens: tuple[tuple[AccountTokenPurpose, str], ...]
    pending_verification: bool
    holds_place: bool
    superuser: bool = False
    pending_setup: bool = False


#: Every state of the links of an account that point 21 tells apart. The first two are the ones that wait — the badge stays
#: once the link expired, the place does not —; the rest are the accounts that do not.
VERIFICATION_SCENES = [
    pytest.param(_VerificationScene(active=False, tokens=((EMAIL_VERIFICATION, "live"),), pending_verification=True, holds_place=True), id="inactive-with-a-live-verification-link"),
    pytest.param(_VerificationScene(active=False, tokens=((EMAIL_VERIFICATION, "expired"),), pending_verification=True, holds_place=False), id="inactive-with-an-expired-verification-link"),
    pytest.param(_VerificationScene(active=False, tokens=((EMAIL_VERIFICATION, "revoked"),), pending_verification=False, holds_place=False), id="inactive-with-a-revoked-verification-link"),
    pytest.param(_VerificationScene(active=False, tokens=((EMAIL_VERIFICATION, "consumed"),), pending_verification=False, holds_place=False), id="inactive-with-a-consumed-verification-link"),
    pytest.param(_VerificationScene(active=False, tokens=((EMAIL_VERIFICATION, "revoked"), (EMAIL_VERIFICATION, "live")), pending_verification=True, holds_place=True), id="inactive-asked-for-the-link-again"),
    pytest.param(_VerificationScene(active=False, tokens=(), pending_verification=False, holds_place=False), id="inactive-without-any-link"),
    pytest.param(_VerificationScene(active=False, tokens=((PASSWORD_RESET, "live"),), pending_verification=False, holds_place=False), id="inactive-with-a-reset-link-only"),
    pytest.param(_VerificationScene(active=True, tokens=((EMAIL_VERIFICATION, "live"),), pending_verification=False, holds_place=False), id="active-with-a-stray-live-verification-link"),
    pytest.param(_VerificationScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "live"),), pending_verification=False, holds_place=False, pending_setup=True), id="the-initial-administrator-waiting-for-its-setup"),
]


async def _waiting_by_the_service(private: _Private, user_id: int) -> tuple[bool, bool]:
    """``(awaiting_verification, holds_place)`` as ``email_verification`` answers them for the account, read fresh from the private database: the service's own criterion — the one the sign-in's 403 EMAIL_NOT_VERIFIED reads —, which point 21 reuses for ``pending_verification``, and the place a live link holds."""
    async with AsyncSession(private.engine) as session:
        user = await user_service.get_user_by_id(session, user_id)
        assert user is not None, f"Setup: the account {user_id} must exist in the private database"
        return await email_verification.awaiting_verification(session, user), await email_verification.holds_place(session, user)


async def _unspent_verification_links(private: _Private, user_id: int) -> list[int]:
    """The ids of the account's ``email_verification`` tokens neither consumed nor revoked, live or expired: the rows a waiting account is made of, read from the table."""
    return [row.id for row in await _private_tokens(private) if row.user_id == user_id and row.purpose == EMAIL_VERIFICATION.value and row.consumed_at is None and row.revoked_at is None]


def _waiting_answer_violations(step: str, response: httpx.Response, listed: Optional[dict[str, Any]], account: _Account, *, active: bool, superuser: bool, holds_place: bool, pending_verification: bool) -> list[str]:
    """What is wrong with the answer of a PATCH on ``account`` and with the item GET /users listed right after (``listed``): a 200, the account exactly its eleven fields with these values, whatever state the PATCH left it in, and the answer the very item listed — it replaces the account's row in the Users tab."""
    if response.status_code != 200:
        return [f"{step}: expected 200, got {response.status_code} {response.text}"]
    answer = response.json()
    flags = {"active": active, "superuser": superuser, "holds_place": holds_place, "pending_verification": pending_verification}
    violations = [f"{step}, its answer: {problem}" for problem in _user_item_violations(answer, account, active=active, superuser=superuser, holds_place=holds_place, pending_verification=pending_verification)]
    violations += [f"{step}, listed right after: {problem}" for problem in _user_item_violations(listed, account, active=active, superuser=superuser, holds_place=holds_place, pending_verification=pending_verification)]
    _expect(violations, _comparable(answer) == _comparable(listed), f"{step}: the answer must be the account as GET /users lists it right after ({flags}): answered {answer}, listed {listed}")
    return violations


class TestAnAccountWaitingForItsVerificationInTheUsersTab:
    """Lot E-7, point 21: the Users tab tells the account waiting for its email verification link from a deactivated one. In-process only, on the private instance: every account and token row is the test's, and the whole item — ``holds_place``, ``pending_setup`` and ``pending_verification`` together — is read."""

    # red until E-7
    @pytest.mark.asyncio
    @pytest.mark.parametrize("scene", VERIFICATION_SCENES)
    async def test_pending_verification_is_an_inactive_account_with_an_unspent_verification_link(self, private: _Private, scene: _VerificationScene) -> None:
        """UADM-VER-01: an account in one state of its links, beside root, the caller. GET /users → its pending_verification is true exactly when it is inactive and holds an email_verification token neither consumed nor revoked — live or expired alike: the badge stays after the link expired — (the criterion of email_verification.awaiting_verification, which the sign-in's 403 EMAIL_NOT_VERIFIED reads); its holds_place is true only with a live link (an expired one holds no place), its pending_setup true only for the initial administrator waiting for its setup, which waits for no verification. The whole item is read, its eleven fields with the three flags together; root's are all false.

        The scenes: one live link; one expired; one revoked only — what an administrator's deactivation of a waiting account
        leaves, an ordinary deactivated account —; one consumed only; a revoked link then a live one — «send the link
        again» —; no token at all; a live reset link only; an ACTIVE account with a stray unspent live verification token
        (an active account never waits, and holds no place); the initial administrator, an inactive superuser with a live
        setup link.

        Premise first: the service's own reading of the scene — awaiting_verification, holds_place, and
        pending_admin_filter() — says what the scene says. If one no longer does, the criterion has moved, and this
        expectation moves with it, not the flag.
        """
        print_section(f"UADM-VER-01: pending_verification of an account active={scene.active}, administrator={scene.superuser}, tokens {[(purpose.value, state) for purpose, state in scene.tokens]}")
        root, cookie = await _admin(private)
        subject = await _add_user(private, "subject", admin=scene.superuser, active=scene.active)
        for purpose, state in scene.tokens:
            await _private_link(private, subject.user_id, purpose, state)
        awaiting, holds = await _waiting_by_the_service(private, subject.user_id)
        setup = subject.user_id in await _pending_admin_ids(private)
        assert (awaiting, holds, setup) == (
            scene.pending_verification,
            scene.holds_place,
            scene.pending_setup,
        ), f"premise: (awaiting_verification, holds_place, pending_admin_filter selects it) is {(awaiting, holds, setup)}; point 21 expects {(scene.pending_verification, scene.holds_place, scene.pending_setup)} because it is the same notion — if the criterion moved, this expectation moves with it"

        items = await _private_listed(private, cookie)

        violations = _user_item_violations(items.get(subject.user_id), subject, active=scene.active, superuser=scene.superuser, holds_place=scene.holds_place, pending_setup=scene.pending_setup, pending_verification=scene.pending_verification)
        violations += _user_item_violations(items.get(root.user_id), root, active=True, superuser=True)
        assert not violations, f"pending_verification must be the criterion of awaiting_verification, holds_place and pending_setup unchanged:{_verdict(violations)}"
        print_success(f"pending_verification {scene.pending_verification}, holds_place {scene.holds_place}, pending_setup {scene.pending_setup}; root false")

    # red until E-7
    @pytest.mark.asyncio
    async def test_pending_verification_is_decided_per_account(self, private: _Private) -> None:
        """UADM-VER-02: root (the caller), an active member, an inactive account with a live verification link, an inactive one with no token at all, and an inactive one whose only verification link was revoked. GET /users → pending_verification true for the account with the live link only — with holds_place true —, false for every other account: another account's live link makes nobody else wait, the inactive account without a link, and the one whose own link was revoked beside it, included. Every account of the instance is listed, each exactly its eleven fields.

        Premise first: the service reads each account as the case built it — the waiting one waits and holds its place,
        no other does.
        """
        print_section("UADM-VER-02: pending_verification account by account")
        root, cookie = await _admin(private)
        member = await _add_user(private, "member")
        waiting = await _add_user(private, "waiting", active=False)
        idle = await _add_user(private, "idle", active=False)
        spent = await _add_user(private, "spent", active=False)
        await _private_link(private, waiting.user_id, EMAIL_VERIFICATION, "live")
        await _private_link(private, spent.user_id, EMAIL_VERIFICATION, "revoked")
        # (account, is_active, is_superuser, holds_place, pending_verification)
        expected = [(root, True, True, False, False), (member, True, False, False, False), (waiting, False, False, True, True), (idle, False, False, False, False), (spent, False, False, False, False)]
        read = {account.username: await _waiting_by_the_service(private, account.user_id) for account, *_ in expected}
        assert read == {"root": (False, False), "member": (False, False), "waiting": (True, True), "idle": (False, False), "spent": (False, False)}, f"premise: the service reads the waiting account as waiting and holding its place, no other: {read}"

        items = await _private_listed(private, cookie)

        found = {item.get("username"): item.get("pending_verification", "<missing>") for item in items.values()}
        violations: list[str] = []
        _expect(violations, sorted(items) == sorted(row[0].user_id for row in expected), f"GET /users must list every account of the instance: {sorted(items)}")
        _expect(violations, found == {"root": False, "member": False, "waiting": True, "idle": False, "spent": False}, f"pending_verification must be true for the account with the live link only: {found}")
        for account, active, superuser, holds_place, pending_verification in expected:
            violations += _user_item_violations(items.get(account.user_id), account, active=active, superuser=superuser, holds_place=holds_place, pending_verification=pending_verification)
        assert not violations, f"pending_verification must be decided account by account:{_verdict(violations)}"
        print_success("true for the waiting account only; another account's link makes nobody else wait")

    # red until E-7
    @pytest.mark.asyncio
    async def test_the_patch_answer_carries_pending_verification_and_ending_the_wait_clears_it(self, private: _Private) -> None:
        """UADM-VER-03: an inactive account with a live verification link, beside root. PATCH {is_superuser: true} → 200, the account exactly its eleven fields, still inactive, now an administrator, pending_verification true and holds_place true — promoting it ends no wait: its link is still unspent —, and the answer is the item GET /users lists right after. Then PATCH {is_active: false}, the administrator ending the wait → 200, still inactive and an administrator, pending_verification false and holds_place false — its verification links are revoked: an ordinary deactivated account —, the answer again the item GET /users lists right after, and no verification token left unspent.

        Premise first: the service reads the account as waiting, holding its place, and it holds exactly one unspent verification link.
        """
        print_section("UADM-VER-03: PATCH on an account waiting for its verification link")
        _, cookie = await _admin(private)
        waiting = await _add_user(private, "waiting", active=False)
        await _private_link(private, waiting.user_id, EMAIL_VERIFICATION, "live")
        assert await _waiting_by_the_service(private, waiting.user_id) == (True, True), "premise: the account waits for its verification link and holds its place"
        assert len(await _unspent_verification_links(private, waiting.user_id)) == 1, "premise: the account holds exactly one unspent verification link"

        promote = await _call(private, "PATCH", f"/users/{waiting.user_id}", cookie=cookie, json={"is_superuser": True})
        promoted_list = (await _private_listed(private, cookie)).get(waiting.user_id)
        waiting_after_promotion = await _waiting_by_the_service(private, waiting.user_id)
        links_after_promotion = await _unspent_verification_links(private, waiting.user_id)
        end = await _call(private, "PATCH", f"/users/{waiting.user_id}", cookie=cookie, json={"is_active": False})
        ended_list = (await _private_listed(private, cookie)).get(waiting.user_id)
        links_after_end = await _unspent_verification_links(private, waiting.user_id)

        violations = _waiting_answer_violations("PATCH {is_superuser: true}", promote, promoted_list, waiting, active=False, superuser=True, holds_place=True, pending_verification=True)
        _expect(violations, waiting_after_promotion == (True, True) and len(links_after_promotion) == 1, f"promoting the account must end no wait: (awaiting_verification, holds_place) {waiting_after_promotion}, unspent verification links {links_after_promotion}")
        violations += _waiting_answer_violations("PATCH {is_active: false}", end, ended_list, waiting, active=False, superuser=True, holds_place=False, pending_verification=False)
        _expect(violations, links_after_end == [], f"ending the wait must revoke its verification links, none unspent: {links_after_end}")
        assert not violations, f"The PATCH answer must carry pending_verification as the list does, and ending the wait must clear it:{_verdict(violations)}"
        print_success("promoted: still waiting, place held; wait ended: false, false; each answer as listed right after")

    # red until E-7
    @pytest.mark.asyncio
    async def test_an_account_whose_link_expired_is_pending_and_its_reactivation_clears_it(self, private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-VER-04: root, an active member, and an inactive account whose only verification link expired, with LIBREFOLIO_MAX_USERS=3: two places taken — the active accounts; the expired link holds none —, one free. GET /users → the account pending_verification true and holds_place false: the badge stays after the link expired, the place does not; usage used 2 of 3. PATCH {is_active: true} → 200, the account exactly its eleven fields, active, pending_verification false and holds_place false, the answer the item GET /users lists right after, its verification link revoked (none unspent), usage used 3.

        Premise first: the service reads the account as waiting without holding a place, and it holds exactly one unspent
        verification link, expired.
        """
        print_section("UADM-VER-04: an expired verification link, then the reactivation")
        _, cookie = await _admin(private)
        await _add_user(private, "member")
        waiting = await _add_user(private, "waiting", active=False)
        await _private_link(private, waiting.user_id, EMAIL_VERIFICATION, "expired")
        monkeypatch.setenv(MAX_USERS_VARIABLE, "3")
        assert await _waiting_by_the_service(private, waiting.user_id) == (True, False), "premise: the account waits for its verification link, whose expiry freed its place"
        assert len(await _unspent_verification_links(private, waiting.user_id)) == 1, "premise: the account holds exactly one unspent verification link, expired"

        before, usage_before = await _private_view(private, cookie, waiting.user_id)
        response = await _call(private, "PATCH", f"/users/{waiting.user_id}", cookie=cookie, json={"is_active": True})
        after, usage_after = await _private_view(private, cookie, waiting.user_id)
        links_after = await _unspent_verification_links(private, waiting.user_id)

        violations = [f"listed before the reactivation: {problem}" for problem in _user_item_violations(before, waiting, active=False, superuser=False, holds_place=False, pending_verification=True)]
        _expect(violations, usage_before == {"used": 2, "max_users": 3, "billing_url": None}, f"before the reactivation the expired link holds no place, one is free: usage {usage_before}")
        violations += _waiting_answer_violations("PATCH {is_active: true}", response, after, waiting, active=True, superuser=False, holds_place=False, pending_verification=False)
        _expect(violations, links_after == [], f"the reactivation must revoke its verification link, none unspent: {links_after}")
        _expect(violations, usage_after == {"used": 3, "max_users": 3, "billing_url": None}, f"after the reactivation the account takes the free place: usage {usage_after}")
        assert not violations, f"An account whose link expired must be pending, and its reactivation must clear it:{_verdict(violations)}"
        print_success("expired link: pending, place free; reactivated: 200, active, not pending")

    # red until E-7
    def test_admin_user_read_declares_pending_verification_false_by_default(self) -> None:
        """UADM-VER-05: AdminUserRead declares ``pending_verification: bool``, false by default — an AdminUserRead built without it, as UADM-064 and UADM-AV-04 build one, does not wait for a verification link —, and nothing else changes: its fields are exactly the eleven an account is listed with."""
        print_section("UADM-VER-05: AdminUserRead.pending_verification")
        declared = AdminUserRead.model_fields.get("pending_verification")
        assert declared is not None, f"AdminUserRead must declare pending_verification (lot E-7, point 21); it declares {sorted(AdminUserRead.model_fields)}"
        built = AdminUserRead(id=1, username="built", email="built@example.com", is_active=False, is_superuser=False, created_at=utcnow(), protected=False)

        violations: list[str] = []
        _expect(violations, declared.annotation is bool, f"pending_verification must be a bool: {declared.annotation!r}")
        _expect(violations, not declared.is_required() and declared.default is False, f"pending_verification must default to false: required {declared.is_required()}, default {declared.default!r}")
        _expect(violations, getattr(built, "pending_verification", "<missing>") is False, f"an account built without it must not wait for a verification link: {getattr(built, 'pending_verification', '<missing>')!r}")
        _expect(violations, set(AdminUserRead.model_fields) == USER_ITEM_KEYS, f"AdminUserRead must be exactly {sorted(USER_ITEM_KEYS)}: {sorted(AdminUserRead.model_fields)}")
        assert not violations, f"AdminUserRead.pending_verification broke its contract:{_verdict(violations)}"
        print_success("a bool, false by default, eleven fields")
