# Risk Analysis — ripianificazione

**Data apertura**: 16 Settembre 2026
**Stato**: ⏸️ **in pausa fino a dopo la 1.2**, per decisione del developer (D382, 09/10/2026): la cartella resta in
`Phase_0/` e non si archivia
**Premessa (16/09)**: il sottosistema Risk era **rilasciato in beta** con un banner su ogni vista. Dalla 1.2.0 il banner
resta solo sul gradino «simulazione» di L4 e sulla scheda Rischio di Asset Detail (CHANGELOG 1.2.0).

## ⏸️ In pausa fino a dopo la 1.2 — cosa resta aperto

Il developer, il 09/10/2026: *«risk facciamo bene ad aggiornarlo, ma non lo archivamo perchè ancora non va bene, lo so
già guardandolo, solo mi sono fermato dal lavorarlo per concludere questa release»* (D382). La cartella resta intera in
`Phase_0/`, e le voci aperte della famiglia Risk (Risk, A, F) stanno **qui, e solo qui**. I piani sono allineati al
codice di `3cceb4f90` (09/10/2026): ogni passo chiuso porta la sua evidenza, e ogni passo ancora aperto rimanda a
questo elenco.

### Lavoro pianificato e non fatto

| # | cosa | da dove viene |
|---|---|---|
| A1 | **Fase 3**: il pannello «+» degli asset anche nel segnale «Confronto Asset» e negli altri usi di `SignalAssetParamControl`. Le fasi 1 e 2, il selettore del benchmark, sono fatte (D370, D371, D378) | richiesta del developer del 02/10, in [`implementation_2/progress/F-L3-rischio-rendimento.md`](./implementation_2/progress/F-L3-rischio-rendimento.md) |
| A2 | **Asset Detail**: la scheda Rischio va riprogettata. Oggi usa ancora il pannello monolitico `RiskAnalysisPanel.svelte`, con TE, IR e `sobol_start_index`, e tiene il banner beta. Con lei torna D54 | D8, D47 |
| A3 | **Simulazione**: resta in beta finché non c'è una guardia sul rapporto fra storia e orizzonte | `TODO_FUTURI.md` § «La simulazione risponde alla finestra, non al portafoglio» |
| A4 | **Percorsi adattivi** della simulazione per i portafogli grandi: oggi, ai valori di default, da 67 posizioni la risposta è «troppo grande», con la cura | D379; il developer l'ha messa dopo la 1.2 (07/10) |
| A5 | **Rendimento totale** con cedole e dividendi: oggi i rendimenti vengono dai soli prezzi | `TODO_FUTURI.md` § «Rischio — rendimento totale con cedole e dividendi» |
| A6 | **Ottimizzazione oltre 100 titoli utilizzabili**: risponde `invalid_parameters` invece di `resource_limit` (`risk_plugins/portfolio_optimization.py`, ramo `except ValueError`); nessun pannello la chiede | [`implementation_2/R5-post-merge-e-review.md`](./implementation_2/R5-post-merge-e-review.md), D381 |
| A7 | **Traduzioni** delle pagine di teoria del rischio: 5 su 22, solo su richiesta esplicita del developer | [`implementation/I-documentazione.md`](./implementation/I-documentazione.md), «terza metà» |

### Domande mai decise

Dalle schede della review del 24/09 ([`implementation_2/R5-tempo2-schede.md`](./implementation_2/R5-tempo2-schede.md),
«Esito delle schede»):

- **C4**: il tasso privo di rischio è sempre 0 su Dashboard e Broker (`levels/RiskLevelsPanel.svelte`). Asset Detail ha
  il suo campo;
- **C5**: la soglia del Sortino è sempre 0;
- **C8**: gli euro del max drawdown dicono «la stessa caduta, oggi»: va scritto così?
- il periodo non è scritto nell'intestazione dei livelli;
- una partenza tardiva non si vede: `baseline_inside_requested_range` e `short_history` non hanno lettori nel frontend;
- la copertura dello shock sotto 1 non segnala i tipi non configurati;
- `fresh_quote_coverage` è pubblicato e nessuno lo legge (debito 6 di [`implementation/STATO.md`](./implementation/STATO.md)).

### Difetti noti

