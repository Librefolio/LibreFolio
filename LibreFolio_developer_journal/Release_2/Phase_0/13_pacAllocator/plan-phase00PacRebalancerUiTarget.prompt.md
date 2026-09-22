# PAC & Rebalancer — UI target completa

> **Stato:** TARGET CORRENTE — Review A/B/C/D e configurazione finale approvate
> dal developer; nessuna implementazione autorizzata da questo file.
> **Tipo:** piano visuale completo con tutte le ASCII approvate.
> **Suite target:** [piano maestro](plan-phase00PacRebalancerTargetDesign.prompt.md) ·
> [nucleo matematico](plan-phase00PacRebalancerMathematicalCore.prompt.md) ·
> [policy, obiettivi e vincoli](plan-phase00PacRebalancerPolicies.prompt.md) ·
> [architettura](plan-phase00PacRebalancerArchitecture.prompt.md) ·
> [bundle implementativo](implementation/README.md).
> **Baseline letta:** P1 `pac_allocator` + `portfolio_rebalancer`, Tool Host generico
> **Gate:** rilievi della review indipendente incorporati il 2026-09-16; bundle
> implementativo materializzato ma codice non autorizzato. Restano aperti risultato
> product-shaped, dipendenza e capacità MIQP/MIQCP SCIP; proof/status sono
> congelati.
> **Correzione dati 2026-09-16:** layout approvato invariato; PAC e Rebalancer
> mostrano un primario globale `L2_fixed` e una variante margine BUY-only che
> congela il primario. D∞/D1 e percentuali finali sono diagnostici.

## Come leggere l'artifact

Le Review A/B/C/D e la configurazione finale sono state approvate dal developer.
La Review A ha congelato:

1. ingresso nei due Tool;
2. ordine e nomi degli step;
3. gerarchia desktop/mobile;
4. densità;
5. navigazione e riepilogo;
6. persistenza del draft durante avanti/indietro.

Le schermate funding, Broker, Asset, routing, target, FX, strategie e risultati
verranno disegnate nei blocchi successivi **dentro la shell approvata**.

### Legenda visuale

| Simbolo | Significato |
|---|---|
| `[S]` | fatto copiato dal sistema, con fonte/data |
| `[M]` | dato inserito o modificato manualmente |
| `[D]` | riepilogo derivato dal draft, non calcolo economico |
| `[B]` | risultato prodotto dal backend dopo submit |
| `*` | campo obbligatorio |
| `!` | step incompleto o dato da verificare |
| `v` | step localmente completo |
| `~` | dato copiato poi modificato |
| `>` | step attivo |

---

# 1. Confini UX già congelati

- Due card, due route, due renderer:
  - **PAC Allocator**: liquidità nuova/selezionata → soli BUY.
  - **Ribilanciatore di portafoglio**: portafoglio corrente → BUY e, se
    autorizzato, SELL.
- Nessun selettore PAC/Rebalancer dentro il form.
- Un solo volo: input completi → review snapshot → compute backend → risultati.
- Nessuna preview economica nel target.
- Copy/autofill crea proposta modificabile; nessun binding live.
- Nessun ordine eseguito.
- Frontend non calcola allocazione, fee, FX operativo, quantità, tax reserve o
  fattibilità.
- Cash, ordini, trasferimenti e FX restano nelle valute native.
- Valuta di riferimento serve soltanto a confronti, target e grafici.
- P1 non va preservato: prodotto non ancora rilasciato.

---

# 2. Audit visuale P1 → target

| Superficie corrente | Valore da conservare | Problema P1 | Direzione blueprint |
|---|---|---|---|
| `ToolsHub` | card catalogo, docs, fail-closed | descrizioni analysis-only | due card con domanda operativa e confine BUY/SELL |
| `ToolHost` | header, docs, versioni, account generation, reload sicuro | renderer apre form monolitico | host invariato; renderer apre wizard |
| `PacAllocatorTool` | guardie request/draft/account | sezioni tutte insieme, `analyze` | shell PAC progressiva |
| `PortfolioRebalancerTool` | guardie request/draft/account | funding opzionale, nessun ordine | shell Rebalancer progressiva |
| `PacMoneySection` | Decimal, currency select, Broker icon | seleziona l'intero saldo Broker o manuale | righe fonte esplicite con importo scelto |
| `OwnedAssetGallery` | ricerca, scope, provenance, manuale | P1 non separa Asset e route operative | selezione Asset nello Step 4 |
| `PacAssetEditor` | prezzo/provenance | `buy_grid` e `quantity_step` sull'Asset | prezzo/metadata; capability al Broker |
| `RebalanceHoldingEditor` | custodia per Broker, quantità esatta | PMC/tax/SELL assenti | holding completa, PMC e tax |
| `AllocationTargetEditor` | totale Decimal esatto, DataTable | target dentro form lungo | step dedicato, nessuna preview |
| `AllocationFxSection` | copy con stale guard | solo FX di report | FX operativo con spot/source/age/spread/buffer |
| result panel P1 | DataTable e diagnostics | importi/gap teorici | piano operativo con due profili confrontabili |

## 2.1 Componenti generici da riusare come linguaggio visuale

- card `rounded-xl`;
- `DataTable` + `ColumnVisibilityToggle`;
- `CompactCashCell` per importo+valuta;
- comportamento quantità raffinato in `TransactionFormModal`, da estrarre in un
  input condiviso prima di usarlo nei planner;
- `ExactDecimalInput` per Decimal/percentuali non monetarie;
- `CurrencySearchSelect`;
- `AssetSelect` / `BrokerSearchSelect`;
- `SingleDatePicker`;
- `AssetIcon` / `BrokerIcon`;
- `DocsLink`;
- `ConfirmModal` e modali Asset/Broker esistenti;
- badge scope/provenance/stale;
- `AllocationPieChart`, `GeographyMap`, ECharts e `KpiCard` nei risultati;
- dark mode;
- focus ring LibreFolio;
- `data-testid` come selettore, mai testo o classi.

Regola Phase 2: prima cercare/adattare un componente condiviso, poi crearne uno
nuovo soltanto se il contratto manca. Nessuna seconda implementazione di parsing
Decimal, raw edit buffer, selezione Asset/Broker, tabella o icona.

Componenti feature-level P1 obsoleti non vanno preservati per compatibilità; i
primitive condivisi maturi sì. Indice completo: §20.21.

---

# 3. Architettura informativa

## 3.1 Entry e route

```text
/tools
  |
  +-- PAC Allocator --------------------> /tools/pac_allocator
  |      Domanda: come investire cash?
  |      Confine: BUY, portafoglio iniziale zero
  |
  +-- Ribilanciatore di portafoglio ----> /tools/portfolio_rebalancer
         Domanda: come avvicinare tutto il portafoglio al target?
         Confine: BUY; SELL solo se autorizzato
```

La scelta Tool avviene nella card. Lo Step 1 non ripropone un selettore: mostra il
Tool bloccato e raccoglie data + valuta di riferimento.

## 3.2 Step condivisi

| # | Label UI | PAC | Rebalancer |
|---:|---|---|---|
| 1 | Scenario | Tool fisso, data, valuta riferimento | Tool fisso, data, valuta riferimento |
| 2 | Liquidità | fonti e importi da investire | cash/contributi disponibili prima di eventuali SELL |
| 3 | Broker | luoghi ammessi per BUY | luoghi ammessi per BUY/SELL |
| 4 | Asset | Asset target, quantità iniziale zero | Asset + custodie/holding correnti |
| 5 | Routing | Asset×Broker BUY | Asset×Broker BUY/SELL |
| 6 | Target | pesi nuova allocazione | pesi finali intero portafoglio investito |
| 7 | FX | conversioni potenziali | conversioni potenziali |
| 8 | Strategia | Residuo proporzionale / Minima frammentazione | Investi soltanto / Investi e vendi |
| 9 | Rivedi | snapshot PAC immutabile | snapshot Rebalancer immutabile |
| 10 | Risultato | fuori dallo stepper di input | fuori dallo stepper di input |

## 3.3 Perché “Scenario” resta Step 1

La card sceglie il servizio, ma data e valuta di riferimento sono input del
calcolo. Tenerli in uno step corto:

- evita header sovraccarico;
- rende esplicita la valuta tecnica;
- consente provenance della valuta predefinita;
- evita che data/valuta sembrino preferenze globali live;
- crea un inizio identico per entrambi i Tool.

---

# 4. Contratto delle schermate

| Step | Input utente | Copy/autofill | Derivati UI ammessi | Vietato in UI |
|---|---|---|---|---|
| Scenario | data, valuta riferimento | valuta utente | Tool fisso, stato compatibilità | pesi o valore futuro |
| Liquidità | fonte, valuta, disponibile dichiarato, importo scelto | conti/Broker/saldi autorizzati | totali nativi; equivalente indicativo con fonte | trasferimenti finali |
| Broker | origine, capability, fee, regime, minus | identità e fatti Broker | completezza capability | scelta route/ordini |
| Asset | identità, prezzo, quote basis, holding, PMC, tax | Asset/Portfolio/prices | staleness; valore informativo dichiarato dal dominio | quantità BUY/SELL |
| Routing | eleggibilità, priorità, vincoli per lato | compatibilità nota | warning di compatibilità | split effettivo |
| Target | percentuali | distribuzione corrente come base modificabile | somma esatta e restante | preview economica |
| FX | spot, source/date, spread, buffer, fee | dominio FX | età/staleness e coppie potenziali | conversioni scelte |
| Strategia | enum e soli parametri del ramo | default dichiarato | spiegazione conseguenze | coefficienti nascosti |
| Rivedi | conferme finali | nessun refresh automatico | diff/stato/completezza | compute parziale |
| Risultato | selettore coppia risultati | risposta backend | formattazione e filtri | ricalcolo economico |

## 4.1 Stato di ogni step

```text
Non iniziato     ○  nessun dato richiesto inserito
In corso         !  draft presente ma incompletezza locale
Completo         v  validazione locale superata
Modificato       ~  fatto copiato modificato manualmente
Da rivedere      !  dipendenza precedente cambiata
Attivo           >  pannello aperto
```

Uno step “completo” non dichiara fattibilità. Significa soltanto che input locali
richiesti sono presenti e ben formati.

---

# 5. ASCII A0 — Tools Hub desktop

Viewport: desktop 1440 px.

```text
+------------------------------------------------------------------------------------------------------------------+
| [chiave inglese] Tools                                                                      [ Aggiorna catalogo ] |
| Calcoli indipendenti. Nessuna modifica viene scritta nel portafoglio.                                             |
+------------------------------------------------------+-----------------------------------------------------------+
| [monete] PAC Allocator                         [Docs] | [bilancia] Ribilanciatore di portafoglio             [Docs] |
|                                                      |                                                           |
| Distribuisce la liquidità scelta tra gli Asset       | Avvicina l'intero portafoglio ai pesi target con          |
| target e prepara funding, FX e ordini BUY.           | acquisti e, solo se autorizzato, vendite.                 |
|                                                      |                                                           |
| [ BUY ] [ Portafoglio iniziale zero ]                | [ BUY ] [ SELL opzionali ] [ Holding correnti ]           |
|                                                      |                                                           |
| Backend/API 1.0.0 · UI 1.0.0                    -->  | Backend/API 1.0.0 · UI 1.0.0                        -->  |
+------------------------------------------------------+-----------------------------------------------------------+
```

**Intento:** scegliere il problema, non una modalità dentro un mega-form.
**Azioni:** intera card apre il Tool; Docs resta link indipendente.
**Stati:** ready, loading interface, unavailable, degraded già gestiti dal Hub.
**Decisione estetica:** card simmetriche, differenza resa da icona + domanda +
badge semantici, mai dal solo colore.

---

# 6. ASCII A1 — PAC desktop, Step 1 “Scenario”

Viewport: desktop 1440 px. Tool Host sopra; renderer sotto.

```text
+------------------------------------------------------------------------------------------------------------------+
| <- Tools                                                                                 [Docs] [Aggiorna Tool]    |
| PAC Allocator                                                                                                    |
| Trasforma la liquidità selezionata in funding, FX e ordini BUY eseguibili.                                       |
| Backend/API 1.0.0 · UI 1.0.0                                                                                     |
+------------------------------------------------------------------------------------------------------------------+
| CONFIGURA PAC                         Passo 1 di 9 · Scenario                                      Bozza non salvata |
+----------------------+---------------------------------------------------------------------+----------------------+
| PASSI                | SCENARIO                                                            | RIEPILOGO PAC        |
|                      |                                                                     |                      |
| > 1  Scenario        | [monete] PAC Allocator                                              | Scenario             |
| ○ 2  Liquidità       | Il Tool è già scelto. Per cambiare, torna a Tools.                  | Data       15/09/2026|
| ○ 3  Broker          |                                                                     | Valuta     EUR       |
| ○ 4  Asset           | +-----------------------------------------------------------------+ |                      |
| ○ 5  Routing         | | Data del piano *                                                | | Liquidità           |
| ○ 6  Target          | | [ 15/09/2026                         ]                           | | Non configurata     |
| ○ 7  FX              | |                                                                 | |                      |
| ○ 8  Strategia       | | Valuta di riferimento *                  [S] Preferenza utente  | | Broker              |
| ○ 9  Rivedi          | | [ EUR - Euro                         v ]                        | | Nessuno             |
|                      | | Serve solo per target, confronti e grafici.                     | |                      |
|                      | +-----------------------------------------------------------------+ | Asset               |
|                      |                                                                     | Nessuno             |
|                      | [i] Ordini, cash e trasferimenti resteranno nelle valute native.    |                      |
|                      |                                                                     | Target        --     |
|                      |                                                                     | Strategia     --     |
+----------------------+---------------------------------------------------------------------+----------------------+
|                       [ Esci ]                                           [ Continua -> ]                           |
+------------------------------------------------------------------------------------------------------------------+
```

**Intento:** fissare contesto tecnico senza simulare risultati.
**Input visibili:** data, valuta riferimento.
**Derivati:** nome Tool, compatibilità, origine del prefill.
**Azioni:** Esci; Continua.
**Stati:** prefill, modificato, mancante, data non valida.
**Privacy:** nessun valore finanziario nello Step 1.

### Nota CTA

CTA primaria: **Continua**. “Salva e continua” è escluso perché suggerirebbe una
persistenza DB che la v1 non offre.

---

# 7. ASCII A2 — Rebalancer desktop, stessa shell

```text
+------------------------------------------------------------------------------------------------------------------+
| <- Tools                                                                                 [Docs] [Aggiorna Tool]    |
| Ribilanciatore di portafoglio                                                                                    |
| Pianifica acquisti e, se autorizzato, vendite per avvicinare l'intero portafoglio al target.                     |
| Backend/API 1.0.0 · UI 1.0.0                                                                                     |
+------------------------------------------------------------------------------------------------------------------+
| CONFIGURA RIBILANCIAMENTO               Passo 1 di 9 · Scenario                                  Bozza non salvata |
+----------------------+---------------------------------------------------------------------+----------------------+
| PASSI                | SCENARIO                                                            | RIEPILOGO            |
|                      |                                                                     |                      |
| > 1  Scenario        | [bilancia] Ribilanciatore di portafoglio                            | Scenario             |
| ○ 2  Liquidità       | Il Tool considera il portafoglio investito corrente.                | Data       15/09/2026|
| ○ 3  Broker          |                                                                     | Valuta     EUR       |
| ○ 4  Asset           | +-----------------------------------------------------------------+ |                      |
| ○ 5  Routing         | | Data del piano *                [ 15/09/2026              ]     | | Portafoglio         |
| ○ 6  Target          | | Valuta di riferimento *        [ EUR - Euro              v ]     | | Non copiato         |
| ○ 7  FX              | +-----------------------------------------------------------------+ |                      |
| ○ 8  Strategia       |                                                                     | Liquidità           |
| ○ 9  Rivedi          | [i] Nessuna vendita sarà proposta finché non sceglierai              | Non configurata     |
|                      |     esplicitamente “Investi e vendi” nello Step 8.                    |                      |
|                      |                                                                     | Modalità            |
|                      |                                                                     | Investi soltanto    |
+----------------------+---------------------------------------------------------------------+----------------------+
|                       [ Esci ]                                                   [ Continua -> ]                  |
+------------------------------------------------------------------------------------------------------------------+
```

