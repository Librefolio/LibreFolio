# Prompts for Missing UI Mockups

This file contains prompts for generating UI mockups for features that are not yet visually represented.

---

### 1. Settings Page

**Objective**: To provide a central place for the user to manage their profile, application settings, and data.

```markdown
(Using tool: generate_image) Prompt: Desktop UI mockup for the 'Settings' page of the LibreFolio app. Cream background, dark green sidebar. The main content area is divided into sections with clear headings.
Section 1: 'User Profile' with fields for 'Username' (pre-filled), and buttons for 'Change Password' and 'Logout'.
Section 2: 'Application' with a dropdown for 'Base Currency' (showing 'EUR'), and a toggle switch for 'Theme' with options 'Light' and 'Dark'.
Section 3: 'API Access' with a section to 'Generate New API Key' and a list of existing keys with 'Revoke' buttons.
Section 4: 'Data Management' with buttons for 'Export All Data (CSV)' and 'Import Transactions (CSV)'.
The aesthetic is clean, modern, and consistent with the SvelteKit/Skeleton UI style of LibreFolio.
```

---

### 2. Asset Detail Page (Stock/ETF)

**Objective**: To show a detailed view for a standard, market-priced asset like a stock or ETF, contrasting with the P2P loan view.

```markdown
(Using tool: generate_image) Prompt: UI mockup for a specific asset detail page within the 'LibreFolio' desktop app, focusing on a Stock investment (e.g., Apple, AAPL). The page has a cream background. The title at the top says 'Apple Inc. (AAPL)'.
Below the title, a large, clean line chart shows the stock's price history for the last year, with time-range selectors for '1M', '6M', '1Y', '5Y', 'MAX'.
To the right of the chart, a summary box with key stats: 'Current Price', 'Day Change', 'Market Cap', 'P/E Ratio', 'Dividend Yield'.
Below the chart, a 'Your Holdings' section shows a data table with lots/transactions for this specific asset: 'Purchase Date', 'Quantity', 'Purchase Price', 'Total Cost', 'P/L'. The aesthetic is clean, data-driven, and focused on market data.
```

---

### 3. Broker Management Page

**Objective**: A UI for users to add, view, and edit the brokers/platforms where they hold assets.

```markdown
(Using tool: generate_image) Prompt: Desktop UI mockup for a 'Broker Management' page in the LibreFolio app. Cream background, dark green sidebar. The title is 'My Brokers'. The main content area displays a grid of cards, where each card represents a broker (e.g., 'Interactive Brokers', 'Degiro', 'Coinbase'). Each card shows the broker's logo, name, and a summary line like '3 Assets, 2 Cash Accounts'. A prominent button 'Add New Broker' is visible at the top. Each broker card has a small 'Edit' or '...' menu.
```

---

### 4. Add/Edit Broker Modal

**Objective**: A modal form for adding or editing a broker's details.

```markdown
(Using tool: generate_image) Prompt: UI design of a modal window for 'Add New Broker' in the LibreFolio app, over a blurred background. The modal has a cream background and a dark green title. It contains form inputs for 'Broker Name' (e.g., 'Interactive Brokers'), 'Description' (e.g., 'Main stock trading account'), and 'Website URL' (e.g., 'https://www.interactivebrokers.com'). At the bottom right, an outlined 'Cancel' button and a solid dark green 'Save Broker' button.
```

---

### 5. Currency Management Page

**Objective**: Although currencies are mostly handled automatically, a power-user might want to view or manage them.

```markdown
(Using tool: generate_image) Prompt: Desktop UI mockup for a 'Currency Management' settings page in the LibreFolio app. Cream background, dark green sidebar. The title is 'Currencies'. The page features a clean data table listing all currencies used in the portfolio. Columns are: 'Code' (e.g., 'USD'), 'Name' (e.g., 'United States Dollar'), 'Symbol' (e.g., '$'), and a toggle switch labeled 'Is Base Currency'. A button 'Add Custom Currency' is at the top. The 'EUR' row has its 'Is Base Currency' toggle active and disabled.
```
