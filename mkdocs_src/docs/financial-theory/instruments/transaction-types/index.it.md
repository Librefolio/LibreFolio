# 💸 Tipi di Transazione

LibreFolio registra ogni evento finanziario come una transazione. Comprendere questi tipi è fondamentale per un tracciamento accurato del portafoglio e per la dichiarazione fiscale.

## 📋 Transazioni Singole

Queste operano indipendentemente su un singolo conto broker.

| | Tipo | Codice | Descrizione | Liquidità | Asset | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/buy.png){: width="32" } ![](../../../static/icons/transactions/sell.png){: width="32" } | **Acquisto / Vendita** | `BUY` / `SELL` | Acquisto o vendita di un asset. | ⬇️⬆️ | ⬆️⬇️ | [📖](buy-sell.md) |
| ![](../../../static/icons/transactions/deposit.png){: width="32" } ![](../../../static/icons/transactions/withdrawal.png){: width="32" } | **Deposito / Prelievo** | `DEPOSIT` / `WITHDRAWAL` | Aggiunta o rimozione di liquidità da un conto broker. | ⬆️⬇️ | — | [📖](deposit-withdrawal.md) |
| ![](../../../static/icons/transactions/dividend.png){: width="32" } ![](../../../static/icons/transactions/interest.png){: width="32" } | **Dividendo / Interesse** | `DIVIDEND` / `INTEREST` | Rendimento ricevuto da asset azionari o a reddito fisso. | ⬆️ | — | [📖](dividend-interest.md) |
| ![](../../../static/icons/transactions/fee.png){: width="32" } ![](../../../static/icons/transactions/tax.png){: width="32" } | **Commissione / Tassa** | `FEE` / `TAX` | Costi associati alle operazioni, manutenzione del conto o tasse. | ⬇️ | — | [📖](fee.md) |
| ![](../../../static/icons/transactions/adjustment.png){: width="32" } | **Rettifica** | `ADJUSTMENT` | Correzione manuale dei saldi. | ± | ± | [📖](adjustment.md) |

## 🔀 Transazioni Composte

Queste rappresentano movimenti **tra** conti o valute. Producono due voci collegate che si bilanciano a vicenda.

| | Tipo | Codice | Descrizione | Liquidità | Asset | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/transfer.png){: width="32" } | **Trasferimento Asset** | `TRANSFER` | Spostamento di titoli tra broker. | — | ⬆️⬇️ | [📖](transfer.md) |
| ![](../../../static/icons/transactions/cash-transfer.png){: width="32" } | **Trasferimento Liquidità** | `CASH_TRANSFER` | Bonifico tra broker. | ⬆️⬇️ | — | [📖](cash-transfer.md) |
| ![](../../../static/icons/transactions/fx-conversion.png){: width="32" } | **Conversione Valutaria** | `FX_CONVERSION` | Cambio valuta all'interno di un broker. | ⬆️⬇️ | — | [📖](fx-conversion.md) |

---

## 🔗 Correlati

- 📊 **[Tipi di Asset](../asset-types/index.md)** — Gli strumenti su cui agiscono queste transazioni
- 📅 **[Eventi Asset](../asset-events/index.md)** — Eventi globali vs transazioni personali
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Implicazioni fiscali delle transazioni
