# Note della designer — Review colori LibreFolio

> Versione analizzata: **v1.2** (branch `dev_release2`, commit `27228466cb`). Schermate catturate il **2026-10-14**.
> Questo è il file di lavoro della designer: scrivere nei campi **✏️**. Gli sviluppatori lo leggono
> per preparare i token colore e le correzioni. La sintesi tecnica è in `../reports/00_SINTESI.md`.

## 0. Come usare questo file

1. **Prima giornata, giro sui ruoli:** sfogliare la gallery (§1.1) in chiaro e in scuro, poi compilare
   il **vocabolario dei ruoli** (§3) e le **decisioni di base** (§4). Servono valori indicativi, non definitivi.
2. **Giri successivi, schermata per schermata:** per ogni area (§5) ci sono come arrivarci, cosa guardare
   e una riga ✏️ per ogni schermata.
3. Per citare una schermata usare il suo codice, ad es. `dashboard/kpi-top`, aggiungendo tema e
   dispositivo se serve: `dashboard/kpi-top · scuro · mobile`.
4. Spuntare `[x]` le schermate già riviste. Le idee generali vanno in §6.

## 1. Come vedere le cose

### 1.1 Gallery statica (consigliata per iniziare)
- Aprire nel browser **`../snapshots/baseline-r1/index.html`**: ogni schermata è mostrata in chiaro e in scuro
  affiancate. Ci sono le pagine desktop e mobile, in italiano e in inglese. Cliccando su un'immagine la si vede a piena grandezza.
- Ogni schermata ha un'àncora, ad es. `desktop-it.html#dashboard/kpi-top`. I link «🖥» e «📱» delle tabelle sotto puntano lì.
- Dispositivi: **desktop 1280×720** (alcune schermate desktop sono più alte per mostrare un blocco intero;
  dal vivo bisogna scorrere) e **mobile 430×932** (iPhone 14 Pro Max).
- Le schermate hanno animazioni ferme, puntatore fuori dall'area e dati di esempio. Alcune usano dati
  **REPLAY/MOCK** (indicati nelle tabelle) che dal vivo non si vedono identici.
- I file originali sono in `../snapshots/baseline-r1/png/<dispositivo>/<lingua>/<tema>/<area>/<nome>.png`.

### 1.2 App dal vivo (per hover, focus, menu e interazioni)
Uno sviluppatore avvia in un terminale:
```bash
~/.copilot/session-state/aec04834-1532-4d86-9e3f-f942e82aca89/files/scripts/designer_live.sh
```
- Indirizzo: **http://localhost:6160** (server di test con gli stessi dati della gallery; nessun dato reale).
- Accesso: **`e2e_test_admin` / `E2eAdminPass123!`**. È l'utente usato da quasi tutte le schermate.
  `e2e_test_user` / `E2eTestPass123!` è un utente normale.
- **Tema:** pulsante sole/luna nella barra in alto, oppure Impostazioni → Preferenze → Tema (chiaro / scuro / automatico).
- **Lingua:** selettore lingua nella barra in alto.
- Per fermarlo: `Ctrl+C` nel terminale.

### 1.3 Strumenti del browser utili (Chrome / Edge)
- **Colore reale di un elemento:** tasto destro → *Ispeziona* → pannello *Computed* → `color` / `background-color`
  → la freccia mostra quale regola vince. Se la regola è `html.dark …` in `app.css`, è l'override globale (P1):
  in tema scuro il colore scritto nel componente **non** è quello mostrato.
- **Panoramica colori della pagina:** DevTools → ⋮ → *More tools* → **CSS Overview** → *Capture overview*.
  Elenca tutti i colori usati e i problemi di contrasto.
- **Daltonismo:** DevTools → ⋮ → *More tools* → **Rendering** → *Emulate vision deficiencies*
  (protanopia, deuteranopia, tritanopia, acromatopsia).
- **Contrasto puntuale:** nel selettore colore di un elemento (pannello *Styles*) compare il rapporto di contrasto AA/AAA.

## 2. Legenda dei problemi già trovati (dettagli in `../reports/`)

| Codice | In breve |
|---|---|
| **P1** | In tema scuro alcune regole globali di `app.css` vincono sui colori scritti nei componenti: testi, sfondi bianchi/grigi, bordi dei riquadri arrotondati, bordi e focus dei campi. Va giudicato a schermo. |
| **P2** | Le variabili di tema esistono ma nessun componente le usa; i colori sono scritti a mano ovunque. |
| **P3** | Due scale di grigi mescolate (gray e slate); livelli di superficie scura incoerenti; classi inesistenti. |
| **P4** | Stesso significato, colori diversi: guadagno green o emerald, errore rosso o ambra, info blue o sky, 8 verdi brand in scuro… |
| **P5** | Stesso colore, significati diversi nei grafici: il rosso perdita è anche una fetta di allocazione, ecc. |
| **P6** | Palette dei grafici duplicate, con ordini diversi; colori dei broker che dipendono dalla posizione in lista. |
| **P7** | Logica dei colori duplicata nel codice (badge, stati, segno). |
| **P8** | Tabelle, modali file/immagini e conferme con un sistema di colori proprio. |
| **P9** | Accessibilità: testo grigio chiaro 2.5:1, bordi dei campi scuri 2.3:1, solo rosso/verde per guadagno/perdita. |
| **P10** | Splash, pagina offline, icona dell'app (PWA) e riquadro del logo non allineati al tema. |
| **P11** | Lo stesso nome di colore esiste in due versioni: classi Tailwind v4 (OKLCH, più sature) e hex dei grafici (sRGB). Su un Mac recente l'app dal vivo è più satura degli screenshot. |

## 3. Vocabolario dei ruoli (giro 1)

Ogni riga è un *ruolo*: un colore con uno scopo, che diventerà un token. «Attuale» è il valore più usato
oggi. ✏️ Proporre il valore, oppure lasciare vuoto e scrivere un'indicazione nelle note. Aggiungere o togliere righe liberamente.

| Ruolo | Dove | Attuale chiaro | Attuale scuro | ✏️ Proposta chiaro | ✏️ Proposta scuro | ✏️ Note |
|---|---|---|---|---|---|---|
| Sfondo pagina | dietro a tutto | `#f5f4ef` (beige) | `#0f172a` | | | |
| Superficie (card, modali) | card, pannelli | `#ffffff` | `#1e293b` | | | |
| Superficie secondaria / hover | righe, campi, hover | `#f9fafb` · `#f3f4f6` | `#334155` | | | |
| Menu laterale | sidebar | `#1a4031` | `#166534` | | | |
| Testo primario | titoli, valori | `#111827` | `#f8fafc` | | | |
| Testo secondario | descrizioni | `#4b5563` | `#cbd5e1` | | | |
| Testo attenuato | etichette, note | `#6b7280` · `#9ca3af` | `#94a3b8` | | | `#9ca3af` su bianco: 2.5:1 |
| Placeholder / disabilitato | campi vuoti | `#9ca3af` | `#64748b` | | | |
| Bordo | separatori, card | `#e5e7eb` | `#334155` | | | |
| Bordo campi | input, select | gray-300 / gray-200 | `#546175` | | | scuro: 2.3:1 |
| Brand / azione primaria | bottoni, link | `#1a4031` | `#166534` (pieno) · `#39af50` (testo) · `#00d681` (resto) | | | 8 verdi in scuro |
| Focus | anello di focus | `#1a4031` | `#4ade80` | | | |
| Successo | conferme, stato ok | emerald-600 `#059669` (anche green) | emerald-400 `#34d399` | | | |
| Avviso | attenzione | amber-500 `#f59e0b` / 600 | amber-400 `#fbbf24` | | | |
| Errore / pericolo | errori, elimina | red-500 `#ef4444` / 600 `#dc2626` | red-400 `#f87171` | | | |
| Info | suggerimenti | sky / blue-500 | sky-300/400 | | | |
| Guadagno (testo) | variazioni + | emerald-600 · green-600 | emerald-400 · green-400 | | | |
| Perdita (testo) | variazioni − | red-500 · red-600 | red-400 | | | |
| Guadagno / perdita (grafici) | candele, barre | `#16a34a` / `#dc2626` · `#ef4444` | `#4ade80` / `#f87171` | | | serve un secondo segnale per i daltonici? |
| Neutri grafici | assi, griglia, tooltip | 4 set diversi | 4 set diversi | | | |
| Palette categoriale | allocazioni, serie | 14 colori (torta) ≠ 14 (storico) | 14 + 14 | | | quanti colori servono? |
| Sfondo modale (overlay) | dietro le modali | nero 45–50% | nero 45–50% | | | |

## 4. Decisioni di base (giro 1)

Per ognuna: ✏️ **Decisione** e ✏️ **Perché**. Le domande vengono dalla sintesi tecnica (`../reports/00_SINTESI.md`, §4).

**A — Fondamenta**
- **A1.** Usiamo un solo insieme di colori con un nome per ruolo (i token del §3) al posto delle classi scritte a mano? → ✏️
- **A2.** Scala di grigi unica (più fredda *slate* o più neutra *gray*), uguale in chiaro e in scuro? → ✏️
- **A3.** Un solo verde brand per tema (pieno, testo, focus, sfumature)? Ruolo di beige, salvia `#9caf9c` e scuro `#111111`? → ✏️
- **A4.** Lo sfondo pagina chiaro resta beige o diventa bianco/grigio chiaro? → ✏️
- **A5.** Obiettivo di contrasto: AA (4.5:1 testo, 3:1 grafica e bordi dei campi)? → ✏️

**B — Significati**
- **B6.** Colori di successo, avviso, errore, info, neutro e disabilitato (famiglia e sfumatura, in chiaro e in scuro). → ✏️
- **B7.** Guadagno e perdita (testo, barre, linee) + un secondo segnale per i daltonici (▲▼, motivi, blu/arancio?). → ✏️
- **B8.** Un solo stile per badge, avvisi, toast, focus e overlay; meno livelli di trasparenza. → ✏️
- **B9.** Serve un colore per tipo di transazione (acquisto, vendita, dividendo, commissione…)? → ✏️

**C — Grafici**
- **C10.** Una palette categoriale unica: quanti colori, in che ordine, escludendo i colori riservati (brand, guadagno, perdita). → ✏️
- **C11.** Colori fissi per entrate, costi, dividendi, interessi, portafoglio e benchmark. → ✏️
- **C12.** Assi, griglie e tooltip dei grafici con gli stessi neutri dell'interfaccia. → ✏️
- **C13.** Colori dei broker e dei lotti: stabili e scelti a mano, o generati? → ✏️

