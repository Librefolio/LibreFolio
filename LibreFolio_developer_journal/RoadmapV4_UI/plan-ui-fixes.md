# Plan: UI Fixes Post Data-Separation

**Created**: 2026-02-06
**Status**: 🔲 TODO
**Priority**: Medium
**Depends on**: Data Separation completed ✅

## Context

Durante i test di verifica della migrazione prod/test data separation, sono stati identificati alcuni bug UI pre-esistenti che necessitano correzione.

---

## 🐛 Bug List

### Bug 1: User Preferences Not Applied on Login

**Location**: Login flow / Language handling
**Severity**: Medium
**Description**: 
- Le preferenze utente (lingua, tema) salvate in `user_settings` non vengono applicate automaticamente al login
- Il pulsante lingua nella dashboard è correttamente temporaneo (session-only)
- Ma al login, la lingua dovrebbe essere letta da `user_settings` e applicata

**Expected Behavior**:
1. User logs in
2. System reads `user_settings.language` from DB
3. System applies that language to the session
4. Dashboard shows correct language

**Current Behavior**:
- Login uses last browser session language
- User must manually go to Settings to see their saved preference

**Fix Approach**:
- In login response, include user settings (language, theme, base_currency)
- Frontend applies these settings to the session/store on successful login

---

### Bug 2: Base Currency Not Used in Broker Creation Modal

**Location**: `BrokerCreateModal.svelte` - Initial Balance field
**Severity**: Low
**Description**:
- When creating a broker, the initial balance currency input doesn't default to user's `base_currency`
- Same issue may exist in transaction deposit/withdrawal forms (POC, not yet implemented)

**Expected Behavior**:
- Currency selector defaults to user's `base_currency` from settings

**Fix Approach**:
- Read `userSettings.base_currency` from store
- Set as default value for currency inputs

---

### Bug 3: BRIM Upload Modal - No Scroll for Many Files

**Location**: `BrimUploadModal.svelte`
**Severity**: Medium
**Description**:
- When uploading many files at once, the modal content overflows
- The "Upload" button in the footer becomes unreachable
- No scrollbar appears to scroll down to the button

**Expected Behavior**:
- Modal content should be scrollable when file list is long
- Footer with action buttons should remain visible

**Fix Approach**:
- Add `max-height` and `overflow-y: auto` to the file list container
- Ensure footer stays fixed at bottom of modal

---

### Bug 4: Files Page - Broker Column Not Auto-Added

**Location**: `FilesPage.svelte` or `BrimFilesTable.svelte`
**Severity**: Low
**Description**:
- If user has only 1 broker, the "Broker" column is correctly hidden
- When user uploads a file to a 2nd broker, the column should auto-appear
- Currently, user must click "Reset" in the filter menu to see the new column

**Expected Behavior**:
- Table should detect when files span multiple brokers and auto-show column
- Or: Always show broker column if user has more than 1 broker

**Fix Approach**:
- Option A: Check `brokers.length > 1` to show column (simpler)
- Option B: Check if displayed files have different `broker_id` values (reactive)

---

## 📋 Implementation Order

1. **Bug 1** - Most impactful for UX
2. **Bug 3** - Blocks user workflow
3. **Bug 4** - Minor annoyance
4. **Bug 2** - Nice to have, transactions not yet implemented

---

## 📝 Notes

- These bugs existed before the data separation migration
- They were discovered during manual testing of the new prod/test structure
- None are blockers for the data separation feature

