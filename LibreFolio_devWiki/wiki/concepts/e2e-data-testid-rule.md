---
title: "E2E data-testid Rule"
category: concept
tags: [testing, frontend, playwright, e2e, i18n]
related_features: [F-067, F-008]
---

# Concept: E2E data-testid Rule

## Definition

**ALWAYS use `data-testid` attributes for Playwright selectors. NEVER use CSS classes or text content.**

This is a **hard rule** in LibreFolio E2E tests. All interactive elements and assertion targets must have `data-testid` attributes. This makes tests:
1. **i18n-safe**: text changes across languages don't break tests
2. **Refactor-safe**: CSS class renames don't break tests
3. **Explicit**: intent is clear — this element is meant to be tested

## Pattern

```typescript
// ✅ CORRECT — use data-testid
await expect(page.getByTestId('assets-page')).toBeVisible({timeout: 10_000});
await page.getByTestId('asset-search-input').fill('AAPL');
await page.getByTestId('asset-card-0').click();

// ❌ WRONG — never use CSS classes
await page.locator('.asset-list').click();  // breaks on CSS refactor

// ❌ WRONG — never use text content
await page.getByText('Search').click();  // breaks in IT/FR/ES
await page.getByRole('button', {name: 'Search'}).click();  // breaks on i18n
```

## Why This Approach

1. **i18n robustness**: LibreFolio has 4 languages (EN/IT/FR/ES). Selecting by text (`getByText('Save')`) fails when the page is in Italian (`Salva`). `data-testid` is language-agnostic.
2. **Style independence**: Tailwind classes and component CSS change frequently. Tests must not break when `.btn-primary` becomes `.btn-blue`.
3. **Semantic clarity**: `data-testid="logout-button"` documents that this element is part of the test contract. Developers know not to remove it.
4. **Playwright best practice**: `getByTestId()` is faster than complex CSS selectors or text queries.

## Svelte Implementation

```svelte
<!-- Button example -->
<button data-testid="asset-sync-button" on:click={syncAsset}>
    {$t('assets.sync')}
</button>

<!-- Input example -->
<input
    type="text"
    data-testid="asset-search-input"
    placeholder={$t('common.search')}
    bind:value={searchQuery}
/>

<!-- Conditional element (data-testid stays even if not visible) -->
{#if showModal}
    <div data-testid="asset-detail-modal" class="modal">
        <!-- modal content -->
    </div>
{/if}
```

## Naming Convention

| Element Type | Pattern | Example |
|--------------|---------|---------|
| Page container | `{page-name}-page` | `assets-page`, `fx-detail-page` |
| Button | `{action}-button` | `logout-button`, `sync-button`, `save-button` |
| Input | `{field}-input` | `login-username`, `assets-search-input` |
| Card/Item | `{type}-card-{index}` | `asset-card-0`, `fx-pair-card-1` |
| Modal | `{name}-modal` | `asset-detail-modal`, `confirm-delete-modal` |
| Form | `{name}-form` | `login-form`, `broker-edit-form` |
| Table row | `{type}-row-{id}` | `asset-row-123`, `transaction-row-456` |

## Mobile vs Desktop

Use **same data-testid** for both viewports. Tests detect viewport via Playwright project config:

```typescript
// Desktop and mobile both use same testid
await page.getByTestId('hamburger-menu').click();  // mobile only
await page.getByTestId('sidebar-nav').click();     // desktop only
```

Helper `openMobileMenu()` in `auth-helpers.ts` abstracts mobile-specific navigation.

## Dynamic Lists

For lists of items (assets, FX pairs, transactions), use:

```svelte
{#each assets as asset, i}
    <div data-testid="asset-card-{i}">
        <!-- card content -->
    </div>
{/each}
```

Test pattern:

```typescript
// Access first item
const firstCard = page.getByTestId('asset-card-0');
await expect(firstCard).toBeVisible();

// Access all items via regex
const allCards = page.locator('[data-testid^="asset-card-"]');
const count = await allCards.count();
expect(count).toBeGreaterThan(0);
```

## Exceptions

**Only 2 cases where data-testid is not used:**

1. **Third-party components** (e.g., Flowbite dropdowns, modals) — use Playwright's `getByRole()` with accessible name
2. **Dynamic content where adding testid is impractical** (rare) — use `locator()` with specific context

Example:

```typescript
// Third-party modal (Flowbite)
await page.getByRole('dialog').waitFor({state: 'visible'});

// But prefer wrapping div with data-testid
<div data-testid="custom-modal-wrapper">
    <FlowbiteModal {...props} />
</div>
```

## Enforcement

- **Code review**: PRs rejected if new E2E tests use CSS classes or text selectors
- **Convention documented**: `knowledge_base/07_testing_frontend.md` section "Conventions"
- **Fixtures enforce rule**: `auth-helpers.ts` and domain helpers (e.g., `fx-helpers.ts`) always use `getByTestId()`

## Where It Applies

- All Playwright E2E tests in `frontend/e2e/` (181+ tests)
- Gallery screenshot tests in `frontend/e2e/gallery.spec.ts`
- All custom test helpers in `frontend/e2e/fixtures/`

Does **not** apply to:
- Unit tests (Vitest) — use component selectors directly
- Backend tests (pytest) — no DOM, no selectors

## Source files

| Role | Path |
|------|------|
| E2E tests directory | `frontend/e2e/` |
| Auth helpers | `frontend/e2e/fixtures/auth-helpers.ts` |
| FX helpers | `frontend/e2e/fx/fx-helpers.ts` |
| Asset helpers | `frontend/e2e/assets/assets-helpers.ts` |
| Playwright config | `frontend/playwright.config.ts` |
| Source KB file | `LibreFolio_developer_journal/knowledge_base/07_testing_frontend.md` |
