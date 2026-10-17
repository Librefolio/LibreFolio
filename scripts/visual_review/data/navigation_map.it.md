# Mappa degli screenshot della gallery LibreFolio (`frontend/e2e/gallery.spec.ts`)

> **Provenance.** Generated on 2026-10-14 by reading `frontend/e2e/gallery.spec.ts` (+ fixtures) at commit
> `27228466c`: one table per gallery category, first column = shot ids (`category/name`; a row may list several,
> abbreviating the next ones as `, -suffix`). Consumed by `scripts/visual_review/navmap.py`. Shots added to the
> gallery later are still published, with «?» as navigation, until this file is updated (by hand, or by asking an
> agent to re-derive it from the spec). Keep every category heading as a single word: `## <category>`.

## Fatti generali

- **Totale:** 177 shot `category/name` distinti. È più dei ~132 che ti aspettavi; il conteggio per categoria è in fondo. Ogni shot è salvato come `<viewport>/<lang>/<theme>/<category>/<name>.png` sotto `mkdocs_src/docs/gallery/`.
- **Viewport** (`frontend/playwright.config.ts` 123-142):
  - `desktop`: Desktop Chrome, 1280×720.
  - `mobile`: iPhone 14 Pro Max (430×932, con touch, motore Chromium).
  - **Attenzione, "tall shots":** su desktop molti shot allungano temporaneamente l'altezza della finestra per far entrare tutto il blocco (`extendScreenToBlock`, `fitScreenToDialog`, `fitViewportToBlock`, `fitScreenToPacProof`, `fitScreenToCompareDialog` in `fixtures/galleryTallShots.ts` e simili). Il PNG desktop può quindi essere più alto di 720 px. Dal vivo bisogna scorrere.
- **Lingue e temi:** ogni test gira su en, it, fr, es × light, dark. Fa eccezione `dashboard/menu-open`, che esiste solo su mobile (`test.skip` alla riga 1260). Le guardie sul viewport cambiano solo l'inquadratura, non saltano nessuno shot.
- **Come si cambia il tema:** pulsante sole/luna nell'header (`theme-toggle`, `lib/components/ui/ThemeToggle.svelte`), con `setTheme` (spec ~214). Alcuni test invece scrivono `librefolio-theme` in localStorage e ricaricano: auth/update-available-modal, support/donation-popup e gli shot onboarding.
- **Come si cambia la lingua:** selettore lingua nell'header (`language-selector-button`, `lib/components/layout/LanguageSelector.svelte`) → voce di menu «English / Italiano / Français / Español» (`fixtures/auth-helpers.ts` 116-129). In più cambia la locale del browser (`setBrowserLocale`) per date e numeri.
- **CSS iniettato e altri ritocchi** (il live può differire leggermente):
  - `freezeAnimations` (spec ~200): `animation-play-state: paused; animation-delay: -0.1s; transition-duration: 0s` su tutti gli elementi. Lo sfondo animato resta fermo al 10%.
  - Context con `reducedMotion: 'reduce'`: niente marquee sui testi lunghi, niente anello pulsante del coachmark, spinner fermi, niente flash dei prezzi.
  - Puntatore "parcheggiato" (`parkPointer`), quindi nessun hover involontario.
  - Gallery offline in ogni test (`guardGalleryOffline`, `hideGalleryTempData`, `keepFaviconImagesLoading`):
    - il poll dei prezzi live e il catalogo provider rispondono da fixture;
    - sync e probe sono bloccati;
    - broker e file temporanei degli altri test sono nascosti;
    - le favicon sono riscritte con una query string.
- **Utenti:**
  - Quasi tutto usa **e2e_test_admin** (`TEST_ADMIN`). **e2e_test_user non viene mai usato.**
  - `dashboard/empty-state` usa **e2e_test_empty**.
  - Onboarding e Danske Bank usano **account usa-e-getta** registrati via API, poi cancellati.
  - **MOCK** = dati finti o replay, non riproducibili tali e quali con il DB di test normale.
  - **Replay `dashboard-report.json`** = la risposta di `/api/v1/portfolio/report` sostituita dal file `frontend/e2e/dashboard-report.json`, con le date spostate a oggi.
- **Prerequisito:** `./dev.py db populate --force`.
- **Nota sulle schede:** gli id `dashboard-tab-posizioni`, `dashboard-tab-transazioni` e `dashboard-tab-risk` corrispondono alle schede «Posizioni», «Transazioni» e «Rischio». Le etichette italiane del menu laterale non le ho verificate una per una; ho usato il nome della pagina.

---

## auth

| Shot | Viewport/lingue | Route | Come arrivarci (IT) | Utente / dati | Componenti |
|---|---|---|---|---|---|
| auth/01-login | entrambi / 4 | `/` | Aprire l'app da disconnessi: pagina di login | nessuno | `routes/+page.svelte`, `lib/features/auth/LoginCard.svelte` |
| auth/02-register-empty | entrambi / 4 | `/` | Login → link «Registrati» → modale di registrazione vuota | nessuno | `lib/features/auth/RegisterCard.svelte` |
| auth/03-register-filled | entrambi / 4 | `/` | Come sopra, poi compilare utente `demo_user`, email `demo@example.com`, password `MyStr0ng!Pass`. Mostra il misuratore di robustezza | nessuno (solo input) | `lib/features/auth/RegisterCard.svelte` |
| auth/update-available-modal | entrambi / 4 | `/dashboard` (dopo il login) | Accedere da admin: si apre da solo il popup «Aggiornamento disponibile v99.9.0» | admin. **MOCK**: release finta in localStorage e `container-image-status` intercettato | `lib/features/update-check/UpdateAvailableModal.svelte` |

