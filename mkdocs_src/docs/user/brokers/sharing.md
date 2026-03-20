# 🤝 Broker Sharing

LibreFolio allows you to share access to your brokerage accounts with other users. This is useful for families, financial advisors, or accountants who need visibility into your portfolio.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Broker Sharing Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📋 How to Share

1. Navigate to a broker's detail page
2. Click the **Share** button (:material-share-variant:) in the header
3. The **Sharing Modal** opens
4. **Search** for the user by username
5. **Select a role** (Viewer, Editor, or Owner)
6. **Set the share percentage** (drag slider or type value)
7. Click **Save** to apply changes

!!! warning "Only Owners can manage access"
    You must be an **Owner** of the broker to add, remove, or modify other users' access.

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
- 👑 **Owner**: Full control. Can do everything, including adding/removing other users.

---

## 📊 Share Percentage

Each user with access to a broker has a **share percentage** (0% to 100%). This represents how much of the broker's portfolio value belongs to that user.

!!! example "Joint Account"
    You and your spouse share a brokerage account 50/50:

    - You (Owner): **50%**
    - Spouse (Editor): **50%**

    When computing total portfolio value, the system counts 50% of this broker's value for each of you.

!!! example "Financial Advisor"
    Your financial advisor needs to see your portfolio but doesn't own any of it:

    - You (Owner): **100%**
    - Advisor (Viewer): **0%**

The sum of all share percentages for a broker **must not exceed 100%**, but it can be less (e.g., a co-owned account where the co-owner is not in the system).

---

## 💡 Common Scenarios

| Scenario | Suggested Setup |
|----------|----------------|
| **Spouse / Partner** | Editor or co-Owner, 50% share each |
| **Financial Advisor** | Viewer, 0% share |
| **Accountant** | Viewer, 0% share |
| **Family member** | Viewer or Editor, custom share % |

!!! note "Portfolio Aggregation"
    The share percentage is designed for future portfolio aggregation features. When these are implemented, each user's dashboard will show their proportional share of all brokers they have access to.
