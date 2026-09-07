# 🤝 Broker Sharing

LibreFolio allows you to share access to your brokerage accounts with other users. This is useful for families, financial advisors, or accountants who need visibility into your portfolio.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Broker Sharing Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📋 How to Share

Only an **Owner** of the broker can manage access. You can open the sharing panel in two ways:

- **From the broker list**: click the **Share** icon (:material-share-variant:) on the broker's card — the **Sharing Modal** opens.
- **From the broker detail page**: click the **Share** button in the header — you land on the **Info** tab, which hosts the sharing panel.

Then:

1. **Search** for the user by username
2. **Select a role** (Viewer, Editor, or Owner)
3. **Set the ownership percentage** — only for the *Owner* role (drag the slider or type a value; Viewers and Editors always carry 0%)
4. Click **Save** to apply changes

!!! warning "Only Owners can manage access"

    You must be an **Owner** of the broker to add, remove, or modify other users' access. Non-owners see the same panel in read-only mode.

---

## 🛡️ Access Roles

When you share a broker, you assign a **role** that determines what the other user can do:

| Feature                              | Viewer | Editor | Owner |
|:-------------------------------------|:------:|:------:|:-----:|
| **View Broker Details**              |   ✅    |   ✅    |   ✅   |
| **View Transactions**                |   ✅    |   ✅    |   ✅   |
| **View Reports & Charts**           |   ✅    |   ✅    |   ✅   |
| **Add/Edit Transactions**            |   ❌    |   ✅    |   ✅   |
| **Import Files (BRIM)**              |   ❌    |   ✅    |   ✅   |
| **Edit Broker Settings**             |   ❌    |   ✅    |   ✅   |
| **Manage Access (Add/Remove Users)** |   ❌    |   ❌    |   ✅   |
| **Delete Broker**                    |   ❌    |   ❌    |   ✅   |

- 👁️ **Viewer**: Read-only access. Ideal for accountants or family members who just need to see data.
- ✏️ **Editor**: Can manage day-to-day operations (transactions, imports) but cannot delete the broker or change access.
- 👑 **Owner**: Full control. Can do everything, including adding/removing other users. A broker can have **more than one Owner** — see the share percentage below.

---

## 📊 Share Percentage

Each **Owner** of a broker has a **share percentage** (0% to 100%). This represents how much of the broker's portfolio value belongs to that owner. Viewers and Editors always carry 0% — the schema rejects any non-zero share for them.

!!! example "Joint Account"

    You and your spouse co-own a brokerage account 50/50. Both of you are Owners:

    - You (Owner): **50%**
    - Spouse (Owner): **50%**

    Each of you sees 50% of this broker's value counted in your own dashboard.

!!! example "Financial Advisor"

    Your financial advisor needs to see your portfolio but doesn't own any of it:

    - You (Owner): **100%**
    - Advisor (Viewer): **0%**

The sum of all share percentages for a broker **must not exceed 100%**, but it can be less (e.g., a co-owned account where the co-owner is not in the system). The panel shows the **Allocated** and **Available** totals while you edit.

!!! note "Portfolio Aggregation"

    The share percentage is **already applied** to your portfolio aggregation: the Dashboard and portfolio-level statistics scale every amount of a shared broker by your ownership share. An Owner with 50% sees half of that broker's value, income, and P&L counted in their totals. Viewers and Editors, whose share is always 0% by rule, see the broker's **full** amounts instead — the share only scales what you *own*.

---

## 🚪 Leaving a Shared Broker (Self-Service)

You never need an Owner's intervention to get out of a broker you have access to. In the sharing panel, the **Your access** section lets you:

- **Leave broker** — removes your own access immediately. The broker disappears from your lists.
- **Switch to viewer** — an Editor can demote themselves to Viewer; an Owner can promote them again later.

!!! danger "Last Owner: leaving deletes the broker"

    If you are the **only Owner** left, the leave action becomes **Leave and delete broker**: leaving *permanently deletes the broker together with all its transactions and imported report files*. This cannot be undone. If that is not what you want, assign another user as Owner first, then leave.

---

## 💡 Common Scenarios

| Scenario | Suggested Setup |
|----------|----------------|
| **Spouse / Partner** | Two Owners, 50% share each |
| **Financial Advisor** | Viewer, 0% share |
| **Accountant** | Viewer, 0% share |
| **Family member** | Viewer or Editor, 0% share |
