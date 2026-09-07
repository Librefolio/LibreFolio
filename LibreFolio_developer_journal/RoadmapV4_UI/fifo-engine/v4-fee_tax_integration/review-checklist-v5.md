# Review checklist — FIFO Engine v5

> **Scopo:** artefatto operativo per la review congiunta. Due sezioni: **(1) decisioni da confermare** e
> **(2) rinvii da approvare**, poi **(3) test manuali guidati** (dove andare + valore atteso) e **(4) verifica
> automatica**. Companion: [`implementation-recap-v5.md`](./implementation-recap-v5.md). Piano:
> [`implementation-plan-v5.md`](./implementation-plan-v5.md) (§10 = sintesi test, Appendice A = checklist completa).
>
> Legenda esito: `[ ]` da verificare · `[x]` ok · `[!]` da correggere.

---

## 1. Decisioni da confermare (deviazioni / scelte a basso rischio)

| # | Decisione | Dove | Default proposto | Impatto se si cambia |
|---|-----------|------|------------------|----------------------|
| D1 | **Colonne nette nascoste di default se l'asset non ha FEE/TAX** (`hiddenByDefault: !hasNetCosts`), coerente con la colonna `asset-income` esistente. §8.1 diceva "visibili di default" in assoluto. | `UnifiedLotsTable.svelte` (`hasNetCosts`, def. colonne nette) | **Tenere nascoste senza costi** (tabella meno affollata, coerente con income) | Rendere sempre visibili = 1 riga per colonna (togliere `hiddenByDefault`); netto=lordo quando fees/taxes=0 |
| D2 | **Empty analysis status** migra `UNAVAILABLE` → `COMPLETE` con `lots=[]`. | `lots_analysis_service.py` `_empty_response`; `schemas/portfolio.py` enum | **`COMPLETE`** (nessun consumer FE ramifica sullo status; grep=0) | Introdurre un 4° valore globale = rompe l'accordo "3 valori" e il mapping 1:1 |
| D3 | **`net_metrics_status` sempre `AVAILABLE`** per ora (trigger `UNAVAILABLE` non emesso dal backend). | `lots_analysis_service.py` `_build_lot_summaries`; FE "—" latente | **Lasciare AVAILABLE** finché non arriva il trigger FX-missing/conservazione | Attivare il trigger richiede prima l'emissione backend di `FX_RATE_MISSING_FOR_ALLOCATION` / `ALLOCATION_CONSERVATION_FAILED` |
| D4 | **Campo DTO pubblico resta `calculation_status`** (non rinominato), tipizzato a 3 valori. | `schemas/portfolio.py` `LotsAnalysisResponse` | **Non rinominare** (no churn API/FE) | Rinominare = breaking change su client + FE |
| D5 | **FEE/TAX broker-level (`asset_id=None`) restano esclusi** dal FIFO (li gestisce il Portfolio Engine); entrano solo i FEE/TAX asset-linked. | `lots_analysis_service.py` `_build_engine_transactions` | **Escludere broker-level dal FIFO** | Includerli richiederebbe una semantica di allocazione senza asset (fuori scope) |
| D6 | **UPDATE di campo non correlato su FEE/TAX legacy-invalida ora viene rifiutato** (validator su stato finale). | `transactions.py` validator condiviso | **Accettabile/desiderabile** (audit 0.2 = 0 righe; forza bonifica) | Ammorbidire = validare solo i campi toccati (accoppia CREATE/UPDATE) |

> Le voci D1–D3 sono le uniche "fuori pista" rispetto alla lettera del piano; D4–D6 sono scelte già argomentate
> nel piano ma vale la pena confermarle esplicitamente in review.

---

## 2. Rinvii da approvare (non implementati, con proposta)