**Differenza strutturale:** shell identica; icona, titolo, descrizione, summary e
microcopy dichiarano portafoglio corrente e SELL opzionali.
**Default policy visibile ma non ancora editabile:** “Investi soltanto”. Mostra il
confine sicuro, non completa lo Step 8.

---

# 8. ASCII A3 — Desktop, step avanzato e densità

Esempio di shell con Step 5 attivo. Il contenuto specifico verrà disegnato in
Review B; qui conta la gerarchia.

```text
+------------------------------------------------------------------------------------------------------------------+
| CONFIGURA PAC                             Passo 5 di 9 · Routing                              Ultima modifica 14:32 |
+----------------------+---------------------------------------------------------------------+----------------------+
| PASSI                | ASSET x BROKER                                                     | RIEPILOGO PAC        |
| v 1  Scenario        | Scegli dove ogni Asset può essere acquistato e con quali vincoli.  |                      |
| v 2  Liquidità       |                                                                     | Liquidità nativa     |
| v 3  Broker          | +-----------------------------------------------------------------+ | EUR  3.500,00       |
| v 4  Asset           | | XMAW World                                      2 route       | | USD    500,00       |
| > 5  Routing         | | [contenuto dettagliato nei §§10-18]                           v | |                      |
| ○ 6  Target          | +-----------------------------------------------------------------+ | Broker      2 v      |
| ○ 7  FX              |                                                                     | Asset       4 v      |
| ○ 8  Strategia       | +-----------------------------------------------------------------+ | Routing     3/4 !    |
| ○ 9  Rivedi          | | HEAL Healthcare                                  1 route       | |                      |
|                      | | [contenuto dettagliato nei §§10-18]                           ! | | Target        --     |
|                      | +-----------------------------------------------------------------+ | FX            --     |
|                      |                                                                     | Strategia     --     |
|                      | [Mostra solo incompleti] [Espandi tutti]                             |                      |
+----------------------+---------------------------------------------------------------------+----------------------+
| [ <- Indietro ]                      1 Asset richiede attenzione                 [ Continua -> ] (disabled)      |
+------------------------------------------------------------------------------------------------------------------+
```

## 8.1 Regola densità desktop

- massimo tre zone: stepper 208–224 px, contenuto fluido, summary 264–288 px;
- card contenuto non oltre due colonne di campi;
- liste lunghe usano DataTable o accordion per Asset/Broker;
- summary mostra quantità/configurazione, non previsioni economiche;
- CTA in footer sticky soltanto dentro il renderer;
- header Tool Host resta fuori dallo sticky footer.

---

# 9. ASCII A4 — Tablet/laptop compatto

Viewport: 900–1199 px.

```text
+--------------------------------------------------------------------------------------------+
| CONFIGURA PAC                           Passo 5 di 9 · Routing       [Riepilogo (3 !)] [v]   |
| [1 v]--[2 v]--[3 v]--[4 v]--[5 >]--[6 o]--[7 o]--[8 o]--[9 o]                    44%       |
+--------------------------------------------------------------------------------------------+
| ASSET x BROKER                                                                             |
| Scegli dove ogni Asset può essere acquistato.                                               |
|                                                                                            |
| +----------------------------------------------------------------------------------------+ |
| | XMAW World                                                                   2 route  v | |
| | [contenuto step]                                                                         | |
| +----------------------------------------------------------------------------------------+ |
| +----------------------------------------------------------------------------------------+ |
| | HEAL Healthcare                                                              1 route  ! | |
| | [contenuto step]                                                                         | |
| +----------------------------------------------------------------------------------------+ |
+--------------------------------------------------------------------------------------------+
| [ <- Indietro ]                                      [ Continua -> ] (disabled)              |
+--------------------------------------------------------------------------------------------+
```

Trasformazione:

- stepper verticale → progress rail orizzontale numerica;
- label completa solo per step attivo;
- summary rail → drawer;
- contenuto usa larghezza piena;
- nessuna perdita di stato o informazione.

---

# 10. ASCII A5 — Mobile, Step 1

Viewport: 390 px.

```text
+--------------------------------------------+
| <- Tools                     [Docs] [Refresh]|
| PAC Allocator                              |
| Funding, FX e ordini BUY.                  |
| API 1.0.0 · UI 1.0.0                      |
+--------------------------------------------+
| Passo 1 di 9                    [Riepilogo] |
| [=======---------------------------------] |
| Scenario                                   |
+--------------------------------------------+
| [monete] PAC Allocator                     |
| Tool già scelto. Torna a Tools per cambiarlo.|
|                                            |
| Data del piano *                           |
| [ 15/09/2026                         ]     |
|                                            |
| Valuta di riferimento *                    |
| [ EUR - Euro                         v ]     |
| [S] Preferenza utente                      |
|                                            |
| [i] Cash e ordini restano in valuta nativa.|
+--------------------------------------------+
| [ Esci ]                     [ Continua -> ]|
+--------------------------------------------+
```

Regole:

- target touch minimo 44 px;
- una colonna;
- CTA sticky con safe-area;
- Docs/Refresh icon-only ma con `aria-label`;
- summary apre bottom sheet;
- stepper completo non occupa viewport.

---

# 11. ASCII A6 — Mobile, navigazione step

Tap su “Passo 5 di 9” oppure progress bar.

```text
+--------------------------------------------+
| Scegli uno step                         [x] |
+--------------------------------------------+
| v  1  Scenario                             |
| v  2  Liquidità                            |
| v  3  Broker                               |
| v  4  Asset                                |
| >  5  Routing                              |
| o  6  Target                               |
| o  7  FX                                   |
| o  8  Strategia                            |
| o  9  Rivedi                               |
+--------------------------------------------+
| v Completo   ! Da rivedere   o Non iniziato|
+--------------------------------------------+
```

Comportamento:

- step completato: navigabile;
- step attivo: `aria-current="step"`;
- step futuro: navigabile soltanto se predecessori richiesti sono completi;
- step con errore: resta navigabile e porta focus al primo errore;
- chiusura sheet: focus torna al trigger.

---

# 12. ASCII A7 — Summary mobile

```text
+--------------------------------------------+
| Riepilogo PAC                           [x] |
+--------------------------------------------+
| Scenario                              v     |
| 15/09/2026 · EUR                            |
|                                            |
| Liquidità nativa                      v     |
| EUR 3.500,00 · USD 500,00                   |
|                                            |
| Broker                                v     |
| Directa · Broker PAC Demo                   |
|                                            |
| Asset                                 v     |
| 4 Asset                                    |
|                                            |
| Routing                               !     |
| 3 di 4 Asset completi                       |
|                                            |
| Target                                o     |
| FX                                    o     |
| Strategia                             o     |
+--------------------------------------------+
| [ Vai al primo dato incompleto ]            |
+--------------------------------------------+
```

Summary mostra solo:

- valori digitati/copiati;
- conteggi;
- completezza;
- totale target;
- provenance/stale sintetico.

Non mostra quantità, fee previste, ordini o target “raggiunto”.

---

# 13. ASCII A8 — Uscita/reload con draft sporco

```text
                 +--------------------------------------------------+
                 | Uscire dal PAC Allocator?                        |
                 |                                                  |
                 | La configurazione corrente non è salvata.        |
                 | Uscendo perderai 4 Asset e 2 fonti di liquidità. |
                 |                                                  |
                 | [ Continua a modificare ]   [ Esci e scarta ]    |
                 +--------------------------------------------------+
```

Usato per:

- link “Tools”;
- browser navigation intercettabile;
- refresh esplicito Tool Host;
- cambio Tool.

Cambio account/sessione non offre “mantieni draft”: renderer viene smontato,
richieste abortite, dati personali eliminati dalla memoria UI.

---

# 13.1 ASCII A9 — Modifica strutturale che cancella dati successivi

Avanti/indietro non perde mai dati. Una conferma compare soltanto quando una modifica
strutturale rende impossibile conservare configurazioni dipendenti.

```text
              +--------------------------------------------------------------------------------+
              | Rimuovere Directa Demo?                                                    [x] |
              +--------------------------------------------------------------------------------+
              | Questa modifica cancellerà dati che dipendono dal Broker:                       |
              |                                                                                |
              | - 4 route Asset x Broker;                                                       |
              | - 1 conversione FX EUR -> USD;                                                  |
              | - 4 profili vincolo BUY e 1 profilo SELL;                                      |
              | - il risultato calcolato dallo snapshot precedente.                             |
              |                                                                                |
              | Liquidità, Asset e target non dipendenti resteranno invariati.                  |
              |                                                                                |
              | [ Annulla ]                              [ Rimuovi e cancella dipendenze ]       |
              +--------------------------------------------------------------------------------+
```

Regola:

- navigazione avanti/indietro: nessuna perdita;
- modifica non distruttiva: dati successivi restano, step dipendente diventa
  `Da rivedere`;
- modifica strutturale distruttiva: `ConfirmModal` con elenco esatto dei dati
  rimossi;
- nessun reset globale quando basta eliminare una singola dipendenza;
- dopo conferma, focus torna al controllo modificato e summary indica gli step
  incompleti.

---

# 14. Navigazione e validazione

## 14.1 Regole

1. “Continua” esegue solo validazione locale dello step.
2. Errore → focus sul primo campo invalido + summary errori in cima al contenuto.
3. “Indietro” non valida e non perde il draft.
4. Modifica a uno step precedente conserva i dati compatibili e marca i dipendenti
   `Da rivedere`.
5. Se una modifica elimina dati dipendenti, il frontend calcola prima l'impatto e
   richiede conferma tramite `ConfirmModal`; annullare lascia il draft byte-identico.
6. Nessuna risposta copy tardiva può sovrascrivere un campo modificato.
7. Nessun refresh dominio automatico dopo Apply.
8. Step 9 crea snapshot immutabile e mostra provenance/staleness.
9. Compute parte soltanto da Step 9.
10. Modifica dopo risultato rende il risultato stale e disabilita uso operativo.
11. Cambio account/generation abortisce copy/compute e resetta tutto.

## 14.2 Dipendenze visuali

```text
Scenario
   |
Liquidità ----+
   |          |
Broker -------+--> Asset --> Routing --> Target --> FX --> Strategia --> Rivedi
```

Relazione funzionale completa:

- Asset dipende da Broker solo per compatibilità futura; selezione Asset resta
  possibile anche senza Asset DB;
- Routing dipende da Asset + Broker;
- FX dipende da funding + Broker + route + valute Asset;
- cambio Broker/Asset/routing può invalidare FX;
- cambio target non invalida capability, ma invalida review e risultato;
- cambio strategia invalida review e risultato.

---

# 15. Responsive

| Viewport | Stepper | Summary | Contenuto | CTA |
|---|---|---|---|---|
| `>=1200` | verticale sinistra | rail destra | centro fluido | footer sticky renderer |
| `900–1199` | progress orizzontale | drawer | piena larghezza | footer sticky |
| `<900` | “Passo N di 9” + progress | bottom sheet | una colonna | bottom sticky + safe-area |

DataTable future:

- desktop: colonne configurabili;
- tablet: colonne core + dettaglio riga;
- mobile: card-row/accordion, non scroll orizzontale obbligatorio per azioni core;
- export/copy tabella non previsto in v1.

---

# 16. Accessibilità shell

- `h1` dal Tool Host; ogni step usa `h2`.
- Stepper desktop = `nav aria-label="Avanzamento configurazione"`.
- Step attivo = `aria-current="step"`.
- Stato non comunicato solo da colore.
- Focus va al titolo step dopo navigazione.
- Error summary usa link al campo.
- Footer sticky non copre ultimo controllo.
- `prefers-reduced-motion`: niente transizioni progress animate.
- Drawer/modal intrappola focus e lo restituisce al trigger.
- Back/Continue seguono ordine DOM.
- Valori finanziari mantengono privacy mode esistente.
- Icone decorative `aria-hidden`; pulsanti icon-only con nome accessibile.

---

# 17. Decisioni approvate — Review A

> **Approvazione developer:** intera Review A approvata il 15 settembre 2026.

## A. Architettura

- Due card/route; nessun mode switch interno.
- 9 step di input, risultato fuori dallo stepper.
- “Scenario” come Step 1.

## B. Desktop

- stepper verticale;
- contenuto centrale;
- summary rail destra;
- footer CTA sticky.

## C. Tablet/mobile

- progress compatto;
- summary drawer/bottom sheet;
- una colonna;
- CTA sticky.

## D. Densità

- una responsabilità per step;
- massimo due colonne di campi;
- liste lunghe in DataTable/accordion;
- summary senza calcoli economici.

## E. Navigazione e dipendenze

- avanti/indietro conserva tutti i valori configurati;
- cambi compatibili marcano step dipendenti `Da rivedere`;
- cambi distruttivi mostrano `ConfirmModal` con elenco esatto dei dati rimossi;
- nessuna cancellazione silenziosa o reset globale.

## F. Terminologia proposta

| Concetto | Label |
|---|---|
| cash/input | Liquidità |
| execution venue | Broker |
| eligibility | Routing |
| objective distribution | Target |
| operational FX facts | FX |
| optimization mode | Strategia |
| immutable confirmation | Rivedi |

---

# 18. Review B — input operativi

> Review A non disponibile durante la sessione: applicato il layout raccomandato in
> autonomia. Non equivale all'approvazione estetica finale.

## 18.1 ASCII B1 — Liquidità e fonti

Valido per entrambi i Tool. Nel Rebalancer la copy cambia nome in “Cash disponibile”,
ma il contratto resta identico.

```text
+------------------------------------------------------------------------------------------------------------------+
| PASSI                | LIQUIDITÀ E FONTI                                               | RIEPILOGO               |
| v 1  Scenario        | Scegli esattamente quale liquidità può entrare nel piano.       | Liquidità nativa        |
| > 2  Liquidità       | Il saldo non selezionato resta fuori dal calcolo.               | EUR  3.500,00            |
| ○ 3  Broker          |                                                                  | USD    500,00            |
| ○ 4  Asset           | [ + Nuova liquidità ] [ Prendi da conto/Broker ] [ + Manuale ]  |                         |
| ...                  |                                                                  | 3 fonti              v   |
|                      | +----------------------------------------------------------------+ |                         |
|                      | | Nuovo risparmio                             new_external [M]  | | Equivalente indicativo |
|                      | | Importo da usare       1.000,00    Valuta EUR                | | 3.926,20 EUR           |
|                      | | Etichetta              Risparmio settembre          [Edit]  | | FX dominio 15/09       |
|                      | +----------------------------------------------------------------+ |                         |
|                      | +----------------------------------------------------------------+ |                         |
|                      | | Banca Demo                         existing_account [S]       | |                         |
|                      | | Disponibile           8.400,00 EUR · rilevato 15/09          | |                         |
|                      | | Importo da usare     [ 2.500,00 ] EUR         max 8.400,00  | |                         |
|                      | | Uscita fondi: ammessa · destinazione scelta nello Step 3     | |                         |
|                      | +----------------------------------------------------------------+ |                         |
|                      | +----------------------------------------------------------------+ |                         |
|                      | | Conto USD manuale                    manual_account [M]       | |                         |
|                      | | Disponibile dichiarato  900,00 USD                           | |                         |
|                      | | Importo da usare       [ 500,00 ] USD                         | |                         |
|                      | +----------------------------------------------------------------+ |                         |
|                      |                                                                  |                         |
|                      | [i] Trasferimenti e FX effettivi saranno calcolati dal backend.  |                         |
+----------------------+------------------------------------------------------------------+-------------------------+
| [ <- Indietro ]                                                               [ Continua -> ]                    |
+------------------------------------------------------------------------------------------------------------------+
```

