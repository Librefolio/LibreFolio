# 📊 Prezzo Medio di Carico (PMC)

## 💡 Cos'è il PMC?

Il **Prezzo Medio di Carico** (PMC, o *Costo Medio Ponderato*) è il costo unitario medio di un asset in un portafoglio, ponderato per la quantità acquisita a ogni prezzo.

Risponde alla domanda: _"In media, quanto ho pagato per singola unità di questo asset?"_

!!! info "Altri nomi"

    - **PMC** — Prezzo Medio di Carico (Italia)
    - **ACB** — Average Cost Basis (Canada, US)
    - **PMP** — Prix Moyen Pondéré (Francia)

## 🧮 Formula

Il PMC viene calcolato **iteratamente** man mano che ogni transazione viene elaborata in ordine cronologico:

$$
PMC_{\text{nuovo}} = \frac{PMC_{\text{attuale}} \times Q_{\text{pool}} + Costo_{\text{unit}} \times Q_{\text{tx}}}{Q_{\text{pool}} + Q_{\text{tx}}}
$$

Dove:

- $PMC_{\text{attuale}}$ = prezzo medio di carico attuale prima di questa transazione
- $Q_{\text{pool}}$ = quantità totale detenuta nel pool prima di questa transazione
- $Costo_{\text{unit}}$ = costo di acquisizione unitario della nuova transazione
- $Q_{\text{tx}}$ = quantità aggiunta dalla nuova transazione

## ⚙️ Come LibreFolio calcola il PMC

LibreFolio utilizza un **algoritmo iterativo consapevole dell'inventario** che elabora tutte le transazioni idonee per una determinata coppia (broker, asset) in ordine cronologico.

### 🏷️ Effetti delle Transazioni

Ogni transazione contribuisce al calcolo del PMC in uno di questi modi:

| Effetto | Condizione | Impatto sul PMC |
|--------|-----------|---------------|
| **Ponderato** | `qty > 0` e `unit_cost > 0` | Il PMC si sposta verso il nuovo costo di acquisizione |
| **Quantità ridotta** | `qty < 0` | Uscite al PMC attuale — PMC invariato, il pool diminuisce |
| **Diluizione** | `qty > 0` ma `unit_cost = 0` | Il pool cresce, il numeratore resta invariato → il PMC **diminuisce** |
| **Auto PMC** | `qty > 0`, `cost_basis_mode = "auto"` | Pool invariato — le unità entrano al PMC attuale |

### 📅 Ordinamento nello stesso giorno

Quando si verificano più transazioni nella stessa data:

1. **Prima le aggiunte** (qty > 0) — elaborate prima delle riduzioni
2. **Dopo le riduzioni** (qty < 0) — assicura che il pool non diventi transitoriamente negativo

### 🔻 Esaurimento del Pool

- Quando `new_qty = 0`: il PMC viene azzerato (posizione chiusa)
- Quando `new_qty < 0` (caso limite di arrotondamento): limitato a 0

## 📝 Esempi Pratici

??? example "Esempio 1: Due acquisti — il PMC sale"

    | Data | Tipo | Qty | Costo Unitario | Pool Qty | PMC |
    |------|------|-----|-----------|----------|-----|
    | 1 apr | ACQUISTO | 10 | $150 | 10 | $150.00 |
    | 15 apr | ACQUISTO | 5 | $180 | 15 | $160.00 |

    $$
    PMC = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160.00
    $$

    Il secondo acquisto a un prezzo più alto **trascina il PMC verso l'alto**.

??? example "Esempio 2: Acquisto poi vendita — PMC invariato"

    | Data | Tipo | Qty | Costo Unitario | Pool Qty | PMC |
    |------|------|-----|-----------|----------|-----|
    | 1 apr | ACQUISTO | 10 | $150 | 10 | $150.00 |
    | 15 apr | VENDITA | -5 | (al PMC) | 5 | $150.00 |

    La vendita (VENDITA) rimuove unità al PMC attuale ($150). Il PMC rimane **invariato** — diminuisce solo il pool.

??? example "Esempio 3: Acquisizione a costo zero — Diluizione"

    | Data | Tipo | Qty | Costo Unitario | Pool Qty | PMC |
    |------|------|-----|-----------|----------|-----|
    | 1 apr | ACQUISTO | 10 | $150 | 10 | $150.00 |
    | 1 mag | ADJUSTMENT | +5 | $0 | 15 | $100.00 |

    $$
    PMC = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100.00
    $$

    Il PMC viene **diluito** perché 5 unità sono entrate a costo zero (es. frazionamento, airdrop, regalo).

## 🔄 Override della Base di Costo

Per i trasferimenti e gli aggiustamenti, LibreFolio supporta un **override della base di costo**: un costo unitario specificato dall'utente che rappresenta il costo storico delle unità trasferite.

**Quando impostato (modalità manuale):**

