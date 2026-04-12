# 📊 Tipi di Asset

LibreFolio supporta un'ampia gamma di classi di asset per coprire un portafoglio diversificato. Ogni tipo di asset ha comportamenti specifici riguardanti la quotazione, i dividendi e la gestione fiscale.

## 📋 Asset Supportati

<table>
 <thead>
 <tr>
 <th style="width: 60px; text-align: center;">Icona</th>
 <th style="white-space: nowrap;">Tipo</th>
 <th style="white-space: nowrap;">Codice</th>
 <th>Descrizione</th>
 <th style="white-space: nowrap;">Dettagli</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/stock.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Azioni</strong></td>
 <td style="white-space: nowrap;"><code>STOCK</code></td>
 <td>Quote azionarie di una società. I prezzi sono tipicamente recuperati dalle borse pubbliche.</td>
 <td><a href="stocks/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/etf.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>ETF</strong></td>
 <td style="white-space: nowrap;"><code>ETF</code></td>
 <td>Exchange Traded Funds. Panieri di titoli che vengono scambiati come azioni.</td>
 <td><a href="etfs/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/bond.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Obbligazioni</strong></td>
 <td style="white-space: nowrap;"><code>BOND</code></td>
 <td>Titoli a reddito fisso che rappresentano un prestito a un emittente (governativo o societario).</td>
 <td><a href="bonds/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/crypto.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Crypto</strong></td>
 <td style="white-space: nowrap;"><code>CRYPTO</code></td>
 <td>Valute digitali e token (Bitcoin, Ethereum, ecc.).</td>
 <td><a href="crypto/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/crowdfunding.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>P2P / Crowdfunding</strong></td>
 <td style="white-space: nowrap;"><code>CROWDFUNDING</code></td>
 <td>Prestiti peer-to-peer o crowdfunding immobiliare. Spesso valutati tramite pagamenti di interessi programmati.</td>
 <td><a href="real-estate/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/fund.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Fondi Comuni</strong></td>
 <td style="white-space: nowrap;"><code>FUND</code></td>
 <td>Fondi di investimento gestiti professionalmente.</td>
 <td><a href="mutual-fund/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/hold.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Commodities</strong></td>
 <td style="white-space: nowrap;"><code>HOLD</code></td>
 <td>Asset fisici come Oro, Argento o Diamanti detenuti come riserva di valore a lungo termine.</td>
 <td><a href="commodities/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/other.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Altro</strong></td>
 <td style="white-space: nowrap;"><code>OTHER</code></td>
 <td>Qualsiasi altra classe di asset (es. Arte, Private Equity, Collezionabili).</td>
 <td><a href="other/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/other.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Indice &amp; Benchmark</strong></td>
 <td style="white-space: nowrap;"><code>—</code></td>
 <td>Indici di mercato (S&amp;P 500, MSCI World) utilizzati come benchmark di riferimento — non direttamente negoziabili.</td>
 <td><a href="index-benchmark/">📖</a></td>
 </tr>
 </tbody>
</table>

---

## 🔗 Correlati

- 💸 **[Tipi di Transazioni](../transaction-types/index.md)** — Operazioni che influenzano il tuo portafoglio
- 📅 **[Eventi degli Asset](../asset-events/index.md)** — Azioni societarie che influenzano i prezzi degli asset
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Implicazioni fiscali per classe di asset