## onboarding

| Shot | Viewport/lingue | Route | Come arrivarci (IT) | Utente / dati | Componenti |
|---|---|---|---|---|---|
| onboarding/welcome-setup | entrambi / 4 | `/welcome` | Primo accesso con un account nuovo: pagina di benvenuto con lingua, valuta (precompilata) e avatar con le iniziali | account nuovo usa-e-getta | `features/onboarding/components/WelcomePage.svelte`, `routes/(app)/welcome/+page.svelte` |
| onboarding/core-tour-step | entrambi / 4 | `/dashboard` | Account nuovo → completare il benvenuto → avviare il tour («Inizia») → «Avanti» fino al passo che indica la voce FX. Su mobile il menu laterale è aperto | account nuovo | `OnboardingCoachmark.svelte`, `layout/Sidebar.svelte` |
| onboarding/contextual-guide | entrambi / 4 | `/fx` | Account nuovo con la guida FX attiva → Menu → FX → la guida contestuale appare → «Avanti» (passo «filtri») | account nuovo; le card FX usano dati offline/fixture | `OnboardingCoachmark.svelte`, `routes/(app)/fx/+page.svelte`, `fx/FxCard.svelte` |

## dashboard

Tutti gli shot usano l'utente admin. Dove indicato, i dati vengono dal **REPLAY** `dashboard-report.json` (preset 1A selezionato).

