# 👥 Users & Invitations

The **Users** tab of **Settings › Administration** is where an administrator looks after the
accounts of the instance: who can sign in, who is an administrator, and who is invited to join. It
works the same whether you host LibreFolio yourself or a hosting provider runs it for you.

---

## 🧭 Open the Tab {: #open-the-tab }

Open **Settings** (gear icon in the sidebar), then **Administration** and its **Users** tab, next to
**Global Settings**. Only administrators have this tab: everyone else does not see it.

The tab has three parts: the places taken, at the top; the **Accounts**; the **Open invitations**.
After each change, the tab reloads its lists, so it always shows what the server holds.

!!! tip "💻 On a server without a browser"

    The [command line](cli_tools.md) does most of this too: `user invite`, `user reset-link`,
    `user deactivate` and `user activate`, `user promote` and `user demote`, `user reset-onboarding`.
    It can also go past the user limit. It cannot delete an account or revoke an invitation.

---

## 📏 Places and Subscription {: #places }

The header counts the places taken: **3 / 10 accounts** when the instance has a user limit,
**3 accounts** when it has none. Active accounts and open invitations take a place, and so does an
account [waiting for its email](#waiting) while its link is live, and so does an
initial administrator still [waiting for its setup link](#pending-setup); deactivated
accounts do not. The limit is set on the server with `LIBREFOLIO_MAX_USERS`: see «When the Instance Is Full» in
[Environment Variables](configuration.md).

- 💳 **Manage subscription** appears next to the count only when the server has a billing page
  (`LIBREFOLIO_BILLING_URL`), as a hosting provider sets one for a managed instance. It opens that
  page in a new tab.
- 🚫 When the instance is full, a banner says *The instance is full: no new invitation until you
  deactivate or delete an account, or revoke an invitation.*, with **Manage subscription** when
  there is a billing page. **Invite** is off, and a deactivated account cannot be reactivated until
  a place is free, unless it is [waiting for its email](#waiting) with a live link.
- 🔒 **Invite** is also off while registration is closed. If the **Registration** global setting is
  **Closed**, the tab tells you to change it there ([Global Settings](settings.md), «Who Can Sign
  Up»). If the server closes it with `LIBREFOLIO_REGISTRATION`, the tab names the variable: only the
  server's configuration can open it again.

---

## 👤 Accounts {: #accounts }

One row per account, oldest first: the username with its badges, then the e-mail and the creation
date.

| Badge | Meaning |
|---|---|
| **You** | Your own account |
| **Admin** | An administrator: it manages the instance, its settings, its users and its invitations |
| **Deactivated** | The account cannot sign in, and takes no place — unless it is [waiting for its email](#waiting) |
| **Waiting for setup** | The [initial administrator](hosting_providers.md#initial-admin), not active yet: nobody has used its setup link, nor set the account up another way. Shown instead of **Deactivated**: see [Waiting for Its Setup Link](#pending-setup) |
| **Protected** | Nobody can deactivate, demote or delete it: see [When an Action Is Off](#action-off) |

Click a row to open its actions, and again to close them. Your own row has none: it says *This is
your account. Manage it from:* with a link to **Profile**, the tab where you change your details or
[delete your account](../user/settings/profile.md).

### ⚙️ What Each Action Does {: #actions }

| Action | What it does | Asks first |
|---|---|---|
| **Deactivate** | The account can no longer sign in, and is signed out of every device. Its brokers and transactions stay, and its place is freed. Shown for an active account | ✅ |
| **Reactivate** | The account can sign in again, with its data as it was; its old sessions do not come back. It takes a place again, so it needs a free one. Shown for a deactivated account, but not for the initial administrator [waiting for its setup link](#pending-setup) | — |
| **Make administrator** | The account manages the instance too: settings, users and invitations | ✅ |
| **Remove administrator** | The account stays, as a regular user, and is signed out of every device | ✅ |
| **Password-reset link** | A link to choose a new password: see [Password-Reset Links](#reset-links) | Its own dialog |
| **Sign out everywhere** | The account is signed out of every device: its user signs in again on each one. The account stays active | ✅ |
| **Restart the guides** | The next time its user opens LibreFolio, the [Welcome setup](../user/getting-started.md#welcome-setup) and every guide start again, as for a new account. Their data and preferences stay | ✅ |
| **Delete** | Removes the account for good: see [Delete an Account](#delete) | Its own dialog |

### 🔒 When an Action Is Off {: #action-off }

LibreFolio turns off the actions it knows the server would refuse, and says why under the buttons:

| The panel says | Off | What you can do |
|---|---|---|
| *This account is protected: nobody can deactivate, demote or delete it.* | **Deactivate**, **Remove administrator**, **Delete** | Nothing, from this tab |
| *It is the only active administrator: it cannot be deactivated or demoted.* | **Deactivate**, **Remove administrator** | Make another account an administrator first |
| *The instance is full: free a place to reactivate it.* | **Reactivate** | Deactivate or delete another account, or revoke an invitation; the command line's `user activate` goes past the limit |
| *An administrator must be demoted before it can be deleted.* | **Delete** | **Remove administrator** first, then **Delete** |
| *This administrator account activates through its setup link. If the link is lost, run `dev.py user setup-link` on the server, or ask your hosting provider.* | No **Reactivate** | Have its setup link used, or give a new one: see [Waiting for Its Setup Link](#pending-setup) |

- 👑 The instance always keeps an active administrator. Your own row has no actions, so to step
  down: make another account an administrator, then ask them to remove your rights.
- 🛡️ **Protected** is reserved for the administrator who pays for a
  [managed instance](hosting_providers.md#managed-profile). No account is protected on a
  self-hosted instance.

### ⏳ Accounts Waiting for Their Email {: #waiting }

With **Require Email Verification** on ([Global Settings](settings.md)), a new account waits until
its owner opens the link LibreFolio emails to its address. Until then:

- its row shows **Deactivated**: this version has no badge of its own for a waiting account;
- it takes a place while its link is live, that is for 24 hours after the last link sent;
- **Reactivate** lets it in at once: it can sign in, and the links already sent stop working. While
  its link is live, this takes no extra place, since its place is already counted: **Reactivate**
  works even on a full instance, and so does `user activate` on the
  [command line](cli_tools.md), without a limit warning. Once the link has expired, reactivating it
  needs a free place, as for any deactivated account;
- **Delete** removes it, as any account. This tab offers no **Deactivate** for an account that is
  not active; `user deactivate` on the command line, or the administrator API
  (`PATCH /api/v1/users/{id}` with `is_active: false`), keeps it but ends the wait: its links stop
  working, its place is free, and it can sign in only once reactivated.

How the verification works, and its limits: [Email Verification](email.md#verification).

### 👑 Waiting for Its Setup Link {: #pending-setup }

When LibreFolio creates the administrator of `LIBREFOLIO_ADMIN_EMAIL` at its first start, the
account waits, not yet active, until someone opens its setup link and chooses the password, or sets
it up another way (below): see
[The Initial Administrator](hosting_providers.md#initial-admin). Until then:

- its row shows **Waiting for setup** instead of **Deactivated**, even once its link has expired;
- it takes a place, as an active account does;
- its panel has no **Reactivate**: nobody knows its password, and activating it would also stop its
  setup link from working. Under the buttons, the panel says instead: *This administrator account
  activates through its setup link. If the link is lost, run `dev.py user setup-link` on the
  server, or ask your hosting provider.*;
- the other actions are those of any deactivated account. **Remove administrator**, for example,
  leaves it waiting for its setup, as a regular account.

The server refuses to activate it too: `PATCH /api/v1/users/{id}` with `is_active: true` answers
`409`, with the code `PENDING_SETUP`, and changes nothing. If a **Reactivate** reaches the server
anyway, for example from a list loaded before, the tab says why instead of a generic error.
`GET /api/v1/users` marks the account with `pending_setup: true`.

This version has no button for a new setup link: on the server, `user setup-link` prints one (see
«A New Setup Link for the Initial Administrator» in [Command-Line Tools](cli_tools.md)), and on an
instance a hosting provider runs, the provider gives it. Once the link is used, the account is
active, like any other.

The account also stops waiting when it is set up another way, without its link:

- **activated on the server** with `user activate`: the command line does not refuse it, unlike
  this tab. Its password is still the one nobody knows, until `user reset` or a reset link gives it
  one;
- **given a password**, with `user reset` on the server, or with a
  [password-reset link](#reset-links) once it is used: one you create with
  **Password-reset link** in its panel, or one `user reset-link` prints. The account stays inactive
  until it is activated.

From then on, every setup link it had stops working: the setup page says *This link has been
withdrawn.*, and `user setup-link` finds no administrator waiting. The tab shows it as any other
account: **Deactivated** while it is not active, with **Reactivate**, and `GET /api/v1/users` marks
it `pending_setup: false`. Like any deactivated account it then takes no place, so **Reactivate**
needs a free one. A reset link nobody uses, or **Remove administrator**, leaves it waiting.

### 🔤 Usernames with an @ {: #usernames-with-at }

From version 1.3, a new username cannot contain `@`: at sign-in, LibreFolio reads anything with an
`@` as an email address. Registration, a change of username in the Profile and `user create` on the
[command line](cli_tools.md) refuse it, and a `LIBREFOLIO_ADMIN_USERNAME` with an `@` stops the
server at startup («The Initial Administrator» in [Environment Variables](configuration.md)).
Spaces, accented letters and signs such as `.`, `_`, `-` or `+` are still fine.

An account created before version 1.3 may have one, such as `anna@example.com` as its username:

- 🏷️ the username stays as it is: nothing renames it. Its user can change it in their
  [Profile](../user/settings/profile.md), to a name without `@`;
- 🔑 the account signs in with its email address, as every account has one. The username itself
  works only while no account has it as its email address: typed at sign-in, an address names the
  account that has it;
- 📧 no other account can take that username as its email address, in any capitals: registration,
  the Profile, `user create` and `user set-email` refuse it with *Email already registered*. The
  account itself can take it as its own address.

---

## ✉️ Invitations {: #invitations }

To invite someone:

1. Click **Invite**.
2. Optionally, write their address in **E-mail (optional)**. It is only a note of whom the
   invitation is for: the link works for whoever opens it. The list of invitations shows it, and
   the registration form starts with it, where the person can change it.
3. Tick **Administrator** if the new account should manage the instance.
4. Click **Create the link**: *Share this link: it works once, for 7 days.* Check the
   [server address](#server-address), click **Copy** and send the link yourself, by message or
   e-mail, or let LibreFolio email it: [Send by Email](#send-by-email).
5. Click **Done**: the invitation joins **Open invitations**.

The person opens the link and creates their account with the username, e-mail and password they
choose: [Getting Started](../user/getting-started.md) shows what they see.

- 🔗 The link is shown only once, when you create it. If it gets lost, revoke the invitation and
  create a new one.
- 📏 An invitation takes a place from the moment you create it until it is used, revoked or
  expires; the account it creates then takes that place.
- 🔤 An e-mail address belongs to one account only, whatever its capitals (`Anna@example.com` is
  `anna@example.com`), but only the letters A to Z are matched this way: `Émile@example.com` and
  `émile@example.com` are two different addresses.

### 📋 Open Invitations {: #open-invitations }

The invitations nobody has used yet, oldest first: the e-mail (or *No e-mail*), an **Admin** badge
when the invitation makes an administrator, and when it was created and expires. An invitation
leaves the list once it is used, revoked or expired.

**Revoke** withdraws an invitation at any time, after a confirmation: the link stops working at
once, and its place is freed.

---

## 🔑 Password-Reset Links {: #reset-links }

When someone forgot their password, send them a link to choose a new one themselves. With email,
they can also ask for one from the login page: see [Forgotten Passwords](email.md#forgot-password).

1. Open their row and click **Password-reset link**.
2. The dialog explains: *A single-use link to set a new password, valid 30 minutes. The links
   created before for this account stop working.* Click **Create the link**.
3. Check the [server address](#server-address), click **Copy** and send the link, or click
   **Send by email** ([Send by Email](#send-by-email)); then click **Done**.

- ⏱️ The link works once, for 30 minutes, and only the newest link of an account works.
- 🔒 It also stops working as soon as the person changes their password or email address, or you
  run `user reset` or `user set-email` on the [command line](cli_tools.md).
- 🚪 Creating the link signs nobody out. Once the person sets the new password, their account is
  signed out of every device.
- 🔗 The link is shown only once: if it gets lost, create a new one.

What the person sees is in [Getting Started](../user/getting-started.md).

---

## 🌐 The Server Address of a Link {: #server-address }

Invitation and password-reset links show in the same panel:

- **Server address**: where the link starts. It is filled in with `LIBREFOLIO_PUBLIC_URL` when the
  server sets it, otherwise with the address your browser is using now. *Change it if your users
  reach LibreFolio at another address*: for example, you are on `http://192.168.1.10:6040` at
  home, while your users go through `https://librefolio.example.com`.
- **Link**: the server address followed by the link's own path. **Copy** puts it on the clipboard;
  if the browser refuses, the link is selected so that you can copy it by hand. *Valid until …*
  gives its expiry.

When you change the address, your browser checks, half a second after you stop typing, that
**this** instance answers there, and not just any server. The filled-in address itself is not
checked.

| Message | What it means |
|---|---|
| *Checking that this LibreFolio answers at this address…* | The check is running |
| *This instance answers at this address.* | The link reaches this LibreFolio |
| *Something answers at this address, but not this instance: check it before sharing.* | Another LibreFolio answers there: probably not the address you meant |
| *This address could not be checked from this browser: you can still share the link.* | The browser got no answer it could read. Nothing answers there (a wrong or closed address, or no answer within 8 seconds); a page opened with `https://` checks an `http://` address, which the browser blocks; a page on a public address checks a local one, which some browsers block or allow only after asking your permission; or an older LibreFolio answers, which cannot be checked |
| *Enter an address that starts with http:// or https://, without ? or #.* | Not an address: **Copy** stays off until you fix it |

Whatever the result, except an address that is not one, you can copy the link: the check only
advises. Back on the filled-in address, the message goes away. How the check works:
[Address Probe](../developer/architecture/security.md#address-probe), for developers.

!!! tip "🌐 Set the address once"

    Set `LIBREFOLIO_PUBLIC_URL` to the address your users open, and the panel starts from it: see
    «Accounts and Sign-ups» in [Environment Variables](configuration.md). The
    [command line](cli_tools.md) puts it in front of the links it prints, too.

---

## 📧 Send by Email {: #send-by-email }

While the instance can send emails with a link — email **Ready** and `LIBREFOLIO_PUBLIC_URL` set to
an address LibreFolio can use ([Emails with a Link](email.md#public-url)) — both link dialogs have
**Send by email** under the link:

- **An invitation**: **Send to** starts with the address written in the invitation, and you can
  change it. Left empty, the email goes to the address written in the invitation; without one, the
  dialog asks for an address.
- **A password-reset link** has no field: the email goes to the address of the account, and only
  while the account is active.
- **The link in the email starts with `LIBREFOLIO_PUBLIC_URL`**, whatever the **Server address**
  above shows: the dialog says so.
- **The language**: an invitation goes in the language chosen in **Language of the email**, the
  instance's **Default Language** unless you pick another; a reset link goes in the account's. The
  dialog's answer names the language the email was written in.
- **The result** shows in the dialog: *Sent to …* with the address, or why the email did not go out
  ([Sending Errors](email.md#sending-errors)).

Without email, the button is not there: copy the link as before. The rules and the limits:
[Links Sent by an Administrator](email.md#admin-links).

---

## 🗑️ Delete an Account {: #delete }

Open the account's row and click **Delete**; for an administrator, click **Remove administrator**
first. The deletion follows the same rule as deleting one's own account
([Profile](../user/settings/profile.md)):

1. For an active account, the dialog first offers **Deactivate** instead: it keeps every broker and
   transaction and can be undone; the account just can no longer sign in.
2. Then it shows what the deletion would take:
    - **Deleted, with all their transactions and files**: the brokers the account is the only Owner
      of, each with its number of transactions. They go for the users it shared them with too.
      Without any, the dialog says *No broker is deleted.*;
    - **Shared brokers that stay (only the access goes)**: the other brokers the account can open,
      with its role on each;
    - a warning when transactions on other brokers are halves of transfers with the brokers that
      go: they stay, without their other half. A received transfer becomes an adjustment at its
      cost, and a transfer sent to one of those brokers an adjustment that takes the assets out at
      their average cost on the broker that sent them (see
      [Edit or delete a broker](../user/brokers/index.md)).
3. Type the account's username, then click **Delete Permanently**.

!!! danger "Deleting an account cannot be undone"

    The account, its settings and the brokers listed as deleted go at once, and whoever is signed
    in to it is signed out at their next request. If the deletion fails for a technical reason,
    nothing is deleted. If the dialog cannot load what the deletion would take, it does not let you
    delete: close it and try again.

How the rule works: [Deleting an Account](../developer/architecture/access_control.md#admin-account-deletion),
for developers.

---

## 🔗 Related

- 📝 **[Environment Variables](configuration.md)** — «Accounts and Sign-ups»: `LIBREFOLIO_MAX_USERS`,
  `LIBREFOLIO_REGISTRATION`, `LIBREFOLIO_PUBLIC_URL` and `LIBREFOLIO_BILLING_URL`
- ⚙️ **[Global Settings](settings.md)** — «Who Can Sign Up»: the **Registration** setting
- 🛠️ **[Command-Line Tools](cli_tools.md)** — «Manage Users»: most of these tasks, without a browser
- 👤 **[Profile](../user/settings/profile.md)** — Your own account, and how to delete it
- 🏢 **[Hosting for Others](hosting_providers.md)** — Running LibreFolio for other people
- 🧑‍💻 For developers: **[Administrator API](../developer/architecture/access_control.md#admin-user-api)**
  and **[Settings Components](../developer/frontend/components/features/settings.md#userstab)**