| # | Rinvio | Motivo | Proposta per il run dedicato |
|---|--------|--------|------------------------------|
| R1 | **Fase 9 lato Portfolio Engine** (accumulatori assoluti pre-share + riconciliazione runtime) | Doppio path accumulatori (`portfolio_engine.py:834-851` **e** `portfolio_service.py:1715-1762`); nessun consumer per i valori assoluti; file caldo (~1800 righe, share sparsa in 5+ punti) | (1) scegliere path canonico; (2) accumulatori assoluti **accanto** agli esistenti (additivi, zero rimozioni); (3) test `absolute·share == user`; (4) test riconciliazione Portfolio-assoluto vs FIFO `allocated+orphan` (metà FIFO **già** bloccata da `TestEconomicConservation`) |
| R2 | **`LotComparisonChart` serie nette parallele** | Chart molto intricato (mode × unit × aggregate/per-lot × bucket × resolution × tooltip override); §8.3 lo marca come rifinitura da verificare a occhio prima | Implementare iterativamente **dopo** la review visiva; il netto è già in 3 superfici (tabella, modal, tooltip Gantt) |
| R3 | **Provenienza pool nel modal** (§8.2, "se presente") | Opzionale; il breakdown mostra gli importi ma non il mapping `economic_allocation_groups`→lotto (regola + `source_transaction_ids`) | Aggiungere una riga/accordion "provenienza" se in review si ritiene utile |
| R4 | **Trigger `net_metrics_status=UNAVAILABLE`** | Il backend non emette ancora `FX_RATE_MISSING_FOR_ALLOCATION`/`ALLOCATION_CONSERVATION_FAILED` che localizzano l'indisponibilità | Emettere i codici lato motore/service; la UI "—" è già cablata |

---

## 3. Test manuali guidati (accettazione frontend)

**Setup:** login `e2e_test_user` / `E2eTestPass123!` → apri un **asset con storia FEE/TAX/income** →
pannello **Lots Analysis**. Selettori `data-testid`. Nessun test automatico grafico (per preferenza esplicita).

### 3.1 — Superfici toccate in questa sessione (priorità review)

