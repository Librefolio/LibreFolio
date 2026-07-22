# 🔬 Analisi dei Lotti FIFO

L'analisi dei lotti FIFO è il complemento **per lotto** del [Prezzo Medio di Carico (PMC)](../weighted-average-cost.md).

Il PMC risponde: _"Qual è il mio prezzo medio di carico per questa posizione?"_ L'analisi dei lotti FIFO risponde a una domanda diversa: _"Come sta andando ogni singolo lotto di acquisto nel tempo?"_

Invece di fondere tutti gli acquisti in un unico pool, LibreFolio traccia ogni lotto attraverso il suo ciclo di vita — **aperto**, **parzialmente chiuso**, **completamente chiuso** — e abbina le vendite in ordine **FIFO** (first in, first out).

!!! info "Complemento, non sostituzione"

    Il PMC è aggregato e a livello di posizione. L'analisi dei lotti FIFO è granulare e a livello di lotto. Entrambe le viste sono utili: una per il prezzo medio di carico, l'altra per l'attribuzione economica lotto per lotto.

---

## 💡 Cos'è l'Analisi dei Lotti FIFO?

Un **lotto** è un gruppo di acquisto: ad esempio, un ACQUISTO di 100 azioni, o un trasferimento in entrata che preserva il costo storico.

Quando si verifica una VENDITA, i lotti più vecchi ancora aperti vengono chiusi per primi. Questo crea una storia lotto per lotto:

- quanto di ogni lotto è ancora aperto
- quanto è già stato venduto
- quanto ricavo di vendita quel lotto ha generato
- quanto reddito è stato guadagnato mentre quel lotto era detenuto
- quanto rendimento è derivato dalla variazione di prezzo rispetto al reddito da capitale

Questo rende l'analisi dei lotti FIFO particolarmente utile quando due posizioni nello stesso asset sono state acquistate a prezzi o date molto diverse.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-gantt-chart" alt="Cronologia Vita e Custodia Lotti — ogni barra è un lotto, colorata per broker custode, spessore proporzionale alla quantità detenuta">
</div>

La cronologia **Vita e Custodia Lotti** sopra rende visibile il ciclo di vita: ogni barra è un lotto, colorata in base al broker che lo detiene attualmente, con spessore proporzionale alla quantità ancora detenuta in quel segmento. Una barra che termina a metà grafico è un lotto completamente chiuso; una barra che arriva a "oggi" è ancora aperta.

---

## 🧮 Rendimento Non Realizzato per Lotto

Il **Rendimento Non Realizzato** isola il movimento **solo di prezzo** di un lotto rispetto al suo prezzo di riferimento di apertura.

$$
\text{RendimentoRelativo} = \frac{\text{PrezzoMercato}}{\text{PrezzoDiRiferimento}} - 1
$$

In pratica:

- se esiste una quotazione di mercato alla data di apertura del lotto, quella quotazione di apertura diventa `prezzo_di_riferimento`
- se il lotto è stato aperto prima della prima quotazione di mercato disponibile, il sistema utilizza come riferimento il costo di apertura del lotto stesso, scalato alle unità della quotazione di mercato

Questa metrica esclude dividendi, interessi e ricavi di vendita realizzati. Risponde: _"Quanto si è mosso il prezzo di mercato da quando questo lotto è stato aperto?"_

!!! tip "Fallback del prezzo di riferimento"

    Quando non esiste una quotazione di mercato del giorno di apertura, LibreFolio utilizza il prezzo di acquisto del lotto come base di riferimento, scalato alla convenzione di quotazione dell'asset. Questo evita rendimenti percentuali fuorvianti su strumenti quotati per 100 unità nominali.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-wac-chart" alt="Grafico PMC / Prezzo di Mercato — una bolla per lotto, colorata per broker di apertura, dimensionata per valore di apertura, tracciata sulla linea del prezzo di mercato">
</div>

Il grafico **PMC / Prezzo di Mercato** traccia ogni lotto come una bolla sulla linea del prezzo di mercato: il colore della bolla indica il broker presso cui il lotto è stato aperto, la dimensione della bolla scala con il valore di apertura del lotto. Un lotto valutato solo al costo (senza prezzo di mercato in tempo reale) viene disegnato con un contorno tratteggiato.

