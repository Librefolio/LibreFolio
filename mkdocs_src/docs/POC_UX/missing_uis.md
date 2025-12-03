# Prompts for Missing UI Mockups

This file contains prompts for generating UI mockups for features that are not yet visually represented in the POC.

---

### 1. Import Data Wizard (CSV Mapping)

**Objective**: To guide the user through mapping columns from their CSV file to the application's data fields.

```markdown
(Using tool: generate_image) Prompt: Desktop UI mockup for 'Import CSV' wizard in LibreFolio. Step 2 of 3. Main area shows a preview of the uploaded CSV file (first 5 rows) in a table. Above each column header, there is a dropdown selector to map it to a system field (e.g., mapping "Trade Date" to "Date", "Amt" to "Amount"). A sidebar shows the mapping status '3/5 columns mapped' and instructions. Buttons at bottom right: outlined 'Back', solid dark green 'Next'. Clean, functional interface.
```

---

### 2. Empty State Dashboard (Onboarding)

**Objective**: To show what a new user sees before they have added any data, encouraging them to get started.

```markdown
(Using tool: generate_image) Prompt: Desktop UI mockup for the Dashboard of LibreFolio for a new user. Instead of charts and numbers, the main area features a friendly, flat-style illustration (in dark green/cream) of an empty vault or a planting pot. A large central button says 'Add Your First Asset'. To the right, a 'Getting Started' checklist card: '1. Set Base Currency (Done)', '2. Add Broker (Pending)', '3. Import Data or Add Asset'. The tone is friendly and encouraging.
```

---

### 3. 404 Error Page

**Objective**: A branded error page for broken links.

```markdown
(Using tool: generate_image) Prompt: A creative 404 error page for LibreFolio. Cream background. A stylized illustration of a broken piggy bank or a lost coin in the dark forest green style. Large text: '404 - Asset Not Found'. Subtext: 'The page you are looking for seems to have been liquidated.' A solid dark green button: 'Return to Dashboard'.
```

---

### 4. Mobile Navigation Drawer

**Objective**: To show the full navigation menu on mobile devices.

```markdown
(Using tool: generate_image) Prompt: Mobile UI mockup showing the side navigation drawer open. The background of the drawer is solid dark forest green. List items are white with clean icons: 'Dashboard', 'Portfolio', 'Transactions', 'Reports', 'Settings'. At the bottom of the drawer, a user profile summary with a small avatar and 'Logout' icon. The rest of the screen (overlay) is dimmed.
```

### 5. Loading State (Skeleton UI)

**Objective**: To visualize the loading experience, ensuring it feels fast and modern.

```markdown
(Using tool: generate_image) Prompt: UI mockup showing a 'Loading' state for the LibreFolio Dashboard. The layout matches the standard dashboard (three top cards, main chart, side list), but all text and charts are replaced by shimmering light grey/cream 'skeleton' bars. No spinners, just a pulse effect on the shapes. Background is cream.
```