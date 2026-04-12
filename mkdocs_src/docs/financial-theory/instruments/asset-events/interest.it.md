# 📈 Interessi

Un evento di **interesse** rappresenta un pagamento periodico di interessi derivante da uno strumento di debito, un titolo a reddito fisso o un accordo di prestito.

---

## 📖 Definizione

L'interesse è il costo del denaro preso in prestito, pagato dall'emittente (mutuatario) al detentore (mutuante). Per gli investitori, i pagamenti di interessi rappresentano il reddito guadagnato dal possesso di obbligazioni, titoli, depositi a termine o prestiti peer-to-peer.

A differenza dei dividendi (che dipendono dagli utili dell'azienda), i pagamenti di interessi sono **obbligatori per contratto**: l'emittente deve pagare il tasso concordato indipendentemente dalla performance finanziaria.

**Calendari di interessi comuni:**

| Frequenza | Strumenti Tipici |
|-----------|-------------------|
| Mensile | Conti di risparmio, prestiti P2P |
| Trimestrale | Obbligazioni corporate, alcuni titoli di stato |
| Semestrale | Titoli del Tesoro USA, molti titoli di stato europei |
| Annuale | Alcune obbligazioni corporate, depositi a termine |
| Alla scadenza | Obbligazioni zero-coupon, certificati di deposito |

---

## 📉 Impatto sul Prezzo di Mercato

Per le **obbligazioni con cedola**, i pagamenti di interessi causano un reset periodico della componente dell'**interesse maturato**:

1. Tra le date di cedola, il "dirty price" (prezzo sporco) dell'obbligazione (clean price + interesse maturato) aumenta gradualmente
2. Nella data di pagamento della cedola, l'interesse maturato torna a zero
3. Il "clean price" (prezzo pulito) può scendere leggermente intorno alla data di stacco della cedola

!!! example "Esempio"

    Un'obbligazione con valore nominale di 1.000 € paga una cedola annuale del 4% ogni sei mesi (20 € ogni 6 mesi).

    - **Giorno prima della cedola**: Clean price 980 €, Interesse maturato 20 € $\rightarrow$ Dirty price 1.000 €
    - **Data della cedola**: L'interesse maturato torna a 0 €, l'investitore riceve 20 € in contanti
    - **Giorno dopo la cedola**: Clean price 980 €, Interesse maturato $\approx$ 0,11 € $\rightarrow$ Dirty price 980,11 €

Per gli asset di tipo **Scheduled Investment** in LibreFolio, gli eventi di interesse modificano direttamente il prezzo calcolato:

$$
\text{price}(d) = \text{initial{\_}value} + \text{accrued{\_}interest}(d) - \sum \text{INTEREST events}
$$

---

## 📊 Metriche di Rendimento

### Rendimento Corrente (Current Yield)

$$
\text{Current Yield} = \frac{\text{Annual Coupon}}{\text{Current Market Price}} \times 100\%
$$

### Rendimento a Scadenza (Yield to Maturity - YTM)

Il rendimento totale previsto se l'obbligazione viene detenuta fino alla scadenza, tenendo conto dei pagamenti delle cedole, del rimborso del valore nominale e del prezzo di mercato attuale.

---

## 🧮 Come LibreFolio Gestisce gli Interessi

In LibreFolio, un evento `INTEREST` viene registrato con:

- **Data**: La data del pagamento degli interessi
- **Importo**: L'importo in contanti ricevuto
- **Valuta**: La valuta del pagamento

Per gli asset del provider **Scheduled Investment**, gli eventi di interesse vengono generati automaticamente dal calendario degli interessi configurato e influenzano direttamente il calcolo del prezzo. Per le obbligazioni con prezzo di mercato, servono come indicatori informativi.

---

## 🔗 Correlati

- 📅 **[Panoramica Eventi Asset](index.md)** — Tutti i tipi di eventi
- 📆 **[Convenzioni di Conteggio dei Giorni](../../fundamentals/day-count.md)** — Come vengono calcolati i periodi di maturazione degli interessi
- 🏁 **[Regolamento a Scadenza](maturity-settlement.md)** — Rimborso finale del capitale alla scadenza dell'obbligazione
