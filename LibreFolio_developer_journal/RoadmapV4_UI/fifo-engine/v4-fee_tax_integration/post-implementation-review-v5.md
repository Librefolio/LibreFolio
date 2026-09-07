# Post-implementation review — FIFO Engine v5 (dopo i primi test manuali)

> Documento di review correttiva prodotto **dopo** i primi test manuali dell'utente sull'implementazione
> reale. Fonti di verità: il **codice** (citazioni file:riga verificate in questa sessione) e le **decisioni
> di prodotto D1–D6** confermate dall'utente. Nessun commit eseguito.
>
> Compagni di questo file: `implementation-plan-v5.md` (piano), `implementation-recap-v5.md` (recap),
> `review-checklist-v5.md` (checklist test manuali — aggiornata in questa sessione).

---

## 0. Executive summary

| Tema | Esito |
|------|-------|
| **Bug colonne nette nascoste** (§3) | **CORRETTO** in `DataTable.svelte` (modello a *override*). Causa: stato di visibilità che non distingueva "nascosto per default dinamico" da "nascosto dall'utente" e non si ri-sincronizzava quando `hiddenByDefault` passava `true→false` al caricamento dati. `front check`/`format`/`build` verdi. |
| **Mappa modali / "doppio click"** (§8) | La checklist era **errata**: il doppio click **non** apre `LotCustodyModal`. Percorso canonico = **menu azioni riga → "Dettaglio lotto"** o **click cella custody-badge**. Checklist **corretta**. |
| **`net_metrics_status` / UNAVAILABLE** (§6) | **Nessun path reale** lo emette (FX mancante → fallback nativo → netto sempre calcolabile). Raccomandata **rimozione** (R4) come semplificazione differibile, non bloccante. |
| **Stato FAILED** (§7) | I 4 codici sono **rotture di topologia quantitativa non isolabili** dall'architettura attuale (nessuna partizione di affidabilità per broker). **FAILED è corretto** — mantenere, documentando il *perché*. Frontend: banner + dati comunque mostrati ("warn but show"). |
| **Riconciliazione Portfolio Engine** (§5, R1) | Classe **B (+ C latente) = D**: double-check indipendente, non prerequisito di correttezza. **Differibile** senza cambiare i valori mostrati oggi. |
| **Dataset di test** (§4) | Confermato: **2 FEE, entrambe `asset_id=null`; 0 TAX; 0 costi asset-linked** → colonne nette correttamente nascoste nel DB di test. Fornita **specifica fixture** ripetibile (15 scenari) da eseguire in run dedicato. |
| **net_pnl vs net_total_pnl** (§9, R2/R3) | Semantica confermata e **asimmetrica per progetto**: `value_history.net_pnl` esclude income (capital-only); `summary.net_total_pnl` e `return_history.net_total_return` includono income. Il grafico netto futuro deve usare i campi **summary/return** (income-inclusive). R3 (provenienza) è **solo frontend**: i dati esistono già nel DTO. |

**Pronto per il commit** dopo: (a) la fix colonne nette (fatta, verificata); (b) presa d'atto del trade-off storage
(§3.4). Il resto sono raccomandazioni/rinvii documentati, non blocchi.

---

## 1. Decisioni di prodotto recepite (D1–D6)

| ID | Decisione | Impatto su questa review |
|----|-----------|--------------------------|
| **D1** | Colonne nette visibili di default se **almeno una riga** dell'intera tabella ha `AllocatedFees>0 ∨ AllocatedTaxes>0`. Reset ripristina questo default dinamico; preferenza utente esplicita può poi nasconderle. | La fix §3 implementa **esattamente** questa policy (valutazione su tutte le righe via `hasNetCosts`; override utente persistiti; reset = svuota override). |
| **D2** | Analisi vuota ma calcolata: `calculation_status=COMPLETE`, `lots=[]`. Non è errore. | Coerente col codice: `analysis_status` è `COMPLETE` in assenza di issue (`fifo_lot_engine.py:300-302`). |
| **D3** | Comportamento ordinario: `net_metrics_status=AVAILABLE`. Valutare `UNAVAILABLE` solo su scenari reali. | §6: **nessuno** scenario reale lo richiede → raccomandata rimozione. |
| **D4** | Il campo pubblico resta `LotsAnalysisResponse.calculation_status` (non rinominato). | Nessuna modifica al nome. Confermato `calculation_status` in `schemas/portfolio.py`. |
| **D5** | FEE/TAX con `asset_id=null` → **escluse dal FIFO**, gestite dal Portfolio Engine. | §4: spiega perché il DB di test (solo FEE senza asset) non mostra colonne nette. |
| **D6** | La validazione UPDATE considera lo **stato finale completo**; un record già invalido va corretto prima di aggiornarlo. | Nessuna azione in questa review (già coperto da Fase 0.1 del piano). |