L'equivalente illustrativo usa `1 USD = 0,8524 EUR`: `3.500,00 EUR +
500,00 USD = 3.926,20 EUR`. Non è ancora budget route né risultato planner.

**Intento:** selezionare cash, non scegliere ancora dove investirlo.
**Input:** tipo fonte, valuta, saldo dichiarato se manuale, importo usato, label.
**Derivati:** totali per valuta; equivalente solo indicativo con fonte/data.
**Azioni:** aggiungi, modifica, rimuovi, copy.
**Stati:** nessuna fonte, saldo stale, importo > disponibile, valuta mancante.
**Privacy:** importi rispettano privacy mode.

### Regole

- Ogni click aggiunge una riga union `source_kind`.
- Un Broker sorgente non diventa automaticamente Broker operativo.
- Un Broker operativo non rende automaticamente disponibile tutto il suo cash.
- Nuova liquidità non ha “saldo disponibile”: importo e disponibilità coincidono.
- Fonte manuale richiede saldo dichiarato e importo `<=` saldo.
- Lo Step 3 mapperà sorgente→destinazione; nessun falso auto-bonifico.

## 18.2 ASCII B2 — “Prendi liquidità da…”

```text
              +--------------------------------------------------------------------------------+
              | Prendi liquidità da un conto o Broker                                      [x] |
              +--------------------------------------------------------------------------------+
              | Cerca [ Banca / Broker / valuta...                                      ]      |
              | Scope autorizzato: solo conti visibili all'utente                              |
              |                                                                                |
              | ( ) Banca Demo                                                                 |
              |     EUR 8.400,00 disponibili · aggiornato 15/09/2026                           |
              |                                                                                |
              | (o) Directa Demo                                                               |
              |     EUR 1.159,00 · USD 240,00 · aggiornato 15/09/2026                          |
              |                                                                                |
              | ( ) Broker osservato                                                           |
              |     Non selezionabile: nessun accesso OWNER                                    |
              |                                                                                |
              | Valuta *          [ EUR v ]                                                    |
              | Importo da usare * [ 800,00                     ] max 1.159,00                  |
              |                                                                                |
              | [ Annulla ]                                      [ Aggiungi fonte ]            |
              +--------------------------------------------------------------------------------+
```

**Copy:** seleziona una sola coppia conto/valuta per riga; altre valute diventano
righe separate.
**Permessi:** contesti non autorizzati possono spiegare indisponibilità, mai
esporre saldo o essere selezionati.
**Provenance:** account, data snapshot e scope restano visibili dopo Apply.

## 18.3 ASCII B3 — Nuova liquidità / fonte manuale

```text
+------------------------------------------------------------------+
| Aggiungi conto manuale                                       [x] |
+------------------------------------------------------------------+
| Nome Conto *                         [ Banca non configurata    ] |
| Valuta *                             [ EUR v                    ] |
| Liquidità disponibile dichiarata *  [ 5.000,00                 ] |
|                                      Limite massimo dichiarato; |
|                                      non viene usato in automatico.|
| Importo da usare *                   [ 2.000,00                 ] |
|                                      Deve essere <= 5.000,00.  |
|                                                                  |
| Le destinazioni e i bonifici verranno definiti nei Broker.       |
| Aggiungere il conto come fonte autorizza questo scenario a       |
| proporre soltanto i trasferimenti esplicitamente configurati.    |
|                                                                  |
| [ Annulla ]                                [ Aggiungi fonte ]    |
+------------------------------------------------------------------+
```

Per “Nuova liquidità” restano soltanto:

```text
Importo *  [ 1.000,00 ]   Valuta * [ EUR v ]
Etichetta  [ Nuovo risparmio                    ]
```

`Liquidità disponibile dichiarata` non alimenta grafici o allocazioni: è un
vincolo di sicurezza e conservazione del ledger
(`importo da usare <= liquidità disponibile`). Per `new_external`, importo e
disponibilità coincidono, quindi un secondo campo sarebbe ridondante.

Niente `is_new`, `is_manual`, “semantica importo” o booleano “trasferimento
ammesso”: il ramo della union e l'aggiunta esplicita della fonte decidono i campi.

## 18.4 ASCII B4 — Conflitto solo dopo refresh/copy esplicito

```text
             +--------------------------------------------------------------------------------+
             | Directa è cambiata dall'ultima copia                                        [x] |
             +--------------------------------------------------------------------------------+
             | Hai chiesto “Aggiorna dal sistema”. Il saldo EUR ora è diverso:                |
             |                                                                                |
             | Saldo copiato nel draft                         1.159,00 EUR                   |
             | Saldo disponibile dal sistema · 15/09/2026      1.204,33 EUR                   |
             | Importo scelto manualmente                         800,00 EUR   [non cambia]     |
             | Etichetta manuale                              “PAC Directa”   [non cambia]     |
             |                                                                                |
             | Aggiornando, cambia soltanto il fatto sorgente e la sua data.                   |
             | Nessun campo modificato da te verrà sovrascritto.                               |
             |                                                                                |
             | [ Mantieni snapshot copiato ]                      [ Aggiorna saldo sorgente ]  |
             +--------------------------------------------------------------------------------+
```

Questo non è uno step normale del wizard. Compare soltanto dopo click esplicito su
`Aggiorna dal sistema` / `Copia di nuovo` quando un nuovo fatto collide con uno
snapshot già usato:

- nessun polling o binding live apre il modal;
- una risposta tardiva senza stessa request/account generation viene scartata;
- aggiornare sostituisce solo fatti di dominio selezionati e relativa provenance;
- campi manuali restano byte-identici;
- se il nuovo saldo rende `importo da usare` troppo alto, il valore manuale resta,
  lo Step 2 diventa `Da correggere` e il modal mostra il link al campo;
- mantenere conserva lo snapshot precedente e il suo badge stale.

### Regola selettori, gallery e creazione

| Esigenza | Primitive/UI |
|---|---|
| scegliere più Asset o Broker | gallery filtrabile con card esistenti |
| scegliere un Asset in una riga | `AssetSelect`, con icona, ticker, valuta e stato |
| scegliere un Broker in una riga | `BrokerSearchSelect`, con icona, ruolo e disabled reason |
| creare entità persistente autorizzata | azione `Crea nuovo` → `AssetModal` / `BrokerModal` esistenti |
| aggiungere dato soltanto allo scenario | CTA separata `Asset manuale` / `Broker manuale`; nessuna persistenza implicita |

Gallery e selector riusano le stesse entità selezionate nel draft. Tornare indietro
non ricrea la selezione e non cambia ordine/priorità.

### Regola input numerici

| Dato | Primitive |
|---|---|
| importo + valuta, prezzo, PMC, fee fissa, min/max fee | `CompactCashCell`; valuta disabilitata quando ereditata |
| quantità/limiti in quote | componente condiviso estratto dal quantity editor di `TransactionFormModal` |
| percentuale, spread, safety margin, aliquota | `ExactDecimalInput` con suffisso e range esplicito |
| data prezzo/FX | `SingleDatePicker` |

Prima di usarlo qui, il quantity editor deve diventare condiviso e
`TransactionFormModal` deve migrare senza regressioni di raw input, virgola/punto,
zeri finali, frecce, blur formatting e sign hint.

---

## 18.5 ASCII B5 — Broker operativi

```text
+------------------------------------------------------------------------------------------------------------------+
| PASSI                | BROKER SU CUI OPERARE                                             | RIEPILOGO              |
| v 1  Scenario        | Scegli i luoghi dove il backend può proporre BUY/SELL.            | Fonti        3 v        |
| v 2  Liquidità       | [ Scegli Broker esistente ] [ + Broker manuale ]                  | Broker       2 v        |
| > 3  Broker          |                                                                      |                         |
| ○ 4  Asset           | +--------------------------------+ +--------------------------------+ | Directa        v       |
| ...                  | | Directa Demo        esistente | | Broker Margine Demo   manuale | | Broker Margine v       |
|                      | | [S] aggiornato 15/09           | | [M] scenario-only              | |                         |
|                      | | EUR · auto-FX                  | | EUR · nativo                   | | Funding link  3/3      |
|                      | | Ordine EUR: numero quote      | | Ordine EUR: importo · incr. 0,01| |                         |
|                      | | BUY fee: zero                  | | BUY fee: zero                  | |                         |
|                      | | SELL fee: configurata          | | SELL non usato                 | |                         |
|                      | | Regime: dichiarativo           | | Regime: dichiarativo           | |                         |
|                      | | Funding: cash locale + Banca   | | Funding: solo cash locale       | |                         |
|                      | | [ Modifica ] [ Rimuovi ]       | | [ Modifica ] [ Rimuovi ]       | |                         |
|                      | +--------------------------------+ +--------------------------------+ |                         |
+----------------------+-----------------------------------------------------------------------+-------------------------+
| [ <- Indietro ]                                                                  [ Continua -> ]                   |
+------------------------------------------------------------------------------------------------------------------+
```

**Intento:** configurare capability di esecuzione scenario-only.
**Input:** origine, valute, FX mode, frazioni, step monetario condizionale, fee,
regime, minus, funding link.
**Derivati:** completezza e compatibilità strutturale.
**Vietato:** persistenza automatica, scelta ordine, split Asset.

## 18.6 ASCII B6 — Editor Broker

```text
+----------------------------------------------------------------------------------------------------+
| Configura Directa Demo · dati scenario-only                                                    [x] |
+----------------------------------------------------------------------------------------------------+
| ORIGINE                                                                                            |
| [S] Broker esistente · snapshot 15/09/2026 14:21 · [ Ripristina valori copiati ]                  |
|                                                                                                    |
| CONTI E MODALITÀ ORDINE                                                                            |
| +------+-------------------------------+--------------------------+--------------------+------------+ |
| | Val. | Gestione FX                   | Cosa inserisci nel Broker| Incremento importo | Addebito   | |
| | EUR  | Auto-conversione all'acquisto | Numero intero di quote v | —                  | EUR        | |
| | USD  | Solo valuta nativa             | Importo da investire v   | [ 1,00 ] USD       | USD        | |
| +------+-------------------------------+--------------------------+--------------------+------------+ |
| [ + Aggiungi valuta ]                                                                                |
|                                                                                                    |
| COMMISSIONI PER LATO E VALUTA                                                                       |
| +------+-------+------------+----------+----------------+----------------+-------------------------+ |
| | Val. | Lato  | Fisso      | Tasso % | Min componente | Max componente | Anteprima formula       | |
| | EUR  | BUY   | [ 0,00 ]   | [ 0 ]   | [ 0,00 ]       | [ — ]          | 0                       | |
| | EUR  | SELL  | [ 5,00 ]   | [ 0,19] | [ 1,50 ]       | [ 18,00 ]      | 5 + clamp(0,19%)        | |
| +------+-------+------------+----------+----------------+----------------+-------------------------+ |
| [i] Min/max si applicano solo alla componente percentuale. 0 è valido.                             |
|                                                                                                    |
| FISCALITÀ                                                                                           |
| Regime *             ( ) Amministrato     (o) Dichiarativo/libero                                  |
| Minus pregresse      [ 0,00 ] [ EUR v ]   Data [ 15/09/2026 ]                                     |
| Ritenuta SELL        [D] Riserva fiscale self_reserved nel conto                                   |
|                                                                                                    |
| FUNDING AMMESSO                                                                                    |
| [v] Cash locale Directa · nessun trasferimento                                                     |
| [v] Banca Demo EUR -> Directa EUR                                                                  |
| [ ] Conto USD manuale -> Directa USD                                                               |
|                                                                                                    |
| [ Annulla ]                                                                [ Applica al draft ]   |
+----------------------------------------------------------------------------------------------------+
```

### Normalizzazione campi Broker

- `fx_mode`: un enum per valuta/contesto:
  - `native_currency_required`;
  - `auto_convert_on_buy`.
- `order_instruction_kind`: un enum per Broker/valuta:
  - `whole_quantity`: nel Broker si inserisce un numero intero di quote, per esempio
    `51`; unità implicita `1`, nessun campo step;
  - `monetary_amount`: nel Broker si inserisce un importo monetario, per esempio
    `182,00 EUR`; quantità stimata solo informativa.
- `order_amount_step` appare solo per `monetary_amount` con label
  `Incremento minimo importo`: è lo scatto accettato dal configuratore Broker per
  quella valuta (`0,01`, `1`, `10` EUR), non precisione del prezzo né step di
  possesso.
- Nessun `quantity_step`.
- Fee BUY e SELL sempre separate; fisso + percentuale possono coesistere.
- `Margine prezzo BUY` e `Margine prezzo SELL` sono coefficienti route
  espliciti, distinti da spread e buffer FX; lo zero resta visibile/editabile.
- Fee dinamiche/per mercato non compaiono in v1.
- `withholding_kind` è read-only derivato dal regime.
- Carried losses sono fatti; v1 non promette compensazione.
- Funding link source→Broker viene configurato qui, quando destinazioni sono note.

---

## 18.7 ASCII B7 — Asset PAC

```text
+------------------------------------------------------------------------------------------------------------------+
| PASSI                | ASSET DA ACQUISTARE                                                | RIEPILOGO PAC         |
| v 1  Scenario        | Seleziona Asset canonici o aggiungili manualmente.                 | Broker       2 v      |
| v 2  Liquidità       | [ Cerca Asset...                  ] [Scope: Tutti v] [ + Manuale ] | Asset        4 v      |
| v 3  Broker          |                                                                      |                         |
| > 4  Asset           | +------------------------------+ +------------------------------+   | Prezzi       4/4      |
| ○ 5  Routing         | | [icon] XMAW World        [v] | | [icon] XDWF Financials  [v] |   | Metadata     3/4 !    |
| ...                  | | ISIN IE00... · ETF            | | ISIN IE00... · ETF            |   |                         |
|                      | | 50,230 EUR / 1 quota          | | 42,235 EUR / 1 quota          |   | Unknown geo  1       |
|                      | | [S] Provider · 15/09 · fresco | | [S] Provider · 15/09 · fresco |   |                         |
|                      | | Tipo 100% Equity              | | Settore 100% Financials       |   |                         |
|                      | | [ Modifica ]                  | | [ Modifica ]                  |   |                         |
|                      | +------------------------------+ +------------------------------+   |                         |
|                      | +------------------------------+ +------------------------------+   |                         |
|                      | | [icon] XDWI Industrials  [v] | | [?] Asset manuale        [!] |   |                         |
|                      | | ...                          | | ID scenario mancante          |   |                         |
|                      | +------------------------------+ +------------------------------+   |                         |
+----------------------+-----------------------------------------------------------------------+-------------------------+
| [ <- Indietro ]                                                            [ Continua -> ] disabled               |
+------------------------------------------------------------------------------------------------------------------+
```

PAC non mostra holding o PMC: il modello parte da quantità zero. Prezzo e metadata
servono a calcolo e risultati.

## 18.8 ASCII B8 — Editor Asset manuale

```text
+----------------------------------------------------------------------------------------------+
| Asset manuale                                                                            [x] |
+----------------------------------------------------------------------------------------------+
| IDENTITÀ                                                                                     |
| ID strumento *       [ ISIN / ID univoco scenario                      ]                     |
| Nome *                [ ETF Globale Manuale                             ]                     |
| Ticker                [ WORLD ]          Tipo [ ETF v ]                                       |
| [i] Mai unire Asset per nome. Lo stesso ID riusa la stessa identità nel draft.               |
|                                                                                              |
| PREZZO                                                                                       |
| Prezzo originale *   [ 50,230 ]      Valuta quotazione * [ EUR v ]                           |
| Quote base quantity* [ 1 ]           Data prezzo *        [ 15/09/2026 ]                     |
| Fonte                 [ Inserimento manuale                         ]                          |
|                                                                                              |
| ESPOSIZIONI OPZIONALI                                                                        |
| Tipo        [ Equity 100%                              ]                                      |
| Settore     [ World diversified 100%                   ]                                      |
| Geografia  [ Unknown 100%                              ]                                      |
| Quote mancanti confluiscono in Unknown; nessuna rinormalizzazione.                            |
|                                                                                              |
| Aliquota plusvalenze [ 26,00 ] %  [M] modificabile                                           |
|                                                                                              |
| [ Annulla ]                                                       [ Applica al draft ]       |
+----------------------------------------------------------------------------------------------+
```

`quote_base_quantity` dice quante quote sono rappresentate dal prezzo sorgente;
non è passo ordine.

## 18.9 ASCII B9 — Asset e holding Rebalancer

```text
+------------------------------------------------------------------------------------------------------------------+
| PASSI                | PORTAFOGLIO CORRENTE                                              | RIEPILOGO              |
| v 1  Scenario        | Copia Asset e custodie autorizzate oppure aggiungi manualmente.    | Asset canonici   4     |
| v 2  Liquidità       | [ Copia dal Portfolio ] [ + Asset/holding manuale ]                | Custodie         6     |
| v 3  Broker          |                                                                      | Prezzi         4/4     |
| > 4  Asset           | +--------------------------------------------------------------------------------------+ | PMC            5/6 !  |
| ○ 5  Routing         | | XMAW World · prezzo 55,3165 EUR / 1 · [S] 15/09                        [Modifica] | | Tax rate      4/4     |
| ...                  | |--------------------------------------------------------------------------------------| |                         |
|                      | | Custodia        Intera     Quota personale   Q.tà piano [S]   PMC       Stato          | |                         |
|                      | | Directa Demo    523,5148   50%              261,7574          53,5780 EUR v           | |                         |
|                      | | Fineco Demo      18        100%              18               —         !             | |                         |
|                      | | [ + Aggiungi custodia manuale ]                                                   | |                         |
|                      | +--------------------------------------------------------------------------------------+ |                         |
+----------------------+-----------------------------------------------------------------------------------------+
| [ <- Indietro ]                                          1 PMC richiesto mancante             [ Continua -> ]   |
+------------------------------------------------------------------------------------------------------------------+
```

### Holding

- Custodia intera resta un fatto distinto dalla quota economica personale.
- Quantità usata nel piano arriva già dal dominio o viene inserita manualmente.
- Inventario frazionario resta esatto.
- PMC è per Asset×Broker con valuta, data e provenance.
- Il prezzo è Asset-level; conversioni operative sono route-level e backend.
- Aliquota Asset è un rapporto nel wire, ma UI mostra percentuale.

---

## 18.10 ASCII B10 — Routing Asset×Broker

PAC mostra solo tab BUY. Rebalancer mostra BUY e SELL.
Il riquadro seguente illustra l'editor e non è lo snapshot numerico C1-C15; le
route esatte dei due witness sono dichiarate subito dopo.

```text
+------------------------------------------------------------------------------------------------------------------+
| PASSI                | ROUTING · XMAW WORLD                                               | RIEPILOGO              |
| ...                  | Broker ammessi e vincoli. Target e split restano Asset-level.      | Asset completi  3/4    |
| > 5  Routing         | [ < Asset precedente ]                         [ Asset successivo > ]|                         |
|                      |                                                                      | Route BUY       6      |
|                      | [ BUY ] [ SELL · solo Rebalancer ]                                  | Route SELL      4      |
|                      |                                                                      | Warning         1      |
|                      | +--------------------------------------------------------------------------------------+ |
|                      | | [v] Directa Demo             Priorità [ 1 ]    EUR · intero · auto-FX              | |
|                      | | Compatibilità: pronta [v]                                                      | |
|                      | | Minimo se operi       [ 0,00 ] EUR                                             | |
|                      | | Obbligo route         [ Nessun ordine obbligatorio v ]                          | |
|                      | | Cap massimo           [ Nessun cap v ]                                         | |
|                      | | Fee BUY stimabile     0                                                        | |
|                      | | Margine prezzo BUY   [ 0,00 ] % · esplicito anche senza FX                     | |
|                      | +--------------------------------------------------------------------------------------+ |
|                      | +--------------------------------------------------------------------------------------+ |
|                      | | [v] Broker PAC Demo          Priorità [ 1 ]    EUR · cash amount · step 1 EUR     | |
|                      | | Compatibilità: prezzo disponibile [v]                                          | |
|                      | | Minimo se operi       [ 25,00 ] EUR                                             | |
|                      | | Obbligo route         [ Minimo obbligatorio v ] [ 100,00 ] EUR                  | |
|                      | | Cap massimo           [ Controvalore v ]       [ 1.500,00 ] EUR                | |
|                      | +--------------------------------------------------------------------------------------+ |
|                      | [ ] Banca Demo · funding-only, non selezionabile per ordini                           |
+----------------------+-----------------------------------------------------------------------------------------+
| [ <- Indietro ]                                                               [ Continua -> ]                   |
+------------------------------------------------------------------------------------------------------------------+
```

Nel witness PAC C1-C15, HEAL ha inoltre una seconda route BUY esclusiva su
`Broker Margine Demo × EUR`: `monetary_amount`, step `0,01`, minimo se si opera
`3,00`, cap route `3,00`, fee zero e cash locale selezionato `3,72`. Nel
witness Rebalancer compare anche `Broker Baseline Demo`: l'`invest_only`
congelato vi spende il contributo `1.252,00` su due route monetarie
all-or-nothing, ciascuna con minimo se si opera uguale al cap: HEAL
`1.164,50` e XDWI `87,50`. Directa non ha cash finché il SELL non accredita
`1.094,33`, usati sulla route XDWF. La route HEAL-only su
Broker Margine Demo ha minimo e cap `48,00`, finanziati dal saldo locale
preesistente `48,00`: passare da residuo `-22,50` a `+25,50` peggiora L2,
quindi resta inattiva sia nel baseline `invest_only` sia nel primario
`invest_and_sell` e apre una nuova riga soltanto nella variante margine.
Nessun altro Asset è eleggibile su Broker Margine Demo; su Broker Baseline Demo
sono eleggibili soltanto le due route all-or-nothing dichiarate.

### Editor vincoli tipizzato

```text
Minimo se la riga esiste        [ 25,00 ] EUR

