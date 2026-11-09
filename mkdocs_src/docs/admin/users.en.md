# 👥 Users and Invitations

An administrator looks after the accounts of the instance — who can sign in, who is an administrator, who is invited — in one tab.

**Where:** **Settings › Administration › Users**. The same on every installation.

---

## 🧭 Open the Tab {: #open-the-tab }

1. Open **Settings** (gear icon in the sidebar), then **Administration**, then the **Users** tab, next to **Global Settings**.

    Only administrators see this tab.

The tab has three parts: the **places** taken, at the top; the **Accounts**; the **Account links**. After each change it reloads its lists: it always shows what the server holds.

!!! tip "💻 On a server without a browser"

    The [command line](cli_tools.md) does most of these things, on the server, in LibreFolio's folder:

    ```bash
    pipenv run ./dev.py user invite
    pipenv run ./dev.py user reset-link <username>
    pipenv run ./dev.py user deactivate <username>
    pipenv run ./dev.py user activate <username>
    pipenv run ./dev.py user promote <username>
    pipenv run ./dev.py user demote <username>
    pipenv run ./dev.py user reset-onboarding <username>
    ```

    With Docker, the command goes in the container: «Where to run the commands» in [Command-Line Tools](cli_tools.md).
    The command line also goes past the user limit. It cannot delete an account or revoke an invitation.

---

## 📏 Places {: #places }

The header counts the places taken: **3 / 10 accounts** with a user limit, **3 accounts** without.