---

## 💰 Rendimento Totale per Lotto

Il **Rendimento Totale** è più ampio del Rendimento Non Realizzato. Include il valore corrente di mercato del lotto, eventuali ricavi di vendita già realizzati da quel lotto e qualsiasi reddito allocato ricevuto mentre il lotto era detenuto.

La matematica dei lotti di LibreFolio utilizza questi elementi costitutivi esatti:

$$
\text{ValoreIniziale} = \text{CostoOriginale}
$$

$$
\text{Ricavi}(t) = \sum \text{Ricavi di Chiusura} \text{ fino a } t
$$

$$
\text{ValoreTotale}(t) = \text{ValoreCorrente}(t) + \text{Ricavi}(t)
$$

$$
\text{PnL}(t) = \text{ValoreTotale}(t) - \text{CostoOriginale}
$$

$$
\text{PnLMercato} = \text{PnL} - \text{PnLRealizzato}
$$

$$
\text{PnLRealizzato} = \sum \text{PnL Realizzato di Chiusura}
$$

$$
\text{RedditoAsset} = \sum_t \text{Reddito}_i(t)
$$

$$
\text{PnL Totale} = \text{PnLMercato} + \text{PnLRealizzato} + \text{RedditoAsset}
$$

Per il riepilogo scalare del lotto, la percentuale di rendimento è:

$$
\text{RendimentoTotale} = \frac{\text{PnL Totale}}{\text{ValoreIniziale}}
$$

Per la cronologia dei rendimenti nel tempo, LibreFolio utilizza:

$$
\text{RendimentoTotale}(t) = \frac{\text{ValoreTotale}(t) + \text{Reddito}(t)}{\text{CostoOriginale}} - 1
$$

Questo risponde: _"Qual è il rendimento economico completo di questo lotto, inclusi sia il movimento di prezzo che il rendimento da cassa?"_

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" alt="Grafico di confronto Valore/Rendimento in modalità Rendimento — rendimento percentuale per lotto dalla data di apertura di ciascun lotto">
</div>

Il grafico di confronto **Valore/Rendimento**, passato alla modalità **Rendimento**, traccia esattamente questa percentuale — una linea per lotto, ciascuna misurata dalla propria data di apertura, sull'insieme di lotti attualmente selezionato.

---

## ⚙️ Ridimensionamento qbq

Alcuni strumenti sono quotati **per quantità base**, non per singola unità. LibreFolio chiama questa quantità base `qbq` (`quote_base_quantity`).

- Per la maggior parte delle azioni, `qbq = 1`
- Per molte obbligazioni, `qbq = 100`

La regola di valutazione esatta è:

$$
\text{ValoreDetenuto}(qta, prezzo, qbq) = \left(\frac{qta}{qbq}\right)\cdot prezzo
$$

$$
\text{ValoreCorrente}(t) = \left(\frac{\text{QuantitàAperta}(t)}{qbq}\right)\cdot \text{PrezzoMercato}(t)
$$

!!! warning "Il ridimensionamento qbq è importante"

    Supponiamo che un'obbligazione abbia una quantità nominale di 1.000 e sia quotata a **101,50 per 100 nominali**.

    - `qbq = 100`
    - quantità lotto = `1.000`
    - valore di mercato = `(1.000 / 100) × 101,50 = 1.015,00`

    Se confronti direttamente `101,50` con una base di costo per singola unità come `0,992`, ottieni risultati privi di senso perché i due numeri vivono su scale diverse.

    Il confronto corretto ridimensiona il costo del lotto sull'asse della quotazione di mercato:

    $$
    0,992 \times 100 = 99,20
    $$

    Quindi il confronto di prezzo significativo è **101,50 vs 99,20**, non **101,50 vs 0,992**.

Senza questo ridimensionamento, i rendimenti e le valutazioni delle obbligazioni possono essere errati di ordini di grandezza.

---

## 🛟 Stimato al Costo