- La transazione entra nel calcolo del PMC come una normale acquisizione ponderata
- Ciò preserva la continuità dei costi tra diversi broker (es. quando si trasferisce dal broker A al broker B)

**Quando non impostato (nessuna modalità specificata):**

- La transazione entra con `unit_cost = 0` (effetto diluizione)
- Questo è appropriato per frazionamenti, regali o airdrop in cui non esiste un prezzo d'acquisto

**Quando in modalità auto (`cost_basis_mode = "auto"`):**

- La transazione entra al **PMC attuale del pool** — il PMC rimane algebricamente invariato
- Questo è appropriato per trasferimenti o aggiustamenti in cui la base di costo dovrebbe essere ereditata dal pool del broker di origine

$$
PMC_{\text{nuovo}} = \frac{PMC \times Q_{\text{pool}} + PMC \times Q_{\text{tx}}}{Q_{\text{pool}} + Q_{\text{tx}}} = PMC
$$

!!! tip "Auto PMC nell'interfaccia utente"

    Nel modulo di transazione, l'interruttore "Auto" utilizza questa modalità. La tabella dei risultati mostra il badge dell'effetto **Auto PMC** (in italiano, **Auto WAC** in inglese), indicando che le unità sono entrate al costo attuale del pool senza alterare il PMC.

??? example "Esempio 4: Trasferimento in modalità Auto — PMC invariato"

    | Data | Tipo | Qty | Costo Unitario | Pool Qty | PMC |
    |------|------|-----|-----------|----------|-----|
    | 1 apr | ACQUISTO | 10 | $150 | 10 | $150.00 |
    | 15 apr | ACQUISTO | 5 | $180 | 15 | $160.00 |
    | 1 mag | TRANSFER (auto) | +3 | $160 (=PMC) | 18 | $160.00 |

    $$
    PMC = \frac{160 \times 15 + 160 \times 3}{15 + 3} = \frac{2880}{18} = 160.00
    $$

    Il ricevente del trasferimento in **modalità auto** eredita il PMC attuale come costo unitario. Il pool cresce ma il PMC rimane **invariato**.

## 🌍 Gestione Multi-Valuta

Quando un portafoglio contiene acquisizioni in valute diverse, LibreFolio:

1. Determina la **valuta di destinazione** (la più frequente tra le acquisizioni)
2. Converte tutti i costi unitari nella valuta di destinazione utilizzando i tassi di cambio FX storici
3. Calcola il PMC nella valuta di destinazione unificata

!!! warning "Disponibilità dei tassi FX"

    Se un tasso di cambio FX richiesto è mancante, il calcolo del PMC potrebbe essere incompleto. L'interfaccia utente avvisa della mancanza di coppie FX e fornisce azioni rapide per aggiungerle o sincronizzarle.

## 🎯 Dove viene utilizzato il PMC in LibreFolio

- **Base di costo**: $\text{CB}(a,b,t) = q(a,b,t) \times \text{PMC}(a,b,t) \times \text{fx}(\cdot)$
- **PnL Realizzato sulla VENDITA**: $\text{realizzato} = P_{\text{vendita}} - q_{\text{venduta}} \times \text{PMC}_{\text{pre-vendita}}$
- **Scomposizione della pool di liquidità**: la VENDITA restituisce $C = q_{\text{venduta}} \times \text{PMC}$ alla Pool del Capitale
- **Modulo di trasferimento**: suggerisce automaticamente il `cost_basis_override` per i trasferimenti in uscita

!!! warning "Il PMC non viene mai utilizzato per la valutazione degli asset"

    Il PMC è un costrutto contabile per la base di costo. La catena di valutazione per il valore di mercato utilizza: `MARKET_PRICE → LAST_BUY_PRICE → MISSING`. Vedi [NAV](nav.md).

## ⚙️ Implementazione: Ambito a Livello di Posizione

Il PMC è mantenuto **per posizione** $(a, b)$ — cioè per coppia (asset, broker). Lo stesso asset detenuto su due broker ha due pool PMC indipendenti.

$$
\text{PMC}(a, b_1, t) \neq \text{PMC}(a, b_2, t) \quad \text{in generale}
$$

Il motore calcola il PMC inline durante il loop giornaliero delle transazioni — non sono necessarie query separate al database. Ciò consente di ottenere un costo ammortizzato pari a O(1) per transazione anziché il costo O(N) di rieseguire la query sull'intera cronologia.

### Ordinamento delle transazioni nello stesso giorno

All'interno dello stesso giorno, **i caricamenti (acquisti) vengono elaborati prima degli scarichi (vendite)**:

$$
\text{ACQUISTO}_1, \text{ACQUISTO}_2, \ldots \quad \text{poi} \quad \text{VENDITA}_1, \text{VENDITA}_2, \ldots
$$

Questo previene quantità negative transitorie e assicura che la VENDITA legga sempre il PMC corretto che include gli ACQUISTI dello stesso giorno.
