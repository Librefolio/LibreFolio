# Plan: Mobile PWA + Optimizations

> **Parent**: RoadmapV4_UI
> **Status**: 🧪 Ready for Testing (2026-05-26)
> **Created**: 2025-07-22

## Problem

Su mobile l'utente accidentalmente fa zoom, trigger gesture di navigazione del browser, e l'esperienza non è app-like. Servono ottimizzazioni CSS + PWA manifest per un'esperienza nativa. Inoltre manca un pulsante "Installa App" e la documentazione utente.

## Approach

4 fasi incrementali: CSS fixes → PWA manifest (con icone generate dalla pipeline build) → Install button nel HelpMenu → Documentazione.

---

## Todos

### 1. `mobile-css-fixes` — Ottimizzazioni CSS/meta per mobile ✅
- [x] `<meta name="viewport" ... maximum-scale=1, user-scalable=no>` in `app.html`
- [x] `overscroll-behavior: contain` su body (disabilita pull-to-refresh + overscroll)
- [x] `overscroll-behavior-x: none` su html (disabilita swipe back su Android)
- [x] `touch-action: manipulation` globale (no double-tap zoom)
- [x] `-webkit-tap-highlight-color: transparent` (no flash blu su tap)
- [x] Verificare `font-size >= 16px` su input (evita auto-zoom iOS)

### 2. `pwa-manifest` — Manifest + icone PWA ✅
- [x] Estendere `generate_favicon()` in `dev.py` per generare anche icone PWA (192×192, 512×512) da `logo_square.png`
  - Aggiungere margine bianco (~12% padding) attorno al logo prima del resize
  - Output in `frontend/static/icons/` (icon-192.png, icon-512.png)
  - Stessa logica PIL già usata per il favicon
- [x] Creare `frontend/static/manifest.json` con display:standalone, theme_color:#1a4031, background_color
- [x] Aggiungere `<link rel="manifest">` in `app.html`
- [x] Aggiungere meta tags Apple in `app.html`: `apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style`, `apple-touch-icon`

### 3. `install-button` — Bottone "Installa App" nel HelpMenu ✅
- [x] Aggiungere voce "Installa App" nel dropdown HelpMenu (icona: `Download`)
- [x] Logica: intercettare `beforeinstallprompt` event → mostra il bottone solo se disponibile
- [x] Fallback iOS: detect user agent → mostra istruzioni ("Condividi → Aggiungi a Home")
- [x] Nascondere il bottone se già in standalone mode (`window.matchMedia('(display-mode: standalone)')`)
- [x] Chiave i18n: `help.installApp` + `help.installAppIos` per EN/IT/FR/ES

### 4. `pwa-docs` — Documentazione in mkdocs ✅
- [x] Nuova pagina: `mkdocs_src/docs/user/pwa.en.md` — guida installazione PWA
  - Come installare su Android/iOS/Desktop
  - Tabelle confronto HTTP/HTTPS, troubleshooting
  - Note su Tailscale per HTTPS su LAN
- [x] Aggiungere entry nel FAQ: "Can I use LibreFolio as a mobile app?" → link alla pagina PWA
- [x] Nav entry in mkdocs.yml con traduzioni IT/FR/ES

---

## Dependencies

```
mobile-css-fixes (indipendente)
pwa-manifest (indipendente)
install-button → pwa-manifest
pwa-docs → install-button
```

## Notes

- `logo_square.png` (944×944 RGBA) → base per icone PWA, con padding bianco aggiunto in fase di generazione
- Service Worker NON implementato (non serve per uso online-only, il progetto è self-hosted)
- Su HTTP LAN: manifest + standalone funzionano. Solo `beforeinstallprompt` (banner auto Chrome) richiede HTTPS
- iOS non mostra mai banner automatico → guida manuale nell'UI
- `display: standalone` nel manifest → su "Add to Home" non mostra barra URL né gesture browser
- `generate_favicon()` in `dev.py` (riga ~1557) è il punto di estensione per le icone PWA
- HelpMenu in `frontend/src/lib/components/layout/HelpMenu.svelte` — target per il bottone Install

---

## Execution Tracking

### Progress

**2026-05-26 17:27** — Implementazione completata ✅

