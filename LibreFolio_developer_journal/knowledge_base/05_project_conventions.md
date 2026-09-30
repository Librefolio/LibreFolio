# LibreFolio — Project Conventions

## Regole Generali

- **Progetto embrionale** — esiste solo su questa macchina, niente backward compatibility
- **Codice in inglese** — commenti, docstrings, nomi variabili, README
- **UI multilingue** — solo interfaccia grafica in EN/IT/FR/ES
- **Edit > Rewrite** — preferire modifiche puntuali per evitare perdite di funzionalità
- **No migrazioni Alembic incrementali** — modificare `001_initial.py` e ricreare DB con `./dev.py db create-clean`
- **Obiettivo** — codebase pulito e mantenibile per condivisione futura

---

## ⚠️ Async I/O Rule (Event Loop Safety)

In `async def` handlers/methods, **ogni libreria sync che fa I/O** (rete, filesystem pesante) **DEVE** essere wrappata in `await asyncio.to_thread(...)`.

**Mai chiamare direttamente**:
- `requests.get()`, `urllib.urlopen()`, `httplib` (usare `httpx.AsyncClient` o `to_thread`)
- `yf.Ticker().info`, `yf.Search()`, `ticker.history()` (yfinance usa `requests` internamente)
- Operazioni filesystem lente (directory walk, file grandi) — `Path.exists()` veloce è ok

**Perché**: uvicorn usa un singolo event loop. Una chiamata sync blocca l'intero loop per tutta la sua durata, stallando TUTTE le risposte concorrenti (incluso StaticFiles per JS chunks).

**Pattern corretto** (vedi JustETF provider):
```python
# ❌ SBAGLIATO — blocca l'event loop per 1-5 secondi
async def get_current_value(self, ...):
    ticker = yf.Ticker(identifier)
    info = ticker.info  # sync HTTP!

# ✅ CORRETTO — offload al thread pool
async def get_current_value(self, ...):
    info = await asyncio.to_thread(lambda: yf.Ticker(identifier).info)
```

**Regola complementare**: se un endpoint fa solo sync I/O leggero (es. `Path.exists()`, `FileResponse`), definirlo come `def` (non `async def`). FastAPI lo esegue nel thread pool automaticamente, senza bloccare il loop. Esempio: `frontend_catchall()`, `mkdocs_static()` in `main.py`.

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

Le emoji bandiera (`🇮🇹`, `🇫🇷`, `🇪🇸`, `🇬🇧`) su Windows escono come due lettere («EU»): Segoe UI Emoji non ha bandiere. Soluzione (dal 29/09/2026): **una sola faccia globale che disegna solo le bandiere**, `'LF Flags'`, in `frontend/static/lf-flags.css`, linkata da `app.html` e `offline.html` (estratto):

```css
@font-face {
    font-family: 'LF Flags';
    src: local('Apple Color Emoji'), local('AppleColorEmoji'), local('Noto Color Emoji'), local('NotoColorEmoji'),
        url('/fonts/noto-color-emoji/noto-color-emoji.0.woff2') format('woff2');
    unicode-range: U+1F1E6-1F1FF; /* solo gli indicatori regionali */
}

html {
    font-family: 'LF Flags', Inter, system-ui, sans-serif;
}
```

- `'LF Flags'` sta in testa a ogni pila: `html`, `@theme --font-sans` e `--font-mono` in `app.css`, le pile di `offline.html`. Per il suo `unicode-range` disegna solo le bandiere: cifre, `#`, `*` e ogni altra emoji restano ai font che vengono dopo (Inter, il monospace, le emoji di sistema).
- Sui dispositivi Apple le bandiere di Apple (`local()`); altrove il sottoinsieme Noto delle bandiere (~700 KB), scaricato solo se sulla pagina c'è una bandiera. `scripts/update_js_cache.py` tiene solo quel sottoinsieme, come file 0.
- **Mai un font emoji in una `font-family`**: i font emoji disegnano anche cifre, `#` e `*`. Un componente con una pila sua che può mostrare una bandiera la comincia con `'LF Flags'`, oppure avvolge la bandiera in `.emoji-flag` (`'LF Flags', Inter, system-ui, sans-serif`). Gate: `frontend/src/flagFont.gate.test.ts`.
- Il testo di ECharts (canvas e tooltip) non passa dalle pile globali: lì le bandiere non sono ancora coperte. Dettagli nella devWiki, `problems/flag-emoji-windows.md`.

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

