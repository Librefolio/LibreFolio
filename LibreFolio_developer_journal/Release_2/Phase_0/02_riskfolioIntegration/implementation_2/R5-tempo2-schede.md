# R5 · tempo ② — schede per la review componente per componente

> Allegato di [`R5-post-merge-e-review.md`](R5-post-merge-e-review.md). Preparate il 23–24/09 in
> attesa del checkpoint del tempo ①, portate nel journal all'apertura del tempo ② (24/09). Sono
> **candidati da provare col developer**, non verdetti: le misure sui dati sono in sola lettura sulla
> copia di prod, le formule citano il codice.


## R12 — la ciambella «per tipo» a due anelli (Allocazione)

**La domanda**: *che tipo di cose possiedo — e dentro gli ETF, che cosa c'è?*

**Mini-lezione**: un ETF è un contenitore. Un «ETF azionario» contiene azioni, un «ETF
obbligazionario» obbligazioni. Il modello salva il sottotipo (`ETF_STOCK`, `ETF_BOND`, …) e il
principio scritto nel docstring è che *il sottotipo risponde a «quale tipo base contiene»*. Quindi
nella torta il sottotipo deve stare **dentro la famiglia del tipo base**: il tuo ETF azionario è
una parte della fetta *Azione*, non una categoria a sé.

**Come è costruita**
- anello base, a tutto spessore: una fetta per famiglia (tipo base), peso = **somma dei membri**
- banda esterna sovrapposta: i membri, **solo** dove la famiglia ha sottotipi; altrove trasparente
- gli archi combaciano per costruzione — misurato Δ 0.0000° su tutte e cinque le tue famiglie
- percentuali sul valore totale **alla data finale** del periodo; «Liquidità» è una famiglia a sé
- codice: `charts/AllocationPieChart.svelte` (`mode='type'`) + `charts/allocationRings.ts`;
  colori D71 da `charts/allocationHierarchy.ts`; roll-up `primaryAssetType` in `utils/assetTypes.ts`

**Numeri che conosci** (payload della copia, 23/09): ETF 49,79 % · Crowdfunding 30,55 % ·
Obbligazioni 16,13 % · **ETF azionario ≈ 3,5 % ≈ ≈ X €** · Liquidità 0,01 %.
Il tuo ETF azionario vale davvero circa ≈ X €? È il controllo più diretto.

⚠️ **Da riguardare dal vivo**: nelle mie letture del 23/09 il payload diceva `3.53` e il tooltip
`3.52%`. Il tooltip mostra il valore del backend arrotondato a due decimali
(`weightOf: (item) => item.value` → `roundedPercent`), quindi non dovrebbero divergere; ma le due
letture erano in momenti diversi e sulla copia gira lo scheduler dei prezzi. **Probabile** un
aggiornamento fra le due, **non dimostrato**: lo rileggiamo payload e tooltip nello stesso istante.

**Scelte estetiche da giudicare — solo tu puoi, un canvas non si asserisce**

| # | cosa guardare | perché è una scelta |
|---|---|---|
| R12a | niente spazio di 1° fra le fette in modalità anelli | `padAngle` toglie un grado **per arco**; i due anelli hanno archi diversi → con lo spazio scivolerebbero |
| R12b | legenda non cliccabile in modalità anelli | spegnere una voce toglierebbe un arco da un anello solo |
| R12c | famiglia piccola (3,5 %): una sola icona visibile | `hideOverlap` toglie quella della banda interna |
| R12d | tooltip: membro `3.52%`, famiglia `Azione 3.5%` | due arrotondamenti diversi sulla stessa riga |
| R12e | 8 dei tuoi 15 asset sono `ETF` generico | **dato, non codice**: più ne classifichi, più il secondo anello racconta |
| R12f | la stessa famiglia ha lo stesso colore qui e nel grafico storico? | D71 assegna il colore per rango: la torta ordina per peso **di oggi**, lo storico per peso **medio del periodo** (`AllocationHistoryChart.svelte`, `weight: dataset.avgWeights[name]`) → se i ranghi differiscono, i colori differiscono |

