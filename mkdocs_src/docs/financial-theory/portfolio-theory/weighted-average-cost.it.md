# 📊 Costo Medio Ponderato (WAC)

## 💡 Cos'è il WAC?

Il **Costo Medio Ponderato** (WAC - *Weighted Average Cost*) è il costo unitario medio di un asset in un portafoglio, ponderato per la quantità acquisita a ogni prezzo.

Risponde alla domanda: _"In media, quanto ho pagato per singola unità di questo asset?"_

!!! info "Other names"

    - **PMC** — Prezzo Medio di Carico (Italy)
    - **ACB** — Average Cost Basis (Canada, US)
    - **CMP** — Coût Moyen Pondéré (France)

## 🧮 Formula

Il WAC viene calcolato **iterativamente** man mano che ogni transazione viene elaborata in ordine cronologico:

$$
WAC_{new} = \frac{WAC_{current} \times Q_{pool} + Cost_{unit} \times Q_{tx}}{Q_{pool} + Q_{tx}}
$$

Dove:

- $WAC_{current}$ = costo medio ponderato attuale prima di questa transazione
- $Q_{pool}$ = quantità totale detenuta nel pool prima di questa transazione
- $Cost_{unit}$ = costo di acquisizione per unità della nuova transazione
- $Q_{tx}$ = quantità aggiunta dalla nuova transazione

## ⚙️ Come LibreFolio calcola il WAC

LibreFolio utilizza un **algoritmo iterativo consapevole dell'inventario** che elabora tutte le transazioni qualificate per una determinata coppia (broker, asset) in ordine cronologico.

### 🏷️ Effetti delle Transazioni

Ogni transazione contribuisce al calcolo del WAC in uno di questi modi:

| Effetto | Condizione | Impatto sul WAC |
|--------|-----------|---------------|
| **Ponderazione** | `qty > 0` e `unit_cost > 0` | Il WAC si sposta verso il nuovo costo di acquisizione |
| **Riduzione quantità** | `qty < 0` | Uscita al WAC attuale — WAC invariato, il pool diminuisce |
| **Diluizione** | `qty > 0` ma `unit_cost = 0` | Il pool cresce, il numeratore resta invariato → il WAC **diminuisce** |

### 📅 Ordinamento dello stesso giorno

Quando avvengono più transazioni nella stessa data:

1. **Prima le aggiunte** (qty > 0) — elaborate prima delle riduzioni
2. **Poi le riduzioni** (qty < 0) — garantisce che il pool non diventi transitoriamente negativo

### 🔻 Esaurimento del Pool

- Quando `new_qty = 0`: il WAC viene resettato a 0 (posizione chiusa)
- Quando `new_qty < 0` (caso limite di arrotondamento): viene fissato a 0

## 📝 Esempi Pratici

??? example "Example 1: Two Buys — WAC rises"

 | Data | Tipo | Qta | Costo Unitario | Qta Pool | WAC |
 |------|------|-----|-----------|----------|-----|
 | 1 apr | BUY | 10 | $150 | 10 | $150.00 |
 | 15 apr | BUY | 5 | $180 | 15 | $160.00 |

 $$
 WAC = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160.00
 $$

 Il secondo acquisto a un prezzo più alto **tira verso l'alto il WAC**.

??? example "Example 2: Buy then Sell — WAC unchanged"

 | Data | Tipo | Qta | Costo Unitario | Qta Pool | WAC |
 |------|------|-----|-----------|----------|-----|
 | 1 apr | BUY | 10 | $150 | 10 | $150.00 |
 | 15 apr | SELL | -5 | (al WAC) | 5 | $150.00 |

 La vendita (SELL) rimuove unità al WAC attuale ($150). Il WAC rimane **invariato** — diminuisce solo il pool.

??? example "Example 3: Zero-Cost Acquisition — Dilution"

 | Data | Tipo | Qta | Costo Unitario | Qta Pool | WAC |
 |------|------|-----|-----------|----------|-----|
 | 1 apr | BUY | 10 | $150 | 10 | $150.00 |
 | 1 mag | ADJUSTMENT | +5 | $0 | 15 | $100.00 |

 $$
 WAC = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100.00
 $$

 Il WAC viene **diluito** perché 5 unità sono entrate a costo zero (es. frazionamento azionario, airdrop, regalo).

## 🔄 Override della Base di Costo

Per i trasferimenti e gli aggiustamenti, LibreFolio supporta un **cost basis override**: un costo unitario specificato dall'utente che rappresenta il costo storico delle unità trasferite.

**Quando impostato:**

- La transazione entra nel calcolo del WAC come una normale acquisizione ponderata
- Questo preserva la continuità del costo tra diversi broker (es. quando si trasferisce dal broker A al broker B)

**Quando non impostato:**

- La transazione entra con `unit_cost = 0` (effetto diluizione)
- Questo è appropriato per frazionamenti azionari, regali o airdrop dove non esiste un prezzo di acquisto

## 🌍 Gestione Multi-Valuta

Quando un portafoglio contiene acquisizioni in valute diverse, LibreFolio:

1. Determina la **valuta di destinazione** (la più frequente tra le acquisizioni)
2. Converte tutti i costi unitari nella valuta di destinazione utilizzando i tassi di cambio storici
3. Calcola il WAC nella valuta di destinazione unificata

!!! warning "FX Rate Availability"

    Se un tasso di cambio richiesto è mancante, il calcolo del WAC potrebbe essere incompleto. L'interfaccia utente avvisa circa le coppie di valute mancanti e fornisce azioni rapide per aggiungerle o sincronizzarle.

## 🎯 Dove viene usato il WAC in LibreFolio

- **Modulo di trasferimento**: suggerisce automaticamente il `cost_basis_override` per i trasferimenti in uscita
- **Calcolo P&L**: guadagni realizzati = sell_price − WAC (FIFO al runtime, WAC per la base di costo)
- **Vista portafoglio**: prezzo medio di ingresso per ogni posizione
