# 📊 Costo Medio Ponderato (WAC)

## 💡 Cos'è il WAC?

Il **Costo Medio Ponderato** (WAC, dall'inglese *Weighted Average Cost*) è il costo unitario medio di un asset in un portafoglio, ponderato per la quantità acquisita a ogni prezzo.

Risponde alla domanda: _"In media, quanto ho pagato per singola unità di questo asset?"_

!!! info "Altri nomi"

    - **PMC** — Prezzo Medio di Carico (Italia)
    - **ACB** — Average Cost Basis (Canada, US)
    - **CMP** — Coût Moyen Pondéré (Francia)

## 🧮 Formula

Il WAC viene calcolato **iterativamente** man mano che ogni transazione viene elaborata in ordine cronologico:

$$
WAC_{new} = \frac{WAC_{current} \times Q_{pool} + Cost_{unit} \times Q_{tx}}{Q_{pool} + Q_{tx}}
$$

Dove:

- $WAC_{current}$ = costo medio ponderato attuale prima di questa transazione
- $Q_{pool}$ = quantità totale detenuta nel pool prima di questa transazione
- $Cost_{unit}$ = costo di acquisizione unitario della nuova transazione
- $Q_{tx}$ = quantità aggiunta dalla nuova transazione

## ⚙️ Come LibreFolio calcola il WAC

LibreFolio utilizza un **algoritmo iterativo consapevole dell'inventario** che elabora tutte le transazioni idonee per una determinata coppia (broker, asset) in ordine cronologico.

### 🏷️ Effetti delle Transazioni

Ogni transazione contribuisce al calcolo del WAC in uno di questi modi:

| Effetto | Condizione | Impatto sul WAC |
|--------|-----------|---------------|
| **Ponderato** | `qty > 0` e `unit_cost > 0` | Il WAC si sposta verso il nuovo costo di acquisizione |
| **Quantità ridotta** | `qty < 0` | Uscite al WAC attuale — WAC invariato, il pool diminuisce |
| **Diluizione** | `qty > 0` ma `unit_cost = 0` | Il pool cresce, il numeratore resta invariato → il WAC **diminuisce** |
| **Auto WAC** | `qty > 0`, `cost_basis_mode = "auto"` | Pool invariato — le unità entrano al WAC attuale |

### 📅 Ordinamento nello stesso giorno

Quando si verificano più transazioni nella stessa data:

1. **Prima le aggiunte** (qty > 0) — elaborate prima delle riduzioni
2. **Dopo le riduzioni** (qty < 0) — assicura che il pool non diventi transitoriamente negativo

### 🔻 Esaurimento del Pool

- Quando `new_qty = 0`: il WAC viene azzerato (posizione chiusa)
- Quando `new_qty < 0` (caso limite di arrotondamento): limitato a 0

## 📝 Esempi Pratici

??? example "Esempio 1: Due acquisti — il WAC sale"

    | Data | Tipo | Qty | Costo Unitario | Pool Qty | WAC |
    |------|------|-----|-----------|----------|-----|
    | 1 apr | BUY | 10 | $150 | 10 | $150.00 |
    | 15 apr | BUY | 5 | $180 | 15 | $160.00 |

    $$
    WAC = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160.00
    $$

    Il secondo acquisto a un prezzo più alto **trascina il WAC verso l'alto**.

??? example "Esempio 2: Acquisto poi vendita — WAC invariato"

    | Data | Tipo | Qty | Costo Unitario | Pool Qty | WAC |
    |------|------|-----|-----------|----------|-----|
    | 1 apr | BUY | 10 | $150 | 10 | $150.00 |
    | 15 apr | SELL | -5 | (al WAC) | 5 | $150.00 |

    La vendita (SELL) rimuove unità al WAC attuale ($150). Il WAC rimane **invariato** — diminuisce solo il pool.

??? example "Esempio 3: Acquisizione a costo zero — Diluizione"

    | Data | Tipo | Qty | Costo Unitario | Pool Qty | WAC |
    |------|------|-----|-----------|----------|-----|
    | 1 apr | BUY | 10 | $150 | 10 | $150.00 |
    | 1 mag | ADJUSTMENT | +5 | $0 | 15 | $100.00 |

    $$
    WAC = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100.00
    $$

    Il WAC viene **diluito** perché 5 unità sono entrate a costo zero (es. frazionamento, airdrop, regalo).

## 🔄 Override della Base di Costo

Per i trasferimenti e gli aggiustamenti, LibreFolio supporta un **override della base di costo**: un costo unitario specificato dall'utente che rappresenta il costo storico delle unità trasferite.

**Quando impostato (modalità manuale):**

- La transazione entra nel calcolo del WAC come una normale acquisizione ponderata
- Ciò preserva la continuità dei costi tra diversi broker (es. quando si trasferisce dal broker A al broker B)

**Quando non impostato (nessuna modalità specificata):**

- La transazione entra con `unit_cost = 0` (effetto diluizione)
- Questo è appropriato per frazionamenti, regali o airdrop in cui non esiste un prezzo d'acquisto

**Quando in modalità auto (`cost_basis_mode = "auto"`):**

- La transazione entra al **WAC attuale del pool** — il WAC rimane algebricamente invariato
- Questo è appropriato per trasferimenti o aggiustamenti in cui la base di costo dovrebbe essere ereditata dal pool del broker di origine

$$
WAC_{new} = \frac{WAC \times Q_{pool} + WAC \times Q_{tx}}{Q_{pool} + Q_{tx}} = WAC
$$

!!! tip "Auto WAC nell'interfaccia utente"

    Nel modulo di transazione, l'interruttore "Auto" utilizza questa modalità. La tabella dei risultati mostra il badge dell'effetto **Auto WAC** (o **Auto PMC** in italiano), indicando che le unità sono entrate al costo attuale del pool senza alterare il WAC.

??? example "Esempio 4: Trasferimento in modalità Auto — WAC invariato"

    | Data | Tipo | Qty | Costo Unitario | Pool Qty | WAC |
    |------|------|-----|-----------|----------|-----|
    | 1 apr | BUY | 10 | $150 | 10 | $150.00 |
    | 15 apr | BUY | 5 | $180 | 15 | $160.00 |
    | 1 mag | TRANSFER (auto) | +3 | $160 (=WAC) | 18 | $160.00 |

    $$
    WAC = \frac{160 \times 15 + 160 \times 3}{15 + 3} = \frac{2880}{18} = 160.00
    $$

    Il ricevente del trasferimento in **modalità auto** eredita il WAC attuale come costo unitario. Il pool cresce ma il WAC rimane **invariato**.

## 🌍 Gestione Multi-Valuta

Quando un portafoglio contiene acquisizioni in valute diverse, LibreFolio:

1. Determina la **valuta di destinazione** (la più frequente tra le acquisizioni)
2. Converte tutti i costi unitari nella valuta di destinazione utilizzando i tassi di cambio FX storici
3. Calcola il WAC nella valuta di destinazione unificata

!!! warning "Disponibilità dei tassi FX"

    Se un tasso di cambio FX richiesto è mancante, il calcolo del WAC potrebbe essere incompleto. L'interfaccia utente avvisa della mancanza di coppie FX e fornisce azioni rapide per aggiungerle o sincronizzarle.

## 🎯 Dove viene utilizzato il WAC in LibreFolio

- **Modulo di trasferimento**: suggerisce automaticamente il cost_basis_override per i trasferimenti in uscita
- **Calcolo P&L**: guadagni realizzati = prezzo_vendita − WAC (FIFO al runtime, WAC per la base di costo)
- **Vista Portafoglio**: prezzo medio di ingresso per ogni posizione
