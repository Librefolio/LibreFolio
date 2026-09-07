# 🔌 Fournisseurs de Prix

LibreFolio prend en charge plusieurs fournisseurs de prix pour récupérer automatiquement les prix actuels et les données historiques de vos actifs.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="yahoo-finance/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Yahoo Finance favicon">
            <span class="card-title" style="margin: 0;">Yahoo Finance</span>
        </div>
        <span class="card-desc">Fournisseur par défaut pour actions mondiales, ETF et fonds communs.</span>
    </a>
    <a href="justetf/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="justETF favicon">
            <span class="card-title" style="margin: 0;">justETF</span>
        </div>
        <span class="card-desc">Comparaison des ETF européens, prix et structures d'actifs.</span>
    </a>
    <a href="borsa-italiana/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Borsa Italiana favicon">
            <span class="card-title" style="margin: 0;">Borsa Italiana</span>
        </div>
        <span class="card-desc">Actions italiennes, obligations, ETF et fonds avec recherche URL intelligente.</span>
    </a>
    <a href="css-scraper/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="../../../static/cssscraper.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="CSS Scraper icon">
            <span class="card-title" style="margin: 0;">CSS Scraper</span>
        </div>
        <span class="card-desc">Scraper de pages web pour prix d'obligations personnalisées ou exotiques.</span>
    </a>
    <a href="scheduled-investment/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="../../../static/scheduled_investment.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Scheduled Investment icon">
            <span class="card-title" style="margin: 0;">Investissement Programmé</span>
        </div>
        <span class="card-desc">Actifs à revenu fixe calculant leur valeur via des calendriers de taux d'intérêt.</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
     <div style="display: flex; align-items: center; gap: 0.75rem;">
     <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
     <span class="card-title" style="margin: 0;">Demander un Nouveau Plugin</span>
     </div>
     <span class="card-desc">Votre fournisseur de prix est manquant ? Demandez un nouveau plugin ou contribuez !</span>
    </a>
</div>

## 📊 Comparaison des Fournisseurs

| Fournisseur | Prix Actuel | Historique | Recherche | Identifiant | Remarques |
|----------|:---:|:---:|:---:|---|---|
| <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Yahoo Finance** | ✅ | ✅ | ✅ | Ticker (ex. `AAPL`, `VWCE.DE`) | Meilleur pour actions, ETF, fonds communs |
| <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **justETF** | ✅ (EUR) | ✅ | ✅ | ISIN (ex. `IE00BK5BQT80`) | ETF européens, multi-devises |
| <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Borsa Italiana** | ✅ | ✅ | ✅ | ISIN ; les fonds utilisent un code interne | Actions italiennes, obligations, ETF et fonds. NAV des fonds valeur courante uniquement si datée d'aujourd'hui. |
| <img src="../../../static/cssscraper.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **CSS Scraper** | ✅ | ❌ | ❌ | URL | Extrait les données de prix de n'importe quelle page web |
| <img src="../../../static/scheduled_investment.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Investissement Programmé** | ✅ | ✅ | ❌ | Auto-généré | Instruments à revenu fixe avec calendriers d'intérêts |

## 🎯 Choisir un Fournisseur

- **Actions & ETF** : Utilisez **Yahoo Finance** — couverture la plus large, supporte la recherche
- **ETF Européens** : Utilisez **justETF** pour des données plus détaillées sur les ETF européens
- **Borsa Italiana** : Utilisez Borsa Italiana directement pour les actions, obligations, ETF et fonds Euronext Milano. La recherche intelligente peut également résoudre les URL Borsa et capturer automatiquement les paramètres.
- **Comptes d'épargne / Dépôts à terme** : Utilisez **Investissement Programmé** avec des calendriers d'intérêts
