# 🔌 Fournisseurs

LibreFolio prend en charge plusieurs fournisseurs de prix pour récupérer automatiquement les cours actuels et les données historiques de vos actifs.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
 <a href="yahoo-finance/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Yahoo Finance favicon">
 <span class="card-title" style="margin: 0;">Yahoo Finance</span>
 </div>
 <span class="card-desc">Fournisseur par défaut pour les actions mondiales, les ETF et les fonds communs de placement.</span>
 </a>
 <a href="justetf/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="justETF favicon">
 <span class="card-title" style="margin: 0;">justETF</span>
 </div>
 <span class="card-desc">Comparaison d'ETF européens, prix et structures d'actifs.</span>
 </a>
 <a href="borsa-italiana/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Borsa Italiana favicon">
 <span class="card-title" style="margin: 0;">Borsa Italiana</span>
 </div>
 <span class="card-desc">Intégration de la bourse italienne pour les instruments Euronext.</span>
 </a>
 <a href="css-scraper/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="../../static/cssscraper.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="CSS Scraper icon">
 <span class="card-title" style="margin: 0;">CSS Scraper</span>
 </div>
 <span class="card-desc">Scraper via sélecteur de page web pour des prix d'obligations personnalisés ou des actifs exotiques.</span>
 </a>
 <a href="scheduled-investment/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="../../static/scheduled_investment.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Scheduled Investment icon">
 <span class="card-title" style="margin: 0;">Investissement Programmé</span>
 </div>
 <span class="card-desc">Actifs à revenu fixe calculant la valeur via des échéanciers d'intérêts.</span>
 </a>
</div>

## 📊 Comparaison des fournisseurs

| Fournisseur | Prix actuel | Historique | Recherche | Identifiant | Notes |
|----------|:---:|:---:|:---:|---|---|
| <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Yahoo Finance** | ✅ | ✅ | ✅ | Ticker (ex: `AAPL`, `VWCE.DE`) | Idéal pour les actions, ETF, fonds communs |
| <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **justETF** | ✅ (EUR) | ✅ | ✅ | ISIN (ex: `IE00BK5BQT80`) | ETF européens, multi-devises |
| <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Borsa Italiana** | ✅ | ✅ | ✅ | ISIN ou code alpha | Actions, obligations et ETF italiens |
| <img src="../../static/cssscraper.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **CSS Scraper** | ✅ | ❌ | ❌ | URL | Scrape les données de prix de n'importe quelle page web |
| <img src="../../static/scheduled_investment.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Investissement Programmé** | ✅ | ✅ | ❌ | Auto-généré | Instruments à revenu fixe avec échéanciers d'intérêts |

## 🎯 Choisir un fournisseur

- **Actions & ETF** : Utilisez **Yahoo Finance** — couverture la plus large, permet la recherche
- **ETF Européens** : Utilisez **justETF** pour des données plus détaillées sur les ETF européens
- **Borsa Italiana** : Utilisez Borsa Italiana directement pour les cotations Euronext Milano
- **Obligations sur Borsa Italiana** : Utilisez **CSS Scraper** pour scraper les prix directement du web
- **Comptes d'épargne / Dépôts à terme** : Utilisez **Investissement Programmé** avec des échéanciers d'intérêts
