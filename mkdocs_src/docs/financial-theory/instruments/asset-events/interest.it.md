# 📈 Interessi

Un evento di **interesse** rappresenta un pagamento periodico di interessi derivante da uno strumento di debito, un titolo a reddito fisso o un accordo di prestito.

---

## 📖 Definizione

L'interesse è il costo del denaro preso in prestito, pagato dall'emittente (mutuatario) al detentore (prestatore). Per gli investitori, i pagamenti degli interessi rappresentano il reddito guadagnato dal possesso di obbligazioni, titoli, depositi a termine o prestiti peer-to-peer.

A differenza dei dividendi (che dipendono dagli utili dell'azienda), i pagamenti degli interessi sono **obblighi contrattuali**: l'emittente deve pagare il tasso concordato indipendentemente dalle prestazioni finanziarie.

**Frequenze di pagamento comuni:**

| Frequenza | Strumenti Tipici |
|-----------|-------------------|
| Mensile | Conti di risparmio, prestiti P2P |
| Trimestrale | Obbligazioni societarie, alcuni titoli di stato |
| Semestrale | Treasury bonds USA, molti titoli di stato europei |
| Annuale | Alcune obbligazioni societarie, depositi a termine |
| Alla scadenza | Obbligazioni zero-coupon, certificati di deposito |

---

## 🧮 Formule degli Interessi

??? example "📏 Interesse Semplice"

 Interesse calcolato solo sul capitale originale — senza capitalizzazione:

 $$
 I = P \times r \times t
 $$

 Dove:

 - $P$ = capitale (investimento iniziale)
 - $r$ = tasso di interesse annuale (es. 0,04 per il 4%)
 - $t$ = tempo in anni

 Utilizzato per: prestiti a breve termine, alcuni conti di risparmio, buoni del tesoro.

??? example "📈 Interesse Composto"

 Interesse calcolato sul capitale **più** gli interessi precedentemente accumulati:

 $$
 A = P \times \left(1 + \frac{r}{n}\right)^{n \times t}
 $$

 Dove:

 - $A$ = importo finale (capitale + interessi)
 - $P$ = capitale
 - $r$ = tasso di interesse annuale
 - $n$ = frequenza di capitalizzazione per anno (12 = mensile, 4 = trimestrale, 1 = annuale)
 - $t$ = tempo in anni

 L'interesse guadagnato è: $I = A - P$

 Utilizzato per: la maggior parte delle obbligazioni, conti di risparmio con reinvestimento, piattaforme P2P.

---

## 📉 Impatto sul Prezzo di Mercato

Per le **obbligazioni con cedola**, i pagamenti degli interessi causano un reset periodico della componente dell'**interesse maturato**:

1. Tra le date di cedola, il "dirty price" dell'obbligazione (clean price + interesse maturato) aumenta gradualmente
2. Nella data di pagamento della cedola, l'interesse maturato torna a zero
3. Il clean price può scendere leggermente intorno alla data ex-cedola

??? example "Ciclo della cedola obbligazionaria"

 Un'obbligazione con valore nominale 1.000 € paga una cedola annuale del 4% ogni sei mesi (20 € ogni 6 mesi).

 - **Giorno prima della cedola**: Clean price 980 €, Interesse maturato 20 € → Dirty price 1.000 €
 - **Data della cedola**: L'interesse maturato torna a 0 €, l'investitore riceve 20 € in contanti
 - **Giorno dopo la cedola**: Clean price 980 €, Interesse maturato ≈ 0,11 € → Dirty price 980,11 €

Per gli asset di **investimento programmato** in LibreFolio, gli eventi di interesse modificano direttamente il prezzo calcolato:

$$
\text{price}(d) = V_0 + I_{accrued}(d) - \sum_{k} C_k
$$

Dove:

- $V_0$ = valore dell'investimento iniziale
- $I_{accrued}(d)$ = interesse maturato fino alla data $d$
- $\sum_k C_k$ = somma di tutti i pagamenti di interessi (cedole) già distribuiti

---

## 📊 Metriche di Rendimento

??? example "📐 Current Yield"

 La misura di rendimento più semplice — reddito annuale relativo al prezzo attuale:

 $$
 \text{Current Yield} = \frac{\text{Annual Coupon}}{\text{Current Market Price}} \times 100
 $$

 Dove:

 - **Annual Coupon** = pagamenti totali della cedola per anno (es. 40 € per un'obbligazione al 4% con valore nominale di 1.000 €)
 - **Current Market Price** = quanto pagheresti per comprare l'obbligazione oggi

 Limitazione: ignora la plusvalenza/minusvalenza se detenuta fino a scadenza.

??? example "📐 Yield to Maturity (YTM)"

 Il rendimento totale previsto se l'obbligazione viene mantenuta fino alla scadenza, tenendo conto di **tutti** i flussi di cassa: pagamenti delle cedole, rimborso del valore nominale e la differenza tra il prezzo di acquisto e il valore nominale.

 YTM è il tasso $y$ che soddisfa:

 $$
 P = \sum_{t=1}^{T} \frac{C}{(1+y)^t} + \frac{F}{(1+y)^T}
 $$

 Dove:

 - $P$ = prezzo di mercato attuale
 - $C$ = pagamento della cedola per periodo
 - $F$ = valore nominale (restituito a scadenza)
 - $T$ = numero di periodi fino alla scadenza
 - $y$ = rendimento a scadenza (per periodo)

 YTM deve essere risolto numericamente (non esiste una soluzione in forma chiusa).

---

## 🧮 Come LibreFolio gestisce gli interessi

In LibreFolio, un evento `INTEREST` viene registrato con:

- **Date**: La data di pagamento dell'interesse
- **Amount**: L'importo in denaro ricevuto
- **Currency**: La valuta del pagamento

Per gli asset del provider di **investimento programmato**, gli eventi di interesse vengono generati automaticamente dal calendario degli interessi configurato e influenzano direttamente il calcolo del prezzo. Per le obbligazioni con prezzo di mercato, servono come marker informativi.

---

## 🔗 Correlati

- 📅 **[Panoramica Eventi Asset](index.md)** — Tutti i tipi di eventi
- 📆 **[Convenzioni di Conteggio dei Giorni](../../fundamentals/day-count.md)** — Come vengono calcolati i periodi di maturazione degli interessi
- 🏁 **[Regolamento alla Scadenza](maturity-settlement.md)** — Ritorno finale del capitale alla scadenza dell'obbligazione
- 📈 **[Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** — Misurare il rendimento totale