1. **mobile-css-fixes** ✅
   - `app.html`: viewport con no-zoom, viewport-fit=cover
   - `app.css`: overscroll-behavior, touch-action:manipulation, tap-highlight transparent
   - Media query @768px: font-size min 16px su input/select/textarea (previene auto-zoom iOS)

2. **pwa-manifest** ✅
   - `dev.py`: esteso `generate_favicon()` → aggiunta `generate_pwa_icons()` con PIL
   - Icone 192×192 e 512×512 generate da `logo_square.png` con ~12% padding bianco
   - `manifest.json`: display:standalone, theme_color:#1a4031, background_color:#f5f4ef
   - `app.html`: manifest link + meta Apple (apple-mobile-web-app-capable, status-bar-style, touch-icon)
   - Icons salvate in `frontend/static/icons/`

3. **install-button** ✅
   - `HelpMenu.svelte`: rewrite con Svelte 5 runes ($state)
   - Intercetta `beforeinstallprompt` (Chrome/Android) → mostra bottone Install solo se disponibile
   - iOS detection → mostra istruzioni "Tap Share → Add to Home"
   - Standalone detection → nasconde il bottone se già installato
   - i18n: `help.installApp`, `help.installAppIos` in EN/IT/FR/ES
   - Dark mode support

4. **pwa-docs** ✅
   - Creata `mkdocs_src/docs/user/pwa.en.md` (EN only)
     - Guida installazione per Android/iOS/Desktop
     - Tabella confronto HTTP/HTTPS
     - Troubleshooting
   - FAQ aggiornato con Q&A "Can I use as mobile app?" → link a pwa.md
   - mkdocs.yml nav entry + traduzioni titolo (IT/FR/ES)

**Build status**: ✅ No errors, no warnings

### Deviations Log

- PIL era già installato (usato per favicon)
- Le icone generate hanno il padding bianco corretto

**Bugfix 2026-05-27**: HelpMenu non si apriva al click
- **Causa**: `isOpen` era `let` semplice ma il file usava runes mode (contiene `$state`). In Svelte 5 runes mode, `let` senza `$state` non è reattivo → `{#if isOpen}` non reagiva.
- **Fix**: `let isOpen = false` → `let isOpen = $state(false)`
- **Fix2**: `apple-mobile-web-app-capable` deprecato → `mobile-web-app-capable`

**Bugfix 2026-05-27**: Install button non appariva nel menu
- **Causa**: race condition — `beforeinstallprompt` scattava PRIMA che `onMount` registrasse il listener. La condizione `canInstall || isIos` risultava false su desktop.
- **Fix**: 
  1. Bottone "Install App" ora **sempre visibile** (tranne in standalone mode)
  2. Early capture in `app.html`: `window.__pwaInstallPrompt` cattura l'evento prima che Svelte monti
  3. `onMount` legge `window.__pwaInstallPrompt` come fallback
  4. Click handler: se `deferredPrompt` → prompt nativo; se iOS → istruzioni share; altrimenti → hint "cerca ⊕ nella barra indirizzi"
  5. Aggiunta chiave i18n `help.installAppDesktop` (EN/IT/FR/ES)
- **Console messages ignorabili**:
  - `beforeinstallpromptevent.preventDefault()` → comportamento atteso
  - `UNSUPPORTED_OS` → estensione browser, non nostro

**Bugfix 2026-05-27**: Deprecation warnings + theme-color dinamico
- **Fix**: `on:click` → `onclick` (Svelte 5 syntax, 2 occorrenze in HelpMenu.svelte)
- **Enhancement**: theme-color dinamico per la title bar della PWA:
  - Light mode: `#1a4031` (libre-green)
  - Dark mode: `#0f172a` (slate-900, il bg primary dark)
  - Aggiornato in: `themeStore.ts` (`applyTheme`) + `app.html` (anti-FOUC script)
- **Developer docs**: creata `mkdocs_src/docs/developer/frontend/pwa.md` + nav entry

