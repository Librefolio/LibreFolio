# 🔌 Fournisseurs

Un fournisseur maintient les prix d'un actif à jour pour vous : le prix du jour, son historique et, pour certains, des détails tels que le type ou le secteur. Chaque actif a au plus un fournisseur : choisissez un résultat de **Recherche en ligne** pour le connecter, ou configurez-le vous-même dans **Attribution du fournisseur** — voir [Créer et modifier](../create-edit.md).

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="yahoo-finance/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon Yahoo Finance">
            <span class="card-title" style="margin: 0;">Yahoo Finance</span>
        </div>
        <span class="card-desc">Actions, ETF, fonds et cryptomonnaies des bourses du monde entier.</span>
    </a>
    <a href="justetf/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon justETF">
            <span class="card-title" style="margin: 0;">justETF</span>
        </div>
        <span class="card-desc">Comparaison d'ETF européens, prix et structures d'actifs.</span>
    </a>
    <a href="borsa-italiana/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon Borsa Italiana">
            <span class="card-title" style="margin: 0;">Borsa Italiana</span>
        </div>
        <span class="card-desc">Actions, obligations, ETF et fonds italiens, en italien ou en anglais.</span>
    </a>
    <a href="css-scraper/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="../../../static/cssscraper.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icône CSS Scraper">
            <span class="card-title" style="margin: 0;">CSS Scraper</span>
        </div>
        <span class="card-desc">Scraper de sélecteurs de page web pour les prix d'obligations personnalisés ou exotiques.</span>
    </a>
    <a href="scheduled-investment/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="../../../static/scheduled_investment.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icône Investissement programmé">
            <span class="card-title" style="margin: 0;">Investissement programmé</span>
        </div>
        <span class="card-desc">Actifs à revenu fixe dont la valeur est calculée via des calendriers d'intérêts.</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
     <div style="display: flex; align-items: center; gap: 0.75rem;">
     <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
     <span class="card-title" style="margin: 0;">Demander un nouveau plugin</span>
     </div>
     <span class="card-desc">Votre fournisseur de prix est manquant ? Demandez un nouveau plugin ou contribuez au code !</span>
    </a>
    </div>

## 📊 Comparaison des fournisseurs

| Fournisseur | Prix actuel | Historique | Recherche | Détails | Identifiant | Idéal pour |
|----------|:---:|:---:|:---:|:---:|---|---|
| <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Yahoo Finance** | ✅ | ✅ | ✅ | ✅ | Symbole (`AAPL`, `VWCE.DE`) ou ISIN | Actions, ETF, fonds et cryptomonnaies du monde entier |
| <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **justETF** | ✅ | ✅ | ✅ | ✅ | ISIN (`IE00B4L5Y983`) | ETF européens, valorisés en EUR, USD, CHF ou GBP |
| <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Borsa Italiana** | ✅ | ✅ | ✅ | ✅ | ISIN (`IT0003128367`) | Instruments cotés à Milan, fonds communs de placement italiens |
| <img src="../../../static/cssscraper.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **CSS Scraper** | ✅ | ❌ | ❌ | ❌ | URL de la page | Un prix affiché sur n'importe quelle page web publique |
| <img src="../../../static/scheduled_investment.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Investissement programmé** | ✅ | ✅ | ❌ | ❌ | Aucun — créé pour vous | Dépôts, prêts et obligations évalués par leurs intérêts |

Les **détails** sont le type, la devise, la description et les données similaires que LibreFolio propose de remplir pour vous. Certains fournisseurs enregistrent également des [événements d'actifs](../detail/events.md) : dividendes (Yahoo Finance, justETF), divisions (Yahoo Finance), paiements d'intérêts et échéance (Investissement programmé).

## 🎯 Choisir un fournisseur

- **Actions, ETF ou cryptomonnaies sur n'importe quelle bourse** → **Yahoo Finance**.
- **Un ETF européen**, ou des prix d'ETF en USD, CHF ou GBP → **justETF**.
- **Actions, obligations, ETF ou fonds négociés à Milan**, et fonds communs de placement italiens → **Borsa Italiana**.
- **Un prix affiché uniquement sur une page web** → **CSS Scraper**.
- **Un compte d'épargne, un dépôt à terme, un prêt P2P ou une obligation suivis par leurs intérêts** →
  **Investissement programmé**.
- **Rien ne correspond ?** Cochez **Aucun fournisseur** et saisissez les prix vous-même dans l'[Éditeur de données](../detail/data-editor.md).

## 🔗 Voir aussi

- 🛠️ **Pour les développeurs : [Fournisseurs d'actifs](../../../developer/backend/assets/system_providers.md)** — Comment chaque fournisseur fonctionne en interne
