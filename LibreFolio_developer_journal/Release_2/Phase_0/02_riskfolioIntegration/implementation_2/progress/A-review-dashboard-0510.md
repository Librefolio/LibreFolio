# Review della Dashboard sui dati veri — 05/10 (6163)

> **Per il developer.** Server su **http://127.0.0.1:6163** (solo da questo Mac), copia del nuovo snapshot del coordinator
> (prezzi fino al 02/10). Entri con le tue credenziali.
> **Fuori da questa review**: il lab (Asset Global), che avrà una review breve a parte; la didascalia di L2, ancora in
> lavorazione (i test rossi sono scritti, il codice no).
> A fine review cancello la copia e i log (lo snapshot resta del coordinator).

---

## 1. Il lavoro di A dal 30/09 — Dashboard → **Rischio** (vale anche sulla pagina di un broker)

1. **Il selettore del benchmark** (livello 3, «Sto venendo pagato per questo rischio?», in alto nel livello).
   - La lista contiene **anche gli asset che possiedi**.
   - Al caricamento della pagina mostra **il benchmark salvato**, mai vuoto se uno è scelto.
   - Scegline uno: il confronto parte subito. Apri un broker: trovi la **stessa** scelta.
2. **Le quote sotto l'1 %**: uno o due decimali, mai «0 %».
   - Dove: livello 2 (peso e contributo di ogni riga, scheda «Quanto di me non è misurato qui?», riga sotto le schede) e
     le frasi sotto lo scatter del livello 3.
   - Si vede solo se hai un asset o una quota sotto l'1 %.
3. **La frase sotto lo scatter** (livello 3) separa liquidità e posizioni senza prezzo. Ciascuna delle due frasi compare
   solo se la sua parte c'è.
4. **Le icone del manuale**: un libro accanto al titolo di ogni livello L1–L4 (su L4, che si chiude, accanto
   all'interruttore). In L1, le tre «ⓘ» delle misure di coda portano ciascuna alla sua pagina.
5. **L'avviso in cima** (visto il 30/09, qui con tutto il resto): blu per i progetti di crowdfunding; prima la causa, poi le
   misure interessate raggruppate sotto la domanda del loro livello, compresi Sortino/Sharpe e lo scatter della
   composizione attuale.

---

## 2. F3 — il blocco del replay storico (punti di Risk, com'erano)

> Dashboard → Risk → L4 «What if…» → Historical replay; also on a broker page.

- Period: a single range picker, without quick presets; the old two single pickers are gone. The crisis menu opens
  upwards when the block sits low on the page.
- Run on a catalogue crisis (e.g. the 2008 crisis or COVID-19) on the real portfolio. Assets born after the crisis are
  left out, and the block under the bars says so:
  - a header «Fuori dal replay: N asset; il X% del valore conta come liquidità a rendimento zero»;
  - the excluded assets grouped by reason (no prices in the period, first quoted after the period began, no recent
    price at the start or at the end, no exchange rate), each asset with its share of the value.
- When more than half of the value is left out, a strong warning stands **above** the total.
- When the period's edges caused the exclusions, a button appears: «Rigioca il periodo {inizio} – {fine}: tornano N
  asset». **One click** sets the dates and replays. With a catalogue crisis chosen, a note «Solo una parte della crisi.»
  sits beside it.
- Type a prehistoric start (e.g. 1019): the block shows «Niente da rigiocare» with the reasons and, if there is one,
  the common-period button.
- L4's amber list of reasons no longer repeats the exclusion sentences. It keeps only the status line («Replay
  storico: Parziale»).
- **Questions for the developer**:
  - are the header and the reasons clear, and is the weight readable;
  - is the block well placed under the bars;
  - is the button's wording right;
  - is anything missing that the old «Escludi e riprova» gave him?

---

## 3. D15 — lo storico dell'allocazione per famiglia (punti di Risk, com'erano)

> Dashboard → Allocation → history view → dimension «Tipo».

- Every ETF subtype (equity, bond, commodity…) stacks next to the generic ETF, in shades of the ETF colour; real-estate
  crowdfunding sits with Crowdfunding.
- Compare with the pie («Ora»): the same grouping and the same colour families.
- Each raw type is still its own series; only order and colour follow the family.

---

## 4. La torta con il secondo anello, e i margini