Obbligo route                   [ Nessun ordine obbligatorio v ]
                                [ Minimo obbligatorio          ]
                                  -> importo [ 100,00 ] EUR

Cap massimo                     [ Nessun cap v ]
                                [ Quantità   ] -> [ 20 ] quote
                                [ Controvalore ] -> [ 1.500,00 ] EUR
```

Nessun booleano parallelo; ogni selettore apre soltanto i campi del proprio ramo.
Required BUY + required SELL sullo stesso Asset viene bloccato prima di Review.

### SELL Rebalancer

```text
[ SELL ]
+----------------------------------------------------------------------------------------------+
| [v] Directa Demo · inventario disponibile 261,7574 quote                                     |
| Priorità [1]   Minimo se operi [25,00 EUR]   Obbligo [Nessuno v]   Cap [Quantità v] [20]     |
| Fee SELL 4,00 flat · PMC 53,5780 EUR · tax 26% · self_reserved                              |
| [i] “Investi soltanto” ignorerà tutti i vincoli SELL.                                        |
+----------------------------------------------------------------------------------------------+
```

---

## 18.11 ASCII B11 — Target PAC

```text
+------------------------------------------------------------------------------------------------------------------+
| PASSI                | TARGET · NUOVA ALLOCAZIONE                                       | RIEPILOGO PAC          |
| ...                  | Definisce come distribuire la liquidità investibile.             | Asset        4 v       |
| > 6  Target          | Non è una preview del piano.                                      | Routing      4/4 v     |
|                      |                                                                     |                         |
|                      | +-----------------------------+---------------+------------------+ | Totale      100,00% v  |
|                      | | Asset                       | Target %      | Distribuzione    | | Restante      0,00%   |
|                      | | XMAW World                  | [ 70,05 ]     | ##############   | |                         |
|                      | | XDWF Financials             | [ 12,71 ]     | ###              | | Nessun valore futuro   |
|                      | | XDWI Industrials            | [ 12,24 ]     | ##               | | calcolato               |
|                      | | HEAL Healthcare             | [  5,00 ]     | #                | |                         |
|                      | +-----------------------------+---------------+------------------+ |                         |
|                      |                                                                     |                         |
|                      | Totale 100,00%                               Restante 0,00% [v]    |                         |
+----------------------+---------------------------------------------------------------------+-------------------------+
| [ <- Indietro ]                                                               [ Continua -> ]                    |
+------------------------------------------------------------------------------------------------------------------+
```

## 18.12 ASCII B12 — Target Rebalancer

```text
+------------------------------------------------------------------------------------------------------------------+
| TARGET · PORTAFOGLIO FINALE                                            [ Usa distribuzione corrente come base ] |
| Percentuali dell'intero portafoglio investito dopo il piano. Cash escluso.                                     |
+-----------------------------------+----------------+----------------------+--------------------------------------+
| Asset                             | Ora [S]        | Target %            | Distribuzione target                  |
| XMAW World                        | 62,40%          | [ 55,00 ]           | ###########                          |
| XDWF Financials                   |  8,10%          | [ 12,00 ]           | ##                                   |
| XDWI Industrials                  | 18,50%          | [ 18,00 ]           | ####                                 |
| HEAL Healthcare                   | 11,00%          | [ 15,00 ]           | ###                                  |
+-----------------------------------+----------------+----------------------+--------------------------------------+
| Totale target 100,00% · Restante 0,00% [v]                                                                  |
| [i] “Ora” è un fatto dominio copiato. “Dopo” compare soltanto nel risultato backend.                          |
+------------------------------------------------------------------------------------------------------------------+
```

“Usa distribuzione corrente” copia valori nel target come base modificabile. Non è
consiglio, non crea binding e non avvia compute.

---

## 18.13 ASCII B13 — FX potenzialmente necessari

```text
+------------------------------------------------------------------------------------------------------------------+
| PASSI                | FX POTENZIALMENTE NECESSARI                                      | RIEPILOGO              |
| ...                  | Il backend sceglierà conversioni/importi nel singolo compute.    | Coppie       2 v       |
| > 7  FX              | [ Aggiorna proposte FX ]                                           | Stale        1 !       |
|                      |                                                                     | Buffer max   1,00%     |
|                      | +--------------------------------------------------------------------------------------+ |
|                      | | Directa · EUR -> USD · Auto-FX acquisto                                  [S] [~] | |
|                      | | 1 EUR = [ 1,1732 ] USD    Fonte ECB    12/09/2026 · 3 giorni fa [stale]          | |
|                      | | Spread aggiuntivo [ 0,50 ] %     Margine sicurezza [ 1,00 ] %                   | |
|                      | | Fee conversione    [ 0,00 ] EUR                                                | |
|                      | | Prezzo XMAW: 50,23 USD originale -> 43,02 EUR mid [S dominio]                  | |
|                      | |                              [ Conferma dato stale ] [ Ripristina ] [ Modifica ] | |
|                      | +--------------------------------------------------------------------------------------+ |
|                      | +--------------------------------------------------------------------------------------+ |
|                      | | Broker PAC Demo · USD -> EUR · Conversione preventiva                    [M]     | |
|                      | | 1 USD = [ 0,8524 ] EUR    Fonte Manuale  15/09/2026 · oggi                      | |
|                      | | Spread aggiuntivo [ 0,00 ] %     Margine sicurezza [ 0,00 ] %                   | |
|                      | | Fee conversione    [ 2,00 ] USD                                                | |
|                      | +--------------------------------------------------------------------------------------+ |
|                      | [i] Il margine resta cash; non è fee e non viene convertito.                       |
+----------------------+-----------------------------------------------------------------------------------------+
| [ <- Indietro ]                                         1 tasso stale confermato          [ Continua -> ]        |
+------------------------------------------------------------------------------------------------------------------+
```

### Regole FX

- Coppie mostrate da valute funding, Broker e route; non sono conversioni decise.
- Campo rate esplicita sempre verso: `1 source = N destination`.
- Spot modificato diventa `[~]`; fonte manuale.
- Età e staleness restano visibili.
- Spread e margine sono percentuali distinte.
- Fee conversione è costo separato, default esplicito `0`.
- Prezzo operativo convertito arriva dal dominio/backend FX; UI non lo calcola.
- Nessun ciclo o multi-hop configurabile in v1.

---

## 18.14 ASCII B14 — Strategia PAC

```text
+------------------------------------------------------------------------------------------------------------------+
| STRATEGIA PAC                                                                                                    |
| Scegli come distribuire ordini fattibili. Tutti i vincoli precedenti restano rigidi.                             |
|                                                                                                                  |
| +----------------------------------------------------+ +-------------------------------------------------------+ |
| | (o) Proporzionale                                 | | ( ) Minima frammentazione                           | |
| |                                                    | |                                                       | |
| | Primario: L2 fixed -> U.                           | | Primario: L2 fixed -> U.                              | |
| | Poi priorità -> fee -> righe -> tie-break.         | | Poi split -> righe -> priorità -> fee -> tie.         | |
| | Variante: max BUY -> L2 -> costi/righe.            | | Variante: max BUY -> L2 -> costi/righe.               | |
| |                                                    | |                                                       | |
| | Parametri aggiuntivi: nessuno.                     | | Parametri aggiuntivi: nessuno.                       | |
| +----------------------------------------------------+ +-------------------------------------------------------+ |
|                                                                                                                  |
| [i] Entrambe usano target monetari fissi; cambiano soltanto i tier operativi dopo L2 fixed e U.                 |
+------------------------------------------------------------------------------------------------------------------+
```

## 18.15 ASCII B15 — Strategia Rebalancer

```text
+------------------------------------------------------------------------------------------------------------------+
| MODALITÀ RIBILANCIAMENTO                                                                                          |
|                                                                                                                  |
| +----------------------------------------------------+ +-------------------------------------------------------+ |
| | (o) Investi soltanto · consigliata                 | | ( ) Investi e vendi                                  | |
| |                                                    | |                                                       | |
| | Usa liquidità e contributi verso gli Asset         | | Congela prima il miglior piano “Investi soltanto”.   | |
| | sotto target. Il vincolo SELL=0 resta rigido.      | | SELL solo sopra target e solo per finanziare BUY.    | |
| | Restituisce due profili di risultato confrontabili.| | Quantum minimo; mai sale-to-cash o BUY+SELL Asset.   | |
| |                                                    | | Fee SELL e tax reserve riducono il cash riusabile.   | |
| | Dati SELL richiesti: nessuno.                      | | Dati SELL: PMC, fee, aliquota e inventory completi.  | |
| +----------------------------------------------------+ +-------------------------------------------------------+ |
|                                                                                                                  |
| Vincoli comuni; cambia solo il dominio SELL. Ogni modalità restituisce primario e variante margine.             |
+------------------------------------------------------------------------------------------------------------------+
```

Se “Investi e vendi” rende incompleto un dato SELL, CTA porta allo specifico
Asset/Broker; nessun default fiscale viene inventato.

---

## 18.16 ASCII B16 — Review snapshot

```text
+------------------------------------------------------------------------------------------------------------------+
| PASSI                | RIVEDI E CALCOLA                                                  | SNAPSHOT                |
| v 1  Scenario        | Verifica dati e fonti. Il backend riceverà questa copia completa. | Creato ora              |
| v 2  Liquidità       |                                                                     | Draft rev. 18           |
| v 3  Broker          | +----------------------------------------------------------------+ | Sessione verificata     |
| v 4  Asset           | | v Scenario       15/09/2026 · EUR                            | |                         |
| v 5  Routing         | | v Liquidità      EUR 1.300 · 2 fonti                         | | Fatti                  |
| v 6  Target          | | v Broker         3 operativi · 2 funding link                 | | Freschi       21       |
| v 7  FX              | | v Asset          4 · prezzi 4/4 · PMC 4/4                    | | Stale          0 v     |
| v 8  Strategia       | | v Routing        4 BUY · 1 SELL                              | | Manuali        8       |
| > 9  Rivedi          | | v Target         100,00%                                      | | Modificati     3       |
|                      | | v FX              nessuna conversione                         | |                         |
|                      | | v Strategia       Investi e vendi                              | | Schema        1.0.0    |
|                      | +----------------------------------------------------------------+ |                         |
|                      |                                                                     |                         |
|                      | [ Mostra snapshot completo ] [ Mostra solo modificati/stale ]      |                         |
|                      |                                                                     |                         |
|                      | [i] Nessun ordine verrà inviato. Il calcolo usa solo questo payload.|                         |
|                      |                                                                     |                         |
|                      |                         [ Calcola piano ]                           |                         |
+----------------------+---------------------------------------------------------------------+-------------------------+
```

### Submit

1. Validazione cross-step.
2. Copia immutabile del draft.
3. Fingerprint locale.
4. Un solo `POST compute`.
5. Input disabilitati soltanto durante request attiva.
6. Cancel interrompe attesa e segnala cancellazione; non finge risultato.
7. Risposta accettata solo con stessa account generation/request/snapshot.

## 18.17 Review B — decisioni applicate

| Tema | Decisione blueprint |
|---|---|
| Fonte→Broker | selezione cash nello Step 2; link di trasferimento nello Step 3 |
| Conto manuale | `Nome Conto`; saldo dichiarato = limite massimo, non dato grafico |
| Refresh dominio | solo esplicito; conflict modal cambia fatti, mai campi manuali |
| PAC holding | quantità iniziale zero, nessun PMC |
| Rebal holding | custodia intera distinta da quantità economica personale |
| Ordine Broker | enum `whole_quantity` / `monetary_amount` per Broker/valuta |
| Incremento importo | solo `monetary_amount`; nessun `quantity_step` o precisione ambigua |
| Route | priorità + vincoli tipizzati; SELL visibile solo Rebalancer |
| Target | step isolato, nessun “Dopo” |
| FX | spot/source/age/spread/buffer/fee; conversione finale backend |
| Policy/modalità | card enum; PAC riordina tier obiettivo, Rebalancer abilita/vieta SELL |
| Primitive | input transazioni, selector, modali e DataTable riusati/generalizzati |
| Review | snapshot completo; unico compute |

---

# 19. Review C — risultati

> Tutti i valori sono illustrativi. Nessun ordine viene inviato.

## 19.1 Gerarchia comune

```text
Risultato
├── esito leggibile + status/proof/stop separati
├── selettore Primario fixed-L2 / Variante margine
├── delta fra soluzioni
├── grafico primario specifico del Tool
├── KPI funding/costi/residui
├── esposizioni Tipo / Settore / Geografia
├── Asset summary
├── piano operativo foldable: Funding → FX → ordini per Broker
├── Sankey opzionale soltanto per i flussi monetari reali
└── dettagli solver/provenance/issue
```

Il risultato sostituisce lo stepper. “Modifica configurazione” riapre Step 9 con
draft intatto; una modifica rende il risultato stale.

## 19.2 ASCII C1 — Header risultato comune

```text
+------------------------------------------------------------------------------------------------------------------+
| <- Tools                                                                                               [Docs]    |
| PAC Allocator · Piano calcolato                                                                                  |
| Snapshot 15/09/2026 14:35 · Valuta di riferimento EUR · schema 1.0.0                                            |
+------------------------------------------------------------------------------------------------------------------+
| [v] Piano disponibile    [Incumbent Decimal]      [Gap solver noto]   [Completato]                                |
| L2 fixed 3,92421202 EUR² · U 3,725 EUR · 0 hard constraint violati · nessun issue bloccante                        |
|                                                                                                                  |
| [ Modifica configurazione ]                                                  [ Calcola nuovo piano ]             |
+------------------------------------------------------------------------------------------------------------------+
| SOLUZIONE VISUALIZZATA                                                                                           |
| [ Primario · minimo L2 ] [ Variante margine +3,00 EUR ]              [ Confronta le due soluzioni ]              |
+------------------------------------------------------------------------------------------------------------------+
```

Badge non collassati della soluzione selezionata:

- `availability=ready`;
- `variant_result.outcome=incumbent_found`;
- `variant_result.proof=gap_bounded`;
- `variant_result.stop_reason=completed`.

Il primario usa lo stesso envelope di ricerca e una validazione Decimal
indipendente. `completed` o lo status floating `optimal` non usano icona/check
“ottimo”: `optimal_proven` richiede una fonte esatta dichiarata.

---

## 19.3 Scelta grafico primario — confronto alternative ECharts

| Famiglia | Cosa comunica bene | Limite | Decisione v1 |
|---|---|---|---|
| barre raggruppate | confronto semplice fra 2 serie | diventa alta e ripetitiva con 3 stati e molti Asset | fallback accessibile, non primaria |
| matrix mini-bar | molti Asset × stati, scala comune, confronto riga/colonna | richiede etichette e tooltip molto curati | **scelta primaria** |
| dumbbell/slope | distanza fra due valori | perde chiarezza con `Ora/Target/Dopo` e valori vicini | possibile evoluzione, non v1 |
| Sankey standard | flussi reali fra sorgente, Broker, FX e ordini | ogni link ha un solo `value`: stessa larghezza ai due estremi | solo nel piano operativo |
| nastri comparativi verticali | Prima/Target/Dopo della stessa categoria, variazione immediata, nessun incrocio | richiede ECharts `custom`, non `series.sankey` puro | **scelta Tipo/Settore** |
| watermark | trattamento visivo/sfondo | non rappresenta dati | escluso dai grafici decisionali |

Riferimenti considerati:
[watermark](https://echarts.apache.org/examples/en/editor.html?c=watermark),
[matrix mini-bar geo](https://echarts.apache.org/examples/en/editor.html?c=matrix-mini-bar-geo),
[Sankey semplice](https://echarts.apache.org/examples/en/editor.html?c=sankey-simple),
[Sankey verticale](https://echarts.apache.org/examples/en/editor.html?c=sankey-vertical).

Scelte:

- **Asset:** ECharts matrix mini-bar con scala percentuale condivisa. Ogni riga
  parte con `AssetIcon`; ogni colonna è uno stato.
- **Tipo/Settore:** grafico a nastri verticali ispirato a Sankey. Stesse categorie,
  stesso ordine, una corsia per categoria; il nastro si restringe/allarga fra rail
  `Prima`, `Target`, `Dopo`.
- **Funding:** Sankey standard, perché qui esistono veri flussi monetari.

Click/focus apre tooltip accessibile con percentuale, valore assoluto e delta.
Tabella sottostante resta fonte leggibile; nessun grafico sostituisce i numeri.

## 19.4 ASCII C2 — PAC overview desktop

```text
+------------------------------------------------------------------------------------------------------------------+
| PIANO PRIMARIO · MINIMO L2 FIXED                            [ Primario fixed-L2 | Variante margine ]              |
+------------------------------------------------------------------------------------------------------------------+
| TARGET ACQUISTI vs PIANO PROPOSTO · matrix mini-bar                                                    [i]       |
|                                                                                                                  |
| Asset                         Target                      Piano selezionato                 Delta                 |
| [◎] XMAW World               |##############| 70,05%     |##############| 70,08%            +0,03 pp             |
| [◎] XDWF Financials          |###           | 12,71%     |###           | 12,71%             0,00 pp             |
| [◎] XDWI Industrials         |##            | 12,24%     |##            | 12,22%            -0,02 pp             |
| [◎] HEAL Healthcare          |#             |  5,00%     |#             |  4,98%            -0,02 pp             |
|                                                                                                                  |
| [ Apri tabella Asset ]             Scala 0-100% · stesso asse per tutte le celle                                |
+----------------------+----------------------+----------------------+----------------------+----------------------+
| Cash selezionato     | Valore investito     | Costi stimati        | Residuo spendibile   | Cash fisico finale   |
| 3.659,00 EUR         | 3.655,28 EUR         | 0,00 EUR             | 3,72 EUR              | 3,72 EUR             |
+----------------------+----------------------+----------------------+----------------------+----------------------+
| F_ref 3.659,00 · L2 fixed 3,92421202 EUR² · U 3,725 · max |r|/F_ref 0,038% · Dinf pct 0,03 pp · Righe 4       |
+------------------------------------------------------------------------------------------------------------------+
```

PAC confronta Target/Dopo. Nessun “Ora” artificiale: il PAC puro ha patrimonio
iniziale zero. Percentuali usano capitale investito valorizzato a mid; fee, spread e
buffer restano costi/cash separati.

## 19.5 ASCII C3 — Delta soluzione ottimizzata

```text
+------------------------------------------------------------------------------------------------------------------+
| VARIANTE MARGINE                                                                                                 |
| Congela il primario; aggiunge solo BUY. Massimizza impiego e mostra il delta L2 fixed.                           |
+---------------------------+---------------------------+---------------------------+----------------------------+
| Investimento aggiunto     | Fee aggiuntive            | Residuo recuperato        | Nuove righe                |
| +3,00 EUR                 | +0,00 EUR                 | 3,00 EUR                  | 1                          |
+---------------------------+---------------------------+---------------------------+----------------------------+
| Nuova riga · HEAL Healthcare · Broker Margine Demo · BUY cash amount 3,00 EUR                                  |
| Tutte le altre righe invariate.                                                                                  |
+------------------------------------------------------------------------------------------------------------------+
```

“Residuo recuperato” include solo investimento addizionale, mai fee.
Nel witness HEAL×Broker Margine Demo è l'unica route additiva ancora eleggibile:
minimo e cap sono entrambi `3,00 EUR`, con step `0,01`; le quattro route
primarie Directa sono `whole_quantity` e la quota successiva supera il residuo.
Il BUY `+3,00` è quindi il massimo deployment ammissibile e apre una nuova riga
senza modificare il BUY HEAL primario da `20` quote.

## 19.6 ASCII C4 — Esposizioni PAC

```text
+------------------------------------------------------------------------------------------------------------------+
| ESPOSIZIONI                                                       [ Tipo ] [ Settore ] [ Geografia ]             |
+------------------------------------------------------------------------------------------------------------------+
| SETTORE · Target -> Dopo · nastri verticali                                      [ Apri dettaglio v ]           |
|                                                                                                                  |
| TARGET      [ Broad 70,05% ][ Financial 12,71% ][ Industrial 12,24% ][ Health 5,00% ]                           |
|                  ||||||||||          ||||              |||||             ||                                   |
|                  |||||||||/          ||||              |||||             |/    larghezza varia per categoria  |
|                  |||||||||           ||||              |||||             ||                                   |
| DOPO        [ Broad 70,08% ][ Financial 12,71% ][ Industrial 12,22% ][ Health 4,98% ]                           |
|                                                                                                                  |
| Delta              +0,03 pp               0,00 pp             -0,02 pp          -0,02 pp                        |
| [i] Stesso ordine e stessa corsia: nessun incrocio/overlap. È confronto, non flusso monetario.                  |
+------------------------------------------------------------------------------------------------------------------+
| TIPO                                                                                       [ Apri dettaglio v ]    |
| [ stesso grafico a nastri · Target -> Dopo · categorie/Unknown sempre presenti ]                                  |
+------------------------------------------------------------------------------------------------------------------+
| GEOGRAFIA                                                                               [ Mostra delta ]          |
| +-----------------------------------------------+ +-----------------------------------------------+              |
| | MAPPA TARGET · zoom/hover sincronizzati       | | MAPPA DOPO · zoom/hover sincronizzati        |              |
| | Unknown 5,00% sempre esplicito                | | Delta tooltip: Dopo - Target                 |              |
| +-----------------------------------------------+ +-----------------------------------------------+              |
+------------------------------------------------------------------------------------------------------------------+
```

Per PAC le due rail sono `Target` e `Dopo`. Ogni categoria occupa la stessa corsia
su entrambe; larghezza sinistra = Target, larghezza destra = Dopo. Curve di confine
Bezier producono nastro rastremato/espanso, quindi variazione visibile senza
incroci. Un `series.sankey` puro non funziona: il singolo `link.value` imporrebbe
larghezza costante e cancellerebbe una delle due percentuali. Implementazione
prevista: ECharts `custom` con label esplicita “Confronto esposizioni — non flusso”.

Geografia riusa due `GeographyMap` sincronizzate. `Mostra delta` trasforma la
seconda mappa in choropleth divergente `Dopo - Target`; niente archi geografici,
perché il modello non conosce trasferimenti punto-punto.

`Apri dettaglio` espande **sotto lo stesso grafico**, non apre una nuova pagina:

```text
+------------------------------------------------------------------------------------------------------+
| DETTAGLIO TIPO                                                [Colonne] [Filtra] [Chiudi dettaglio]  |
| Categoria | Target % | Dopo % | Delta pp | Target valore | Dopo valore | Unknown/provenance          |
| Equity    | 100,00   | 100,00 |  0,00    | 3.659,00      | 3.655,28    | metadata completa           |
+------------------------------------------------------------------------------------------------------+
```

È un `DataTable` con mini-bar nelle celle percentuali, stessa estetica del grafico
primario. Settore e Geografia usano lo stesso contratto; `Unknown` non scompare.

## 19.7 ASCII C5 — Asset summary PAC

Tabella `DataTable` core. Target e residuo sono Asset-level, quindi non vengono
duplicati per Broker.

```text
+---------------------------------------------------------------------------------------------------+
| ALLOCAZIONE PER ASSET                            [Occhio Colonne] [Filtra] [Reset layout]          |
+-------------------------------+----------------+--------------------+-------------+------------+-------+
| Asset                         | Target fisso   | Valore investito   | Residuo €   | Dopo %     | Route |
| [◎] XMAW World               | 2.563,13 EUR   | 2.561,73 EUR       | -1,40       | 70,08%     | 1     |
| [◎] XDWF Financials          |   465,06 EUR   |   464,59 EUR       | -0,47       | 12,71%     | 1     |
| [◎] XDWI Industrials         |   447,86 EUR   |   446,82 EUR       | -1,04       | 12,22%     | 1     |
| [◎] HEAL Healthcare          |   182,95 EUR   |   182,14 EUR       | -0,81       | 4,98%      | 1     |
+-------------------------------+----------------+--------------------+-------------+------------+-------+
| Totale                        | 3.659,00 EUR   | 3.655,28 EUR       | Σr -3,725  | 100,00%    | 4     |
+---------------------------------------------------------------------------------------------------+
```

`Valore investito` = valore delle unità acquistate convertito a mid nella valuta di
riferimento, costi esclusi. Differisce dall'addebito Broker quando esistono fee,
spread o buffer. `Valore mid` resta nome tecnico di una colonna audit nascosta, non
label default. I target esatti non formattati sono `2.563,1295`, `465,0589`,
`447,8616` e `182,9500`; le celle mostrano centesimi e i totali derivano dai
Decimal originali. Qui `C_free=3,720` e `A_round=+0,005`, quindi `U=3,725`
e `Σr=-3,725`: cash spendibile e shortfall contabile non sono la stessa
grandezza. Per questo `C_free` appare soltanto nei KPI e nei ledger
Broker×valuta, mai come colonna Asset.
Il toggle colonne espone
`Costi attribuiti`, `Buffer riservato`, decomposizione del residuo,
`L2_fixed`, score normalizzato, D∞/D1 diagnostici, route rank e tie reason.
Con target zero, il rapporto target-normalizzato è `—`, non infinito.

## 19.8 ASCII C6 — Rebalancer overview desktop

```text
+------------------------------------------------------------------------------------------------------------------+
| RIBILANCIATORE · INVESTI E VENDI · PRIMARIO FIXED-L2                                                            |
+------------------------------------------------------------------------------------------------------------------+
| PORTAFOGLIO: PRIMA / TARGET / DOPO · matrix mini-bar                                                            |
|                                                                                                                  |
| Asset                         Prima              Target             Dopo               Gap dopo                  |
| [◎] XMAW World               |########| 62,40%  |####### | 55,00%  |####### | 55,18%    +0,18 pp              |
| [◎] XDWF Financials          |#       |  8,10%  |##      | 12,00%  |##      | 11,92%    -0,08 pp              |
| [◎] XDWI Industrials         |###     | 18,50%  |###     | 18,00%  |###     | 17,96%    -0,04 pp              |
| [◎] HEAL Healthcare          |##      | 11,00%  |##      | 15,00%  |##      | 14,95%    -0,05 pp              |
|                                                                                                                  |
| [ Apri tabella Asset ]                                                                                        |
+------------------------------------------------------------------------------------------------------------------+
| MOVIMENTI · BUY 2.346,33 · SELL 1.106,33 · Nuova liquidità 1.252,00 · Cash locale 48,00 · Costi/tax 12,00 |
+------------------------------------------------------------------------------------------------------------------+
```

Il grafico usa l'intero portafoglio investito. BUY e SELL restano anche movimenti
espliciti: la sola differenza percentuale non consente di ricostruirli.
Nel witness `K_reachable=1.300,00` resta composto da due righe sorgente
distinte: contributo nuovo `1.252,00` su Broker Baseline Demo e saldo
preesistente selezionato `48,00` su Broker Margine Demo. Directa non riceve
quel contributo: prima del SELL non ha cash selezionato.

## 19.9 ASCII C7 — KPI Rebalancer

```text
+----------------------+----------------------+----------------------+----------------------+----------------------+
| Investito prima      | Funding raggiungibile| F_ref target/account | Investito dopo F_final| U = F_ref-F_final   |
| 24.800,00 EUR        | 1.300,00 EUR         | 26.100,00 EUR        | 26.040,00 EUR         | 60,00 EUR            |
+----------------------+----------------------+----------------------+----------------------+----------------------+
| U 60,00: cash 48,00 · riserve fisiche 8,00 · perdite economiche 4,00 · rounding +0,00                    |
| Max gap prima 7,40 pp | Max gap dopo 0,18 pp | Turnover 3.452,66 EUR | Ordini BUY 3 · SELL 1 · FX 0              |
+------------------------------------------------------------------------------------------------------------------+
```

Cash KPI resta separato da esposizioni Asset. `F_ref` non include vendite e
genera i target monetari fissi; non è il denominatore delle percentuali
diagnostiche: `Prima` usa il totale investito iniziale,
`Dopo` usa `F_final`. `U` non è sinonimo di cash libero; la disclosure separa
cash spendibile, riserve ancora fisiche, perdite/uscite economiche e rettifica
rounding firmata.

## 19.10 ASCII C8 — Esposizioni Rebalancer

Tipo e Settore usano tre rail verticali `Prima → Target → Dopo`. Ogni categoria
resta nella stessa corsia; il nastro cambia spessore due volte. Target è quindi
misura centrale reale, non arco decorativo. Stesso ordine → nessun incrocio.
Geografia mantiene due mappe sincronizzate `Prima`/`Dopo`; toggle
`Delta dal target` trasforma la seconda in mappa divergente.

```text
+------------------------------------------------------------------------------------------------------------------+
| SETTORE · nastri verticali Prima -> Target -> Dopo                                           [Apri dettaglio v] |
| PRIMA       [ Broad 62% ][ Financial 8% ][ Industrial 19% ][ Health 11% ]                                      |
|                  |||||           ||                ||||              ||                                        |
|                  ||||\           ||\               |||\              ||\                                       |
| TARGET      [ Broad 55% ][ Financial 12%][ Industrial 18% ][ Health 15% ]                                      |
|                  ||||            |||               ||||              |||                                       |
|                  ||||\           |||               ||||              |||                                       |
| DOPO        [ Broad 55,18 ][ Financial 11,92 ][ Industrial 17,96 ][ Health 14,95 ]                              |
| Delta target      +0,18 pp          -0,08 pp             -0,04 pp          -0,05 pp                            |
+------------------------------------------------------------------------------------------------------------------+
| [ Apri dettaglio v ]  DataTable: Prima | Target | Dopo | Delta target | assoluti | provenance                  |
+------------------------------------------------------------------------------------------------------------------+
| MAPPA PRIMA                                             | MAPPA DOPO                         [Delta dal target]   |
| Unknown 11%                                             | Unknown 15%                                             |
+---------------------------------------------------------+--------------------------------------------------------+
```

Hover/focus evidenzia una sola corsia su tutte le rail e legge
`Prima → Target → Dopo`. Niente archi geografici: comunicherebbero movimenti non
calcolati.

## 19.11 ASCII C9 — Asset summary Rebalancer

```text
+------------------------------------------------------------------------------------------------------------------+
| PIANO PER ASSET                                                   [Occhio Colonne] [Filtra] [Reset layout]        |
+--------------------------+-------------+-------------+-------------+-------------+-------------+----------------+
| Asset                    | Valore prima| Target      | BUY invest. | SELL lordo | Valore dopo | r_a / % diag.  |
| [◎] XMAW World          | 15.475,20   | 14.355,00   |        —    | 1.106,33    | 14.368,87   | +13,87/+0,18pp |
| [◎] XDWF Financials     |  2.008,80   |  3.132,00   | 1.094,33    |       —     |  3.103,13   | -28,87/-0,08pp |
| [◎] XDWI Industrials    |  4.588,00   |  4.698,00   |    87,50    |       —     |  4.675,50   | -22,50/-0,04pp |
| [◎] HEAL Healthcare     |  2.728,00   |  3.915,00   | 1.164,50    |       —     |  3.892,50   | -22,50/-0,05pp |
+--------------------------+-------------+-------------+-------------+-------------+-------------+----------------+
| Totale · EUR             | 24.800,00   | 26.100,00   | 2.346,33    | 1.106,33    | 26.040,00   | Σr=-60,00      |
+------------------------------------------------------------------------------------------------------------------+
```

BUY e SELL dello stesso Asset non possono coesistere.
`Target = w_aF_ref` e non totalizza a `Valore dopo`; la differenza monetaria
firmata è `r_a` e `Σ_ar_a=-U`.

## 19.12 ASCII C10–C12 — Piano operativo unificato

C10, C11 e C12 diventano un'unica sezione ordinata. Header foldato comunica
sequenza e totale; apertura mostra il `DataTable` pertinente.

```text
+------------------------------------------------------------------------------------------------------------------+
| PIANO OPERATIVO · 5 azioni                               [ Sequenza ] [ Flusso Sankey ] [Espandi tutti]          |
+------------------------------------------------------------------------------------------------------------------+
| v 1  FUNDING E TRASFERIMENTI             1 azione · 3.655,28 EUR · finanzia Directa Demo                       |
|   +----------------------------------------------------------------------------------------------------------+   |
|   | [Colonne]  Azione | Da | A | Valuta | Importo | Motivo                                                  |   |
|   |             Bonifico | Banca Demo | Directa Demo | EUR | 3.655,28 | Funding ordini                      |   |
|   +----------------------------------------------------------------------------------------------------------+   |
|                                                                                                                  |
| v 2  ORDINI · DIRECTA DEMO                4 BUY · valore investito 3.655,28 EUR · fee 0,00 EUR                  |
|   +----------------------------------------------------------------------------------------------------------+   |
|   | [Colonne] [Filtra]                                                                                       |   |
|   | Asset               Lato Prezzo       Istruzione  Q.tà esatta/st. Valore mid  Addebito  Fee             |   |
|   | [◎] XMAW World     BUY  50,230 EUR   51 quote    51 esatta       2.561,73   2.561,73  0,00            |   |
|   | [◎] HEAL Health    BUY   9,107 EUR   20 quote    20 esatta         182,14     182,14  0,00            |   |
|   | Totale                               4 ordini                    3.655,28   3.655,28  0,00            |   |
|   +----------------------------------------------------------------------------------------------------------+   |
|   Directa Demo · saldo iniziale 3.655,28 · addebiti 3.655,28 · residuo 0,00 EUR                                 |
|   Broker Margine Demo · saldo iniziale 3,72 · addebiti 0,00 · residuo 3,72 EUR                                  |
+------------------------------------------------------------------------------------------------------------------+
| Totale scenario · selezionato 3.659,00 · addebiti 3.655,28 · cash 3,72 · A_round +0,005 · U 3,725              |
| [i] Ordine consigliato. Verificare saldo, prezzi e mercato nel Broker; nessuna esecuzione o settlement impliciti.|
+------------------------------------------------------------------------------------------------------------------+
```

Tab `Flusso Sankey` è ammessa qui perché mostra flussi reali:

```text
Banca Demo EUR -> Directa EUR ->+-> BUY Asset EUR
                                +-> FX EUR/USD -> Directa USD -> BUY Asset USD
