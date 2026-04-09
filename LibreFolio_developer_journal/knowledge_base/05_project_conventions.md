# LibreFolio — Project Conventions

## Regole Generali

- **Progetto embrionale** — esiste solo su questa macchina, niente backward compatibility
- **Codice in inglese** — commenti, docstrings, nomi variabili, README
- **UI multilingue** — solo interfaccia grafica in EN/IT/FR/ES
- **Edit > Rewrite** — preferire modifiche puntuali per evitare perdite di funzionalità
- **No migrazioni Alembic incrementali** — modificare `001_initial.py` e ricreare DB con `./dev.py db create-clean`
- **Obiettivo** — codebase pulito e mantenibile per condivisione futura

---

## Test Users

| Username | Password | Ruolo |
|----------|----------|-------|
| `e2e_test_user` | `E2eTestPass123!` | User normale |
| `e2e_test_admin` | `E2eAdminPass123!` | Admin |

---

## Svelte 5 Runes

I componenti nuovi usano **Svelte 5 Runes**:

```svelte
let value = $state(initialValue);
let computed = $derived(expression);
$effect(() => { /* side effect */ });
```

Non usare il vecchio `$: reactive` o `let` + `bind:`.

---

## Tailwind CSS 4

Configurazione via `@theme {}` direttamente in `app.css`:

```css
@theme {
    --color-libre-green: #1a4031;
    --color-libre-beige: #f5f4ef;
}
```

**Non** usare `tailwind.config.ts` per i colori — è deprecato in v4.

---

## Dark Mode

Il dark mode usa variabili CSS in `html.dark` / `[data-md-color-scheme="slate"]`:

- Frontend: `html.dark` con classi Tailwind `dark:*`
- MkDocs: `[data-md-color-scheme="slate"]` in `extra.css`
- Sync bidirezionale: `app-sync.js` sincronizza tema tra app e docs

---

## Emoji Bandiera (Windows Fix)

Le emoji bandiera (`🇮🇹`, `🇫🇷`, `🇪🇸`, `🇬🇧`) non funzionano su Windows (Segoe UI Emoji non le supporta). Soluzione: web font `Noto Color Emoji`:

```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap');

.emoji-flag {
    font-family: 'Noto Color Emoji', 'Apple Color Emoji', 'Segoe UI Emoji', sans-serif;
}
```

Applicare `.emoji-flag` SOLO ai container bandiera (language selector, currency flags) — le altre emoji funzionano con i font di sistema.

---

## Roadmap e Piani

| Cosa | Dove |
|------|------|
| Piani attivi | `LibreFolio_developer_journal/RoadmapV4_UI/plan-*.md` |
| Sub-plan Phase 4 completati | `RoadmapV4_UI/phases/phase-04-subplan/` |
| Sub-plan Phase 5 completati | `RoadmapV4_UI/phases/phase-05-subplan/` |
| Sub-plan Phase 6 | `RoadmapV4_UI/phases/phase-06-subplan/` (Bugfix Step 1-4) |
| Fasi macro | `RoadmapV4_UI/phases/phase-{00..09}.md` |
| Knowledge base consolidation | `plan-asset06_Steps0-4_knowledgeBaseConsolidationAndEmojiFix.prompt.md` |