- **La torta** (Dashboard → Allocazione → «Ora», dimensione «Tipo»): quando una famiglia contiene un sottotipo, la
  relazione è disegnata come **un secondo anello**, separato dal primo, invece che con le sfumature (D72). Senza
  sottotipi resta l'anello unico di prima.
- **I margini**: meno spazio vuoto a sinistra del grafico di crescita (Dashboard) e del confronto dei lotti (pagina di un
  broker).

---

## 5. La domanda sulla palette (di Risk, da fare esattamente così)

«Per distinguere le sfumature di una stessa famiglia misuriamo la distanza fra due colori in CIEDE2000 (ΔE). Sulla
torta, oggi, la coppia più vicina sta a **5,4**. Sul grafico storico, prima del D15, la coppia più vicina stava a **8,3**.
Ora la famiglia ETF dello storico, che ha da 4 a 7 membri, usa la stessa regola della torta, e la sua coppia più vicina
scende fra **5,8 e 7,8** (5,82 · 6,10 · 6,97 · 7,76 per 7, 5, 4 e 6 membri). Resta sopra il minimo della torta, ma sotto
il vecchio minimo dello storico. Due posizioni della palette dello storico sono grigie, quindi senza un tono da
conservare.
- **(a) [consigliato]** Un criterio unico per i due grafici, ΔE ≥ 5,4 (il minimo della torta): va bene com'è, e il test
  lo fissa.
- **(b)** Lo storico resta più severo (≥ 8,3), con una regola delle sfumature regolata solo per lui: più codice, e le
  sfumature ETF dei due grafici non sarebbero più uguali.
Guardando le sfumature ETF sul grafico storico con i suoi dati, quale preferisce?»

---

## Risposte del developer

> Le registro qui testuali, tranne le cifre ricavate dai suoi dati e i nomi dei suoi asset: il journal finisce nel repo
> pubblico, quindi sono omessi (`[…]`). A Risk sono andate così come sono.

### Parte 1 — il lavoro di A (05/10, testuale)

> il selettore dell'asset per il benckmark non mi pare quello che avevamo detto con risk, il pannel in asset-correlation con i vari filtri, e in oltre quando viene scelto cambia l'altezza del selettore e quindi la resa.
> Riguardo le 4 card, nell'? il tooltip ripete il titolo, servirebbe una piccola spiegazione su ciascuna metrica, in compenso i limiti funzionano
> Sempre nelle 4 card, eccetto per volatilità, gli altri hanno un sotto titolo che è il titolo, magari inventiamoci qualcosa di meglio
>
> la frase sotto lo scatter è corretta ma troppo caotica, bisogna semplificare, andare a capo e rendere il tutto meno un muro di testo:
> Sopra la retta significa pagato meglio per il rischio preso. I punti mostrano il rendimento atteso in media-varianza, la grandezza in cui la pendenza della retta è lo Sharpe: su un asset molto volatile il rendimento realmente vissuto è più basso, perché la volatilità erode il composto. La liquidità ([quota omessa] del patrimonio) non è un punto: nel modello rende esattamente zero, e disegnarla la trasformerebbe in una misura. Anche le posizioni senza una serie di prezzi ([quota omessa] del patrimonio) non sono punti: non è stato possibile misurarle, e il modello le tiene a rendimento esattamente zero.
>
> Poi non si capisce se la retta sia calcolata da una qualche metrica o è solo la retta passante per il portafoglio, e non si capisce dall'infobox il perchè della larghezza del punto, e il benckmark se presente già come punto diventa un punto doppio, in arancione l'istanza benckmark e in grigio, con la sua larghezza quella del portafoglio, mi aspettavo che si riusasse la stessa, cambiando semplicemente il portafoglio.

**Smistamento (A)**:
- **a Risk** (il suo `BenchmarkSelect`, e il selettore del lab di F): il selettore del benchmark non è «il pannello di
  asset-correlation con i vari filtri»; e scelto un asset l'altezza del selettore cambia.
- **miei**: le 4 card di L3 (tooltip del «?» = il titolo → una breve spiegazione per metrica; sottotitolo = il titolo, tranne
  la volatilità → qualcosa di meglio); la nota sotto lo scatter (semplificare, andare a capo, niente muro di testo); la
  retta (non si capisce da cosa nasce); il tooltip del punto (non spiega la dimensione); il benchmark posseduto disegnato
  due volte (atteso: lo stesso punto, che cambia solo ruolo).

### Parte 2 — F3, il replay storico (05/10, testuale)