Se non è disponibile un prezzo di mercato in tempo reale per un asset, LibreFolio **non** interrompe l'analisi. Invece, valuta temporaneamente la parte ancora aperta del lotto al costo:

$$
\text{ValoreCorrente} = \text{ValoreIniziale}\cdot \frac{\text{QuantitàAperta}}{\text{QuantitàOriginale}}
$$

$$
\text{PnLMercato} = 0
$$

Implicazione pratica:

- il lotto mostra ancora il valore residuo
- i ricavi già realizzati rimangono ancora visibili
- i dividendi o gli interessi allocati rimangono ancora visibili
- **la volatilità non realizzata è temporaneamente sottostimata**

!!! info "Interpretazione"

    La stima al costo è un fallback operativo conservativo. Significa: _"Sappiamo quanto hai pagato, ma non sappiamo attualmente quanto pagherebbe il mercato."_

---

## 💸 Allocazione del Reddito tra i Lotti {: #income-allocation-across-lots }

I dividendi e gli interessi collegati a un asset vengono allocati **pro-rata tra i lotti in acquisto ammissibili
al giorno precedente la data del reddito (D-1)**, e solo tra i lotti detenuti **presso il broker pagatore**.

Regola di allocazione esatta:

$$
w_i(D) = \frac{\text{QtàAmmissibile}_i(D)}{\sum_j \text{QtàAmmissibile}_j(D)}, \qquad
\text{QtàAmmissibile}_i(D) = \text{QtàAperta}_i(D-1)
$$

$$
\text{Reddito}_i = \text{Converti}(I, val, D)\cdot w_i(D)
$$

Dove:

- $I$ = importo del reddito ricevuto alla data $D$
- $\text{Converti}(I, val, D)$ = reddito convertito nella valuta di destinazione alla data $D$
- $\text{QtàAmmissibile}_i(D)$ = quantità del lotto $i$ aperta presso il **broker pagatore** al $D-1$ (la quantità
  in trasferimento in uscita da quel broker conta comunque come originata lì)
- solo i lotti in acquisto partecipano al denominatore

La regola **D-1** mantiene puntuale la data di rilevazione: un acquisto effettuato *nel* giorno del reddito non
matura quella distribuzione, e nemmeno un lotto venduto il giorno precedente. I lotti ammissibili più grandi
ricevono una quota maggiore; i lotti detenuti presso altri broker, o non ancora (o non più) ammissibili, non
ricevono nulla.

!!! warning "Modificato in FIFO v5"

    Le versioni precedenti utilizzavano la data del reddito stessa con **tutti** i broker ($\text{QtàAperta}_i(t)$
    su ogni lotto). Il motore attuale utilizza l'ammissibilità al D-1 limitata al broker pagatore. Se nessun lotto
    è ammissibile, il reddito viene mantenuto come **reddito orfano a livello di asset** (mai perso, mai assegnato
    al lotto sbagliato).

!!! tip "Regola di conservazione"

    Gli importi dei lotti allocati sommati restituiscono esattamente il totale dell'evento di reddito convertito. Il reddito viene distribuito, non creato.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-custody-modal" alt="Modale dettaglio lotto — la riga Reddito Asset mostra il dividendo/interesse pro-rata allocato a questo lotto specifico, insieme al badge Stimato al Costo quando non è disponibile un prezzo di mercato in tempo reale">
</div>

La riga **Reddito Asset** della modale di dettaglio del lotto è esattamente $\text{Reddito}_i$ della formula sopra — la quota pro-rata che questo lotto specifico ha ricevuto. Quando il lotto non ha un prezzo di mercato in tempo reale, la stessa modale mostra anche il badge **Stimato al Costo** della sezione precedente.

---

## 💸 Costi e Metriche Nette {: #costs-and-net-metrics }

Le `FEE` e `TAX` collegate a un asset vengono allocate ai lotti tramite una **scala deterministica di abbinamento
alle operazioni**, per poi essere sottratte e produrre le cifre **nette** insieme a quelle lorde.

### Allocazione deterministica dei costi

