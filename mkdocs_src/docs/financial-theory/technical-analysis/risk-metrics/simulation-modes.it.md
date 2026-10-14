# 🎲 Modalità di simulazione

La simulazione proietta un portafoglio in avanti generando un gran numero di futuri possibili e leggendo la distribuzione di dove arrivano. È l'unico punto di questa sezione in cui **nulla dell'output è accaduto**: ogni percorso è fabbricato, e il modo in cui è fabbricato decide cosa possono contenere i risultati e cosa no.

Esistono cinque modi di fabbricarli. Il risultato nomina quello usato, con le sue impostazioni, in un breve blocco — *Cosa ha assunto questa simulazione* — ma non cosa implicano quelle impostazioni. Questa pagina lo dichiara.

---

## 🧭 Le cinque modalità {: #the-five-modes }

Nella scheda **Rischio** della Dashboard e della pagina di un broker, la simulazione è il terzo strumento di **E se…?**, dopo il replay storico e lo shock ipotetico. Offre cinque modalità, ciascuna con la propria assunzione scritta sotto il nome:

| Modalità | Come vengono creati i percorsi | Assunzione aggiunta allo storico |
|---|---|---|
| **Storia rimescolata** — *Consigliata*, predefinita | [Bootstrap a blocchi congiunto](#block-bootstrap) | Nessuna: i tuoi rendimenti, riordinati in blocchi |
| **Mercato calmo** | Bootstrap a blocchi congiunto con un [regime](#prescribed-regimes) | Oscillazioni ridotte del 30% per l'intero orizzonte |
| **Crisi prolungata** | Bootstrap a blocchi congiunto con un regime | Oscillazioni ×2,5 e un livello che cala del 20% all'anno, per 14 mesi |
| **Shock e recupero** | Bootstrap a blocchi congiunto con un regime | Un calo del 35% nei primi due mesi, poi lo storico così com'era |
| **Curva normale (GBM)** — *Avanzata* | [Moto browniano geometrico](#the-process) | Rendimenti gaussiani con deriva, volatilità e correlazione costanti |

Le prime quattro estraggono rendimenti reali dalla finestra analizzata e differiscono solo per il regime che dichiarano sopra di essi; l'ultima estrae da un modello adattato a quella finestra. Un regime non può essere combinato con la curva normale, e l'elenco non offre una simile coppia.

Accanto alla modalità, il passaggio chiede un **Orizzonte (giorni)** — 365 per impostazione predefinita, al massimo 3 650 — e un numero di **Percorsi di simulazione** — 8 192 per impostazione predefinita, da 256 a 100 000 — e, solo per la curva normale, una **Strategia di campionamento**. Un **Seme casuale** fissa le estrazioni — quasi-Monte Carlo non ne ha bisogno — così che gli stessi input diano sempre lo stesso risultato. **Simula** la esegue. La risposta fornisce il **Rendimento medio terminale**, la **Probabilità di perdita** — la quota di percorsi che terminano sotto il punto di partenza — e l'intervallo dal 5° al 95° percentile nell'ultimo giorno, sopra un cono che disegna il 5°, 50° e 95° percentile giorno per giorno.

La scheda **Rischio e Scenari** della pagina di dettaglio di un asset esegue ancora solo la curva normale, con campionamento Monte Carlo o quasi-Monte Carlo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="whatif-simulation" alt="La casella Simulazione di E se…? della Dashboard: l'avviso beta e l'avviso sul modello, le cinque modalità con Storia rimescolata consigliata, orizzonte, percorsi e seme, e dopo Simula le cifre terminali, il cono e Cosa ha assunto questa simulazione" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🧪 Perché la simulazione è ancora in beta {: #why-beta }

Ogni altra parte dell'Analisi del rischio è uscita dalla beta. Solo il passaggio di simulazione si apre con un avviso: *La simulazione è ancora in beta. Il suo esito dipende fortemente da quanta storia viene richiesta rispetto all'orizzonte: una finestra breve con un orizzonte lungo può produrre cifre non plausibili.* Sotto di esso, un secondo avviso resta per sempre, perché un modello resta un modello: *Questo è l'unico gradino che è un modello anziché una misurazione. Leggilo come un intervallo di possibilità, non come una previsione.*

Il difetto dietro il primo avviso è il rapporto tra l'orizzonte $H$, contato in passi, e le $n$ osservazioni della finestra. Un percorso ricampionato di $H$ passi riutilizza ogni osservazione $H/n$ volte in media: da un quarto di storia, un orizzonte di un anno è quel quarto, rimescolato e ripetuto circa quattro volte, e qualunque cosa abbia fatto quel quarto — un rally, un periodo calmo, una discesa — diventa l'anno. La curva normale non ne è immune, perché la sua deriva e la sua volatilità sono quelle della finestra, mantenute invariate per quanto lungo sia l'orizzonte. Richiedere più storia non sempre lo cura: una posizione con una storia breve accorcia la finestra condivisa per tutte (vedi [Qualità dei dati](data-quality.md#alignment-what-missing-data-actually-costs)). Non è ancora applicata alcuna protezione su quel rapporto, e finché non ce ne sarà una, il passaggio resta in beta. L'[incertezza della deriva](#the-drift-is-an-estimate), mostrata accanto a ogni risultato, è quel rapporto all'opera.

---

## 🔁 Storia rimescolata: il bootstrap a blocchi congiunto {: #block-bootstrap }

La modalità predefinita non stima nulla. Prende i rendimenti semplici delle posizioni sulla finestra analizzata, allineati su un unico calendario condiviso — una riga per data di osservazione, una colonna per posizione — li trasforma in rendimenti logaritmici $x_{s,i} = \ln(1 + r_{s,i})$, e costruisce ogni futuro da **blocchi** di righe consecutive di quella matrice.

Con $n$ osservazioni nella finestra e blocchi di $b$ osservazioni, un percorso di $H$ passi è assemblato da $\lceil H/b \rceil$ blocchi. Ogni blocco parte da una riga estratta uniformemente a caso tra le $n$ e prende le $b$ righe da lì, riavvolgendo dall'ultima riga alla prima; i blocchi sono posti uno dopo l'altro e tagliati a $H$ passi. La posizione $i$ cresce lungo il percorso della somma composta dei suoi rendimenti logaritmici estratti, e il portafoglio è la composizione di oggi mantenuta senza ribilanciamento, la sua quota di liquidità $c$ che non rende nulla:

$$
G_i(s) = \exp\Big(\sum_{u=1}^{s} x_{u,i}\Big), \qquad R(s) = c + \sum_i w_i \, G_i(s) - 1
$$

dove $w_i$ sono i pesi di oggi e $R(s)$ è il rendimento del portafoglio dopo $s$ passi. Tre proprietà seguono dalla costruzione:

- **Vengono estratte righe intere.** Il rendimento di una data di ogni posizione viaggia con il rendimento di ogni altra posizione della stessa data, quindi il loro co-movimento è portato per costruzione: nessuna covarianza è stimata, invertita o verificata, e nessuna può fallire.
- **I rendimenti consecutivi restano insieme dentro un blocco.** La dipendenza a breve raggio — una settimana turbolenta, una serie di giorni tranquilli — sopravvive dentro ogni blocco, ed è rotta solo alle giunzioni.
- **Senza un regime, ogni passo è accaduto.** Le code sono quelle della finestra, non di una curva a campana: un singolo passo non può muoversi più del movimento più grande registrato nella finestra, e un percorso non contiene nulla che la finestra non contenesse.

### 📏 Giorni di calendario e passi {: #calendar-days-and-steps }

L'orizzonte è espresso in giorni di calendario, ma lo storico è una sequenza di osservazioni: una serie quotata nei giorni di negoziazione ne contiene circa 252 all'anno, non 365. Un orizzonte di $D$ giorni di calendario è quindi convertito alla frequenza osservata della finestra $f$, il numero di osservazioni che contiene all'anno (vedi [Annualizzazione osservata](observed-annualization.md)):

$$
H = \max\Big(1,\ \operatorname{round}\Big(\frac{D \, f}{365}\Big)\Big)
$$

I $H$ passi sono simulati e poi riletti con un punto per giorno di calendario: il giorno $d$ mostra il passo $\lfloor d \, H / D \rfloor$, quindi un giorno che cade tra due passi ripete quello precedente — nessuna negoziazione, nessun movimento.

### 🧱 La lunghezza del blocco {: #block-length }

Se non viene richiesta una lunghezza del blocco, questa segue la regola pratica del blocco mobile, proporzionale alla radice cubica del campione:

$$
b = \min\big(n,\ \max(2,\ \operatorname{round}(n^{1/3}))\big)
$$

Questo dà 6 osservazioni per un anno di giorni di negoziazione, e 9 per tre anni: abbastanza lungo da trasportare il raggruppamento della volatilità attraverso alcuni giorni consecutivi, abbastanza corto da lasciare molti blocchi distinti da cui estrarre. Il risultato riporta la lunghezza usata, riconvertita in giorni di calendario, come *Lunghezza del blocco*.

L'analisi accetta anche una lunghezza richiesta, `block_length_days`, da 1 a 5 000 giorni di calendario, convertita in osservazioni alla stessa frequenza $f$. Il passaggio **E se…?** non la offre e usa sempre la regola precedente, quindi solo una richiesta inviata direttamente all'analisi può impostarla — e solo una tale richiesta può incontrare il rifiuto descritto in [Limiti](#limits).

---

## 🌦️ Regimi prescritti {: #prescribed-regimes }

*Mercato calmo*, *Crisi prolungata* e *Shock e recupero* ricampionano esattamente come sopra, poi trasformano ogni rendimento logaritmico estratto durante l'intervallo del regime:

$$
\tilde{x}_{s,i} = \bar{x}_i + k_s \, (x_{s,i} - \bar{x}_i) + \delta_s
$$

dove $\bar{x}_i$ è il rendimento logaritmico medio della posizione $i$ sulla finestra, $k_s$ scala le oscillazioni attorno ad esso e $\delta_s$ ne sposta il livello. Fuori dall'intervallo, $k_s = 1$ e $\delta_s = 0$: lo storico viene estratto così com'era.

| Modalità | Intervallo | $k_s$ | $\delta_s$, per passo |
|---|---|---|---|
| Mercato calmo | l'intero orizzonte | $0.7$ | $0$ |
| Crisi prolungata | i primi 426 giorni di calendario (14 mesi) | $2.5$ | $\ln(0.8)/f$ |
| Shock e recupero | i primi 61 giorni di calendario (2 mesi) | $1$ | $\ln(0.65)/m$ |

con $f$ la frequenza osservata della finestra e $m$ il numero di passi coperti dallo shock. Su un anno di passi, lo spostamento della crisi si compone in un fattore di $0.8$ — un livello inferiore del 20% ogni anno rispetto a quanto darebbe il solo storico — oltre a oscillazioni larghe due volte e mezzo. Lo shock si compone a $0.65$, un calo del 35% oltre lo storico, sul suo intervallo, e sempre per intero: su un orizzonte più breve di due mesi, l'intero calo cade dentro l'orizzonte. Gli intervalli sono convertiti in passi allo stesso modo dell'orizzonte.

Un regime è **dichiarato, mai stimato**: questi numeri sono l'ipotesi, messa per iscritto, non qualcosa di misurato dai tuoi dati. Ogni passo applica lo stesso $k_s$ e lo stesso $\delta_s$ a ogni posizione, il che lascia le correlazioni tra esse quelle dello storico.

Quando l'orizzonte è più breve dell'intervallo di un regime, il regime copre solo l'orizzonte, e il risultato lo dice — per una crisi su un orizzonte di un anno: *Dichiarato su 426 giorni, applicato su 365: il cono risponde alla domanda più breve.*

---

## 📈 La curva normale: moto browniano geometrico {: #the-process }

Nella modalità *Curva normale (GBM)*, ogni percorso proviene da un **moto browniano geometrico**. Per un singolo asset, il valore $S_t$ evolve come

$$
dS_t = \mu S_t \, dt + \sigma S_t \, dW_t
$$

dove $\mu$ è la deriva, $\sigma$ la volatilità e $W_t$ un moto browniano, ed è qui che entra la casualità. Ogni asset simulato parte da 1,0, quindi il suo percorso è un fattore di crescita anziché un prezzo, ed è avanzato un giorno alla volta fino a raggiungere l'orizzonte.

Gli asset non sono simulati separatamente e sommati in seguito. Sono assemblati in un unico processo i cui shock sono legati insieme da **una matrice di correlazione**, così che un movimento in un asset arrivi accompagnato dai movimenti che il suo co-movimento misurato implica.

Integrando l'equazione si ottiene il percorso in forma chiusa:

$$
S_t = S_0 \exp\left(\left(\mu - \frac{\sigma^{2}}{2}\right) t + \sigma W_t\right)
$$

Due proprietà di questo modello fanno la maggior parte del lavoro, ed entrambe sono restrizioni:

- **$\mu$ e $\sigma$ sono costanti.** Ciascuno prende un valore e lo mantiene per l'intero orizzonte, e così fa ogni voce della matrice di correlazione. Nulla nella simulazione cambia la propria volatilità, o le proprie correlazioni, mentre viene eseguita.
- **La casualità entra solo attraverso $W_t$**, quindi su qualsiasi intervallo il rendimento logaritmico è distribuito normalmente. La forma dei rendimenti simulati è stabilita prima che venga estratto il primo percorso, e quella forma è la curva a campana.

La seconda proprietà è quella da portare in tutto ciò che segue: la distribuzione normale è **più sottile nelle code** dei rendimenti che i mercati producono davvero, e le code sono ciò per cui si legge una simulazione di rischio.

---

## 🎲 Due modi di estrarre lo stesso modello {: #sampling-strategies }

La **Strategia di campionamento** offerta con la curva normale — e solo con essa — è tra **Monte Carlo** e **quasi-Monte Carlo**. È una scelta su come vengono prodotti i numeri casuali, e su nient'altro. Il bootstrap non ha tale scelta: estrae sempre gli inizi dei suoi blocchi da un generatore pseudo-casuale con seme.

!!! warning "Due voci non sono due modelli"

    Un menu con due voci invita a leggere che ci siano due modelli disponibili, e che uno di essi possa adattarsi a un portafoglio meglio dell'altro. Non ce ne sono due. Entrambe le voci guidano lo stesso moto browniano geometrico, con la stessa deriva, la stessa volatilità e la stessa matrice di correlazione, ed entrambe estraggono numeri **gaussiani** per farlo.

    Quasi-Monte Carlo compra **convergenza**, non realismo. La sua sequenza a bassa discrepanza copre lo spazio campionario in modo più uniforme delle estrazioni pseudo-casuali, quindi la stima si assesta con meno percorsi. Non simula un mercato diverso, e non ripara nessuna delle assunzioni di questa pagina.

Ciò che differisce è ciò di cui ciascuna ha bisogno per essere riproducibile, e ciò che ciascuna richiede al numero di percorsi:

| | Monte Carlo | Quasi-Monte Carlo |
|---|---|---|
| Numeri estratti da | un generatore pseudo-casuale | una sequenza a bassa discrepanza di Sobol |
| Riprodotta da | un seme casuale | un indice di partenza nella sequenza |
| Numero di percorsi | nessun ulteriore requisito | deve essere una **potenza di due** |
| Limite aggiuntivo | — | posizioni × giorni dell'orizzonte al massimo 21 201 — vedi [Limiti](#limits) |

Entrambe sono completamente riproducibili: lo stesso seme, o lo stesso indice di partenza, rigenera gli stessi percorsi. Nessuna accetta il parametro dell'altra — un seme e un indice di partenza Sobol si escludono a vicenda. La Dashboard non mostra alcun indice di partenza: entra sempre nella sequenza da 0. La scheda **Rischio e Scenari** della pagina dell'asset consente di impostarlo.

---

## 📐 Da dove provengono i parametri {: #parameters }

Nella curva normale, il modello è fornito dalla misurazione anziché dalla scelta. I rendimenti della finestra analizzata sono convertiti in rendimenti logaritmici, e da questi:

- la **covarianza** è la covarianza campionaria, simmetrizzata e scalata a termini annuali. Ogni osservazione nella finestra ha lo stesso peso — un rendimento del primo giorno conta esattamente quanto uno dell'ultimo;
- le **volatilità** sono le radici quadrate della sua diagonale, e la **matrice di correlazione** è ciò che rimane una volta divisa fuori quella scala;
- la scalatura a termini annuali usa il fattore di intervallo osservato misurato descritto in [Annualizzazione osservata](observed-annualization.md), non una convenzione fissa.

La deriva è l'unico parametro che non è semplicemente la media misurata:

$$
\mu = \bar{r}_{\log} \cdot f + \frac{\sigma^{2}}{2}
$$

con $\bar{r}_{\log}$ il rendimento logaritmico medio per osservazione, $f$ il fattore di annualizzazione e $\sigma^{2}$ la varianza annuale. Il termine di metà varianza è la correzione di convessità di Itô. Il parametro di deriva del processo è un tasso di crescita *semplice* atteso, mentre ciò che è stato misurato è un rendimento *logaritmico* medio, e i due differiscono esattamente di metà della varianza; aggiungerla di nuovo è ciò che rende la crescita logaritmica attesa dei percorsi simulati uguale al rendimento logaritmico medio della finestra. Senza di essa, i percorsi crescerebbero più lentamente dei dati da cui provengono.

La liquidità è trattata diversamente dalle posizioni, in ogni modalità. Entra nel percorso del portafoglio al suo peso e vi rimane: la componente di liquidità **rende esattamente zero** per l'intero orizzonte e non contribuisce con alcuna variazione propria.

---

## 🧮 La deriva è una stima {: #the-drift-is-an-estimate }

Qualunque sia la modalità, il centro del cono si basa sulla crescita media della finestra — il bootstrap estrae ogni riga con la stessa probabilità, la curva normale imposta la sua deriva dalla stessa media — e quella media è una stima campionaria, con un proprio errore standard. Il cono non contiene quell'errore: è la diffusione dei percorsi *data* la deriva. Quindi accanto al risultato, una riga dichiara quanto quell'errore da solo sposta la mediana.

Con $\hat{\sigma}$ la deviazione standard del rendimento logaritmico del portafoglio per osservazione sulle $n$ osservazioni della finestra — liquidità contata al suo peso, che non rende nulla — e $H$ l'orizzonte in passi, il fattore al 95% è

$$
\varphi = \exp\left(z_{0.975} \, \frac{H \, \hat{\sigma}}{\sqrt{n}}\right), \qquad z_{0.975} \approx 1.96
$$

e alla mediana $M$ dell'ultimo giorno è dato l'intervallo $\big[(1 + M)/\varphi - 1,\ (1 + M)\,\varphi - 1\big]$: *La deriva proviene da … osservazioni: questo da solo colloca questa mediana tra … e ….* Quando $\varphi$ supera la diffusione del cono stesso, $(1 + P_{95})/(1 + P_{5})$, la riga diventa un avviso ambra: l'incertezza sulla sola deriva è allora più ampia della banda disegnata dalla simulazione.

L'esponente cresce con $H$ e si riduce solo con $\sqrt{n}$: raddoppiare l'orizzonte lo raddoppia, mentre dimezzarlo richiede quattro volte tanta storia. Questo è il [rapporto dietro l'avviso beta](#why-beta), scritto come numero.

---

## 🚧 Limiti {: #limits }

Una simulazione viene rifiutata, anziché eseguita male, nei casi seguenti. Il rifiuto è esso stesso il risultato — la simulazione torna non disponibile — e il banner di **E se…?** dice perché:

| Rifiuto | Quando | A schermo | Cosa cambiare |
|---|---|---|---|
| Storia troppo breve | Meno di 30 osservazioni nella finestra | *Storia insufficiente per questo calcolo.* | Un intervallo di date più lungo |
| Blocco più lungo dello storico | Una lunghezza del blocco richiesta copre più osservazioni di quante ne contenga la finestra | *Parametri di calcolo non validi.* | Un blocco più corto, o una finestra più lunga |
| Numero di percorsi | Quasi-Monte Carlo con un numero di percorsi che non è una potenza di due | *Parametri di calcolo non validi.* | Una potenza di due: 4 096, 8 192, 16 384… |
| Budget dei percorsi | Qualsiasi modalità, quando percorsi × (giorni dell'orizzonte + 1) supera 20 000 000, o percorsi × giorni dell'orizzonte × posizioni supera 200 000 000 | *Questa simulazione è troppo grande per essere eseguita. Usa meno percorsi di simulazione o un orizzonte più breve.* | Meno percorsi, o un orizzonte più breve |
| Sequenza troppo grande | Curva normale con quasi-Monte Carlo, quando posizioni × giorni dell'orizzonte supera 21 201 | *Questa simulazione quasi-Monte Carlo è troppo grande per essere eseguita. Accorcia l'orizzonte o scegli il campionamento Monte Carlo.* | Un orizzonte più breve, o il campionamento Monte Carlo |
| Storia troppo lunga | Storia rimescolata o un regime, quando la finestra contiene più di 5 000 osservazioni, o osservazioni della finestra × posizioni supera 250 000 | *Questa simulazione è troppo grande per essere eseguita: il periodo contiene troppa storia. Scegli un periodo più breve.* | Un intervallo di date più breve |
| Troppe posizioni | Qualsiasi modalità, quando prendono parte più di 100 posizioni | *Una simulazione può includere al massimo 100 posizioni, e questo portafoglio ne ha di più. Simula invece un broker con meno posizioni.* | Nessuna impostazione: un broker con meno posizioni, simulato dalla sua pagina |

Ogni limite di dimensione risponde `resource_limit` — troppo grande per essere eseguito, che non è né un fallimento né un difetto nei parametri. I suoi dettagli nominano il limite raggiunto, il valore raggiunto e il tetto, e un `remedy` nomina ciò che riporta la richiesta entro portata. Il rimedio sceglie la frase sullo schermo, quindi ciascuna dice cosa cambiare; un rifiuto di dimensione che non nomina alcun rimedio, o per cui il banner non ha una frase, è mostrato con la frase generale *Questo calcolo è troppo grande per essere eseguito.* Il rifiuto della lunghezza del blocco è invece un rifiuto di un'impostazione, e il suo codice lo dice — parametri non validi anziché storia insufficiente. Dichiara la lunghezza richiesta, le osservazioni che copre e le osservazioni contenute nella finestra: il rimedio è un blocco più corto, dato che spesso più storia non è disponibile. Il rifiuto di Sobol dichiara il numero di dimensioni della sequenza necessarie — una per posizione e per giorno dell'orizzonte — e il limite. All'orizzonte predefinito di 365 giorni, il limite ammette 58 posizioni; al massimo, 3 650 giorni, cade tra cinque e sei: cinque posizioni richiedono 18 250 dimensioni, sei ne richiedono 21 900. Il numero di percorsi non ha alcun ruolo, e il campionamento Monte Carlo non ha tale limite.

I limiti di dimensione mordono prima di quanto sembri. Con gli 8 192 percorsi predefiniti, qualsiasi orizzonte oltre 2 440 giorni supera il primo budget dei percorsi — a 2 441 giorni, 8 192 × 2 442 = 20 004 864. Con i 365 giorni predefiniti e 8 192 percorsi, un ambito di 67 posizioni o più supera il secondo: 8 192 × 365 × 67 = 200 335 360. Il budget dello storico si stringe man mano che l'ambito cresce: la finestra può contenere al massimo 5 000 osservazioni — quasi vent'anni di giorni di negoziazione — e al massimo 250 000 diviso per il numero di posizioni, quindi il primo vincolo governa fino a 50 posizioni e il secondo oltre, fino a 2 500 osservazioni, circa dieci anni, a 100. Oltre 100 posizioni nessuna impostazione aiuta: l'ambito è rifiutato prima che qualsiasi cosa sia ricampionata o stimata, qualunque siano le impostazioni, e ciò che resta è simulare un singolo broker con meno posizioni. In ogni conteggio, le posizioni sono quelle che la simulazione legge, quindi una posizione [esclusa](data-quality.md#exclusions) non conta in nessuno di essi. Una richiesta oltre diversi limiti li incontra uno alla volta: ogni rifiuto ne nomina uno, e il successivo appare una volta curato.

---

## 💡 Interpretazione {: #interpretation }

Leggi l'output come ciò che la modalità implica, mai come ciò che ci si aspetta accada:

- **Nulla in esso è prova.** Un percorso ricampionato riorganizza ciò che la finestra conteneva; un percorso di modello è una conseguenza della deriva, della volatilità e delle correlazioni immesse. Nessuno dei due porta informazioni che la finestra non possedesse già, e un regime aggiunge solo l'ipotesi che dichiara.
- **Più percorsi riducono l'errore di campionamento, non l'errore di modello.** Aumentare il numero di percorsi fa convergere il risultato — alla risposta che *questa modalità* dà. Nessun numero di percorsi aggiunge un crollo che la finestra non conteneva, ispessisce una coda gaussiana o fa muovere una correlazione fissa.
- **Il centro della distribuzione è un'estrapolazione.** È la crescita media della finestra mantenuta invariata — spostata, sotto una crisi o uno shock, della quantità dichiarata dal regime. Una finestra che è salita produce futuri che salgono, per tutto il tempo in cui dura l'orizzonte, e quanto precisamente sia nota quella media è l'[incertezza della deriva](#the-drift-is-an-estimate).
- **La diffusione è ampia quanto lo era la finestra, e non di più** — salvo il fattore che un regime dichiara. Un periodo di stima calmo fornisce oscillazioni calme e un co-movimento confortevole, e la simulazione produce quindi un futuro calmo in perfetta buona fede.

Le cifre che leggono ciò che è effettivamente accaduto — [Value at Risk](value-at-risk.md), [Peggior realizzazione](worst-realization.md), [Drawdown massimo](max-drawdown.md) — sono almeno limitate da una storia che si è verificata. Una simulazione è limitata solo dalle proprie assunzioni. La curva normale può mostrare una perdita peggiore di qualsiasi cosa registrata, la cui forma è del modello anziché del mercato; un lungo percorso ricampionato può incatenare blocchi cattivi in un calo che il mercato non ha mai consegnato in un'unica tirata.

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "La finestra è l'unica fonte"

    Ogni modalità legge una finestra: il bootstrap ne riutilizza le righe, la curva normale ne adatta le medie, ed entrambe pesano ogni osservazione allo stesso modo, senza peso aggiuntivo su quelle recenti. Una finestra senza un crollo non ne contiene alcuno da estrarre, e una finestra che è salita viene proiettata in avanti in salita, per quanto lungo sia l'orizzonte. La finestra su cui è stato calcolato ogni risultato è pubblicata con esso — vedi [Qualità dei dati](data-quality.md).

!!! warning "La curva normale sottostima le code"

    I rendimenti reali di mercato producono movimenti estremi più spesso, e più grandi, di quanto una distribuzione normale consenta. La modalità *Curva normale (GBM)*, costruita su incrementi gaussiani, riporta quindi esiti rari come più rari e più miti di quanto siano stati storicamente, e lo fa con maggiore sicurezza all'estremità della distribuzione — la parte che una simulazione di rischio esiste per descrivere. [Value at Risk](value-at-risk.md) copre lo stesso difetto nella sua forma parametrica. Il bootstrap conserva le code della finestra: né più sottili, né più spesse.

!!! warning "La volatilità si raggruppa solo fino a un blocco"

    Nella curva normale, la volatilità è un singolo numero per l'intero orizzonte, quindi un giorno cattivo non rende il giorno successivo più probabile che sia cattivo. Il bootstrap conserva il raggruppamento della finestra dentro ogni blocco, lungo pochi giorni, e lo perde alle giunzioni: un periodo turbolento ricampionato dura all'incirca quanto un blocco, non quanto quello da cui proviene, a meno che una *Crisi prolungata* ne dichiari uno. I mercati reali si comportano diversamente: i periodi turbolenti arrivano in serie, e le crisi persistono. Un tratto peggiore simulato non è lo stesso oggetto di una crisi storica e non dovrebbe essere confrontato con essa.

!!! warning "Le correlazioni non si rompono mai"

    La curva normale applica una matrice di correlazione a ogni futuro; il bootstrap porta il co-movimento della finestra, e i regimi lo lasciano invariato per progettazione. Nessuno dei due può produrre, a meno che la finestra non lo contenga, l'evento che danneggia maggiormente un portafoglio diversificato: correlazioni che salgono verso uno proprio quando i mercati scendono, lasciando che posizioni che si compensavano cadano insieme. [Correlazione](correlation.md) copre la versione misurata, e quanto dipenda dalla finestra da cui è stata tratta.

!!! warning "La liquidità sta ferma, e non succede nient'altro"

    La porzione di liquidità del portafoglio non cresce né varia lungo l'orizzonte, qualunque cosa potrebbe rendere in realtà, e la composizione è mantenuta senza ribilanciamento. Anche costi, flussi di cassa e inflazione sono esclusi: il risultato li elenca sotto *Esclusi dal cono*. Più lungo è l'orizzonte, più queste semplificazioni contano.

---

## 🔗 Correlati {: #related }

- 📊 **[Volatilità](volatility.md)** — la misura di dispersione che la curva normale prende come uno dei suoi due parametri
- 🔗 **[Correlazione](correlation.md)** — la struttura di co-movimento che la simulazione mantiene fissa attraverso ogni percorso
- 📅 **[Annualizzazione osservata](observed-annualization.md)** — la frequenza misurata che trasforma i giorni di calendario in passi, e le statistiche della finestra in annuali
- 📉 **[Value at Risk](value-at-risk.md)** — la stessa domanda sulle code risolta da rendimenti osservati anziché generati
- ⏮️ **[Replay storico](historical-replay.md)** — un episodio reale applicato al portafoglio corrente, dove nulla è generato
- 🧪 **[Qualità dei dati](data-quality.md)** — la finestra e il conteggio delle osservazioni da cui sono stati stimati i parametri
