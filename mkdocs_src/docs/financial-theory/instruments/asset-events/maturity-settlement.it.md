# 🏁 Regolamento alla Scadenza

Un evento di **regolamento alla scadenza** segna la fine di uno strumento finanziario a termine: l'emittente restituisce il capitale (valore nominale) all'investitore e non avvengono ulteriori calcoli del prezzo.

---

## 📖 Definizione

La scadenza è la data in cui uno strumento di debito (obbligazione, nota, certificato di deposito, prestito a termine) raggiunge la sua conclusione contrattuale. In questa data:

1. Il **capitale** (valore nominale / valore alla pari) viene restituito all'investitore
2. Viene effettuato l'eventuale **ultimo pagamento degli interessi** (se applicabile)
3. Lo strumento **cessa di esistere** — non vi sono più quotazioni o scambi

### Strumenti con Data di Scadenza

| Strumento | Scadenza Tipica | Regolamento |
|------------|-----------------|------------|
| **Buoni del Tesoro (Treasury Bills)** | 4 settimane – 1 anno | Valore nominale alla scadenza |
| **Titoli di Stato** | 2 – 30 anni | Valore nominale + cedola finale |
| **Obbligazioni Societarie** | 1 – 30 anni | Valore nominale + cedola finale |
| **Certificati di Deposito** | 1 mese – 5 anni | Capitale + interessi maturati |
| **Depositi a Termine** | 1 mese – 5 anni | Capitale + interessi |
| **Prestiti P2P** | 1 – 5 anni | Capitale residuo |

---

## 📉 Impatto sul Prezzo di Mercato

Man mano che un'obbligazione si avvicina alla scadenza, il suo prezzo di mercato converge verso il **valore nominale** (par), indipendentemente dal fatto che sia stata scambiata a premio o a sconto:

$$
\lim_{d \to \text{scadenza}} P(d) = \text{Valore Nominale}
$$

Questo fenomeno è chiamato **pull to par**:

- **Obbligazioni emesse a premio** (prezzo > par): il prezzo diminuisce gradualmente verso il valore nominale
- **Obbligazioni emesse a sconto** (prezzo < par): il prezzo aumenta gradualmente verso il valore nominale

!!! example "Esempio: Scadenza di un Titolo di Stato"

    Un titolo di stato a 10 anni con valore nominale di 1.000 € e cedola annuale del 3%:

    - **All'emissione** (2015): Prezzo = 1.000 € (par)
    - **A metà vita** (2020): Prezzo = 1.050 € (premio, perché i tassi di mercato sono scesi)
    - **Vicino alla scadenza** (2024): Prezzo = 1.005 € (convergenza verso il par)
    - **Alla scadenza** (2025-01-15): L'investitore riceve:
    - 1.000 € (restituzione del valore nominale)
    - 30 € (ultima cedola annuale)
    - Totale: 1.030 €

!!! example "Esempio: Obbligazione Zero-Coupon"

    Un'obbligazione zero-coupon con valore nominale di $1.000 acquistata a $850:

    - **All'acquisto**: Prezzo = $850 (sconto)
    - **Alla scadenza**: L'investitore riceve $1.000
    - **Rendimento implicito**: $150 ($1.000 − $850)
    - Nessun pagamento di interessi intermedi — tutto il rendimento deriva dal regolamento alla scadenza

---

## 📊 Dopo la Scadenza

Una volta che un evento di regolamento alla scadenza viene registrato in LibreFolio:

- La **serie di prezzi** dell'asset termina alla data di scadenza
- L'importo del regolamento rappresenta l'**ultimo valore della serie**
- L'asset può rimanere nel sistema per analisi storiche, ma non riceverà nuovi dati di prezzo

---

## 🧮 Come LibreFolio Gestisce il Regolamento alla Scadenza

In LibreFolio, un evento `MATURITY_SETTLEMENT` viene registrato con:

- **Data**: La data di scadenza
- **Importo**: Il valore nominale / l'importo del capitale restituito
- **Valuta**: La valuta del regolamento
- **Note**: Descrizione opzionale (es. "Scadenza obbligazione Treasury 10Y")

Per il provider **Scheduled Investment**, la data di scadenza è configurata nelle impostazioni del provider. La formula di calcolo del prezzo riconosce che non avviene ulteriore maturazione dopo la scadenza:

$$
\text{price}(d) = \begin{cases}
\text{initial\\_value} + \text{accrued}(d) - \Sigma\text{INT} + \Sigma\text{ADJ} & \text{if } d < \text{maturity} \\
\text{settlement\\_amount} & \text{if } d \geq \text{maturity}
\end{cases}
$$

---

## 🔗 Correlati

- 📅 **[Panoramica Eventi Asset](index.md)** — Tutti i tipi di eventi
- 📈 **[Interessi](interest.md)** — Pagamenti periodici di cedole prima della scadenza
- 📆 **[Convenzioni di Conteggio dei Giorni](../../fundamentals/day-count.md)** — Come viene calcolato il maturato tra le date di cedola
- 📊 **[Aggiustamento Prezzo](price-adjustment.md)** — Variazioni di valore non monetarie prima della scadenza
