# 💸 Rendimento sul costo (YOC)

Il rendimento sul costo (YOC) misura il **reddito lordo registrato non negativo prodotto per unità corrente sulle ultime 365 date di calendario**, rispetto al prezzo medio di carico per unità della posizione aperta ([Prezzo medio di carico, o PMC](../weighted-average-cost.md)).

LibreFolio lo calcola separatamente per ogni coppia $(a,b)$:

$$
(a,b) = (\text{asset},\ \text{broker})
$$

Lo stesso asset detenuto presso due broker ha quindi due valori YOC indipendenti.

!!! warning "Reddito lordo registrato — non un rendimento al netto delle imposte"

    YOC utilizza solo importi in contanti non negativi da transazioni `DIVIDEND` e `INTEREST` collegate ad asset. Lo zero esatto è accettato; gli importi di reddito negativi non sono supportati. Le transazioni separate `TAX` e `FEE` non vengono sottratte, quindi il risultato non deve essere letto come performance di reddito al netto delle imposte o netta.

---

## 🧭 Ambito e finestra temporale scorrevole

Sia $T$ la data di fine report selezionata. YOC utilizza sempre la finestra inclusiva:

$$
\boxed{[T-364,\ T]}
$$

Questa finestra contiene 365 date di calendario ed è **indipendente dalla data di inizio del report**. Spostare l'inizio di un report della dashboard non cambia YOC quando $T$ rimane invariata.

Sono idonee solo le voci non negative, collegate ad asset, dal registro delle transazioni personali:

| Incluse | Escluse |
|---|---|
| Righe `Transaction` collegate ad asset di tipo `DIVIDEND` o `INTEREST`, con importo in contanti uguale o maggiore di zero | Transazioni separate `TAX`, `FEE` e `ADJUSTMENT` |
| L'importo in contanti non negativo, la valuta, la data, l'asset e il broker pagatore | Reddito da `AssetEvent` del provider o manuale |
| Reddito assegnato alla coppia esatta $(a,b)$ | Reddito senza un asset |

Lo schema delle transazioni accetta un importo in contanti `DIVIDEND` o `INTEREST` pari a zero esatto, ma rifiuta un importo negativo. Un `ADJUSTMENT` può influire sulla quantità riprodotta, sul PMC o sugli input di split collegati, ma non entra mai nel numeratore del reddito YOC.

Il calcolo non prevede una allowlist di classi di asset. Si applica a ogni tipo di posizione long aperta rappresentata dal motore del portafoglio, inclusi crypto e asset manuali, purché gli input richiesti di registro, PMC, split e FX siano validi.

---

## 🧮 Definizione matematica

Per ogni transazione di reddito idonea $j$:

| Simbolo | Significato |
|---|---|
| $D_j$ | Data della transazione |
| $I_j$ | Importo lordo in contanti della transazione non negativo nella valuta $c_j$, con $I_j\geq0$ |
| $C^*$ | Valuta di report selezionata |
| $q_j$ | Quantità long idonea presso il broker pagatore alla fine del giorno $D_j-1$ |
| $s_j$ | Prodotto dei rapporti di split collegati datati da $D_j$ fino a $T$, inclusi |
| $w_{a,b,T}$ | Prezzo medio di carico per unità (PMC) della coppia $(a,b)$ a $T$, mantenuto in $C^*$ ai tassi storici |

### 💱 Conversione del reddito

Ogni importo di reddito viene convertito nella valuta di report alla propria data di transazione:

$$
I_j^* =
I_j \cdot \mathrm{fx}(c_j,C^*,D_j)
$$

### 🧬 Normalizzazione per unità corrente

Il reddito per unità viene prima allocato sulla quantità idonea del giorno precedente, poi normalizzato per ogni split collegato valido alla data del reddito o successivo:

$$
g_{a,b,T}
=
\sum_{\substack{j \in (a,b)\\T-364 \leq D_j \leq T}}
\frac{I_j^*}{q_j \cdot s_j}
$$

Per uno split 2-per-1, $s_j=2$: il reddito storico per vecchia unità viene diviso per due, così è confrontabile con le unità correnti. Anche uno split collegato datato $D_j$ è incluso.

### 📊 Denominatore del prezzo medio di carico

Il denominatore è il prezzo medio di carico per unità della posizione, **già espresso nella valuta di report**: quando è stata costruita la media, ogni acquisizione vi è entrata al tasso della propria data (vedi la sezione multi-valuta di [Prezzo medio di carico (PMC)](../weighted-average-cost.md)):

$$
w_{a,b,T}^*
=
\frac{C^{*}_{a,b,T}}{Q_{a,b,T}}
$$

dove $Q_{a,b,T}$ è la quantità del pool a costo medio della coppia a $T$ e $C^{*}_{a,b,T}$ il suo costo storico in $C^*$: ogni acquisizione $i$ ha aggiunto $P_i \cdot \mathrm{fx}(\mathrm{ccy}(P_i), C^*, d_i)$ per l'importo $P_i$ pagato alla data $d_i$, e ogni riduzione ha rimosso la sua quota proporzionale.

