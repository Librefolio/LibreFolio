# 📊 Tipi di Asset

LibreFolio supporta un'ampia gamma di classi di asset per coprire un portafoglio diversificato. Ogni tipo di asset ha comportamenti specifici riguardanti la quotazione, i dividendi e la gestione fiscale.

## 📋 Asset Supportati

| | Type | Code | Description | |
|:---:|:---|:---|---|:---:|
| ![](../../../static/icons/asset-types/stock.png){: width="32" } | **Stock** | `STOCK` | Quote azionarie di una società. I prezzi sono tipicamente recuperati dalle borse pubbliche. | [📖](stocks.md) |
| ![](../../../static/icons/asset-types/etf.png){: width="32" } | **ETF** | `ETF` | Exchange Traded Funds. Panieri di titoli che vengono scambiati come azioni. | [📖](etfs.md) |
| ![](../../../static/icons/asset-types/bond.png){: width="32" } | **Bond** | `BOND` | Titoli a reddito fisso che rappresentano un prestito a un emittente (governativo o societario). | [📖](bonds.md) |
| ![](../../../static/icons/asset-types/crypto.png){: width="32" } | **Crypto** | `CRYPTO` | Valute digitali e token (Bitcoin, Ethereum, ecc.). | [📖](crypto.md) |
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | **P2P / Crowdfunding** | `CROWDFUND` | Prestiti peer-to-peer o crowdfunding immobiliare. Spesso valutati tramite pagamenti di interessi programmati. | [📖](real-estate.md) |
| ![](../../../static/icons/asset-types/fund.png){: width="32" } | **Fondi Comuni** | `FUND` | Fondi di investimento gestiti professionalmente. | [📖](mutual-fund.md) |
| ![](../../../static/icons/asset-types/hold.png){: width="32" } | **Commodities** | `HOLD` | Asset fisici come Oro, Argento o Diamanti detenuti come riserva di valore a lungo termine. | [📖](commodities.md) |
| ![](../../../static/icons/asset-types/other.png){: width="32" } | **Altro** | `OTHER` | Qualsiasi altra classe di asset (es. Arte, Private Equity, Collezionabili). | [📖](other.md) |
| ![](../../../static/icons/asset-types/other.png){: width="32" } | **Indice &amp; Benchmark** | `—` | Indici di mercato (S&amp;P 500, MSCI World) utilizzati come benchmark di riferimento — non direttamente negoziabili. | [📖](index-benchmark.md) |

---

## 🔗 Correlati

- 💸 **[Tipi di Transazioni](../transaction-types/index.md)** — Operazioni che influenzano il tuo portafoglio
- 📅 **[Eventi degli Asset](../asset-events/index.md)** — Azioni societarie che influenzano i prezzi degli asset
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Implicazioni fiscali per classe di asset
