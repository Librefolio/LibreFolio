# Valuta iniziale delle pagine: la Default Currency dell'utente, non quella dell'istanza

> Lotto di N, 08/10. Coordinator: c8328a01. Base `108a2adf5` (treno 17; nessun file di codice cambiato rispetto a
> `cf4248bd9`), worktree pulito. Corsia 6159/6169, `/tmp/librefolio-r2-n`.
> Decisione del developer (verbatim): «Dalla Default Currency dell'utente: è un difetto». Si corregge senza
> attendere approvazione.

## 1. Stato reale (verificato su `108a2adf5`)

`globalSettings.default_currency` è la valuta dell'**istanza** per i **nuovi** utenti: la chiave i18n dice «Default
currency for new users» (`en.json:2027`). La valuta dell'utente è `userSettings.base_currency`.

**I punti che partono dalla valuta dell'istanza** (tutti gli usi di `default_currency` fuori dalle schede delle
impostazioni):

| Pagina | Dove | Effetto |
|---|---|---|
| Dashboard | `dashboard/+page.svelte:179` (iniziale = `restoredView.targetCurrency ?? istanza`), `:201` (`baseCurrency`), `:203-211` (l'effetto la segue finché l'utente non sceglie a mano), `:858` `defaultCurrency`, `:861` placeholder, `:864` prefill della coppia FX («Prefill base = user default currency», ma usa l'istanza) | report, grafici, KPI nella valuta dell'istanza |
| Elenco broker | `brokers/+page.svelte:88-98`, `:361` | riepiloghi dei broker |
| Dettaglio broker | `brokers/[id]/+page.svelte:191` (iniziale), `:214-220` (`baseCurrency` + inseguimento), `:562`, e i ripieghi `targetCurrency \|\| baseCurrency` (`:621`, `:646`, `:651`, `:672`, `:684`) | report, KPI, grafici, lotti, rischio |
| Pannello rischio degli asset | `assets/+page.svelte:1618` (`AssetSetRiskPanel targetCurrency`) | `target_currency` di `POST /risk/eligibility` e delle altre richieste di rischio (`AssetSetRiskPanel.svelte:281`, `:323`, `:509`, `:850-864`) |
| **Dettaglio FX, AI Export** (trovato da me, non era nella lista di Q) | `fx/[pair]/+page.svelte:225` (`fxAiExportTargetCurrency = istanza \|\| canonicalQuote`), usato a `:1012` | `target_currency` della richiesta AI Export. Le altre superfici usano la valuta della pagina |

- **Le impostazioni dell'utente ci sono sempre quando una pagina monta.** Il bootstrap carica impostazioni utente,
  onboarding e impostazioni globali insieme, e senza impostazioni utente va in `blocked`
  (`appBootstrap.svelte.ts:65-73`). Il layout `(app)` rende le pagine solo a bootstrap pronto
  (`(app)/+layout.svelte:231-243`).
- **`base_currency` è una `string` obbligatoria** in `UserSettingsRead` (`generated.ts:770-778`).
- **Precedenti che già usano la valuta dell'utente**: `BrokerForm.svelte:131`, `AssetModal.svelte:683`,
  `PacPlannerTool.svelte:63`, `:287`, `welcome/+page.svelte:70`.

## 2. Correzione

- **Una sola regola**, in uno store derivato `defaultDisplayCurrency` in `lib/stores/app/settings.ts`:
  `$userSettings?.base_currency || $globalSettings.default_currency || 'EUR'`. Le cinque pagine la usano.
  - Restano com'erano la scelta ricordata (`restoredView.targetCurrency`) e la scelta manuale
    (`targetCurrencyManuallySet`).
  - Per la stessa via cambiano anche il placeholder, il «default» del menu e il prefill della coppia FX.
- **Testid** sui due `CurrencySearchSelect` dei broker (`broker-page-target-currency`,
  `broker-detail-target-currency`), aggiunti **prima** del rosso, così il rosso cade sulla valuta.

## 3. Rischio di stato condiviso provocato dalla correzione

`assets/asset-modal.spec.ts:221-262` (NR «Bug G») porta a GBP per qualche secondo il `base_currency` dell'utente
**condiviso** TEST_USER. Il suo commento lo dice tollerabile «only because … no neighbour asserts on the base
currency». Dopo la correzione **ogni** pagina segue quella valuta: una Dashboard di un vicino, aperta in quella
finestra, partirebbe in GBP.

Cura proposta: lo stesso test, ma con l'intercettazione di `GET /settings/user` (`base_currency: 'GBP'`) al posto
della `PUT` e del ripristino. Nessuna scrittura condivisa. Precedenti di intercettazione:
`files-uploader.spec.ts:140`, `header-scroll.spec.ts:33`.

## 4. Test (test-author, rossi prima)

- **E2E nuovo**: `frontend/e2e/portfolio/default-currency.spec.ts`.
  - Intercetta `GET /settings/user` (utente = USD) e `GET /settings/global` (istanza = GBP): niente scritture,
    niente dipendenze dalla configurazione reale.
  - Per ogni pagina verifica il valore del select e il `target_currency` della richiesta: Dashboard, elenco broker,
    dettaglio broker, pannello rischio (`/risk/eligibility`), AI Export dell'FX. Rossi oggi: vedrebbero GBP.
  - Una guardia, verde prima e dopo: la scelta manuale ricordata vince sulla Default Currency.
- **Unit**: `src/lib/stores/app/settings.test.ts`: la precedenza utente → istanza → `'EUR'`, e il valore che segue
  le impostazioni caricate dopo.
- **Registrazioni nel runner** (file condivisi, solo righe nuove):
  - `_frontend_portfolio.py`: l'azione `front-portfolio default-currency`;
  - `_frontend_utility.py`: la riga del test unit nella lista di `front-utility core-unit`.

## 5. Gate

- Il test nuovo, poi i gate richiesti: `front-portfolio dashboard`, `front-broker detail`,
  `front-portfolio risk-lab` (il pannello rischio degli asset) e `component-unit`.
- In più: `front-broker list`, `front-utility core-unit`, l'NR di `asset-modal` e `front check`.

## 6. Conflitti previsti

- Le cinque pagine sono file molto toccati: le righe cambiate sono poche e puntuali.
- I due file del runner: solo righe aggiunte.
- `asset-modal.spec.ts`: da concedere.

## 7. Passi

1. ✅ (08/10) Analisi breve, mandata al coordinator. **Approvata, compreso il quinto punto** (AI Export dell'FX).
   Concessi: le due righe del runner e il blocco NR di `asset-modal.spec.ts:221-262`.
   > **⚠️ Fuori pista**: il coordinator ha avanzato il worktree al treno 17 (`108a2adf5`), che non cambia nessun file
   > di codice. L'azione del test unit si chiama `front-utility core-unit`, non `unit`.
2. ✅ (08/10) Testid sui due select dei broker (`broker-page-target-currency`, `broker-detail-target-currency`),
   messi prima del rosso. Il test-author ha scritto `e2e/portfolio/default-currency.spec.ts` (6 test),
   `src/lib/stores/app/settings.test.ts` (5 casi) e il blocco NR di `asset-modal` con l'intercettazione.
   Registrazioni nel runner: `_frontend_portfolio.py` (+10) e `_frontend_utility.py` (+1), solo righe aggiunte.
3. ✅ (08/10) Rosso in corsia, con il codice di produzione invariato:
   - E2E: **5 falliti, 1 passato**. (a), (c), (d), (e), (f) «Expected USD, Received GBP», cioè la valuta
     dell'istanza; la guardia (b) è verde (`/tmp/libreFolio_n_defcur_red.log`).
   - Unit: **5 falliti**, per l'export mancante (`/tmp/libreFolio_n_defcur_unit_red.log`).
   - NR di `asset-modal`: verde prima della correzione, senza scrittura condivisa.
4. ✅ (08/10) Correzione con `/tmp/libreFolio_n_defcur_fix.py`.
   > **Note implementazione**:
   > - `defaultDisplayCurrency` in `settings.ts`: un `derived` di `userSettings` e `globalSettings`.
   > - Dashboard, elenco e dettaglio broker, assets e FX importano lui al posto di `globalSettings`: in quelle
   >   pagine non resta nessun riferimento a `globalSettings`.
   > - Il commento della guardia `!loading` nell'elenco broker è aggiornato (non parla più di
   >   `globalSettings.load()`).
   > - Il ripiego `data.canonicalQuote` dell'FX era irraggiungibile (lo store globale ha sempre `default_currency`)
   >   ed è caduto.
5. ✅ (08/10) Verde e gate, nella corsia 6159:
   - il test nuovo: **6 passati a 1 worker e 6 a 4 worker**; unit **5 passati**;
   - `front-portfolio dashboard` 27/27, `front-broker detail` 33/33, `front-broker list` 9/9,
     `front-portfolio risk-lab` 44/44, `front-asset asset-modal` 17/17 (NR compreso);
   - `front-utility component-unit` 2850/2850 (111 file), `front-utility core-unit` 3440/3440 (118 file);
   - `front check`: svelte-check 0 errori e 0 avvisi. Prettier pulito. `check-orphans` ✅.
6. ✅ (08/10) Checkpoint: 3 commit proposti in `/tmp/libreFolio_commits/libreFolio_commit_n_defcur_C1..C3.txt` (la
   correzione con i suoi test e le registrazioni; l'NR di `asset-modal`; questo piano). Liste in
   `n_defcur_paths_C1..C3.txt`, blob in `n_defcur_blobs.txt`, albero in `n_defcur_final_tree.txt`. Stato: FROZEN.
