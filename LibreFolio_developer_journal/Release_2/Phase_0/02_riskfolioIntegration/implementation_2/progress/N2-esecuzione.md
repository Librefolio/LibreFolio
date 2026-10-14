# N2 — Un fattore comune fra asset posseduti · esecuzione

> **Brief**: messaggio del coordinatore del 2026-09-18 (round 2, seguito di F1), nato da un
> reperto di S2 sulla heatmap delle correlazioni di L2.
> **Piano d'analisi**: artefatto di sessione, riassunto qui nei passi.
> **Baseline**: `bafa4663b23afe1f92d0388424cb91c21c5e073f` — vedi passo 1.
> **Corsia**: porta **6151** · data dir **`/tmp/librefolio-r2-f1`**. Mai 6150 (server di review).

---

## Il problema in una riga

La heatmap delle correlazioni disegnerebbe **49 celle quasi bianche**: nessuna delle 21
coppie di asset posseduti supera 0,3, perché ogni serie di prezzi del mock è generata con
**rumore indipendente** e il mercato finto **non ha un fattore comune fra le posizioni**.

È il passo 7 di F1 un livello più sotto: là mancava il fattore fra portafoglio e indice
(beta 0,023 → 0,884), qui manca **fra le posizioni**.

## La decisione

**A + B**, autorizzate dal coordinatore. Due asset ricostruiti su diciassette.