> riguardo i preset, non mi piace che abbiano un altezza diversa dal periodo, e la posizione del replay non la metterei sulla stessa riga, ma a capo allineata a destra fissa.
> Poi creerei dello spazio tra replay e monte carlo, potenzialmente anche proprio dei tab nel pannel, uno per ogni tool, o ancora meglio, un selettore di tool da usare che aggiunge quella sezione, per ora sono solo questi 2, nel tempo possono aumentare, e ogni tool ha un suo riquadrro per non essere confuso.
>
> poi che ci sia in cima stess test parziale mi pare sbagliato, credo doveva comparire il banner che avvisava che alcuni asset non esistevano o che bisognava ridurre il periodo. e anche nel grafico, gli ultimi […] non dovevano esserci, proprio per questo motivo:
>
> Cosa succede se…?
>
> Stress test: Parziale
>
> Replay storico
> Rendimenti reali di un periodo reale.
>
> Preset
>
> Seleziona
> Periodo
> DAL
>
> AL
>
> Esegui replay
> [Uscita del replay sui suoi dati, omessa: il journal è pubblico. Si vedeva un totale negativo per il periodo; gli ETF
> con impatto negativo, in percentuale e in euro; il BTP e i progetti di crowdfunding, senza prezzi nel periodo,
> esclusi ma disegnati a +0,00 %; sotto le barre, «Fuori dal replay» con una quota rilevante del valore lasciata fuori,
> e il motivo «Nessun prezzo nel periodo» con gli esclusi e il loro peso.]
>
> bisogna poi migliorare la resa dando più enfasi e ordine ai numeri, mettendo le cose incolonnate, facendo scorrere i nomi degli asset se lo  spazio non torna, magari usando la datatable per permettere all'utente di cambiare la larghezza della zona centrale con le barre.
>
> Riguardo lo shick ipotetico, è sezione succezziva o rientra in replay?

**Risposta di A alla domanda**: lo shock ipotetico è la sezione **successiva**, separata dal replay. L4 ha tre passi, in
quest'ordine: replay storico (osservato), shock ipotetico (assunto), simulazione Monte Carlo (modellata)
(`L4WhatIf.svelte:57-73`).

**Smistamento (A)**:
- **a Risk** (`L4Replay`, `L4WhatIf`): l'altezza dei preset diversa da quella del periodo; «Esegui replay» a capo,
  allineato a destra; spazio fra replay e Monte Carlo, o tab per strumento, o meglio un selettore di strumenti che aggiunge
  la sezione, un riquadro per strumento; gli asset esclusi ancora disegnati nel grafico con +0.00%; i numeri incolonnati e
  più in evidenza, nomi che scorrono, magari la datatable per allargare la zona delle barre; il banner atteso («alcuni asset
  non esistevano / ridurre il periodo»).
- **mio** (`RiskLevelsPanel.svelte`): la riga di stato di L4 dice «Stress test: Parziale» invece di «Replay storico:
  Parziale». `l4Health = degradedResults(l4Results)` è **senza etichette**, e replay e shock hanno tutti e due il codice
  `stress`, quindi tutti e due si chiamano «Stress test». Servono le etichette per istanza, come per i due VaR di L1.

### Parte 3 — D15, lo storico per famiglia (05/10, testuale)

> il grafico a torta è perfetto!
> quello per allocazione va bene, ma nel tooltip se metti vicini padre e figli, magari tabbando i figli, sarebbe meglio

**Smistamento (A)**: **a Risk** (D15, il grafico storico): nel tooltip, padre e figli vicini, con i figli rientrati.

### Parte 4 — i margini (05/10, testuale)

> in % si ed è perfetto, ma nei grafici in abs e p&l c'è ancora quello spazio che ti avevo chiesto di togliere anche se in p&l-income mi pare corretto, capisci tu cosa non è andato bene... Riguardo l'income già che ci siamo, facciamo che il bucket di default è 1M

**Smistamento (A)**: **a Risk / coordinator** (il grafico di crescita è di I, non mio): in modalità % lo spazio a sinistra
va bene; in Abs e in P&L c'è ancora; in P&L-income sembra giusto. Il developer chiede di capire cosa non è andato. Nuova
richiesta: nell'income, il bucket predefinito diventa **1M**. (A fa una diagnosi in sola lettura prima di passarlo.)

### Parte 5 — la palette (05/10, testuale)