**Cosa sarebbe un difetto**: un arco esterno che sborda dalla sua famiglia · un sottotipo con lo
stesso colore della famiglia · una famiglia senza sottotipi spezzata in due · passando da anelli a
torta piatta (filtro broker) una serie fantasma che resta a schermo.

**Owner**: anelli → **Risk** · gerarchia colori e grafico storico → **I** · roll-up e icone → **K**.

---

## Tre fatti che valgono per tutte le schede — misurati sui tuoi dati il 23/09

Letti in sola lettura sulla copia (resta byte-identica alla snapshot), solo conteggi.

| tipo | asset | quotazioni | per giorno di calendario | nel weekend | ultimi 365 gg: passi piatti |
|---|---|---|---|---|---|
| ETF (justETF) | 8 | 43 300 | 1,0 | 28,6 % ≈ 2/7 | 31 % — ma **3,6 %** nei feriali |
| ETF_STOCK · ETF_BOND (justETF) | 1 + 1 | ~3 600 | 1,0 | sì | ~33 % — **6 %** nei feriali |
| BOND (Borsa Italiana) | 1 | 399 | 0,69 | **no** | 3 % |
| **CROWDFUND** | **4** | **0** | — | — | — |

**F1 — la griglia dei dati.** La serie del **portafoglio** (TWRR) ha un punto per ogni giorno di
calendario, weekend compresi, a rendimento ≈ 0 (`portfolio_engine.py`, `current += timedelta(days=1)`).
Le serie degli **asset** (`series_preparation.py:236-289`) usano l'**unione** delle date in cui
*almeno un* asset ha una quotazione fresca, e tengono quelle in cui *tutti* hanno un valore, anche
riportato in avanti **senza limite di età**. justETF scrive sabato e domenica con la chiusura del
venerdì, e quelle righe contano come **fresche**. → **Sui tuoi dati anche le serie degli asset
sono di calendario, f ≈ 365.** Un giorno è un giorno di calendario ovunque.
⚠️ *Il 23/09 avevo scritto il contrario, «col BOND dentro, l'intersezione è fatta di giorni di
borsa»: l'avevo preso da una frase della doc (`observed-annualization.en.md:94-95`) senza leggere il
codice. Corretto alle 17:4x, dopo il reperto del docs-writer di F sul riporto in avanti.*

**F2 — il crowdfunding (≈ 30,5 %) non ha una serie di prezzi.** Cosa succede dipende dal
perimetro:
- **perimetri pesati** (portafoglio, fetta, Broker Detail): gli asset senza serie vengono
  **esclusi** e il loro peso diventa liquidità, `usable_cash_weight = 1 − Σ pesi utilizzabili`
  (`risk/service.py:608-687`, avviso `assets_excluded`). **Per il motore del rischio un terzo del
  tuo portafoglio è contante fermo: rischio zero, rendimento zero.** Nel TWRR di L1 entra
  probabilmente al valore implicito delle transazioni, piatto — *da confermare dal vivo*;
- **Asset Global** (`asset_set`, senza pesi): l'asset viene **escluso e basta**, non diventa
  liquidità (`missing_price`). Misurato da A sulla copia: `[1,3,8]` e `[1,3,8,12]` danno entrambi
  574 osservazioni, quindi l'esclusione non accorcia nemmeno la finestra congiunta.

**F3 — i dati degli ETF sono sani**: i passi piatti sono i weekend scritti con la chiusura del
venerdì, non prezzi vecchi.

**F4 — cosa distorcono davvero gli zeri del weekend** (misurato il 24/09 su 3 tuoi asset justETF,
730 giorni, calcolati come fa il motore; griglia di calendario ÷ griglia di borsa):

| grandezza | rapporto | lettura |
|---|---|---|
| volatilità annualizzata | **1,00 · 1,00 · 1,00** | gli zeri diluiscono la varianza di ~252/365, il fattore osservato f ≈ 365 la rimoltiplica: **nessuna distorsione** (per la stessa aritmetica Sharpe e Sortino — non misurati) |
| VaR/CVaR «giornata storta» | **0,87 – 0,92** | sottostimata dell'8–13 % |
| VaR/CVaR «mese storto» (21 oss.) | **0,81 – 0,91** | sottostimato del 9–19 %: sono 3 settimane, con 2/7 di zeri |

