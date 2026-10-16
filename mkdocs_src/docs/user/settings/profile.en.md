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

- **Username** and **Email** are editable (unlocked tab required). Changes apply to your login credentials straight away.
- **Account Created** is a read-only field showing your registration date.

## 🔐 Security

### 🔑 Change Password

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="password-modal" alt="Change Password">
</div>

The **Change Password** button (always available, no unlock needed) opens a modal requiring:

1. Your **current password** (for verification)
2. A **new password** that satisfies all the rules: minimum 8 characters, at least one uppercase letter, one lowercase letter, one number, and one special character — and it must differ from the current one
3. **Confirmation** of the new password

After confirmation, your session remains active — you do not need to log in again. Every other device signed in to your account is signed out.

### 🗑️ Delete Account

The **Delete Account** button permanently removes your account and its settings. Its dialog first shows what your deletion would take with it, then asks you to type your **username**. **Delete Permanently** acts at once: you are logged out and returned to the login page.

Your brokers follow the same rule as [leaving a shared broker](../brokers/sharing.md), and the dialog lists them before you confirm:

- **Deleted, with all their transactions and files**: the brokers you are the **only Owner** of, each with its number of transactions. Their imported report files go too, and they disappear also for the users you shared them with. Without any, the dialog says *No broker is deleted.*;
- **Shared brokers that stay (only the access goes)**: every other broker you can open, with your role on it. It stays for its other users: only your access is removed;
- a warning when transactions on other brokers are halves of transfers with the brokers that go: they stay, without their other half (a received transfer becomes an adjustment at its cost).

If the dialog cannot load that list, it does not let you delete: close it and try again. If the deletion fails for a technical reason, nothing is deleted.

!!! warning "Irreversible"

    Deleting your account cannot be undone. If you are the **only active administrator** of the instance, the deletion is refused: first make another account an administrator, from the [Users](../../admin/users.md) tab.

---

## 🔗 Related

- 🎛️ **[User Preferences](preferences.md)** — Language, base currency, and theme
- ⚙️ **[Settings Overview](index.md)** — General settings summary
- ℹ️ **[About](about.md)** — Version info, plugins, and changelog
- 🛡️ **[Global Settings](../../admin/settings.md)** — Instance-wide options (admin)
