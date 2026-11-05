# 💸 Rendimento sul costo (YOC)

Il rendimento sul costo (YOC) misura i **proventi lordi registrati prodotti per unità corrente sulle ultime 365 date di calendario**, rispetto al prezzo medio di carico per unità della posizione aperta ([Prezzo medio di carico, o PMC](../weighted-average-cost.md)). Ogni importo di provento conta con il proprio segno, quindi una correzione registrata riduce i proventi invece di aggiungersi.

LibreFolio lo calcola separatamente per ogni coppia $(a,b)$:

$$
(a,b) = (\text{asset},\ \text{broker})
$$

Lo stesso asset detenuto presso due broker ha quindi due valori YOC indipendenti.

!!! warning "Proventi lordi registrati — non un rendimento al netto delle imposte"

    YOC usa solo gli importi in denaro delle transazioni `DIVIDEND` e `INTEREST` collegate ad asset, ciascuno con il proprio segno. Un nuovo importo negativo viene rifiutato, ma righe più vecchie possono ancora contenerne uno: tale correzione riduce i proventi, come accade nella dashboard. Le transazioni `TAX` e `FEE` separate non vengono sottratte, quindi il risultato non deve essere letto come performance al netto delle imposte o come performance di proventi netti.

---

## 🧭 Ambito e finestra mobile

Sia $T$ la data di fine report selezionata. YOC usa sempre la finestra inclusiva:

$$
\boxed{[T-364,\ T]}
$$

Questa finestra contiene 365 date di calendario ed è **indipendente dalla data di inizio del report**. Spostare l'inizio di un report della dashboard non cambia YOC quando $T$ rimane invariata.

Si qualificano solo le voci collegate ad asset del registro personale delle transazioni:

| Incluse | Escluse |
|---|---|
| Righe `Transaction` collegate ad asset di tipo `DIVIDEND` o `INTEREST`, qualunque sia il segno del loro importo in denaro | Transazioni `TAX`, `FEE` e `ADJUSTMENT` separate |
| L'importo in denaro con segno, la valuta, la data, l'asset e il broker pagatore | Proventi da `AssetEvent` del provider o manuali |
| Proventi assegnati all'esatta coppia $(a,b)$ | Proventi senza un asset |

Lo schema delle transazioni accetta un importo in denaro esattamente pari a zero per `DIVIDEND` o `INTEREST`, ma rifiuta un nuovo importo negativo. Una riga negativa salvata in precedenza resta ammissibile e conta con il proprio segno. Una rettifica `ADJUSTMENT` può influire sulla quantità riprodotta, sul PMC o sugli input degli split collegati, ma non entra mai nel numeratore dei proventi YOC.

Il calcolo non prevede un elenco consentito di classi di asset. Si applica a ogni tipo di posizione long aperta rappresentata dal motore di portafoglio, inclusi crypto e asset manuali, purché gli input richiesti di registro, PMC, split e FX siano validi.

---

## 🧮 Definizione matematica

Per ogni transazione di provento ammissibile $j$:

| Simbolo | Significato |
|---|---|
| $D_j$ | Data della transazione |
| $I_j$ | Importo in denaro lordo della transazione nella valuta $c_j$, con il proprio segno: $I_j<0$ per una vecchia correzione negativa |
| $C^*$ | Valuta di report selezionata |
| $q_j$ | Quantità long ammissibile presso il broker pagatore alla fine del giorno $D_j-1$ |
| $s_j$ | Prodotto dei rapporti di split collegati con data da $D_j$ a $T$, inclusi |
| $w_{a,b,T}$ | Prezzo medio di carico per unità (PMC) della coppia $(a,b)$ a $T$, mantenuto in $C^*$ ai tassi storici |

### 💱 Conversione dei proventi

Ogni importo di provento viene convertito nella valuta di report alla propria data di transazione:

$$
I_j^* =
I_j \cdot \mathrm{fx}(c_j,C^*,D_j)
$$

### 🧬 Normalizzazione per unità correnti

Il provento per unità viene prima allocato sulla quantità ammissibile del giorno precedente, poi normalizzato per ogni split collegato valido alla data del provento o successivo:

$$
g_{a,b,T}
=
\sum_{\substack{j \in (a,b)\\T-364 \leq D_j \leq T}}
\frac{I_j^*}{q_j \cdot s_j}
$$

Per uno split 2-per-1, $s_j=2$: il provento storico per vecchia unità viene diviso per due, così da essere confrontabile con le unità correnti. È incluso anche uno split collegato datato $D_j$.

### 📊 Denominatore del prezzo medio di carico

Il denominatore è il prezzo medio di carico per unità della posizione, **già espresso nella valuta di report**: quando la media è stata costruita, ogni acquisizione vi è entrata al tasso della propria data (vedere la sezione multi-valuta di [Prezzo medio di carico](../weighted-average-cost.md)):

$$
w_{a,b,T}^*
=
\frac{C^{*}_{a,b,T}}{Q_{a,b,T}}
$$

dove $Q_{a,b,T}$ è la quantità del pool a costo medio della coppia a $T$ e $C^{*}_{a,b,T}$ il suo costo storico in $C^*$: ogni acquisizione $i$ ha aggiunto $P_i \cdot \mathrm{fx}(\mathrm{ccy}(P_i), C^*, d_i)$ per l'importo $P_i$ pagato alla data $d_i$, e ogni riduzione ha rimosso la sua quota proporzionale.

Nessuna conversione viene applicata alla data di fine report $T$: il denominatore è ciò che è stato pagato e non si muove con il tasso di cambio odierno.

LibreFolio riporta quindi:

$$
\boxed{
\mathrm{YOC}_{a,b,T}
=
\frac{g_{a,b,T}}{w_{a,b,T}^*}
}
$$

Il valore API è una frazione e la tabella Posizioni lo visualizza come percentuale. Un valore disponibile può essere positivo o esattamente zero. Quando $g_{a,b,T}<0$ — le correzioni della finestra superano i suoi proventi — LibreFolio non mostra affatto YOC (vedere le regole di disponibilità di seguito).

---

## 🔁 Regole su quantità, custodia, trasferimento e split

La quantità ammissibile $q_j$ viene deliberatamente valutata alla **fine del giorno precedente al pagamento**:

- conta solo la quantità `LONG`;
- un **acquisto nello stesso giorno è escluso**;
- una **vendita nello stesso giorno è inclusa**, perché quelle unità esistevano alla fine del giorno $D_j-1$;
- la custodia presso il broker viene rispettata durante tutto il replay dei trasferimenti;
- un frammento in transito conta ancora per il broker di origine, mai per la destinazione prima dell'arrivo;
- le unità che arrivano da un broker che non puoi vedere — per esempio in qualità di co-proprietario del broker ricevente — contano dal loro arrivo: l'altro broker non viene mai riprodotto e il loro costo è il costo di carico del trasferimento in arrivo, parte del prezzo medio di carico (senza di esso, YOC non è disponibile).

I proventi restano associati al broker che li ha registrati. Spostare unità dal broker A al broker B **non** trasferisce automaticamente i proventi storici di A nel valore YOC di B. I proventi successivi registrati presso B usano la quantità ammissibile del giorno precedente di B e il prezzo medio di carico di B.

Gli split collegati successivi e nello stesso giorno ridimensionano i proventi per unità precedenti nelle unità esistenti a $T$. LibreFolio usa righe esplicite di split collegati; non deduce una rettifica a livello di asset da uno split registrato solo presso un altro broker. Se un replay connesso tra broker contiene uno split ma manca una riga di split corrispondente per il broker dei proventi/corrente, la normalizzazione è ambigua e YOC adotta un comportamento fail-closed. Uno split collegato non valido, duplicato, non corrispondente o non positivo rende altresì indisponibile la coppia interessata invece di produrre un risultato approssimativo.

Le rettifiche `ADJUSTMENT` restano solo input di replay: possono modificare la quantità o il PMC e possono portare uno split collegato, ma i loro importi non contano mai come proventi.

??? example "Operazioni nello stesso giorno e uno split successivo"

    Supponiamo che un dividendo di 20 € venga registrato il 30 giugno. Il broker pagatore deteneva 100 unità long ammissibili alla fine del giorno 29 giugno. Un acquisto o una vendita il 30 giugno non modifica quel denominatore.

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

