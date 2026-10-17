# 👤 Profile

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="profile" alt="Profile">
</div>

The **Profile** tab manages your **identity** in LibreFolio — who you are and how you log in. Display choices (language, currency, theme) live in **[Preferences](preferences.md)** instead; instance-wide options live in the **[Admin tab](../../admin/settings.md)**.

## 🔒 Edit Lock

The tab opens **locked**: fields are read-only until you click the ✏️ **pencil button** in the header. This prevents accidental edits. If you lock the tab again while changes are unsaved, a confirmation dialog asks whether to discard them.

While unlocked, every modified field shows its own **save** / **undo** buttons, and the header offers **save all** and **undo all** for bulk actions.

## 🖼️ Avatar

Hover your avatar (while unlocked) and click the 📷 camera overlay to open the image picker: choose an existing image from the [Files library](../files/index.md), a shared one or one of your own, or upload a new one. Uploads pass through the **[Image Crop tool](../misc/image-crop.md)** with the *avatar* preset (square crop, circular preview).

The avatar is saved immediately and is used across the app wherever your identity is shown — sidebar, broker sharing, and collaborator lists.

Since the other users see your avatar, its picture is **shared**: an image you upload here is stored shared, and one of your personal images becomes shared when you pick it, with a notice (see [Shared or personal](../files/index.md#visibility)).

!!! note "Also settable from the Welcome page"

    Brand-new accounts can pick the same picture once, during the **[first-login Welcome
    setup](../getting-started.md#welcome-setup)** — it's the
    same picker, just reached from a different screen. Skipping that step leaves your initials
    as the avatar; you can always add or change a picture later from here.

## ✏️ Username, Email, Account Created

- **Username** and **Email** are editable (unlocked tab required). Changes apply to your login credentials straight away. Changing the email also asks for your current password: see [Changing Your Email](#email-change) below.
- **Account Created** is a read-only field showing your registration date.

### 📧 Changing Your Email {: #email-change }

As soon as the email in the field is another address than your current one, a **Current Password** field appears under the email's description, with a reminder: *To change your email, enter your current password. Your other devices will be signed out.* The email's save button, and **save all**, stay disabled until you type it.

- **Wrong password**: the tab says *Current password is incorrect*. Your new email stays in its field and only the password is emptied: type it again, then save.
- **Wrong password, again and again**: wrong passwords here and failed sign-ins with your username count together. After 10 in 15 minutes, the change is refused even with the right password, and so is signing in with your username, for up to 15 minutes.
- **Email refused for another reason**, for example because another account already uses it, even with other capitals: the tab shows the reason, and your current email comes back.
- **Email saved**: you stay signed in on this device. Every other device signed in to your account is signed out, and needs to sign in again. Any password-reset link sent to you before the change stops working, even one still waiting in your old mailbox.
- **A notice to your old address**: when your instance can send emails, LibreFolio writes to the address you had before, to tell you of the change. It shows nothing of the new address, and says what to do if you did not make the change. Nothing goes to the new address.
- **Only the capitals changed**, such as `Anna@example.com` for `anna@example.com`: it is still your address, so the tab asks for no password, you save it straight away, no device is signed out and it stays verified. Only the letters A to Z are matched this way, accented letters are not: `Émile@example.com` and `émile@example.com` are two different addresses.

Changing only your username asks for no password and signs no device out.

!!! info "Why your password"

    Your email address is how your account can be recovered: a password-reset link sent there lets whoever reads it choose a new password. Without this check, someone with a moment inside your open session (a computer left unlocked, a stolen session cookie) could put their own address on your account, and keep the account for good. Without your password, they cannot change the address.

## 🔐 Security

### 🔑 Change Password

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="password-modal" alt="Change Password">
</div>

The **Change Password** button (always available, no unlock needed) opens a modal requiring:

1. Your **current password** (for verification)
2. A **new password** that meets every rule of the checklist under the field: at least 8 characters, an uppercase letter, a lowercase letter, a number and a special character — and it must differ from the current one
3. **Confirmation** of the new password

The checklist follows what you type, and the server applies exactly the same rules. Letters and digits of any alphabet count: `É` is an uppercase letter, `é` a lowercase one. A special character is anything that is neither a letter, a number nor a space, such as `!`, `_` or `€`. If the server still refuses the new password, the modal says *Password does not meet security requirements*, and the checklist shows which rules are missing.

Wrong current passwords and failed sign-ins with your username count together, as for [the email](#email-change): after 10 in 15 minutes, the change is refused even with the right current password, and so is signing in with your username, for up to 15 minutes.

After confirmation, your session remains active — you do not need to log in again. Every other device signed in to your account is signed out. Any password-reset link sent to you before the change stops working.

### 🗑️ Delete Account

The **Delete Account** button permanently removes your account and its settings. Its dialog first shows what your deletion would take with it, then asks you to type your **username**. **Delete Permanently** acts at once: you are logged out and returned to the login page.

Your brokers follow the same rule as [leaving a shared broker](../brokers/sharing.md), and the dialog lists them before you confirm:

- **Deleted, with all their transactions and files**: the brokers you are the **only Owner** of, each with its number of transactions. Their imported report files go too, and they disappear also for the users you shared them with. Without any, the dialog says *No broker is deleted.*;
- **Shared brokers that stay (only the access goes)**: every other broker you can open, with your role on it. It stays for its other users: only your access is removed;
- a warning when transactions on other brokers are halves of transfers with the brokers that go: they stay, without their other half. A received transfer becomes an adjustment at its cost, and a transfer sent to one of those brokers an adjustment that takes the assets out at their average cost on the broker that sent them (see [Edit or delete a broker](../brokers/index.md)).

If the dialog cannot load that list, it does not let you delete: close it and try again. If the deletion fails for a technical reason, nothing is deleted.

!!! warning "Irreversible"

    Deleting your account cannot be undone. If you are the **only active administrator** of the instance, the deletion is refused: first make another account an administrator, from the [Users](../../admin/users.md) tab.

---

## 🔗 Related

- 🎛️ **[User Preferences](preferences.md)** — Language, base currency, and theme
- ⚙️ **[Settings Overview](index.md)** — General settings summary
- ℹ️ **[About](about.md)** — Version info, plugins, and changelog
- 🛡️ **[Global Settings](../../admin/settings.md)** — Instance-wide options (admin)