## 5. Schermate per area (177 schermate)

Ogni area ha: tabella di navigazione (🖥 desktop · 📱 mobile apre la gallery), «Cosa guardare» (spunti
dall'analisi, da confermare a schermo) e le righe ✏️ per le note.
**REPLAY/MOCK** = dati finti o registrati: dal vivo non si vede identico.


### 5.1 Accesso e registrazione — `auth` (4 schermate)

| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |
|---|---|---|---|---|
| `auth/01-login` | [🖥](../snapshots/baseline-r1/desktop-it.html#auth/01-login) [📱](../snapshots/baseline-r1/mobile-it.html#auth/01-login) | `/` — Aprire l'app da disconnessi: pagina di login | nessuno | `routes/+page.svelte`, `lib/components/auth/LoginCard.svelte` |
| `auth/02-register-empty` | [🖥](../snapshots/baseline-r1/desktop-it.html#auth/02-register-empty) [📱](../snapshots/baseline-r1/mobile-it.html#auth/02-register-empty) | `/` — Login → link «Registrati» → modale di registrazione vuota | nessuno | `auth/RegisterCard.svelte` |
| `auth/03-register-filled` | [🖥](../snapshots/baseline-r1/desktop-it.html#auth/03-register-filled) [📱](../snapshots/baseline-r1/mobile-it.html#auth/03-register-filled) | `/` — Come sopra, poi compilare utente `demo_user`, email `demo@example.com`, password `MyStr0ng!Pass`. Mostra il misuratore di robustezza | nessuno (solo input) | `auth/RegisterCard.svelte` |
| `auth/update-available-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#auth/update-available-modal) [📱](../snapshots/baseline-r1/mobile-it.html#auth/update-available-modal) | `/dashboard` (dopo il login) — Accedere da admin: si apre da solo il popup «Aggiornamento disponibile v99.9.0» | admin. **MOCK**: release finta in localStorage e `container-image-status` intercettato | `auth/UpdateAvailableModal.svelte` |

**Cosa guardare** (spunti dall'analisi, da confermare a schermo):
- Riquadro bianco del logo identico anche in scuro (`LoginCard.svelte:44`, `RegisterCard.svelte:152`, `ForgotPasswordCard.svelte:16`) — P10.
- Indicatore di robustezza password solo con colori chiari, senza varianti scure (`PasswordStrength.svelte`).
- Campi in scuro: bordo fisso `#546175`, il verde di focus non compare (P1); contrasto del bordo 2.3:1 (P9).
- Bottone primario: `#1a4031` in chiaro; in scuro `#166534` a riposo e `#00d681` al passaggio del mouse (P1, P4).
- Sfondo animato del login: gradiente scuro definito a parte in `app.css` (`.animated-bg-gradient`).

**✏️ Note — auth**
- [ ] `auth/01-login` — 
- [ ] `auth/02-register-empty` — 
- [ ] `auth/03-register-filled` — 
- [ ] `auth/update-available-modal` — 
- ✏️ Note generali sull'area:

### 5.2 Onboarding (primo accesso, tour, guide) — `onboarding` (3 schermate)

| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |
|---|---|---|---|---|
| `onboarding/welcome-setup` | [🖥](../snapshots/baseline-r1/desktop-it.html#onboarding/welcome-setup) [📱](../snapshots/baseline-r1/mobile-it.html#onboarding/welcome-setup) | `/welcome` — Primo accesso con un account nuovo: pagina di benvenuto con lingua, valuta (precompilata) e avatar con le iniziali | account nuovo usa-e-getta | `features/onboarding/components/WelcomePage.svelte`, `routes/(app)/welcome/+page.svelte` |
| `onboarding/core-tour-step` | [🖥](../snapshots/baseline-r1/desktop-it.html#onboarding/core-tour-step) [📱](../snapshots/baseline-r1/mobile-it.html#onboarding/core-tour-step) | `/dashboard` — Account nuovo → completare il benvenuto → avviare il tour («Inizia») → «Avanti» fino al passo che indica la voce FX. Su mobile il menu laterale è aperto | account nuovo | `OnboardingCoachmark.svelte`, `layout/Sidebar.svelte` |
| `onboarding/contextual-guide` | [🖥](../snapshots/baseline-r1/desktop-it.html#onboarding/contextual-guide) [📱](../snapshots/baseline-r1/mobile-it.html#onboarding/contextual-guide) | `/fx` — Account nuovo con la guida FX attiva → Menu → FX → la guida contestuale appare → «Avanti» (passo «filtri») | account nuovo; le card FX usano dati offline/fixture | `OnboardingCoachmark.svelte`, `routes/(app)/fx/+page.svelte`, `fx/FxCard.svelte` |

**Cosa guardare** (spunti dall'analisi, da confermare a schermo):
- Card di benvenuto scritta come `bg-white dark:bg-slate-900`, ma in scuro diventa `#1e293b` per l'override globale (P1).
- Coachmark del tour: colore di anello, fumetto ed evidenziazione.
- Avatar con le iniziali: colore generato automaticamente dal testo; verificarne la leggibilità.

**✏️ Note — onboarding**
- [ ] `onboarding/welcome-setup` — 
- [ ] `onboarding/core-tour-step` — 
- [ ] `onboarding/contextual-guide` — 
- ✏️ Note generali sull'area:

### 5.3 Dashboard — `dashboard` (33 schermate)

Tutti gli shot usano l'utente admin. Dove indicato, i dati vengono dal **REPLAY** `dashboard-report.json` (preset 1A selezionato).

| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |
|---|---|---|---|---|
| `dashboard/kpi-top` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/kpi-top) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/kpi-top) | `/dashboard` — Menu → Dashboard → periodo «1A» → in cima alla pagina | REPLAY | `routes/(app)/dashboard/+page.svelte`, `dashboard/KpiSection.svelte` |
| `dashboard/main` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/main) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/main) | `/dashboard` — Scorrere fino al grafico di crescita → selettore in valuta (€) | REPLAY | `dashboard/GrowthChart.svelte` |
| `dashboard/main-pct` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/main-pct) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/main-pct) | `/dashboard` — Grafico di crescita → selettore «%» | REPLAY | `GrowthChart.svelte` |
| `dashboard/growth-pnl-candles` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/growth-pnl-candles) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/growth-pnl-candles) | `/dashboard` — Grafico di crescita → modalità «P&L» → sotto-modo «Candele» (larghezza candela di default) | REPLAY | `GrowthChart.svelte` |
| `dashboard/growth-pnl-income` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/growth-pnl-income) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/growth-pnl-income) | `/dashboard` — P&L → sotto-modo «Entrate» | REPLAY | `GrowthChart.svelte` |
| `dashboard/growth-pnl-line` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/growth-pnl-line) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/growth-pnl-line) | `/dashboard` — P&L → sotto-modo «Linea» | REPLAY | `GrowthChart.svelte` |
| `dashboard/privacy-masked` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/privacy-masked) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/privacy-masked) | `/dashboard` — Icona occhio (privacy) nell'header → importi mostrati come «•••»; inquadrata la riga dei KPI | REPLAY | `ui/PrivacyToggle.svelte`, `KpiSection.svelte`, `layout/Header.svelte` |
| `dashboard/menu-open` | [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/menu-open) | `/dashboard` — Su telefono: icona ☰ in alto → menu laterale aperto | REPLAY | `layout/Sidebar.svelte`, `layout/Header.svelte` |
| `dashboard/allocation-type-now` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/allocation-type-now) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/allocation-type-now) | `/dashboard` — Scorrere al pannello Allocazione → scheda «Tipo» → vista «Ora» | REPLAY | `dashboard/AllocationPanel.svelte` |
| `dashboard/allocation-type-history` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/allocation-type-history) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/allocation-type-history) | `/dashboard` — Allocazione → «Tipo» → vista «Storico» | REPLAY | `AllocationPanel.svelte` |
| `dashboard/allocation-sector-now` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/allocation-sector-now) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/allocation-sector-now) | `/dashboard` — Allocazione → «Settore» → «Ora» | REPLAY | `AllocationPanel.svelte` |
| `dashboard/allocation-sector-history` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/allocation-sector-history) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/allocation-sector-history) | `/dashboard` — Allocazione → «Settore» → «Storico» | REPLAY | `AllocationPanel.svelte` |
| `dashboard/allocation-geo-now` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/allocation-geo-now) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/allocation-geo-now) | `/dashboard` — Allocazione → «Geografia» → «Ora» | REPLAY | `AllocationPanel.svelte` |
| `dashboard/allocation-geo-history` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/allocation-geo-history) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/allocation-geo-history) | `/dashboard` — Allocazione → «Geografia» → «Storico» | REPLAY | `AllocationPanel.svelte` |
| `dashboard/positions-holdings-table` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/positions-holdings-table) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/positions-holdings-table) | `/dashboard` — Scheda «Posizioni» → «Esposizione/Detenute» → vista «Tabella» (alto su desktop) | REPLAY | `dashboard/PositionsPanel.svelte`, `ExposureTable.svelte` |
| `dashboard/positions-holdings-map` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/positions-holdings-map) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/positions-holdings-map) | `/dashboard` — Posizioni → «Detenute» → vista «Mappa» (treemap) | REPLAY | `PositionsPanel.svelte`, `ExposureTreemap.svelte` |
| `dashboard/positions-performance-table` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/positions-performance-table) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/positions-performance-table) | `/dashboard` — Posizioni → «Performance» → «Tabella» | REPLAY | `ContributionTable.svelte` |
| `dashboard/positions-performance-map` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/positions-performance-map) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/positions-performance-map) | `/dashboard` — Posizioni → «Performance» → «Mappa» (grafico performance) | REPLAY | `PerformanceChart.svelte` |
| `dashboard/fifo-lots-panel` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/fifo-lots-panel) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/fifo-lots-panel) | `/dashboard` — Periodo «Max» (o 2A) → Posizioni → Detenute/Tabella → riga «Apple» → menu ⋮ → «Analizza lotti» → pannello in cima | admin, **dati LIVE** (niente replay) | `brokers/lots/LotsAnalysisPanel.svelte` |
| `dashboard/fifo-lots-wac-chart` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/fifo-lots-wac-chart) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/fifo-lots-wac-chart) | `/dashboard` — Stesso pannello, scorrere al grafico prezzo medio (WAC) | LIVE | `lots/LotWacPriceChart.svelte` |
| `dashboard/fifo-lots-gantt-chart` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/fifo-lots-gantt-chart) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/fifo-lots-gantt-chart) | `/dashboard` — Scorrere al Gantt dei lotti | LIVE | `lots/LotGanttChart.svelte` |
| `dashboard/fifo-lots-table` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/fifo-lots-table) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/fifo-lots-table) | `/dashboard` — Scorrere alla tabella unificata dei lotti | LIVE | `lots/UnifiedLotsTable.svelte` |
| `dashboard/fifo-lots-comparison-chart` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/fifo-lots-comparison-chart) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/fifo-lots-comparison-chart) | `/dashboard` — Scorrere al grafico di confronto dei lotti | LIVE | `lots/LotComparisonChart.svelte` |
| `dashboard/fifo-lots-comparison-chart-return` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/fifo-lots-comparison-chart-return) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/fifo-lots-comparison-chart-return) | `/dashboard` — Nel grafico di confronto → modalità «Rendimento» | LIVE | `LotComparisonChart.svelte` |
| `dashboard/fifo-lots-custody-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/fifo-lots-custody-modal) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/fifo-lots-custody-modal) | `/dashboard` — Tabella lotti → prima riga ⋮ → «Vedi dettagli» → modale custodia | LIVE | `lots/LotCustodyModal.svelte` |
| `dashboard/transactions-tab` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/transactions-tab) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/transactions-tab) | `/dashboard` — Scheda «Transazioni» della dashboard | REPLAY (lista transazioni probabilmente live, ?) | `dashboard/+page.svelte`, `transactions/TransactionsTable.svelte` |
| `dashboard/empty-state` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/empty-state) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/empty-state) | `/dashboard` — Accedere con un account senza dati → Dashboard vuota | **e2e_test_empty** | `dashboard/+page.svelte` |
| `dashboard/data-quality-banner` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/data-quality-banner) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/data-quality-banner) | `/dashboard` — Banner «Qualità dati» in alto → espanderlo: prezzi vecchi (Apple, Microsoft) e coppia FX USD-CHF mancante | **MOCK** (issues iniettate nel replay) | `ui/feedback/DataQualityBanner.svelte` |
| `dashboard/data-quality-sync-rates` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/data-quality-sync-rates) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/data-quality-sync-rates) | `/dashboard` — Banner espanso → problema «Tassi di cambio mancanti» (EUR-GBP, EUR-USD) con pulsante «Sincronizza tassi» | **MOCK** | `DataQualityBanner.svelte` |
| `dashboard/risk-hurt` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/risk-hurt) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/risk-hurt) | `/dashboard` — Periodo 1A → scheda «Rischio» → blocco 1 «Quanto può far male?» (card, sott'acqua, istogramma) | admin LIVE (benchmark azzerato in localStorage) | `risk/levels/RiskLevelsPanel.svelte` |
| `dashboard/risk-diversification` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/risk-diversification) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/risk-diversification) | `/dashboard` — Rischio → blocco 2 «Sono diversificato quanto credo?» | LIVE | `RiskLevelsPanel.svelte` |
| `dashboard/risk-paid` | [🖥](../snapshots/baseline-r1/desktop-it.html#dashboard/risk-paid) [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/risk-paid) | `/dashboard` — Rischio → blocco 3 «Sono pagato per questo rischio?» con benchmark «MSCI World Index» | LIVE (benchmark preimpostato in localStorage: sceglierlo a mano) | `RiskLevelsPanel.svelte` |
| `dashboard/risk-whatif` | ⚠️ desktop non catturata [📱](../snapshots/baseline-r1/mobile-it.html#dashboard/risk-whatif) | `/dashboard` — Rischio → blocco 4 «E se…?» → aprirlo → «+ Replay storico» → preset «Crisi finanziaria globale» → «Esegui» | **MOCK** (finestra della crisi iniettata via route sulla query di rischio) | `risk/levels/l4/L4Replay.svelte`, `RiskLevelsPanel.svelte` |

**Cosa guardare** (spunti dall'analisi, da confermare a schermo):
- Guadagni e perdite qui sono `green-600/400`, mentre in Asset, FX e Broker sono `emerald` (P4). Le barre KPI invertono le sfumature tra chiaro e scuro (`KpiSection.svelte:223,264`).
- Grafico di crescita: linea NAV `#1a4031` / `#4ade80` (diverso dal verde brand scuro `#00d681`); costi arancio qui ma rossi nel grafico Performance; dividendi oro `#b08d00` / `#facc15` (decisione di ottobre 2026); interessi viola.
- Allocazione: le palette di «Ora» (torta) e «Storico» hanno ordini diversi, quindi la stessa categoria cambia colore (P6). Lo slot rosso `#dc2626` sembra una perdita (P5). Sottotipi = sfumature del colore padre (decisione D71).
- Mappa posizioni (treemap): scala rosso/verde per intensità. In chiaro le perdite più grandi diventano *più chiare*, all'opposto dei guadagni (`ExposureTreemap.svelte:488`). Distinzione solo rosso/verde (daltonismo, P9).
- Banner qualità dati: errori e avvisi sono entrambi ambra (`DataQualityBanner.svelte:80`) (P4).
- Lotti FIFO: colori dei broker generati dalla posizione in lista, quindi cambiano se si elimina un broker. SPLIT nel Gantt è `#ca8a04` (contrasto 2.94:1, già scartato a ottobre) (P9). Il grafico WAC usa verdi e rossi chiari diversi (`#86efac` / `#fca5a5`).
- Scheda Rischio: istogrammi, sott'acqua, simulazioni; confrontare i colori con quelli di Asset e Laboratorio di rischio.
- Menu laterale (mobile `menu-open`): `bg-libre-green`, forzato in scuro a `#166534`.
- Attenzione: quasi tutta la dashboard della gallery usa dati registrati (REPLAY); dal vivo i numeri e le forme saranno diversi.

