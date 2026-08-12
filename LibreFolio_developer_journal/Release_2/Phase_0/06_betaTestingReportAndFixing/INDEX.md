# Beta Testing — Report, Analisi e Piani di Fix

> Sessione di beta testing del **05/08/2026** con l'utente **Marco** (inserimento da zero dei
> propri report Crédit Agricole su **server Linux di produzione**, non su localhost).
> Fonte primaria: [`00_20260805_betaTester_report.md`](00_20260805_betaTester_report.md).

---

## 1. Contesto della sessione

| Elemento | Valore |
|---|---|
| Data | 05/08/2026 (+ code 06/08 mattina) |
| Ambiente | Server Linux di produzione (Docker), **non** localhost |
| Broker | Un unico broker "Crédit Agricole" |
| File importati | **3 file XLSX contemporaneamente** |
| Cartella sorgente | `~/Downloads/01_ReportFinaziari/CreditAgricole_NonnaAnna/` |
| Riferimento di verità | `Totali_05082026/Andamento Portafoglio_CAI_20260805174957.xlsx` |
| Copertura temporale report | fino a **luglio 2026** |

I 3 file coprono **due layout diversi** dello stesso broker:

| File | Layout | Righe |
|---|---|---|
| `Lista Movimenti Deposito Titoli_CAI_20240605-20240801.xlsx` | Deposito Titoli (titoli, con quantità) | 63 |
| `Lista Movimenti_CAI_20240801-20241231.xlsx` | Movimenti Conto (cassa reale) | 110 |
| `Lista Movimenti_CAI_20241028-20260731.xlsx` | Movimenti Conto (cassa reale) | 476 |

> ⚠️ **Nota metodologica permanente**: Crédit Agricole ha **due layout di import distinti**
> gestiti dallo stesso plugin — *Deposito Titoli* (con controparti cash artificiali) e
> *Movimenti Conto* (cassa reale). Non vanno mai semplificati o unificati.

### Correzioni manuali già applicate dal tester

Per poter proseguire il test, il tester ha corretto a mano alcune transazioni: le ha
**trovate, duplicate come acquisti, e cancellate le originali** (che erano state salvate come
generici prelievi/depositi). Questo spiega perché alcuni asset risultano corretti in dashboard
pur essendo affetti dallo stesso bug. (affermazione vera nel server linux docker)

---

## 2. Esito dell'analisi — sintesi esecutiva

### 2.1 Una sola causa radice spiega entrambe le anomalie contabili

Il plugin Crédit Agricole **non ha un ramo per la causale `COMPRAVENDITA TITOLI/FONDI/OPZIONI`**.
Tali righe cadono nel fallback generico `DEPOSIT/WITHDRAWAL by sign`
(`broker_credit_agricole.py:591-629`). Risultato: **ogni acquisto/vendita presente solo
nell'estratto conto viene perso come movimento di cassa**, e la posizione non viene mai aperta.

Nei file del tester questo colpisce **4 righe su 4**. Tre erano già state corrette a mano;
la quarta — **BTP 01/03/35 3,35%** — no, ed è esattamente il buco da ~50k.

### 2.2 Il patrimonio netto NON ha un doppio conteggio

L'ipotesi del tester ("sommiamo due volte dividendi e interessi") è stata **verificata e
smentita**. Dettaglio completo in [`02_riconciliazione_credit_agricole.md`](02_riconciliazione_credit_agricole.md).
In breve: la formula è a conteggio singolo, già coperta da invariante di test, e il "530k"
della banca è il **controvalore titoli soltanto** — non confrontabile con un patrimonio netto
che include la liquidità.

### 2.3 Numeri chiave

| Grandezza | Valore |
|---|---:|
| Ctv di carico totale (Excel banca) | 529.887,94 € |
| Ctv di carico BTP 01/03/35 (mancante) | 50.018,11 € |
| **Differenza → carico atteso in LibreFolio** | **479.869,83 €** ≈ *i 480k osservati* ✅ |
| Ritenute estraibili ma mai registrate | 2.203,42 € (su 56 cedole) |

---

## 3. Documenti di questa cartella

| File | Contenuto |
|---|---|
| [`00_20260805_betaTester_report.md`](00_20260805_betaTester_report.md) | Report grezzo della sessione (fonte primaria, non modificare) |
| [`01_tassonomia_findings.md`](01_tassonomia_findings.md) | Classificazione dei 34 rilievi nelle 4 categorie richieste + severità + destinazione |
| [`02_riconciliazione_credit_agricole.md`](02_riconciliazione_credit_agricole.md) | Dossier numerico e metodo per la sessione di verifica congiunta |

## 4. Piani di fix