```

Non sostituisce sequenza/tabelle. Nodi e link riportano valuta nativa; nessuna
somma tra valute senza conversione.

Colonne default:

| Pannello | Colonne visibili |
|---|---|
| Funding | azione, da, a, valuta, importo, motivo |
| FX | Broker, coppia, debito, credito stimato, spot, spread, safety margin |
| Ordini | Asset con icona, lato, prezzo corrente, istruzione Broker, quantità esatta/stimata, valore mid/lordo, addebito/accredito, costi, buffer, fee |

La v1 non inventa un `Budget route`: il target e $r_a$ restano Asset-level
nella tabella Asset, mentre il cash finale resta Broker×valuta nei ledger.
Ordini e renderer non derivano cash route sottraendo il target dal valore
investito. Un futuro envelope route potrà esistere soltanto come fatto
backend-authored con semantica propria.

`ColumnVisibilityToggle` mostra/ordina colonne audit nascoste:

- ID Asset/Broker/route;
- prezzo mid e prezzo charge/sell;
- addebito/accredito totale;
- FX cost e tasso effettivo;
- source/date/staleness;
- tax reserve e `withholding_kind`;
- rettifica posting rounding firmata;
- vincoli attivi;
- target Asset reference;
- issue/provenance.

Le tabelle ordine dei vari Broker condividono lo stesso layout colonne tramite
`additionalTableRefs`; Funding e FX hanno layout indipendenti.

## 19.13 ASCII C13 — Dettaglio riga BUY/SELL

Espansione riga `DataTable`, non pannello ripetuto:

```text
+------------------------------------------------------------------------------------------------------------------+
| [◎] XMAW World · SELL · Directa Demo                                                                            |
+----------------------+----------------------+----------------------+----------------------+----------------------+
| Istruzione Broker    | Q.tà                 | Credito lordo        | Fee SELL             | Tax reserve          |
| 20 quote             | 20 esatta            | 1.106,33 EUR         | 4,00 EUR             | 8,00 EUR             |
+----------------------+----------------------+----------------------+----------------------+----------------------+
| PMC 53,5780 EUR · plus lorda 34,77 · imponibile post-fee 30,77 · aliquota 26% · self_reserved                 |
| Credito spendibile dopo fee e riserva 1.094,33 EUR · riserva fisica separata 8,00 EUR                         |
| Funding SELL: contribuisce 1.094,33 EUR ai BUY · quantum 1 quota · gate locale verificato 2/2                  |
| Controfattuale -1 quota/riga: funding insufficiente · global=gap_bounded                                       |
| Prezzo/source 55,3165 EUR · Provider Demo · 15/09/2026 · vincoli whole units · issue nessuno                   |
+------------------------------------------------------------------------------------------------------------------+
```

Per `self_reserved`, tax reserve compare anche nel cash fisico finale ma non nel
cash spendibile. Riga BUY mostra prezzo originale/mid/charge, fee, FX cost,
addebito totale, vincoli e provenance con stesso schema visuale.

---

## 19.14 ASCII C14 — Proof e diagnostica

```text
+------------------------------------------------------------------------------------------------------------------+
| Dettagli calcolo                                                                                       [Apri v]  |
+------------------------------------------------------------------------------------------------------------------+
| Availability piano ready                                                                                         |
| Primario            incumbent_found · proof gap_bounded · stop completed                                         |
| Variante margine    incumbent_found · proof gap_bounded · stop completed                                         |
| Validazione         decimal_verified · accounting e tupla obiettivo del candidato                                |
| Solver evidence     SCIP x.y · reported optimal · primal/dual grezzi · tol 1e-7 · settings [Apri]               |
| Objective primario  L2 fixed 3,92421202 EUR² · U 3,725 EUR · route/cost/rows/tie                                |
| Variante            U 0,725 EUR · L2 fixed 8,06421202 EUR² · Delta L2 +4,14000000 EUR²                          |
| Diagnostici         Dinf pct 0,03 pp · D1 pct 0,07 pp · percentuali finali [Apri]                               |
| Limiti             tempo 5s · nodi 50.000 · usati 1.284                                                         |
| Policy primaria    proportional: L2 -> U -> priorità -> fee -> righe -> tie                                     |
| Policy variante    U -> L2 risultante -> costi/righe incrementali -> tie                                        |
| Snapshot           sha256: abcd... · schema 1.0.0                                                               |
| Issue              nessuno                                                                                       |
+------------------------------------------------------------------------------------------------------------------+
```

Lo status floating `reported optimal` resta evidenza numerica: non cambia il
badge in `optimal_proven`. Il foldout mostra valori e unità di ogni bound/tier,
tolleranze, versione e settings; se manca un bound coerente usa `not_proven`.

Dettaglio non nasconde status critici: esito/proof/stop restano sintetizzati
nell'header.

Per Rebalancer lo stesso pannello usa righe specifiche:

```text
+------------------------------------------------------------------------------------------------------------------+
| Dettagli calcolo Rebalancer                                                                          [Apri v]  |
+------------------------------------------------------------------------------------------------------------------+
| Primario            fixed_l2_primary · incumbent_found · proof gap_bounded · stop completed                      |
| Riferimento         F_ref 26.100,00 EUR · target monetari fissi · F_final 26.040,00 EUR > 0                     |
| Score primario      L2 fixed 2.038,3538 EUR² [bound solver grezzi nel foldout]                                  |
| Accounting          F_ref 26.100,00 · U 60,00 = cash 48 + riserve 8 + perdite 4 + rounding +0                  |
| SELL                local=verified 2/2 · global=gap_bounded · 1 quantum attivo · nessuna vendita verso cash idle|
| Variante            margin_deployment · BUY-only su azioni primarie congelate · U 12,00 · Delta L2 +144,0000   |
| Diagnostici         Dinf_pct 0,18 pp · D1_pct 0,36 pp · actual-final percentages                               |
| Ordine primario     L2 fixed -> U -> turnover -> costi -> righe/split -> tie                                    |
| Ordine variante     U -> L2 fixed risultante -> costi/righe incrementali -> tie                                 |
| Coefficienti        scaling/GCD safe · activity safe · dynamic range safe                                        |
| Snapshot            sha256: abcd... · schema 1.0.0                                                              |
+------------------------------------------------------------------------------------------------------------------+
```

I bound solver MIQP/MIQCP e la minimalità SELL mostrano soltanto la prova realmente
ottenuta. “Localmente irriducibile” non diventa “SELL minimo globale”; uno
status floating `optimal` non diventa `optimal_proven`.

## 19.15 Confronto base / ottimizzata

Modalità default: tab singola, perché riduce rumore. “Confronta” apre side-by-side:

```text
+---------------------------------------------------------+--------------------------------------------------------+
| PRIMARIO · MINIMO L2                                    | VARIANTE MARGINE                                       |
| Investito 3.655,28                                      | Investito 3.658,28              +3,00                 |
| Fee 0                                                   | Fee 0                             +0                    |
| Cash spendibile 3,72                                   | Cash spendibile 0,72            -3,00                 |
| U contabile 3,725                                      | U contabile 0,725               -3,000                |
| L2 fixed 3,92421202 EUR²                                | L2 fixed 8,06421202 EUR²          +4,14000000 EUR²     |
| Righe 4                                                 | Righe 5                           +1                    |
+---------------------------------------------------------+--------------------------------------------------------+
| Delta: HEAL +3,00 EUR · cash/U -3,00 EUR · L2 +4,14000000 EUR² · Dinf/D1 diagnostici [Apri]                    |
+------------------------------------------------------------------------------------------------------------------+
```

Il confronto PAC usa la route HEAL-only di `Broker Margine Demo`, con minimo e
cap `3,00 EUR`, dichiarata in B10/C3; senza quel dominio la route monetaria
dovrebbe continuare a ridurre `U` e il witness non sarebbe un optimum della
variante.

Se le soluzioni coincidono:

```text
[i] Nessun acquisto addizionale ammissibile. La variante coincide con il primario.
```

Nel Rebalancer la stessa interazione confronta primario e variante margine:

```text
+---------------------------------------------------------+--------------------------------------------------------+
| PRIMARIO FIXED-L2                                       | VARIANTE MARGINE                                       |
| L2 fixed 2.038,3538 EUR²                                | L2 fixed 2.182,3538 EUR²         +144,0000 EUR²        |
| U 60,00                                                 | U 12,00                          -48,00                 |
| SELL 1.106,33 · 1 riga                                  | SELL invariato                    =                    |
| BUY 2.346,33 · 3 righe                                  | BUY +48,00 · 1 riga              +                    |
+---------------------------------------------------------+--------------------------------------------------------+
| Delta: HEAL BUY +48,00 (unica route residua eleggibile) · U -48,00 · SELL invariati · L2 +144,0000 [Apri]       |
+------------------------------------------------------------------------------------------------------------------+
```

Nel witness sintetico Rebalancer, `C_free=48,00` è già sul Broker Margine Demo.
Una nuova route HEAL-only `monetary_amount` ha minimo se si opera e cap entrambi
pari a `48,00`; nessun importo minore appartiene al dominio. Le route additive
degli altri Asset sono già al cap o non eleggibili. Senza tali vincoli, un BUY
minore su HEAL o un BUY di `48,00` su XDWF ridurrebbe `L2_fixed` e dovrebbe
essere promosso a nuovo primario anziché apparire come variante peggiorativa.
La sequenza congelata è esplicita: `invest_only` usa `1.164,50` su HEAL e
`87,50` su XDWI, lasciando entrambi a residuo `-22,50`; il SELL successivo
finanzia `1.094,33` su XDWF. La variante porta il solo residuo HEAL a `+25,50`.

## 19.16 Review C — decisioni applicate

| Tema | Decisione blueprint |
|---|---|
| Primo grafico PAC | matrix mini-bar Target/Piano; Asset icon; nessun Ora artificiale |
| Primo grafico Rebalancer | matrix mini-bar Prima/Target/Dopo intero portafoglio |
| Sankey standard | solo flussi reali Funding→Broker→FX→ordini |
| Tipo/Settore | nastri verticali custom, stesse corsie, Prima→Target→Dopo |
| Geografia | due mappe sincronizzate + delta divergente; niente archi falsi |
| “Apri dettaglio” | `DataTable` inline con mini-bar, assoluti, delta, Unknown/provenance |
| Cash | KPI separati dagli Asset |
| Target/residuo | Asset summary una sola volta |
| Valore mid | default rinominato `Valore investito`; termine tecnico solo audit |
| Asset | `AssetIcon` in grafici e tabelle |
| Operatività | un solo blocco foldable: funding → FX → Broker |
| Tabelle | `DataTable`; `ColumnVisibilityToggle`; layout condiviso fra Broker |
| Tabella Broker core | prezzo, budget, istruzione, quantità, investito/lordo, margine, fee |
| Coppia risultati | Primario fixed-L2 / Variante margine per entrambi i Tool |
| Proof | status separati; mai “ottimo” senza prova |

# 20. Review D — mobile e stati

## 20.1 Regola mobile

Mobile non riduce il contratto. Cambia presentazione:

- tabella → card/accordion;
- summary rail → bottom sheet;
- stepper → progress compatto;
- colonne parallele → sezioni verticali;
- audit avanzato → disclosure;
- CTA core sempre raggiungibili.

## 20.2 ASCII D1 — Funding mobile

```text
+--------------------------------------------+
| Passo 2 di 9                    [Riepilogo] |
| [==========------------------------------] |
| Liquidità e fonti                         |
+--------------------------------------------+
| Scegli solo cash utilizzabile nel piano.   |
|                                            |
| [ + Nuova liquidità ]                      |
| [ Prendi da conto/Broker ]                 |
| [ + Fonte manuale ]                        |
|                                            |
| +----------------------------------------+ |
| | Banca Demo                 [S] [Edit] | |
| | Disponibile 8.400,00 EUR              | |
| | Usa                                   | |
| | [ 2.500,00                       ] EUR | |
| | max 8.400,00                          | |
| +----------------------------------------+ |
|                                            |
| +----------------------------------------+ |
| | Nuovo risparmio            [M] [Edit] | |
| | 1.000,00 EUR                           | |
| +----------------------------------------+ |
|                                            |
| Totale nativo                              |
| EUR 3.500,00                               |
+--------------------------------------------+
| [ <- Indietro ]             [ Continua -> ]|
+--------------------------------------------+
```

Nessuna griglia a due colonne; amount/currency restano associati nella stessa card.

## 20.3 ASCII D2 — Broker editor mobile

```text
+--------------------------------------------+
| Configura Broker PAC Demo               [x]|
+--------------------------------------------+
| [1] Conti e ordini                         |
| Valuta [EUR v]                             |
| FX [Solo valuta nativa v]                  |
| Cosa inserisci nel Broker                  |
| [ Importo da investire v ]                 |
| Incremento minimo [1,00] EUR               |
| [ + Valuta ]                               |
|                                            |
| [2] Commissioni                            |
| +----------------------------------------+ |
| | BUY · EUR                        [v]   | |
| | Fisso 1,00 · 0,10% · min 0 · max —    | |
| | [ Modifica ]                            | |
| +----------------------------------------+ |
| | SELL · EUR                       [!]   | |
| | Mancano minimo/massimo                  | |
| | [ Completa ]                            | |
| +----------------------------------------+ |
|                                            |
| [3] Fiscalità                              |
| Regime [Dichiarativo/libero v]             |
| Minus [0,00] EUR · 15/09/2026              |
|                                            |
| [4] Funding                                |
| [v] Banca Demo EUR                         |
| [ ] Conto USD manuale                      |
+--------------------------------------------+
| [ Annulla ]                [ Applica ]      |
+--------------------------------------------+
```

Editor lungo usa sezioni numerate, non tab orizzontali nascoste.

## 20.4 ASCII D3 — Routing mobile

```text
+--------------------------------------------+
| Passo 5 di 9 · Routing         Asset 2 di 4|
| XMAW World                                 |
| [ BUY ] [ SELL ]                           |
+--------------------------------------------+
| +----------------------------------------+ |
| | [v] Directa Demo                 v     | |
| | Priorità 1 · EUR · intero              | |
| | Minimo se operi 0                      | |
| | Obbligo nessuno · Cap nessuno          | |
| | [ Modifica vincoli ]                   | |
| +----------------------------------------+ |
| +----------------------------------------+ |
| | [v] Broker PAC Demo              !     | |
| | Priorità 1 · EUR · cash step 1         | |
| | Minimo 25 · Obbligo 100                | |
| | Cap 1.500 EUR                          | |
| | [ Modifica vincoli ]                   | |
| +----------------------------------------+ |
|                                            |
| [ < Asset ]              [ Asset > ]       |
+--------------------------------------------+
| [ <- Indietro ]             [ Continua -> ]|
+--------------------------------------------+
```

Il cambio Asset mantiene tab BUY/SELL selezionata. Badge incompleto resta testuale.

---

## 20.5 ASCII D4 — Risultato PAC mobile

```text
+--------------------------------------------+
| PAC Allocator · Piano calcolato             |
| 15/09/2026 · EUR                            |
| [v] Verificato Decimal · Gap solver noto    |
| [ Modifica configurazione ]                 |
+--------------------------------------------+
| Soluzione                                   |
| [ Primario ] [ Variante margine +3,00 EUR ] |
+--------------------------------------------+
| Target acquisti vs piano · matrix           |
| [◎] XMAW World                             |
| Target 70,05 |##############|               |
| Piano  70,08 |##############|  +0,03 pp     |
| [◎] XDWF Financials                        |
| Target 12,71 |###           |               |
| Piano  12,71 |###           |   0,00 pp     |
| [ Apri tabella Asset ]                      |
+--------------------------------------------+
| Valore investito                            |
| 3.655,28 EUR                                |
| Costi 0 · Cash 3,72 · U 3,725               |
+--------------------------------------------+
| Esposizioni                                 |
| Tipo · Target/Dopo                     [>]  |
| Settore · Target/Dopo                  [>]  |
| Geografia · 2 mappe + delta            [>]  |
+--------------------------------------------+
| Asset · DataTable/card               4 [>]  |
| Piano operativo                     5 [>]  |
|   1 Funding · 0 FX · 1 Broker con ordini   |
| Dettagli calcolo                       [>]  |
+--------------------------------------------+
```

Ordine informazioni uguale al desktop. Tipo/Settore mostrano corsie
Target→Dopo; nel Rebalancer ogni categoria diventa una mini-card
Prima→Target→Dopo quando il grafico completo non entra. Le mappe diventano coppie
verticali; nessun carosello obbligatorio. `Piano operativo` apre gli stessi fold
Funding→FX→Broker, non schermate duplicate.

## 20.6 ASCII D5 — Ordine mobile

```text
+--------------------------------------------+
| [◎] XMAW World · BUY                       |
| Directa Demo                                |
+--------------------------------------------+
| Istruzione Broker                           |
| 51 quote                                    |
|                                            |
| Prezzo corrente       50,230 EUR            |
| Quantità              51 esatta             |
| Valore investito      2.561,730 EUR         |
| Costi attribuiti          0,000 EUR         |
| Buffer riservato          0,000 EUR         |
| Fee BUY               0,00 EUR              |
| Addebito totale       2.561,73 EUR          |
|                                            |
| [ Colonne/dettagli audit v ]                |
| Originale/mid/charge  50,230 / 50,230       |
| Target Asset [ref]    2.563,1295 EUR        |
| Residuo Asset [ref]      -1,3995 EUR        |
| Provenance            Provider · 15/09      |
+--------------------------------------------+
```

È proiezione mobile della stessa riga `DataTable`; nessun secondo modello dati.
Istruzione operativa è sempre primo valore dopo titolo/lato/Broker.

## 20.7 ASCII D6 — Confronto mobile

```text
+--------------------------------------------+
| Confronta soluzioni                      [x]|
+--------------------------------------------+
| Metrica          Primario          Margine |
| Investito         3.655,28        3.658,28 |
| Fee                   0,00            0,00 |
| Cash spendibile       3,72            0,72 |
| U contabile          3,725           0,725 |
| L2 fixed EUR²    3,92421202      8,06421202 |
| Righe                     4               5 |
|                                            |
| Delta                                      |
| HEAL · BUY +3,00 EUR                       |
+--------------------------------------------+
| [ Mostra variante margine ]                |
+--------------------------------------------+
```

---

## 20.8 ASCII D7 — Busy e cancel

```text
+------------------------------------------------------------------------------------------------------------------+
| CALCOLO IN CORSO                                                                                                 |
| [spinner] Validazione e ricerca del piano operativo...                                                           |
|                                                                                                                  |
| Snapshot rev. 18 · 4 Asset · 3 Broker · 5 route · limite 5s                                                     |
| La configurazione è bloccata finché questa richiesta è attiva.                                                   |
|                                                                                                                  |
| [ Interrompi attesa ]                                                                                           |
+------------------------------------------------------------------------------------------------------------------+
```

Regole:

- nessun timer cosmetico che prometta avanzamento;
- spinner `motion-reduce`;
- cancel invia abort/checkpoint;
- navigazione/account change abortiscono;
- una seconda richiesta non parte finché la prima è owner;
- risposta vecchia ignorata.

## 20.9 ASCII D8 — Invalid locale

```text
+------------------------------------------------------------------------------------------------------------------+
| [!] Completa 2 campi prima di continuare                                                                         |
| 1. Importo da usare supera il saldo disponibile.                                      [ Vai al campo ]          |
| 2. La valuta della fonte manuale è obbligatoria.                                      [ Vai al campo ]          |
+------------------------------------------------------------------------------------------------------------------+
| Banca Demo · Importo da usare *                                                                                  |
| [ 9.000,00 ] EUR                                                                                                 |
| ! Massimo disponibile: 8.400,00 EUR                                                                              |
+------------------------------------------------------------------------------------------------------------------+
```

Non chiama backend. Error summary riceve focus; link porta al controllo.

## 20.10 ASCII D9 — `needs_input`

```text
+------------------------------------------------------------------------------------------------------------------+
| [!] Il backend richiede dati aggiuntivi                                                                          |
| Nessun piano è stato calcolato. Il draft è conservato.                                                           |
+------------------------------------------------------------------------------------------------------------------+
| PMC_MISSING                                                                                                      |
| XMAW World · Fineco Demo · PMC e valuta fiscale necessari per “Investi e vendi”.                                |
| [ Vai a Asset e holding ]                                                                                        |
|                                                                                                                  |
| FX_QUOTE_STALE_UNCONFIRMED                                                                                       |
| EUR -> USD · quotazione di 5 giorni fa non confermata.                                                           |
| [ Vai a FX ]                                                                                                     |
+------------------------------------------------------------------------------------------------------------------+
```

`availability=needs_input`; nessuna soluzione e nessuna falsa infeasibility.

## 20.11 ASCII D10 — `unsupported`

```text
+------------------------------------------------------------------------------------------------------------------+
| [!] Scenario non supportato dalla prima versione                                                                 |
| Nessun piano operativo prodotto.                                                                                 |
+------------------------------------------------------------------------------------------------------------------+
| FX_MULTI_HOP_UNSUPPORTED                                                                                         |
| La route richiede EUR -> USD -> JPY. La v1 ammette un solo hop.                                                  |
|                                                                                                                  |
| [ Modifica routing/FX ]                                                          [ Torna al riepilogo ]         |
+------------------------------------------------------------------------------------------------------------------+
```

Scenario ben formato ma fuori dominio. Nessun fallback o semplificazione silenziosa.

## 20.12 ASCII D11 — `no_op`

```text
+------------------------------------------------------------------------------------------------------------------+
| [i] Nessuna operazione proposta                                                                                  |
| Il piano vuoto è fattibile; nessun ordine ammesso migliora l'obiettivo con questi input.                         |
+------------------------------------------------------------------------------------------------------------------+
| Motivo principale        Budget sotto i minimi condizionali                                                      |
| Cash selezionato         20,00 EUR                                                                               |
| Minimo ordine utile      25,00 EUR                                                                               |
| Hard constraint violati  0                                                                                       |
|                                                                                                                  |
| Primario                 0 ordini · U 20,00 EUR · optimal_proven                                                 |
| Variante margine         coincide con primario · delta 0                                                        |
|                                                                                                                  |
| [ Modifica liquidità ] [ Modifica vincoli ]                                                                      |
+------------------------------------------------------------------------------------------------------------------+
```

No-op non è errore e non è infeasible.

## 20.13 ASCII D12 — `infeasible_proven`

```text
+------------------------------------------------------------------------------------------------------------------+
| [x] Vincoli incompatibili · infeasibilità provata                                                                |
| Non esiste alcun piano, incluso il piano vuoto, che soddisfi tutti i vincoli obbligatori.                        |
+------------------------------------------------------------------------------------------------------------------+
| REQUIRED_MIN_NOTIONAL_UNFUNDED                                                                                   |
| XMAW World · Directa Demo · BUY obbligatorio 1.000 EUR                                                           |
| Cash raggiungibile sulla route 800 EUR                                                                           |
|                                                                                                                  |
| Outcome            infeasible_proven · proof_source deterministic_conflict                                      |
| Witness            mandatory debit 1.000 EUR > reachable cash 800 EUR · Decimal                                 |
| Stop               completed                                                                                     |
|                                                                                                                  |
| [ Vai al vincolo ] [ Vai alla liquidità ]                                                                        |
+------------------------------------------------------------------------------------------------------------------+
```

Compare solo con conflict witness Decimal deterministico o oracle esaustivo
esatto. Uno status floating `infeasible` usa invece
`no_incumbent/not_proven`, anche se lo stop è `completed`.

## 20.14 ASCII D13 — Incumbent con limite

```text
+------------------------------------------------------------------------------------------------------------------+
| [!] Piano fattibile · ottimalità non provata                                                                     |
| Il limite di tempo è stato raggiunto. Le operazioni mostrate rispettano cash e vincoli, ma potrebbe esistere     |
| una soluzione migliore.                                                                                          |
+------------------------------------------------------------------------------------------------------------------+
| Outcome      incumbent_found       Proof gap_bounded      Stop time_limit                                       |
| Validation   decimal_verified      Solver gap 1,8%        Tol/version/settings [Apri]                           |
|                                                                                                                  |
| [ Mostra piano fattibile ]                              [ Modifica scenario ]                                    |
+------------------------------------------------------------------------------------------------------------------+
```

Ordini possono essere mostrati perché incumbent è fattibile. Label “ottimo” vietata.

## 20.15 ASCII D14 — Limite senza incumbent

```text
+------------------------------------------------------------------------------------------------------------------+
| [!] Nessun piano trovato entro il limite                                                                         |
| Non è una prova di infeasibilità. Nessuna operazione viene mostrata.                                             |
+------------------------------------------------------------------------------------------------------------------+
| Outcome      no_incumbent          Proof not_proven       Stop node_limit                                       |
|                                                                                                                  |
| [ Semplifica vincoli ] [ Torna al riepilogo ]                                                                    |
+------------------------------------------------------------------------------------------------------------------+
```

## 20.16 ASCII D15 — Risultato stale

```text
+------------------------------------------------------------------------------------------------------------------+
| [!] Risultato non aggiornato                                                                                     |
| Hai cambiato il target dopo questo calcolo. Valori e ordini sotto restano consultabili, ma non descrivono più    |
| il draft corrente.                                                                                                |
|                                                                                                                  |
| Snapshot risultato rev. 18 · Draft corrente rev. 19                                                              |
| [ Torna a Rivedi ] [ Scarta risultato precedente ]                                                               |
+------------------------------------------------------------------------------------------------------------------+
| RISULTATO PRECEDENTE · NON CORRENTE                                                                               |
| ... contenuto mantenuto con watermark/banner persistente ...                                                     |
+------------------------------------------------------------------------------------------------------------------+
```

Nessun ricalcolo automatico.

## 20.17 ASCII D16 — Cambio account/sessione

```text
+--------------------------------------------------------------+
| Sessione cambiata                                            |
| Il Tool è stato azzerato per proteggere i dati del conto.    |
|                                                              |
| [ Torna ai Tools ]                                           |
+--------------------------------------------------------------+
```

Comportamento:

- abort copy/compute;
- smonta renderer;
- elimina draft/risultato dalla memoria UI;
- non mostra dati del precedente account;
- nuovo mount parte dalla nuova account generation.

## 20.18 Matrice status backend → UI

| Availability | Outcome | Proof | Evidence | Presentazione |
|---|---|---|---|---|
| `needs_input` | — | — | issue input | issue azionabili; nessuna soluzione |
| `unsupported` | — | — | confine dichiarato | nessun fallback |
| `ready` | `no_op` | `optimal_proven` | exact oracle/score-lattice | ricerca vuota provata + fonte |
| `ready` | `infeasible_proven` | `infeasibility_proven` | conflict Decimal/exact oracle | dominio vuoto provato; nessuna soluzione |
| `ready` | `incumbent_found` | `optimal_proven` | exact oracle/score-lattice | piano Decimal + badge/prova esatta |
| `ready` | `incumbent_found` | `gap_bounded` | solver bound/tolleranze/versione/settings | piano Decimal + gap noto; stop completed o limite |
| `ready` | `incumbent_found` | `not_proven` | bound assente/non confrontabile | piano Decimal + warning |
| `ready` | `no_incumbent` | `not_proven` | limite/cancel o floating infeasible | nessun piano; non infeasible provato |

`L2_fixed`, `U`, diagnostici, `cash_deficit` e objective values restano
metriche, non status.
Ogni riga con piano espone `incumbent_validation=decimal_verified`; ciò certifica
il candidato, non l’ottimalità. `reported optimal/infeasible` del solver resta nel
foldout tecnico e non viene promosso. `proof_source=exhaustive_oracle |
score_lattice_closure` è obbligatorio per `optimal_proven`; per
`infeasible_proven` sono ammessi soltanto `deterministic_conflict |
exhaustive_oracle`.

I campi `availability`, `outcome`, `proof`, `proof_source` e `stop_reason`
seguono le union discriminate del
[piano architetturale §14](plan-phase00PacRebalancerArchitecture.prompt.md);
non sono alias intercambiabili. La closure coefficient-safe è definita nel
[nucleo matematico §19.2.1](plan-phase00PacRebalancerMathematicalCore.prompt.md),
non dalla tolerance floating del solver.

---

## 20.19 Accessibilità completa

### Wizard

- navigazione step come `nav` + lista ordinata;
- titolo step riceve focus;
- error summary con anchor;
- campi Decimal con label/unità esterna ma associata;
- enum come radio group o select, non switch multipli;
- disclosure con stato `aria-expanded`;
- badge stale/modificato con testo.

### Grafici

- titolo e descrizione;
- alternativa tabellare sempre disponibile;
- colori accompagnati da label/marker/pattern;
- Ora/Target/Dopo non distinti solo da tonalità;
- tooltip raggiungibili da tastiera;
- animazioni disattivate con reduced motion.

### Tabelle/card

- header persistenti desktop;
- mobile card mantiene ordine semantico;
- lato BUY/SELL testuale;
- numeri allineati e valuta ripetuta dove ambigua;
- dettaglio riga controllabile da tastiera;
- nessuna azione core nel solo context menu.

### Modali/sheet

- focus trap;
- titolo associato;
- Escape annulla quando sicuro;
- conferma distruttiva esplicita;
- focus restituito al trigger.

---

## 20.20 Privacy e provenance

- Privacy mode oscura importi, quantità, costi, percentuali e valori grafici.
- Status, issue, label campo e completezza restano leggibili.
- Nessun payload in log browser, URL, analytics o error message.
- Nessun dato reale nell'artifact, fixture o screenshot docs.
- Ogni fatto copiato mostra:
  - dominio sorgente;
  - timestamp/data;
  - stato stale;
  - eventuale modifica manuale.
- “Ripristina” usa l'ultima proposta già applicata; un nuovo fetch richiede preview.
- Snapshot risultato conserva provenance ricevuta dal backend.

---

## 20.21 Component map visuale

Questa è mappa di responsabilità, non ancora piano file-per-file. I nomi nuovi sono
concettuali; Phase 2 dovrà confermarli contro il codice corrente.

```text
ToolHost (esistente)
└── PacPlannerView / RebalancerPlannerView
    └── AllocationPlannerShell
        ├── PlannerStepNavigation
        ├── PlannerSummary
        ├── ScenarioStep
        ├── FundingSourcesStep
        │   ├── FundingSourceCard
        │   └── ExplicitRefreshConflictModal
        ├── TradingBrokersStep
        │   ├── TradingBrokerCard
        │   └── TradingBrokerEditor
        ├── AssetsStep
        │   ├── AssetSelectionGallery
        │   ├── AssetSelect
        │   ├── AssetScenarioEditor
        │   └── HoldingEditor
        ├── AssetBrokerRoutingStep
        │   └── SideOrderConstraintsEditor
        ├── PlannerTargetStep
        ├── OperationalFxStep
        ├── PlannerStrategyStep
        ├── PlannerReviewStep
        └── PlannerResultView
            ├── OutcomeSummary
            ├── SolutionSelector
            ├── AssetAllocationMatrixChart
            ├── ExposureComparison
            │   ├── VerticalExposureRibbonChart
            │   ├── PairedGeographyMaps
            │   └── ExposureDetailDataTable
            ├── AssetPlanDataTable
            ├── OperationalPlan
            │   ├── FundingActionsDataTable
            │   ├── FxActionsDataTable
            │   ├── BrokerOrdersDataTable
            │   └── MoneyFlowSankey
            └── SolverDiagnostics
