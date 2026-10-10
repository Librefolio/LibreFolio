# 📊 Prezzo Medio di Carico (PMC)

## 💡 Cos'è il PMC?

Il **Prezzo Medio di Carico** (PMC) è il costo unitario medio di un asset in un portafoglio, ponderato per la quantità acquisita a ciascun prezzo.

Risponde alla domanda: _"In media, quanto ho pagato per unità per questo asset?"_

!!! info "Altri nomi"

    - **WAC** — Weighted Average Cost
    - **ACB** — Average Cost Basis (Canada, Stati Uniti)
    - **CMP** — Coût Moyen Pondéré (Francia)

## 🧮 Formula

Il PMC viene calcolato **iterativamente** man mano che ogni transazione viene elaborata cronologicamente:

$$
PMC_{new} = \frac{PMC_{current} \times Q_{pool} + Costo_{unit} \times Q_{tx}}{Q_{pool} + Q_{tx}}
$$

Dove:

- $PMC_{current}$ = costo medio ponderato corrente prima di questa transazione
- $Q_{pool}$ = quantità totale detenuta nel pool prima di questa transazione
- $Costo_{unit}$ = costo di acquisizione per unità della nuova transazione — quanto è stato effettivamente pagato, nella valuta in cui è mantenuto il PMC, convertito al tasso della data della transazione stessa (vedi [Gestione multi-valuta](#multi-currency-handling))
- $Q_{tx}$ = quantità aggiunta dalla nuova transazione

Equivalentemente, LibreFolio mantiene il costo totale del pool $C_{pool}$ accanto alla sua quantità, con $PMC = C_{pool} / Q_{pool}$: un'acquisizione aggiunge il suo costo, una riduzione di $q$ unità rimuove $C_{pool} \cdot q / Q_{pool}$.

## ⚙️ Come LibreFolio calcola il PMC

LibreFolio utilizza un **algoritmo iterativo che tiene conto dell'inventario** che elabora tutte le transazioni idonee per una data coppia (broker, asset) in ordine cronologico. Lo stesso algoritmo serve ogni schermata che mostra un costo medio: la Dashboard, la tabella delle Posizioni, l'analisi dei lotti e l'anteprima della transazione.

### 🏷️ Effetti delle transazioni

Ogni transazione contribuisce al calcolo del PMC in uno di questi modi:

| Effetto | Condizione | Impatto sul PMC |
|--------|-----------|---------------|
| **Ponderato** | `qty > 0` con un costo noto maggiore di zero | Il PMC si sposta verso il nuovo costo di acquisizione |
| **Quantità ridotta** | `qty < 0` | Esce al PMC corrente — PMC invariato, il pool si riduce |
| **Diluizione** | `qty > 0` a costo zero | Il pool cresce, il numeratore resta invariato → il PMC **diminuisce** |
| **Split** | Rettifica collegata a un evento di split | Quantità riscalata, costo totale invariato → PMC diviso per il rapporto di split |
| **Costo sconosciuto** | `qty > 0` senza costo noto: un trasferimento o una rettifica senza override del costo di carico | Il pool cresce senza costo — il PMC è **incompleto** (vedi [Override del costo di carico](#cost-basis-override)) |

### 📅 Ordinamento nello stesso giorno

Quando più transazioni avvengono nella stessa data:

1. **Prima le aggiunte** (qty > 0) — elaborate prima delle riduzioni
2. **Poi le riduzioni** (qty < 0) — assicura che il pool non diventi transitoriamente negativo

### 🔻 Esaurimento del pool

- Quando la quantità raggiunge 0, l'ultima riduzione prende l'**intero** costo rimanente, quindi il costo totale è conservato esattamente; il pool riparte da zero e un acquisto successivo apre un nuovo pool completo
- Una riduzione maggiore del pool viene limitata alla quantità disponibile

## 📝 Esempi pratici

??? example "Esempio 1: Due acquisti — il PMC sale"

    | Data | Tipo | Qtà | Costo unitario | Qtà pool | PMC |
    |------|------|-----|-----------|----------|-----|
    | 1 apr | BUY | 10 | $150,00 | 10 | $150,00 |
    | 15 apr | BUY | 5 | $180,00 | 15 | $160,00 |

    $$
    PMC = \frac{150,00 \times 10 + 180,00 \times 5}{10 + 5} = \frac{2400,00}{15} = 160,00
    $$

    Il secondo acquisto a un prezzo più alto **fa salire il PMC**.

??? example "Esempio 2: Acquisto poi vendita — PMC invariato"

    | Data | Tipo | Qtà | Costo unitario | Qtà pool | PMC |
    |------|------|-----|-----------|----------|-----|
    | 1 apr | BUY | 10 | $150,00 | 10 | $150,00 |
    | 15 apr | SELL | -5 | (al PMC) | 5 | $150,00 |

    La vendita rimuove unità al PMC corrente ($150,00). Il PMC rimane **invariato** — solo il pool si riduce.

??? example "Esempio 3: Acquisizione a costo zero — Diluizione"

    | Data | Tipo | Qtà | Costo unitario | Qtà pool | PMC |
    |------|------|-----|-----------|----------|-----|
    | 1 apr | BUY | 10 | $150,00 | 10 | $150,00 |
    | 1 mag | ADJUSTMENT | +5 | $0 | 15 | $100,00 |

    $$
    PMC = \frac{150,00 \times 10 + 0 \times 5}{10 + 5} = \frac{1500,00}{15} = 100,00
    $$

    Il PMC è **diluito** perché 5 unità sono entrate a costo zero — una rettifica il cui override del costo di carico è zero, come un airdrop. Uno split 3-a-2 collegato al suo evento di split raggiunge lo stesso $100,00 senza alcuna acquisizione: il pool mantiene i suoi $1.500,00 e li distribuisce su 15 unità.

## 🔄 Override del costo di carico {: #cost-basis-override }

Per trasferimenti e rettifiche, LibreFolio supporta un **override del costo di carico**: un costo unitario, in una valuta a tua scelta, che rappresenta il costo storico delle unità in entrata. Un trasferimento o una rettifica che aggiunge quantità ne ha bisogno: il modulo della transazione lo richiede.

**Quando impostato (modalità manuale):**

- La transazione entra nel calcolo del PMC come una normale acquisizione ponderata che costa $\text{override} \times Q_{tx}$, convertita alla data della transazione come qualsiasi acquisto
- Questo preserva la continuità del costo tra broker (ad es., quando si trasferisce dal broker A al broker B)
- Un override di **zero** è un'acquisizione gratuita: la diluizione dell'Esempio 3

**Quando manca:**

- Il costo di quelle unità è **sconosciuto**, non zero: entrano nel pool senza alcun costo e il PMC rimane incompleto finché la posizione non viene chiusa
- La Dashboard mostra il costo medio e il P&L latente di quella posizione come non disponibili e avverte del costo di carico mancante; l'anteprima della transazione conta le unità a zero (diluizione)

**Quando la modalità auto (`cost_basis_mode = "auto"`):**

- LibreFolio calcola il PMC della posizione di origine — per un trasferimento, la posizione del broker mittente quando le unità sono partite (la data di trasferimento in uscita), prima dell'operazione in uscita; per una rettifica, la posizione stessa alla data della transazione, senza questa transazione — e lo memorizza come override
- Da quel momento la transazione è un'ordinaria acquisizione ponderata a quel costo unitario. Per una rettifica sulla stessa posizione, il PMC rimane quindi algebricamente invariato, nella valuta in cui è stato calcolato:

$$
PMC_{new} = \frac{PMC \times Q_{pool} + PMC \times Q_{tx}}{Q_{pool} + Q_{tx}} = PMC
$$

!!! tip "Modalità auto nell'UI"

    Nel modulo della transazione, l'interruttore **Auto** calcola il valore quando confermi: l'anteprima mostra il PMC suggerito e le transazioni da cui proviene, ciascuna con il suo effetto.

??? example "Esempio 4: Trasferimento in modalità auto — il costo segue le unità"

    Il broker A detiene il pool dell'Esempio 1 e invia 3 unità al broker B, che non ne deteneva alcuna:

    | Broker | Data | Tipo | Qtà | Costo unitario | Qtà pool | PMC |
    |--------|------|------|-----|-----------|----------|-----|
    | A | 1 apr | BUY | 10 | $150,00 | 10 | $150,00 |
    | A | 15 apr | BUY | 5 | $180,00 | 15 | $160,00 |
    | A | 1 mag | TRANSFER out | −3 | (al PMC) | 12 | $160,00 |
    | B | 1 mag | TRANSFER in (auto) | +3 | $160,00 (PMC di A) | 3 | $160,00 |

    In **modalità auto** il lato ricevente prende il PMC del mittente come proprio override del costo di carico: il broker B parte dalla media del broker A, e i $480,00 di costo si spostano con le 3 unità.

## 🌍 Gestione multi-valuta {: #multi-currency-handling }

Il PMC è mantenuto in una singola valuta, la **valuta obiettivo** $T$, e ogni acquisizione vi entra al suo **costo storico**: l'importo effettivamente pagato, convertito al tasso della data propria dell'acquisizione $d_i$:

$$
c_i^{T} = P_i \cdot \mathrm{fx}\bigl(\mathrm{ccy}(P_i),\, T,\, d_i\bigr), \qquad \mathrm{fx}(T, T, d) = 1
$$

Qui $P_i$ è il denaro pagato per un BUY, nella sua valuta di cassa, oppure $\text{override} \times Q_{tx}$ nella valuta dell'override per un trasferimento o una rettifica. Un importo già in $T$ non necessita di alcun tasso; altrimenti, quando la data esatta non ha un tasso, viene utilizzato l'ultimo tasso precedente.

Il costo di carico di una posizione è quindi

$$
\mathrm{CB}(a,b,t) = q(a,b,t) \times \mathrm{PMC}^{T}(a,b,t)
$$

con **nessun tasso di cambio a $t$**: è quanto è stato pagato, e non cambia quando i tassi di cambio variano. Per un asset prezzato in un'altra valuta, l'effetto del tasso di cambio risiede quindi nella plusvalenza/minusvalenza latente — valore di mercato al tasso del giorno meno costo storico — che la Dashboard scorpora (vedi [P&L periodo](portfolio-engine/period-pnl.md#unrealized-change-by-currency)).

La valuta obiettivo dipende da dove viene mostrato il PMC:

| Dove | Valuta obiettivo $T$ |
|-------|---------------------|
| Dashboard, tabella Posizioni, vendite realizzate, Rendimento sul costo | La valuta di visualizzazione (report) |
| Righe PMC dell'analisi lotti | La valuta dell'analisi |
| Anteprima transazione, costo di carico automatico, serie PMC (`POST /portfolio/wac`) | La valuta scelta nell'anteprima, altrimenti la valuta dell'**ultima acquisizione** |
| Pianificatore PAC | La valuta del pianificatore |

La valuta dell'ultima acquisizione è la valuta pagata dalla transazione più recente che ha aggiunto quantità — una regola deterministica; in caso di parità, vince la prima registrata. Uno split, o un'acquisizione di costo sconosciuto, fa fallback sulla valuta dell'asset stesso.

??? example "Esempio 5: Un asset in dollari acquistato con euro, valuta di visualizzazione EUR"

    | Data | Tipo | Qtà | Pagato | Tasso USD→EUR | Costo in EUR |
    |------|------|-----|------|--------------|-------------|
    | 1 apr | BUY | 10 | €400,00 | — (pagato in EUR) | €400,00 |
    | 1 mag | BUY | 5 | 300,00 USD | 0,90 | €270,00 |

    $$
    PMC^{EUR} = \frac{400,00 + 270,00}{10 + 5} = \frac{670,00}{15} \approx 44,67 \text{ EUR}
    $$

    Il primo acquisto non necessita di un tasso: il suo costo è esattamente i €400,00 pagati. Il costo di carico della posizione rimane €670,00 qualunque cosa faccia il dollaro in seguito; un dollaro più debole abbassa il valore di mercato in euro e si manifesta come una perdita latente.

!!! warning "Disponibilità del tasso FX"

    Quando non esiste un tasso alla data di acquisizione o prima, LibreFolio non conta mai quel costo come zero. Le unità entrano nel pool senza il loro costo e il PMC viene contrassegnato come incompleto: l'anteprima della transazione non mostra alcun PMC ed elenca la coppia mancante con le sue date, la Dashboard mostra il costo medio e il P&L latente della posizione come non disponibili, e l'analisi dei lotti esclude quei giorni dalle sue righe PMC. L'UI avverte delle coppie FX mancanti e fornisce azioni rapide per aggiungerle o sincronizzarle.

## 🎯 Dove viene usato il PMC in LibreFolio

- **Costo di carico**: $\mathrm{CB}(a,b,t) = q(a,b,t) \times \mathrm{PMC}^{T}(a,b,t)$, storico, senza conversione a $t$
- **P&L realizzato su SELL**: $\text{realizzato} = P_{\text{vendita}} - q_{\text{vendute}} \times \text{PMC}^{T}_{\text{pre-vendita}}$, con i proventi $P_{\text{vendita}}$ convertiti alla data di vendita e le unità vendute che escono al loro costo storico
- **Scomposizione del pool di cassa**: SELL restituisce $C = q_{\text{vendute}} \times \text{PMC}^{T}_{\text{pre-vendita}}$ al Pool di capitale
- **Rendimento sul costo**: il prezzo medio di acquisto del denominatore del [Rendimento sul costo](portfolio-engine/yield-on-cost.md)
- **Modulo di trasferimento**: suggerisce automaticamente il cost_basis_override del lato ricevente dal PMC della posizione mittente

!!! warning "Il PMC non viene mai usato per la valutazione degli asset"

    Il PMC è un costrutto contabile per il costo di carico. Il valore di mercato utilizza i livelli unificati del resolver: `MARKET → TRADE_AVG → CARRIED → MISSING`, esposti alle righe di portafoglio come `MARKET_PRICE`, `LAST_TRADE_PRICE` o `MISSING`. Vedi [Risoluzione del prezzo](portfolio-engine/price-resolution.md).

## ⚙️ Implementazione: ambito a livello di posizione

Il PMC è mantenuto **per posizione** $(a, b)$ — cioè per coppia (asset, broker). Lo stesso asset detenuto su due broker ha due pool PMC indipendenti.

$$
\text{PMC}(a, b_1, t) \neq \text{PMC}(a, b_2, t) \quad \text{in generale}
$$

Il costo medio di ogni posizione in un report viene calcolato **una volta, prima del replay giornaliero**, con tutte le conversioni necessarie raggruppate in un'unica richiesta al servizio FX; il replay giornaliero segue poi passo dopo passo il pool di ciascuna posizione invece di ricalcolarlo, e non esegue mai autonomamente la conversione di un costo.

### 📅 Ordinamento delle transazioni nello stesso giorno

All'interno della stessa data, **le aggiunte vengono elaborate prima delle riduzioni**:

$$
\text{BUY}_1, \text{BUY}_2, \ldots \quad \text{poi} \quad \text{SELL}_1, \text{SELL}_2, \ldots
$$

Ciò previene quantità negative transitorie e assicura che SELL legga sempre il PMC corretto che include i BUY dello stesso giorno.

## 🔗 Correlati

- 🔬 **[Analisi lotti FIFO](fifo-engine/fifo-lot-analysis.md)** — Complemento per lotto: traccia ogni lotto di acquisizione individualmente invece di fonderli in un'unica media
- 🔁 **[Acquisto & Vendita](../../instruments/transaction-types/buy-sell.md)** — Transazioni che alimentano il pool PMC
- 📈 **[NAV / Patrimonio netto](portfolio-engine/nav.md)** — Come il valore contabile basato sul PMC differisce dal NAV a prezzo di mercato
- 📖 **[Valore contabile](portfolio-engine/book-value.md)** — Costo di carico aperto: la somma dei costi storici
- ⚖️ **[PMC & Costo di carico (Manuale sviluppatore)](../../../developer/backend/transactions/wac.md)** — L'unica implementazione del costo medio e i suoi chiamanti