| | coppia | ρ ante → post | ricostruisco | tx riprezzate | peso |
|---|---|---|---|---:|---:|
| **A** | RE Loan Milano ~ RE Loan Roma | `+0,1200 → 0,93` | **RE Loan Roma (#5)** | 1 | 8,6 % |
| **B** | Bitcoin ~ Ethereum | `−0,1365 → 0,70` | **Ethereum (#7)** | 6 | 0,75 % |
| ~~C~~ | ~~Apple ~ Microsoft~~ | rifiutata | — | — | — |

**C rifiutata** perché ricostruire uno `STOCK` cambierebbe `equity_factors` → le serie dei
due indici → il beta → la struttura che il vincolo ② dichiara corretta.

Tecnica, la stessa di F1: `ε_dipendente = √ρ · ε_guida + √(1−ρ) · ε_idio`, che dà **ρ
esatto** e **conserva la varianza**.

---

## Passo 1 — Baseline ✅ 2026-09-18

Il kickoff chiedeva di portare l'albero a `7d75a9c6c`. **Non posso**: `checkout`, `reset`,
`merge`, `rebase` sono fuori dalle mie regole. Riportato al coordinatore, che ha **deciso
di non spostare niente** sulla base di questa prova:

```
git merge-base --is-ancestor bafa4663b 7d75a9c6c   →  vero (7 commit indietro, nessuna divergenza)
git diff --name-only bafa4663b 7d75a9c6c -- backend/   →  VUOTO
blob di populate_mock_data.py nei due commit        →  bc01b7397a064816… IDENTICO
```

> **Note implementazione**: `git rev-parse HEAD` →
> `bafa4663b23afe1f92d0388424cb91c21c5e073f`, albero pulito. I 7 commit mancanti sono docs
> del giornale più frontend (`ScatterChart`, `RiskCardGrid`, `_frontend_utility.py`):
> nessuno tocca il perimetro.

> **⚠️ Fuori pista — `api sync` saltato, con ratifica.** Il vincolo di `_comune.md` lo
> impone dopo ogni aggiornamento di baseline. Ma fra i due commit **nessun file di
> `backend/app/` cambia**, quindi il contratto OpenAPI è identico, e questo mandato non
> tocca il frontend. La regola esiste perché `generated.ts` è ignorato da git, **non come
> rito**: verificata assente la condizione che la motiva, la regola non si applica. Il
> coordinatore ha ratificato.

---

## Passo 2 — Misura ANTE ✅ 2026-09-18

**Finestra dichiarata dal prodotto**: `2025-09-24 → 2026-09-18` · **360 osservazioni** ·
frequenza `daily` · `return_basis=price_only` · `composition_as_of 2026-09-18` ·
coverage `0,9677` · escluso `#17` (`missing_price`, per progetto).

Misurato con le **analitiche del prodotto** (`RiskService.execute`, lo stesso punto
d'ingresso del router), non con formule mie. Payload integrale in
`/tmp/librefolio-r2-f1/n2_ante.json`.

| grandezza | valore |
|---|---|
| `cash_weight` | `0,5056920495577144` |
| `portfolio_volatility` | `0,05031302048858704` |
| `diversification_ratio` | `1,9626584002716814` |
| `effective_number_of_assets` | `16,26661924475477` |

| asset | peso | quota di rischio |
|---|---:|---:|
| Apple | 14,8382 % | **72,6886 %** |
| Microsoft | 2,5661 % | 1,9821 % |
| Tesla | 3,1842 % | 3,0592 % |
| RE Loan Milano | 17,2875 % | 2,6043 % |
| RE Loan Roma | 8,5402 % | 1,0740 % |
| Bitcoin | 2,3804 % | **17,8081 %** |
| Ethereum | 0,6343 % | 0,7837 % |

Matrice del prodotto, 21 coppie: **0 sopra 0,9 · 0 sopra 0,3**.
La più forte è **`RE Loan Milano ~ RE Loan Roma = +0,1323`**; poi
`Loan Roma~ETH +0,1026`, `MSFT~Loan Milano −0,0613`, `MSFT~ETH −0,0560`,
`MSFT~Tesla +0,0542`, **`BTC~ETH −0,0541`**.

> **Note implementazione**: `RiskService(db).execute(...)` con
> `scope=portfolio`, `mode=current_composition`,
> `composition_policy=current_buy_and_hold`, `target_currency=EUR`.
> `comparison` richiede un parametro obbligatorio (da fornire al passo 7);
> `historical_kpi` **non supporta** `current_composition` — va in modo `historical`.

> **⚠️ Fuori pista 1 — la mia sonda misurava su una base che il prodotto non usa.**
> `n2_corr.py` interseca in senso **stretto** e ottiene **257** date; il prodotto
> ricampiona a **giornaliero** e ne usa **360**. Ne discendono tre smentite di cose che
> avevo dichiarato io:
>
> | avevo detto | il prodotto dice |
> |---|---|
> | «355 date comuni» (poi corretto a 257) | **360 osservazioni** |
> | «`BTC~ETH −0,1365`, la coppia più forte delle 21» | **`−0,0541`, la sesta** |
> | «prestiti `+0,1200`» | **`+0,1323`** |
>
> 🔑 E il corollario che ribalta una cosa che avevo scritto: dire *«tre corsie, tre
> numeri, nessuno sbagliato»* era **falso**. Il `+0,131` di S2 è **il numero del
> prodotto**; il mio `+0,1200` era il numero della **mia sonda**. Non erano tre campioni
> della stessa grandezza: uno era il prodotto e due erano approssimazioni.
> **L'oracolo giusto — l'analitica `correlation` — esisteva dall'inizio e non l'ho usato
> fino al passo 2.**

> **⚠️ Fuori pista 2 — la mia previsione girava sulla base sbagliata, e l'ho rifatta.**
> Le σ per asset non sono pubblicate, ma sono ricavabili **esattamente** dagli output:
> con `xᵢ = wᵢσᵢ` vale `componentᵢ · σₚ = xᵢ (Cx)ᵢ`, sette equazioni e sette incognite
> con `C` nota. Primo tentativo a punto fisso `x = b/(Cx)`: **divergente**, σ negative e
> `σₚ` a 17 milioni. Sostituito con `least_squares` innescato a `√b`:
> **residuo `6,3·10⁻¹³`**, `σₚ` ricostruita `0,050313020494` contro `0,050313020489`
> pubblicata, DR `1,962658400950` contro `1,962658400272`. Sonda: `n2_forecast2.py`.

### 2.1 Previsione rifatta sulla base del prodotto

| | ANTE | dopo **A** | dopo **A+B** |
|---|---:|---:|---:|
| `portfolio_volatility` | 0,050313 | 0,050807 | **0,052532** (+4,41 %) |
| `diversification_ratio` | 1,962658 | **1,943582** | **1,879763** (−4,22 %) |
| quota rischio Ethereum | 0,7837 % | 0,7686 % | **3,9486 %** (×5,0) |
| quota rischio Apple | 72,69 % | 71,28 % | 66,68 % |

**B pesa ancora 3,5 volte A** (+3,40 % contro +0,98 %): la conclusione qualitativa regge,
i numeri no. E la collisione che avevo segnalato **si stringe**: il DR previsto **dopo A**
è `1,9436`, che arrotonda a **1,94** — la cifra che S2 ha misurato **prima**.

### 2.2 🔴 Reperto grave: `cash_weight` e NEA dipendono **solo dalla data di fine**


Quattro finestre, stessa lane, stesso DB:

| finestra richiesta | analizzata | n_obs | `cash_weight` | **NEA** | DR |
|---|---|---:|---:|---:|---:|
| piena | `2025-09-24 → 2026-09-18` | 360 | `0,5056920495577144` | 16,2666 | 1,9627 |
| fine `oggi−3` | `2025-09-24 → 2026-09-15` | 357 | `0,5088738899828749` | 16,4686 | 1,9857 |
| fine `oggi−30` | `2025-09-24 → 2026-08-19` | 236 | `0,9708535477333845` | 🔴 **1 177,1413** | 1,0000 |
| solo 6 mesi | `2026-03-18 → 2026-09-18` | 185 | `0,5056920495577144` | 16,2666 | 1,9655 |

**La data d'inizio non conta**: la finestra di sei mesi dà `cash_weight` e NEA **byte per
byte identici** a quella piena. Conta **solo `composition_as_of`, cioè la data di fine.**

**Arbitrato chiuso**: il mio `0,5089` di F1 è **riprodotto esattamente**
(`0,5088738899828749`) da una finestra che finisce a `oggi−3`. **Non era stantio: era la
cifra giusta di un'altra data di fine.**

> 🔴 **E la terza riga è un difetto di prodotto, non del mock.** Con una finestra che
> finisce un mese fa, la scheda di concentrazione direbbe
> **«numero efficace di asset: 1 177»** su un portafoglio che a quella data ne teneva
> **uno solo**, con `DR = 1,0000` esatto.
>
> Verificato nel DB, non dedotto: al `2026-08-19` esistono **due sole** transazioni su
> asset, entrambe su **#1 (Apple)** — `BUY 2026-07-30` e `BUY 2026-08-13`. Un asset
> distinto. Le altre 53 cadono in `2026-09`. Quindi `cash_weight = 0,9708535477333845`,
> peso dell'unico titolo `0,0291464522666155`, e
> `1/0,0291464522666155² = 1177,1413` — **la cifra pubblicata, alla cifra**.
>
> È la mia quattordicesima del round 1 — *il nome promette un conteggio che il numero
> non mantiene* — passata da **11,4 su 2 asset** a **1 177 su 1**. Il numero che dovrebbe
> contare gli asset sbaglia di un fattore **1 177**, e la verità è **uno**.
>
> ⚠️ **Correzione a me stesso, nello stesso paragrafo**: avevo scritto «1 177 su 7»
> leggendo la composizione *corrente*. Sette è quello che il portafoglio tiene **oggi**,
> non a quella data. **Il numero di asset è esso stesso funzione della finestra**, e l'ho
> dato per costante — lo stesso errore che la regola di S2 esiste per impedire.
>
> **Non è mio da correggere** (`services/risk/` e la resa sono fuori perimetro):
> riportato al coordinatore.

### 2.3 🔴 Il beta ANTE — e un mio errore di F1

`comparison` richiede `comparison_asset_id` (`comparison.py:35`). Misurato contro
entrambi i benchmark, **stessa finestra dichiarata** `2025-09-24 → 2026-09-18`, 360 oss.,
`status=partial`:

| | `#10` S&P 500 | `#11` MSCI World |
|---|---:|---:|
| `beta` | `0,23456306785050546` | `0,23263371406160005` |
| `correlation` | `0,6678692493115539` | `0,6610549068856425` |
| `tracking_error` | `0,13870633210075872` | `0,13888940494026675` |
| `information_ratio` | `−0,5161879681001313` | `−0,4735114556463348` |

> **⚠️ Fuori pista 3 — il `beta = 0,884` che ho consegnato in F1 non è il beta del
> portafoglio.** Al passo 7 di F1 ho eseguito `ComparisonAnalytic` con una sonda che
> **passava pesi propri** — lo si legge nel referto stesso: `effective_number_of_assets
> = 5,2631578947` con `Σw² = 0,19`, *«coerente coi pesi passati»*. Il prodotto usa la
> composizione **vera**, che è **cassa al 50,57 %** e il cui investito è per metà
> prestiti a beta ~0.
>
> ```
> 0,8842536997 × (1 − 0,5056920496) = 0,4371   ← sola diluizione da cassa
> misurato dal prodotto              = 0,2346   ← il resto è composizione
> ```
>
> **La riparazione di F1 però è reale, e migliore di come l'avevo misurata**: il prodotto
> dà `correlation = 0,6679`, sopra lo `0,5203` che avevo riportato. L'indice *traccia*
> davvero il fattore azionario. **È falsa solo la grandezza del beta**, e la cifra che la
> card mostrerà è **`0,2346`**, non `0,884`.
>
> 🔑 **È lo stesso errore del Fuori pista 1, commesso in un altro mandato**: in F1 ho
> passato pesi miei, in N2 ho usato una base d'intersezione mia. **Due volte ho misurato
> la mia sonda credendo di misurare il prodotto.**

I tre numeri pubblicati sono **mutuamente coerenti**: `σ_b = ρσₚ/β = 0,143256`,
e `ρσₚ/σ_b` restituisce `0,23456306785050546` alla diciassettesima cifra.

**Previsione falsificabile per il POST**: A e B non toccano il legame con l'indice
(prestiti e cripto sono ~0 con esso per progetto), quindi `cov(p,b)` resta ferma mentre
`σₚ` sale del 4,41 %. Attesi: **`beta` invariato a ~`0,2346`**, `correlation`
`0,6679 → ~0,640`. **Se il beta si muove in modo apprezzabile, A o B sono tracimati
sull'indice** — e questo è il controllo del vincolo ② più stringente di un confronto
diretto.

### 2.4 🔴 Tre basi dentro lo stesso prodotto — e due cifre pubblicate che non si riconciliano

| analitica | modo / scope | osservazioni |
|---|---|---:|
| `risk_contribution`, `correlation`, `comparison` | portfolio / `current_composition` | **360** |
| `historical_kpi` | asset / `historical` | **258** |

Volatilità degli indici secondo `historical_kpi`, stessa finestra richiesta:

| asset | piena (`→ 09-18`) | `oggi−3` (`→ 09-15`) |
|---|---:|---:|
| `#10` S&P 500 | `0,17150733864923587` | `0,171909148672705` |
| `#11` MSCI World | `0,17117061138331616` | `0,1714728420163941` |

Questo **arbitra la cifra di S3** (`vol = 0,171146` per l'asset 11): è giusta, ed è sulla
base a **258** osservazioni.

> 🔴 **Ma le due cifre pubblicate non si riconciliano.** `comparison` implica
> `σ_b = 0,143256`; `historical_kpi` pubblica `0,171171`. **Scarto 19,49 %.**
> Chi prendesse le due cifre pubblicate e applicasse l'identità di manuale otterrebbe
> `β = ρσₚ/σ_b = 0,196310` contro il `0,234563` pubblicato, **e concluderebbe che uno dei
> due è sbagliato. Nessuno dei due lo è.**
>
> È la regola nuova del coordinatore — *«verifica che i due numeri escano dallo stesso
> produttore»* — **con il caso più duro possibile: stesso prodotto, stesso asset, stessa
> finestra richiesta, due analitiche registrate, due basi.** E nel payload **non c'è nulla
> che lo dica**: entrambe riportano la stessa `analyzed_range`, e solo `n_observations`
> (360 contro 258) tradisce la differenza.
>
> Fuori perimetro: riportato, non toccato.

## Passo 3 — Iniezione del fattore comune ✅ 2026-09-18

Unica regione toccata: `populate_mock_data.py`, il ciclo principale di generazione.
Un solo passaggio, perché nell'ordine di `price_configs` **ogni guida precede il proprio
dipendente** (`btc` prima di `eth`, `loan1` prima di `loan2`): non serve una seconda
passata.

| dipendente | guida | `c` seminato |
|---|---|---:|
| `#5` RE Loan Roma | `#4` RE Loan Milano | **0,93** |
| `#7` Ethereum | `#6` Bitcoin | **0,70** |

> **Note implementazione**: `u_dep = c·u_guida + √(1−c²)·u_idio`, con `u = variation /
> noise_range ∈ (−1,1)`. La varianza è conservata esattamente
> (`c²/3 + (1−c²)/3 = 1/3`), quindi la volatilità del dipendente non cambia; e
> `corr(u_dep, u_guida) = c` **esattamente**, non `√c`.
>
> Le guide e i cinque asset non coinvolti **mantengono l'espressione originale**
> (`Decimal(str(variation_raw))`), non la forma normalizzata-e-riscalata: `x/a*a` non è
> l'identità in virgola mobile, e una differenza di 1 ULP diventerebbe una stringa
> decimale diversa → un prezzo diverso → un importo di transazione diverso. Il numero di
> estrazioni da `random` per data è invariato (1 `uniform` + 1 `randint`), quindi anche
> i volumi restano identici.

> **⚠️ Fuori pista 4 — due cose che davo per assodate, entrambe false, entrambe mie.**
>
> 1. Il mio appunto diceva che la tecnica `√ρ·ε_guida + √(1−ρ)·ε_idio` era *«già provata
>    in `_populate_benchmark_indices`»*. **Non è quello che quella funzione fa**: fa la
>    **media** dei fattori azionari (`sum(factors)/len(factors)`) più un rumore di
>    tracking. La tecnica «già provata» non esisteva.
> 2. Quella formula **non dà `ρ`**: dà **`√ρ`**, perché qui la guida *è un asset*, non un
>    fattore latente. È la convenzione giusta per **due dipendenti che condividono un
>    fattore**, non per un dipendente che insegue una guida. Con `ρ=0,93` avrei seminato
>    `0,964`.
>
> Stessa famiglia di `MDD_Rel`/`DaR_Rel`: **entrambe conservano la varianza, una sola
> centra il bersaglio.** Trovata rileggendo il sorgente invece del mio riassunto.

### 3.1 Verifica di non-interferenza — per identità, non per somiglianza

Impronta `SUM(close)` a 10 decimali su tutte e nove le serie, prima e dopo:

```
5|RE Loan Roma   1296468.6139366190  ->  1282162.2884598150
7|Ethereum        756510.0164892613  ->   615352.6964701681
```

**Nient'altro.** `1, 2, 3, 4, 6` e **`10, 11` byte per byte identici.**
Il **vincolo ②** è quindi verificato *per identità*: gli indici sono costruiti da
`equity_factors`, alimentato solo dai `STOCK`, che non ho toccato — le correlazioni
indice↔azionario **non possono** essersi mosse.

## Passo 4 — Misura POST ✅ 2026-09-18

**Stessa finestra dichiarata**: `2025-09-24 → 2026-09-18` · 360 oss. ·
`composition_as_of 2026-09-18`.

| coppia | ANTE | POST |
|---|---:|---:|
| `#4` Loan Milano ~ `#5` Loan Roma | `0,1323` | 🎯 **`0,938327`** |
| `#6` Bitcoin ~ `#7` Ethereum | `−0,0541` | **`0,672387`** |
| le altre 19 | < 0,133 | **< 0,073** |

`coppie > 0,9`: **0 → 1** · `coppie > 0,3`: **0 → 2**. Il contrasto del **vincolo ①** è
ottenuto: una coppia sopra la ridondanza, una a gradino intermedio, diciannove piatte.

### 4.1 Il margine sopra 0,90, misurato

Il bersaglio è la ρ **misurata dal prodotto**, non quella seminata. Seminato `c = 0,93`,
il prodotto misura `0,938327`: **il ricampionamento l'ha alzata, non abbassata.**

| fine finestra | analizzata | n | ρ(4,5) | ρ(6,7) |
|---|---|---:|---:|---:|
| oggi | `→ 2026-09-18` | 360 | `0,938327` | `0,672387` |
| oggi−7 | `→ 2026-09-11` | 353 | `0,938200` | `0,675909` |
| oggi−14 | `→ 2026-09-04` | 346 | `0,938492` | `0,675562` |

**Escursione su due settimane: `0,000292`.** Il margine sopra la soglia è `0,0383`,
cioè **131 volte** lo scivolamento misurato di un fortnight. Il timore che *«una coppia a
0,905 oggi sia a 0,89 fra una settimana»* è quantificato e **non si materializza**:
la deriva reale è di `3·10⁻⁴`, non di `1,5·10⁻²`.

### 4.2 Raggio d'azione dichiarato — previsto contro misurato

| grandezza | ANTE | POST | Δ | previsto |
|---|---:|---:|---:|---:|
| `portfolio_volatility` | `0,0503130204885870` | `0,0522601510798225` | **+3,87 %** | +4,41 % |
| `diversification_ratio` | `1,9626584002716814` | `1,8835610755771213` | **−4,03 %** | −4,22 % |
| `effective_number_of_assets` | `16,2666192447547715` | `16,3488064452649269` | +0,51 % | — |
| `cash_weight` | `0,5056920495577144` | `0,5065788033924528` | +0,18 % | — |
| `beta` vs `#11` | `0,23263371406160005` | `0,23246548952784465` | **−0,07 %** | **invariato** ✅ |
| `correlation` vs `#11` | `0,6610549068856425` | `0,6514571539785635` | −1,45 % | — |

Quote di rischio:

| asset | ANTE | POST | previsto |
|---|---:|---:|---:|
| Apple | 72,6886 % | **66,7809 %** | 66,68 % |
| Microsoft | 1,9821 % | 1,8516 % | 1,82 % |
| Tesla | 3,0592 % | 2,7767 % | 2,81 % |
| RE Loan Milano | 2,6043 % | 3,4352 % | 3,29 % |
| RE Loan Roma | 1,0740 % | 1,8580 % | 1,89 % |
| Bitcoin | 17,8081 % | **19,4534 %** | 19,57 % |
| Ethereum | 0,7837 % | **3,8442 %** | 3,95 % |

**Ogni quota di rischio prevista è centrata entro 0,15 punti percentuali.** La previsione
era costruita risolvendo sette σ incognite da un contratto che non le pubblica: il
raffronto la **valida come metodo**, non solo come numero.

Il `beta` invariato è la conferma più stringente del **vincolo ②**: se A o B fossero
tracimati sul legame con l'indice, si sarebbe mosso. Non lo ha fatto.

---

## Passo 5 — Cancelli ✅ 2026-09-18

> **Nota implementazione**: eseguiti nell'ordine obbligato, corsia `6151` /
> `/tmp/librefolio-r2-f1`.

| cancello | comando | esito |
|---|---|---|
| unitari rischio | `dev.py test … services risk-all` | **400 passed** in 41,25 s |
| ripopolamento | `dev.py test … db populate --force --clean` | ok |
| API rischio | `dev.py test … api risk` | **10 passed** in 12,12 s |
| **API intero** | `dev.py test … api all` | **679 passed, 3 skipped**, 0 falliti, 6 m 33 s |
| lint | `ruff check populate_mock_data.py` | All checks passed |
| formato | `black --check populate_mock_data.py` | unchanged |

> **⚠️ Fuori pista — regressione di complessità introdotta da me.** L'iniezione dentro
> il ciclo ha portato `populate_price_history` **oltre** il limite C901 di ruff (10), che
> la funzione già sfiorava. Riparata estraendo `_daily_variation`. **La correzione è
> stata dimostrata a identità**: ripopolato e confrontate le impronte `SUM(close)` a
> dieci decimali su tutte e nove le serie → **zero differenze**. Il rifattore non muove
> un solo prezzo.

> **Perché `api all` e non solo `api risk`.** Il DB finto alimenta molto più della fetta
> rischio, e il mio raggio d'azione passa per il **NAV**: AI Export calcola il proprio
> Herfindahl da `nav_weight_percent`. `api risk` non l'avrebbe guardato. Una `grep` non
> aveva trovato nulla che inchiodasse valori monetari dei due asset toccati, ma **ciò che
> una ricerca non trova non è una garanzia**: il cancello largo lo è.

---

## Passo 6 — L'ipotesi della coda riportata in avanti ❌ **falsificata** 2026-09-18

> **Nota implementazione**: il coordinatore ha sospeso A+B segnalando che su finestre
> recenti la heatmap mostra già `0,96` ovunque, con decadimento monotono all'allungarsi
> della finestra, e ha ipotizzato una **coda riportata in avanti** (prezzi che finiscono
> prima di oggi → rendimenti nulli condivisi → correlazione gonfiata verso 1). Mi ha
> chiesto di inchiodare la causa nel DB, che è l'unica misura che lui non poteva fare.

### 6.1 — Nel DB non c'è nessuna coda

Misurato sul DB ripopolato di fresco, `today = 2026-09-18`:

| asset | punti | ultimo | scarto da oggi | giorni finali piatti | giorni piatti **ovunque** |
|---|---:|---|---:|---:|---:|
| 1, 2, 3, 4, 5 | 267 | `2026-09-18` | **0 g** | **0** | **0** |
| 6, 7 | 373 | `2026-09-18` | **0 g** | **0** | **0** |
| 10, 11 | 267 | `2026-09-18` | **0 g** | **0** | **0** |

**Ogni serie finisce esattamente oggi. Non esiste un solo `close` ripetuto in nessuna
serie.** La condizione che l'ipotesi richiede è assente.

### 6.2 — E il decadimento non si riproduce

Stessa forma di query del coordinatore — `asset_set [1,2,6,7]`, `mode historical`, EUR —
nella mia corsia, con conteggi di osservazioni che coincidono coi suoi:

| finestra | oss. | AAPL~MSFT | AAPL~BTC | BTC~ETH |
|---|---:|---:|---:|---:|
| 1 mese | 32 | **0,0141** *(lui 0,9507)* | **0,2173** *(lui 0,9647)* | 0,5988 *(lui 0,9347)* |
| 3 mesi | 94 | −0,0938 *(lui 0,8551)* | 0,0423 *(lui 0,8841)* | 0,6207 *(lui 0,8505)* |
| 6 mesi | 186 | −0,0768 *(lui 0,7616)* | −0,0255 *(lui 0,7937)* | 0,7155 *(lui 0,7898)* |
| 1 anno | 360 | −0,0388 *(lui 0,6194)* | 0,0145 *(lui 0,6701)* | 0,6724 *(lui 0,6355)* |

**Nessun gonfiamento, nessun decadimento monotono.**

### 6.3 🔑 Il contrasto che vale più della smentita

`BTC~ETH` è **la coppia che ho seminato io** (`c = 0,70`). Guarda le due colonne:

| | 1 mese | 3 mesi | 6 mesi | 1 anno | forma |
|---|---:|---:|---:|---:|---|
| mia, **fattore vero** | 0,5988 | 0,6207 | 0,7155 | 0,6724 | **piatta** |
| sua, **artefatto** | 0,9347 | 0,8505 | 0,7898 | 0,6355 | **decade** |

> **Un fattore comune vero è insensibile alla finestra. Un artefatto di coda decade
> monotonicamente al crescere della finestra, perché la coda pesa meno.** Le due firme
> sono distinguibili a vista, e sono esattamente opposte. Questo non smentisce solo
> l'attribuzione: fornisce **il criterio** per riconoscere il caso la prossima volta.

### 6.4 🔴 L'indizio del backend non è un indizio

`data_quality_degraded / carried_forward` si accende su **tutte e quattro** le mie
finestre — **con zero giorni piatti nel DB**. Non è una spia di staleness: le azioni
hanno 267 punti su 373 giorni di calendario (giorni di borsa), quindi l'allineamento su
griglia giornaliera riporta in avanti i fine settimana **per costruzione**. Si accenderà
su ogni query, per sempre, anche su dati perfettamente sani.

> **Un avviso che si accende sempre non distingue niente.** È la stessa famiglia del
> `check-links` cieco e del file di test non registrato: un segnale che sembra evidenza
> e non lo è.

### 6.5 — Il meccanismo è giusto, l'attribuzione no

Gli zeri condivisi **gonfiano davvero** la correlazione e **decadono davvero** con la
finestra: il ragionamento del coordinatore sul meccanismo regge. Ma la condizione che lo
produce — serie che finiscono presto o bucate — **è esattamente ciò che F1 ha riparato**
(prima di F1 gli asset 4, 5, 17 avevano 0 o 1 punto prezzo). La spiegazione che resta in
piedi è che la sua corsia `6167` stia misurando un DB **anteriore a `bafa4663b`**.

**Previsione falsificabile consegnata**: se ripopola la sua corsia, il decadimento
sparisce e i suoi numeri diventano i miei.

### 6.6 — Ricaduta su F1 e N2

Il coordinatore ha chiesto se i miei numeri fossero inquinati dalla coda. **No**: sono
stati misurati su questo stesso DB, in cui §6.1 prova che non ci sono né buchi né
giorni piatti. La domanda era legittima; la risposta è misurata, non dedotta.

### 6.7 — Tutte le 21 coppie, tutte le finestre

`asset_set [1..7]`, `mode historical`, EUR. Estratto (ordinato per ampiezza massima):

| coppia | 1 mese (32) | 3 mesi (94) | 6 mesi (186) | 1 anno (360) | escursione |
|---|---:|---:|---:|---:|---:|
| **LoanMI~LoanRM** *(seminata)* | **0,9320** | **0,9456** | **0,9371** | **0,9383** | **0,0137** |
| **BTC~ETH** *(seminata)* | 0,5988 | 0,6207 | 0,7155 | 0,6724 | 0,1167 |
| Tesla~BTC | −0,3519 | −0,0231 | −0,0003 | −0,0374 | 0,3516 |
| Apple~MSFT | 0,0141 | −0,0938 | −0,0768 | −0,0388 | 0,1079 |
| *(le altre 17)* | — | — | — | — | ≤ 0,30 |

| | 1 mese | 3 mesi | 6 mesi | 1 anno |
|---|---:|---:|---:|---:|
| coppie **> 0,90** | **1** | **1** | **1** | **1** |
| coppie **> 0,30** | **2** | **2** | **2** | **2** |

> 🔑 **Il contrasto è invariante per finestra.** La coppia seminata attraversa la soglia
> `NEAR_IDENTICAL` di S2 su **tutte e quattro** le finestre, con un'escursione di
> `0,0137`. È la proprietà che un'affermazione *strutturale* deve avere: «questi due sono
> lo stesso prodotto comprato due volte» **non può dipendere dal date picker**. Se
> cambiasse verdetto fra un mese e un anno, la card non starebbe descrivendo il
> portafoglio ma la scelta dell'utente.

### 6.8 — La terza firma: il segno

L'artefatto spinge **in una direzione sola** (verso +1); il rumore campionario **vaga in
entrambe**. Le tre coppie del coordinatore sono tutte fortemente positive su ogni
finestra. Le mie non seminate attraversano lo zero — `Tesla~BTC` va a `−0,3519` su un
mese e a `−0,0374` su un anno. **Rumore simmetrico, non deriva sistematica.**

Le tre firme, insieme, distinguono i due casi senza ambiguità:

| | fattore vero | rumore su finestra corta | artefatto di coda |
|---|---|---|---|
| al crescere della finestra | **piatto** | si smorza verso 0 | **decade monotono** |
| segno | stabile | **attraversa lo zero** | sempre positivo |
| coppie coinvolte | **poche, scelte** | sparse | **tutte insieme** |

---

## Passo 7 — Divergenza fra corsie: causa trovata (dal coordinatore) e conferme mie ✅ 2026-09-18

> **Nota implementazione**: le impronte `SUM(close)` della mia corsia e della sua non
> coincidevano su asset che **non ho seminato** (1, 2, 6). Il coordinatore ha isolato la
> causa: `asset_sources/price_store.py:190-194` **riscrive la riga di oggi** in
> `price_history` quando il prezzo corrente viene aggiornato, e lui aveva aperto la
> pagina asset nella sua corsia per un controllo visivo. `merged_high` viene allargato
> fino a coprire il nuovo `close`, mentre `open`, `low` e `volume` restano del
> generatore.

### 7.1 🔑 La serie ricostruita dal codice, senza DB

Per un asset che non sia guida né dipendente, la serie è **interamente determinata** da
`asset.id`, dall'elenco delle date e da costanti cablate in `price_configs`. Nessun
ingresso variabile, e `_stable_seed` è SHA-256 puro (`:154-157`), esplicitamente immune
alla randomizzazione di `hash()`. L'ho quindi ricostruita **dal codice**:

| asset | punti | primo | ultimo | giorni discordanti (>1e-9) |
|---|---:|---|---|---:|
| 1 Apple | 267 | `171.19242125013744` | `264.56831337973017` | **0** |
| 2 Microsoft | 267 | `365.81268841283907` | `322.03371583405624` | **0** |
| 6 Bitcoin | 373 | `42789.92092982742` | `25889.80757115069` | **0** |

**907 giorni ricostruiti, zero discordanti.**

> **Questo sposta la definizione di «corretto».** Non è più «la corsia di qualcuno»: è
> l'uscita del generatore, riproducibile da chiunque senza DB e senza server. Due corsie
> che litigano non hanno un arbitro; il codice sì.

### 7.2 — Le somme dicono che il giorno diverso è **esattamente uno**

Risolvendo `close_suo = close_mio + Δsomma`:

| asset | Δ somma | close implicito | residuo dall'arrotondamento a 6 cifre |
|---|---:|---:|---:|
| Apple | `70,761687` | **`335,33`** | `3,8·10⁻⁷` |
| Microsoft | `173,056284` | **`495,09`** | `−1,7·10⁻⁷` |
| Bitcoin | `54959,112429` | **`80 848,92`** | `1,5·10⁻⁷` |

**Tutti e tre valori esatti a due decimali.** Se i giorni diversi fossero due o più, il
close implicito non sarebbe un numero pulito: il fatto che lo sia **prova l'unicità del
giorno dalle sole somme**, senza accedere all'altra corsia.

### 7.3 🔴 La contaminazione non è un evento: è uno stato che deriva

I valori che il coordinatore ha letto colonna per colonna (`close 335,650`,
`80 942`) **non coincidono con quelli che le sue stesse somme implicano**
(`335,33`, `80 848,92`): scarto `−0,32` e `−93,08`.

> **Ogni visita alla pagina riscrive di nuovo la riga di oggi.** Impronta e tabella
> vengono da **due momenti diversi della stessa corsia che si muove**.
>
> La conseguenza pratica è la parte che conta: **non si può recuperare una corsia
> contaminata sottraendo lo scarto noto, perché lo scarto non è fisso.** Rimisurare su
> una corsia intatta non è la via più pulita: è l'**unica**.

### 7.4 🔑 Un rilevatore che non richiede una corsia di riferimento

Il generatore produce prezzi con 13-16 cifre significative; il negozio dei prezzi ne
scrive **due decimali esatti**. Quindi:

```sql
SELECT COUNT(*) FROM price_history WHERE close = ROUND(close, 2);
```

Misurato sulla mia corsia: **0 righe su 2 615** (lunghezze da 13 a 16 caratteri).

**Zero falsi positivi su tutto il DB**, e una sola query dice se una corsia è stata
guardata. Non serve né un secondo DB né la memoria di chi ha aperto cosa.

### 7.5 — La quarta firma

Alle tre firme del §6.8 se ne aggiunge una, e il coordinatore ha ragione che serviva:

| | fattore vero | rumore | artefatto di coda | **outlier condiviso** |
|---|---|---|---|---|
| al crescere della finestra | piatto | si smorza | **decade** | **decade** |
| segno | stabile | attraversa zero | positivo | **positivo** |
| coppie coinvolte | poche | sparse | tutte | **tutte** |

> **Le ultime due colonne sono indistinguibili a livello di statistica.** È il motivo per
> cui il §7.4 vale: si separano **sui dati**, non sui numeri derivati.
