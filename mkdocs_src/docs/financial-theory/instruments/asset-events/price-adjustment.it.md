# 📊 Adeguamento del Prezzo

Un evento di **adeguamento del prezzo** rappresenta una variazione non monetaria del fair value di un asset — come una svalutazione, una correzione mark-to-market, un haircut o un re-rating.

---

## 📖 Definizione

Gli adeguamenti del prezzo catturano variazioni di valore che **non sono causate da transazioni di mercato** e **non comportano flussi di cassa** per l'investitore. Si tratta di modifiche algebriche (positive o negative) del fair value calcolato dell'asset.

Questi eventi sono particolarmente rilevanti per gli asset che non hanno una quotazione di mercato continua — come il debito privato, gli strumenti illiquidi o gli asset tracciati tramite il provider Scheduled Investment.

### Scenari Comuni

| Scenario | Importo | Descrizione |
|----------|--------|-------------|
| **Svalutazione (Write-down)** | Negativo | Riduzione del valore contabile dovuta a perdita di valore (impairment) |
| **Mark-to-market** | +/− | Rivalutazione periodica per riflettere il fair value attuale |
| **Haircut** | Negativo | Riduzione forzata (es. durante una ristrutturazione del debito) |
| **Re-rating** | Positivo | Revisione al rialzo del fair value dopo eventi positivi |
| **Adeguamento NAV** | +/− | Correzione del Net Asset Value per fondi chiusi |

---

## 📉 Impatto sul Prezzo di Mercato

Per gli **asset con prezzo di mercato** (azioni, ETF), gli adeguamenti del prezzo sono rari e tipicamente informativi — il prezzo di mercato riflette già l'evento.

Per gli **asset con valutazione basata su modello** (Scheduled Investment, manuale), l'adeguamento modifica direttamente il prezzo calcolato:

$$
\text{price}(d) = \text{base{\_}value}(d) + \sum_{i : d_i \leq d} \text{PRICE{\_}ADJUSTMENT}_i
$$

!!! example "Esempio: Svalutazione di un'Obbligazione"

    Un'obbligazione societaria originariamente valutata 1.000 € viene parzialmente svalutata dopo che l'emittente ha segnalato difficoltà finanziarie.

    - **Prima dell'adeguamento**: valore calcolato = 1.000 €
    - **Evento di adeguamento prezzo**: importo = −200
    - **Dopo l'adeguamento**: valore calcolato = 800 €

    Questa non è una transazione di mercato — è una correzione del modello di fair value.

!!! example "Esempio: Haircut su prestito P2P"

    Un prestito peer-to-peer di 5.000 € subisce un haircut del 20% durante una ristrutturazione del debito.

    - **Evento di adeguamento prezzo**: importo = −1.000
    - **Nuovo fair value**: 4.000 €

---

## 📊 Quando usare gli Adeguamenti del Prezzo

Usa `PRICE_ADJUSTMENT` quando:

- ✅ Il fair value dell'asset cambia senza una transazione di mercato
- ✅ Devi registrare una svalutazione o un impairment
- ✅ L'asset ha una valutazione basata su modello (Scheduled Investment) e necessita di una correzione manuale
- ✅ Una ristrutturazione del debito influisce sul valore nominale

**Non** usare per:

- ❌ Variazioni regolari del prezzo di mercato (queste sono catturate dai punti dati del prezzo)
- ❌ Flussi di cassa (usa `DIVIDEND` o `INTEREST` invece)
- ❌ Variazioni della quantità di azioni (usa `SPLIT` invece)

---

## 🧮 Come LibreFolio gestisce gli Adeguamenti del Prezzo

In LibreFolio, un evento `PRICE_ADJUSTMENT` viene registrato con:

- **Data**: La data di decorrenza dell'adeguamento
- **Importo**: La variazione algebrica (positiva per gli incrementi, negativa per i decrementi)
- **Valuta**: La valuta dell'adeguamento
- **Note**: Descrizione della motivazione (es. "Svalutazione parziale dovuta al default dell'emittente")

Per il provider **Scheduled Investment**, gli adeguamenti del prezzo fanno parte della formula principale:

$$
\text{price}(d) = \text{initial{\_}value} + \text{accrued{\_}interest}(d) - \sum \text{INTEREST} + \sum \text{PRICE{\_}ADJUSTMENT}
$$

---

## 🔗 Correlati

- 📅 **[Panoramica Eventi Asset](index.md)** — Tutti i tipi di eventi
- 📈 **[Interessi](interest.md)** — Pagamenti periodici di interessi
- 🏁 **[Regolamento a Scadenza](maturity-settlement.md)** — Restituzione finale del capitale