```

### Indice componenti da riusare

| Superficie | Path corrente | Uso/gate |
|---|---|---|
| importo + valuta | `frontend/src/lib/components/ui/display/CompactCashCell.svelte` | default per cash, prezzo, PMC e fee; non ricreare parsing locale |
| Decimal generico | `frontend/src/lib/components/ui/input/ExactDecimalInput.svelte` | percentuali/rate; verificare behavior parity prima di estendere |
| quantità transazione | `frontend/src/lib/components/transactions/modals/TransactionFormModal.svelte` | estrarre input condiviso; migrare form esistente prima dei planner |
| selezione Asset | `frontend/src/lib/components/ui/select/AssetSelect.svelte` | singola selezione in riga, icona e create callback |
| selezione Broker | `frontend/src/lib/components/ui/select/BrokerSearchSelect.svelte` | singola selezione, ruolo, disabled IDs e create callback |
| gallery Asset | `frontend/src/lib/features/tools/pac-allocator/OwnedAssetGallery.svelte` | riusare interazione multi-select/provenance; contratto P1 da sostituire |
| creazione persistente Asset | `frontend/src/lib/components/assets/AssetModal.svelte` | solo CTA persistente autorizzata |
| creazione persistente Broker | `frontend/src/lib/components/brokers/BrokerModal.svelte` | solo CTA persistente autorizzata |
| icone | `frontend/src/lib/components/assets/AssetIcon.svelte`, `frontend/src/lib/components/brokers/BrokerIcon.svelte` | tutte le card, select, chart label e tabelle |
| tabella | `frontend/src/lib/components/table/DataTable.svelte` | config/result/detail; sorting/filter/resize/footer/mobile |
| colonne | `frontend/src/lib/components/table/ColumnVisibilityToggle.svelte` | core visibile, audit opzionale; sincronizza tabelle Broker |
| conferma | `frontend/src/lib/components/ui/modals/ConfirmModal.svelte` | cancellazione dipendenze e conflitti espliciti |
| valuta/data | `frontend/src/lib/components/ui/select/CurrencySearchSelect.svelte`, `frontend/src/lib/components/ui/date/SingleDatePicker.svelte` | controlli esistenti, no select/input paralleli |
| esposizioni | `frontend/src/lib/components/charts/AllocationPieChart.svelte`, `frontend/src/lib/components/charts/GeographyMap.svelte` | `GeographyMap` riusata; pie solo fallback/compact se utile |
| KPI | `frontend/src/lib/components/dashboard/KpiCard.svelte` | linguaggio Dashboard prima/dopo |
| ECharts reference | `frontend/src/lib/components/dashboard/ExposureTreemap.svelte` | base lifecycle/theme/resize/touch per nuovo `custom` ribbon chart |
| host/catalogo | `frontend/src/lib/features/tools/ToolHost.svelte`, `frontend/src/lib/features/tools/ToolsHub.svelte` | conservare guardie, docs, catalog e account generation |

Gate Phase 2 obbligatorio per l'input quantità:

1. confrontare `ExactDecimalInput` con edit buffer/handler quantità della transazione;
2. estrarre o estendere un solo componente shared;
3. migrare `TransactionFormModal` con comportamento invariato;
4. riusarlo nei planner;
5. vietare componenti planner-locali per quantità/importi.

## 20.22 Inventario P1 visuale

| P1 | Blueprint | Classificazione |
|---|---|---|
| `ToolHost` | host esterno al wizard | conserva |
| `ToolsHub` | card con copy operativo | conserva/adatta contenuto |
| `PacAllocatorTool` | `PacPlannerView` | sostituisce |
| `PortfolioRebalancerTool` | `RebalancerPlannerView` | sostituisce |
| `PacMoneySection` | `FundingSourcesStep` | ridisegna |
| `OwnedAssetGallery` | `AssetPicker` | riusa pattern, contratto nuovo |
| `PacAssetEditor` | `AssetScenarioEditor` | sostituisce `buy_grid` |
| `RebalanceHoldingEditor` | Asset + holdings | ridisegna |
| `AllocationTargetEditor` | `PlannerTargetStep` | riusa Decimal/DataTable |
| `AllocationFxSection` | `OperationalFxStep` | sostituisce semantica P1 |
| `PacResultPanel` | `PlannerResultView` PAC | elimina/sostituisce |
| `RebalancerResultPanel` | `PlannerResultView` Rebalancer | elimina/sostituisce |
| `AllocationDiagnostics` | `OutcomeSummary` | riusa pattern, amplia status |

## 20.23 Review D — decisioni applicate

| Tema | Decisione blueprint |
|---|---|
| Mobile input | card/accordion, nessuna tabella orizzontale core |
| Mobile result | stessa gerarchia desktop; matrix card, mini-corsie exposure, piano operativo unico |
| Ordine mobile | proiezione stessa riga DataTable; istruzione prima, audit foldato |
| Busy | stato vero + cancel; nessun progresso finto |
| Invalid | locale, focus/error summary, no request |
| Needs input | issue backend con deep-link |
| Unsupported | confine v1 esplicito |
| No-op | risultato valido, non errore |
| Infeasible | solo con prova |
| Limit | incumbent distinto da nessun incumbent |
| Stale | risultato consultabile ma marcato non corrente |
| Account change | reset completo |
| Grafici | alternativa DataTable; nastri senza overlap + mappe in coppia verticale |
| Privacy | valori e grafici protetti |

---

# 21. Consolidamento visuale

## 21.1 Flusso PAC finale

```text
Tools Hub
  -> Scenario
  -> Liquidità
  -> Broker operativi
  -> Asset target
  -> Routing BUY
  -> Target nuova allocazione
  -> FX potenziali
  -> Strategia PAC
  -> Review snapshot
  -> Compute
  -> Matrix mini-bar Target/Piano
  -> Esposizioni Target/Dopo · nastri/mappe
  -> Asset summary DataTable
  -> Piano operativo unico: Funding -> FX -> ordini BUY per Broker
