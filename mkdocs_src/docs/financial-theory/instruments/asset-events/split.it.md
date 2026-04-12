# ✂️ Split

Uno **stock split** (o frazionamento azionario, o reverse split nel caso di raggruppamento) è un'operazione societaria che modifica il numero di azioni in circolazione mantenendo costante la capitalizzazione di mercato totale.

---

## 📖 Definizione

In uno stock split, una società divide le proprie azioni esistenti in più nuove azioni. Il **valore totale** della posizione di un investitore rimane invariato — cambiano solo il numero di azioni e il prezzo per azione.

### Forward Split (Frazionamento)

La società aumenta il numero di azioni. Ogni azione esistente diventa più azioni a un prezzo proporzionalmente inferiore.

| Rapporto | Significato |
|-------|---------|
| **2:1** | Ogni azione diventa 2 azioni a metà prezzo |
| **3:1** | Ogni azione diventa 3 azioni a un terzo del prezzo |
| **4:1** | Ogni azione diventa 4 azioni a un quarto del prezzo |
| **10:1** | Ogni azione diventa 10 azioni a un decimo del prezzo |

### Reverse Split (Raggruppamento)

La società riduce il numero di azioni. Più azioni esistenti si fondono in un numero minore di azioni a un prezzo proporzionalmente più alto.

| Rapporto | Significato |
|-------|---------|
| **1:2** | Ogni 2 azioni diventano 1 azione al doppio del prezzo |
| **1:10** | Ogni 10 azioni diventano 1 azione al 10× del prezzo |
| **1:20** | Ogni 20 azioni diventano 1 azione al 20× del prezzo |

---

## 📉 Impatto sul Prezzo di Mercato

Uno split causa una **variazione di prezzo immediata e proporzionale** che è matematicamente neutra:

$$
P_{\text{after}} = \frac{P_{\text{before}}}{\text{split ratio}}
$$

$$
Q_{\text{after}} = Q_{\text{before}} \times \text{split ratio}
$$

Dove $P$ è il prezzo per azione e $Q$ è la quantità di azioni.

!!! example "Esempio: Split Apple 4:1 (Agosto 2020)"

    - **Prima dello split**: 100 azioni × $500 = $50,000 valore totale
    - **Dopo lo split**: 400 azioni × $125 = $50,000 valore totale
    - **Variazione prezzo**: −75% (ma il valore della posizione rimane invariato)

!!! example "Esempio: Reverse Split 1:10"

    - **Prima**: 1,000 azioni × $0.50 = $500 valore totale
    - **Dopo**: 100 azioni × $5.00 = $500 valore totale
    - **Motivazione**: La società vuole alzare il prezzo dell'azione sopra i requisiti minimi di quotazione del mercato

---

## 📊 Perché le Società Effettuano Split

### Frazionamenti (Forward split)

- **Accessibilità**: Un prezzo per azione più basso rende il titolo più accessibile agli investitori retail
- **Liquidità**: Un maggior numero di azioni in circolazione può aumentare il volume di scambi
- **Psicologia**: Un prezzo nominale più basso può attrarre più acquirenti
- **Opzioni**: Un prezzo per azione più basso riduce il capitale necessario per i contratti di opzioni (100 azioni per contratto)

### Raggruppamenti (Reverse split)

- **Conformità alla quotazione**: I mercati richiedono prezzi minimi per azione (ad esempio, $1.00 su NASDAQ)
- **Percezione istituzionale**: Alcuni fondi hanno requisiti minimi di prezzo
- **Spesso un segnale di allarme**: I reverse split sono frequentemente associati a società in difficoltà

---

## 📈 Adeguamento Storico dei Prezzi

Quando si analizzano i prezzi storici attraverso gli split, i provider di dati forniscono tipicamente **prezzi rettificati** (adjusted prices) — tutti i prezzi storici vengono divisi per il rapporto di split cumulativo, in modo che il grafico mostri una linea continua.

Per esempio, se Apple valeva $100 prima di uno split 4:1, il prezzo storico rettificato diventa $25 per corrispondere alla scala post-split.

---

## 🧮 Come LibreFolio Gestisce gli Split

In LibreFolio, un evento `SPLIT` viene registrato con:

- **Date**: La data di efficacia dello split
- **Amount**: Il rapporto di split (ad esempio, `2` per uno split 2:1, `0.1` per un reverse split 1:10)
- **Notes**: Descrizione opzionale (ad esempio, "forward split 4:1")

Gli eventi di split appaiono come **marcatori sul grafico** e aiutano a spiegare improvvise discontinuità di prezzo. Quando si utilizzano i **prezzi rettificati** di provider come Yahoo Finance, lo split è già integrato nei dati dei prezzi.

---

## 🔗 Correlati

- 📅 **[Panoramica degli eventi degli asset](index.md)** — Tutti i tipi di eventi
- 💸 **[Tipi di Transazione](../transaction-types/index.md)** — Come gli split influenzano le transazioni del portafoglio
- 📚 **[Tipi di asset](../asset-types/index.md)** — Tipi di asset che possono subire split