---

## 2. Diagnosi e correzione del bug "colonne nette nascoste"

### 2.1 Sintomo osservato (DB di produzione)

Asset con un lotto avente `tasse`/`commissioni` presenti (P&L netto ≠ lordo; la **modale** mostra
correttamente la scomposizione netta), ma **le 4 colonne nette restano nascoste** di default e **Reset
layout** non le rende visibili.

### 2.2 Cosa NON era la causa (escluso con prove)

- **Parsing valori (stringhe/Decimal):** `UnifiedLotsTable.svelte` usa `safeNum()` (`:96-101`) su
  `allocated_fees`/`allocated_taxes`; `DataTable` parseNumber gestisce stringhe decimali. Il confronto `>0`
  è corretto. La **modale** (`LotCustodyModal.svelte`) usa **gli stessi campi e la stessa logica**
  (`lotHasNetCosts` `:293`) di `hasNetCosts` (`UnifiedLotsTable.svelte:438`): se la modale mostra il
  breakdown, i dati **ci sono** e sono numerici. → il problema **non** è dato/parsing/timing.
- **Timing di mount:** la tabella è renderizzata solo nel ramo `{:else}` dopo il caricamento dati
  (`LotsAnalysisPanel.svelte:446-497`). Nessun render con dati vuoti.

### 2.3 Causa reale (in `DataTable.svelte`)

Lo stato di visibilità era uno snapshot `columnVisibility = $state<VisibilityState>({})` che:

1. **non distingueva** "colonna nascosta perché `hiddenByDefault` dinamico" da "colonna nascosta
   dall'utente" — le due cose collassavano in un unico `false`;
2. **non si ri-sincronizzava** quando, al caricamento dati, `hiddenByDefault` di una colonna **già esistente**
   passava da `true` (nessun costo, dataset iniziale) a `false` (arrivano righe con costi): l'`$effect` di
   sync reagiva solo ad **aggiunte/rimozioni** di ID colonna, non al *flip* del flag su una colonna già
   presente;
3. una preferenza persistita `false` (obsoleta) poteva quindi **prevalere per sempre** sul nuovo default
   dinamico `true`, violando **D1**.

### 2.4 Patch applicata (modello a override)

Sostituito lo snapshot con un **modello a override esplicito**:

- `columnVisibilityOverrides = $state<VisibilityState>({})` — contiene **solo** le scelte esplicite
  dell'utente;
- `columnVisibility = $derived(...)` — visibilità **effettiva** calcolata live come
  `id ∈ overrides ? overrides[id] : !hiddenByDefault`, quindi **sempre allineata** al default dinamico
  corrente per le colonne non toccate dall'utente;
- `toggleColumnVisibility` scrive negli override; `resetColumns` svuota gli override (→ riapplica il default
  dinamico corrente) e persiste sotto la **nuova chiave** `columnVisibilityOverrides`;
- l'`$effect` di sync ora fa solo **pruning** degli override su ID non più validi (mantiene la gestione di
  ordine/larghezza invariata).

Policy risultante (= **D1**):

```
prima apertura / nessuna preferenza  → default dinamico (hasNetCosts)
Reset layout                         → cancella override → riapplica default dinamico corrente
preferenza utente salvata            → prevale (può nascondere anche con hasNetCosts=true)
```

Questa correzione sistemica risolve **anche** l'analoga colonna dinamica `asset-income`.

### 2.5 Trade-off da mettere a verbale (⚠️ da confermare prima del commit)

La persistenza cambia chiave: `columnVisibility` → `columnVisibilityOverrides`. **Le mappe legacy di sola
visibilità non vengono migrate** → *una-tantum*, si perde la preferenza show/hide delle colonne su **tutte**
le tabelle che usano `DataTable` (ordine e larghezze **preservati**). È una scelta deliberata e contenuta a
favore della correttezza. `DataTable` è un componente condiviso caldo (es. tabella Transazioni): la fix
**non** cambia il comportamento delle colonne con `hiddenByDefault` statico, tocca solo quelle a default
dinamico (verificato type-safe da `front check`).

