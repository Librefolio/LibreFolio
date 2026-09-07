# 📊 Prezzo Medio di Carico (PMC)

## 💡 Cos'è il PMC?

Il **Prezzo Medio di Carico** (PMC) è il costo unitario medio di un asset in un portafoglio, ponderato per la quantità acquistata a ciascun prezzo.

Risponde alla domanda: _"In media, quanto ho pagato per unità di questo asset?"_

!!! info "Altri nomi"

    - **PMC** — Prezzo Medio di Carico (Italia)
    - **ACB** — Average Cost Basis (Canada, USA)
    - **CMP** — Coût Moyen Pondéré (Francia)

## 🧮 Formula

Il PMC viene calcolato **in modo iterativo** man mano che ogni transazione viene elaborata cronologicamente:

$$
PMC_{nuovo} = \frac{PMC_{corrente} \times Q_{pool} + Costo_{unitario} \times Q_{tx}}{Q_{pool} + Q_{tx}}
$$

Dove:

- $PMC_{corrente}$ = prezzo medio di carico corrente prima di questa transazione
- $Q_{pool}$ = quantità totale detenuta nel pool prima di questa transazione
- $Costo_{unitario}$ = costo di acquisizione per unità della nuova transazione
- $Q_{tx}$ = quantità aggiunta dalla nuova transazione

## ⚙️ Come LibreFolio Calcola il PMC

LibreFolio utilizza un **algoritmo iterativo basato sull'inventario** che elabora tutte le transazioni qualificanti per una data coppia (broker, asset) in ordine cronologico.

### 🏷️ Effetti delle Transazioni

Ogni transazione contribuisce al calcolo del PMC in uno di questi modi:

| Effetto | Condizione | Impatto sul PMC |
|--------|-----------|---------------|
| **Ponderato** | `qty > 0` e `unit_cost > 0` | Il PMC si avvicina al nuovo costo di acquisizione |
| **Quantità ridotta** | `qty < 0` | Uscita al PMC corrente — PMC invariato, pool si riduce |
| **Diluizione** | `qty > 0` ma `unit_cost = 0` | Pool cresce, numeratore invariato → PMC **diminuisce** |
| **PMC Automatico** | `qty > 0`, `cost_basis_mode = "auto"` | Pool invariato — le unità entrano al PMC corrente |

### 📅 Ordinamento Stesso Giorno

Quando più transazioni avvengono nella stessa data:

1. **Prima gli aumenti** (qty > 0) — elaborati prima delle riduzioni
2. **Poi le riduzioni** (qty < 0) — garantisce che il pool non diventi temporaneamente negativo

### 🔻 Esaurimento del Pool

- Quando `new_qty = 0`: Il PMC si azzera (posizione chiusa)
- Quando `new_qty < 0` (caso limite di arrotondamento): bloccato a 0

## 📝 Esempi Pratici

??? example "Esempio 1: Due Acquisti — Il PMC sale"

    | Data | Tipo | Q.tà | Costo Unitario | Q.tà Pool | PMC |
    |------|------|------|----------------|-----------|-----|
    | 1 Apr | ACQUISTO | 10 | 150 $ | 10 | 150,00 $ |
    | 15 Apr | ACQUISTO | 5 | 180 $ | 15 | 160,00 $ |

    $$
    PMC = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160,00
    $$

    Il secondo acquisto a un prezzo più alto **spinge il PMC verso l'alto**.

??? example "Esempio 2: Acquisto poi Vendita — PMC invariato"

    | Data | Tipo | Q.tà | Costo Unitario | Q.tà Pool | PMC |
    |------|------|------|----------------|-----------|-----|
    | 1 Apr | ACQUISTO | 10 | 150 $ | 10 | 150,00 $ |
    | 15 Apr | VENDITA | -5 | (al PMC) | 5 | 150,00 $ |

    La VENDITA rimuove unità al PMC corrente (150 $). Il PMC rimane **invariato** — solo il pool si riduce.

??? example "Esempio 3: Acquisizione a Costo Zero — Diluizione"

    | Data | Tipo | Q.tà | Costo Unitario | Q.tà Pool | PMC |
    |------|------|------|----------------|-----------|-----|
    | 1 Apr | ACQUISTO | 10 | 150 $ | 10 | 150,00 $ |
    | 1 Mag | RETTIFICA | +5 | 0 $ | 15 | 100,00 $ |

    $$
    PMC = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100,00
    $$

    Il PMC viene **diluito** perché 5 unità sono entrate a costo zero (es. frazionamento, airdrop, donazione).

## 🔄 Override della Base di Costo

Per trasferimenti e rettifiche, LibreFolio supporta un **override della base di costo**: un costo unitario specificato dall'utente che rappresenta il costo storico delle unità trasferite.

**Quando impostato (modalità manuale):**

- La transazione entra nel calcolo del PMC come una normale acquisizione ponderata
- Questo preserva la continuità del costo tra broker (es., quando si trasferisce dal broker A al broker B)

**Quando non impostato (nessuna modalità specificata):**

- La transazione entra con `unit_cost = 0` (effetto diluizione)
- Questo è appropriato per frazionamenti, donazioni o airdrop dove non esiste un prezzo di acquisto

