# 📊 Types d'actifs

LibreFolio prend en charge un large éventail de classes d'actifs afin de couvrir un portefeuille diversifié. Chaque type d'actif possède des règles de gestion spécifiques concernant la tarification, les dividendes et la gestion fiscale.

## 📋 Actifs pris en charge

<table>
 <thead>
 <tr>
 <th style="width: 60px; text-align: center;">Icône</th>
 <th style="white-space: nowrap;">Type</th>
 <th style="white-space: nowrap;">Code</th>
 <th>Description</th>
 <th style="white-space: nowrap;">Détails</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/stock.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Action</strong></td>
 <td style="white-space: nowrap;"><code>STOCK</code></td>
 <td>Parts de capital d'une entreprise. Les prix sont généralement récupérés depuis les marchés boursiers.</td>
 <td><a href="stocks/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/etf.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>ETF</strong></td>
 <td style="white-space: nowrap;"><code>ETF</code></td>
 <td>Exchange Traded Funds. Paniers de titres qui s'échangent comme des actions.</td>
 <td><a href="etfs/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/bond.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Obligation</strong></td>
 <td style="white-space: nowrap;"><code>BOND</code></td>
 <td>Titres à revenu fixe représentant un prêt à un emprunteur (gouvernemental ou d'entreprise).</td>
 <td><a href="bonds/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/crypto.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Crypto</strong></td>
 <td style="white-space: nowrap;"><code>CRYPTO</code></td>
 <td>Monnaies numériques et jetons (Bitcoin, Ethereum, etc.).</td>
 <td><a href="crypto/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/crowdfunding.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>P2P / Crowdfunding</strong></td>
 <td style="white-space: nowrap;"><code>CROWDFUNDING</code></td>
 <td>Prêts entre particuliers ou financement participatif immobilier. Souvent valorisés via des paiements d'intérêts programmés.</td>
 <td><a href="real-estate/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/fund.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Fonds commun de placement</strong></td>
 <td style="white-space: nowrap;"><code>FUND</code></td>
 <td>Fonds d'investissement gérés professionnellement.</td>
 <td><a href="mutual-fund/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/hold.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Matières premières</strong></td>
 <td style="white-space: nowrap;"><code>HOLD</code></td>
 <td>Actifs physiques comme l'or, l'argent ou les diamants détenus pour leur valeur à long terme.</td>
 <td><a href="commodities/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/other.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Autre</strong></td>
 <td style="white-space: nowrap;"><code>OTHER</code></td>
 <td>Toute autre classe d'actifs (ex: Art, Private Equity, Objets de collection).</td>
 <td><a href="other/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/asset-types/other.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Index &amp; Benchmark</strong></td>
 <td style="white-space: nowrap;"><code>—</code></td>
 <td>Index de marché (S&amp;P 500, MSCI World) utilisés comme benchmarks — non négociables directement.</td>
 <td><a href="index-benchmark/">📖</a></td>
 </tr>
 </tbody>
</table>

---

## 🔗 Liens connexes

- 💸 **[Types de transactions](../transaction-types/index.md)** — Opérations qui affectent votre portefeuille
- 📅 **[Événements d'actifs](../asset-events/index.md)** — Opérations sur titres affectant le prix des actifs
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Implications fiscales par classe d'actifs
