# 📬 Email: Links and Messages

This page covers the messages LibreFolio sends once email works: the **links** for invitations and
password resets, **forgotten passwords**, the **limits** on those emails, the **verification** of
new addresses, and the notice of an **address change**.

Email has to work first: the SMTP variables, the **Email** tab and the test email are in
[Email](email.md), and what to check when a message does not go out is in
[Email: When It Does Not Work](email_troubleshooting.md).

---

## 🌐 Emails with a Link {: #public-url }

An invitation or a password-reset link sent by email is built from `LIBREFOLIO_PUBLIC_URL` alone:
that address, then the page that takes the link, such as
`https://librefolio.example.com/reset-password#token=…`. Never from the address your browser
used, nor from anything else in a request.

- **Why.** Anyone can send LibreFolio a request that names another address. If a link were built
  from the request, a stranger could have LibreFolio email one of your users a real link to a site
  of theirs, and catch its secret part when the user opens it.
- **What to set.** The address your users open LibreFolio at, with `http://` or `https://` and a
  host name, such as `https://librefolio.example.com`: no user name or password, no `?` or `#`, no
  spaces. It is the same variable the command line puts in front of the links it prints: see
  [Accounts and Sign-ups](configuration_accounts.md#accounts).
- **Without it**, or with an address that breaks these rules, no email with a link goes out: such
  an email is refused with `EMAIL_LINKS_UNAVAILABLE`, while the test email still works, and
  **Require Email Verification** cannot be turned on ([Email Verification](#verification)). The
  links you copy, from the [command line](cli_tools.md) for one, stay as they are.
- **What the email says**: it names your instance by the host of `LIBREFOLIO_PUBLIC_URL`, and says
  how long the link still works: 7 days for a new invitation, 30 minutes for a reset link, 24 hours
  for a verification link, 72 hours for the setup link of the initial administrator. A link works
  once.
- **The secret part** of the link comes after `#`: browsers never send it to the server, so it
  stays out of server and proxy logs.
- **To check it**: with email **Ready**, Settings › Administration › Email shows a notice when
  `LIBREFOLIO_PUBLIC_URL` is not set or cannot be used, and the start log has a line
  ([What the Log Says](email_troubleshooting.md#logs)). Once it can be used, the tab shows the address and checks, from
  your browser, that this instance answers there: see [The Address in Emailed Links](email.md#links-check).
  From anywhere, `/api/v1/system/instance` shows `"links": true` once email and the address are
  both fine.

---

## 📨 Links Sent by an Administrator {: #admin-links }

An invitation or a password-reset link that an administrator creates can go out by email, instead
of being copied by hand. While email is **Ready** and `LIBREFOLIO_PUBLIC_URL` can be used
([Emails with a Link](#public-url)), the invitation and reset dialogs of
[Users & Invitations](users.md#send-by-email) show **Send by email** under the link:

1. Create the link as usual: **Invite**, or **Password-reset link** on the person's row.
2. For an invitation, check the address in **Send to**: it starts with the one written in the
   invitation, and you can change it. A reset link has no field: it goes to the address of its
   account.
3. For an invitation, choose the **Language of the email**: **The instance's language** writes it
   in the instance's **Default Language** ([Global Settings](settings.md)); pick English,
   Italiano, Français or Español for someone who reads another one. A reset link goes in its
   account's language.
4. Click **Send by email**. The dialog says *Sent to …* with the address and the language the email
   was written in, or why the email did not go out ([Sending Errors](email_troubleshooting.md#sending-errors)).

The rules:

- **The link in the email starts with `LIBREFOLIO_PUBLIC_URL`**, whatever **Server address** the
  dialog shows: only the secret part of the link travels from the dialog. The dialog says so above
  the button.
- **An invitation** goes to the address in **Send to**, or else to the one written in the
  invitation, in the language chosen in **Language of the email**, the instance's **Default
  Language** unless you picked another. It is the email's language only: it does not become the
  language of the account the invitation creates. It names you as the person who invites, and says so when the new account will be an administrator.
- **A password-reset link** goes only to the address of its account, in the account's language,
  and only while the account is active.
- **Only a live link** goes out: one that has expired, was used or was revoked is refused, and a
  new one must be created.
- Each email counts against the hourly limit.

---

## 🗝️ Forgotten Passwords {: #forgot-password }

Someone who forgot their password can ask for a reset link by email, with their username or their
email address, without signing in. On the login page, **Forgot Password?** opens a form for it
while emails with a link can go out: email **Ready** and a usable `LIBREFOLIO_PUBLIC_URL`. Below the
form, a panel closed until clicked keeps the command an administrator can run on the server.
Otherwise the page shows that command, open, under the warning *Email recovery is not available on
this instance. Reset your password from the server terminal, or ask your administrator for a
password-reset link.* In the [managed profile](hosting_providers.md#managed-profile), the page shows
neither the command nor that warning: in their place, *Ask your administrator for a password-reset
link: they can create one for your account.* When the page cannot read the instance's configuration
from the server, it shows only that advice, in either profile. An administrator creates that link in
**Settings › Administration › Users**, even without email
([Password-Reset Links](users.md#reset-links)).

It is safe because changing an account's email address asks for its current password
([Profile](../user/settings/profile.md)): see [Security Notes](email_troubleshooting.md#security).

It works this way:

- **The same answer for everyone**: *If an active account matches, its owner gets an email with a
  link to choose a new password*, whether an account matches or not. The search for the account
  and the email come after the answer, so nobody can use it to find out which accounts exist.
- **The account** is found as the login finds it, by username or email address. Only an active
  account gets the email, at its own address and in its language.
- **The link** works once, for 30 minutes, and replaces the reset links that earlier requests sent
  the account. While a reset link an administrator created is still live, nothing is sent: a
  request never cancels it.
- **When email or `LIBREFOLIO_PUBLIC_URL` is not ready**, the request is refused with a short
  message, the same for everyone.

The limits:

| Limit | Past it |
| --- | --- |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` requests an hour (20 by default) from the same address, a count shared with the registrations and **Send the link again** ([Limits on Activation and Password-Reset Emails](#activation-limits)); an IPv6 address counts by its /64, the block one subscriber usually holds | The request is refused until a place frees in that count, or in the hourly limit of the instance if that one waits longer; the answer says how long. |
| 3 requests an hour for the same username or email address, whether an account matches or not | The request is refused until the oldest of them is an hour old. |
| The hourly limit of the instance, `LIBREFOLIO_SMTP_MAX_PER_HOUR` | The request is refused until an email fits again. |
| 3 emails an hour to the same mailbox, whatever account they are for and however its address is written | Nothing is sent, and the answer stays the same. |
| 1 email every 5 minutes, and 3 an hour, for the same account, the reset links an administrator created included | Nothing is sent, and the answer stays the same. Two requests at the same moment cannot both send. |

The limit per account counts the account's reset links in the database. The others are kept in the
memory of each server process: with several processes, each keeps its own count, and a restart
forgets them. A reset email that did not go out still counts, for the account and for the mailbox.

**One mailbox, however its address is written.** The limit per mailbox counts the aliases of an
address as one mailbox: capitals do not count, nor a `+tag` on any domain (`name+news@example.com`
is `name@example.com`), nor the dots of a Gmail address, where `googlemail.com` is `gmail.com`
(`first.last@googlemail.com` is `firstlast@gmail.com`). The limits of the
[verification emails](#verification-limits) and of the
[notices of an email change](#email-change-notice) count the same way. Each email still goes to the
address exactly as the account has it. A mailbox that takes mail under any name, such as a catch-all
domain or Fastmail's `anything@user.fastmail.com`, counts each name apart: only the hourly limit of
the instance holds those back.

**Behind a reverse proxy**, the address that counts is the visitor's, as LibreFolio reads it (see
[The Visitor's Address](connection_proxy.md#client-address)):

- When `LIBREFOLIO_CLIENT_IP_HEADER` names the header your proxy sets with the visitor's address
  (`Fly-Client-IP` on Fly.io, `X-Real-IP` from Nginx), LibreFolio reads it there. Set it only if
  every request crosses that proxy: a visitor who reaches LibreFolio directly could write the header.
- Otherwise it is the address the server (uvicorn) sees, which takes the visitor's address from the
  proxy's `X-Forwarded-For` header only when the proxy's address is listed in `FORWARDED_ALLOW_IPS`
  (`127.0.0.1` when not set). List your proxy's addresses or networks there, such as
  `172.18.0.0/16`, never `*`: with `*`, uvicorn takes the first address of the header, which the
  visitor can write.
- **A proxy LibreFolio does not trust, on a local address** (a Docker network, your own network or
  your VPN), such as a proxy container in front of the Docker image, the usual setup: these limits
  per address leave the requests through it out, so that the requests of one visitor cannot use up
  the count of **Forgot password?**, **Send the link again** and the registrations for everyone. The limits
  per username or email address, per account and per mailbox, and the hourly limit of the instance,
  still count them. The log warns once per server process, and the security checks report it as a
  warning of `platform.client_address` (see [The Visitor's Address](connection_proxy.md#client-address)).
- **A proxy LibreFolio does not trust, on a public address**, such as a CDN: every visitor shares
  the proxy's address and its count, so the first `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` requests of
  anyone use up the count of those requests through the proxy for everyone, for up to an hour.
  Tell LibreFolio about the proxy.

---

## 🚦 Limits on Activation and Password-Reset Emails {: #activation-limits }

The emails that activate an account and the ones that reset a password are held back by **two
counters**, the same for every way to ask for them. Each counts over the last 60 minutes, in the
memory of each server process.

| Counter | Variable | Default | What it counts |
| --- | --- | --- | --- |
| **Per address** | `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` | 20 an hour | The emails that leave for one client address (an IPv6 address by its /64), in one count: the registrations, every **Send the link again** with the right password, and every **Forgot password?** for an account that exists. Tries are not counted: a wrong password, a request for a name no account has, or one refused by another limit costs it nothing |
| **Per instance** | `LIBREFOLIO_SMTP_MAX_PER_HOUR` | 50 an hour | Every email the instance sends: activations, resets, invitations, notices |

Three more limits stay as they are. They are not counters of activation emails, and they rarely
matter for an account whose email was held, since nothing has reached its mailbox yet:

- the sign-in's limit on **wrong passwords** ([Failed Sign-ins](configuration_accounts.md#login-limit)), which
  **Send the link again** shares with the login page;
- **3 emails an hour to the same mailbox**, so that LibreFolio cannot be used to flood someone
  else's address;
- **1 email every 5 minutes, and 3 an hour, for the same account**, for **Send the link again**.

The per-address counter counts **emails that leave**, not tries. It is looked at first, so a
request is refused at once, before the password is checked, when the count is full; it is spent at
the last moment, when the email is about to go, and not by anything else: wrong passwords have
their own limit, a request for a name no account has costs nothing (and, for **Forgot password?**,
the answer is the same whether an account matches), and a **Send the link again** refused by the
limit per account or per mailbox spends nothing. An email that the SMTP server then refuses stays
counted: it was tried.

When a counter holds a request back, the answer says how many seconds to wait, and that time is
true: it is the **longest** of the waits of the counters that held it back, so the same request
made then goes through, unless others from the same network used the place meanwhile (the answer
then says the new time).

**An example.** An office with one internet address and a limit of 20. Twenty colleagues register
between 9:00 and 9:40, and their twenty emails go. At 9:45 the 21st, Mario, registers: his account
is created, but his email is held, and the page tells him to try again in about 15 minutes, the
time until the 9:00 email leaves the count at 10:00. At 9:46 he signs in and asks for the link
again: the same counter refuses him, for 14 minutes. At 10:00 he asks again with his username and
password, and the link goes.

The counter per address is shared on purpose, with a consequence to know: when a network has used
up its count with registrations, **Forgot password?** from that network waits too, until a place
frees. Raise `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` for a network where many people sign up
together, such as a school or an office, and restart.

---

## ✅ Email Verification {: #verification }

With **Require Email Verification** on, a new account cannot sign in until its owner confirms the
address with a link that LibreFolio emails to the account. The switch is in
**Settings › Administration › Global Settings**, in the **Security** category
([Global Settings](settings.md)), and it is off by default.

- **Who waits**: every account created from the registration page while the switch is on, the
  ones opened with an invitation included. The first account of a new instance, its administrator,
  never waits, nor does the administrator LibreFolio creates from `LIBREFOLIO_ADMIN_EMAIL`, which
  its setup link activates; neither do the accounts created with `user create` on the
  [command line](cli_tools.md), nor the accounts that already exist.
- **Right after the registration**, the login page says: *Account created. We are sending you an
  email with a link to activate it: open it within 24 hours, then sign in. No email after a few
  minutes? Check the spam folder, then sign in with your username and password: you will be
  offered a new link.* When the client address already had the emails of
  `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` registrations (20 by default) in the
  last hour, or the hourly limit of the instance is spent, no email goes, and the page says so
  instead, with how long to wait: *Account created, but the activation email could not leave now.
  Try again in about N minutes: sign in with your username and password, and you will be offered a
  new link.* N is true: it is the time until both counters admit a new email
  ([Limits on Activation and Password-Reset Emails](#activation-limits)). Behind a reverse proxy LibreFolio
  does not trust, on a local address (the usual Docker setup), nothing is counted per address, so
  this second text never shows ([Forgotten Passwords](#forgot-password)). Either way the account
  is created and waits.
- **The email**, *Confirm your email address*, leaves right after that answer, unless a limit holds
  it back ([Limits of the Verification Emails](#verification-limits)), in the instance's
  **Default Language**: a new account has no language of its own yet. Its button,
  **Confirm my email address**, opens a link that starts with `LIBREFOLIO_PUBLIC_URL`
  ([Emails with a Link](#public-url)) and works once, for 24 hours.
- **Until the address is confirmed**, the account cannot sign in. Signing in with the right
  password says that the address is not verified yet, and offers **Send the link again**: a new
  link, which stops the older ones. With a wrong password, the login gives its usual refusal, so
  nobody learns more than from any other attempt.
- **Once the owner confirms**, the account is active, and its owner is back on the login page with a
  confirmation. What the person sees, step by step: *If LibreFolio Asks You to Confirm Your Email*
  in [Getting Started](../user/getting-started.md).
- **Opening the link confirms nothing**: it shows a page of LibreFolio with a button,
  **Confirm my email address**, and only the click on it uses the link up. The reason is the mail
  filters that scan links, such as Microsoft Defender Safe Links: they open the links of a message
  in a browser that runs scripts, and if opening were enough, the filter would activate the account
  in place of its owner. Such an opening spends nothing; the link stays valid for its owner.
  Someone who opens a link without having signed up has only to close the page.
- **While a hosting provider blocks the instance**, the page of the link says so, once its owner
  clicks **Confirm my email address**, and offers no retry: the link is not used up, and works
  again once the instance is unblocked, as long as it has not expired; otherwise signing in offers
  a new one ([Hosting for Others](hosting_instances.md#instance-block)). Signing in still offers
  **Send the link again**, which then says *This instance is blocked by its hosting provider: try
  again once it is unblocked.*, never that the password is wrong, and works once the instance is
  unblocked. Nobody can sign up meanwhile: the registration page says the same.

### 🔀 Turning It On and Off {: #verification-switch }

- **It turns on only while emails with a link can go out**: email **Ready**
  ([Settings › Administration › Email](email.md#email-tab)), a usable `LIBREFOLIO_PUBLIC_URL`
  ([Emails with a Link](#public-url)), and an instance that no hosting provider blocks. Until then,
  while it is off, the switch is greyed
  out, with the hint *Needs an email with a link to go out: set up SMTP and LIBREFOLIO_PUBLIC_URL
  first (Settings › Administration › Email).* Should that change between the moment you open the tab and your save,
  the save is refused — *Email verification needs an email with a link to go out, and none can go
  now: check Settings › Administration › Email.* — and nothing of it is stored.
- **Turning it off always works.** The accounts already waiting keep waiting: their links still
  work, and so does **Send the link again**. To let one in at once, activate it
  ([Waiting Accounts](#verification-waiting)).
- **While it is on, saving the other settings always works**, even when email has stopped working
  since.
- **If email stops working while it is on** — the server or a variable breaks — nobody can sign up
  any more, not even with an invitation, which stays valid: the registration page says *Sign-up is
  not possible right now: this instance cannot send the verification email. Try again later, or ask
  its administrator.*, and no account is created. Only the first account of a new instance is let
  through. **Send the link again** fails the same way.
  Fix email ([When It Does Not Work](email_troubleshooting.md#troubleshooting)), or turn the switch off.

### ⏳ Waiting Accounts {: #verification-waiting }

In **Settings › Administration › Users**, a waiting account shows the badge **Waiting for
verification**, not **Deactivated**, even once its link has expired. Hover over the badge, or open
the row, for the hint: its owner has not opened the link yet, signing in offers a new one, and
**Reactivate** lets the account in at once.

- **It takes a place** of the user limit (`LIBREFOLIO_MAX_USERS`) while its link is live, like an
  open invitation. When the last link sent expires, 24 hours later, the place is free again, and
  **Send the link again** then needs a free place: on a full instance, its owner is told to ask you.
- **To let it in without the email**, click **Reactivate** on its row
  ([Accounts Waiting for Their Email](users.md#waiting)), or run `user activate` on the
  [command line](cli_tools.md): it can sign in at once, and the links already sent stop working.
  While its link is live, this takes no extra place, since its place is already counted:
  **Reactivate** works even on a full instance, and `user activate` prints no limit warning. Once
  the link has expired, reactivating it needs a free place, as for any deactivated account.
- **To turn it away**, delete it ([Delete an Account](users.md#delete)), or deactivate it: with
  `user deactivate` on the command line, or with the administrator API
  (`PATCH /api/v1/users/{id}` with `is_active: false`). Deactivated, it stops waiting: its links stop
  working, its place is free, its row reads **Deactivated** from then on, and signing in tells its
  owner that the account is disabled. The Users tab itself offers no **Deactivate** for an account
  that is not active: there, **Delete** is the way.

### 📏 Limits of the Verification Emails {: #verification-limits }

| Limit | Past it |
| --- | --- |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` emails an hour (20 by default) from the same address, counting the emails that leave: the registrations, **Send the link again** with the right password and **Forgot password?** for an account that exists; an IPv6 address counts by its /64 | The next new accounts are still created and wait, but their emails do not leave: the login page says so right after the registration, with how long to wait, and their owners ask for the link again from the login page once that time has passed. **Send the link again** is refused for the same time. |
| The sign-in's own limit on wrong passwords, shared with the login page: 10 every 15 minutes for the same username or email address, 50 from the same address (see [Failed Sign-ins](configuration_accounts.md#login-limit)) | The request is refused before the password is checked: the page says in how many minutes to try again. The right password clears the failures of what was typed. |
| 1 email every 5 minutes, and 3 an hour, for the same account, the email of the registration included | The request is refused: the page says in how many minutes to try again. |
| 3 emails an hour to the same mailbox, whatever account they are for and however its address is written ([Forgotten Passwords](#forgot-password)): the email of a registration and the links sent again alike, and only the emails that went out | **Send the link again** is refused: the page says in how many minutes to try again. After a registration, the account is created and waits, but no email leaves, and nothing tells its owner: the page gives its usual text, which already says what to do (look in the spam folder, then sign in to be offered a new link). |
| The hourly limit of the instance, `LIBREFOLIO_SMTP_MAX_PER_HOUR` | The request is refused until an email fits again. A registration made while it is spent is held like one past the limit of its address. |
| A free place, once the account's link has expired | The request is refused: its owner is told to ask you. |

**What stays invisible.** After a registration, *We are sending you an email* means that the email
is queued, not that it was delivered: it leaves after the answer, and it can still not go. The
mailbox's limit of 3 verification emails an hour, the hourly limit of the instance, an SMTP
failure, email or `LIBREFOLIO_PUBLIC_URL` that stopped working meanwhile, a restart: none of them
reaches the page. Only the log says it, with `Verification email: not sent` or
`Verification email: the request failed` ([What the Log Says](email_troubleshooting.md#logs)), and a restart before the
email left leaves no line at all. The account waits with its hold, and **Send the link again**
recovers it; that is why the text of the page tells the person what to do when nothing arrives.
The mailbox limit is deliberately not checked before the answer: a registration that answered
differently when the mailbox had just received emails would tell anyone who signs up with someone
else's address whether that mailbox is receiving them.

A link whose email did not go out counts neither for the account nor for the mailbox. If the
account stops waiting in the meantime — its address confirmed, or an administrator activated or
deactivated it — no new link is sent. The limits per address and per mailbox are kept in the memory
of each server process: with several processes, each keeps its own count, and a restart forgets
them. Behind a reverse proxy, the address that counts follows the rules given in
[Forgotten Passwords](#forgot-password).

---

## 🔔 Email Address Changes {: #email-change-notice }

When someone changes the email address of their account, in [Profile](../user/settings/profile.md),
LibreFolio writes to the address the account had **before**:

- **Only to the old address**: the new one gets nothing.
- **Nothing of the new address, and no username**: the email says only that the address changed,
  without any part of the new one, not even its domain, and it opens with a plain «Hello,»
  ([Security Notes](email_troubleshooting.md#security)).
- **No link.** It tells the owner that, if they did not make the change, someone may be using their
  account: change the password at once if they still can, and tell you.
- **In the account's language.** It names your instance by the host of `LIBREFOLIO_PUBLIC_URL`, with
  its port if it has one, or «LibreFolio» when the variable is not set or cannot be used: with no
  link inside, the notice does not need it.
- **After the change**: the email leaves after the answer, and the change never waits for it. With
  email off, nothing is sent, and the log says so in an information line, not a warning. The notice
  counts against the hourly limit like any email.
- **At most 3 an hour for an account, and 3 an hour to the same mailbox**, however its address is
  written ([Forgotten Passwords](#forgot-password)). Past either, the change still goes through and
  the notice is skipped. Without these limits, an account could point its email at any address and
  change it again, to make your instance write there.
- **Not for capitals alone.** Changing only the capitals of the letters A to Z, such as
  `Anna@example.com` for `anna@example.com`, is no change of address, so no notice goes. Accented
  letters count as different: `Émile@example.com` for `émile@example.com` is a change, with its
  notice.

---

## 🔗 Related

- 📄 **[Email](email.md)** — Where the Configuration Lives, The Variables, Examples, …
- 📄 **[Email: When It Does Not Work](email_troubleshooting.md)** — When It Does Not Work, Security Notes
