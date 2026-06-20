# 💰 Dividendo

Un **dividendo** è una distribuzione di liquidità pagata da una società (o un fondo) ai suoi azionisti, che rappresenta una quota degli utili dell'azienda.

---

## 📖 Definizione

I dividendi sono pagamenti periodici effettuati dagli utili di una società ai suoi azionisti. Vengono solitamente pagati trimestralmente (comune negli Stati Uniti) o semestralmente/annualmente (comune in Europa). Anche gli ETF distribuiscono i dividendi raccolti dalle loro posizioni sottostanti.

**Date chiave** nel ciclo di vita del dividendo:

| Data | Significato |
|------|---------|
| **Data di dichiarazione**&nbsp; | Il consiglio di amministrazione annuncia l'importo e le date del dividendo |
| **Data ex-dividend**&nbsp; | Primo giorno di trading in cui gli acquirenti NON ricevono il dividendo. Il prezzo del titolo solitamente scende dell'importo del dividendo all'apertura del mercato. |
| **Data di registrazione**&nbsp; | La società verifica chi possiede le azioni (solitamente 1-2 giorni dopo la data ex) |
| **Data di pagamento**&nbsp; | La liquidità viene accreditata sui conti degli azionisti |

---

## 📉 Impatto sul Prezzo di Mercato

Nella **data ex-dividend**, il prezzo del titolo teoricamente scende dell'**esatto importo del dividendo**. Ciò accade perché i nuovi acquirenti in tale data non riceveranno il pagamento imminente.

!!! example "Example"

    **Apple (AAPL)** quota a $180.00. Un dividendo trimestrale di $0.25 stacca il dividendo (ex-date).

    - **Prima della chiusura della data ex**: $180.00
    - **Apertura data ex** (teorica): $179.75
    - **Differenza**: −$0.25 (= importo del dividendo)

    In pratica, le forze di mercato possono far variare il prezzo di apertura effettivo, ma la borsa **aggiusta il prezzo di riferimento** verso il basso esattamente di $0.25.

---

## 📊 Effetto sul Rendimento Totale

Mentre il prezzo scende dell'importo del dividendo, il **rendimento totale** (variazione di prezzo + dividendi ricevuti) rimane neutrale al momento del pagamento. Nel tempo, i dividendi reinvestiti generano un effetto di capitalizzazione significativo.

$$
\text{Total Return} = \frac{P_{\text{end}} - P_{\text{start}} + \sum D_i}{P_{\text{start}}}
$$

Dove $D_i$ rappresenta ogni pagamento di dividendo ricevuto durante il periodo di detenzione.

---

## 🔢 Dividend Yield

Il **dividend yield** (rendimento da dividendo) esprime il dividendo annuale come percentuale del prezzo attuale dell'azione:

$$
\text{Dividend Yield} = \frac{\text{Annual Dividends per Share}}{\text{Current Price per Share}} \times 100\%
$$

!!! tip "Typical ranges"

    - Titoli growth: 0–1%
    - Società mature: 2–4%
    - High-yield / REITs: 4–8%+

---

## 🧮 Come LibreFolio Gestisce i Dividendi

In LibreFolio, un evento `DIVIDEND` (e la corrispondente transazione di portafoglio) viene registrato con:

- **Date**: La data ex-dividend
- **Amount**: L'importo del pagamento in contanti per azione
- **Currency**: La valuta del pagamento (es. USD, EUR)

### La Differenza Contabile: Dividendo vs Interesse
È fondamentale distinguere tra una transazione di **Dividendo** e una di **Interesse** a livello di database:

1. **Dividendo (basato su Equity)**: Nel tracciamento di portafoglio a partita doppia, un dividendo rappresenta un ingresso di cassa (`cash.amount > 0`) generato dal possesso di azioni di un asset azionario specifico. Il numero di azioni possedute alla data ex rimane costante — non vengono aggiunte o rimosse nuove azioni durante questo pagamento in contanti. Pertanto, la transazione nel database richiede `quantity = 0` per evitare doppi conteggi o il gonfiamento del saldo delle azioni. Qualsiasi informazione sul numero di azioni che hanno generato il pagamento è trattata come *informativa* e viene solitamente memorizzata nel campo della descrizione.
2. **Interesse (basato su Debito/Rendimento)**: Un pagamento di interessi rappresenta il rendimento su debiti o depositi di liquidità (es. conti di risparmio o cedole obbligazionarie). A differenza dei dividendi, gli interessi non richiedono strettamente l'esistenza di un asset azionario sottostante (l'asset è opzionale).

Per gli **asset con prezzo di mercato** (Yahoo Finance, justETF), gli eventi di dividendo sono informativi — spiegano il gap di prezzo alla data ex ma non modificano il prezzo recuperato. Per gli asset di **Investimento Programmato**, essi sono parte integrante del modello di prezzo.

---

## 🔗 Correlati

- 📅 **[Panoramica Eventi Asset](index.md)** — Tutti i tipi di eventi
- 💸 **[Tipi di Transazione](../transaction-types/index.md)** — Come appaiono i dividendi nelle transazioni di portafoglio
- 📈 **[Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** — Rendimento totale inclusi i dividendi