YOC usa la politica FX storica corrente del portafoglio:

- i proventi richiedono FX per $D_j$;
- il prezzo medio di carico (PMC) non richiede FX a $T$: ciascuna delle sue acquisizioni è stata convertita alla propria data quando la media è stata costruita;
- quando la data esatta è assente, viene usato il tasso memorizzato più recente alla data indicata o anteriore a essa;
- non viene sostituito alcun tasso forward.

La provenienza conserva sia la **data richiesta** sia la **data effettiva del tasso** di ogni conversione dei proventi, oltre alla coppia di valute e ai giorni riportati all'indietro. Il tooltip della tabella Posizioni può quindi mostrare, per esempio, che una conversione dei proventi del 30 giugno ha usato il tasso più recente del 28 giugno.

Se una qualsiasi conversione dei proventi richiesta non può essere risolta, l'intera coppia è indisponibile. Se il costo di un'acquisizione non può essere convertito — oppure un trasferimento o una rettifica non ha un costo di carico — il prezzo medio di carico stesso è indisponibile, e lo stesso vale per YOC. LibreFolio non omette silenziosamente la transazione interessata né riutilizza un valore non correlato.

---

## 🚦 Disponibilità e comportamento fail-closed

YOC distingue un'assenza valida di proventi da un calcolo di cui non ci si può fidare.

| Stato | Significato | Cella della tabella Posizioni |
|---|---|---|
| **Disponibile** | Esiste almeno una transazione di proventi ammissibile, ogni input richiesto è valido e il provento per unità con segno $g_{a,b,T}$ è zero o più. Il risultato è positivo quando $g_{a,b,T}>0$; è esattamente zero quando $g_{a,b,T}=0$ — per esempio quando ogni riga ammissibile è registrata con importo zero, oppure una correzione compensa esattamente i proventi. La provenienza contrassegna quel caso di zero esatto con `net_zero=true`. Non si applica un'età minima della coppia. | Percentuale con due decimali: per esempio, `2.50%` o `0.00%`. |
| **Nessun provento** | Nella finestra non esiste alcuna riga di proventi ammissibile e la coppia ha una cronologia di registro completa di 365 date. Il valore API è zero, ma questo stato è distinto da uno zero disponibile. | `-` con tooltip esplicativo e nessuna icona di avviso. |
| **Indisponibile** | La coppia senza proventi è troppo giovane, un input richiesto di registro/calcolo non ha superato la validazione, oppure le correzioni lasciano il provento per unità sotto zero. Il suo valore è `null` e la sua motivazione identifica la causa. | `-` con un'icona info e un tooltip con la motivazione personalizzata. |

Il campo esterno `yield_on_cost` è obbligatorio e non nullo per ogni posizione. Un risultato indisponibile è quindi rappresentato dallo stato `unavailable` dell'oggetto risultato e dal valore `value` nullo, non da un campo esterno mancante o nullo.

Sia $F_{a,b}$ la prima data in assoluto di una transazione collegata ad asset per la coppia. Un risultato senza proventi diventa valido solo quando:

$$
(T-F_{a,b})+1 \geq 365
$$

Equivalentemente, $F_{a,b} \leq T-364$. Chiudere e successivamente riaprire la posizione **non** azzera questa età: la transazione originaria della coppia rimane il riferimento.

Questo filtro di un anno viene valutato **solo quando la finestra mobile non contiene transazioni di proventi ammissibili**. Non è una regola di annualizzazione: una coppia più giovane con proventi validi registrati può avere un valore YOC disponibile, perché la metrica somma semplicemente i proventi osservati all'interno di $[T-364,T]$.

Il calcolo adotta un comportamento fail-closed per una qualsiasi di queste condizioni:

- i proventi non hanno una quantità long ammissibile alla fine del giorno $D_j-1$;
- il replay delle transazioni o dei trasferimenti è incoerente;
- i dati degli split collegati non sono validi o sono incoerenti;
- manca l'FX storico richiesto;
- il prezzo medio di carico (PMC) è mancante o non positivo — tra i casi di mancanza rientra un'acquisizione il cui costo non è stato convertito o non ha un costo di carico.