**Quando in modalità automatica (`cost_basis_mode = "auto"`):**

- La transazione entra al **PMC corrente del pool** — il PMC rimane algebricamente invariato
- Questo è appropriato per trasferimenti o rettifiche dove la base di costo dovrebbe essere ereditata dal pool del broker di origine

$$
PMC_{nuovo} = \frac{PMC \times Q_{pool} + PMC \times Q_{tx}}{Q_{pool} + Q_{tx}} = PMC
$$

!!! tip "PMC Automatico nell'interfaccia"

    Nel modulo di transazione, l'interruttore "Auto" utilizza questa modalità. La tabella di qualificazione mostra il badge dell'effetto **PMC Automatico** (o **PMC Automatico** in italiano), indicando che le unità sono entrate al costo corrente del pool senza alterare il PMC.

??? example "Esempio 4: Trasferimento in Modalità Auto — PMC invariato"

    | Data | Tipo | Q.tà | Costo Unitario | Q.tà Pool | PMC |
    |------|------|------|----------------|-----------|-----|
    | 1 Apr | ACQUISTO | 10 | 150 $ | 10 | 150,00 $ |
    | 15 Apr | ACQUISTO | 5 | 180 $ | 15 | 160,00 $ |
    | 1 Mag | TRASFERIMENTO (auto) | +3 | 160 $ (=PMC) | 18 | 160,00 $ |

    $$
    PMC = \frac{160 \times 15 + 160 \times 3}{15 + 3} = \frac{2880}{18} = 160,00
    $$

    Il destinatario del trasferimento in **modalità auto** eredita il PMC corrente come costo unitario. Il pool cresce ma il PMC rimane **invariato**.

## 🌍 Gestione Multi-Valuta

Quando un portafoglio contiene acquisizioni in valute diverse, LibreFolio:

1. Determina la **valuta target** dall'override della richiesta quando fornito; altrimenti usa la valuta dell'acquisizione più recente (deterministico), con fallback sulla valuta dell'asset
2. Converte tutti i costi unitari nella valuta target utilizzando i tassi di cambio storici
3. Calcola il PMC nella valuta target unificata

!!! warning "Disponibilità Tasso di Cambio"

    Se un tasso di cambio richiesto è mancante, il calcolo del PMC potrebbe essere incompleto. L'interfaccia avvisa riguardo alle coppie di cambio mancanti e fornisce azioni rapide per aggiungerle o sincronizzarle.

## 🎯 Dove viene utilizzato il PMC in LibreFolio

- **Base di costo**: $\text{CB}(a,b,t) = q(a,b,t) \times \text{PMC}(a,b,t) \times \text{fx}(\cdot)$
- **P&L realizzato in VENDITA**: $\text{realizzato} = P_{\text{vendita}} - q_{\text{venduta}} \times \text{PMC}_{\text{pre-vendita}}$
- **Scomposizione del pool di cassa**: La VENDITA restituisce $C = q_{\text{venduta}} \times \text{PMC}$ al Pool di Capitale
- **Modulo di trasferimento**: suggerisce automaticamente cost_basis_override per i trasferimenti in uscita

!!! warning "Il PMC non viene mai utilizzato per la valutazione degli asset"

    Il PMC è un costrutto contabile per la base di costo. La catena di valutazione per il valore di mercato utilizza: `MARKET_PRICE → LAST_BUY_PRICE → MISSING`. Vedi [Risoluzione Prezzi](portfolio-engine/price-resolution.md).

## ⚙️ Implementazione: Ambito a Livello di Posizione

Il PMC viene mantenuto **per posizione** $(a, b)$ — cioè, per coppia (asset, broker). Lo stesso asset detenuto su due broker ha due pool PMC indipendenti.

$$
\text{PMC}(a, b_1, t) \neq \text{PMC}(a, b_2, t) \quad \text{in generale}
$$

Il motore calcola il PMC inline durante il ciclo giornaliero delle transazioni — nessuna query separata al database necessaria. Ciò raggiunge un costo ammortizzato O(1) per transazione invece del costo O(N) di rieseguire query sull'intera cronologia.

### 📅 Ordinamento delle transazioni nello stesso giorno

All'interno della stessa data, **gli aumenti vengono elaborati prima delle riduzioni**:

$$
\text{BUY}_1, \text{BUY}_2, \ldots \quad \text{poi} \quad \text{SELL}_1, \text{SELL}_2, \ldots
$$

Questo previene quantità negative transitorie e garantisce che SELL legga sempre il PMC corretto che include gli BUY dello stesso giorno.

## 🔗 Correlati

- 🔬 **[Analisi dei Lotti FIFO](fifo-engine/fifo-lot-analysis.md)** — Complemento per lotto: traccia ogni batch di acquisizione individualmente invece di combinarli in una media
- 🔁 **[Acquisto & Vendita](../../instruments/transaction-types/buy-sell.md)** — Transazioni che alimentano il pool PMC
- 📈 **[NAV / Patrimonio Netto](portfolio-engine/nav.md)** — Come il valore contabile basato sul PMC differisce dal NAV a prezzi di mercato
