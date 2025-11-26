# Proof of Concept - UI Mockups

This page collects the UI mockups generated for LibreFolio, along with the prompts used to create them.

---

## Logo Designs

### Prompt 1A: The Secure Shield

> Minimalist logo design for 'LibreFolio', a self-hosted financial tracking application. The icon should combine the concept of a secure vault or shield with financial growth. A stylized, solid dark forest green shield shape contains an upward-trending line graph or arrow rendered in a contrasting mint green color. Below the icon, the word 'LibreFolio' is written in a clean, modern, dark forest green sans-serif font. The background is a clean, solid cream off-white. The overall feeling should be trustworthy, professional, private, and open-source. Flat design.

![Logo Concept A1](./logo/Gemini_Generated_Image_logoA1.png)

### Prompt 1B: The Smart Ledger

> Minimalist logo design for 'LibreFolio'. The icon is a stylized open book or financial ledger viewed from above, rendered in solid dark forest green. The 'lines' on the right-hand page of the book are not straight text but instead form an upward-curving financial bar chart or growth graph, rendered in a contrasting mint green color, indicating knowledge leading to growth. Below the icon, the word 'LibreFolio' is written in a clean, modern, dark forest green sans-serif font. The background is a clean, solid cream off-white. Flat design, professional and smart.

![Logo Concept B](./logo/Gemini_Generated_Image_LogoB.png)

### Prompt 1C: The Financial Shield

> Minimalist logo design for 'LibreFolio'. The central icon is a classic, solid shield shape in dark forest green, representing security and privacy. Centered prominently inside the shield is a stylized monogram letter 'L' (for LibreFolio) combined with an upward-pointing arrow, rendered in a contrasting mint green color, symbolizing protected growth. Below the shield icon, the word 'LibreFolio' is written in a clean, modern, dark forest green sans-serif font. The background is a clean, solid cream off-white. Flat design, strong and trustworthy.

![Logo Concept A2](./logo/Gemini_Generated_Image_LogoA2.png)

---

## Main Application Screens

### Dashboard (Desktop)

