# ![](../../../static/icons/asset-types/bond.png){: width="32" style="vertical-align: middle;" } Obbligazioni

Un'**obbligazione** è un titolo a reddito fisso che rappresenta un prestito da parte di un investitore a un ente mutuatario (governo o società). Il mutuatario paga interessi periodici (**cedole**) e restituisce il capitale (**valore nominale**) alla scadenza.

---

## 🔑 Caratteristiche Principali

| Proprietà | Dettaglio |
|----------|--------|
| **Codice in LibreFolio** | `BOND` |
| **Prezzo** | Quotato come percentuale del valore nominale (es. 98,50 = 98,5% del valore nominale) |
| **Valuta** | Denominata nella valuta di emissione |
| **Cedole** | Tasso fisso o variabile, pagate semestralmente o annualmente |
| **Scadenza** | Data fissa in cui il capitale viene restituito |
| **Provider tipici** | Yahoo Finance, Scheduled Investment, Manuale |

---

## 📊 Concetti di Prezzo delle Obbligazioni

### 💵 Valore Nominale (Par)

L'importo che l'emittente restituirà alla scadenza — tipicamente $ 1.000 o € 1.000 per obbligazione.

### 📈 Tasso Cedolare

Il tasso di interesse annuale pagato sul valore nominale:

$$
\text{Cedola Annuale} = \text{Valore Nominale} \times \text{Tasso Cedolare}
$$

### 📊 Rendimento a Scadenza (YTM)

Il rendimento totale previsto se l'obbligazione viene detenuta fino alla scadenza, tenendo conto del prezzo di acquisto, dei pagamenti delle cedole e del valore nominale alla scadenza. La formula dello YTM è un'**approssimazione matematica** ampiamente utilizzata per descrivere come il mercato prezza le obbligazioni in risposta alle variazioni dei tassi di interesse, e funge da base per molte altre metriche a reddito fisso:

$$
P = \sum_{t=1}^{n} \frac{C}{(1 + y)^t} + \frac{F}{(1 + y)^n}
$$

dove $P$ = prezzo, $C$ = cedola, $F$ = valore nominale, $y$ = YTM, $n$ = periodi.

### 📉 Prezzo Dirty vs Prezzo Clean

- **Prezzo Clean (Clean Price)**: Il prezzo quotato, escludendo l'interesse maturato
- **Prezzo Dirty (Dirty Price)**: Prezzo clean + interesse maturato (ciò che si paga effettivamente)

$$
\text{Prezzo Dirty} = \text{Prezzo Clean} + \text{Interesse Maturato}
$$

L'interesse maturato dipende dalla [Convenzione di Conteggio dei Giorni](../../fundamentals/day-count.md).

---

## 📈 Relazione Prezzo–Rendimento

I prezzi delle obbligazioni si muovono in modo **inverso** rispetto ai rendimenti:

- Quando i tassi di interesse aumentano → i prezzi delle obbligazioni scendono
- Quando i tassi di interesse diminuiscono → i prezzi delle obbligazioni salgono

Ciò accade perché le obbligazioni esistenti con cedole più basse diventano meno attraenti rispetto alle nuove obbligazioni emesse a tassi più elevati.

---

## 🔗 Correlati

- 📈 **[Eventi di Interesse](../asset-events/interest.md)** — Pagamenti delle cedole e maturazione
- 🏁 **[Regolamento a Scadenza](../asset-events/maturity-settlement.md)** — Restituzione del capitale a fine vita
- 📊 **[Aggiustamento del Prezzo](../asset-events/price-adjustment.md)** — Mark-to-market e svalutazioni
- 📅 **[Convenzioni di Conteggio dei Giorni](../../fundamentals/day-count.md)** — Come viene calcolato l'interesse maturato