Un pool di costo (stesso broker, stesso giorno, stesso tipo) viene abbinato al primo target non vuoto in questo ordine:

| Costo | Ordine di abbinamento |
|------|----------------|
| `FEE` | operazioni dello stesso giorno → operazioni del giorno precedente → posizioni aperte → orfano a livello di asset |
| `TAX` | reddito dello stesso giorno → operazioni dello stesso giorno → reddito del giorno precedente → operazioni del giorno precedente → posizioni aperte → orfano a livello di asset |

All'interno di un'operazione abbinata, il costo **passa esattamente ai lotti toccati da quell'operazione** — il
costo di un ACQUISTO finisce sul lotto che ha aperto, il costo di una VENDITA finisce sui lotti consumati in FIFO
— quindi l'attribuzione del costo non contraddice mai l'abbinamento FIFO stesso. Gli importi vengono convertiti
nella valuta di destinazione e memorizzati come magnitudini positive.

!!! tip "Conservazione"

    Per pool, $\sum_i \text{Costo}_i + \text{Orfano} = \text{Converti}(\text{pool}, val, D)$. Un costo che non
    trova alcun lotto ammissibile (es. una commissione registrata dopo che la posizione è stata completamente
    chiusa) diventa **costo orfano a livello di asset** invece di essere scartato o forzato su un lotto non
    correlato.

### Lordo vs netto

Con i costi attribuiti per lotto, LibreFolio riporta sia la performance lorda che quella netta:

$$
\text{PnL Totale Netto}_i = \text{PnL Totale}_i - \text{Commissioni}_i - \text{Tasse}_i
$$

$$
\text{RendimentoTotaleNetto}_i = \frac{\text{PnL Totale Netto}_i}{\text{ValoreIniziale}_i}
$$

dove $\text{PnL Totale}_i$ **include** già il reddito (PnL di mercato + PnL realizzato + reddito da asset). La
serie storica del valore per lotto riporta invece un PnL netto *solo di capitale*,
$\text{pnl}_i - \text{Commissioni}_i - \text{Tasse}_i$, che **esclude** il reddito — ogni riga netta rispecchia
la propria controparte lorda meno i costi.

!!! example "Numeri esemplificativi"

    ACQUISTO 10×100, VENDITA 4×120, prezzo corrente 110, dividendo 50, commissioni 8, tasse 5:
    P&L Totale Lordo $= 60 + 80 + 50 = 190$; P&L Totale Netto $= 190 - 13 = 177$; su un valore iniziale di 1.000
    corrisponde a un rendimento totale del **19%** lordo contro il **17,7%** netto.

I costi con `asset_id = null` **non** fanno parte di questa vista a livello di lotto — sono a livello di
portafoglio e gestiti dal [Portfolio Engine](../portfolio-engine/roi.md). Vedi
[Commissioni e Tasse](../../../instruments/transaction-types/fee.md) per la teoria a livello di strumento.

---

## 📝 Esempio Pratico