→ il difetto sta **solo nei quantili per osservazione**, non nelle grandezze annualizzate.

**F5 — altri tre reperti sulla qualità del dato** (docs-writer di A; 1 e 2 verificati dal coordinator):
- 🔴 **la baseline conta fra i punti riportati**: in `series_preparation.py:311-313`
  `carried_price_points` non ha la guardia `index > 0` che ha `fresh_quote_points` (`:318`). Un
  intervallo che parte di lunedì, con un asset senza righe nel weekend (il tuo BOND), ha la baseline
  di domenica riportata → `CARRIED_FORWARD` → **ogni sezione `partial`**, anche se tutti gli asset
  fossero quotati negli stessi giorni. Una riga, col suo test. **È il caso comune, non un caso limite** (misura di F, 24/09): le serie si caricano da `inizio − 1 giorno` (`service.py:514-517`), quindi con storia precedente la baseline è **sempre** il giorno prima dell'inizio. Basta un asset non quotato quel giorno (ogni inizio di domenica o lunedì per un titolo dei soli feriali, ogni festivo) e l'esito è `partial`. Sui tuoi dati: il BTP da solo, con un inizio di lunedì, esce `partial` solo per questo.
- 🟡 **una partenza tardiva non si vede**: `baseline_inside_requested_range` e `short_history:<id>` non
  hanno consumatori nel frontend (solo una fixture di test). Oggi lo tradisce solo la copertura.
- 🟢 **il cambio sui giorni riportati**: un prezzo riportato è convertito al cambio del suo giorno
  (`price_query.py:403-407`), quindi per un asset in altra valuta il «rendimento» di un giorno
  riportato è la variazione del cambio. **Sui tuoi dati non conta**: i tuoi 15 asset sono tutti in EUR.

---

## Dashboard — i tuoi dati, in €

Legenda: 🔴🟠🟡 = **candidati da provare insieme**, non verdetti · ✅ = verificato nel codice.

### 0 · Intestazione (`RiskPanelHeader`)
**Domanda**: *su cosa sto guardando il rischio?* Titolo, perimetro, banner di qualità del dato.
- 🟡 il periodo arriva come prop ma **non viene scritto** nell'intestazione: lo si legge solo dal
  selettore date della pagina → basta, o va ripetuto qui?
- dal vivo: il banner nomina il crowdfunding escluso (F2)? Se no, è la prima cosa da aggiungere.

### 1a · L1 «giornata storta / mese storto» — VaR e CVaR storici
**Mini-lezione**: il **VaR 95 %** è la perdita che nel passato è stata superata solo nel 5 % dei
giorni peggiori. Il **CVaR** (o Expected Shortfall) è la *media* di quel 5 % peggiore: risponde a
*«quando va male davvero, quanto male in media?»*. È più onesto del VaR, che guarda solo la soglia.
✅ la card mette il CVaR in evidenza e il VaR come secondo numero solo se diverso (`levelHelpers.ts:344-359`).
- ✅ storico puro: perdite ordinate, lettura alla posizione della confidenza (`metrics.py:790-807`),
  95 %, minimo 20 osservazioni; perdite positive con pavimento a zero.
- ✅ «21 giorni» = rendimenti composti su **21 osservazioni** consecutive sovrapposte, niente √t
  (`metrics.py:731-741`).