**Test utente 2026-05-27 10:23**: Installazione desktop ✅
- L'install su desktop Chrome funziona: si apre come finestra separata (chromeless)
- Title bar color verde corretto in light mode
- Nota utente: servirebbe leggermente più padding bianco sull'icona → prossimo giro
- Domande emerse:
  - Doppio URL (locale + HTTPS): **non possibile** — PWA è legata all'origine di installazione. Si possono avere 2 installazioni separate (una per URL).
  - Theme-color dinamico dark: **implementato** (vedi sopra)
  - Fallback page offline: **analisi sotto**

### 📋 Analisi: Offline Fallback Page

**Richiesta**: mostrare una pagina "Server non raggiungibile" con estetica LibreFolio quando l'endpoint è offline.

**Fattibilità**: ✅ SÌ, richiede un **Service Worker minimale** (solo per la fallback, no cache generale).

**Come funziona**:
1. Il SW intercetta tutte le request di navigazione (`mode: 'navigate'`)
2. Prova a fare `fetch(request)` normalmente
3. Se fallisce (network error) → serve una pagina HTML statica pre-cached: `/offline.html`
4. La pagina offline ha la stessa estetica di LibreFolio (logo, colori, messaggio)

**Requisiti**:
- `frontend/static/sw.js` — Service Worker (~25 righe, solo fallback)
- `frontend/static/offline.html` — pagina statica con logo + messaggio
- Registrazione SW in `app.html`: `navigator.serviceWorker.register('/sw.js')`
- Il SW NON fa caching generale: l'app resta online-only
- Funziona su HTTP localhost e HTTPS

**Impatto**: minimo. Il SW fa solo fallback, non cache. Aggiornamenti app restano immediati.

**Compatibilità OS**: ✅ Tutti i browser moderni (Chrome, Firefox, Safari, Edge) su tutti gli OS (Windows, macOS, Linux, Android, iOS 11.3+). L'unica eccezione sarebbe IE11 (morto dal 2022).

**Status**: ✅ Implementato (2026-05-27)

### ✅ Implementazione: Offline Fallback (2026-05-27)

**File creati**:
- `frontend/static/sw.js` — Service Worker minimale (~25 righe)
  - `install`: pre-cacha `/offline.html` in cache `offline-v1`
  - `fetch`: intercetta solo `navigate`, serve fallback su network failure
  - `activate`: pulisce vecchie cache, `skipWaiting()` + `clients.claim()`
- `frontend/static/offline.html` — Pagina fallback statica (~130 righe)
  - CSS inline (zero dipendenze esterne)
  - Dark mode via `@media (prefers-color-scheme: dark)`
  - i18n: detecta `navigator.language` → EN/IT/FR/ES
  - Auto-retry: ping server ogni 10s, reload on success
  - Bottone "Riprova" manuale
  - Branding LibreFolio (colori, icona foglia inline SVG)

**File modificati**:
- `frontend/src/app.html` — aggiunta registrazione SW: `navigator.serviceWorker.register('/sw.js')`
- `mkdocs_src/docs/developer/frontend/pwa.md` — sostituita sezione "No Service Worker" con documentazione SW completa

**FAQ utente**:
- **Come si aggiorna il SW?** → Automatico. Il browser controlla `sw.js` ad ogni apertura della PWA (byte-diff). Se diverso, scarica e installa il nuovo SW. Al prossimo avvio, il nuovo SW è attivo.
- **Cosa succede se installo 2 volte?** → Impossibile. Dopo l'install, `beforeinstallprompt` non scatta più. L'OS impedisce duplicati sulla stessa origin.
- **Funziona su iOS?** → Sì. Service Workers supportati da iOS 11.3+ (2018). Cache eviction aggressiva è irrilevante (pre-cachiamo solo 1 file da ~5KB che viene ricachato alla prossima visita).

---

## 🧪 Test Plan

### 📍 Fase 1: Localhost (Mac)

#### Start dev server
```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio

# Terminal 1: Backend
./dev.py backend start

# Terminal 2: Frontend (con HMR)
cd frontend && npm run dev
```

Poi apri: `http://localhost:5173`

#### Test Checklist Localhost

**1. Mobile CSS (simulazione)**
- [ ] Apri DevTools → Toggle device toolbar (Cmd+Shift+M)
- [ ] Seleziona iPhone/Android
- [ ] Verifica: non si dovrebbe fare zoom con double-tap su link/pulsanti
- [ ] Verifica: fai scroll in fondo pagina → non dovrebbe "rimbalzare" (overscroll)
- [ ] Verifica: Input text → font >= 16px (Inspect → Computed)

