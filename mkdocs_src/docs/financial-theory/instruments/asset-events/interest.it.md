# 📈 Interessi

Un evento di **interessi** rappresenta un pagamento periodico di interessi derivante da uno strumento di debito, un titolo a reddito fisso o un accordo di prestito.

---

## 📖 Definizione

L'interesse è il costo del denaro preso in prestito, pagato dall'emittente (mutuatario) al detentore (prestatore). Per gli investitori, i pagamenti degli interessi rappresentano il reddito guadagnato dal possesso di obbligazioni, titoli, depositi a termine o prestiti peer-to-peer.

A differenza dei dividendi (che dipendono dai profitti aziendali), i pagamenti degli interessi sono **contrattualmente obbligatori**: l'emittente deve pagare il tasso concordato indipendentemente dalle prestazioni finanziarie.

**Calendari di interesse comuni:**

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
    - $r$ = tasso di interesse annuo (es. 0,04 per il 4%)
    - $t$ = tempo in anni

    Utilizzato per: prestiti a breve termine, alcuni conti di risparmio, BOT.

??? example "📈 Interesse Composto"

    Interesse calcolato sul capitale **più** gli interessi precedentemente accumulati:

    $$
    A = P \times \left(1 + \frac{r}{n}\right)^{n \times t}
    $$

    Dove:

    - $A$ = importo finale (capitale + interessi)
    - $P$ = capitale
    - $r$ = tasso di interesse annuo
    - $n$ = frequenza di capitalizzazione all'anno (12 = mensile, 4 = trimestrale, 1 = annuale)
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

    Un'obbligazione con valore nominale 1.000 € paga una cedola annuale del 4% semestralmente (20 € ogni 6 mesi).

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

??? example "📐 Rendimento Corrente (Current Yield)"

    La misura di rendimento più semplice — reddito annuo rispetto al prezzo corrente:

    $$
    \text{Current Yield} = \frac{\text{Cedola Annuale}}{\text{Prezzo di Mercato Corrente}} \times 100
    $$

    Dove:

    - **Cedola Annuale** = pagamenti totali delle cedole all'anno (es. 40 € per un'obbligazione al 4% con valore nominale di 1.000 €)
    - **Prezzo di Mercato Corrente** = quanto pagheresti per acquistare l'obbligazione oggi

    Limite: ignora la plusvalenza/minusvalenza se mantenuta fino a scadenza.

??? example "📐 Rendimento a Scadenza (Yield to Maturity - YTM)"

    Il rendimento totale previsto se l'obbligazione viene mantenuta fino alla scadenza, tenendo conto di **tutti** i flussi di cassa: pagamenti delle cedole, rimborso del valore nominale e la differenza tra il prezzo di acquisto e il valore nominale.

    YTM è il tasso $y$ che soddisfa:

    $$
    P = \sum_{t=1}^{T} \frac{C}{(1+y)^t} + \frac{F}{(1+y)^T}
    $$

    Dove:

    - $P$ = prezzo di mercato corrente
    - $C$ = pagamento della cedola per periodo
    - $F$ = valore nominale (restituito alla scadenza)
    - $T$ = numero di periodi fino alla scadenza
    - $y$ = rendimento a scadenza (per periodo)

    L'YTM deve essere risolto numericamente (non esiste una soluzione a forma chiusa).

---

## 🧮 Come LibreFolio Gestisce gli Interessi

In LibreFolio, un evento `INTEREST` (e la corrispondente transazione di portafoglio) viene registrato con:

- **Date**: La data di pagamento degli interessi
- **Amount**: L'importo in contanti ricevuto
- **Currency**: La valuta del pagamento

### La Differenza Contabile: Interessi vs Dividendi
È fondamentale distinguere tra una transazione di **Interessi** e una di **Dividendi** a livello di database:

1. **Interessi (basati su Debito/Rendimento)**: Un pagamento di interessi rappresenta il rendimento su debiti o depositi di liquidità (es. conti di risparmio bancari, prestiti P2P o cedole obbligazionarie). Nel tracciamento del portafoglio a partita doppia, questi rappresentano entrate di cassa (`cash.amount > 0`) dove l'asset sottostante è opzionale. La transazione nel database richiede `quantity = 0` perché non vengono scambiate unità dell'asset durante un pagamento di interessi in contanti.
2. **Dividendi (basati su Equity)**: Un dividendo è una distribuzione di utili pagata agli azionisti. Richiede strettamente l'esistenza di un asset azionario sottostante (l'asset è obbligatorio), e l'erogazione dipende direttamente dal numero di azioni possedute alla data ex-date. Proprio come gli interessi, i dividendi sono puri movimenti di cassa (`quantity = 0`).

Per gli asset di provider di **investimento programmato**, gli eventi di interesse vengono generati automaticamente dal calendario di interessi configurato e influenzano direttamente il calcolo del prezzo. Per le obbligazioni con prezzo di mercato, fungono da indicatori informativi.

---

## 🔗 Correlati

- 📅 **[Panoramica Eventi Asset](index.md)** — Tutti i tipi di eventi
- 📆 **[Convenzioni di Conteggio dei Giorni](../../fundamentals/day-count.md)** — Come vengono calcolati i periodi di maturazione degli interessi
- 🏁 **[Regolamento alla Scadenza](maturity-settlement.md)** — Ritorno finale del capitale alla scadenza dell'obbligazione
- 📈 **[Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** — Misurare il rendimento totale