> i colori attuali sono perfetti, ma mi sono accorto, mentre guardavo, che se si allarga abbastanza il grafico storico, si nota che ora ci sono delle aree con sovrapposizioni, credo che conti 2 volte l'area di padre e figli, se mostri i figli il padre non va graficato, ma mostrato solo nel tooltip per fare la somma

**Smistamento (A)**: **a Risk** (D15). «I colori attuali» sono l'opzione **(a)** (che dice «va bene com'è»): lettura di A,
confermata subito dopo con il developer (sotto). Nuovo difetto: allargando il grafico storico si vedono **aree
sovrapposte**; il developer pensa che padre e figli siano contati due volte. Se si mostrano i figli, il padre non va
disegnato, ma solo mostrato nel tooltip come somma.
- **Conferma del developer (05/10)**: «Sì, (a): i colori come sono».

### Diagnosi dei margini in Abs e P&L (A, sola lettura, 05/10)

- C'è **una sola** `grid` in `dashboard/GrowthChart.svelte` (`:2071`): `left: '3%'`, `containLabel: true` (`cda9408d4`).
  Quindi lo spazio che resta non viene dal margine.
- **Causa probabile**: nelle viste a linee e candele (Abs, P&L, cioè tutte tranne l'income a barre) l'asse y ha un
  **minimo calcolato** (`min: floor(value.min − 8 % dell'ampiezza)`, `:2266`), quindi un valore grezzo, non un tick tondo.
  La sua etichetta è nascosta (`showMinLabel: false`, D25), ma con `containLabel` ECharts misura **tutte** le etichette
  dei tick, anche quella nascosta. Il formattatore del denaro stampa il valore esatto con fino a 15 cifre significative
  (D18, `:2005-2017`): per esempio, con un valore inventato, «12.345k» contro «12k» dei tick visibili. Il margine si
  allarga della differenza.
- **Perché % e income vanno bene**: in % il formattatore è `toFixed(1)`, quindi il bordo è largo come gli altri tick;
  nell'income il minimo non è calcolato (`incomeBars ? undefined : …`), quindi ci sono solo tick tondi.
- **Da verificare** (è il comportamento di ECharts che ricordo: `estimateLabelUnionRect` scorre `scale.getTicks()`, che
  include il bordo, e non guarda `showMinLabel`). Rimedi possibili, per chi possiede il file: arrotondare il minimo
  all'intervallo dei tick, oppure stampare il bordo nascosto con le stesse cifre dei tick.
- Il file è di I: **non** lo tocco.

---

## Le due diagnosi chieste da Risk, sui dati veri (05/10, conclusioni senza valori)

> Fatte sulla copia, attraverso la sessione del developer già aperta nel pannello (cookie), **senza le sue credenziali**,
> con il suo assenso. I valori sono andati solo a Risk; qui le sole conclusioni (vincolo Ⓕ).

1. **D15, «sovrapposizioni fra ETF e crowdfunding»**: **nessun doppio conteggio**. `allocation_history.type` somma a 100 %
   (a meno dell'arrotondamento) in tutti i punti, nessuna chiave è la somma di altre, e tutte le serie del grafico hanno
   `stack: 'allocation'`. **Effetto visivo**: la banda del Crowdfunding è un verde scurissimo (`#1a4031`) con l'area
   semitrasparente (alfa `0x88`, circa metà), che su bianco sembra una miscela di arancio e verde; fra lei e l'ETF
   corrono bande sottili dei sottotipi ETF (una quasi nera, `#322002`). Il developer ha mandato uno screenshot (passato a
   Risk come percorso).
2. **Replay, gli asset a +0,00 %**: **sono in tutte e due le liste**, quindi è un difetto del backend per il criterio di
   Risk. Rifatto lo shock inflazione 2022 (la corsa del developer, con ogni probabilità): il BTP e i progetti di
   crowdfunding sono esclusi in `metadata.historical_replay_audit.excluded_assets` (`no_prices_in_window`,
   `zero_return_residual`), ma `output.impacts` li porta comunque come righe a rendimento zero, e il blocco li disegna.
   Il BTP ha il primo prezzo dopo la finestra; i progetti di crowdfunding non hanno prezzi. Dove correggere lo decide
   Risk.

## Chiusura · 05/10

- Server spento (`stop_bash`), **6163 libera**. **Copia cancellata** (`lsof +D` vuoto prima, `ls` → assente), con i due log
  del server che stavano dentro. Nessuna copia `.prev`. Lo snapshot del coordinator resta.
