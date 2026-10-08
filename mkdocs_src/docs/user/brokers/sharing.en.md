# 🤝 Broker Sharing

Share a broker with the people who need it — a partner, a family member, an advisor or an accountant. Each person gets a **role**, which decides what they can do, and each Owner an **ownership share**, which decides how much of the account counts as theirs.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Broker Sharing Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## ➕ Share a broker

Open the sharing panel with the share button on the broker's card, or with **Share Broker** in the broker's toolbar (it opens the **Info** tab). Only an Owner can change it; everyone else sees it read-only.

1. Click **+** (**Add User**) and find the person **by username**.
2. Choose the **Role** and, for an Owner, the **Ownership %**. Then click **Add User**.
3. Click **Save Configuration**. Nothing changes before you do: until then, **↺ Reset** puts the list back as it was.

??? note "✏️ Change or remove someone — and when a save is refused"

    Click a person's chip to change their **Role** or **Ownership %**, or to **Remove Access**; click **Confirm**, then **Save Configuration**.

    A save is refused if it would leave the broker **without an Owner** — so the last Owner can be neither removed nor demoted — or if the shares add up to **more than 100%** (the panel warns *Total ownership exceeds 100%*).

    Unsaved changes: the dialog opened from the broker list asks before closing, but on the **Info** tab, switching to another tab drops them.

---

## 🛡️ What each role can do

| What you can do | Viewer | Editor | Owner |
|:--|:--:|:--:|:--:|
| See the broker, its transactions, reports and charts | ✅ | ✅ | ✅ |
| Add, edit and import transactions; upload and delete report files | ❌ | ✅ | ✅ |
| Edit the broker's settings | ❌ | ✅ | ✅ |
| Manage who has access | ❌ | ❌ | ✅ |
| Delete the broker | ❌ | ❌ | ✅ |

- 👁️ **Viewer** — read-only, for an accountant or relatives who only need to look.
- ✏️ **Editor** — does the day-to-day work, but cannot share or delete the broker.
- 👑 **Owner** — full control; a broker can have several Owners.

---

## 📊 Ownership share

Each Owner has a **share** from 0% to 100%: the part of the account that is theirs. Viewers and Editors always have 0%. The shares can add up to less than 100% — for example when a co-owner does not use LibreFolio — but never more; the panel shows the **Allocated** and **Available** totals as you edit.

The share decides what counts in your figures:

- The **Dashboard** counts only the brokers you **own** with a share above 0%, and scales their amounts by your share: with 50%, you see half of the broker's value, income and P&L.
- The Dashboard's **Risk** tab covers the same brokers: the ones you own with a share above 0% (see [Risk Tab](../dashboard/index.md#risk-tab)).
- Brokers where you are a Viewer or an Editor, or that you own with 0%, are not on your Dashboard. Their own page shows them: Viewers and Editors see the **full** amounts, Owners their share.

---

## 💡 Common setups

| Who | Setup | What they see |
|:--|:--|:--|
| Spouse or partner | Two Owners, 50% each | Each of you sees half of the account on your own Dashboard |
| Co-owner without a LibreFolio account | You as Owner, 50% | Your half; the other 50% stays unallocated |
| Financial advisor or accountant | Viewer | The whole broker on its page, nothing on their Dashboard |
| Family member who records operations | Editor | Adds and imports transactions, but cannot share or delete the broker |

---

## 🚪 Leave a broker or step down

You never need an Owner to leave. Under **Your access** in the sharing panel, after a confirmation:

- **Leave broker** removes your access at once, and the broker disappears from your lists;
- **Switch to viewer** (Editors only) gives up editing; an Owner can make you an Editor again.

!!! danger "Last Owner: leaving deletes the broker"

    If you are the **only Owner** left, the button becomes **Leave and delete broker**: leaving *permanently deletes the broker together with all its transactions and imported report files*. This cannot be undone. To keep the broker, make another user an Owner first, then leave.

Deleting your account follows the same rule — see [Profile](../settings/profile.md).

To get access to someone else's broker, ask one of its Owners. The brokers you cannot open are listed under **Other Existing Brokers** on the [Brokers](index.md) page, and their share button shows who has access. Every signed-in user of this LibreFolio can see who has access to any broker, so the people who share an instance can find each other.