### 2.6 Check eseguiti dopo la fix

`./dev.py front check` → **0 errori / 0 warning**; `./dev.py front format` → pulito; `./dev.py front build`
→ **OK**. (Log in `/tmp/libreFolio_frontcheck.log`, `_frontformat.log`, `_frontbuild.log`.)
Nessun test grafico automatico aggiunto (per preferenza esplicita).

---

## 3. Verifica del dataset di test + proposta fixture

### 3.1 Stato reale del DB di test (confermato dal seed)

Seed: `backend/test_scripts/test_db/populate_mock_data.py` (eseguito da
`./dev.py test -q db populate --force --clean ...`).

| Fatto | Evidenza |
|-------|----------|
| **2 sole FEE, entrambe `asset_id=null`** | FEE "Monthly platform fee" (`:1139-1147`, `asset=None`); FEE delete-safe su Directa (`:1377-1391`, `asset_id=None`). |
| **0 TAX standalone** | La tassa del dividendo è **netata nell'amount** (`DIVIDEND amount=2.62 = 3.75 − 1.13 tax`, `:1108-1113`), **non** una transazione `TAX`. |
| **La "fee" sulla SELL non è una FEE asset-linked** | `"fee": Decimal("1.00")` su SELL (`:1124`) è incorporata nell'`amount` da `_derive_market_amount`, non genera una transazione `FEE`. |
| **Assegnazione asset** | `asset_id = tx_data["asset"].id if tx_data["asset"] else None` (`:1335`). |

