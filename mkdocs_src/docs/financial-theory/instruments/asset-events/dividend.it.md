# 💰 Dividendi

Un **dividendo** è una distribuzione di denaro pagata da una società (o fondo) ai suoi azionisti, che rappresenta una quota degli utili della società.

---

## 📖 Definizione

I dividendi sono pagamenti periodici effettuati dagli utili di una società ai suoi azionisti. Vengono tipicamente pagati trimestralmente (comune negli USA) o semestralmente/annualmente (comune in Europa). Anche gli ETF distribuiscono i dividendi raccolti dalle loro posizioni sottostanti.

**Date chiave** nel ciclo di vita del dividendo:

| Data | Significato |
|------|---------|
| **Data di dichiarazione**&nbsp; | Il consiglio di amministrazione annuncia l'importo del dividendo e le date |
| **Data ex-dividend**&nbsp; | Primo giorno di trading in cui gli acquirenti NON ricevono il dividendo. Il prezzo dell'azione tipicamente scende dell'importo del dividendo all'apertura del mercato. |
| **Data di registrazione**&nbsp; | La società verifica chi possiede le azioni (solitamente 1-2 giorni dopo la data ex) |
| **Data di pagamento**&nbsp; | Il denaro viene depositato nei conti degli azionisti |

---

## 📉 Impatto sul Prezzo di Mercato

Nella **data ex-dividend**, il prezzo dell'azione teoricamente scende dell'**esatto importo del dividendo**. Ciò accade perché i nuovi acquirenti in tale data non riceveranno il prossimo pagamento.

!!! example "Esempio"

    **Apple (AAPL)** quota a $180.00. Un dividendo trimestrale di $0.25 stacca il dividendo.

    - **Prima della chiusura data ex-dividend**: $180.00
    - **Apertura data ex-dividend** (teorica): $179.75
    - **Differenza**: −$0.25 (= importo del dividendo)

    In pratica, le forze di mercato possono fare sì che il prezzo di apertura effettivo sia diverso, ma la borsa **aggiusta il prezzo di riferimento** verso il basso di esattamente $0.25.

---

## 📊 Effetto sul Rendimento Totale

Sebbene il prezzo scenda dell'importo del dividendo, il **rendimento totale** (variazione del prezzo + dividendi ricevuti) rimane neutrale al momento del pagamento. Nel tempo, i dividendi reinvestiti generano un effetto composto significativo.

$$
\text{Total Return} = \frac{P_{\text{end}} - P_{\text{start}} + \sum D_i}{P_{\text{start}}}
$$

Dove $D_i$ rappresenta ogni singolo pagamento di dividendi ricevuto durante il periodo di detenzione.

---

## 🔢 Dividend Yield

Il **dividend yield** esprime il dividendo annuo come percentuale del prezzo attuale dell'azione:

$$
\text{Dividend Yield} = \frac{\text{Annual Dividends per Share}}{\text{Current Price per Share}} \times 100\%
$$

!!! tip "Range tipici"

    - Azioni growth: 0–1%
    - Società mature: 2–4%
    - High-yield / REITs: 4–8%+

---

## 🧮 Come LibreFolio Gestisce i Dividendi

In LibreFolio, un evento `DIVIDEND` viene registrato con:

- **Date**: La data ex-dividend
- **Amount**: Il pagamento in contanti per azione
- **Currency**: La valuta del pagamento (es. USD, EUR)

Per gli **asset a prezzo di mercato** (Yahoo Finance, justETF), gli eventi di dividendo sono informativi: spiegano il gap di prezzo della data ex ma non modificano il prezzo recuperato. Per gli asset di tipo **Scheduled Investment**, essi sono parte integrante del modello di prezzo.

---

## 🔗 Correlati

- 📅 **[Panoramica Eventi Asset](index.md)** — Tutti i tipi di eventi
- 💸 **[Tipi di Transazione](../transaction-types/index.md)** — Come appaiono i dividendi nelle transazioni del portafoglio
- 📈 **[Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** — Rendimento totale inclusi i dividendi