**2. PWA Manifest**
- [ ] DevTools → Application tab → Manifest
- [ ] Verifica che appaia:
  - name: "LibreFolio"
  - display: "standalone"
  - theme_color: "#1a4031"
  - icons: 192×192 e 512×512

**3. Install Button (Desktop Chrome/Edge)**
- [ ] Vai sul sito
- [ ] Click su **❓ (Help & Support)** in alto a destra
- [ ] Verifica: dovrebbe apparire **"Install App"** nel menu
  - Se NON appare → normale (localhost + Chrome a volte non triggera `beforeinstallprompt`)
  - Alternativa: guarda l'icona ⊕ nella barra indirizzi di Chrome

**4. iOS Simulation (solo look)**
- [ ] DevTools → device iPhone
- [ ] Help menu → Install App
- [ ] Verifica: testo *"Tap Share, then Add to Home Screen"* appare

**5. Dark Mode**
- [ ] Toggle tema (icona sole/luna in alto)
- [ ] Help menu → Install App
- [ ] Verifica: background scuro, testo chiaro, colori corretti

---

### 🐧 Fase 2: Server Linux (Docker)

#### Deploy su server
```bash
# Sul tuo server Linux
cd /path/to/LibreFolio
./dev.py docker build
./dev.py docker start

# Se esposto tramite Tailscale o reverse proxy HTTPS
# → apri https://your-domain.com
```

#### Test Checklist Server

**1. Manifest accessibile**
```bash
# Da terminale o browser
curl https://your-domain.com/manifest.json | jq .

# Dovresti vedere:
# {
#   "name": "LibreFolio",
#   "display": "standalone",
#   ...
# }
```
- [ ] Manifest risponde con JSON valido

**2. Icons accessibili**
```bash
curl -I https://your-domain.com/icons/icon-192.png
# → HTTP 200 OK, Content-Type: image/png

curl -I https://your-domain.com/icons/icon-512.png
# → HTTP 200 OK, Content-Type: image/png
```
- [ ] icon-192.png: HTTP 200, ~22KB
- [ ] icon-512.png: HTTP 200, ~106KB

**3. PWA Install — Android Chrome**
- [ ] Apri `https://your-domain.com` su Android con Chrome
- [ ] Verifica: dopo 2-3 secondi appare **banner in basso**: "Add LibreFolio to Home screen"
  - Oppure: Help menu → **Install App** → tap → banner appare
- [ ] Tap "Install" → l'app appare nella home screen
- [ ] Apri l'app → verifica: **senza barra URL** (fullscreen)

**4. PWA Install — iOS Safari**
- [ ] Apri `https://your-domain.com` su iPhone/iPad con **Safari** (importante!)
- [ ] Help menu → **Install App** → mostra istruzioni
- [ ] Tap Share (quadrato con freccia) → "Add to Home Screen"
- [ ] Verifica: icona con logo LibreFolio appare nella home
- [ ] Apri → verifica: fullscreen (no Safari UI)

**5. PWA Install — Desktop Chrome/Edge**
- [ ] Apri `https://your-domain.com` su Windows/Mac/Linux
- [ ] Help menu → **Install App** (o icona ⊕ nella barra indirizzi)
- [ ] Click Install → verifica: si apre finestra dedicata (senza tab browser)
- [ ] Verifica: l'app appare nel menu Start/Launchpad

**6. Standalone Mode Detection**
- [ ] Dopo aver installato l'app (Android/iOS/Desktop)
- [ ] Apri la PWA installata
- [ ] Help menu → verifica: "Install App" **NON appare** (già installato)

**7. Mobile CSS — Real Device**
- [ ] Usa l'app installata su smartphone
- [ ] Verifica: non zoom accidentale con tap
- [ ] Verifica: no pull-to-refresh (scroll in alto non ricarica)
- [ ] Verifica: no swipe-back gesture che esce dall'app

---

### ⚠️ Troubleshooting