- nel laboratorio, all'apertura ogni sezione chiede due volte: solo L3° aspetta i verdetti di ammissibilità
  (`AssetSetRiskPanel.svelte`; reperto di F al giro 15);
- `risk-contribution.en.md` lascia intendere che le quote negative vengano solo dalle posizioni corte (basta un asset
  di copertura); `max-drawdown.en.md` parla di «portfolio value», mentre il codice usa il TWRR;
- `HurtRow.secondaryLoss` è un campo morto (`levels/levelHelpers.ts`): il VaR si legge come soglia dell'istogramma.

### Buchi veri

Promessi da un piano o da una decisione, mai fatti, e senza una decisione che li abbia cambiati.

| # | cosa | evidenza | peso | proposta |
|---|---|---|---|---|
| B1 | **L'icona della documentazione su tutti i pannelli di tutte le pagine**, con la sua pagina | decisione del developer del 24/09 ([`implementation_2/progress/F-laboratorio-postmerge.md`](./implementation_2/progress/F-laboratorio-postmerge.md), «Correzioni in avanti e decisione del developer sul seguito»; Doc1–Doc3 in [`implementation_2/R5-post-merge-e-review.md`](./implementation_2/R5-post-merge-e-review.md)). Sul rischio c'è; fuori no: dei componenti di `frontend/src/lib/components/dashboard/` solo `KpiSection.svelte` ha un `DocsLink` | medio | l'inventario pagina per pagina (Doc1) e un giro dedicato dopo la 1.2, oppure una decisione che ne restringa la portata |
| B2 | **Le colonne di rischio di Asset Global** (D54: nascoste per default, il max drawdown visibile) e la colonna ρ̄ (F-4) | mai costruite. Il rinvio a `TODO_FUTURI.md` annunciato da F ([`implementation/progress/F-esecuzione.md`](./implementation/progress/F-esecuzione.md), Q-F4) non è mai stato scritto. La fonte dei dati ora c'è (`asset_set_kpi`, `asset_set_drawdown`) | basso-medio | decidere: costruirle con la ripresa di Asset Detail, come dice D54, oppure ritirare D54 |
| B3 | **La fetta per asset del portafoglio** (D58, D59): il backend c'è, nessuna pagina la chiede | filtro per asset su `PortfolioRiskScope` e `sliced_asset_ids` in `backend/app/schemas/risk.py`; nessuno scope `portfolio` con `asset_ids` nel frontend. Così il confronto di una fetta con il suo riferimento, lo scopo di D59, non si può fare, e la rinormalizzazione non è dichiarata da nessuna parte ([`implementation/C-backend-affettamento-portafoglio.md`](./implementation/C-backend-affettamento-portafoglio.md), definizione di finito) | medio | decidere alla ripresa: un selettore della fetta in L3, oppure ritirare la parte di interfaccia di D58 |
| B4 | **Il CHANGELOG 1.2.0 non dice che due numeri della 1.1.0 cambiano**: M2 (VaR e CVaR, nuovo stimatore della coda, sempre verso l'alto) e A9 (il tasso privo di rischio convertito alla frequenza della serie) | D87; il brief di J, §3 ([`implementation/J-chiusura-e-rilascio.md`](./implementation/J-chiusura-e-rilascio.md)); nessuna delle due voci nel capitolo 1.2.0. ⚠️ Le cifre di J valgono in un caso particolare (verifica del 09/10 sul codice di oggi): lo 0,27% del CVaR è a T = 750, e fra 250 e 1500 osservazioni la mediana al 95% è 0,385%; il «0,03–0,13» di A9 vale al 16% di volatilità, mentre al 5% di volatilità, con tasso al 5%, lo Sharpe era gonfiato di 0,30. Il tasso si imposta solo nella scheda Rischio di Asset Detail: laboratorio, Dashboard e Broker lo tengono a 0 | medio | due righe in «🔄 Changed», proposte al coordinatore |
| B5 | **Le pagine di Sharpe e Sortino scrivono il tasso giornaliero con l'esponente `1/365`**; il codice usa `1/f`, la frequenza osservata (A9) | `sharpe-ratio.en.md` e `sortino-ratio.en.md` (e le tre traduzioni) contro `backend/app/services/risk/metrics.py` | basso-medio | docs-writer in inglese, e la stessa correzione nelle tre lingue |
| B6 | **V1 e V2 della lista di A**, dalla review visiva del developer: i badge degli asset e la frase breve nell'avviso unico; il tooltip vero sulle barre dell'istogramma | [`implementation_2/progress/A-dashboard-esecuzione.md`](./implementation_2/progress/A-dashboard-esecuzione.md), tabella del lavoro; `levels/l1/ReturnHistogram.svelte` usa ancora il `title` nativo; `AssetChip.svelte` esiste già | basso | un giro piccolo alla ripresa |

### Rinvii già registrati in [`TODO_FUTURI.md`](../../../../TODO_FUTURI.md)

Tracking Error e Information Ratio · ottimizzazione di portafoglio · Monte Carlo avanzato (GJR-GARCH, livelli 4 e 5) ·
stimatori robusti di covarianza · rivalutare le misure di N contro riskfolio-lib · catalogo scenari dinamico, sostituti
nel replay e RQMC · separatore decimale · avanzamento della simulazione · i 110 `raise ValueError` del motore.

---

---

## Perché questa cartella è stata svuotata

La prima campagna Risk (Luglio 2026) ha prodotto un backend completo e auditato e
**21 documenti di piano**, ma il frontend si è fermato al **26% della catena G6**
(work item 7 di 23). Il rilascio è avvenuto comunque, coprendo le viste incomplete con
un banner beta.

L'analisi del 16 Settembre 2026 ha stabilito che il problema non è la qualità del
backend né la resa grafica, ma **l'assenza di una domanda guida**: i piani rispondevano
a *«quali strumenti di rischio esistono?»* invece che a *«quale decisione deve prendere
l'utente?»*. Senza quella domanda ogni metrica pesa uguale, le implementi tutte, la UI
diventa una lista e l'utente non sa dove guardare.

Il materiale precedente **non è stato cancellato**: è in
[`_archive-backendFirst-G0G6/`](./_archive-backendFirst-G0G6/) e resta la fonte
autoritativa per il **contratto matematico**, le **evidenze di benchmark** e le
**decisioni di architettura backend**, che restano tutte valide.

Ciò che è superato è la **pianificazione frontend** (catena G6) e la **gerarchia di
priorità fra le metriche**.

---

## Ordine di lettura

| # | Documento | Contenuto |
|---|---|---|
| 0 | [`00-analisi-stato-attuale.md`](./00-analisi-stato-attuale.md) | Inventario **verificato sul codice** di cosa esiste davvero, dove, e quanto del piano è stato eseguito. |
| 1 | [`01-tesi-e-quattro-domande.md`](./01-tesi-e-quattro-domande.md) | **La direzione.** Tesi guida, i quattro livelli di domanda, la regola dei pesi. Fonte di ogni decisione successiva. |
| 2 | [`02-verdetti-per-strumento.md`](./02-verdetti-per-strumento.md) | Per ogni strumento: cosa fa, a che domanda risponde, verdetto e destinazione. |
| 3 | [`03-mappa-livelli-pagine.md`](./03-mappa-livelli-pagine.md) | Mappa livelli × pagine, conseguenze architetturali, scomposizione del monolite. |
| 4 | [`04-decisioni-e-questioni-aperte.md`](./04-decisioni-e-questioni-aperte.md) | Registro delle decisioni prese, dei rinvii, e di ciò che resta aperto. **Documento vivo.** |
| 5 | [`05-grammatica-visiva-e-rappresentazioni.md`](./05-grammatica-visiva-e-rappresentazioni.md) | Diagnosi estetica, contratto di primitive, anatomia della card, sei rappresentazioni, dossier heatmap, layout per zona. |
| 6 | [`06-matematica-librerie-e-reimplementazioni.md`](./06-matematica-librerie-e-reimplementazioni.md) | Le due sorgenti matematiche del progetto, confronto a tre vie con NumPy e Riskfolio, distorsione del CVaR, costo dei segnali rolling, setaccio delle 42 funzioni Riskfolio, piano di migrazione M1-M6. |
| 7 | [`07-piano-esecutivo.md`](./07-piano-esecutivo.md) | **L'ordine.** Dodici flussi paralleli, cinque dipendenze, tre cancelli, la taglia in superficie misurata, l'indirizzo dell'oracolo M4, la banda di porte e la voce di CHANGELOG. Non riassume i precedenti: rimanda. |
| 8 | [`implementation/`](./implementation/) | **I mandati.** Undici piani di lavoro assegnabili a sotto-agenti, uno per flusso, con lane, proprietà dei file e contratti. Il [`README`](./implementation/README.md) della cartella è la mappa di coordinamento; [`kickoff/`](./implementation/kickoff/) i prompt di avvio, [`contracts/`](./implementation/contracts/) i contratti K1-K8 e [`progress/`](./implementation/progress/) i piani vivi. |
| 9 | [`implementation_2/`](./implementation_2/) | **Il secondo giro e il giro UI.** Il [`REGISTRO`](./implementation_2/REGISTRO.md) dei mandati, i piani S1–S5, i piani di A e di F in [`progress/`](./implementation_2/progress/), e il journal di Risk, [`R5-post-merge-e-review.md`](./implementation_2/R5-post-merge-e-review.md), che arriva fino alla 1.2. |

---

## Stato dell'avanzamento

| Blocco | Stato |
|---|---|
| Analisi dello stato attuale | ✅ 16 Set 2026 |
| Tesi e quattro domande | ✅ 16 Set 2026 |
| Verdetti per strumento | ✅ 16 Set 2026 |
| Mappa livelli × pagine | ✅ 16 Set 2026 |
| **UI/UX per zona e scelta dei grafici** | ✅ 16 Set 2026 |
| **Matematica, librerie e reimplementazioni** | ✅ 16 Set 2026 |
| **Piano esecutivo** | ✅ 17 Set 2026 |
| **Mandati di implementazione** | ✅ 17 Set 2026 |
| Esecuzione — primo giro, [`implementation/`](./implementation/) | ✅ 18 Set 2026 (J mai creato: lo sostituisce il secondo giro) |
| Esecuzione — secondo giro e giro UI, [`implementation_2/`](./implementation_2/) | ✅ 18 Set – 08 Ott 2026, tutto in `dev_release2` |
| Rilascio | ✅ 1.2.0: fuori dalla beta, salvo la simulazione e la scheda di Asset Detail |
| Seguito | ⏸️ in pausa fino a dopo la 1.2 (D382) |

---

## Vincoli di scopo già fissati

- **Asset Detail è parcheggiato in beta.** Non rientra in questo giro: si riapre a fine
  catena (D47), quando i quattro livelli e la grammatica visiva saranno in piedi, così
  eredita una direzione già decisa. La discussione si concentra su **Dashboard**,
  **Broker Detail** e **Asset Global**.
- *(Superato nei fatti: la famiglia è entrata in `dev_release2` a treni, e la 1.2.0 toglie il banner superficie per
  superficie.)* **Si rilascia solo a catena completa** (D46). Il lavoro vive in un worktree separato
  e non tocca `dev_release2` finché non è pronto; il banner beta si toglie a quel punto,
  in un colpo solo.
- **I segnali rolling restano dove sono** (Overview di Asset Detail). Non vengono
  spostati né duplicati.
- *(Superato dal piano esecutivo del 17/09 e dai giri seguenti: il backend è stato riaperto dai mandati A, migrazione
  matematica, H, Monte Carlo, e N, acquisizioni, poi dai limiti della simulazione, D379, e dall'istogramma, D380 e
  D381.)* **Il backend non viene riaperto** su: contratto matematico, QuantLib MC/QMC, obbligo
  di processo `spawn`, serie canoniche, metadata di qualità del dato.
- **La catena G6 non viene ripresa.** 23 item a catena singola con gate umani bloccanti
  si è dimostrato un modello fragile: un solo stop congela tutto il resto.
- *(Superato come l'altro punto sul backend; le due eccezioni sono diventate i mandati B e C.)* **Il backend non viene
  riaperto**, con due eccezioni decise il 17 Set: il filtro per
  asset su `PortfolioRiskScope` (D58), che oggi sa affettare solo per broker, e
  l'estensione di `AssetType` con i sottotipi (D52). Entrambe servono il confronto con
  il riferimento giusto, che è il perno di L3.

---

## Riferimenti

- Archivio prima campagna: [`_archive-backendFirst-G0G6/`](./_archive-backendFirst-G0G6/)
- Rinvii registrati: [`../../../../TODO_FUTURI.md`](../../../../TODO_FUTURI.md)
