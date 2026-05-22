# 💸 Tipi di Transazione

LibreFolio registra ogni evento finanziario come una transazione. Comprendere questi tipi è fondamentale per un tracciamento accurato del portafoglio e per la dichiarazione fiscale.

## 📋 Transazioni Singole

Queste operano indipendentemente su un singolo conto broker.

| | Tipo | Codice | Descrizione | Liquidità | Asset | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/buy.png){: width="32" } | **Acquisto / Vendita** | `BUY` / `SELL` | Acquisto o vendita di un asset. | ⬇️⬆️ | ⬆️⬇️ | [📖](buy-sell.md) |
| ![](../../../static/icons/transactions/deposit.png){: width="32" } | **Deposito / Prelievo** | `DEPOSIT` / `WITHDRAWAL` | Aggiunta o rimozione di liquidità da un conto broker. | ⬆️⬇️ | — | [📖](deposit-withdrawal.md) |
| ![](../../../static/icons/transactions/dividend.png){: width="32" } | **Dividendo** | `DIVIDEND` | Pagamento in liquidità da una posizione in azioni o ETF. | ⬆️ | — | [📖](dividend.md) |
| ![](../../../static/icons/transactions/fee.png){: width="32" } | **Commissione / Tassa** | `FEE` / `TAX` | Costi associati a operazioni, manutenzione del conto o tasse. | ⬇️ | — | [📖](fee.md) |
| ![](../../../static/icons/transactions/interest.png){: width="32" } | **Interesse** | `INTEREST` | Interessi ricevuti da liquidità, obbligazioni o prestiti P2P. | ⬆️ | — | [📖](interest.md) |
| ![](../../../static/icons/transactions/adjustment.png){: width="32" } | **Adeguamento** | `ADJUSTMENT` | Correzione manuale dei saldi. | ± | ± | [📖](adjustment.md) |

## 🔀 Transazioni Composite

Queste rappresentano movimenti **tra** conti o valute. Generano due voci collegate che si compensano a vicenda.

| | Tipo | Codice | Descrizione | Liquidità | Asset | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/transfer.png){: width="32" } | **Trasferimento Asset** | `TRANSFER` | Spostamento di titoli tra broker. | — | ⬆️⬇️ | [📖](transfer.md) |
| ![](../../../static/icons/transactions/cash-transfer.png){: width="32" } | **Trasferimento Liquidità** | `CASH_TRANSFER` | Bonifico tra broker. | ⬆️⬇️ | — | [📖](cash-transfer.md) |
| ![](../../../static/icons/transactions/fx-conversion.png){: width="32" } | **Conversione FX** | `FX_CONVERSION` | Conversione valutaria all'interno di un broker. | ⬆️⬇️ | — | [📖](fx-conversion.md) |

---

## 🔗 Correlati

- 📊 **[Tipi di Asset](../asset-types/index.md)** — Gli strumenti su cui operano queste transazioni
- 📅 **[Eventi Asset](../asset-events/index.md)** — Eventi globali rispetto a transazioni personali
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Implicazioni fiscali delle transazioni