??? example "Esempio: due lotti, un dividendo, un prezzo di mercato"

    Supponiamo stessa azione, stessa valuta, `qbq = 1`.

    | Data | Evento | Q.tà Aperta Lotto A | Q.tà Aperta Lotto B | Note |
    |------|-------|----------------|----------------|-------|
    | 2 Gen | ACQUISTO 100 @ $10 | 100 | 0 | Il lotto A si apre con costo originale $1.000 |
    | 10 Feb | ACQUISTO 50 @ $14 | 100 | 50 | Il lotto B si apre con costo originale $700 |
    | 15 Mar | DIVIDENDO $30 | 100 | 50 | Entrambi i lotti sono ancora aperti |
    | 1 Apr | Prezzo mercato = $16 | 100 | 50 | Valuta entrambi i lotti |

    **Passo 1 — Alloca dividendo pro-rata**

    $$
    w_A = \frac{100}{100 + 50} = \frac{2}{3}
    \qquad
    w_B = \frac{50}{100 + 50} = \frac{1}{3}
    $$

    $$
    \text{Reddito}_A = 30 \times \frac{2}{3} = 20
    \qquad
    \text{Reddito}_B = 30 \times \frac{1}{3} = 10
    $$

    **Passo 2 — Rendimento Non Realizzato per ogni lotto**

    $$
    \text{RendimentoRelativo}_A = \frac{16}{10} - 1 = 60,00\%
    $$

    $$
    \text{RendimentoRelativo}_B = \frac{16}{14} - 1 \approx 14,29\%
    $$

    **Passo 3 — Valore di mercato e Rendimento Totale**

    $$
    \text{ValoreCorrente}_A = 100 \times 16 = 1.600
    \qquad
    \text{ValoreCorrente}_B = 50 \times 16 = 800
    $$

    Poiché nessuna azione è stata ancora venduta, ricavi e P&L realizzato sono entrambi zero.

    $$
    \text{PnL Totale}_A = (1.600 - 1.000) + 20 = 620
    $$

    $$
    \text{RendimentoTotale}_A = \frac{620}{1.000} = 62,00\%
    $$

    $$
    \text{PnL Totale}_B = (800 - 700) + 10 = 110
    $$

    $$
    \text{RendimentoTotale}_B = \frac{110}{700} \approx 15,71\%
    $$

    **Passo 4 — Rendimento aggregato tra i lotti visualizzati**

    $$
    \text{RendimentoAggregato} = \frac{620 + 110}{1.000 + 700} = \frac{730}{1.700} \approx 42,94\%
    $$

    Anche se entrambi i lotti appartengono allo stesso asset, i loro rendimenti differiscono perché sono stati aperti a prezzi diversi.

---

## 📚 Dai Lotti alle Metriche Aggregate

I rendimenti a livello di lotto possono essere aggregati in una serie di rendimenti aggregati, ma **le percentuali non devono essere sommate direttamente**.

LibreFolio utilizza questa regola aggregata esatta tra i lotti visualizzati:

$$
\text{PnLAggregato}(t) = \sum_i \left(\text{PnL}_i(t) + \text{Reddito}_i(t)\right)
$$

$$
\text{ValoreInizialeAggregato}(t) = \sum_i \text{CostoOriginale}_i
$$

$$
\text{RendimentoAggregato}(t) = \frac{\text{PnLAggregato}(t)}{\text{ValoreInizialeAggregato}(t)}
$$

Questa vista a livello di lotto aiuta a spiegare **da dove** proviene il rendimento. Metriche di livello superiore come [ROI](../portfolio-engine/roi.md) e [TWRR](../portfolio-engine/twrr.md) rispondono a domande di portafoglio più ampie:

- **ROI** si concentra sul guadagno relativo al capitale investito
- **TWRR** neutralizza la tempistica dei flussi di cassa esterni
- L'analisi dei lotti FIFO spiega il contributo e il percorso **all'interno** di una posizione

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-table" alt="Tabella Lotti Unificata — una riga per lotto con data di apertura, rendimento totale, valore corrente, custodia e stato, le esatte righe per lotto su cui le formule aggregate sopra eseguono la somma">
</div>

La **Tabella Lotti Unificata** elenca esattamente le righe per lotto $i$ su cui le formule aggregate sopra eseguono la somma — data di apertura, rendimento totale, valore corrente, custodia e stato, tutte filtrabili allo stesso insieme di lotti visibili utilizzato dai grafici.

---

## 🔗 Correlati

- 📊 **[Prezzo Medio di Carico (PMC)](../weighted-average-cost.md)** — vista del costo medio di carico
- 🔁 **[Acquisto & Vendita](../../../instruments/transaction-types/buy-sell.md#fifo-matching)** — breve panoramica sull'abbinamento FIFO
- 💸 **[Dividendo & Interesse](../../../instruments/transaction-types/dividend-interest.md)** — fonte degli eventi di reddito legati all'asset
- 💰 **[Tassazione](../../../fundamentals/taxation.md)** — contesto delle plusvalenze e dell'abbinamento dei lotti
- ⚙️ **[Servizio di Analisi dei Lotti](../../../../developer/backend/transactions/lots_analysis_service.md)** — approfondimento sull'implementazione per sviluppatori
