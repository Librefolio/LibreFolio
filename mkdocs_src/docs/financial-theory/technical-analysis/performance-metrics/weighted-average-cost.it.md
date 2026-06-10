# 📊 Prezzo Medio di Carico (WAC)

## 💡 Cos'è il WAC?

Il **Weighted Average Cost** (WAC), o Prezzo Medio di Carico, è il costo unitario medio di un asset in un portafoglio, ponderato per la quantità acquisita a ciascun prezzo.

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

- $WAC_{current}$ = prezzo medio di carico attuale prima di questa transazione
- $Q_{pool}$ = quantità totale detenuta nel pool prima di questa transazione
- $Cost_{unit}$ = costo di acquisizione per unità della nuova transazione
- $Q_{tx}$ = quantità aggiunta dalla nuova transazione

## ⚙️ Come LibreFolio calcola il WAC

LibreFolio utilizza un **algoritmo iterativo consapevole dell'inventario** che elabora tutte le transazioni idonee per una data coppia (broker, asset) in ordine cronologico.

### 🏷️ Effetti delle transazioni

Ogni transazione contribuisce al calcolo del WAC in uno di questi modi:

| Effetto | Condizione | Impatto sul WAC |
|--------|-----------|---------------|
| **Ponderato** | `qty > 0` e `unit_cost > 0` | Il WAC si sposta verso il nuovo costo di acquisizione |
| **Quantità ridotta** | `qty < 0` | Uscita al WAC attuale — WAC invariato, il pool diminuisce |
| **Diluizione** | `qty > 0` ma `unit_cost = 0` | Il pool cresce, il numeratore resta invariato → il WAC **diminuisce** |
| **Auto WAC** | `qty > 0`, `cost_basis_mode = "auto"` | Il pool resta invariato — le unità entrano al WAC attuale |

### 📅 Ordinamento nello stesso giorno

Quando avvengono più transazioni nella stessa data:

1. **Prima le aggiunte** (qty > 0) — elaborate prima delle riduzioni
2. **Poi le riduzioni** (qty < 0) — assicura che il pool non diventi transitoriamente negativo

### 🔻 Esaurimento del pool

- Quando `new_qty = 0`: il WAC viene resettato a 0 (posizione chiusa)
- Quando `new_qty < 0` (caso limite di arrotondamento): bloccato a 0

## 📝 Esempi Pratici

??? example "Esempio 1: Due acquisti — il WAC sale"

    | Data | Tipo | Qty | Costo Unitario | Qty Pool | WAC |
    |------|------|-----|-----------|----------|-----|
    | 1 Apr | BUY | 10 | $150 | 10 | $150.00 |
    | 15 Apr | BUY | 5 | $180 | 15 | $160.00 |

    $$
    WAC = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160.00
    $$

    Il secondo acquisto a un prezzo più alto **spinge il WAC verso l'alto**.

??? example "Esempio 2: Acquisto poi Vendita — WAC invariato"

    | Data | Tipo | Qty | Costo Unitario | Qty Pool | WAC |
    |------|------|-----|-----------|----------|-----|
    | 1 Apr | BUY | 10 | $150 | 10 | $150.00 |
    | 15 Apr | SELL | -5 | (al WAC) | 5 | $150.00 |

    La vendita (SELL) rimuove unità al WAC attuale ($150). Il WAC rimane **invariato** — diminuisce solo la quantità nel pool.

??? example "Esempio 3: Acquisizione a costo zero — Diluizione"

    | Data | Tipo | Qty | Costo Unitario | Qty Pool | WAC |
    |------|------|-----|-----------|----------|-----|
    | 1 Apr | BUY | 10 | $150 | 10 | $150.00 |
    | 1 Mag | ADJUSTMENT | +5 | $0 | 15 | $100.00 |

    $$
    WAC = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100.00
    $$

    Il WAC viene **diluito** perché 5 unità sono entrate a costo zero (es. frazionamento azionario, airdrop, regalo).

## 🔄 Override del costo di carico

Per trasferimenti e aggiustamenti, LibreFolio supporta un **override del costo di carico**: un costo unitario specificato dall'utente che rappresenta il costo storico delle unità trasferite.

**Quando impostato (modalità manuale):**

- La transazione entra nel calcolo del WAC come una normale acquisizione ponderata
- Questo preserva la continuità dei costi tra diversi broker (es. quando si trasferisce dal broker A al broker B)

**Quando non impostato (nessuna modalità specificata):**

- La transazione entra con `unit_cost = 0` (effetto diluizione)
- Questo è appropriato per frazionamenti azionari, regali o airdrop dove non esiste un prezzo di acquisto

**In modalità auto (`cost_basis_mode = "auto"`):**

- La transazione entra al **WAC attuale del pool** — il WAC rimane algebricamente invariato
- Questo è appropriato per trasferimenti o aggiustamenti in cui il costo di carico deve essere ereditato dal pool del broker di origine

$$
WAC_{new} = \frac{WAC \times Q_{pool} + WAC \times Q_{tx}}{Q_{pool} + Q_{tx}} = WAC
$$

!!! tip "Auto WAC nell'interfaccia utente"

    Nel modulo della transazione, l'interruttore "Auto" utilizza questa modalità. La tabella dei risultati mostra il badge dell'effetto **Auto WAC** (o **Auto PMC** in italiano), indicando che le unità sono entrate al costo attuale del pool senza alterare il WAC.

??? example "Esempio 4: Trasferimento in modalità Auto — WAC invariato"

    | Data | Tipo | Qty | Costo Unitario | Qty Pool | WAC |
    |------|------|-----|-----------|----------|-----|
    | 1 Apr | BUY | 10 | $150 | 10 | $150.00 |
    | 15 Apr | BUY | 5 | $180 | 15 | $160.00 |
    | 1 Mag | TRANSFER (auto) | +3 | $160 (=WAC) | 18 | $160.00 |

    $$
    WAC = \frac{160 \times 15 + 160 \times 3}{15 + 3} = \frac{2880}{18} = 160.00
    $$

    Il ricevente del trasferimento in **modalità auto** eredita il WAC attuale come suo costo unitario. Il pool cresce ma il WAC rimane **invariato**.

## 🌍 Gestione Multi-Valuta

Quando un portafoglio contiene acquisizioni in diverse valute, LibreFolio:

1. Determina la **valuta di destinazione** (la più frequente tra le acquisizioni)
2. Converte tutti i costi unitari nella valuta di destinazione utilizzando i tassi di cambio storici
3. Calcola il WAC nella valuta di destinazione unificata

!!! warning "Disponibilità tassi FX"

    Se un tasso FX richiesto è mancante, il calcolo del WAC potrebbe essere incompleto. L'interfaccia utente avvisa in caso di coppie FX mancanti e fornisce azioni rapide per aggiungerle o sincronizzarle.

## 🎯 Dove viene utilizzato il WAC in LibreFolio

- **Modulo di trasferimento**: suggerisce automaticamente il `cost_basis_override` per i trasferimenti in uscita
- **Calcolo P&L**: guadagni realizzati = prezzo\_vendita − WAC (FIFO all'esecuzione, WAC per il costo di carico)
- **Vista portafoglio**: prezzo medio di ingresso per ogni posizione
