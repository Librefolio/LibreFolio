# 💸 Tipi di Transazione

LibreFolio registra ogni evento finanziario come una transazione. Comprendere questi tipi è fondamentale per un monitoraggio accurato del portafoglio e per la rendicontazione fiscale.

## 📋 Transazioni Supportate

| | Type | Code | Description | Cash | Asset | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/buy.png){: width="32" } | **Acquisto / Vendita** | `BUY` / `SELL` | Acquisto o vendita di un asset. | ⬇️⬆️ | ⬆️⬇️ | [📖](buy-sell.md) |
| ![](../../../static/icons/transactions/deposit.png){: width="32" } | **Deposito / Prelievo** | `DEPOSIT` / `WITHDRAWAL` | Aggiunta o rimozione di liquidità da un conto broker. | ⬆️⬇️ | — | [📖](deposit-withdrawal.md) |
| ![](../../../static/icons/transactions/dividend.png){: width="32" } | **Dividendo** | `DIVIDEND` | Pagamento in liquidità da una posizione in azioni o ETF. | ⬆️ | — | [📖](dividend.md) |
| ![](../../../static/icons/transactions/fee.png){: width="32" } | **Commissione / Tassa** | `FEE` / `TAX` | Costi associati a operazioni, gestione del conto o tasse. | ⬇️ | — | [📖](fee.md) |
| ![](../../../static/icons/transactions/interest.png){: width="32" } | **Interesse** | `INTEREST` | Interessi ricevuti da liquidità, obbligazioni o prestiti P2P. | ⬆️ | — | [📖](interest.md) |
| ![](../../../static/icons/transactions/transfer.png){: width="32" } | **Trasferimento / FX** | `TRANSFER_IN/OUT` / `FX_CONVERSION` | Spostamento di asset tra portafogli o conversione di valute. | variabile | variabile | [📖](transfer.md) |

---

## 🔗 Correlati

- 📊 **[Tipi di Asset](../asset-types/index.md)** — Gli strumenti su cui agiscono queste transazioni
- 📅 **[Eventi Asset](../asset-events/index.md)** — Eventi globali vs transazioni personali
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Implicazioni fiscali delle transazioni