> Desktop UI mockup for 'LibreFolio' financial dashboard on a wide screen. The overall aesthetic is clean, modern, and minimalist, inspired by SvelteKit Skeleton UI. The background is cream off-white (#FDFBF7). On the left, there is a dark forest green (#1A4D3E) sidebar navigation menu with clean white icons and text labels for Dashboard, Holdings, Transactions, and Settings. The main content area features three large summary cards at the top with rounded corners: 'Total Net Worth €125,450.00' (with a small mint green upward arrow and +2.4%), 'Weighted ROI 8.2%', and 'Available Cash €5,300'. Below the cards, a large, clean line chart showing portfolio growth over the last 6 months with a soft green gradient fill. To the right of the line chart, a donut chart showing asset allocation (e.g., Stocks 50%, ETFs 30%, P2P Loans 20%).

![Dashboard 1](./dashboard/Gemini_Generated_Image_dashboard.png)
![Dashboard 2](./dashboard/Gemini_Generated_Image_dashboard2.png)

### Dashboard (Mobile)

> Mobile phone UI mockup for the 'LibreFolio' financial app. iPhone screen format. The design is a responsive adaptation of the desktop dashboard with a cream background and dark green accents. At the very top, a dark forest green header bar shows the 'LibreFolio' logo and a menu icon. Below the header, a prominent display shows the main KPI: a large '€125,450.00' total balance with a smaller green '+2.4% Today' indicator underneath. Below this, a scrollable list of asset summary cards with rounded corners: 'VWCE ETF' showing a mini sparkline chart and current value, 'Bitcoin (BTC)' with its value, and 'P2P Loan Project Y' with a 'Repaying' status. At the bottom of the screen, a dark forest green navigation bar with white icons for Home, Portfolio, and a central '+' button for adding transactions.

![Mobile Home](./mobile/Gemini_Generated_Image_mobileHome.png)
![Mobile 2](./mobile/Gemini_Generated_Image_mobile2.png)

### Portfolio Page

> Desktop UI mockup for the 'Portafoglio' (Portfolio) page of the LibreFolio app. The page has a cream background and the dark green sidebar on the left. The main content area features a large, detailed, clean data table (datagrid) with rounded corners listing current holdings. Columns include: Asset (with icon, e.g., 'Apple AAPL'), Quantity ('15'), Avg Price ('$140.00'), Current Price ('$175.50'), Total Value ('$2,632.50'), Day Change ('+1.2%' in green), and Total P/L ('+25.3%' in green). Rows show various assets like stocks, ETFs, and crypto with appropriate data, some showing green positive gains, others red negative losses. A search/filter bar is above the table. The aesthetic is clean Material UI.

![Portfolio Detail](./portfolio/Gemini_Generated_Image_portafoglio_detail.png)

### Transactions Page

> Desktop UI mockup for the 'Transazioni' (Transactions) page of the LibreFolio app. Cream background, dark green sidebar. At the top of the main content, a filter bar with inputs for date range, transaction type, and asset search. Below it, a long, clean chronological list or table of financial transactions. Each row has an icon indicating type, date, description, and amount. Examples: A row with a green arrow up icon for 'BUY - VWCE ETF - 10 units @ €95.00 - Total -€950.00'; A row with a coin icon for 'DIVIDEND - Coca Cola - +€32.50'; A row with a red arrow down for 'SELL - Bitcoin - 0.1 BTC - Total +€3,800.00'. The amounts are colored green for inflows and grey/red for outflows.

![Transaction 1](./transactions/Gemini_Generated_Image_transaction1.png)
![Transaction 2](./transactions/Gemini_Generated_Image_transaction2.png)
![Transaction 3](./transactions/Gemini_Generated_Image_transaction3.png)

### Cash Management Page

> Desktop UI mockup for the 'Cassa' (Cash) page of the LibreFolio app. Cream background, dark green sidebar. The top of the main area features two prominent rectangular cards with rounded corners displaying cash balances: one titled 'Euro Balance (Base)' showing '€ 5,300.00' and another titled 'USD Balance' showing '$ 1,250.50'. Below these cards, two large action buttons: a solid dark green one 'Add Funds (Deposit)' and an outlined one 'Withdraw Funds'. Below the buttons, a specific table titled 'Cash Movements Ledger' showing only money transfers, e.g., 'Date: 2023-11-20, Type: DEPOSIT, Amount: +€1,000', 'Date: 2023-11-15, Type: SETTLEMENT (Buy AAPL), Amount: -$450.00'.

![Cash Page](./cash/Gemini_Generated_Image_cassa.png)

### P2P Loan Asset Detail

> UI mockup for a specific asset detail page within the 'LibreFolio' desktop app, focusing on a P2P Loan investment. The page has a cream background. Title at the top says 'P2P Loan - Green Energy Fund #45'. Below the title, a prominent horizontal progress bar component shows the repayment status: 'Repaid: €450 / €1000 (45%)', with the repaid portion filled in solid mint green and the remaining in light grey. Below the progress bar, a clean, modern data table with rounded corners titled 'Amortization Schedule'. The table has columns for 'Date', 'Interest Paid', 'Principal Repaid', and 'Remaining Balance', showing numerical data rows. The aesthetic is clean, tabular data-driven, distinct from a stock price chart view.

![Scheduled Investment 1](./scheduled_investment/Gemini_Generated_Image_ScheduleInvestment1.png)
![Scheduled Investment 2](./scheduled_investment/Gemini_Generated_Image_ScheduleInvestment2.png)

### Reports Page

> Desktop UI mockup for the 'Report' page of the LibreFolio app. Cream background, dark green sidebar. The main content area has navigation tabs at the top: 'Performance', 'Income & Dividends', 'Realized Gains (Tax)'. The 'Performance' tab is active. Below the tabs, a large area chart shows the 'Portfolio Value Growth vs Benchmark (S&P500)' over 5 years, with two lines (one dark green for portfolio, one grey for benchmark). Below that, a section for 'Monthly Income', featuring a bar chart showing dividend payouts received each month for the current year, with bars of varying heights in mint green. A summary box next to it shows 'Total dividends YTD: €450.20'.

![Report Page](./reports/Gemini_Generated_Image_report_page.png)
![Report Performance](./reports/Gemini_Generated_Image_report-performance.png)
![Report Income/Dividends](./reports/Gemini_Generated_Image_report-income-and-dividends.png)
![Report Realized Gains](./reports/Gemini_Generated_Image_report-realized-gains-(tax).png)

### Settings

_(No specific prompts were provided for these, but they appear to be settings screens)_

![Settings 1](./settings/Gemini_Generated_Image_setting1.png)
![Settings 2](./settings/Gemini_Generated_Image_setting2.png)

---

## Modals & Forms

### Add Transaction Modal

> UI design of a modal window overlay for 'Add Transaction' in the LibreFolio web app. The modal appears centered over a slightly blurred background of the dashboard. The modal itself has a clean cream background with rounded corners and a dark green title 'New Transaction'. It contains clean form inputs with distinct labels: a dropdown selector for 'Transaction Type' showing 'BUY', a search input field for 'Asset' showing 'Apple (AAPL)', numerical input fields for 'Price' and 'Quantity', and a date picker field. Below the inputs, a toggle switch option for 'Deduct from Cash balance'. At the bottom right of the modal, two buttons: an outlined dark green button for 'Cancel' and a solid dark forest green button for 'Save Transaction'.

*(This prompt likely corresponds to the transaction images under "Main Application Screens")*

### Add New Asset Modal (with Provider Search)

> Desktop UI mockup of a modal window for 'Aggiungi Nuovo Asset' in the LibreFolio app, on a cream background. The title is 'Aggiungi Nuovo Asset' in dark forest green. The form is designed for smart searching. Field 1 (Search & Provider Select): A horizontal group. On the left, a search input field with a magnifying glass icon and placeholder 'Cerca per Simbolo o Nome (es. AAPL)'. On the right, a multi-select dropdown button labeled 'Provider Ricerca: 2 selezionati'. When clicked, it shows a list with checkboxes: '[x] yfinance (Yahoo Finance)', '[x] Alpha Vantage', '[ ] Altro Provider'. Field 2 (Auto-filled): Label 'Simbolo (Ticker)', input type text, value 'AAPL', state is read-only (greyed out, auto-filled after search). Field 3 (Auto-filled): Label 'Nome Asset', input type text, value 'Apple Inc.', state is editable. Field 4 (Auto-filled): Label 'Tipo di Asset', input type dropdown selector showing value 'Stock'. At the bottom right, two buttons: a dark green outlined 'Annulla' and a solid dark forest green 'Salva Asset'. A small help text below the search field says: "I dati verranno precompilati dai provider selezionati.".

![Add Asset Plugin 1](./modals/Gemini_Generated_Image_plugin1.png)
![Add Asset Plugin 2](./modals/Gemini_Generated_Image_plugin2.png)
![Add Asset Plugin 3](./modals/Gemini_Generated_Image_plugin3.png)

### Edit Asset Modal

> Desktop UI mockup of a modal window for 'Modifica Asset' in the LibreFolio app, on a cream background. The title is 'Modifica Asset: Vanguard World'. Top Section (Core Data): Field 1: Label 'Simbolo (Ticker)', input type text, value 'VWCE', state is disabled/read-only (greyed out text). Field 2: Label 'Nome Asset', input type text, value 'Vanguard FTSE All-World UCITS ETF'. Field 3: Label 'Tipo di Asset', input type dropdown selector showing current value 'ETF'. Middle Section (Additional Details - separated by a subtle divider line): Subheader: 'Dettagli Aggiuntivi (Note)' in dark green. Field 4: Label 'Valuta Base dell'Asset', input type dropdown selector showing value 'EUR' (allows choosing the currency the asset is traded in). Field 5: Label 'Allocazione Geografica / Note', input type text field showing value 'Globale / Paesi Sviluppati' (free text for context). At the bottom right, two buttons: a dark green outlined button 'Annulla' and a solid dark forest green button 'Salva Modifiche'. The style is consistent with the LibreFolio design.

*(No specific image seems to match this prompt directly, but it's related to asset management modals.)*