| Takes a place | |
|---|---|
| Active account | ✅ |
| Open invitation | ✅ |
| Account [waiting for its email](#waiting) | ✅ while its link is live |
| Initial administrator [waiting for its setup link](#pending-setup) | ✅ |
| Deactivated account | ❌ |

**Where the limit is set:** in LibreFolio's `.env`, with `LIBREFOLIO_MAX_USERS`: «When the Instance Is Full» in [Environment Variables](configuration_accounts.md#user-limit).

When **Invite** is off:

| Why | What the tab says | What you can do |
|---|---|---|
| 🚫 The instance is full | A banner: *The instance is full: no new invitation until you deactivate or delete an account, or revoke an invitation.* Not even a deactivated account can be reactivated, unless it is [waiting for its email](#waiting) with a live link | Deactivate or delete an account, or revoke an invitation |
| 🔒 The **Registration** global setting is **Closed** | It tells you to change it in [Global Settings](settings.md), «Who Can Sign Up» | Change it there, or in [Who Can Sign Up](#registration) below |
| 🔒 The server closes registration with `LIBREFOLIO_REGISTRATION` | It names the variable | Only the server's configuration can open it again |

### 🚪 Who Can Sign Up {: #registration }

**Where:** the **Who can sign up** selector, next to **Invite**. It is the **Registration** global setting, the same as in [Global Settings](settings.md) («Who Can Sign Up»).

1. Choose **Open**, **By invitation** or **Closed**.

    The choice is saved at once, with no **Save** button, and the tab reads the setting again.

- ⚠️ Only **Open** asks you to confirm first: it lets in anyone who reaches the login page. If you cancel, the mode stays as it was.
- 🔒 If the server sets the mode with `LIBREFOLIO_REGISTRATION`, the selector is off and the tab names the variable.

---

## 👤 Accounts {: #accounts }

One row per account, oldest first: avatar, username with its badges, email, creation date. The avatar is the picture the user chose in their [Profile](../user/settings/profile.md); without an avatar, the first letter of the username in a circle.

| Badge | Meaning |
|---|---|
| **You** | Your own account |
| **Admin** | An administrator: it manages the instance, its settings, its users and its invitations |
| **Deactivated** | The account cannot sign in and takes no place |
| **Waiting for setup** | The [initial administrator](configuration_accounts.md#initial-admin), not active yet: nobody has used its setup link, nor set it up another way. In the place of **Deactivated**: see [Waiting for Its Setup Link](#pending-setup) |
| **Waiting for verification** | An account that has not yet opened the verification link sent to its address, even after the link has expired. It cannot sign in and takes a place while the link is live. In the place of **Deactivated**: see [Accounts Waiting for Their Email](#waiting) |

**Where the actions are:** click a row to open them, again to close them. Your own row has none: it says *This is your account. Manage it from:* with a link to **Profile**, where you change your details or [delete your account](../user/settings/profile.md).

### ⚙️ What Each Action Does {: #actions }

| Action | What it does | Asks to confirm |
|---|---|---|
| **Deactivate** | The account can no longer sign in and is signed out of every device. Brokers and transactions stay; its place is freed. Only for an active account | ✅ |
| **Reactivate** | The account signs in again, with its data; the old sessions do not come back. It takes a place again, so it needs a free one, unless it is [waiting for its email](#waiting) with a live link (the place is already counted). For a deactivated account, one waiting for its email included, but not for the initial administrator [waiting for its setup link](#pending-setup) | — |
| **Cancel setup link** | The setup link of the initial administrator [waiting for its setup](#pending-setup) stops working, the one already handed over included; the account keeps waiting for a new link. Only for that account, in the place of **Reactivate**: see [Cancel Its Setup Link](#cancel-setup) | ✅ |
| **Make administrator** | The account manages the instance too: settings, users and invitations | ✅ |
| **Remove administrator** | The account stays, as a regular user, and is signed out of every device | ✅ |
| **Password-reset link** | A link to choose a new password: see [Password-Reset Links](#reset-links) | Its own dialog |
| **Sign out everywhere** | The account is signed out of every device and signs in again on each one. It stays active | ✅ |
| **Restart the guides** | The next time LibreFolio is opened, the [Welcome Setup](../user/getting-started.md#welcome-setup) and every guide start again, as for a new account. Data and preferences stay | ✅ |
| **Delete** | Removes the account for good: see [Delete an Account](#delete) | Its own dialog |

### 🔒 When an Action Is Off {: #action-off }

LibreFolio turns off the actions the server would refuse and explains why under the buttons:

| The panel says | Off | What you can do |
|---|---|---|
| *It is the only active administrator: it cannot be deactivated or demoted.* | **Deactivate**, **Remove administrator** | Make another account an administrator first |
| *The instance is full: free a place to reactivate it.* | **Reactivate** | Deactivate or delete another account, or revoke an invitation; the command line's `user activate` goes past the limit |
| *An administrator must be demoted before it can be deleted.* | **Delete** | **Remove administrator** first, then **Delete** |
| *It waits for its setup: it keeps its role until then.* | **Remove administrator**, for the initial administrator [waiting for its setup link](#pending-setup) | [Cancel its setup link](#cancel-setup), or **Delete** the account, with no **Remove administrator** first |
| *This administrator account activates through its setup link. If the link is lost, run `dev.py user setup-link` on the server.* | No **Reactivate**: **Cancel setup link** in its place | Have its setup link used, or give a new one: see [Waiting for Its Setup Link](#pending-setup) |

- 👑 The instance always keeps an active administrator. Your own row has no actions: to step down, make another account an administrator, then ask them to remove your rights.

### ⏳ Accounts Waiting for Their Email {: #waiting }

With **Require Email Verification** on ([Global Settings](settings.md)), a new account waits until its owner confirms the address with the link LibreFolio emails them. Until then:

- 🏷️ the row shows **Waiting for verification** instead of **Deactivated**, even after the link has expired. Hover over the badge for the hint, or open the row: under the buttons it reads *Its owner has not opened the verification link yet: signing in offers to send a new one. Reactivate lets the account in at once, without the email.*;
- 📏 it takes a place while its link is live: 24 hours after the last link was sent;
- ✅ **Reactivate** lets it in at once: it can sign in, and the links already sent stop working. With the link still live, no free place is needed (its own is already counted): it works even on a full instance, as `user activate` on the [command line](cli_tools.md) does, without a limit warning. With the link expired, a free place is needed, as for any deactivated account;
- 🗑️ **Delete** removes it, as any account;
- ⛔ the tab offers no **Deactivate** for an account that is not active. On the server, `user deactivate`, or the administrator API (`PATCH /api/v1/users/{id}` with `is_active: false`), keeps it but ends the wait: its links stop working, its place is free, the row shows **Deactivated** again, and it can sign in only once reactivated.

How the verification works, and its limits: [Email Verification](email_flows.md#verification).

### 👑 Waiting for Its Setup Link {: #pending-setup }

When LibreFolio creates the administrator of `LIBREFOLIO_ADMIN_EMAIL` at the first start, the account waits, not active, until someone opens its setup link and chooses the password, or sets it up another way (below): [The Initial Administrator](configuration_accounts.md#initial-admin). Until then:

- 🏷️ the row shows **Waiting for setup** instead of **Deactivated**, even after the link has expired or been [cancelled](#cancel-setup);
- 📏 it takes a place, as an active account does;
- ⛔ the panel has no **Reactivate**: nobody knows its password, and activating it would also stop the setup link from working. In its place there is **Cancel setup link** ([below](#cancel-setup)), with the reason from the [table above](#action-off);
- 🔒 **Remove administrator** is off, with its reason ([table above](#action-off)). To stop the link already handed over, cancel it; to stop the account altogether, delete it;
- 🗑️ **Delete** needs no **Remove administrator** first, unlike every other administrator;
- the other actions are those of any deactivated account.

The server refuses to activate it or to demote it: `PATCH /api/v1/users/{id}` with `is_active: true`, or with `is_superuser: false`, answers `409`, code `PENDING_SETUP`, and changes nothing. If such a change reaches the server anyway, for example from a list loaded before, the tab says *This administrator waits for its setup: it can be neither reactivated nor demoted here.* `GET /api/v1/users` marks it with `pending_setup: true`.

**A new setup link.** This version has no button to create one.

**Where:** on the server, in LibreFolio's folder:

```bash
pipenv run ./dev.py user setup-link
```

The command prints the link: «A New Setup Link for the Initial Administrator» in [Command-Line Tools](cli_tools.md). Once used, the account is active like any other.

**Set up another way, without its link.** The account stops waiting this way too:

| Where | How | Result |
|---|---|---|
| On the server | `user activate` | The command line does not refuse it, unlike the tab, and prints no limit warning: the account already holds its place. Its password stays the one nobody knows, until `user reset` or a reset link gives it one |
| On the server | `user reset` | A password is assigned. The account stays inactive until it is activated |
| In its panel, or on the server | A [password-reset link](#reset-links) used: from **Password-reset link**, or printed by `user reset-link` | As above: inactive until it is activated |

From then on every setup link stops working: the setup page says *This link has been withdrawn.*, and `user setup-link` finds no administrator waiting. The tab shows it as any other account: **Deactivated** until it is active, with **Reactivate**, and `GET /api/v1/users` marks it with `pending_setup: false`. It takes no place any more, so **Reactivate** needs a free one. A reset link nobody uses leaves it waiting, as [cancelling its setup link](#cancel-setup) does.

### 🚫 Cancel Its Setup Link {: #cancel-setup }

When the link went to the wrong person, or someone else may have seen it (a forwarded email, the server's log).

**Where:** the row of the account **Waiting for setup**, **Cancel setup link** button. On the server, `user deactivate` on this account cancels the link the same way.

1. Open the row and click **Cancel setup link**.

    The dialog asks *Cancel the setup link of {username}?* and explains: *The link already handed over stops working. The account keeps waiting for its setup: a new link comes from «dev.py user setup-link» on the server.*

2. Click **Cancel the link**.

    A message confirms: *The setup link of {username} no longer works.*

What happens:

- 🔗 every setup link of the account stops working, the one handed over included: whoever opens it reads *This link has been withdrawn.* and cannot set the account up;
- ⏳ the account keeps waiting: the row still shows **Waiting for setup**, it keeps its place, and it cannot be reactivated here;
- 🔁 to let the administrator in, give a new link with `user setup-link` on the server (above). Restarting the server with the same `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` gives no new link: the instance has already seen that token. Each start logs a warning that the setup link was withdrawn, and asks to run `dev.py user setup-link` or to set a new token.

Special cases:

| Case | What happens |
|---|---|
| The administrator completed the setup after your list was loaded | Nothing to cancel: LibreFolio changes nothing and says *This administrator completed its setup in the meantime: nothing was changed.* The tab reloads: the row shows an active administrator, with **Deactivate** in the place of **Cancel setup link**; its owner has signed in |
| You want to remove the account | **Delete** ([Delete an Account](#delete)), with no **Remove administrator** first. The account is deleted with its setup links, the place is freed and nobody waits for a setup any more: `user setup-link` finds nobody, and the `LIBREFOLIO_ADMIN_*` variables create nothing at the next starts, since the instance has accounts |
| You want to remove it, but the setup was completed in the meantime | Nothing is deleted: the dialog says *An administrator must be demoted before it can be deleted.*, since it is now an active administrator |

### 🔤 Usernames with an @ {: #usernames-with-at }

From version 1.3 a new username cannot contain `@`: at sign-in, LibreFolio reads anything with an `@` as an email address. Registration, a change of username in the Profile and `user create` on the [command line](cli_tools.md) refuse it; a `LIBREFOLIO_ADMIN_USERNAME` with an `@` stops the server at startup («The Initial Administrator» in [Environment Variables](configuration_accounts.md#initial-admin)). Spaces, accented letters and signs such as `.`, `_`, `-` or `+` are fine.

An account created before version 1.3 may have one, for example `anna@example.com`:

- 🏷️ the username stays as it is: nothing renames it. The user can change it in their own [Profile](../user/settings/profile.md), to a name without `@`;
- 🔑 the account signs in with its own email address. The username works at sign-in only while no account has it as its email address: a typed address names the account that owns it;
- 📧 no other account can take that username as its email address, in any capitals: registration, the Profile, `user create` and `user set-email` refuse it with *Email already registered*. The account itself can take it as its own address.

---

## ✉️ Invitations {: #invitations }

**Where:** **Users**, **Invite** button. On the server: `pipenv run ./dev.py user invite` ([command line](cli_tools.md)).

1. Click **Invite**.

2. Optional: write their address in **E-mail (optional)**.

    It is only a note of whom the invitation is for: the link works for whoever opens it. The list of invitations shows it, and the registration form starts from it, editable.

3. Tick **Administrator** if the new account should manage the instance.

4. Click **Create the link**.

    *Share this link: it works once, for 7 days.* Check the [server address](#server-address), click **Copy** and send the link yourself (message or email), or let LibreFolio send it: [Send by Email](#send-by-email).

5. Click **Done**.

    The invitation appears in [Account links](#account-links). The person opens the link and creates the account with the username, email and password they choose: [Getting Started](../user/getting-started.md) shows what they see.

- 🔗 The link is shown only once, when you create it. If it gets lost, revoke the invitation and create a new one.
- 📏 An invitation takes a place from when you create it until it is used, revoked or expires; the account it creates then takes that place.
- 🔤 An email address belongs to one account only, whatever its capitals (`Anna@example.com` is `anna@example.com`), but only the letters A to Z are compared this way: `Émile@example.com` and `émile@example.com` are two different addresses.

---

## 🔑 Password-Reset Links {: #reset-links }

When someone has forgotten their password, send them a link to choose a new one by themselves. With email, they can also ask for one from the login page: [Forgotten Passwords](email_flows.md#forgot-password).

**Where:** the account's row, **Password-reset link** button. On the server: `pipenv run ./dev.py user reset-link <username>` ([command line](cli_tools.md)).

1. Open the row and click **Password-reset link**.

    The dialog explains: *A single-use link to set a new password, valid 30 minutes. The links created before for this account stop working.*

2. Click **Create the link**.

3. Check the [server address](#server-address), click **Copy** and send the link, or click **Send by email** ([Send by Email](#send-by-email)). Then **Done**.

    The person opens the link and chooses the password: [Getting Started](../user/getting-started.md).

- ⏱️ The link works once, for 30 minutes; only the newest link of an account is valid.
- 🔒 It also stops working as soon as the person changes their password or email address, or when you run `user reset` or `user set-email` on the [command line](cli_tools.md).
- 🚪 Creating the link signs nobody out. When the person sets the new password, the account is signed out of every device.
- 🔗 The link is shown only once: if it gets lost, create a new one.

---

## 📋 Account Links {: #account-links }

Every single-use link of the instance, and where it stands: invitations, password-reset links, email verifications, the setup link of the first administrator, the email change of a managed instance's owner. The link itself never shows here: it shows only once, when it is created.

**Where:** **Users**, the **Account links** section, under the accounts.

| Column | What it shows |
|---|---|
| **Type** | *Invitation*, *Password reset*, *Email verification*, *Administrator setup* or *Email change* |
| **For** | The account the link acts on; for an invitation, the address written in it, or *Anyone with the link*; an **Admin** badge when the invitation creates an administrator |
| **Created by** | The administrator who created it; *—* when LibreFolio or the person asked for it (a verification, a reset from the login page) |
| **Created**, **Expires** | Date and time |
| **State** | *Open*; *Used*, with when and by whom; *Expired*; *Revoked*, with when |

The open links are in the first table. The closed ones — used, expired or revoked — are in **Closed links**, folded: click it to open it. Each table sorts by a column (click its header), filters by a column (the funnel in its header), hides or shows columns (the eye) and pages through long lists.

**Revoke**, in the menu (⋮) of an open link, withdraws it after a confirmation: the link stops working at once, and an invitation frees its place. Invitations, password-reset links and email verifications can be revoked here. The setup link of the waiting administrator is cancelled from its account ([Cancel Its Setup Link](#cancel-setup)); the owner's email change follows the address the host set, and is not revoked here.

---

## 🌐 The Server Address of a Link {: #server-address }

Invitation and password-reset links show in the same panel:

- **Server address**: where the link starts. Filled in with `LIBREFOLIO_PUBLIC_URL` when the server sets it, otherwise with the address your browser is using now. *Change it if your users reach LibreFolio at another address*: for example you are on `http://192.168.1.10:6040` at home, your users go through `https://librefolio.example.com`.
- **Link**: the server address followed by the link's path. **Copy** puts it on the clipboard; if the browser refuses, the link is selected so that you can copy it by hand. *Valid until …* gives its expiry.

When you change the address, half a second after you stop typing the browser checks that **this** instance answers there, and not just any server: it loads `<address>/api/v1/auth/address-probe.png?nonce=…`. The filled-in address itself is not checked.

| Message | What it means |
|---|---|
| *Checking that this LibreFolio answers at this address…* | The check is running |
| *This instance answers at this address.* | The link reaches this LibreFolio |
| *Something answers at this address, but not this instance: check it before sharing.* | Another LibreFolio answers there: probably not the address you meant |
| *This address could not be checked from this browser: you can still share the link.* | The browser did not load the image. Nothing answers there (a wrong or closed address, or no answer within 8 seconds); an `https://` page checks an `http://` address, which the browser blocks; a page on a public address checks a local address, which some browsers block or allow only after asking your permission; a blocked instance does not serve the image; or an older LibreFolio answers, which cannot be checked |
| *Enter an address that starts with http:// or https://, without ? or #.* | Not an address: **Copy** stays off until you fix it |

Whatever the result, except an address that is not one, you can copy the link: the check is only advice. Back on the filled-in address, the message goes away. How it works: [Address Probe](../developer/architecture/security.md#address-probe), for developers.

!!! tip "🌐 Set the address once"

    **Where:** in LibreFolio's `.env`, the address your users open:

    ```bash
    LIBREFOLIO_PUBLIC_URL=https://librefolio.example.com
    ```

    The panel starts from there: «Accounts and Sign-ups» in [Environment Variables](configuration_accounts.md#accounts). The [command line](cli_tools.md) puts it in front of the links it prints, too.

---

## 📧 Send by Email {: #send-by-email }

Condition: email **Ready** and `LIBREFOLIO_PUBLIC_URL` set to an address LibreFolio can use ([Emails with a Link](email_flows.md#public-url)). Then both link dialogs have **Send by email** under the link. Without email the button is not there: copy the link as before.

| | Invitation | Password-reset link |
|---|---|---|
| **Recipient** | **Send to** starts from the address written in the invitation; you can change it. Empty, the email goes to the invitation's address; if there is none, the dialog asks for an address | No field: it goes to the account's address, and only while the account is active |
| **Language** | **Language of the email**: the instance's **Default Language**, unless you pick another | The account's language |

- 🌐 **The link in the email starts with `LIBREFOLIO_PUBLIC_URL`**, whatever the **Server address** above shows: the dialog says so.
- 📨 **The result** is in the dialog: *Sent to …* with the address and the language of the email, and a reminder that the recipient should check the spam folder too if it does not arrive; or why the email did not go out ([Sending Errors](email_troubleshooting.md#sending-errors)).

Rules and limits: [Links Sent by an Administrator](email_flows.md#admin-links).

---

## 🗑️ Delete an Account {: #delete }

**Where:** the account's row, **Delete** button. For an administrator, **Remove administrator** first; not for the initial administrator [waiting for its setup link](#cancel-setup), which you delete directly. The command line does not delete accounts.

The deletion follows the same rule as deleting one's own account ([Profile](../user/settings/profile.md)):

1. For an active account, the dialog first offers **Deactivate** as an alternative.

    It keeps every broker and transaction and can be undone; the account just no longer signs in.

2. The dialog shows what the deletion would take:

    - **Deleted, with all their transactions and files**: the brokers the account is the only owner of, each with its number of transactions. They are deleted for the users it shared them with too. If there are none: *No broker is deleted*;
    - **Shared brokers that stay (only the access goes)**: the other brokers the account can open, with its role on each;
    - a warning when transactions on other brokers are halves of transfers with the deleted brokers: they stay, without the other half. A received transfer becomes an adjustment at its cost; a transfer sent to one of those brokers an adjustment that takes the assets out of the broker that sent them, without a value: their cost counts as a realized loss on that broker ([Edit or delete a broker](../user/brokers/index.md)).

3. Type the account's username, then click **Delete Permanently**.

    The account, its settings and the brokers listed are removed at once.

!!! danger "Deleting an account cannot be undone"

    Whoever is signed in with that account is signed out at the next request. If the deletion fails for a technical reason, nothing is deleted. If the dialog cannot load what the deletion would take, it does not let you delete: close it and try again.

How the rule works: [Deleting an Account](../developer/architecture/access_control.md#admin-account-deletion), for developers.

---

## 🔗 Related

- 📝 **[Environment Variables](configuration_accounts.md#accounts)** — «Accounts and Sign-ups»: `LIBREFOLIO_MAX_USERS`, `LIBREFOLIO_REGISTRATION` and `LIBREFOLIO_PUBLIC_URL`
- ⚙️ **[Global Settings](settings.md)** — «Who Can Sign Up»: the **Registration** setting
- 🛠️ **[Command-Line Tools](cli_tools.md)** — «Manage Users»: most of these tasks, without a browser
- 👤 **[Profile](../user/settings/profile.md)** — Your own account and how to delete it
- 🧑‍💻 For developers: **[Administrator API](../developer/architecture/access_control.md#admin-user-api)** and **[Settings Components](../developer/frontend/components/features/settings.md#userstab)**