- 🟠 **C3 — «mese storto» = 3 settimane, e la «giornata storta» conta i weekend**: 21
  osservazioni sulla griglia di calendario (F1) = **21 giorni di calendario ≈ 3 settimane**: sul
  portafoglio, sulle fette, su Asset Global con gli ETF di justETF. **Un'eccezione sui tuoi dati**
  (misurata dal coordinator): il **BOND da solo** — Asset Detail dell'asset 8, o un insieme `{8}` —
  gira sui suoi giorni di borsa, dove 21 osservazioni ≈ un mese. Basta però un benchmark justETF
  nella stessa richiesta (gli asset di confronto entrano nell'insieme preparato, `service.py:170-171`)
  per spostarlo sulla griglia di calendario, e il risultato diventa `partial`. Stesso nome, due durate.
  E la «giornata storta» conta anche sabati e domeniche a perdita zero (~29 % dei giorni): il 5 % peggiore dei
  giorni di calendario è circa il 7 % peggiore dei giorni di borsa → **sottostima la giornata storta**.
  Decisione **separata da C2** nel codice, ma **la stessa domanda di unità**: `horizon_days` conta
  osservazioni o giorni? Sul **portafoglio** il TWRR ha sempre un punto per giorno di calendario
  (`service.py:932-941`) → 3 settimane **per costruzione, per ogni utente, qualunque fornitore**:
  non basta sistemare i weekend di justETF, che aggiusterebbe solo gli insiemi di asset (nota del
  coordinator). Una correzione valida per ogni griglia: il mese = **30 giorni di calendario
  convertiti con f** (≈ 21 osservazioni sulla griglia di borsa, ≈ 30 su quella di calendario).
  ⚠️ Il costante va cambiato **insieme** alla semantica: reinterpretare come giorni il 21 di oggi
  darebbe ad A circa 15 osservazioni, peggio di adesso.
- numeri che conosci: ricordi un giorno o un mese brutto del tuo portafoglio? È il confronto più
  diretto con la card.

### 1b · L1 «peggior discesa» e drawdown corrente
**Mini-lezione**: il **max drawdown** è la caduta più profonda da un massimo al minimo successivo.
Il «recupero richiesto» è asimmetrico: dopo −20 % serve +25 %.
- ✅ calcolato sull'indice TWRR, **non** sul valore del portafoglio: versamenti e prelievi non
  creano finte cadute. Scelta giusta — ma la pagina di teoria dice «portfolio value» → debito doc.
- ✅ durata in giorni di calendario; il drawdown corrente si nasconde quando sei al massimo.
- 🟡 **C8 — gli euro**: `valore di oggi × frazione` (`L1HowMuchItHurts.svelte:88`). Per il VaR è la
  lettura giusta («domani, su quello che hai oggi»); per il max drawdown è un'ipotesi («la stessa
  caduta, oggi») e va detta così. Nascosti col filtro broker attivo. Da rileggere **dopo il fix
  privacy di J**.

### 1c · L1 grafico «sott'acqua» + Ulcer · istogramma dei rendimenti
- ✅ Ulcer = √(media dei drawdown²) sul numero di rendimenti (`acquired.py:146-166`); coincide con la doc.
- ✅ istogramma sul VaR a 1 giorno, bin di Freedman–Diaconis, un bordo **esattamente** sul VaR.
- dal vivo: aspettati una **colonna alta sullo zero** — sono i weekend (F1). Se c'è, è la prova
  visiva di C3.