| ID | Piano | Ambito | Rilievi | Priorità | Stato |
|---|---|---|---|---|---|
| **P1** | [`plan-phase00BrimCreditAgricoleTrades.prompt.md`](plan-phase00BrimCreditAgricoleTrades.prompt.md) | Plugin BRIM Crédit Agricole | B1–B8 | 🔴 Bloccante | **Fase A ✅ · 🛑 checkpoint di collaudo · Fase B ⏳** |
| **P1‑bis** | [`plan-phase00ImportFlowStepRestructure.prompt.md`](plan-phase00ImportFlowStepRestructure.prompt.md) | **Ordine del flusso di import**: correzione prima del confronto duplicati | — | 🔴 Alta | ✅ **fatto** 2026‑08‑07 — endpoint `/brokers/import/duplicates`, macchina a stati per id con auto‑skip, step «Correzioni» e step «Duplicati» (cross‑file + collisioni DB). Test: 27 API · 463 provider · 18 E2E. *Slot libero per «Unifica asset» (WS‑C) fra `analyze` e `fix`* |
| **P2** | [`plan-phase00ImportWizardUx.prompt.md`](plan-phase00ImportWizardUx.prompt.md) | Wizard di import | W1–W12 | 🟠 Alta | ⏳ |
| **P3** | [`plan-phase00AssetIdentityAndIdentifiers.prompt.md`](plan-phase00AssetIdentityAndIdentifiers.prompt.md) | **Identità dell'asset**: unificazione, identificativi, ciclo di vita | A1–A5, **A6** ➕, **W2** *(da P2)*, **W6** *(assorbito da P2)* | 🔴 Alta (A1 grave) | **Onda 1 ✅ · Onda 2 ✅ codice completo (08/08) — resta il collaudo estetico + E2E (F‑01)** |
| **P4** | [`plan-phase00EngineAccountingAndSignals.prompt.md`](plan-phase00EngineAccountingAndSignals.prompt.md) | Motore contabile e segnali | E1–E2 | 🟠 Media | ⏳ |
| **P5** | [`plan-phase00TransactionsUxPolish.prompt.md`](plan-phase00TransactionsUxPolish.prompt.md) | UX transazioni | T1–T4 | 🟠 Media | ⏳ |
| **P6** | [`plan-phase00I18nAndDocsAssets.prompt.md`](plan-phase00I18nAndDocsAssets.prompt.md) | i18n, font, documentazione | I1–I4 | 🟡 Bassa | ⏳ |
| **P7** | [`plan-phase00FrontendCoverage.prompt.md`](plan-phase00FrontendCoverage.prompt.md) | **Coverage JavaScript**: misurare il frontend, non solo il backend | — | 🟠 Media | ✅ Completo (12/08) — fasi 0/A/B/C/D/E/F/G. Resta solo la prima misura vera, da fare a test E2E finiti. *Nasce da P3: i difetti si nascondevano in codice frontend non misurato* |

> **P1 è stato riorganizzato in due fasi con un collaudo in mezzo** (v3, 06/08/2026). La Fase A
> costruisce la rete di pre-allarme *lasciando volutamente sbagliati i 4 trade*, che sono l'unico
> caso reale su cui la rete si possa validare. La Fase B ripara il plugin, e non parte prima del
> consenso sulla UI.

### Ordine di attacco consigliato

```
P1 ──▶ (riconciliazione congiunta con l'utente) ──▶ P3 ──▶ P2 ──▶ P5 ──▶ P4 ──▶ P6
 │                                                   │
 │ sblocca i totali e la fiducia nei dati            │ A1 è grave: forza la creazione
 │                                                   │ di asset duplicati
```

**Perché P1 per primo**: finché gli acquisti si perdono, ogni altra verifica sui totali è
inaffidabile. **Perché P3 subito dopo**: A1 (impossibile selezionare un asset disattivato)
costringe l'utente a creare asset duplicati, cioè *sporca il database in modo permanente*
mentre lavoriamo — è un danno che cresce nel tempo.

---

## 5. Stato di avanzamento

| ID | Titolo | Stato |
|---|---|---|
| — | Analisi e classificazione dei rilievi | ✅ Completato (06/08/2026) |
| — | Riconciliazione numerica Excel ↔ dashboard | ✅ Completato (06/08/2026) |
| P1 | Plugin Crédit Agricole — compravendite | ✅ Completato (08/08/2026) · Fase A+B implementate, collaudate dall'utente e blindate a test (48 backend + 13 di contratto + 12 E2E) |
| P1‑bis | Ordine del flusso di import (7 step condizionali) | ✅ Completato (07/08/2026) · E2E riallineato al flusso a 7 step (12 test) |
| P2 | Wizard di import | ⏳ Da iniziare |
| P3 | Identità dell'asset: unificazione, identificativi, ciclo di vita | ✅ Completato (08/08/2026) · UI approvata dall'utente; E2E scritti: 7 `tx-import-asset-identity` + 3 `asset-merge` + 7 API di fusione |
| P4 | Motore contabile e segnali | ⏳ Da iniziare |
| P5 | UX transazioni | ⏳ Da iniziare |
| P6 | i18n, font, documentazione | ⏳ Da iniziare |
| P7 | Coverage JavaScript (livelli A e B) | ✅ Fasi 0/A/B/C/E completate (12/08/2026) · `--coverage [py\|js\|all]`, 3 nuovi report JS, 64 spec migrati al barrel. Fase D (analizzatore buchi) aperta |

---

## 6. Punti aperti da riverificare con il tester

Due rilievi del report sono **contraddetti dal codice**. Vanno riprodotti insieme prima di
pianificarne la fix — vedi [`01_tassonomia_findings.md`](01_tassonomia_findings.md) §5.

| Rilievo | Contraddizione |
|---|---|
| "non posso riportare attivo un asset disattivato dal modifica" | Il toggle `active` **esiste** ed è sempre renderizzato — `AssetModal.svelte:1860-1873` |
| "anche export AI è disattivo" | L'AI export **non filtra** per `Asset.active` — `runtime_service.py:586` |