Un solo input richiesto non valido rende indisponibile l'intera coppia. Non esistono somma parziale, sostituto tramite evento sull'asset, fallback sui proventi del provider o approssimazione con la quantità corrente.

Un provento negativo non è un input non valido, ma non lascia alcun rendimento da mostrare. Quando ogni input è valido e $g_{a,b,T}<0$ — le correzioni registrate nella finestra superano i suoi proventi — la coppia è indisponibile con motivo `negative_net_income`, e il tooltip della tabella Posizioni mostra *Le correzioni superano i proventi dell'ultimo anno.* La sua provenienza conserva il provento negativo per unità (`gross_income_per_unit`). Una somma esattamente pari a zero non rientra in questo caso: resta disponibile a `0.00%`, con `net_zero=true`.

---

## 🖥️ Leggere YOC in LibreFolio

YOC compare nella tabella **Posizioni** condivisa, usata sia dalla scheda Posizioni della dashboard sia dalla scheda Posizioni di ciascun broker:

- visibile per impostazione predefinita subito accanto a **Annualizzato**;
- i valori disponibili, incluso lo zero esatto, sono fissati a due cifre decimali;
- i valori positivi non hanno il segno `+` iniziale;
- uno zero disponibile appare come `0.00%` e ha `net_zero=true` nella sua provenienza;
- un trattino normale per assenza di proventi non ha alcuna icona di avviso;
- un trattino di indisponibilità ha un'icona info il cui tooltip spiega il motivo specifico e la provenienza disponibile;
- le scelte di mostra/nascondi sono condivise tra le viste dashboard e broker e persistono tra le sessioni.

Ogni riga rimane specifica del broker. Nell'ambito multi-broker della dashboard, due righe per lo stesso asset possono quindi mostrare valori diversi. Vedere [Posizioni e analisi](../../../../user/dashboard/positions.md) per la guida utente alla tabella.

---

## ⚖️ Che cosa non è YOC

| Metrica | Denominatore e orizzonte | Perché differisce dal valore YOC di LibreFolio |
|---|---|---|
| [**Rendimento da dividendo di mercato**](../../../instruments/asset-events/dividend.md) | Dividendo annuo per azione diviso per il prezzo di mercato corrente | Misura di mercato/provider; YOC usa solo proventi personali registrati e prezzo medio di carico (PMC). |
| **Rendimento cumulativo in contanti** | Totale dei proventi dell'intera durata diviso per il costo di carico totale corrente | YOC usa solo $[T-364,T]$, ricostruisce i proventi per unità storica ammissibile e non divide il contante dell'intera durata per il costo di carico aggregato odierno. |
| [**Rendimento netto annualizzato / CAGR**](net-annualized-return.md) | Rendimento totale netto composto sulla finestra di detenzione | Include performance di mercato, proventi, commissioni e imposte; YOC isola i proventi lordi registrati e non viene annualizzato a partire da un rendimento cumulativo. |
| [**Rendimento corrente dell'obbligazione**](../../../instruments/asset-events/interest.md) | Cedola annua divisa per il prezzo corrente dell'obbligazione | Misura cedola/prezzo a livello di titolo; YOC usa il registro delle transazioni del broker dell'investitore e il PMC. |
| [**Rendimento alla scadenza (YTM)**](../../../instruments/asset-events/interest.md) | Tasso di sconto che equipara le cedole future e il valore di rimborso di un'obbligazione al prezzo | IRR obbligazionario prospettico; YOC è retrospettivo, basato sulle transazioni e si applica a ogni tipo di posizione. |

---

## 🔗 Correlati

- 📊 [Prezzo medio di carico](../weighted-average-cost.md) — denominatore del prezzo medio di carico
- 🖥️ [Posizioni della dashboard](../../../../user/dashboard/positions.md) — stati delle colonne, formattazione e preferenza condivisa
- 💰 [Transazioni di dividendi e interessi](../../../instruments/transaction-types/dividend-interest.md) — voci ammissibili del registro personale
- ⚙️ [Motore di portafoglio](index.md) — stato della posizione e livello delle metriche
