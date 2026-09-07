# 👤 Profile

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="profile" alt="Profile">
</div>

The **Profile** tab manages your **identity** in LibreFolio — who you are and how you log in. Display choices (language, currency, theme) live in **[Preferences](preferences.md)** instead; instance-wide options live in the **[Admin tab](../../admin/settings.md)**.

## 🔒 Edit Lock

The tab opens **locked**: fields are read-only until you click the ✏️ **pencil button** in the header. This prevents accidental edits. If you lock the tab again while changes are unsaved, a confirmation dialog asks whether to discard them.

While unlocked, every modified field shows its own **save** / **undo** buttons, and the header offers **save all** and **undo all** for bulk actions.

## 🖼️ Avatar

Hover your avatar (while unlocked) and click the 📷 camera overlay to open the image picker: choose an existing image from the [Files library](../files/index.md) or upload a new one. Uploads pass through the **[Image Crop tool](../misc/image-crop.md)** with the *avatar* preset (square crop, circular preview).

The avatar is saved immediately and is used across the app wherever your identity is shown — sidebar, broker sharing, and collaborator lists.

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

After confirmation, your session remains active — you do not need to log in again.

### 🗑️ Delete Account

The **Delete Account** button permanently removes your user and everything it owns. To confirm, you must type your **username** in the dialog. The deletion is immediate: you are logged out and returned to the login page.

!!! warning "Irreversible"

    Deleting your account cannot be undone: your brokers, transactions, and settings are removed with it. If you are the **only administrator** of the instance, deletion is refused — promote another user first.

---

## 🔗 Related

- 🎛️ **[User Preferences](preferences.md)** — Language, base currency, and theme
- ⚙️ **[Settings Overview](index.md)** — General settings summary
- ℹ️ **[About](about.md)** — Version info, plugins, and changelog
- 🛡️ **[Global Settings](../../admin/settings.md)** — Instance-wide options (admin)