| Shot | Viewport/lingue | Route | Come arrivarci (IT) | Utente / dati | Componenti |
|---|---|---|---|---|---|
| dashboard/kpi-top | entrambi / 4 | `/dashboard` | Menu → Dashboard → periodo «1A» → in cima alla pagina | REPLAY | `routes/(app)/dashboard/+page.svelte`, `dashboard/KpiSection.svelte` |
| dashboard/main | entrambi / 4 | `/dashboard` | Scorrere fino al grafico di crescita → selettore in valuta (€) | REPLAY | `dashboard/GrowthChart.svelte` |
| dashboard/main-pct | entrambi / 4 | `/dashboard` | Grafico di crescita → selettore «%» | REPLAY | `GrowthChart.svelte` |
| dashboard/growth-pnl-candles | entrambi / 4 | `/dashboard` | Grafico di crescita → modalità «P&L» → sotto-modo «Candele» (larghezza candela di default) | REPLAY | `GrowthChart.svelte` |
| dashboard/growth-pnl-income | entrambi / 4 | `/dashboard` | P&L → sotto-modo «Entrate» | REPLAY | `GrowthChart.svelte` |
| dashboard/growth-pnl-line | entrambi / 4 | `/dashboard` | P&L → sotto-modo «Linea» | REPLAY | `GrowthChart.svelte` |
| dashboard/privacy-masked | entrambi / 4 | `/dashboard` | Icona occhio (privacy) nell'header → importi mostrati come «•••»; inquadrata la riga dei KPI | REPLAY | `ui/PrivacyToggle.svelte`, `KpiSection.svelte`, `layout/Header.svelte` |
| dashboard/menu-open | **solo mobile** / 4 | `/dashboard` | Su telefono: icona ☰ in alto → menu laterale aperto | REPLAY | `layout/Sidebar.svelte`, `layout/Header.svelte` |
| dashboard/allocation-type-now | entrambi / 4 | `/dashboard` | Scorrere al pannello Allocazione → scheda «Tipo» → vista «Ora» | REPLAY | `dashboard/AllocationPanel.svelte` |
| dashboard/allocation-type-history | entrambi / 4 | `/dashboard` | Allocazione → «Tipo» → vista «Storico» | REPLAY | `AllocationPanel.svelte` |
| dashboard/allocation-sector-now | entrambi / 4 | `/dashboard` | Allocazione → «Settore» → «Ora» | REPLAY | `AllocationPanel.svelte` |
| dashboard/allocation-sector-history | entrambi / 4 | `/dashboard` | Allocazione → «Settore» → «Storico» | REPLAY | `AllocationPanel.svelte` |
| dashboard/allocation-geo-now | entrambi / 4 | `/dashboard` | Allocazione → «Geografia» → «Ora» | REPLAY | `AllocationPanel.svelte` |
| dashboard/allocation-geo-history | entrambi / 4 | `/dashboard` | Allocazione → «Geografia» → «Storico» | REPLAY | `AllocationPanel.svelte` |
| dashboard/positions-holdings-table | entrambi / 4 | `/dashboard` | Scheda «Posizioni» → «Esposizione/Detenute» → vista «Tabella» (alto su desktop) | REPLAY | `dashboard/PositionsPanel.svelte`, `ExposureTable.svelte` |
| dashboard/positions-holdings-map | entrambi / 4 | `/dashboard` | Posizioni → «Detenute» → vista «Mappa» (treemap) | REPLAY | `PositionsPanel.svelte`, `ExposureTreemap.svelte` |
| dashboard/positions-performance-table | entrambi / 4 | `/dashboard` | Posizioni → «Performance» → «Tabella» | REPLAY | `ContributionTable.svelte` |
| dashboard/positions-performance-map | entrambi / 4 | `/dashboard` | Posizioni → «Performance» → «Mappa» (grafico performance) | REPLAY | `PerformanceChart.svelte` |
| dashboard/fifo-lots-panel | entrambi / 4 | `/dashboard` | Periodo «Max» (o 2A) → Posizioni → Detenute/Tabella → riga «Apple» → menu ⋮ → «Analizza lotti» → pannello in cima | admin, **dati LIVE** (niente replay) | `brokers/lots/LotsAnalysisPanel.svelte` |
| dashboard/fifo-lots-wac-chart | entrambi / 4 | `/dashboard` | Stesso pannello, scorrere al grafico prezzo medio (WAC) | LIVE | `lots/LotWacPriceChart.svelte` |
| dashboard/fifo-lots-gantt-chart | entrambi / 4 | `/dashboard` | Scorrere al Gantt dei lotti | LIVE | `lots/LotGanttChart.svelte` |
| dashboard/fifo-lots-table | entrambi / 4 | `/dashboard` | Scorrere alla tabella unificata dei lotti | LIVE | `lots/UnifiedLotsTable.svelte` |
| dashboard/fifo-lots-comparison-chart | entrambi / 4 | `/dashboard` | Scorrere al grafico di confronto dei lotti | LIVE | `lots/LotComparisonChart.svelte` |
| dashboard/fifo-lots-comparison-chart-return | entrambi / 4 | `/dashboard` | Nel grafico di confronto → modalità «Rendimento» | LIVE | `LotComparisonChart.svelte` |
| dashboard/fifo-lots-custody-modal | entrambi / 4 | `/dashboard` | Tabella lotti → prima riga ⋮ → «Vedi dettagli» → modale custodia | LIVE | `lots/LotCustodyModal.svelte` |
| dashboard/transactions-tab | entrambi / 4 | `/dashboard` | Scheda «Transazioni» della dashboard | REPLAY (lista transazioni probabilmente live, ?) | `dashboard/+page.svelte`, `transactions/TransactionsTable.svelte` |
| dashboard/empty-state | entrambi / 4 | `/dashboard` | Accedere con un account senza dati → Dashboard vuota | **e2e_test_empty** | `dashboard/+page.svelte` |
| dashboard/data-quality-banner | entrambi / 4 | `/dashboard` | Banner «Qualità dati» in alto → espanderlo: prezzi vecchi (Apple, Microsoft) e coppia FX USD-CHF mancante | **MOCK** (issues iniettate nel replay) | `ui/feedback/DataQualityBanner.svelte` |
| dashboard/data-quality-sync-rates | entrambi / 4 | `/dashboard` | Banner espanso → problema «Tassi di cambio mancanti» (EUR-GBP, EUR-USD) con pulsante «Sincronizza tassi» | **MOCK** | `DataQualityBanner.svelte` |
| dashboard/risk-hurt | entrambi / 4 | `/dashboard` | Periodo 1A → scheda «Rischio» → blocco 1 «Quanto può far male?» (card, sott'acqua, istogramma) | admin LIVE (benchmark azzerato in localStorage) | `risk/levels/RiskLevelsPanel.svelte` |
| dashboard/risk-diversification | entrambi / 4 | `/dashboard` | Rischio → blocco 2 «Sono diversificato quanto credo?» | LIVE | `RiskLevelsPanel.svelte` |
| dashboard/risk-paid | entrambi / 4 | `/dashboard` | Rischio → blocco 3 «Sono pagato per questo rischio?» con benchmark «MSCI World Index» | LIVE (benchmark preimpostato in localStorage: sceglierlo a mano) | `RiskLevelsPanel.svelte` |
| dashboard/risk-whatif | entrambi / 4 | `/dashboard` | Rischio → blocco 4 «E se…?» → aprirlo → «+ Replay storico» → preset «Crisi finanziaria globale» → «Esegui» | **MOCK** (finestra della crisi iniettata via route sulla query di rischio) | `risk/levels/l4/L4Replay.svelte`, `RiskLevelsPanel.svelte` |

## security

| Shot | Viewport/lingue | Route | Come arrivarci (IT) | Utente / dati | Componenti |
|---|---|---|---|---|---|
| security/connection-indicator | entrambi / 4 | `http://lf-e2e.lan:<porta>/dashboard` | Aprire l'app da un nome di rete locale (non localhost) → periodo 1A → (mobile: ☰) → clic sull'indicatore di sicurezza della connessione → dettagli aperti, col puntatore sopra | admin + REPLAY. Serve un hostname LAN (regola di risoluzione del browser) | `layout/ConnectionSecurityIndicator.svelte`, `layout/Header.svelte`, `layout/Sidebar.svelte` |

## settings

Tutti con l'utente admin, su `/settings`, entrambi i viewport e 4 lingue.

| Shot | Viewport/lingue | Route | Come arrivarci (IT) | Utente / dati | Componenti |
|---|---|---|---|---|---|
| settings/user-preferences | entrambi / 4 | `/settings` | Menu → Impostazioni → scheda «Preferenze» | admin | `routes/(app)/settings/+page.svelte`, `lib/features/settings/tabs/PreferencesTab.svelte` |
| settings/global-settings | entrambi / 4 | `/settings` | Impostazioni → scheda «Amministrazione/Globali» (alto su desktop) | admin | `lib/features/settings/tabs/GlobalSettingsTab.svelte` |
| settings/about | entrambi / 4 | `/settings` | Impostazioni → scheda «Informazioni» | admin | `lib/features/settings/tabs/AboutTab.svelte` |
| settings/password-modal | entrambi / 4 | `/settings` | Impostazioni → pulsante «Cambia password» | admin | `lib/features/settings/PasswordChangeModal.svelte`, aperta da `ProfileTab.svelte` |
| settings/profile | entrambi / 4 | `/settings` | Impostazioni → scheda «Profilo» (alto su desktop) | admin | `lib/features/settings/tabs/ProfileTab.svelte` |
| settings/scheduler-config | entrambi / 4 | `/settings` | Scheda Globali → se serve, sbloccare il lucchetto 🔒 → pulsante configurazione scheduler | admin | `lib/features/settings/SchedulerConfigModal.svelte`, `GlobalSettingsTab.svelte` |
| settings/scheduler-log | entrambi / 4 | `/settings` | Scheda Globali → clic sulla riga di stato dello scheduler → modale log | admin | `lib/features/settings/SchedulerLogModal.svelte` |
| settings/changelog-modal | entrambi / 4 | `/dashboard` | (mobile: ☰) → clic sul numero di versione in fondo al menu laterale | admin | `layout/ChangelogModal.svelte`, `layout/Sidebar.svelte` |
| settings/changelog-modal-search | entrambi / 4 | `/dashboard` | Nel changelog → cercare «Docker» → clic sul primo risultato | admin | `ChangelogModal.svelte` |
| settings/cache-panel | entrambi / 4 | `/settings` | Globali → sblocca 🔒 → categoria «Memoria» → pannello cache | admin | `lib/features/settings/CachePanel.svelte` |
| settings/about-plugin-diagnostics | entrambi / 4 | `/settings` | Informazioni → espandere «Diagnostica plugin» (alto su desktop) | admin | `AboutTab.svelte` |
| settings/about-tool-diagnostics | entrambi / 4 | `/settings` | Informazioni → «Diagnostica plugin» → sezione strumenti → espandere «Diagnostica strumenti», scorrere in fondo | admin | `AboutTab.svelte` (pannello tool) |
| settings/onboarding-replay | entrambi / 4 | `/settings?tab=preferences` | Preferenze → categoria «Onboarding» (mobile: menu a tendina delle categorie) | admin | `features/onboarding/components/OnboardingReplaySection.svelte` |

## tools

Shot PAC: dati scenario, non scritti nel DB.
- Broker: «Interactive Brokers» e «DEGIRO».
- Asset: Apple Inc., Microsoft Corporation e un asset manuale «Global Bond ETF» a 52.4.
- Fonti: liquidità copiata da DEGIRO (2000 EUR), contributo «PAC» 500 EUR, conto esterno «Northwind Bank» USD 3000 (di cui 1200 usati).
- Commissione DEGIRO: 0.19%, min 1.5, max 18.
- Target: 30/30/40.
- Dettaglio completo in `fixtures/galleryPac.ts` 81-100.

| Shot | Viewport/lingue | Route | Come arrivarci (IT) | Utente / dati | Componenti |
|---|---|---|---|---|---|
| tools/hub | entrambi / 4 | `/tools` | Menu → Strumenti | admin | `features/tools/ToolsHub.svelte` |
| tools/pac-step-liquidity | entrambi / 4 | `/tools/pac_allocator` | Strumenti → card «PAC Allocator» → compilare lo scenario → passo «Liquidità» | admin + bozza digitata | `pac-allocator/planner/PacPlannerTool.svelte`, `shell/StepNav.svelte`, `shell/SummaryPanel.svelte` |
| tools/pac-step-brokers | entrambi / 4 | idem | Passo Broker → editor del broker aperto | idem | `PacPlannerTool.svelte` |
| tools/pac-step-assets | entrambi / 4 | idem | Passo «Asset» | idem | `steps/AssetsStep.svelte` |
| tools/pac-step-routing | entrambi / 4 | idem | Passo «Instradamento» | idem | `PacPlannerTool.svelte` |
| tools/pac-step-review | entrambi / 4 | idem | Target del bond lasciati incompleti → passo «Revisione» (mostra gli avvisi) | idem | `PacPlannerTool.svelte` |
| tools/pac-step-targets | entrambi / 4 | idem | Passo «Obiettivi» | idem | `PacPlannerTool.svelte` |
| tools/pac-result | entrambi / 4 | idem | Bozza completa → «Calcola» → sezione allocazione del risultato | idem (solver locale) | `PacPlannerTool.svelte` |
| tools/pac-result-plan | entrambi / 4 | idem | Risultato → «Piano operativo» | idem | idem |
| tools/pac-result-proof | entrambi / 4 | idem | Risultato → «Prova e solver» | idem | idem |

## support

| Shot | Viewport/lingue | Route | Come arrivarci (IT) | Utente / dati | Componenti |
|---|---|---|---|---|---|
| support/donation-popup | entrambi / 4 | `/dashboard` | Accedere → popup donazione con i pulsanti social (X, Reddit, Facebook, Instagram, TikTok) | admin. **MOCK**: la risposta del login viene forzata a `show_donation_popup=true` | `lib/features/support/DonationPopupModal.svelte` |
| support/social-share-modal | entrambi / 4 | `/settings` | Impostazioni → Informazioni → card supporto → «Reddit» → modale di condivisione, messaggio scrollato in fondo | admin | `lib/features/support/SocialShareModal.svelte`, `AboutTab.svelte` |

## files

| Shot | Viewport/lingue | Route | Come arrivarci (IT) | Utente / dati | Componenti |
|---|---|---|---|---|---|
| files/static-tab | entrambi / 4 | `/files?tab=static` | Menu → File → scheda «Risorse statiche» (alto su desktop) | admin | `routes/(app)/files/+page.svelte`, `files/FilesTable.svelte` |
| files/brim-tab | entrambi / 4 | `/files?tab=brim` | File → scheda «Report broker» | admin | `FilesTable.svelte` |
| files/static-grid | entrambi / 4 | `/files?tab=static` | Risorse statiche → vista «Griglia» | admin | `files/+page.svelte` |
| files/preview-modal-csv | entrambi / 4 | `/files?tab=brim&filename=schwab-export.csv` | Report broker → riga `schwab-export.csv` → anteprima (griglia) | admin | `files/FilePreviewModal.svelte` |
| files/preview-modal-image | entrambi / 4 | `/files?tab=static&filename=men_01.png` | Statiche → `men_01.png` → anteprima | admin | `FilePreviewModal.svelte` |
| files/preview-modal-pdf | entrambi / 4 | `…filename=ebook.pdf` | Statiche → `ebook.pdf` → anteprima (attendere ~4 s che spariscano i controlli pagina) | admin | `FilePreviewModal.svelte` |
| files/preview-modal-markdown | entrambi / 4 | `…filename=preview_markdown_sample.md` | Statiche → quel file → anteprima | admin | `FilePreviewModal.svelte` |
| files/preview-modal-text | entrambi / 4 | `…filename=preview_notes_sample.txt` | Statiche → quel file → anteprima | admin | `FilePreviewModal.svelte` |
| files/brim-report-sets | entrambi / 4 | `/files?tab=brim` | Report broker → badge dei set → filtro colonna «Caricato da» aperto | **account usa-e-getta** con broker «Danske Bank» e 7 file caricati via API | `FilesTable.svelte` |

## transactions

| Shot | Viewport/lingue | Route | Come arrivarci (IT) | Utente / dati | Componenti |
|---|---|---|---|---|---|
| transactions/list | entrambi / 4 | `/transactions` | Menu → Transazioni | admin | `routes/(app)/transactions/+page.svelte`, `transactions/TransactionsTable.svelte` |
| transactions/form-modal | entrambi / 4 | `/transactions` | Pulsante «+ Aggiungi» → modale nuova transazione (tipo di default) | admin | `modals/TransactionFormModal.svelte` |
| transactions/form-modal-sell, -dividend, -deposit, -adjustment, -transfer, -fxconversion, -cash-transfer, -withdrawal, -interest, -fee, -tax (11 shot) | entrambi / 4 | `/transactions` | «+ Aggiungi» → menu «Tipo» → scegliere SELL / DIVIDEND / DEPOSIT / ADJUSTMENT / TRANSFER (alto su desktop) / FX_CONVERSION / CASH_TRANSFER / WITHDRAWAL / INTEREST / FEE / TAX | admin | `TransactionFormModal.svelte` |
| transactions/picker-modal | entrambi / 4 | `/transactions` | Prima riga ⋮ → «Modifica» → chiudere il form → nell'editor multiplo, pulsante «Scegli transazioni» | admin | `modals/TransactionPickerModal.svelte`, `TransactionBulkModal.svelte` |
| transactions/action-modal | entrambi / 4 | `/transactions` | Prima riga (fra le prime 30) che nel ⋮ offre «Dividi» → clic su «Dividi» | admin | `modals/TransactionActionModal.svelte` |
| transactions/clone-flow | entrambi / 4 | `/transactions` | Prima riga ⋮ → «Clona» → chiudere il form → editor multiplo con il clone | admin | `TransactionBulkModal.svelte` |
| transactions/promote-merge-modal | entrambi / 4 | `/transactions?types=WITHDRAWAL,DEPOSIT&page_size=50` | Selezionare 2 righe (prelievo + deposito) → toolbar «Promuovi» → modale unione (o conferma) | admin; le righe dipendono dai dati | `modals/PromoteMergeModal.svelte` |
| transactions/bulk-delete-pair-modal | entrambi / 4 | `/transactions` | Riga che contiene «delete-safe» ed «ETH» → ⋮ → «Elimina» → editor con la coppia collegata | admin (riga di seed «delete-safe») | `TransactionBulkModal.svelte` |
| transactions/bulk-todo-banner | entrambi / 4 | `/transactions` | Importa → seleziona l'estratto conto «Demo Bank» → analizza → revisione → «Importa» → nell'editor espandere il banner «da fare» → clic sull'ultima voce (riga evidenziata) | account usa-e-getta. **MOCK**: le voci «da fare» sono iniettate nella risposta del parse | `TransactionBulkModal.svelte` |

## brokers

| Shot | Viewport/lingue | Route | Come arrivarci (IT) | Utente / dati | Componenti |
|---|---|---|---|---|---|
| brokers/list | entrambi / 4 | `/brokers` | Menu → Broker (alto su desktop) | admin | `routes/(app)/brokers/+page.svelte`, `brokers/BrokerCard.svelte` |
| brokers/detail | entrambi / 4 | `/brokers/[id]` | Broker → card «Interactive Brokers» → scheda Panoramica | admin | `routes/(app)/brokers/[id]/+page.svelte` |
| brokers/edit-modal | entrambi / 4 | `/brokers/[id]` | Prima card broker → pulsante «Modifica» | admin (primo broker in lista) | `brokers/BrokerModal.svelte` |
| brokers/sharing-modal | entrambi / 4 | `/brokers` | Card «Coinbase» → icona condividi | admin | `brokers/BrokerSharingModal.svelte` |
| brokers/info-tab | entrambi / 4 | `/brokers/[id]` | Card «Coinbase» → scheda «Info» | admin | `brokers/[id]/+page.svelte` |
| brokers/positions-holdings-table / -holdings-map / -performance-table / -performance-map | entrambi / 4 | `/brokers/[id]` (Coinbase) | Coinbase → periodo 1A → scheda «Posizioni» → Detenute/Performance × Tabella/Mappa | admin LIVE | `dashboard/PositionsPanel.svelte`, `ExposureTable.svelte`, `ExposureTreemap.svelte`, `ContributionTable.svelte` |
| brokers/fifo-lots-panel, -wac-chart, -gantt-chart, -table, -comparison-chart, -comparison-chart-return, -custody-modal | entrambi / 4 | `/brokers/[id]` (Coinbase) | Coinbase → periodo Max → Posizioni → Detenute/Tabella → prima riga ⋮ → «Analizza lotti» → stessi passi della dashboard | admin LIVE | `lots/LotsAnalysisPanel.svelte` + grafici dei lotti |
| brokers/transactions-tab | entrambi / 4 | `/brokers/[id]` | Prima card broker → scheda «Transazioni» | admin | `brokers/[id]/+page.svelte` |
| brokers/import-modal | entrambi / 4 | `/brokers/[id]` | Scheda Transazioni → «Storico importazioni» | admin | `brokers/BrokerImportFilesModal.svelte` |
| brokers/import-wizard-step1 | entrambi / 4 | `/transactions` | Transazioni → «Importa» → passo 1 | admin | `modals/ImportWizardModal.svelte` |
| brokers/import-wizard-step2 | entrambi / 4 | `/transactions` | Importa → «Avanti» → passo 2 (scelta file) | admin | `ImportWizardModal.svelte` |
| brokers/import-wizard-step3 | entrambi / 4 | `/transactions` | Passo 2 → spuntare `generic_simple.csv` → «Analizza» | admin | `ImportWizardModal.svelte` |
| brokers/import-wizard-step4-resolution | entrambi / 4 | `/transactions` | Passo 3 → «Continua» (confermare l'avviso) → passo 4 | admin | `ImportWizardModal.svelte` |
| brokers/import-wizard-duplicate | entrambi / 4 | `/transactions` | Come sopra, tabella del passo 4 centrata | admin | `ImportWizardModal.svelte` |
| brokers/import-bulk-staging | entrambi / 4 | `/transactions` | Prima riga ⋮ → «Modifica» → chiudere il form → editor multiplo | admin | `TransactionBulkModal.svelte` |
| brokers/import-wizard-assets-step | entrambi / 4 | `/transactions` | Importa → caricare `e2e/assets/demo_credit_agricole_titoli.csv` + `demo_credit_agricole_conto.csv` → broker «Interactive Brokers» → Avanti → Analizza → Continua → passo «Asset» | admin (file caricati e poi eliminati) | `ImportWizardModal.svelte` |
| brokers/import-wizard-fix-step | entrambi / 4 | idem | Confermare tutti gli asset → Continua → passo «Correzioni» | idem | idem |
| brokers/import-wizard-duplicates-step | entrambi / 4 | idem | Accetta tutto → Continua → passo «Duplicati» → priorità file visibile → primo livello espanso | idem | idem |
| brokers/import-nway-compare | entrambi / 4 | idem | Primo gruppo duplicati → «Confronta» | idem | `modals/TransactionCompareModal.svelte` |
| brokers/import-report-set-card | entrambi / 4 | `/transactions` | Importa → «Seleziona file» → pannello «Danske Bank» → spuntare il set (custody + cash) → espandere la card | account usa-e-getta + file campione Danske caricati via API | `transactions/import/ReportSetCard.svelte` |
| brokers/import-report-set-read-as | entrambi / 4 | idem | Card del set → menu «Leggi come» aperto | idem | `ReportSetCard.svelte` |
| brokers/import-report-set-file-menu | entrambi / 4 | idem | Riga «cash» del set → ⋮ (Anteprima / Rimuovi dal set / Elimina) | idem | `ReportSetCard.svelte` |
| brokers/import-report-set-missing | entrambi / 4 | idem | Set con il solo custody → card che segnala l'export cash mancante | idem | `ReportSetCard.svelte` |
| brokers/import-report-set-pairing | entrambi / 4 | idem | Set «gap» (2 custody + cash) → Analizza → riga del set ⋮ → «Vedi dettaglio» → sezione abbinamento | idem | `modals/ParseDetailModal.svelte` |
| brokers/import-wizard-gapfix-step | entrambi / 4 | idem | Revisione → tenere solo le righe di cassa → «Importa» → passo «Allinea con la banca» | idem | `import/GapFixStep.svelte` |

## media

| Shot | Viewport/lingue | Route | Come arrivarci (IT) | Utente / dati | Componenti |
|---|---|---|---|---|---|
| media/image-edit-modal | entrambi / 4 | `/files` | File → Risorse statiche → «Carica» → scegliere un'immagine (`static/icons/transactions/buy.png`) → icona ✏️ modifica → vista ritaglio | admin | `ui/media/ImageEditModal.svelte`, `ui/media/FileUploader.svelte` |
| media/asset-picker-modal | entrambi / 4 | `/brokers/[id]` | Prima card broker → «Modifica» → clic sull'icona del broker → selettore immagini | admin | `ui/media/AssetPickerModal.svelte`, `BrokerModal.svelte` |
| media/file-uploader-empty | entrambi / 4 | `/files` | Risorse statiche → «Carica» (nessun file scelto) | admin | `FileUploader.svelte` |

## fx

| Shot | Viewport/lingue | Route | Come arrivarci (IT) | Utente / dati | Componenti |
|---|---|---|---|---|---|
| fx/list | entrambi / 4 | `/fx` | Menu → FX → periodo 1A | admin; tassi del DB, poll live da fixture | `routes/(app)/fx/+page.svelte`, `fx/FxCard.svelte` |
| fx/list-table | entrambi / 4 | `/fx` | FX → vista «Lista» | admin | `fx/+page.svelte` |
| fx/list-filtered | entrambi / 4 | `/fx` | FX → filtro valuta → «EUR» | admin | `fx/+page.svelte` |
| fx/add-pair-routes | entrambi / 4 | `/fx` | «+ Aggiungi coppia» → USD / CHF → «Aggiungi percorso» → sezione diretti (scrollare in fondo) | admin; catalogo provider da fixture | `fx/FxPairAddModal.svelte` |
| fx/add-pair-chain | entrambi / 4 | `/fx` | Aggiungi coppia → NOK / CHF → Aggiungi percorso → espandere il gruppo catena → scegliere la prima catena | admin | `FxPairAddModal.svelte` |
| fx/sync-progress | entrambi / 4 | `/fx` | Pulsante «Sincronizza tutto» → modale di avanzamento | admin; **sync bloccato** dalla guardia offline (lo stato mostrato può differire, ?) | `fx/+page.svelte` |
| fx/detail-chart | entrambi / 4 | `/fx/EUR-USD` | FX → card «EUR/USD» → periodo 1A | admin | `routes/(app)/fx/[pair]/+page.svelte` |
| fx/detail-signals | entrambi / 4 | `/fx/EUR-USD` | Dettaglio → «Segnali» | admin | `fx/[pair]/+page.svelte` |
| fx/detail-measures | entrambi / 4 | `/fx/EUR-USD` | Dettaglio → «Misure» | admin | idem |
| fx/detail-editor | entrambi / 4 | `/fx/EUR-USD` | Dettaglio → «Modifica dati» | admin | `fx/FxDataEditorSection.svelte`, `ui/data-editor/DataEditor.svelte` |
| fx/detail-csv-import | entrambi / 4 | `/fx/EUR-USD` | Modifica dati → «Importa» | admin | `ui/data-editor/DataImportModal.svelte` |
| fx/chart-settings | entrambi / 4 | `/fx` | Pagina FX → ⚙️ impostazioni grafico | admin | `charts/ChartSettingsModal.svelte` |
| fx/provider-config | entrambi / 4 | `/fx/EUR-USD` | Dettaglio → pulsante «Provider» → modale coppia/provider | admin | `FxPairAddModal.svelte` |

## assets

Asset predefinito: ricerca «Apple» → prima card (Apple Inc.), route `/assets/[id]`.

| Shot | Viewport/lingue | Route | Come arrivarci (IT) | Utente / dati | Componenti |
|---|---|---|---|---|---|
| assets/list | entrambi / 4 | `/assets` | Menu → Asset → periodo 1A | admin | `routes/(app)/assets/+page.svelte`, `assets/AssetCard.svelte` |
| assets/list-table | entrambi / 4 | `/assets` | Vista «Lista» (alto su desktop) | admin | `assets/+page.svelte` |
| assets/list-filtered | entrambi / 4 | `/assets` | Cercare «ETF» | admin | idem |
| assets/detail-chart | entrambi / 4 | `/assets/[id]` | Cercare «Apple» → card → periodo 1A | admin | `routes/(app)/assets/[id]/+page.svelte` |
| assets/detail-chart-candlestick | entrambi / 4 | idem | Grafico → tipo «Candele» | admin | idem |
| assets/detail-chart-rolling-return | entrambi / 4 | idem | Periodo 1S → «Rendimento a calendario/rolling» → finestra 1A → Segnali → confronto con asset «S&P 500» | admin | idem |
| assets/detail-signals | entrambi / 4 | idem | Periodo 1A → aprire «Segnali» | admin | idem |
| assets/detail-signals-ema | entrambi / 4 | idem | Segnali → selettore indicatori → gruppo Trend → «EMA» | admin | idem |
| assets/detail-signals-rsi | entrambi / 4 | idem | Momentum → «RSI» | admin | idem |
| assets/detail-signals-macd | entrambi / 4 | idem | Momentum → «MACD» | admin | idem |
| assets/detail-signals-bollinger | entrambi / 4 | idem | Volatilità → «Bollinger» | admin | idem |
| assets/detail-signals-tree | entrambi / 4 | idem | Segnali → selettore indicatori aperto (gruppo Trend) | admin | idem |
| assets/detail-signals-drawdown | entrambi / 4 | idem | Rischio → «Drawdown», parametro «storia completa» visibile | admin | idem |
| assets/chart-settings | entrambi / 4 | `/assets` | Lista asset → ⚙️ impostazioni grafico | admin | `charts/ChartSettingsModal.svelte` |
| assets/detail-events | entrambi / 4 | `/assets/[id]` | Apple → periodo Max → passare il mouse sull'evento 💰 a metà grafico → popover dividendo | admin. **MOCK**: 240 giorni di prezzi sintetici + dividendo finto | `assets/[id]/+page.svelte` |
| assets/detail-measures | entrambi / 4 | idem | Apple 1A → aprire «Misure» | admin | idem |
| assets/detail-measures-active | entrambi / 4 | idem | «+ Aggiungi misura» | admin | idem |
| assets/detail-classification | entrambi / 4 | idem | Apple → «Metadati/Classificazione» | admin | idem |
| assets/detail-editor | entrambi / 4 | idem | Apple → «Modifica dati» | admin | `assets/AssetDataEditorSection.svelte`, `DataEditor.svelte` |
| assets/create-modal | entrambi / 4 | `/assets` | «+ Aggiungi asset» | admin | `assets/AssetModal.svelte` |
| assets/type-picker-open | entrambi / 4 | `/assets` | Aggiungi asset → menu «Tipo» → espandere la famiglia ETF | admin | `AssetModal.svelte` |
| assets/create-provider-compare | entrambi / 4 | `/assets` | Aggiungi asset → «Altre info» → aggiungere un settore → Cerca online (yfinance) con ISIN `IE000NWGE006` → risultato → modale di confronto | admin. **MOCK**: fondo inventato «Northwind Global Equity UCITS ETF» | `assets/ProviderComparisonModal.svelte`, `AssetModal.svelte` |
| assets/distribution-editor-sector | entrambi / 4 | `/assets/[id]` (Tesla) | Cercare «Tesla» → card → «Modifica» → «Altre info» → editor settori | admin | `ui/input/DistributionEditor.svelte`, `AssetModal.svelte` |
| assets/distribution-editor-geographic | entrambi / 4 | idem | Scorrere all'editor geografico | admin | idem |
| assets/create-wizard-modal | entrambi / 4 | `/transactions` | Importa → Avanti → `generic_simple.csv` → Analizza → Continua → passo 4: selettore asset → «Crea nuovo» | admin | `AssetModal.svelte`, `ImportWizardModal.svelte` |

## risk

Laboratorio di rischio:
- Route: `/assets?tab=correlation`, periodo 1A.
- Selezione: Apple Inc., RE Loan Milano, RE Loan Roma, Bitcoin, Ethereum.
- Benchmark: S&P 500.
- Selezione e benchmark sono preimpostati in localStorage: dal vivo vanno aggiunti a mano.

| Shot | Viewport/lingue | Route | Come arrivarci (IT) | Utente / dati | Componenti |
|---|---|---|---|---|---|
| risk/lab-correlation | entrambi / 4 | `/assets?tab=correlation` | Asset → scheda «Correlazione/Rischio» → selezionare i 5 asset → sezione correlazione | admin LIVE | `risk/AssetSetRiskPanel.svelte`, `risk/RiskAnalysisPanel.svelte` |
| risk/lab-hurt-table | entrambi / 4 | idem | Sezione tabella delle perdite | admin | `AssetSetRiskPanel.svelte` |
| risk/lab-risk-return | entrambi / 4 | idem | Sezione rischio/rendimento con benchmark S&P 500 (alto su desktop) | admin | idem |
| risk/lab-asset-picker | entrambi / 4 | idem | «+» → aggiungere Microsoft e Tesla; NVIDIA e «Test KRW Stock» risultano bloccati | admin | idem |
| risk/lab-benchmark-picker | entrambi / 4 | idem | Sezione rischio/rendimento → selettore benchmark aperto (elenco non utilizzabili visibile) | admin | idem |
| risk/lab-notice | entrambi / 4 | idem | Senza benchmark → avviso di risultati parziali (prezzo vecchio su RE Loan Roma) | admin. **MOCK** (prezzo vecchio iniettato) | idem |
| risk/lab-replay | entrambi / 4 | idem | Sezione «Replay storico» → aprire → «Esegui» → riquadro asset esclusi + tornado | admin. **MOCK** (RE Loan Roma escluso, iniettato) | idem |
| risk/whatif-simulation | entrambi / 4 | `/dashboard` | Periodo 1A → scheda «Rischio» → «E se…?» → «+ Simulazione» → percorsi 2048, seed 123456 → «Esegui» | admin LIVE | `risk/levels/l4/L4Simulation.svelte`, `RiskLevelsPanel.svelte` |

---

**Conteggio per categoria:** auth 4, onboarding 3, dashboard 33, security 1, settings 13, tools 10, support 2, files 9, transactions 19, brokers 34, media 3, fx 13, assets 25, risk 8 = **177**.

Su ogni riga resta un "?" dove non ho verificato:
- **Etichette dei pulsanti:** le etichette italiane esatte (es. «Analizza lotti», «Dividi», «Promuovi») sono dedotte dai `data-testid`, non lette dai file di lingua.
- **Componenti:** le liste transazioni della dashboard, forse live, sono da verificare.