Nessuna conversione viene applicata alla data di fine report $T$: il denominatore è quanto è stato pagato e non si muove con il tasso di cambio odierno.

LibreFolio riporta quindi:

$$
\boxed{
\mathrm{YOC}_{a,b,T}
=
\frac{g_{a,b,T}}{w_{a,b,T}^*}
}
$$

Il valore API è una frazione e la tabella Posizioni lo mostra come percentuale. Un valore disponibile può essere positivo o esattamente zero.

---

## 🔁 Regole su quantità, custodia, trasferimento e split

La quantità idonea $q_j$ è deliberatamente valutata alla **fine del giorno prima del pagamento**:

- conta solo la quantità `LONG`;
- un **acquisto nello stesso giorno è escluso**;
- una **vendita nello stesso giorno è inclusa**, perché quelle unità esistevano alla fine del giorno $D_j-1$;
- la custodia del broker è rispettata durante tutto il replay dei trasferimenti;
- un frammento in transito conta ancora per il broker di origine, mai per la destinazione prima dell'arrivo.

Il reddito rimane associato al broker che lo ha registrato. Spostare unità dal broker A al broker B **non** trasporta automaticamente il reddito storico di A nel YOC di B. Il reddito successivo registrato presso B utilizza la quantità idonea del giorno precedente di B e il prezzo medio di carico di B.

Gli split collegati successivi e nello stesso giorno ridimensionano il reddito per unità precedente nelle unità esistenti a $T$. LibreFolio utilizza righe di split collegato esplicite; non deduce una rettifica a livello di asset da uno split registrato solo presso un altro broker. Se un replay connesso cross-broker contiene uno split ma manca una riga di split corrispondente per il broker del reddito/corrente, la normalizzazione è ambigua e YOC fallisce in modo fail-closed. Uno split collegato non valido, duplicato, non corrispondente o non positivo rende parimenti indisponibile la coppia interessata invece di produrre un risultato approssimativo.

Le transazioni `ADJUSTMENT` rimangono solo input di replay: possono modificare la quantità o il PMC e possono portare uno split collegato, ma i loro importi non contano mai come reddito.

??? example "Operazioni nello stesso giorno e uno split successivo"

    Si supponga che un dividendo di 20 € sia registrato il 30 giugno. Il broker pagatore deteneva 100 unità long idonee alla fine del giorno 29 giugno. Un acquisto o una vendita il 30 giugno non cambia quel denominatore.

    Uno split collegato 2-per-1 avviene tra il 30 giugno e $T$, quindi:

    $$
    g = \frac{20}{100 \times 2} = 0.10\ \mathrm{EUR}
    $$

    Se il prezzo medio di carico (PMC) a $T$ è 4,00 € per unità corrente:

    $$
    \mathrm{YOC} =
    \frac{0.10\ \mathrm{EUR}}{4.00\ \mathrm{EUR}}
    = 2.50\%
    $$

---

## 🌍 Risoluzione FX e provenienza

YOC utilizza l'attuale politica FX storica del portafoglio:

- il reddito richiede FX per $D_j$;
- il prezzo medio di carico (PMC) non necessita di FX a $T$: ciascuna delle sue acquisizioni è stata convertita alla propria data quando è stata costruita la media;
- quando la data esatta è assente, viene utilizzato il tasso memorizzato più recente a quella data o precedente;
- nessun tasso forward viene sostituito.

La provenienza conserva sia la **data richiesta** sia la **data effettiva del tasso** di ogni conversione del reddito, oltre alla coppia di valute e ai giorni trasportati all'indietro. Il tooltip della tabella Posizioni può quindi mostrare, per esempio, che una conversione del reddito del 30 giugno ha utilizzato il tasso più recente del 28 giugno.

Se una qualsiasi conversione del reddito richiesta non può essere risolta, l'intera coppia è indisponibile. Se il costo di un'acquisizione non può essere convertito — o un trasferimento o una rettifica non ha costo di carico — il prezzo medio di carico stesso è indisponibile, e lo è anche YOC. LibreFolio non omette silenziosamente la transazione interessata né riutilizza un valore non correlato.

---

## 🚦 Disponibilità e comportamento fail-closed

YOC distingue un'assenza valida di reddito da un calcolo di cui non ci si può fidare.

| Stato | Significato | Cella Posizioni |
|---|---|---|
| **Disponibile** | Esiste almeno una transazione di reddito idonea e ogni input richiesto è valido. Il risultato è positivo quando qualsiasi importo idoneo è positivo; è esattamente zero quando una o più righe idonee sono registrate con importo zero e nessuna ha un importo positivo. La provenienza contrassegna quel caso di zero esatto con `net_zero=true`. Non si applica un'età minima della coppia. | Percentuale con due decimali: per esempio, `2.50%` o `0.00%`. |
| **Nessun reddito** | Non esiste alcuna riga di reddito idonea nella finestra e la coppia ha una cronologia di registro completa di 365 date. Il valore API è zero, ma questo stato è distinto da uno zero disponibile. | `-` con tooltip esplicativo e nessuna icona di avviso. |
| **Indisponibile** | La coppia senza reddito è troppo giovane, oppure un input richiesto di registro/calcolo non ha superato la validazione. Il suo valore è `null` e il motivo identifica l'errore. | `-` con un'icona info e tooltip personalizzato del motivo. |

