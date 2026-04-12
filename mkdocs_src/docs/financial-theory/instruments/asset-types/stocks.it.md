# <img src="../../../static/icons/asset-types/stock.png" width="32" style="vertical-align: middle;" /> Azioni

Un'**azione** (o quota / equity) rappresenta la proprietà parziale di una società quotata in borsa. Quando acquisti un'azione, diventi un azionista con un diritto proporzionale agli asset e agli utili della società.

---

## 🔑 Caratteristiche Principali

| Proprietà | Dettaglio |
|----------|--------|
| **Codice in LibreFolio** | `STOCK` |
| **Prezzi** | Quotazioni in tempo reale o ritardate dalle borse (NYSE, NASDAQ, LSE, ecc.) |
| **Valuta** | Denominata in valuta locale della borsa |
| **Dividendi** | Molte azioni pagano dividendi periodici in contanti (trimestrali negli USA, semestrali in Europa) |
| **Split** | Le società possono frazionare le azioni (es. 4:1) per abbassare il prezzo per azione |
| **Provider tipici** | Yahoo Finance, CSS Scraper |

---

## 📊 Come Funzionano le Azioni

1. **Determinazione del prezzo**: Le azioni vengono scambiate su borse pubbliche durante gli orari di mercato. Il prezzo riflette l'offerta e la domanda.
2. **Dividendi**: Le società possono distribuire una parte degli utili agli azionisti. Questo crea un [Evento Dividendo](../asset-events/dividend.md) alla data ex.
3. **Plusvalenze**: La differenza tra il prezzo di acquisto e quello di vendita determina il profitto o la perdita. Vedi [Tassazione](../../fundamentals/taxation.md).
4. **Split**: Una società può frazionare le proprie azioni per migliorare la liquidità. Uno split 4:1 significa che ogni azione diventa 4 azioni a ¼ del prezzo. Vedi [Evento Split](../asset-events/split.md).

---

## 📐 Rendimento Totale

Il rendimento totale di un'azione include sia l'apprezzamento del prezzo che i dividendi:

$$
R_{total} = \frac{P_{end} - P_{start} + \sum D_i}{P_{start}}
$$

dove $D_i$ sono tutti i pagamenti di dividendi ricevuti durante il periodo della posizione.

---

## 🔗 Correlati

- 💰 **[Eventi Dividendo](../asset-events/dividend.md)** — Come i dividendi influenzano i prezzi delle azioni
- ✂️ **[Eventi Split](../asset-events/split.md)** — Split forward e reverse
- 📈 **[Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** — Misurare la performance delle azioni