**Conclusione:** poiché FEE/TAX senza `asset_id` sono escluse dal FIFO (**D5**), nel DB di test **nessun
asset** può mostrare costi allocati/colonne nette/audit FIFO. Il comportamento osservato (colonne nette
assenti nel DB di test) è **corretto**, non un bug. Lo scenario è verificabile solo su DB con costi
asset-linked (come la prod dell'utente).

### 3.2 Scenari della checklist testabili **oggi** col dataset corrente

| Scenario checklist | Testabile nel DB di test? |
|--------------------|---------------------------|
| M-H (canonico Gross190/Net177) | ❌ manca l'asset con FEE 8 + TAX 5 |
| M-L (colonne nette visibili, asset **con** FEE/TAX) | ❌ nessun asset con costi asset-linked |
| M-L2 (colonne nette assenti, asset **senza** FEE/TAX) | ✅ (è di fatto lo stato di tutti gli asset) |
| INV-2/INV-3 (income D-1 / scope broker) | ⚠️ parziale: c'è DIVIDEND/INTEREST ma income netato; nessun costo |
| FEE-1..8 / TAX-1..9 (Appendice A) | ❌ non producibili |

### 3.3 Proposta fixture ripetibile (per run dedicato — **non** applicata ora)

**Decisione:** `populate_mock_data.py` è una fixture condivisa consumata da molti test backend/E2E che
asseriscono conteggi e totali. Aggiungere transazioni agli asset/broker esistenti **romperebbe** quei test;
anche un nuovo asset/broker può rompere i test che contano asset/broker/transazioni totali. Poiché questo è
un run di review **senza commit** e senza esecuzione dell'intera suite, la fixture **non** viene wired ora
(coerente con "prepara la fixture solo se non interferisce con altri test; altrimenti consegna il piano
esatto"). Di seguito la **specifica turnkey**.

**Forma raccomandata:** uno **script standalone** dedicato (es.
`backend/test_scripts/test_db/populate_fifo_net_scenarios.py`) che crea **un broker dedicato + un asset
dedicato** e inserisce le transazioni sotto, **non** cablato nel populate di default (eseguibile on-demand),
così da non alterare le asserzioni esistenti. In alternativa, un blocco separato in `populate_mock_data.py`
protetto da flag. Regole da rispettare: **FEE/TAX con `amount<0`** e **`asset_id`** valorizzato; date coerenti
D/D-1; currency dell'asset.

**Scenario canonico M-H (Gross P&L 190 / Net P&L 177):** asset dedicato "FIFONET", broker dedicato,
currency = target.

| Data | Tipo | Qty | Amount | Note |
|------|------|-----|--------|------|
| D-10 | BUY | +10 | −1000 | 10 × 100 |
| D-5 | SELL | −4 | +480 | 4 × 120 → realized 80 |
| D-3 | DIVIDEND | 0 | +50 | income lordo |
| D-3 | FEE | 0 | −8 | `asset_id`=FIFONET (pool FEE) |
| D-3 | TAX | 0 | −5 | `asset_id`=FIFONET (pool TAX) |

Prezzo corrente 110 → Open Value 660, Open P&L 60, Realized 80, Income 50 → **Gross Total P&L 190**;
costi 13 → **Net Total P&L 177**; Gross Ret **19%**, Net Ret **17,7%**.

**Copertura 15 scenari richiesti** (ogni riga = 1 mini-set su asset/broker dedicati, senza toccare i dati
esistenti):

| # | Scenario | Costruzione minima |
|---|----------|--------------------|
| 1 | FEE su sola BUY | BUY in D + FEE in D (nessuna SELL) |
| 2 | FEE su sola SELL | BUY in D-3, SELL in D + FEE in D |
| 3 | FEE con BUY+SELL same-day | BUY in D, SELL in D, FEE in D |
| 4 | Più FEE stesso pool | 2× FEE stesso giorno/asset |
| 5 | TAX con DIVIDEND | DIVIDEND in D + TAX in D |
| 6 | TAX con INTEREST | INTEREST in D + TAX in D |
| 7 | TAX con DIVIDEND+INTEREST | entrambi in D + TAX in D |
| 8 | FEE previous-day | FEE in D, trade in D-1 |
| 9 | TAX previous-day | TAX in D, income in D-1 |
| 10 | Fallback holding | FEE in D, nessun trade/income in D né D-1, posizione aperta |
| 11 | Orphan cost | FEE in D senza alcun lotto eleggibile → `asset_orphan_fees` |
| 12 | Costo post-chiusura | SELL totale in D-1, FEE in D (serie netta con gradino, INV-4) |
| 13 | Canonico Gross190/Net177 | (tabella sopra) |
| 14 | Transfer + income sul From | TRANSFER From→To, DIVIDEND sul From durante il transito |
| 15 | Transfer + income sul To (giorno arrivo) | TRANSFER From→To, DIVIDEND sul To alla data di arrivo |

> **Nota:** il wiring dello script va **validato con la suite backend** (`./dev.py test services roi-fifo-utils`
> + eventuali E2E) in un run dedicato, per confermare che non alteri asserzioni esistenti. Consegnata qui la
> specifica; l'esecuzione è un'attività successiva.

---

## 4. Riconciliazione col Portfolio Engine (R1): scopo, valore, classificazione

### 4.1 Come stanno le cose nel codice

Il Portfolio Engine calcola income/FEE/TAX per **percorso proprio e indipendente** dal FIFO:
accumulatori `per_income[(asset_id,broker_id)]` e `per_fees_taxes[(asset_id,broker_id)]`
(`portfolio_engine.py:834-851`, pre-frame `:576-582`), con `share_percentage` applicata **inline e
sparsa** in più punti (`:224-247, :499-505, :560-563, :741-749, :1165-1191`) — **nessun choke point
pre-share unico**. Il Portfolio Engine **non** chiama il FIFO/LotsAnalysis. Il FIFO, dal canto suo, ha già
**test interni di conservazione per pool** (`TestEconomicConservation`) che bloccano
`Σ allocated + orphan == pool assoluto`.

### 4.2 Funzione primaria (5.1)

La riconciliazione pianificata verifica:

```
AllocatedIncome + AssetOrphanIncome  == PortfolioAbsoluteIncome
AllocatedFees   + AssetOrphanFees    == PortfolioAbsoluteFees
AllocatedTaxes  + AssetOrphanTaxes   == PortfolioAbsoluteTaxes
```

Serve a intercettare, **tra i due motori**: importi persi, doppio conteggio, differenze di scope,
differenze nel trattamento broker, errori nell'applicazione di `share_percentage`. È un **double-check
inter-motore**, non un calcolo che alimenta una metrica mostrata.

### 4.3 Capacità aggiuntive (5.2)

Gli accumulatori assoluti **pre-share** abiliterebbero (solo se un consumer viene costruito): esposizione
di valori assoluti indipendenti dallo share, breakdown Portfolio distinto FEE/TAX, diagnostica cross-engine,
export tecnico, banner di riconciliazione. **Nessuno** di questi è consumato oggi.

### 4.4 Classificazione (5.3)

**R1 = D (principalmente B, con C latente).** Non è **A** (prerequisito di correttezza): le metriche FIFO
mostrate oggi **non dipendono** dalla riconciliazione e sono già protette dai test di conservazione interni;
il Portfolio Engine produce già i suoi numeri per conto proprio. È un **double-check indipendente
fortemente consigliato (B)** e, negli accumulatori pre-share, un abilitatore di **nuove capacità (C)** solo
se si costruisce un consumer.

**Differibile?** **Sì**, senza cambiare **alcun** valore mostrato oggi. **Rischio residuo** senza R1: manca
un controllo end-to-end automatico che i due percorsi indipendenti (Portfolio share-weighted vs FIFO
assoluto×share) restino allineati → una futura modifica a uno dei due motori potrebbe **divergere in
silenzio**. Mitigazione consigliata (nel run dedicato): un **test** di riconciliazione (non necessariamente
accumulatori runtime) Portfolio-assoluto vs FIFO-(allocated+orphan). **Fase 9 non implementata** in questo
run (solo diagnosi + classificazione, come richiesto).

---

## 5. `net_metrics_status`: serve davvero `UNAVAILABLE`?

### 5.1 Stato nel codice

- Enum: `LotNetMetricsStatus = Literal["AVAILABLE", "UNAVAILABLE"]` (`schemas/portfolio.py:462`), default
  campo `"AVAILABLE"` (`:557`).
- **Unico punto di assegnazione:** `lots_analysis_service.py:1321` → sempre `"AVAILABLE"`.
- **Nessun path** nel motore o nel service emette `"UNAVAILABLE"`.

### 5.2 Perché il netto è **sempre** calcolabile oggi

`_converted_external_amount` fa `fx_resolver.convert(...) or amount` (`lots_analysis_service.py:1907`):
se l'FX manca, **fallback silenzioso al valore nativo**. Quindi `target_amount` non è mai `None`, i pool
FEE/TAX producono sempre `allocated_fees`/`allocated_taxes` concreti, e
`net_total_pnl = total_pnl − allocated_fees − allocated_taxes` (`:1284`) è un `Decimal` ben definito per
qualunque lotto esistente.

### 5.3 Scenari valutati (nessuno richiede `UNAVAILABLE`)

| Scenario | Producibile oggi? | Cosa produce | Netto |
|----------|-------------------|--------------|-------|
| FX mancante su pool assegnabile | Sì | Fallback nativo (`:1907`) | **Disponibile** (nativo, precisione ridotta → semmai un warning DQ, non "unavailable") |
| Conservazione fallita | No | `ALLOCATION_CONSERVATION_FAILED` non emesso (sarebbe un bug, non un dato) | n/a |
| Target amount assente | No | `target_amount` mai `None` (§5.2) | **Disponibile** |
| Pool parzialmente allocato / orphan | Sì | Il costo non attribuibile finisce in `asset_orphan_*`, il lotto riceve 0 da quel pool | **Disponibile** (netto = lordo − costi effettivamente allocati) |
| Costo con segno incoerente | Guardia interna (assert loggato), non policy | Al più DEGRADED | **Disponibile** |
| Errore quantitativo globale | Sì | → **FAILED** (§6), non una metrica netta locale | fuori scope netto per-lotto |

### 5.4 Raccomandazione (D3/R4)

**Non esiste un caso reale** in cui un lotto esista, il lordo sia affidabile, ma il suo netto non sia
calcolabile. Coerentemente con **D3**, si raccomanda la **semplificazione**: **rimuovere
`net_metrics_status`** da motore (assente), **DTO** (`schemas/portfolio.py:462,557` → `api sync`),
**frontend** (`LotCustodyModal`/`UnifiedLotsTable`: rendering "—" e gate `lotNetMetricsStatus`),
**i18n** (chiave `netMetricsUnavailable` × EN/IT/FR/ES) e **test**.

- **Non bloccante:** il campo è oggi innocuo (sempre `AVAILABLE`). È una pulizia di superficie.
- **Coordinata:** tocca DTO + `generated.ts` + frontend + i18n + test → merita un **diff dedicato**
  con `./dev.py api sync` + re-verifica. **Non** eseguita in questo run (evita di allargare lo scope di una
  review pre-commit). Alternativa legittima: **mantenerla come hook latente** se è previsto a breve un
  degrade netto su FX mancante (non lo è oggi).

---

## 6. Review dello stato `FAILED`

### 6.1 Meccanica verificata

- Codici: `_QUANTITATIVE_FAILURE_CODES = {SHORT_TRANSFER_NOT_SUPPORTED, SHORT_ADJUSTMENT_NOT_SUPPORTED,
  FIFO_SOURCE_QUANTITY_MISSING, TRANSFER_PAIR_MISSING}` (`fifo_lot_engine.py:23-27`).
- `analysis_status` (`:300-305`): `FAILED` se **un qualsiasi** issue è in quell'insieme; altrimenti
  `DEGRADED` (issue non quantitativi) o `COMPLETE`.
- **Il replay non solleva mai:** ogni handler in errore chiama `_issue(...)` (append-only, `:1013-1034`) e
  fa `return`, saltando **quella** operazione; il loop principale `for event in events:` (`:420-434`)
  **prosegue**. `run()` restituisce quindi un risultato **best-effort** (lotti/closure/economics parziali)
  + lista issue.

### 6.2 Perché FAILED è corretto (e non "troppo aggressivo")

Non è "globale perché quantitativo": è globale perché **non isolabile** nell'architettura attuale. Ogni
codice è una **rottura di topologia della quantità** che si propaga **non localmente** dentro l'asset via
ordine di consumo FIFO — una quantità fantasma/oversold cambia **quali lotti** gli eventi successivi
consumano, quindi contamina lotti che di per sé sembrano validi. Il motore **non ha partizione di
affidabilità per broker/lotto**: non può marcare "affidabili" solo i lotti non coinvolti, perché la
contaminazione passa proprio dall'ordine di consumo. → trattare l'intero asset come inaffidabile (**FAILED**)
è la scelta **safe e corretta**.

### 6.3 Tabella per-codice

| Codice | Emesso in | Perimetro reale | Replay continua? | Lotti non coinvolti affidabili? | Stato attuale | Raccomandato |
|--------|-----------|-----------------|------------------|-------------------------------|---------------|--------------|
| `TRANSFER_PAIR_MISSING` | `:519/:528/:540` | Coppia transfer rotta → quantità in transito non riconciliata; consumo FIFO a valle sul broker corrotto | Sì | **No** (cascata via ordine di consumo) | FAILED | **FAILED** ✔ |
| `FIFO_SOURCE_QUANTITY_MISSING` | `:604/:678/:710` | Sorgente (SELL/ADJ_OUT/TRANSFER) senza quantità sufficiente → oversell/phantom | Sì | **No** | FAILED | **FAILED** ✔ |
| `SHORT_ADJUSTMENT_NOT_SUPPORTED` | `:670` | ADJUSTMENT che porterebbe a posizione short (non modellata) | Sì | **No** | FAILED | **FAILED** ✔ |
| `SHORT_TRANSFER_NOT_SUPPORTED` | `:692` | TRANSFER che porterebbe a short | Sì | **No** | FAILED | **FAILED** ✔ |

**Nessuna riclassificazione.** Motivazione unica e trasversale: assenza di partizione di affidabilità →
cascata non locale. *Nota architetturale (futuro):* un motore con **partizionamento per broker** potrebbe
degradare a scope-broker anziché all'intero asset; oggi quel partizionamento **non esiste**, quindi non è
una modifica di classificazione ma di architettura (fuori scope release).

### 6.4 Cosa mostra il frontend con `calculation_status=FAILED`

Verificato in `LotsAnalysisPanel.svelte`:

- Banner rosso `data-testid=lots-analysis-panel-failed` con testo **esplicito** (`:427-431`): IT *"L'analisi
  dei lotti non è stata ricostruita in modo affidabile … i valori potrebbero essere incompleti"* (idem
  EN/FR/ES).
- **Il pannello NON viene nascosto:** il ramo `{:else}` (`:446-500`) renderizza comunque WAC chart, Gantt,
  `UnifiedLotsTable` e `LotComparisonChart`. Gross **e** netto restano visibili; i lotti restano
  consultabili.

**Semantica "warn but show":** si avverte che i numeri possono essere inaffidabili ma li si lascia
ispezionabili per diagnosi. È **coerente** col testo del banner. (La checklist M-K è stata corretta: la
vecchia dicitura "gross degli altri lotti intatto" era fuorviante — non c'è garanzia di isolamento per-lotto
in FAILED.)

---

## 7. Test "doppio click" e mappa delle modali

### 7.1 Cosa intendeva la checklist e perché era errata

La checklist indicava *"Doppio click su lotto con FEE/TAX → `LotCustodyModal`"*. **Il doppio click non apre
alcuna modale.** In `LotsAnalysisPanel.svelte` il doppio click è **navigazione incrociata**:

- doppio click **riga tabella** → `handleTableRowDoubleClick` (`:363`) = pulse della corsia Gantt;
- doppio click **corsia Gantt** → `handleGanttRowDoubleClick` (`:369`) = scroll alla riga di tabella;
- doppio click **evento su WAC chart** → `handleEventDoubleClick` (`:376`) = selezione lotti + pulse.

### 7.2 Percorso canonico verso la modale

`LotCustodyModal` si apre **solo** tramite `handleCustodyCellClick` (`:335-338`, imposta `modalLot` +
`modalOpen`), raggiunto da:

1. **menu azioni riga (kebab) → "Dettaglio lotto"** (`UnifiedLotsTable.svelte` rowActions `:402-408`,
   label `brokers.lots.viewLotDetail`, IT "Dettaglio lotto", icona Eye) → `onCustodyCellClick`;
2. **click sulla cella custody-badge** della riga → stesso handler.

### 7.3 Mappa esplicita (Componente → interazione → handler → risultato)

| Componente UI | Interazione | Handler | Risultato / Modale | Mobile |
|---------------|-------------|---------|--------------------|--------|
| `UnifiedLotsTable` riga | menu kebab → "Dettaglio lotto" | `onCustodyCellClick`→`handleCustodyCellClick` | **Apre `LotCustodyModal`** | ✅ (menu azioni) |
| `UnifiedLotsTable` cella custody-badge | click | `handleCustodyCellClick` | **Apre `LotCustodyModal`** | ✅ |
| `UnifiedLotsTable` riga | **doppio click** | `handleTableRowDoubleClick` (`:363`) | Pulse corsia Gantt (no modale) | ⚠️ dblclick poco pratico |
| `LotGanttChart` corsia | **doppio click** | `handleGanttRowDoubleClick` (`:369`) | Scroll a riga tabella (no modale) | ⚠️ |
| `LotWacPriceChart` evento | **doppio click** | `handleEventDoubleClick` (`:376`) | Selezione lotti + pulse (no modale) | ⚠️ |
| `UnifiedLotsTable` riga | menu → "Vai al lotto nel Gantt" | `onViewGanttLot` (`:410-416`) | Scroll/evidenzia Gantt | ✅ |

**Una sola modale** in questo pannello: `LotCustodyModal`. Non esistono altre modali FIFO che la checklist
avrebbe dovuto far verificare. → checklist **corretta** (M-M canonico = azioni riga / custody-cell; aggiunta
M-M3 per documentare il doppio click come cross-nav). **Nessuna nuova gesture introdotta.**

---

## 8. `net_pnl` vs `net_total_pnl` (R2) e provenienza (R3)

### 8.1 Formule confermate (asimmetria **voluta**)

| Campo | Formula | Include income? | Citazioni |
|-------|---------|-----------------|-----------|
| `summary.net_total_pnl` | `total_pnl − allocated_fees − allocated_taxes` (dove `total_pnl = market_pnl + realized_pnl + asset_income`) | **Sì** | service `:1284`, schema `:555` |
| `summary.net_total_return` | `net_total_pnl / opening_value` | Sì | service `:1286`, schema `:556` |
| `value_history.net_pnl` | `pnl − allocated_fees − allocated_taxes` (dove `pnl` = market+realized, **senza** income) | **No** (capital-only) | service `:1653`, schema `:637` |
| `return_history.net_total_return` | `(total_value + income − allocated_fees − allocated_taxes)/original_cost − 1` | **Sì** | service `:1730`, schema `:654` |

Ogni linea **netta** rispecchia la propria controparte **lorda** meno i costi: `value_history.net_pnl`
esclude income perché il suo lordo `pnl` lo esclude; `return_history.net_total_return` lo include perché il
rendimento totale lo include. Coerente **dentro** ciascuna serie.

### 8.2 Quale campo per il futuro grafico economico netto

Il **titolo/valore di sintesi** del grafico netto deve usare i campi **income-inclusive**
`summary.net_total_pnl` / `summary.net_total_return` (coerenti con la tabella). Per la **serie temporale**,
`return_history.net_total_return` è la serie netta income-inclusive da plottare; `value_history.net_pnl` è
**capital-only** e va etichettato come tale (o, in futuro, affiancato da una serie netta di P&L totale
income-inclusive, oggi **non** presente come campo). **Rischio da evitare in R2:** plottare `net_pnl`
capital-only come se fosse il netto totale.

### 8.3 R3 — provenienza nel modal

La modale mostra già correttamente il **breakdown numerico** (Gross → −Fees → −Taxes → Net), ma **non** la
provenienza (pool, regola, source tx, weight, native/target amount). I dati di provenienza **esistono già
nel DTO**: `EconomicAllocationGroupSchema` (`schemas/portfolio.py:769`, `source_transaction_ids:781`), campo
response `economic_allocation_groups` (`:838`), popolato dal service (`:508`, map `:1171-1184`). Il
**frontend non li consuma** (0 riferimenti in `components/brokers/lots`). → **R3 è puramente frontend**:
solo la *spiegazione della provenienza*, non matematica né breakdown (già visibili). Forma minima proposta:
un accordion **"Come sono stati allocati i costi"** nel `LotCustodyModal` che elenca, per gruppo: regola,
target operation, source transaction IDs, weight, native amount → target amount. **Non implementato** in
questo run.

---

## 9. Stato dei rinvii R1–R4

| ID | Tema | Classificazione | Azione in questo run | Differibile? |
|----|------|-----------------|----------------------|--------------|
| **R1** | Riconciliazione Portfolio Engine (accumulatori pre-share) | **D** (B double-check + C latente) | Solo diagnosi/classificazione (§4) | **Sì** — nessun valore mostrato cambia; rischio residuo = nessun test cross-engine |
| **R2** | Serie nette nei grafici | Chiarita semantica (§8) | Documentazione campi; **non** implementato | Sì |
| **R3** | Provenienza audit nel modal | Solo frontend (dati già nel DTO) | Proposto accordion; **non** implementato | Sì |
| **R4** | `net_metrics_status` / `UNAVAILABLE` | **Rimozione raccomandata** (§5) | Diagnosi + raccomandazione; **non** rimosso | Sì (pulizia coordinata dedicata) |

---

## 10. File modificati / creati in questo run

| File | Tipo | Contenuto |
|------|------|-----------|
| `frontend/src/lib/components/table/DataTable.svelte` | **modificato** | Fix colonne nette (modello a override — §2.4). Unica modifica di codice del run. |
| `.../v4-fee_tax_integration/review-checklist-v5.md` | **modificato** | Corretti M-M (percorso modale), M-M2 (UNAVAILABLE non producibile → R4), M-K (semantica FAILED); aggiunto M-M3 (doppio click = cross-nav); nota di correzione. |
| `.../v4-fee_tax_integration/post-implementation-review-v5.md` | **creato** | Questo report. |

Nessuna modifica a backend/schemi/test/DTO/i18n in questo run.

---

## 11. Check / test eseguiti

| Comando | Esito |
|---------|-------|
| `./dev.py front check` | **0 errori / 0 warning** |
| `./dev.py front format` | pulito |
| `./dev.py front build` | **OK** |

Analisi backend condotta per sola lettura del codice (nessun test backend modificato/aggiunto). Nessun test
grafico automatico aggiunto (preferenza esplicita).

---

## 12. Da correggere / confermare **prima** del commit

1. **[FATTO]** Fix colonne nette in `DataTable.svelte` — verificata (front check/format/build verdi).
2. **[CONFERMA UTENTE]** Trade-off storage `columnVisibility → columnVisibilityOverrides` (§2.5): perdita
   una-tantum delle preferenze show/hide colonne su tutte le tabelle `DataTable` (ordine/larghezze
   preservati). Accettare o richiedere migrazione legacy.
3. **[VERIFICA MANUALE]** Sul DB con costi asset-linked (prod dell'utente): aprire un asset con
   FEE/TAX allocate → confermare che le 4 colonne nette compaiano di default e che **Reset layout** le
   ripristini (percorso M-L / M-H della checklist).

## 13. Legittimamente differibili (run dedicati)

- **Fixture FIFO net** (§3.3): script standalone 15 scenari + validazione suite.
- **R4** rimozione `net_metrics_status` (§5.4): diff coordinato DTO+FE+i18n+test + `api sync`.
- **R1** test di riconciliazione cross-engine (§4.4).
- **R2** serie nette nei grafici (§8.2) usando i campi income-inclusive.
- **R3** accordion provenienza nel modal (§8.3).

---

*Fine report. Nessun commit eseguito. Risposte e prosa in italiano su richiesta dell'utente.*
