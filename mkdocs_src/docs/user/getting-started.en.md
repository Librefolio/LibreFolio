# 🚀 Getting Started

Welcome to LibreFolio! This guide walks you through registering an account, logging in, and creating your first broker — everything you need to start tracking your portfolio.

---

## 📝 1. Register Your Account

Navigate to the LibreFolio URL (e.g., `http://localhost:8000`) and you'll see the login page. Click **Register** to create a new account.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Registration Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Fill in your details:

- 👤 **Username**: Your display name (unique across the system)
- 📧 **Email**: A valid email address
- 🔑 **Password**: A strong password (the strength indicator helps you)

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registration with Password Strength" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "First User = Admin"

    The very first user to register automatically becomes the **system administrator** (superuser). This user can manage global settings, promote other users, and access all admin features.

---

## 🔐 2. Log In

After registering, you'll be redirected to the login page. Enter your credentials to access your dashboard.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Login Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🏦 3. Create Your First Broker

A **Broker** in LibreFolio represents a brokerage account — the place where your investments live (e.g., Interactive Brokers, Degiro, a bank account, etc.).

!!! note "Why do I need a Broker?"

    All transactions in LibreFolio are tied to a broker. It's the container that groups your trades, imports, and reports. You need at least one broker before you can start tracking anything.

### 📋 Steps

1. Navigate to the **Brokers** page from the sidebar menu
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="list" alt="Broker List" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>
2. Click the **"New Broker"** button
3. Fill in the broker details:
    - 🏷️ **Name**: A descriptive name (e.g., "My Degiro Account")
    - 💰 **Base Currency**: The currency of the account (e.g., EUR, USD)
    - 🖼️ **Icon** *(optional)*: Upload a broker logo or avatar
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Broker List" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>
4. Once created, you can click on a broker to see its details, import reports, and manage transactions.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="detail" alt="Broker Detail" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

---

## 🔮 4. What's Next?

Now that you have an account and a broker, you can:

- 📤 **[Upload broker reports](files/index.md)** — Import CSV/Excel files from your broker for automatic transaction parsing
- 🤝 **[Share your broker](brokers/sharing.md)** — Give access to family members, advisors, or accountants
- 💱 **[Set up FX rates](fx/index.md)** — Configure currency conversion for multi-currency portfolios
- ⚙️ **[Customize settings](../admin/settings.md)** — Adjust language, theme, and system preferences

!!! tip "Portfolio Calculations"

    Brokers are also used for portfolio aggregation calculations. When you share a broker with another user and set a **share percentage**, the system can compute each user's portion of the total portfolio value. This feature is under active development.