| # | Dove andare | Azione | Valore atteso | Esito |
|---|-------------|--------|---------------|-------|
| M-H | Pannello Lots Analysis, asset scenario 6.1 | BUY 10×100, SELL 4×120, prezzo 110, DIV 50, FEE 8, TAX 5 | Open **660**, Proceeds **480**, Gross P&L **190**, **Net P&L 177**, Gross Ret **19%**, **Net Ret 17,7%** | `[ ]` |
| M-L | Tabella lotti → column selector | Asset **con** FEE/TAX | 4 colonne nette (Fees, Taxes, Net P&L, Net return) **visibili**; footer somma corretta | `[ ]` |
| M-L2 | Tabella lotti | Asset **senza** FEE/TAX | Colonne nette **assenti di default** (occultate); netto = lordo (→ decisione **D1**) | `[ ]` |
| M-M | **Menu azioni riga** (kebab) → **"Dettaglio lotto"** su lotto con FEE/TAX → `LotCustodyModal` — *in alternativa* click sulla **cella custody-badge** della riga | Apri breakdown | Sezione "Scomposizione netta": Gross total P&L → **− Fees** → **− Taxes** → **Net** total P&L + Net return | `[ ]` |
| M-M2 | Modal su lotto con `net_metrics_status=UNAVAILABLE` | **Non producibile** dal codice attuale: nessun path lo emette (FX mancante → fallback nativo). Vedi **R4** → raccomandata **rimozione** del campo | Celle nette mostrano "—" | `[ ]` (latente, candidato a rimozione) |
| M-M3 | **Doppio click** su riga tabella / corsia Gantt / evento WAC | Verifica navigazione incrociata (NON apre modale) | Riga↔Gantt (pulse/scroll), evento WAC → selezione lotti. Il doppio click **non** è il percorso per il breakdown netto (→ usare M-M) | `[ ]` |
| M-G | Gantt (`LotGanttChart`), hover su segmento con costi | Tooltip | Righe **Fees**/**Taxes** (rosse) + **Net P&L** quando presenti | `[ ]` |
| M-K | Pannello con analisi **FAILED** (errore quantitativo, es. oversell / transfer rotto) | Osserva header | Banner rosso `data-testid=lots-analysis-panel-failed` **+ tabella e grafici comunque mostrati**: tutti i lotti ricostruiti restano consultabili ma i valori possono essere incompleti (semantica "warn but show", non "hide") | `[ ]` (ramo difensivo, difficile da forzare da UI) |
| M-DQ | Asset con income/costo orphan | Osserva `DataQualityBanner` | Banner con `assetIncomeNoEligibleLots` / `assetCostNoEligibleLots` (interpolati EN/IT/FR/ES) | `[ ]` |

> **⚠️ Correzione M-M (post-test manuale):** la versione precedente indicava *"doppio click sul lotto → LotCustodyModal"*, ma il doppio click **non** apre alcuna modale (è navigazione incrociata riga↔Gantt / selezione evento WAC). Il percorso canonico è **menu azioni riga → "Dettaglio lotto"** oppure **click sulla cella custody-badge**. In questo pannello esiste **una sola** modale (`LotCustodyModal`). Mappa completa UI→handler→modale in `post-implementation-review-v5.md` §8.

### 3.2 — Invarianti economici (verifica numerica)

| # | Scenario | Atteso | Esito |
|---|----------|--------|-------|
| INV-1 | Asset solo BUY/SELL (nessun FEE/TAX/income) | Colonne gross invariate vs oggi; nette = gross | `[ ]` |
| INV-2 | Income D-1: BUY in D + DIVIDEND in D | Il lotto aperto in D **non** riceve income (solo lotti aperti a D-1) | `[ ]` |
| INV-3 | Scope broker: Directa 30 / IBKR 70, DIV +100 su Directa | Σ income lotti Directa = 100; IBKR = 0 | `[ ]` |
| INV-4 | Costo post-chiusura: SELL completa in D-1, FEE in D | Serie **netta** con gradino in D; serie **lorda** invariata | `[ ]` |
| INV-5 | FX target: stessa analisi in EUR e USD | Metriche coerenti nella target; audit mostra nativo+target | `[ ]` |

### 3.3 — Copertura completa
Per la matrice esaustiva (Pool FEE FEE-1..8, Pool TAX TAX-1..9, Status ST-1..6, History HI-1..5, Audit AU-1..9)
esegui **Appendice A** di `implementation-plan-v5.md` (§967+). Qui sopra c'è il sottoinsieme che tocca
direttamente le modifiche di questa sessione.

---

## 4. Verifica automatica (già verde, per rieseguire)

```bash
# Backend
PYTHONPATH=. pipenv run pytest backend/test_scripts/test_services/test_financial -q      # 298
PYTHONPATH=. pipenv run pytest backend/test_scripts/test_schemas -q                       # 274
LIBREFOLIO_TEST_MODE=1 PYTHONPATH=. pipenv run pytest backend/test_scripts/test_api/test_transactions_validate.py -q  # 10
# NB: file API pesanti uno alla volta (2 insieme → OOM 137)

# Frontend
./dev.py front check && ./dev.py i18n audit && ./dev.py front build && ./dev.py front format
```

Esito atteso: backend verde, `front check` 0/0, `i18n audit` Incomplete:0, build/format puliti.

---

## 5. Sintesi decisione richiesta in review

- [ ] **Confermare** D1–D6 (o richiedere modifica).
- [ ] **Approvare** i rinvii R1–R4 (in particolare **R1**: scegliere il path canonico Portfolio prima del run dedicato).
- [ ] **Eseguire** i test manuali §3 (almeno la riga **M-H** come accettazione numerica).
- [ ] **Committare** manualmente con il messaggio in `/tmp/libreFolio_commit_fifo_v5.txt` (o una sua revisione).