Il campo esterno `yield_on_cost` è obbligatorio e non nullo per ogni posizione. Un risultato indisponibile è quindi rappresentato dallo stato `unavailable` dell'oggetto risultato e dal `value` nullo, non da un campo esterno mancante o nullo.

Sia $F_{a,b}$ la primissima data di transazione collegata ad asset per la coppia. Un risultato di nessun reddito diventa valido solo quando:

$$
(T-F_{a,b})+1 \geq 365
$$

Equivalentemente, $F_{a,b} \leq T-364$. Chiudere e successivamente riaprire la posizione **non** azzera questa età: la transazione originale della prima coppia rimane l'ancora.

Questo gate di un anno viene valutato **solo quando la finestra temporale scorrevole non contiene transazioni di reddito idonee**. Non è una regola di annualizzazione: una coppia più giovane con reddito registrato valido può avere un YOC disponibile perché la metrica somma semplicemente il reddito osservato all'interno di $[T-364,T]$.

Il calcolo fallisce in modo fail-closed per una qualsiasi di queste condizioni:

- il reddito non ha quantità long idonea alla fine del giorno $D_j-1$;
- il replay delle transazioni o dei trasferimenti è incoerente;
- i dati dello split collegato sono non validi o incoerenti;
- manca il FX storico richiesto;
- il prezzo medio di carico (PMC) è mancante o non positivo — mancante include un'acquisizione il cui costo non poteva essere convertito o non ha costo di carico.

Un singolo input richiesto errato rende l'intera coppia indisponibile. Non esiste somma parziale, sostituto di evento asset, fallback da reddito del provider o approssimazione con quantità corrente.

---

## 🖥️ Leggere YOC in LibreFolio

YOC appare nella tabella condivisa **Posizioni** utilizzata sia dalla scheda Posizioni della Dashboard sia dalla scheda Posizioni di ciascun broker:

- visibile per impostazione predefinita immediatamente accanto a **Annualizzato**;
- i valori disponibili, incluso lo zero esatto, sono fissati a due cifre decimali;
- i valori positivi non hanno `+` iniziale;
- uno zero disponibile appare come `0.00%` e ha `net_zero=true` nella sua provenienza;
- un trattino normale di nessun reddito non ha icona di avviso;
- un trattino indisponibile ha un'icona info il cui tooltip spiega il motivo specifico e la provenienza disponibile;
- le scelte mostra/nascondi sono condivise tra le viste Dashboard e broker e persistono tra le sessioni.

Ogni riga rimane specifica del broker. Nell'ambito multi-broker della Dashboard, due righe per lo stesso asset possono quindi mostrare valori diversi. Vedi [Posizioni e analisi](../../../../user/dashboard/positions.md) per la guida alla tabella rivolta all'utente.

---

## ⚖️ Cosa non è YOC

| Metrica | Denominatore e orizzonte | Perché differisce da YOC di LibreFolio |
|---|---|---|
| [**Rendimento da dividendo di mercato**](../../../instruments/asset-events/dividend.md) | Dividendo annuo per azione diviso per il prezzo di mercato corrente | Misura di mercato/provider; YOC utilizza solo il reddito personale registrato e il prezzo medio di carico (PMC). |
| **Rendimento cumulativo in contanti** | Reddito totale dell'intero periodo diviso per il costo di carico totale corrente | YOC utilizza solo $[T-364,T]$, ricostruisce il reddito per unità storica idonea e non divide il contante dell'intero periodo per il costo di carico aggregato odierno. |
| [**Rendimento annualizzato netto / CAGR**](net-annualized-return.md) | Rendimento totale netto composto sulla finestra di detenzione | Include performance di mercato, reddito, commissioni e imposte; YOC isola il reddito lordo registrato e non è annualizzato da un rendimento cumulativo. |
| [**Rendimento corrente di un'obbligazione**](../../../instruments/asset-events/interest.md) | Cedola annua divisa per il prezzo corrente dell'obbligazione | Misura cedola/prezzo a livello di strumento; YOC utilizza il registro del broker dell'investitore e il PMC. |
| [**Rendimento alla scadenza (YTM)**](../../../instruments/asset-events/interest.md) | Tasso di sconto che equipara le cedole future e il valore di rimborso di un'obbligazione al prezzo | IRR obbligazionario prospettico; YOC è retrospettivo, basato su transazioni e si applica a ogni tipo di posizione. |

---

## 🔗 Correlati

- 📊 [Prezzo medio di carico (PMC)](../weighted-average-cost.md) — denominatore del prezzo medio di carico
- 🖥️ [Posizioni della dashboard](../../../../user/dashboard/positions.md) — stati delle colonne, formattazione e preferenza condivisa
- 💰 [Transazioni di dividendi e interessi](../../../instruments/transaction-types/dividend-interest.md) — voci idonee del registro personale
- ⚙️ [Motore del portafoglio](index.md) — stato della posizione e livello delle metriche