| Problema | Causa | Fix |
|----------|-------|-----|
| Install button non appare (localhost) | `beforeinstallprompt` non triggerato su HTTP localhost | Normale. Testa su server HTTPS o usa icona ⊕ Chrome |
| Install button non appare (server HTTP LAN) | PWA auto-prompt richiede HTTPS | Usa install manuale: menu browser → "Add to Home" |
| iOS: no "Add to Home" in Share menu | Browser non Safari | Usa Safari (unico browser iOS con PWA) |
| Manifest 404 | Build non include static/ | Verifica `frontend/build/manifest.json` esista |
| Icons 404 | Stessa causa | Ricompila: `cd frontend && npm run build` |

---

### 📝 Quick Test Script

```bash
# Test rapido manifest + icons da server
curl -s https://your-domain.com/manifest.json | jq '.name, .display, .theme_color'
# Output atteso:
# "LibreFolio"
# "standalone"
# "#1a4031"

# Test icons
for size in 192 512; do
  echo "icon-${size}: $(curl -sI https://your-domain.com/icons/icon-${size}.png | grep -i content-length)"
done
# Output atteso:
# icon-192: Content-Length: 22xxx
# icon-512: Content-Length: 106xxx
```

---

### ✅ Acceptance Criteria

**Localhost (minimo)**:
- [ ] Manifest visibile in DevTools
- [ ] Install button appare nel HelpMenu
- [ ] Dark mode funziona
- [ ] Build contiene manifest + icons

**Server Production (completo)**:
- [ ] Install su Android (banner auto + fullscreen)
- [ ] Install su iOS Safari (manuale + fullscreen)
- [ ] Install su Desktop Chrome (finestra dedicata)
- [ ] Mobile CSS: no zoom, no overscroll, no pull-to-refresh
- [ ] Standalone mode detection funziona

---

### 🎯 Cosa Testare per Priorità

**Priorità Alta** (must test):
1. Install su Android + fullscreen check
2. Install su iOS Safari + fullscreen check
3. Mobile CSS: no zoom accidentale
4. **Offline fallback page** (server down → pagina branded)

**Priorità Media** (should test):
4. Desktop PWA install
5. Standalone mode detection
6. Dark mode
7. Offline fallback dark mode + i18n

**Priorità Bassa** (nice to test):
7. HTTP LAN (manual install)
8. Troubleshooting scenarios
9. Offline auto-retry (10s)

---

### 🧪 Test: Offline Fallback Page

**Prerequisiti**: frontend avviato (`npm run dev` o build + preview)

**Test 1: Verifica registrazione SW**
1. Apri `http://localhost:5173` (o porta backend se build)
2. DevTools → Application → Service Workers
3. ✅ Verifica: `sw.js` registrato e "activated and is running"
4. ✅ Verifica: Cache Storage → `offline-v1` contiene `offline.html` e `icon-192.png`

**Test 2: Simulazione server down**
1. Apri il sito normalmente (almeno una volta, per registrare il SW)
2. Ferma il server (Ctrl+C sul backend/frontend)
3. Ricarica la pagina (F5 o Cmd+R)
4. ✅ Verifica: appare la pagina offline con:
   - Sfondo animato (onde verdi + linee chart che si disegnano)
   - Logo LibreFolio (icona 192px)
   - Icona wifi-off con animazione pulse
   - Titolo + messaggio nella lingua del browser
   - Bottone "Riprova"
   - Indicatore rosso lampeggiante "Tentativo di riconnessione…"
5. ✅ Verifica dark mode: se il browser è in dark mode, la pagina deve essere scura

**Test 3: Auto-reconnect**
1. Con la pagina offline aperta, riavvia il server
2. ✅ Verifica: entro 10 secondi la pagina si ricarica automaticamente
3. Alternativa: click "Riprova" → ricarica immediatamente

**Test 4: Nessun impatto su navigazione normale**
1. Server attivo, naviga normalmente nell'app
2. ✅ Verifica: nessun rallentamento o comportamento anomalo
3. DevTools → Network: le request NON passano dalla cache del SW (solo navigate fallite)

**Test 5: Update SW**
1. Modifica un commento in `sw.js` (es. aggiungi uno spazio)
2. Ricarica la pagina
3. DevTools → Application → Service Workers
4. ✅ Verifica: "waiting to activate" appare (nuovo SW in attesa)
5. Chiudi e riapri il tab → il nuovo SW è attivo