### 2a · L2 card di diversificazione
**Mini-lezione**: gli **asset effettivi** (1/Σw², inverso dell'indice di Herfindahl) dicono «quanti
asset di peso uguale varrebbe la tua concentrazione». Il **rapporto di diversificazione** (Σwᵢσᵢ/σₚ)
dice quanto rischio la correlazione ti toglie rispetto a sommare i rischi.
- ✅ nessuna card di «correlazione media»: esistono asset effettivi, rapporto di diversificazione, **scoperto**.
- 🟠 **C9 — gli asset effettivi gonfiati dal crowdfunding**: i pesi non vengono rinormalizzati e la
  liquidità resta al denominatore, per scelta dichiarata (`risk_contribution.py:73-76`,
  `concentration.en.md:86-89`: N_eff = n/s², con s = parte investita). Con F2 hai s ≈ 0,7 → **N_eff
  circa raddoppiato**. È coerente con la teoria scritta, ma su di te dice «sei diversificato il
  doppio» per una ragione — un terzo non quotato — che è l'opposto di una diversificazione.
- ✅ la card «scoperto» mostra `cash_weight`: dal vivo deve leggere ≈ 30,5 %. È la prova di F2.

### 2b · L2 contributo al rischio
**Mini-lezione**: il **PCTR** dice *quale fetta del rischio totale viene da ciascun asset*. Un asset
con peso 10 % può portare il 25 % del rischio. Le quote sommano a 100 % per costruzione (Eulero),
non per aggiustamento; una quota **negativa** vuol dire «questo asset calma il resto».
- ✅ covarianza campionaria senza shrinkage, su un calendario comune, pesi di oggi (`metrics.py:506-626`).
- 🟡 la doc lascia intendere che le quote negative vengano solo dalle posizioni corte; i test mostrano
  che basta un asset di copertura → debito doc.
- sui tuoi dati: il crowdfunding **non comparirà** fra le righe (F2).

### 2c · L2 heatmap di correlazione + coppie — **fix di F**
- ✅ Pearson su **una finestra congiunta** per tutti; ordinamento per somiglianza (cluster su 1−|ρ|).
- 🟡 le soglie 0,9 / 0,7 / 0,3 non sono documentate da nessuna parte.
- 🔄 **cambiata da F in questo round, e cambia anche qui**: «By name» ora ordina davvero per nome
  (prima per id), colori della lista delle coppie allineati alla heatmap. La **polarità dei colori**
  è una tua scelta (F-3 di F): invertirla è una riga nel `visualMap` e sposta anche la Dashboard.
- 🔎 **reperti del docs-writer di F sul motore** (eseguendo il vero `RiskService.execute`; da
  verificare insieme):
  - prezzi e cambi **riportati in avanti senza limite di età** — confermato nel codice
    (`backward_fill_info`). Misurato dal coordinator: su `[1,3,8]` i **176 punti riportati** del
    BOND rendono il risultato `partial` (`CARRIED_FORWARD` → `PARTIAL`, `service.py:803`); `[1,2,3,4]`,
    tutti justETF, esce `ok`. Le 14 448 righe di weekend di justETF sono al 100 % uguali al venerdì
    e arrivano **dalla fonte** (`justetf.py:373-387`, `backward_fill_info=None`), non da un nostro riempimento;
  - 🔎 **caso di prova già pronto sui tuoi dati**: l'avviso `low_pair_coverage` confronta la
    copertura **della cella** (osservazioni / osservazioni della griglia densa, `metrics.py:583`,
    `correlation.py:64-75`), che vale 1,0 per costruzione → non scatta mai (il reperto di F regge). Ma
    la copertura **pubblicata** sul risultato è `calendar_coverage` (`correlation.py:133`): su
    `[1,3,8]` dal 2024-01-01 vale **574/995 = 0,577**, sotto il `min_coverage` di default (0,6). Ogni
    cella dice 1,0 e nessun avviso scatta. *(La mia ipotesi della «partenza tardiva» riguardava
    l'altra copertura: sbagliavo bersaglio.)*
  - la soglia del plugin (`min_observations = 2`) non si applica: agisce solo il parametro (20);
  - `data-quality.en.md` §Alignment dice che un calendario accorciato dà `partial`; per un asset che
    parte tardi l'esito è `ok` con `short_history` → debito doc;
  - 🟡 **testo mio da correggere**: `en.json:3228` (e le altre tre lingue) dice *«Some correlation
    pairs…»* per una condizione che riguarda **tutte** le celle.

### 3a · L3 benchmark
- ✅ uno solo, in `localStorage` per utente: uguale su Dashboard e Broker Detail, ma **per browser**.
- 🟡 **C6 — il flag `is_benchmark` non serve qui**: lo marchi nel modale dell'asset, il selettore dei
  segnali lo usa come sezione (`SignalAssetParamControl.svelte:38`), il selettore del rischio no.

### 3b · L3 Sortino · Sharpe · σ · β
**Mini-lezione**: lo **Sharpe** è il rendimento in eccesso per unità di volatilità; il **Sortino**
fa lo stesso ma penalizza solo le oscillazioni verso il basso — per un risparmiatore è quello giusto,
e infatti è mostrato per primo. Il **β** dice quanto ti muovi quando si muove il benchmark.
- ✅ annualizzazione **osservata** f = N·365/D, non 252 fisso; σ con ddof=1; rendimento atteso aritmetico.
- ✅ perimetro: preferisce il **backtest della composizione di oggi**, ripiega sul TWRR reale; la
  card dice quale ha usato.
- 🟡 **C4 — tasso privo di rischio sempre 0** su Dashboard e Broker (`RiskLevelsPanel.svelte:67`, mai
  scritto): con tassi positivi lo Sharpe è ottimista. Serve un tasso? E da dove?
- 🟡 **C5** — il Sortino usa sempre soglia 0 anche se un giorno avrai un tasso; le pagine di teoria
  scrivono l'esponente 1/365 mentre il codice usa 1/f (il codice spiega perché è giusto) → debito doc.
- sui tuoi dati: σ e rendimenti sono quelli del **70 % quotato diluito dal 30 % fermo** (F2).

### 3c · L3 grafico rischio/rendimento
- ✅ x = volatilità annua, y = rendimento atteso annuo; punti: portafoglio, ogni asset (dimensione =
  peso reale), benchmark; **niente contante**, con una nota. Linea del mercato dei capitali da (0, r_f)
  attraverso il portafoglio — con C4 parte dall'origine.

### 4a · L4 replay storico + tornado
**Mini-lezione**: *«se il tuo portafoglio di oggi fosse stato fermo durante il Covid, la crisi del
2008 o il 2022, come sarebbe andato?»* È un backtest, non un ricordo.
- ✅ tre crisi più un periodo libero; buy-and-hold senza ribilanciamento; esclusi = liquidità a 0 %.
- ✅ un asset senza dati nella finestra **ferma tutto** e propone «escludi e riprova» (`stress.py:456`).
  🔴 **sui tuoi dati succederà sempre**: i 4 crowdfunding non hanno serie → escludendoli, il 30 %
  viene riprodotto come contante che nella crisi **non perde nulla**. Da guardare insieme: il testo
  lo dice chiaramente?
- 🟠 **il testo promette ciò che l'interfaccia non ha** (reperto 3 di A): `replayNeedsChoice` dice
  *«Leave it out, or give it a stand-in»*, ma `L4Replay.svelte:101` manda `proxyAssets: []` fisso e
  c'è solo il bottone di esclusione. **Decisione tua**: togliere la promessa, o costruire la scelta
  del sostituto (per esempio un ETF obbligazionario al posto del crowdfunding — che è un'opinione,
  come dice il testo stesso).
- 🔴 già pianificato, non tuo da decidere: su Asset Global e Asset Detail un replay può finire **muto**
  (il polling dei prezzi ogni 30 s invalida la risposta in volo). **Non** su Dashboard e Broker.
- ✅ la segnalazione «% ed € della stessa barra misurano cose diverse» **non regge**, verificato nel
  codice: `_amount(valore, r) = valore × r` (`stress.py`) e `wᵢ = valoreᵢ / valore del perimetro` sugli
  stessi valori (`service.py:401-413`) → € = contributoᵢ × valore del perimetro. In buy-and-hold
  inoltre Σ wᵢRᵢ è esattamente il totale. Stessa grandezza, due unità: basta un numero dal vivo.

### 4b · L4 shock ipotetico
- ✅ ogni asset in un secchio per tipo al 100 %; shock lineare sui pesi; `equity_crash` e
  `global_risk_off` coprono tutti i tipi, sottotipi ETF allineati al contenuto.
- ✅ i tuoi numeri, `equity_crash`: ETF −25 % · azioni −35 % · obbligazioni −2 % · **crowdfunding −10 %**.
  Qui il crowdfunding **c'è** (lo shock usa il tipo, non la serie dei prezzi).
- 🟡 la copertura sotto 1 non segnala i tipi non configurati (il commento del frontend dice il
  contrario): oggi innocuo sui preset, conta per lo shock scritto a mano.

### 4c · L4 simulazione Monte Carlo + provenienza + incertezza della deriva
**Mini-lezione**: non prevede il futuro. Ricampiona **blocchi di giorni veri** del passato (modo di
default) e li ricuce in migliaia di futuri possibili; il cono mostra dove cade il 90 % di quei futuri.
Il GBM è l'alternativa «da manuale», più liscia, che sottostima le code.
- ✅ bootstrap a blocchi (lunghezza ≈ ∛n), regimi dichiarati (calmo ×0,7 · crisi prolungata ×2,5 per
  426 gg · shock e recupero −35 % in 61 gg), 8 192 percorsi, seme fisso; contante a 0 %.
- ✅ **nessuna guardia** sull'orizzonte lungo rispetto alla finestra (il difetto già annotato).
- 🟡 **C2 — orizzonte del bootstrap in osservazioni, non in giorni: latente, non sui tuoi dati.**
  Il motore estrae `horizon_days` osservazioni (`simulation.py:403`, `resampling.py:141-176`) senza
  convertirle, e il cono le disegna su giorni di calendario; il GBM invece converte (`horizon/365`
  anni). Sulla tua griglia di calendario (f ≈ 365, F1) 365 passi ≈ un anno: **nessun effetto**.
  Morderebbe su un perimetro in cui nessun asset scrive i weekend (f ≈ 252: «365 giorni» ≈ 17 mesi
  di mercato). Compare solo dove la simulazione è offerta (portafoglio e Broker, non Asset Global).
- 🔑 **se si corregge C2, la correzione resta dentro `simulation.py`** (passi = horizon × f / 365).
  I due VaR usano `horizon_days` come **conteggio di osservazioni**, per intento dichiarato
  (`asset_set_var.py:83`, `historical_var.py`; suffisso «days» nell'interfaccia): ridefinirlo
  ovunque cambierebbe anche il «mese storto» di A e del portafoglio (C3, decisione separata).
- 🟡 la pagina di teoria descrive **solo il GBM**; bootstrap, regimi e incertezza della deriva non
  hanno una pagina → debito doc (docs-writer).
- sui tuoi dati: il 30 % di crowdfunding simulato come contante fermo (F2) **restringe il cono**.

---

## Riepilogo dei candidati

| # | sev | cosa | dove si prova | owner |
|---|---|---|---|---|
| F2 | 🔴 | crowdfunding = contante nei perimetri pesati (su Asset Global: solo escluso) | card «scoperto» ≈ 30,5 % · banner · replay | Risk (presentazione) · tu (modello) |
| F5.1 | 🔴 | la baseline conta fra i punti riportati → sezioni `partial` senza ragione | intervallo che parte di lunedì col BOND dentro | Risk (una riga + test) |
| C2 | 🟡 | orizzonte del bootstrap in osservazioni — **latente**, non sui tuoi dati (f ≈ 365); fix solo in `simulation.py` | perimetro senza quotazioni nel weekend | Risk |
| C3 | 🟠 | «mese storto» = 3 settimane (ovunque sui tuoi dati) · «giornata storta» diluita dai weekend — **misurato: −8/−13 % al giorno, −9/−19 % al mese; la volatilità no (1,00)** | colonna sullo zero nell'istogramma | Risk |
| C9 | 🟠 | asset effettivi raddoppiati dal contante | card L2 | Risk · tu (definizione) |
| C4 | 🟡 | tasso privo di rischio fisso a 0 | Sharpe · linea del mercato | Risk · tu |
| C6 | 🟡 | selettore benchmark ignora `is_benchmark` | L3 | Risk |
| C5 · C8 · doc | 🟡 | soglia Sortino, euro del drawdown, sei debiti di documentazione | — | Risk · docs-writer |

---

## Broker Detail — stesso componente, verifica di perimetro

*(da compilare)*

## Asset Global — in %

*(da compilare; i fix sono di A/F)*

---

## Test delle palette (D71) — la garanzia regge per coincidenza

Reperto 🟡 di **I** (24/09), file della famiglia Risk (`420b90ebd`, 18/09).

- `colors.test.ts`, `allocationHierarchy.test.ts` — e anche il mio `allocationRings.test.ts` —
  dichiarano di misurare le palette «reali», ma controllano **una propria copia**: nessuno legge il
  `.svelte`. Se qualcuno cambia `PALETTE_*` in un componente, i test restano verdi.
- Oggi le 8 copie coincidono coi sorgenti (14 colori ciascuna): **nessun difetto adesso**.
- Puntatori per numero di riga ormai sbagliati (`AllocationHistoryChart … line 124/125`, oggi 153/154).
- **Cura proposta** (modello `chartCoreHelpers.test.ts:632`): leggere il sorgente con
  `new URL('…svelte', import.meta.url)`, estrarre `const PALETTE_*` e confrontarlo con la copia; citare
  le costanti per nome, non per riga. La palette storica sta nel file di I: il test la legge soltanto.
- **Da decidere col developer**: è un test **fuori** dalla lista approvata per R12 → serve il suo sì.
