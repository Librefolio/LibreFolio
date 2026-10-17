# 🚀 Getting Started

Welcome to LibreFolio! In a few steps you create your account, take a quick tour and import your
first broker statement — and your dashboard fills up by itself.

---

## 📝 1. Register Your Account

Open your LibreFolio address (for example `http://localhost:6040`): the login page appears. Click
**Register here** to create an account.

If the login page shows no **Register here**, your administrator lets people in only with an
invitation link, or has closed sign-ups: ask them for an invitation, or for an account. With an
invitation, follow [If You Received an Invitation Link](#invitation-link).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Registration Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Fill in your details:

- 👤 **Username** — unique: you log in with it.
- 📧 **Email** — a valid address; it works for logging in too.
- 🔑 **Password** and **Confirm Password** — the strength indicator tells you when the password is
  strong enough.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registration with Password Strength" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "First User = Admin"

    The very first account to register becomes the **administrator**: it manages the instance-wide
    **[Global Settings](../admin/settings.md)** and every admin feature. On an instance whose
    administrator was created from the server's configuration, by a hosting provider for example,
    nobody registers first: that administrator receives a setup link, which opens the instance's
    setup page. There they type the password twice, following the rules shown under the field;
    once they confirm, they are signed in, and the [Welcome setup](#welcome-setup) opens, as for any
    new account.

### ✉️ If You Received an Invitation Link {: #invitation-link }

An administrator can invite you with a link of your own, by message or by email: the email is
*You are invited to LibreFolio*, and its **Create your account** button opens the link.

1. Open the link. LibreFolio checks it, then shows the registration form with a note that you have
   been invited; a second note tells you when the invitation makes you an administrator.
2. If the administrator wrote your email address on the invitation, it is already filled in: you
   can change it.
3. Choose your username and password, then click **Register**.
4. You are back on the login page, with a confirmation: log in with your new account.

- ⏱️ An invitation link works once, for 7 days. If the page says the link has expired, has already
  been used, has been withdrawn or is not valid, ask your administrator for a new one.
- 📬 If the instance asks you to confirm your email address, open the link it emails you before you
  log in: see [If LibreFolio Asks You to Confirm Your Email](#verify-email).
- 🔒 As soon as the page opens, the address bar loses the secret part of the link: keep the message
  you received in case you need to open the link again. If the page says the link is incomplete,
  open it again from that message.
- 🚪 If the page says that registration is disabled, the administrator has closed sign-ups for now:
  ask them.

### 📬 If LibreFolio Asks You to Confirm Your Email {: #verify-email }

Some instances ask every new account to confirm its email address before the first sign-in. Then,
after **Register**:

1. The login page says: *Account created. We sent you an email with a link to activate it: open it
   within 24 hours, then sign in.* You cannot sign in yet.
2. Open the email *Confirm your email address* and click **Confirm my email address**. If the
   button does not work, copy into your browser the address written under it.
3. LibreFolio confirms your address and brings you back to the login page, with a confirmation:
   log in with your username and password.

- ⏱️ The link works once, for 24 hours.
- 📭 No email? Look in the spam folder. Then, on the login page, sign in with your username and
  password: LibreFolio says that your address is not verified yet, and offers **Send the link
  again**. A new link replaces the older ones. If you ask too often, or after too many wrong
  passwords, the page tells you in how many minutes you can ask again.
- ⌛ If the page says that the link has expired, sign in the same way: you are offered a new link.
  If the instance has no free place left meanwhile, ask your administrator.
- ✅ If the page says that the link has already been used, your account is probably active already:
  sign in.
- 🔒 As with an invitation, the address bar loses the secret part of the link as soon as the page
  opens: keep the email until your account is active.

---

## 🔐 2. Log In

After registering, you are back on the login page. Log in with your username (or email) and your
password. If LibreFolio asked you to confirm your email address, open the link it emailed you
first: see [If LibreFolio Asks You to Confirm Your Email](#verify-email).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Login Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! note "Too many login attempts"

    After 10 wrong passwords in 15 minutes for the same username or email address, or 50 from the
    same IP address, the login page says *Too many login attempts: wait a few minutes and try
    again.* Until the wait is over, even the right password is refused: wait up to 15 minutes, then
    log in. Your administrator can also let you in at once, by restarting LibreFolio.

### 📧 If You Forgot Your Password {: #forgot-password }

On the login page, click **Forgot Password?**. When your instance can send emails, the page has a
form at the top:

1. Type your username or your email address, then click **Email me a reset link**.
2. The page answers the same way whether an account matches or not: look in your inbox, and in the
   spam folder.
3. Open the email *Reset your LibreFolio password* and click **Choose a new password**. The page
   that opens is the one of a link sent by an administrator: follow
   [If an Administrator Sent You a Password-Reset Link](#password-reset-link) from step 2.

- ⏱️ The link works once, for 30 minutes.
- 📭 No email after a few minutes? The account may be deactivated or registered with another
  address, or the requests came too close together: try again later, or ask your administrator.
- 💻 Under the form, a closed panel holds the command your administrator runs on the server to reset
  a password; when your instance cannot send emails, the page shows it open. Either way: ask them.

### 🔑 If an Administrator Sent You a Password-Reset Link {: #password-reset-link }

Your administrator can also send you a link to choose a new password yourself, by message or by
email.

1. Open the link: the page shows the account it belongs to.
2. Type the new password twice: it must meet the rules shown under the field.
3. Click **Set the new password**. You are back on the login page, with a confirmation: log in with
   the new password.

- ⏱️ The link works once, for 30 minutes. If the page says it has expired, has already been used or
  has been withdrawn, ask for a new one: each new link withdraws the ones sent before it.
- 🚪 Setting the new password signs your account out on every device: log in again with the new
  password on each of them.

---

## 🎉 3. Welcome Setup & Quick Tour {: #welcome-setup }

The first time you log in, LibreFolio opens a **Welcome** page before the dashboard:

- 🌍 Check **Language** and **Default Currency**: they start from your administrator's defaults.
- 🖼️ Add a **profile picture** if you like — otherwise your initials are shown.
- ✅ Click **Continue** to save, or **Skip setup permanently** to keep the current settings.
- 🚪 Need to leave? **Log out** is at the top right.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="welcome-setup" alt="The first-run Welcome page: the profile picture block with the initials avatar and Choose picture, Language and Default Currency pre-filled, the note that your theme preference is kept unchanged, and Skip setup permanently and Continue" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

A short welcome animation follows, then the **Quick tour** starts by itself — click **Start tour**
to begin right away, or **✕** to skip it. The tour shows where things are: the menu button, then
**Dashboard**, **Transactions**, **Brokers**, **FX**, **Assets**, **Tools** and **Settings**. It
only points: it never opens a form or creates data.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="core-tour-step" alt="The Quick tour on the Dashboard at step 5 of 8, FX rates: a frame and a cursor on the FX Rates entry of the sidebar, and the message panel with Back and Next" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

??? note "👋 Already using LibreFolio? — accounts older than the guides"

    If your account existed before the guides were added, LibreFolio does not send you through them:
    the Welcome setup counts as **Completed**, the tour and every guide as **Skipped**. You can still
    replay any of them from
    **[Settings → Preferences → Onboarding and guides](settings/preferences.md#onboarding-and-guides)**.

??? warning "⚠️ Setup does not load — what to do"

    If your settings or your guide progress cannot be loaded, a **We couldn't load onboarding** page
    offers **Retry** and **Log out**. If your Welcome setup is already done, you may see the
    Dashboard instead, with a **Retry** banner on top.

### 🧭 Contextual guides

Later, short guides start the first time you reach a place where they help:

| Area | Contextual guides |
|---|---|
| **Transactions** | Page overview, Add Transaction form, bulk workspace, and Import Wizard |
| **Brokers** | Brokers page, Add Broker form, and broker details |
| **FX** | FX page, Add Pair form, and pair details |
| **Assets** | Assets page, Add Asset form, and asset details |

- They point at real controls and never click, upload, edit or save for you.
- A pulsing frame marks the area a step talks about; a small cursor marks a button you can try.
  Clicking it does its normal job and moves the guide on.
- The message panel fades a little after a moment, so you can see the page behind it; hover it to
  bring it back.
- Leave a page mid-guide and its guide picks up at the same step when you come back; closing a form
  restarts that form's guide.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="contextual-guide" alt="The FX page guide at step 2 of 4, on filtering dates, currencies and views: a frame around the currency filters, and the message panel with Back and Next" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

You can replay any guide from
**[Settings → Preferences → Onboarding and guides](settings/preferences.md#onboarding-and-guides)**.

---

## 🏦 4. Import Your First Statement (Create Broker & Assets On-the-Fly)

Your dashboard is still empty — whether you land there directly or after the welcome screens above.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Empty Dashboard" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The fastest way to fill it is to import your transaction history. You don't need to set up brokers
or assets first: the Import Wizard creates them as it goes.

### 📋 Steps

1. **Open the Import Wizard**: on the **[Transactions](transactions/index.md)** page, click **Import** (:material-file-upload:). A broker's detail page has the same button, with that broker already selected.

2. **Upload Your Statement**: drop your broker's report (`.csv`, `.xlsx` or `.xls`) into the wizard and assign it to its broker — choose **Create new** if the broker does not exist yet. Every report you upload is kept (you find it in **[Files & Uploads](files/index.md#broker-reports)**): next time, skip this step and tick the report in the next one.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Wizard Upload Step" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. **Select Files & Parse**: tick the reports to import. Each one gets its broker's parser — change it per file if needed, **Generic CSV** for an unknown layout. LibreFolio then reads every row and sums up what it found: transactions, securities, issues and likely duplicates. Some files then need an extra step or two (see the panel below).
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Wizard Parse Step" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

4. **Review & Import**: match each security to your asset library, or create it **on-the-fly** with the details read from the statement. Likely duplicates arrive unticked, and rows dated before the broker's opening date are left out. More in **[Asset Mapping](transactions/import/index.md#asset-mapping)**.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Wizard Review Step: Asset Resolution" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

5. **Save from the Bulk Editor**: **Import N transactions** moves the ticked rows into the bulk editor — nothing is saved yet. Give them a last look, then click **Save All**.

??? note "🧩 Extra steps — only when your files need them"

    The wizard adds a step only when your files call for it; a clean single-file report skips them
    all:

    - **Unify assets** — the same security appears under different names or codes.
    - **Corrections** — some rows could not be fully read.
    - **Duplicates** — the same movement is in two files you import together.
    - **Align with the bank** — after **Review**, for a report set such as Danske Bank, when the
      bank's figures differ from LibreFolio's.

    See **[Steps that appear only when needed](transactions/import/how-to.md#only-when-needed)**.

The first time you open the wizard, a guide walks you through the steps your files need; it never
clicks or saves for you (see **[Guided First Import](transactions/import/how-to.md#guided-first-import)**).
For the full walkthrough see **[How to Import Transactions](transactions/import/how-to.md)**; for the
supported brokers and file formats see **[Import from Broker](transactions/import/index.md)**.

---

## 📈 5. Back to the Dashboard

Go back to the **Dashboard**: your portfolio value, your allocation (by type, sector and geography)
and your performance history are now filled in.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Dashboard Main View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 6. What's Next?

Now that your portfolio is populated, you can:

- 🤝 **[Share your broker](brokers/sharing.md)** — Give access to family members or advisors.
- 💱 **[Set up FX rates](fx/index.md)** — Configure currency conversion for multi-currency portfolios.
- ⚙️ **[Customize your preferences](settings/preferences.md)** — Adjust your language, default currency, and theme. Administrators also manage the system-wide **[Global Settings](../admin/settings.md)**.
- 🧭 **[Replay the welcome setup or guided tours](settings/preferences.md#onboarding-and-guides)** — Revisit the welcome screen, quick tour, or import guide any time from Settings → Preferences.
- 📱 **[Install LibreFolio as an app](pwa.md)** — Put it on your phone's home screen or in its own desktop window.