```

## 21.2 Flusso Rebalancer finale

```text
Tools Hub
  -> Scenario
  -> Liquidità/contributi
  -> Broker operativi
  -> Asset + holding/PMC
  -> Routing BUY/SELL
  -> Target intero portafoglio
  -> FX potenziali
  -> Investi soltanto | Investi e vendi
  -> Review snapshot
  -> Compute
  -> Matrix mini-bar Prima/Target/Dopo
  -> Esposizioni Prima/Target/Dopo · nastri/mappe
  -> Asset summary BUY/SELL DataTable
  -> Piano operativo unico: Funding -> FX -> ordini per Broker
```

## 21.3 Controllo copertura

| Area | Coperta |
|---|---|
| Hub e route separate | sì |
| Shell desktop/tablet/mobile | sì |
| Avanti/indietro senza perdita | sì |
| Conferma cancellazione dipendenze | sì |
| Scenario | sì |
| Nuova liquidità | sì |
| Existing account/Broker | sì |
| Fonte manuale | sì |
| Copy preview/stale | sì |
| Broker esistente/manuale | sì |
| Capability/fee/tax/minus | sì |
| Asset PAC | sì |
| Holding Rebalancer/PMC | sì |
| Asset×Broker BUY/SELL | sì |
| Target distinti | sì |
| FX spot/age/spread/buffer/fee | sì |
| Strategie v1 | sì |
| Snapshot/compute unico | sì |
| PAC primario fixed-L2/variante margine | sì |
| Rebalancer primario fixed-L2/variante margine | sì |
| Grafici/esposizioni | sì |
| Dettagli esposizione DataTable | sì |
| Funding/FX/ordini | sì |
| Indice componenti shared | sì |
| Invalid/needs input/unsupported | sì |
| No-op/infeasible/limits | sì |
| Busy/stale/account change | sì |
| Mobile results | sì |
| Accessibilità/privacy/provenance | sì |

## 21.4 Decisioni estetiche approvate

1. Stepper verticale desktop + summary rail.
2. Nove step input con “Scenario” iniziale.
3. Tablet con rail numerica orizzontale.
4. Mobile con progress + bottom sheet.
5. Risultato fuori dallo stepper.
6. Avanti/indietro conserva il draft.
7. Modifica distruttiva richiede modal con impatto esatto.
8. CTA primaria `Continua`, non `Salva e continua`.
9. Riuso/generalizzazione dei componenti shared esistenti.

## 21.5 Decisioni estetiche approvate nella review finale

1. Matrix mini-bar come grafico Asset primario.
2. Tipo/Settore con rail verticali e nastri rastremati Prima→Target→Dopo.
3. Geografia con mappe sincronizzate + delta divergente, senza archi.
4. Tabelle desktop `DataTable` + proiezione card/accordion mobile.
5. Unico Piano operativo foldable Funding → FX → Broker, con Sankey opzionale.
6. Tab della coppia Tool-specific + compare esplicito.
7. Label `Routing` oppure alternativa più parlante.

---

# 22. Review log

| Review | Stato | Decisioni |
|---|---|---|
| A — IA e shell | **Approvata dal developer** | Wizard incrementale, draft persistente, responsive shell |
| B — input | **Approvata dal developer** | Conto manuale, refresh sicuro, enum ordine, component reuse |
| C — risultati | **Approvata dal developer** | Matrix, nastri verticali/mappe, DataTable, piano operativo unico |
| D — mobile/stati | **Approvata dal developer** | Stesso modello dati, card mobile, matrice outcome/proof/stop |
| Finale | **Approvata dal developer** | Configurazione UI completa congelata come fonte Round 6 |
