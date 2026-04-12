# 📊 Asset Types

LibreFolio supports a wide range of asset classes to cover a diversified portfolio. Each asset type has specific behaviors regarding pricing, dividends, and tax handling.

## 📋 Supported Assets

<table>
  <thead>
    <tr>
      <th style="width: 60px; text-align: center;">Icon</th>
      <th style="white-space: nowrap;">Type</th>
      <th style="white-space: nowrap;">Code</th>
      <th>Description</th>
      <th style="white-space: nowrap;">Details</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/asset-types/stock.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Stock</strong></td>
      <td style="white-space: nowrap;"><code>STOCK</code></td>
      <td>Equity shares in a company. Prices are typically fetched from public exchanges.</td>
      <td><a href="stocks/">📖</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/asset-types/etf.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>ETF</strong></td>
      <td style="white-space: nowrap;"><code>ETF</code></td>
      <td>Exchange Traded Funds. Baskets of securities that trade like stocks.</td>
      <td><a href="etfs/">📖</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/asset-types/bond.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Bond</strong></td>
      <td style="white-space: nowrap;"><code>BOND</code></td>
      <td>Fixed-income securities representing a loan to a borrower (government or corporate).</td>
      <td><a href="bonds/">📖</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/asset-types/crypto.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Crypto</strong></td>
      <td style="white-space: nowrap;"><code>CRYPTO</code></td>
      <td>Digital currencies and tokens (Bitcoin, Ethereum, etc.).</td>
      <td><a href="crypto/">📖</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/asset-types/crowdfunding.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>P2P / Crowdfunding</strong></td>
      <td style="white-space: nowrap;"><code>CROWDFUNDING</code></td>
      <td>Peer-to-peer loans or real estate crowdfunding. Often valued via scheduled interest payments.</td>
      <td><a href="real-estate/">📖</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/asset-types/fund.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Mutual Fund</strong></td>
      <td style="white-space: nowrap;"><code>FUND</code></td>
      <td>Professionally managed investment funds.</td>
      <td><a href="mutual-fund/">📖</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/asset-types/hold.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Commodities</strong></td>
      <td style="white-space: nowrap;"><code>HOLD</code></td>
      <td>Physical assets like Gold, Silver, or Diamonds held for long-term value.</td>
      <td><a href="commodities/">📖</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/asset-types/other.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Other</strong></td>
      <td style="white-space: nowrap;"><code>OTHER</code></td>
      <td>Any other asset class (e.g., Art, Private Equity, Collectibles).</td>
      <td><a href="other/">📖</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/asset-types/other.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Index &amp; Benchmark</strong></td>
      <td style="white-space: nowrap;"><code>—</code></td>
      <td>Market indexes (S&amp;P 500, MSCI World) used as reference benchmarks — not directly tradeable.</td>
      <td><a href="index-benchmark/">📖</a></td>
    </tr>
  </tbody>
</table>

---

## 🔗 Related

- 💸 **[Transaction Types](../transaction-types/index.md)** — Operations that affect your portfolio
- 📅 **[Asset Events](../asset-events/index.md)** — Corporate actions affecting asset prices
- 💰 **[Taxation](../../fundamentals/taxation.md)** — Tax implications by asset class