**✏️ Note — dashboard**
- [ ] `dashboard/kpi-top` — 
- [ ] `dashboard/main` — 
- [ ] `dashboard/main-pct` — 
- [ ] `dashboard/growth-pnl-candles` — 
- [ ] `dashboard/growth-pnl-income` — 
- [ ] `dashboard/growth-pnl-line` — 
- [ ] `dashboard/privacy-masked` — 
- [ ] `dashboard/menu-open` — 
- [ ] `dashboard/allocation-type-now` — 
- [ ] `dashboard/allocation-type-history` — 
- [ ] `dashboard/allocation-sector-now` — 
- [ ] `dashboard/allocation-sector-history` — 
- [ ] `dashboard/allocation-geo-now` — 
- [ ] `dashboard/allocation-geo-history` — 
- [ ] `dashboard/positions-holdings-table` — 
- [ ] `dashboard/positions-holdings-map` — 
- [ ] `dashboard/positions-performance-table` — 
- [ ] `dashboard/positions-performance-map` — 
- [ ] `dashboard/fifo-lots-panel` — 
- [ ] `dashboard/fifo-lots-wac-chart` — 
- [ ] `dashboard/fifo-lots-gantt-chart` — 
- [ ] `dashboard/fifo-lots-table` — 
- [ ] `dashboard/fifo-lots-comparison-chart` — 
- [ ] `dashboard/fifo-lots-comparison-chart-return` — 
- [ ] `dashboard/fifo-lots-custody-modal` — 
- [ ] `dashboard/transactions-tab` — 
- [ ] `dashboard/empty-state` — 
- [ ] `dashboard/data-quality-banner` — 
- [ ] `dashboard/data-quality-sync-rates` — 
- [ ] `dashboard/risk-hurt` — 
- [ ] `dashboard/risk-diversification` — 
- [ ] `dashboard/risk-paid` — 
- [ ] `dashboard/risk-whatif` — 
- ✏️ Note generali sull'area:

### 5.4 Sicurezza connessione — `security` (1 schermate)

| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |
|---|---|---|---|---|
| `security/connection-indicator` | [🖥](../snapshots/baseline-r1/desktop-it.html#security/connection-indicator) [📱](../snapshots/baseline-r1/mobile-it.html#security/connection-indicator) | `http://lf-e2e.lan:<porta>/dashboard` — Aprire l'app da un nome di rete locale (non localhost) → periodo 1A → (mobile: ☰) → clic sull'indicatore di sicurezza della connessione → dettagli aperti, col puntatore sopra | admin + REPLAY. Serve un hostname LAN (regola di risoluzione del browser) | `layout/ConnectionSecurityIndicator.svelte`, `layout/Header.svelte`, `layout/Sidebar.svelte` |

**Cosa guardare** (spunti dall'analisi, da confermare a schermo):
- Indicatore di sicurezza della connessione: nessuna variante scura nel componente (`ConnectionSecurityIndicator.svelte`); verificarlo in scuro.
- Dal vivo appare solo aprendo l'app da un nome di rete locale, non da `localhost`.

**✏️ Note — security**
- [ ] `security/connection-indicator` — 
- ✏️ Note generali sull'area:

### 5.5 Impostazioni — `settings` (13 schermate)

Tutti con l'utente admin, su `/settings`, entrambi i viewport e 4 lingue.

| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |
|---|---|---|---|---|
| `settings/user-preferences` | [🖥](../snapshots/baseline-r1/desktop-it.html#settings/user-preferences) [📱](../snapshots/baseline-r1/mobile-it.html#settings/user-preferences) | `/settings` — Menu → Impostazioni → scheda «Preferenze» | admin | `routes/(app)/settings/+page.svelte`, `settings/tabs/PreferencesTab.svelte` |
| `settings/global-settings` | [🖥](../snapshots/baseline-r1/desktop-it.html#settings/global-settings) [📱](../snapshots/baseline-r1/mobile-it.html#settings/global-settings) | `/settings` — Impostazioni → scheda «Amministrazione/Globali» (alto su desktop) | admin | `settings/tabs/GlobalSettingsTab.svelte` |
| `settings/about` | [🖥](../snapshots/baseline-r1/desktop-it.html#settings/about) [📱](../snapshots/baseline-r1/mobile-it.html#settings/about) | `/settings` — Impostazioni → scheda «Informazioni» | admin | `settings/tabs/AboutTab.svelte` |
| `settings/password-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#settings/password-modal) [📱](../snapshots/baseline-r1/mobile-it.html#settings/password-modal) | `/settings` — Impostazioni → pulsante «Cambia password» | admin | `settings/+page.svelte` (modale password, ?) |
| `settings/profile` | [🖥](../snapshots/baseline-r1/desktop-it.html#settings/profile) [📱](../snapshots/baseline-r1/mobile-it.html#settings/profile) | `/settings` — Impostazioni → scheda «Profilo» (alto su desktop) | admin | `settings/tabs/ProfileTab.svelte` |
| `settings/scheduler-config` | [🖥](../snapshots/baseline-r1/desktop-it.html#settings/scheduler-config) [📱](../snapshots/baseline-r1/mobile-it.html#settings/scheduler-config) | `/settings` — Scheda Globali → se serve, sbloccare il lucchetto 🔒 → pulsante configurazione scheduler | admin | `settings/SchedulerConfigModal.svelte`, `GlobalSettingsTab.svelte` |
| `settings/scheduler-log` | [🖥](../snapshots/baseline-r1/desktop-it.html#settings/scheduler-log) [📱](../snapshots/baseline-r1/mobile-it.html#settings/scheduler-log) | `/settings` — Scheda Globali → clic sulla riga di stato dello scheduler → modale log | admin | `settings/SchedulerLogModal.svelte` |
| `settings/changelog-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#settings/changelog-modal) [📱](../snapshots/baseline-r1/mobile-it.html#settings/changelog-modal) | `/dashboard` — (mobile: ☰) → clic sul numero di versione in fondo al menu laterale | admin | `layout/ChangelogModal.svelte`, `layout/Sidebar.svelte` |
| `settings/changelog-modal-search` | [🖥](../snapshots/baseline-r1/desktop-it.html#settings/changelog-modal-search) [📱](../snapshots/baseline-r1/mobile-it.html#settings/changelog-modal-search) | `/dashboard` — Nel changelog → cercare «Docker» → clic sul primo risultato | admin | `ChangelogModal.svelte` |
| `settings/cache-panel` | [🖥](../snapshots/baseline-r1/desktop-it.html#settings/cache-panel) [📱](../snapshots/baseline-r1/mobile-it.html#settings/cache-panel) | `/settings` — Globali → sblocca 🔒 → categoria «Memoria» → pannello cache | admin | `settings/CachePanel.svelte` |
| `settings/about-plugin-diagnostics` | [🖥](../snapshots/baseline-r1/desktop-it.html#settings/about-plugin-diagnostics) [📱](../snapshots/baseline-r1/mobile-it.html#settings/about-plugin-diagnostics) | `/settings` — Informazioni → espandere «Diagnostica plugin» (alto su desktop) | admin | `AboutTab.svelte` |
| `settings/about-tool-diagnostics` | [🖥](../snapshots/baseline-r1/desktop-it.html#settings/about-tool-diagnostics) [📱](../snapshots/baseline-r1/mobile-it.html#settings/about-tool-diagnostics) | `/settings` — Informazioni → «Diagnostica plugin» → sezione strumenti → espandere «Diagnostica strumenti», scorrere in fondo | admin | `AboutTab.svelte` (pannello tool) |
| `settings/onboarding-replay` | [🖥](../snapshots/baseline-r1/desktop-it.html#settings/onboarding-replay) [📱](../snapshots/baseline-r1/mobile-it.html#settings/onboarding-replay) | `/settings?tab=preferences` — Preferenze → categoria «Onboarding» (mobile: menu a tendina delle categorie) | admin | `features/onboarding/components/OnboardingReplaySection.svelte` |

**Cosa guardare** (spunti dall'analisi, da confermare a schermo):
- Scheda Informazioni: 147 classi colore e solo 4 varianti scure, quindi in scuro si appoggia all'override globale (P1). Riquadro bianco del logo (`AboutTab.svelte:258`).
- Log dello scheduler: stati ok, parziale, fallito e saltato senza varianti scure (`syncHelpers.ts:97`). Badge dei provider: ECB blu, MANUAL ambra… (P4).
- La pagina Impostazioni non ha varianti scure nel proprio file (`routes/(app)/settings/+page.svelte`).
- Changelog, pannello cache, diagnostica: badge di stato e livelli di superficie.

**✏️ Note — settings**
- [ ] `settings/user-preferences` — 
- [ ] `settings/global-settings` — 
- [ ] `settings/about` — 
- [ ] `settings/password-modal` — 
- [ ] `settings/profile` — 
- [ ] `settings/scheduler-config` — 
- [ ] `settings/scheduler-log` — 
- [ ] `settings/changelog-modal` — 
- [ ] `settings/changelog-modal-search` — 
- [ ] `settings/cache-panel` — 
- [ ] `settings/about-plugin-diagnostics` — 
- [ ] `settings/about-tool-diagnostics` — 
- [ ] `settings/onboarding-replay` — 
- ✏️ Note generali sull'area:

### 5.6 Strumenti (PAC Allocator) — `tools` (10 schermate)

Shot PAC: dati scenario, non scritti nel DB.
- Broker: «Interactive Brokers» e «DEGIRO».
- Asset: Apple Inc., Microsoft Corporation e un asset manuale «Global Bond ETF» a 52.4.
- Fonti: liquidità copiata da DEGIRO (2000 EUR), contributo «PAC» 500 EUR, conto esterno «Northwind Bank» USD 3000 (di cui 1200 usati).
- Commissione DEGIRO: 0.19%, min 1.5, max 18.
- Target: 30/30/40.
- Dettaglio completo in `fixtures/galleryPac.ts` 81-100.

| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |
|---|---|---|---|---|
| `tools/hub` | [🖥](../snapshots/baseline-r1/desktop-it.html#tools/hub) [📱](../snapshots/baseline-r1/mobile-it.html#tools/hub) | `/tools` — Menu → Strumenti | admin | `features/tools/ToolsHub.svelte` |
| `tools/pac-step-liquidity` | [🖥](../snapshots/baseline-r1/desktop-it.html#tools/pac-step-liquidity) [📱](../snapshots/baseline-r1/mobile-it.html#tools/pac-step-liquidity) | `/tools/pac_allocator` — Strumenti → card «PAC Allocator» → compilare lo scenario → passo «Liquidità» | admin + bozza digitata | `pac-allocator/planner/PacPlannerTool.svelte`, `shell/StepNav.svelte`, `shell/SummaryPanel.svelte` |
| `tools/pac-step-brokers` | [🖥](../snapshots/baseline-r1/desktop-it.html#tools/pac-step-brokers) [📱](../snapshots/baseline-r1/mobile-it.html#tools/pac-step-brokers) | idem — Passo Broker → editor del broker aperto | idem | `PacPlannerTool.svelte` |
| `tools/pac-step-assets` | [🖥](../snapshots/baseline-r1/desktop-it.html#tools/pac-step-assets) [📱](../snapshots/baseline-r1/mobile-it.html#tools/pac-step-assets) | idem — Passo «Asset» | idem | `steps/AssetsStep.svelte` |
| `tools/pac-step-routing` | [🖥](../snapshots/baseline-r1/desktop-it.html#tools/pac-step-routing) [📱](../snapshots/baseline-r1/mobile-it.html#tools/pac-step-routing) | idem — Passo «Instradamento» | idem | `PacPlannerTool.svelte` |
| `tools/pac-step-review` | [🖥](../snapshots/baseline-r1/desktop-it.html#tools/pac-step-review) [📱](../snapshots/baseline-r1/mobile-it.html#tools/pac-step-review) | idem — Target del bond lasciati incompleti → passo «Revisione» (mostra gli avvisi) | idem | `PacPlannerTool.svelte` |
| `tools/pac-step-targets` | [🖥](../snapshots/baseline-r1/desktop-it.html#tools/pac-step-targets) [📱](../snapshots/baseline-r1/mobile-it.html#tools/pac-step-targets) | idem — Passo «Obiettivi» | idem | `PacPlannerTool.svelte` |
| `tools/pac-result` | [🖥](../snapshots/baseline-r1/desktop-it.html#tools/pac-result) [📱](../snapshots/baseline-r1/mobile-it.html#tools/pac-result) | idem — Bozza completa → «Calcola» → sezione allocazione del risultato | idem (solver locale) | `PacPlannerTool.svelte` |
| `tools/pac-result-plan` | [🖥](../snapshots/baseline-r1/desktop-it.html#tools/pac-result-plan) [📱](../snapshots/baseline-r1/mobile-it.html#tools/pac-result-plan) | idem — Risultato → «Piano operativo» | idem | idem |
| `tools/pac-result-proof` | [🖥](../snapshots/baseline-r1/desktop-it.html#tools/pac-result-proof) [📱](../snapshots/baseline-r1/mobile-it.html#tools/pac-result-proof) | idem — Risultato → «Prova e solver» | idem | idem |

**Cosa guardare** (spunti dall'analisi, da confermare a schermo):
- PAC: badge e avvisi con una palette propria (successo smeraldo, info sky, avviso ambra, errore rosso) (`planner/ui.ts:80`).
- Barre degli obiettivi: «bilanciato» usa il verde brand; eccesso e mancanza non hanno varianti scure (`TargetsStep.svelte:29`).
- Barre di esposizione: unico grafico che usa il verde brand scuro `#00d681` (`ExposureBars.svelte:30`). Mappe di esposizione con la scala verde copiata dalla dashboard.

**✏️ Note — tools**
- [ ] `tools/hub` — 
- [ ] `tools/pac-step-liquidity` — 
- [ ] `tools/pac-step-brokers` — 
- [ ] `tools/pac-step-assets` — 
- [ ] `tools/pac-step-routing` — 
- [ ] `tools/pac-step-review` — 
- [ ] `tools/pac-step-targets` — 
- [ ] `tools/pac-result` — 
- [ ] `tools/pac-result-plan` — 
- [ ] `tools/pac-result-proof` — 
- ✏️ Note generali sull'area:

### 5.7 Supporto e donazioni — `support` (2 schermate)

| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |
|---|---|---|---|---|
| `support/donation-popup` | [🖥](../snapshots/baseline-r1/desktop-it.html#support/donation-popup) [📱](../snapshots/baseline-r1/mobile-it.html#support/donation-popup) | `/dashboard` — Accedere → popup donazione con i pulsanti social (X, Reddit, Facebook, Instagram, TikTok) | admin. **MOCK**: la risposta del login viene forzata a `show_donation_popup=true` | `auth/DonationPopupModal.svelte` |
| `support/social-share-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#support/social-share-modal) [📱](../snapshots/baseline-r1/mobile-it.html#support/social-share-modal) | `/settings` — Impostazioni → Informazioni → card supporto → «Reddit» → modale di condivisione, messaggio scrollato in fondo | admin | `support/SocialShareModal.svelte`, `AboutTab.svelte` |

**Cosa guardare** (spunti dall'analisi, da confermare a schermo):
- Popup donazione: riquadro bianco del logo anche in scuro (P10); pulsanti social.
- Modale di condivisione: livelli di superficie e campo messaggio.

**✏️ Note — support**
- [ ] `support/donation-popup` — 
- [ ] `support/social-share-modal` — 
- ✏️ Note generali sull'area:

### 5.8 File — `files` (9 schermate)

| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |
|---|---|---|---|---|
| `files/static-tab` | [🖥](../snapshots/baseline-r1/desktop-it.html#files/static-tab) [📱](../snapshots/baseline-r1/mobile-it.html#files/static-tab) | `/files?tab=static` — Menu → File → scheda «Risorse statiche» (alto su desktop) | admin | `routes/(app)/files/+page.svelte`, `files/FilesTable.svelte` |
| `files/brim-tab` | [🖥](../snapshots/baseline-r1/desktop-it.html#files/brim-tab) [📱](../snapshots/baseline-r1/mobile-it.html#files/brim-tab) | `/files?tab=brim` — File → scheda «Report broker» | admin | `FilesTable.svelte` |
| `files/static-grid` | [🖥](../snapshots/baseline-r1/desktop-it.html#files/static-grid) [📱](../snapshots/baseline-r1/mobile-it.html#files/static-grid) | `/files?tab=static` — Risorse statiche → vista «Griglia» | admin | `files/+page.svelte` |
| `files/preview-modal-csv` | [🖥](../snapshots/baseline-r1/desktop-it.html#files/preview-modal-csv) [📱](../snapshots/baseline-r1/mobile-it.html#files/preview-modal-csv) | `/files?tab=brim&filename=schwab-export.csv` — Report broker → riga `schwab-export.csv` → anteprima (griglia) | admin | `files/FilePreviewModal.svelte` |
| `files/preview-modal-image` | [🖥](../snapshots/baseline-r1/desktop-it.html#files/preview-modal-image) [📱](../snapshots/baseline-r1/mobile-it.html#files/preview-modal-image) | `/files?tab=static&filename=men_01.png` — Statiche → `men_01.png` → anteprima | admin | `FilePreviewModal.svelte` |
| `files/preview-modal-pdf` | [🖥](../snapshots/baseline-r1/desktop-it.html#files/preview-modal-pdf) [📱](../snapshots/baseline-r1/mobile-it.html#files/preview-modal-pdf) | `…filename=ebook.pdf` — Statiche → `ebook.pdf` → anteprima (attendere ~4 s che spariscano i controlli pagina) | admin | `FilePreviewModal.svelte` |
| `files/preview-modal-markdown` | [🖥](../snapshots/baseline-r1/desktop-it.html#files/preview-modal-markdown) [📱](../snapshots/baseline-r1/mobile-it.html#files/preview-modal-markdown) | `…filename=preview_markdown_sample.md` — Statiche → quel file → anteprima | admin | `FilePreviewModal.svelte` |
| `files/preview-modal-text` | [🖥](../snapshots/baseline-r1/desktop-it.html#files/preview-modal-text) [📱](../snapshots/baseline-r1/mobile-it.html#files/preview-modal-text) | `…filename=preview_notes_sample.txt` — Statiche → quel file → anteprima | admin | `FilePreviewModal.svelte` |
| `files/brim-report-sets` | [🖥](../snapshots/baseline-r1/desktop-it.html#files/brim-report-sets) [📱](../snapshots/baseline-r1/mobile-it.html#files/brim-report-sets) | `/files?tab=brim` — Report broker → badge dei set → filtro colonna «Caricato da» aperto | **account usa-e-getta** con broker «Danske Bank» e 7 file caricati via API | `FilesTable.svelte` |

**Cosa guardare** (spunti dall'analisi, da confermare a schermo):
- Sistema CSS parallelo: `FilesTable`, `FileGrid` e `FilePreviewModal` usano colori esadecimali propri nei blocchi `<style>` (P8). Confrontarli con le altre tabelle e modali.
- Etichette con colori generati dal testo (`getStringColor`); badge dei set di report (`FileSetBadges.svelte`: indaco, ambra, grigio, smeraldo, rosso).

**✏️ Note — files**
- [ ] `files/static-tab` — 
- [ ] `files/brim-tab` — 
- [ ] `files/static-grid` — 
- [ ] `files/preview-modal-csv` — 
- [ ] `files/preview-modal-image` — 
- [ ] `files/preview-modal-pdf` — 
- [ ] `files/preview-modal-markdown` — 
- [ ] `files/preview-modal-text` — 
- [ ] `files/brim-report-sets` — 
- ✏️ Note generali sull'area:

### 5.9 Transazioni — `transactions` (19 schermate)

| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |
|---|---|---|---|---|
| `transactions/list` | [🖥](../snapshots/baseline-r1/desktop-it.html#transactions/list) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/list) | `/transactions` — Menu → Transazioni | admin | `routes/(app)/transactions/+page.svelte`, `transactions/TransactionsTable.svelte` |
| `transactions/form-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#transactions/form-modal) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/form-modal) | `/transactions` — Pulsante «+ Aggiungi» → modale nuova transazione (tipo di default) | admin | `modals/TransactionFormModal.svelte` |
| `transactions/form-modal-sell`<br>`transactions/form-modal-dividend`<br>`transactions/form-modal-deposit`<br>`transactions/form-modal-adjustment`<br>`transactions/form-modal-transfer`<br>`transactions/form-modal-fxconversion`<br>`transactions/form-modal-cash-transfer`<br>`transactions/form-modal-withdrawal`<br>`transactions/form-modal-interest`<br>`transactions/form-modal-fee`<br>`transactions/form-modal-tax` | [🖥](../snapshots/baseline-r1/desktop-it.html#transactions/form-modal-sell) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/form-modal-sell)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#transactions/form-modal-dividend) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/form-modal-dividend)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#transactions/form-modal-deposit) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/form-modal-deposit)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#transactions/form-modal-adjustment) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/form-modal-adjustment)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#transactions/form-modal-transfer) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/form-modal-transfer)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#transactions/form-modal-fxconversion) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/form-modal-fxconversion)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#transactions/form-modal-cash-transfer) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/form-modal-cash-transfer)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#transactions/form-modal-withdrawal) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/form-modal-withdrawal)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#transactions/form-modal-interest) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/form-modal-interest)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#transactions/form-modal-fee) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/form-modal-fee)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#transactions/form-modal-tax) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/form-modal-tax) | `/transactions` — «+ Aggiungi» → menu «Tipo» → scegliere SELL / DIVIDEND / DEPOSIT / ADJUSTMENT / TRANSFER (alto su desktop) / FX_CONVERSION / CASH_TRANSFER / WITHDRAWAL / INTEREST / FEE / TAX | admin | `TransactionFormModal.svelte` |
| `transactions/picker-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#transactions/picker-modal) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/picker-modal) | `/transactions` — Prima riga ⋮ → «Modifica» → chiudere il form → nell'editor multiplo, pulsante «Scegli transazioni» | admin | `modals/TransactionPickerModal.svelte`, `TransactionBulkModal.svelte` |
| `transactions/action-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#transactions/action-modal) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/action-modal) | `/transactions` — Prima riga (fra le prime 30) che nel ⋮ offre «Dividi» → clic su «Dividi» | admin | `modals/TransactionActionModal.svelte` |
| `transactions/clone-flow` | [🖥](../snapshots/baseline-r1/desktop-it.html#transactions/clone-flow) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/clone-flow) | `/transactions` — Prima riga ⋮ → «Clona» → chiudere il form → editor multiplo con il clone | admin | `TransactionBulkModal.svelte` |
| `transactions/promote-merge-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#transactions/promote-merge-modal) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/promote-merge-modal) | `/transactions?types=WITHDRAWAL,DEPOSIT&page_size=50` — Selezionare 2 righe (prelievo + deposito) → toolbar «Promuovi» → modale unione (o conferma) | admin; le righe dipendono dai dati | `modals/PromoteMergeModal.svelte` |
| `transactions/bulk-delete-pair-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#transactions/bulk-delete-pair-modal) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/bulk-delete-pair-modal) | `/transactions` — Riga che contiene «delete-safe» ed «ETH» → ⋮ → «Elimina» → editor con la coppia collegata | admin (riga di seed «delete-safe») | `TransactionBulkModal.svelte` |
| `transactions/bulk-todo-banner` | [🖥](../snapshots/baseline-r1/desktop-it.html#transactions/bulk-todo-banner) [📱](../snapshots/baseline-r1/mobile-it.html#transactions/bulk-todo-banner) | `/transactions` — Importa → seleziona l'estratto conto «Demo Bank» → analizza → revisione → «Importa» → nell'editor espandere il banner «da fare» → clic sull'ultima voce (riga evidenziata) | account usa-e-getta. **MOCK**: le voci «da fare» sono iniettate nella risposta del parse | `TransactionBulkModal.svelte` |

**Cosa guardare** (spunti dall'analisi, da confermare a schermo):
- Tabella: `DataTable` ha un proprio sistema di colori nei `<style>` (circa 140 righe di hex) (P8): intestazione, righe alternate, hover, selezione, filtri.
- Celle importo con bordo verde o rosso di coerenza del segno, senza variante scura (`CompactCashCell.svelte:200`).
- Modali (form, editor multiplo, azioni, promozione): sono le più dense di classi colore; controllare la coerenza di bottoni e avvisi.
- Non esiste una palette per tipo di transazione (acquisto, vendita, dividendo…): decidere se serve.

**✏️ Note — transactions**
- [ ] `transactions/list` — 
- [ ] `transactions/form-modal` — 
- [ ] `transactions/form-modal-sell` — 
- [ ] `transactions/form-modal-dividend` — 
- [ ] `transactions/form-modal-deposit` — 
- [ ] `transactions/form-modal-adjustment` — 
- [ ] `transactions/form-modal-transfer` — 
- [ ] `transactions/form-modal-fxconversion` — 
- [ ] `transactions/form-modal-cash-transfer` — 
- [ ] `transactions/form-modal-withdrawal` — 
- [ ] `transactions/form-modal-interest` — 
- [ ] `transactions/form-modal-fee` — 
- [ ] `transactions/form-modal-tax` — 
- [ ] `transactions/picker-modal` — 
- [ ] `transactions/action-modal` — 
- [ ] `transactions/clone-flow` — 
- [ ] `transactions/promote-merge-modal` — 
- [ ] `transactions/bulk-delete-pair-modal` — 
- [ ] `transactions/bulk-todo-banner` — 
- ✏️ Note generali sull'area:

### 5.10 Broker e importazioni — `brokers` (34 schermate)

| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |
|---|---|---|---|---|
| `brokers/list` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/list) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/list) | `/brokers` — Menu → Broker (alto su desktop) | admin | `routes/(app)/brokers/+page.svelte`, `brokers/BrokerCard.svelte` |
| `brokers/detail` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/detail) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/detail) | `/brokers/[id]` — Broker → card «Interactive Brokers» → scheda Panoramica | admin | `routes/(app)/brokers/[id]/+page.svelte` |
| `brokers/edit-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/edit-modal) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/edit-modal) | `/brokers/[id]` — Prima card broker → pulsante «Modifica» | admin (primo broker in lista) | `brokers/BrokerModal.svelte` |
| `brokers/sharing-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/sharing-modal) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/sharing-modal) | `/brokers` — Card «Coinbase» → icona condividi | admin | `brokers/BrokerSharingModal.svelte` |
| `brokers/info-tab` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/info-tab) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/info-tab) | `/brokers/[id]` — Card «Coinbase» → scheda «Info» | admin | `brokers/[id]/+page.svelte` |
| `brokers/positions-holdings-table`<br>`brokers/positions-holdings-map`<br>`brokers/positions-performance-table`<br>`brokers/positions-performance-map` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/positions-holdings-table) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/positions-holdings-table)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#brokers/positions-holdings-map) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/positions-holdings-map)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#brokers/positions-performance-table) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/positions-performance-table)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#brokers/positions-performance-map) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/positions-performance-map) | `/brokers/[id]` (Coinbase) — Coinbase → periodo 1A → scheda «Posizioni» → Detenute/Performance × Tabella/Mappa | admin LIVE | `dashboard/PositionsPanel.svelte`, `ExposureTable.svelte`, `ExposureTreemap.svelte`, `ContributionTable.svelte` |
| `brokers/fifo-lots-panel`<br>`brokers/fifo-lots-wac-chart`<br>`brokers/fifo-lots-gantt-chart`<br>`brokers/fifo-lots-table`<br>`brokers/fifo-lots-comparison-chart`<br>`brokers/fifo-lots-comparison-chart-return`<br>`brokers/fifo-lots-custody-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/fifo-lots-panel) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/fifo-lots-panel)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#brokers/fifo-lots-wac-chart) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/fifo-lots-wac-chart)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#brokers/fifo-lots-gantt-chart) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/fifo-lots-gantt-chart)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#brokers/fifo-lots-table) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/fifo-lots-table)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#brokers/fifo-lots-comparison-chart) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/fifo-lots-comparison-chart)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#brokers/fifo-lots-comparison-chart-return) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/fifo-lots-comparison-chart-return)<br>[🖥](../snapshots/baseline-r1/desktop-it.html#brokers/fifo-lots-custody-modal) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/fifo-lots-custody-modal) | `/brokers/[id]` (Coinbase) — Coinbase → periodo Max → Posizioni → Detenute/Tabella → prima riga ⋮ → «Analizza lotti» → stessi passi della dashboard | admin LIVE | `lots/LotsAnalysisPanel.svelte` + grafici dei lotti |
| `brokers/transactions-tab` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/transactions-tab) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/transactions-tab) | `/brokers/[id]` — Prima card broker → scheda «Transazioni» | admin | `brokers/[id]/+page.svelte` |
| `brokers/import-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-modal) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-modal) | `/brokers/[id]` — Scheda Transazioni → «Storico importazioni» | admin | `brokers/BrokerImportFilesModal.svelte` |
| `brokers/import-wizard-step1` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-wizard-step1) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-wizard-step1) | `/transactions` — Transazioni → «Importa» → passo 1 | admin | `modals/ImportWizardModal.svelte` |
| `brokers/import-wizard-step2` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-wizard-step2) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-wizard-step2) | `/transactions` — Importa → «Avanti» → passo 2 (scelta file) | admin | `ImportWizardModal.svelte` |
| `brokers/import-wizard-step3` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-wizard-step3) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-wizard-step3) | `/transactions` — Passo 2 → spuntare `generic_simple.csv` → «Analizza» | admin | `ImportWizardModal.svelte` |
| `brokers/import-wizard-step4-resolution` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-wizard-step4-resolution) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-wizard-step4-resolution) | `/transactions` — Passo 3 → «Continua» (confermare l'avviso) → passo 4 | admin | `ImportWizardModal.svelte` |
| `brokers/import-wizard-duplicate` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-wizard-duplicate) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-wizard-duplicate) | `/transactions` — Come sopra, tabella del passo 4 centrata | admin | `ImportWizardModal.svelte` |
| `brokers/import-bulk-staging` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-bulk-staging) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-bulk-staging) | `/transactions` — Prima riga ⋮ → «Modifica» → chiudere il form → editor multiplo | admin | `TransactionBulkModal.svelte` |
| `brokers/import-wizard-assets-step` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-wizard-assets-step) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-wizard-assets-step) | `/transactions` — Importa → caricare `e2e/assets/demo_credit_agricole_titoli.csv` + `demo_credit_agricole_conto.csv` → broker «Interactive Brokers» → Avanti → Analizza → Continua → passo «Asset» | admin (file caricati e poi eliminati) | `ImportWizardModal.svelte` |
| `brokers/import-wizard-fix-step` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-wizard-fix-step) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-wizard-fix-step) | idem — Confermare tutti gli asset → Continua → passo «Correzioni» | idem | idem |
| `brokers/import-wizard-duplicates-step` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-wizard-duplicates-step) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-wizard-duplicates-step) | idem — Accetta tutto → Continua → passo «Duplicati» → priorità file visibile → primo livello espanso | idem | idem |
| `brokers/import-nway-compare` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-nway-compare) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-nway-compare) | idem — Primo gruppo duplicati → «Confronta» | idem | `modals/TransactionCompareModal.svelte` |
| `brokers/import-report-set-card` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-report-set-card) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-report-set-card) | `/transactions` — Importa → «Seleziona file» → pannello «Danske Bank» → spuntare il set (custody + cash) → espandere la card | account usa-e-getta + file campione Danske caricati via API | `transactions/import/ReportSetCard.svelte` |
| `brokers/import-report-set-read-as` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-report-set-read-as) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-report-set-read-as) | idem — Card del set → menu «Leggi come» aperto | idem | `ReportSetCard.svelte` |
| `brokers/import-report-set-file-menu` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-report-set-file-menu) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-report-set-file-menu) | idem — Riga «cash» del set → ⋮ (Anteprima / Rimuovi dal set / Elimina) | idem | `ReportSetCard.svelte` |
| `brokers/import-report-set-missing` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-report-set-missing) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-report-set-missing) | idem — Set con il solo custody → card che segnala l'export cash mancante | idem | `ReportSetCard.svelte` |
| `brokers/import-report-set-pairing` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-report-set-pairing) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-report-set-pairing) | idem — Set «gap» (2 custody + cash) → Analizza → riga del set ⋮ → «Vedi dettaglio» → sezione abbinamento | idem | `modals/ParseDetailModal.svelte` |
| `brokers/import-wizard-gapfix-step` | [🖥](../snapshots/baseline-r1/desktop-it.html#brokers/import-wizard-gapfix-step) [📱](../snapshots/baseline-r1/mobile-it.html#brokers/import-wizard-gapfix-step) | idem — Revisione → tenere solo le righe di cassa → «Importa» → passo «Allinea con la banca» | idem | `import/GapFixStep.svelte` |

**Cosa guardare** (spunti dall'analisi, da confermare a schermo):
- Card broker: guadagno smeraldo, perdita `red-600` (altrove `red-500`) (P4).
- Colori dei broker generati dalla posizione in lista, usati in badge e grafici dei lotti (P6).
- Wizard di importazione: il file con più colori dell'app (527 classi) e una classe inesistente `slate-750`, il cui hover non fa nulla (P3).
- Storico importazioni (`BrokerImportFilesModal`) e modale di mancata corrispondenza con hex propri (P8).
- Card dei set di report: «completo» in `green`, mentre altrove il successo è smeraldo (P4).

**✏️ Note — brokers**
- [ ] `brokers/list` — 
- [ ] `brokers/detail` — 
- [ ] `brokers/edit-modal` — 
- [ ] `brokers/sharing-modal` — 
- [ ] `brokers/info-tab` — 
- [ ] `brokers/positions-holdings-table` — 
- [ ] `brokers/positions-holdings-map` — 
- [ ] `brokers/positions-performance-table` — 
- [ ] `brokers/positions-performance-map` — 
- [ ] `brokers/fifo-lots-panel` — 
- [ ] `brokers/fifo-lots-wac-chart` — 
- [ ] `brokers/fifo-lots-gantt-chart` — 
- [ ] `brokers/fifo-lots-table` — 
- [ ] `brokers/fifo-lots-comparison-chart` — 
- [ ] `brokers/fifo-lots-comparison-chart-return` — 
- [ ] `brokers/fifo-lots-custody-modal` — 
- [ ] `brokers/transactions-tab` — 
- [ ] `brokers/import-modal` — 
- [ ] `brokers/import-wizard-step1` — 
- [ ] `brokers/import-wizard-step2` — 
- [ ] `brokers/import-wizard-step3` — 
- [ ] `brokers/import-wizard-step4-resolution` — 
- [ ] `brokers/import-wizard-duplicate` — 
- [ ] `brokers/import-bulk-staging` — 
- [ ] `brokers/import-wizard-assets-step` — 
- [ ] `brokers/import-wizard-fix-step` — 
- [ ] `brokers/import-wizard-duplicates-step` — 
- [ ] `brokers/import-nway-compare` — 
- [ ] `brokers/import-report-set-card` — 
- [ ] `brokers/import-report-set-read-as` — 
- [ ] `brokers/import-report-set-file-menu` — 
- [ ] `brokers/import-report-set-missing` — 
- [ ] `brokers/import-report-set-pairing` — 
- [ ] `brokers/import-wizard-gapfix-step` — 
- ✏️ Note generali sull'area:

### 5.11 Immagini e upload — `media` (3 schermate)

| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |
|---|---|---|---|---|
| `media/image-edit-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#media/image-edit-modal) [📱](../snapshots/baseline-r1/mobile-it.html#media/image-edit-modal) | `/files` — File → Risorse statiche → «Carica» → scegliere un'immagine (`static/icons/transactions/buy.png`) → icona ✏️ modifica → vista ritaglio | admin | `ui/media/ImageEditModal.svelte`, `ui/media/FileUploader.svelte` |
| `media/asset-picker-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#media/asset-picker-modal) [📱](../snapshots/baseline-r1/mobile-it.html#media/asset-picker-modal) | `/brokers/[id]` — Prima card broker → «Modifica» → clic sull'icona del broker → selettore immagini | admin | `ui/media/AssetPickerModal.svelte`, `BrokerModal.svelte` |
| `media/file-uploader-empty` | [🖥](../snapshots/baseline-r1/desktop-it.html#media/file-uploader-empty) [📱](../snapshots/baseline-r1/mobile-it.html#media/file-uploader-empty) | `/files` — Risorse statiche → «Carica» (nessun file scelto) | admin | `FileUploader.svelte` |

**Cosa guardare** (spunti dall'analisi, da confermare a schermo):
- Modali immagini (modifica, selettore, upload): sistema CSS parallelo con hex propri (P8).
- Testo di errore inline `#dc2626` senza variante scura (`AssetPickerModal.svelte:265`).

**✏️ Note — media**
- [ ] `media/image-edit-modal` — 
- [ ] `media/asset-picker-modal` — 
- [ ] `media/file-uploader-empty` — 
- ✏️ Note generali sull'area:

### 5.12 Cambi (FX) — `fx` (13 schermate)

| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |
|---|---|---|---|---|
| `fx/list` | [🖥](../snapshots/baseline-r1/desktop-it.html#fx/list) [📱](../snapshots/baseline-r1/mobile-it.html#fx/list) | `/fx` — Menu → FX → periodo 1A | admin; tassi del DB, poll live da fixture | `routes/(app)/fx/+page.svelte`, `fx/FxCard.svelte` |
| `fx/list-table` | [🖥](../snapshots/baseline-r1/desktop-it.html#fx/list-table) [📱](../snapshots/baseline-r1/mobile-it.html#fx/list-table) | `/fx` — FX → vista «Lista» | admin | `fx/+page.svelte` |
| `fx/list-filtered` | [🖥](../snapshots/baseline-r1/desktop-it.html#fx/list-filtered) [📱](../snapshots/baseline-r1/mobile-it.html#fx/list-filtered) | `/fx` — FX → filtro valuta → «EUR» | admin | `fx/+page.svelte` |
| `fx/add-pair-routes` | [🖥](../snapshots/baseline-r1/desktop-it.html#fx/add-pair-routes) [📱](../snapshots/baseline-r1/mobile-it.html#fx/add-pair-routes) | `/fx` — «+ Aggiungi coppia» → USD / CHF → «Aggiungi percorso» → sezione diretti (scrollare in fondo) | admin; catalogo provider da fixture | `fx/FxPairAddModal.svelte` |
| `fx/add-pair-chain` | [🖥](../snapshots/baseline-r1/desktop-it.html#fx/add-pair-chain) [📱](../snapshots/baseline-r1/mobile-it.html#fx/add-pair-chain) | `/fx` — Aggiungi coppia → NOK / CHF → Aggiungi percorso → espandere il gruppo catena → scegliere la prima catena | admin | `FxPairAddModal.svelte` |
| `fx/sync-progress` | [🖥](../snapshots/baseline-r1/desktop-it.html#fx/sync-progress) [📱](../snapshots/baseline-r1/mobile-it.html#fx/sync-progress) | `/fx` — Pulsante «Sincronizza tutto» → modale di avanzamento | admin; **sync bloccato** dalla guardia offline (lo stato mostrato può differire, ?) | `fx/+page.svelte` |
| `fx/detail-chart` | [🖥](../snapshots/baseline-r1/desktop-it.html#fx/detail-chart) [📱](../snapshots/baseline-r1/mobile-it.html#fx/detail-chart) | `/fx/EUR-USD` — FX → card «EUR/USD» → periodo 1A | admin | `routes/(app)/fx/[pair]/+page.svelte` |
| `fx/detail-signals` | [🖥](../snapshots/baseline-r1/desktop-it.html#fx/detail-signals) [📱](../snapshots/baseline-r1/mobile-it.html#fx/detail-signals) | `/fx/EUR-USD` — Dettaglio → «Segnali» | admin | `fx/[pair]/+page.svelte` |
| `fx/detail-measures` | [🖥](../snapshots/baseline-r1/desktop-it.html#fx/detail-measures) [📱](../snapshots/baseline-r1/mobile-it.html#fx/detail-measures) | `/fx/EUR-USD` — Dettaglio → «Misure» | admin | idem |
| `fx/detail-editor` | [🖥](../snapshots/baseline-r1/desktop-it.html#fx/detail-editor) [📱](../snapshots/baseline-r1/mobile-it.html#fx/detail-editor) | `/fx/EUR-USD` — Dettaglio → «Modifica dati» | admin | `fx/FxDataEditorSection.svelte`, `ui/data-editor/DataEditor.svelte` |
| `fx/detail-csv-import` | [🖥](../snapshots/baseline-r1/desktop-it.html#fx/detail-csv-import) [📱](../snapshots/baseline-r1/mobile-it.html#fx/detail-csv-import) | `/fx/EUR-USD` — Modifica dati → «Importa» | admin | `ui/data-editor/DataImportModal.svelte` |
| `fx/chart-settings` | [🖥](../snapshots/baseline-r1/desktop-it.html#fx/chart-settings) [📱](../snapshots/baseline-r1/mobile-it.html#fx/chart-settings) | `/fx` — Pagina FX → ⚙️ impostazioni grafico | admin | `charts/ChartSettingsModal.svelte` |
| `fx/provider-config` | [🖥](../snapshots/baseline-r1/desktop-it.html#fx/provider-config) [📱](../snapshots/baseline-r1/mobile-it.html#fx/provider-config) | `/fx/EUR-USD` — Dettaglio → pulsante «Provider» → modale coppia/provider | admin | `FxPairAddModal.svelte` |

**Cosa guardare** (spunti dall'analisi, da confermare a schermo):
- Badge provider: due schemi diversi (`getProviderColor` in HSL e `PROVIDER_COLORS` Tailwind); MANUAL è rosso nel primo e ambra nel secondo (P4).
- Card e tabella: variazioni smeraldo e rosso. La linea del grafico sopra o sotto la base usa `#16a34a` / `#ef4444`, un rosso diverso da quello della dashboard (`#dc2626`) (P4).
- Segnali: palette di default e colori di ruolo uguali in chiaro e scuro, poco contrastati su sfondo scuro (P9).
- Modale di avanzamento della sincronizzazione: stati senza varianti scure.

**✏️ Note — fx**
- [ ] `fx/list` — 
- [ ] `fx/list-table` — 
- [ ] `fx/list-filtered` — 
- [ ] `fx/add-pair-routes` — 
- [ ] `fx/add-pair-chain` — 
- [ ] `fx/sync-progress` — 
- [ ] `fx/detail-chart` — 
- [ ] `fx/detail-signals` — 
- [ ] `fx/detail-measures` — 
- [ ] `fx/detail-editor` — 
- [ ] `fx/detail-csv-import` — 
- [ ] `fx/chart-settings` — 
- [ ] `fx/provider-config` — 
- ✏️ Note generali sull'area:

### 5.13 Asset — `assets` (25 schermate)

Asset predefinito: ricerca «Apple» → prima card (Apple Inc.), route `/assets/[id]`.

| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |
|---|---|---|---|---|
| `assets/list` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/list) [📱](../snapshots/baseline-r1/mobile-it.html#assets/list) | `/assets` — Menu → Asset → periodo 1A | admin | `routes/(app)/assets/+page.svelte`, `assets/AssetCard.svelte` |
| `assets/list-table` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/list-table) [📱](../snapshots/baseline-r1/mobile-it.html#assets/list-table) | `/assets` — Vista «Lista» (alto su desktop) | admin | `assets/+page.svelte` |
| `assets/list-filtered` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/list-filtered) [📱](../snapshots/baseline-r1/mobile-it.html#assets/list-filtered) | `/assets` — Cercare «ETF» | admin | idem |
| `assets/detail-chart` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-chart) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-chart) | `/assets/[id]` — Cercare «Apple» → card → periodo 1A | admin | `routes/(app)/assets/[id]/+page.svelte` |
| `assets/detail-chart-candlestick` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-chart-candlestick) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-chart-candlestick) | idem — Grafico → tipo «Candele» | admin | idem |
| `assets/detail-chart-rolling-return` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-chart-rolling-return) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-chart-rolling-return) | idem — Periodo 1S → «Rendimento a calendario/rolling» → finestra 1A → Segnali → confronto con asset «S&P 500» | admin | idem |
| `assets/detail-signals` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-signals) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-signals) | idem — Periodo 1A → aprire «Segnali» | admin | idem |
| `assets/detail-signals-ema` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-signals-ema) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-signals-ema) | idem — Segnali → selettore indicatori → gruppo Trend → «EMA» | admin | idem |
| `assets/detail-signals-rsi` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-signals-rsi) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-signals-rsi) | idem — Momentum → «RSI» | admin | idem |
| `assets/detail-signals-macd` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-signals-macd) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-signals-macd) | idem — Momentum → «MACD» | admin | idem |
| `assets/detail-signals-bollinger` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-signals-bollinger) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-signals-bollinger) | idem — Volatilità → «Bollinger» | admin | idem |
| `assets/detail-signals-tree` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-signals-tree) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-signals-tree) | idem — Segnali → selettore indicatori aperto (gruppo Trend) | admin | idem |
| `assets/detail-signals-drawdown` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-signals-drawdown) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-signals-drawdown) | idem — Rischio → «Drawdown», parametro «storia completa» visibile | admin | idem |
| `assets/chart-settings` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/chart-settings) [📱](../snapshots/baseline-r1/mobile-it.html#assets/chart-settings) | `/assets` — Lista asset → ⚙️ impostazioni grafico | admin | `charts/ChartSettingsModal.svelte` |
| `assets/detail-events` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-events) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-events) | `/assets/[id]` — Apple → periodo Max → passare il mouse sull'evento 💰 a metà grafico → popover dividendo | admin. **MOCK**: 240 giorni di prezzi sintetici + dividendo finto | `assets/[id]/+page.svelte` |
| `assets/detail-measures` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-measures) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-measures) | idem — Apple 1A → aprire «Misure» | admin | idem |
| `assets/detail-measures-active` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-measures-active) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-measures-active) | idem — «+ Aggiungi misura» | admin | idem |
| `assets/detail-classification` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-classification) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-classification) | idem — Apple → «Metadati/Classificazione» | admin | idem |
| `assets/detail-editor` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/detail-editor) [📱](../snapshots/baseline-r1/mobile-it.html#assets/detail-editor) | idem — Apple → «Modifica dati» | admin | `assets/AssetDataEditorSection.svelte`, `DataEditor.svelte` |
| `assets/create-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/create-modal) [📱](../snapshots/baseline-r1/mobile-it.html#assets/create-modal) | `/assets` — «+ Aggiungi asset» | admin | `assets/AssetModal.svelte` |
| `assets/type-picker-open` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/type-picker-open) [📱](../snapshots/baseline-r1/mobile-it.html#assets/type-picker-open) | `/assets` — Aggiungi asset → menu «Tipo» → espandere la famiglia ETF | admin | `AssetModal.svelte` |
| `assets/create-provider-compare` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/create-provider-compare) [📱](../snapshots/baseline-r1/mobile-it.html#assets/create-provider-compare) | `/assets` — Aggiungi asset → «Altre info» → aggiungere un settore → Cerca online (yfinance) con ISIN `IE000NWGE006` → risultato → modale di confronto | admin. **MOCK**: fondo inventato «Northwind Global Equity UCITS ETF» | `assets/ProviderComparisonModal.svelte`, `AssetModal.svelte` |
| `assets/distribution-editor-sector` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/distribution-editor-sector) [📱](../snapshots/baseline-r1/mobile-it.html#assets/distribution-editor-sector) | `/assets/[id]` (Tesla) — Cercare «Tesla» → card → «Modifica» → «Altre info» → editor settori | admin | `ui/input/DistributionEditor.svelte`, `AssetModal.svelte` |
| `assets/distribution-editor-geographic` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/distribution-editor-geographic) [📱](../snapshots/baseline-r1/mobile-it.html#assets/distribution-editor-geographic) | idem — Scorrere all'editor geografico | admin | idem |
| `assets/create-wizard-modal` | [🖥](../snapshots/baseline-r1/desktop-it.html#assets/create-wizard-modal) [📱](../snapshots/baseline-r1/mobile-it.html#assets/create-wizard-modal) | `/transactions` — Importa → Avanti → `generic_simple.csv` → Analizza → Continua → passo 4: selettore asset → «Crea nuovo» | admin | `AssetModal.svelte`, `ImportWizardModal.svelte` |

**Cosa guardare** (spunti dall'analisi, da confermare a schermo):
- Badge del tipo di asset: 13 tinte diverse (STOCK blu, ETF smeraldo, BOND ambra, CRYPTO viola…) (`assetTypes.ts:109`).
- Grafico: candele `#16a34a` / `#ef4444`; il Δ nel tooltip usa un altro verde (`#10b981`) (P4).
- Segnali (EMA, RSI, MACD, Bollinger, drawdown): colori scelti per distanza di tinta; ruoli positivo e negativo fissi `#16a34a` / `#dc2626`; misura arancio `#f97316`; uguali in entrambi i temi (P9).
- Dettaglio asset: hover con la classe inesistente `slate-750` (`assets/[id]/+page.svelte:3361`) (P3).
- Modale di creazione e modifica, editor delle distribuzioni (settori, geografia): colori delle barre.

**✏️ Note — assets**
- [ ] `assets/list` — 
- [ ] `assets/list-table` — 
- [ ] `assets/list-filtered` — 
- [ ] `assets/detail-chart` — 
- [ ] `assets/detail-chart-candlestick` — 
- [ ] `assets/detail-chart-rolling-return` — 
- [ ] `assets/detail-signals` — 
- [ ] `assets/detail-signals-ema` — 
- [ ] `assets/detail-signals-rsi` — 
- [ ] `assets/detail-signals-macd` — 
- [ ] `assets/detail-signals-bollinger` — 
- [ ] `assets/detail-signals-tree` — 
- [ ] `assets/detail-signals-drawdown` — 
- [ ] `assets/chart-settings` — 
- [ ] `assets/detail-events` — 
- [ ] `assets/detail-measures` — 
- [ ] `assets/detail-measures-active` — 
- [ ] `assets/detail-classification` — 
- [ ] `assets/detail-editor` — 
- [ ] `assets/create-modal` — 
- [ ] `assets/type-picker-open` — 
- [ ] `assets/create-provider-compare` — 
- [ ] `assets/distribution-editor-sector` — 
- [ ] `assets/distribution-editor-geographic` — 
- [ ] `assets/create-wizard-modal` — 
- ✏️ Note generali sull'area:

### 5.14 Laboratorio di rischio — `risk` (8 schermate)

Laboratorio di rischio:
- Route: `/assets?tab=correlation`, periodo 1A.
- Selezione: Apple Inc., RE Loan Milano, RE Loan Roma, Bitcoin, Ethereum.
- Benchmark: S&P 500.
- Selezione e benchmark sono preimpostati in localStorage: dal vivo vanno aggiunti a mano.

| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |
|---|---|---|---|---|
| `risk/lab-correlation` | [🖥](../snapshots/baseline-r1/desktop-it.html#risk/lab-correlation) [📱](../snapshots/baseline-r1/mobile-it.html#risk/lab-correlation) | `/assets?tab=correlation` — Asset → scheda «Correlazione/Rischio» → selezionare i 5 asset → sezione correlazione | admin LIVE | `risk/AssetSetRiskPanel.svelte`, `risk/RiskAnalysisPanel.svelte` |
| `risk/lab-hurt-table` | [🖥](../snapshots/baseline-r1/desktop-it.html#risk/lab-hurt-table) [📱](../snapshots/baseline-r1/mobile-it.html#risk/lab-hurt-table) | idem — Sezione tabella delle perdite | admin | `AssetSetRiskPanel.svelte` |
| `risk/lab-risk-return` | [🖥](../snapshots/baseline-r1/desktop-it.html#risk/lab-risk-return) [📱](../snapshots/baseline-r1/mobile-it.html#risk/lab-risk-return) | idem — Sezione rischio/rendimento con benchmark S&P 500 (alto su desktop) | admin | idem |
| `risk/lab-asset-picker` | [🖥](../snapshots/baseline-r1/desktop-it.html#risk/lab-asset-picker) [📱](../snapshots/baseline-r1/mobile-it.html#risk/lab-asset-picker) | idem — «+» → aggiungere Microsoft e Tesla; NVIDIA e «Test KRW Stock» risultano bloccati | admin | idem |
| `risk/lab-benchmark-picker` | [🖥](../snapshots/baseline-r1/desktop-it.html#risk/lab-benchmark-picker) [📱](../snapshots/baseline-r1/mobile-it.html#risk/lab-benchmark-picker) | idem — Sezione rischio/rendimento → selettore benchmark aperto (elenco non utilizzabili visibile) | admin | idem |
| `risk/lab-notice` | [🖥](../snapshots/baseline-r1/desktop-it.html#risk/lab-notice) [📱](../snapshots/baseline-r1/mobile-it.html#risk/lab-notice) | idem — Senza benchmark → avviso di risultati parziali (prezzo vecchio su RE Loan Roma) | admin. **MOCK** (prezzo vecchio iniettato) | idem |
| `risk/lab-replay` | [🖥](../snapshots/baseline-r1/desktop-it.html#risk/lab-replay) [📱](../snapshots/baseline-r1/mobile-it.html#risk/lab-replay) | idem — Sezione «Replay storico» → aprire → «Esegui» → riquadro asset esclusi + tornado | admin. **MOCK** (RE Loan Roma escluso, iniettato) | idem |
| `risk/whatif-simulation` | [🖥](../snapshots/baseline-r1/desktop-it.html#risk/whatif-simulation) [📱](../snapshots/baseline-r1/mobile-it.html#risk/whatif-simulation) | `/dashboard` — Periodo 1A → scheda «Rischio» → «E se…?» → «+ Simulazione» → percorsi 2048, seed 123456 → «Esegui» | admin LIVE | `risk/levels/l4/L4Simulation.svelte`, `RiskLevelsPanel.svelte` |

**Cosa guardare** (spunti dall'analisi, da confermare a schermo):
- Correlazione rosso↔blu: qui il rosso significa correlazione negativa, non perdita. Enfasi neutra sulla cella selezionata (decisione «hue-free», settembre 2026).
- Rischio/rendimento: portafoglio sky, benchmark ambra, punto selezionato verde (`scatterChartHelpers.ts`).
- Diversificazione: colori invertiti, valore alto = rosso (`L2Diversification.svelte:312`).
- Pannello di analisi: barre rosse e blu senza varianti scure (`RiskAnalysisPanel.svelte:682`).

**✏️ Note — risk**
- [ ] `risk/lab-correlation` — 
- [ ] `risk/lab-hurt-table` — 
- [ ] `risk/lab-risk-return` — 
- [ ] `risk/lab-asset-picker` — 
- [ ] `risk/lab-benchmark-picker` — 
- [ ] `risk/lab-notice` — 
- [ ] `risk/lab-replay` — 
- [ ] `risk/whatif-simulation` — 
- ✏️ Note generali sull'area:

## 6. Note generali e idee
✏️

## 7. Registro dei giri di review
| Data | Giro | Partecipanti | Cosa si è deciso |
|---|---|---|---|
| | 1 — ruoli | | |

