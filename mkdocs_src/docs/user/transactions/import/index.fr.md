# 📥 Importer depuis le courtier (BRIM)

**BRIM** (Broker Report Import Module) vous permet d'importer des transactions directement depuis les fichiers d'exportation de votre courtier — sans saisie manuelle. Téléchargez un rapport CSV et LibreFolio analyse, fait correspondre et importe toutes les transactions en une seule opération.

Pour des instructions étape par étape sur le fonctionnement de l'assistant, consultez le **[Guide d'importation](how-to.md)**.

---

## 🏦 Courtiers pris en charge

LibreFolio prend en charge l'importation de fichiers de relevés provenant des courtiers suivants :

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
 <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="IBKR favicon">
 <span class="card-title" style="margin: 0;">Interactive Brokers</span>
 </div>
 <span class="card-desc">Importez des rapports de transactions à l'aide de Flex Queries.</span>
 </a>
 <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Degiro favicon">
 <span class="card-title" style="margin: 0;">Degiro</span>
 </div>
 <span class="card-desc">Importez les exportations CSV de l'historique des transactions depuis Degiro.</span>
 </a>
 <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="eToro favicon">
 <span class="card-title" style="margin: 0;">eToro</span>
 </div>
 <span class="card-desc">Importez les fichiers de relevés de compte XLSX/CSV depuis eToro.</span>
 </a>
 <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Directa SIM favicon">
 <span class="card-title" style="margin: 0;">Directa SIM</span>
 </div>
 <span class="card-desc">Importez les fichiers CSV de l'historique des transactions depuis Directa SIM.</span>
 </a>
 <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Charles Schwab favicon">
 <span class="card-title" style="margin: 0;">Charles Schwab</span>
 </div>
 <span class="card-desc">Importez l'historique des transactions CSV depuis Charles Schwab.</span>
 </a>
 <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Revolut favicon">
 <span class="card-title" style="margin: 0;">Revolut</span>
 </div>
 <span class="card-desc">Importez les rapports de relevés de compte PDF/CSV depuis Revolut.</span>
 </a>
 <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Coinbase favicon">
 <span class="card-title" style="margin: 0;">Coinbase</span>
 </div>
 <span class="card-desc">Importez les fichiers CSV de l'historique des transactions depuis Coinbase.</span>
 </a>
 <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Freetrade favicon">
 <span class="card-title" style="margin: 0;">Freetrade</span>
 </div>
 <span class="card-desc">Importez les relevés de transactions CSV depuis Freetrade.</span>
 </a>
 <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Finpension favicon">
 <span class="card-title" style="margin: 0;">Finpension</span>
 </div>
 <span class="card-desc">Importez les rapports CSV de l'historique des transactions depuis Finpension.</span>
 </a>
 <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.trading212.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Trading212 favicon">
 <span class="card-title" style="margin: 0;">Trading212</span>
 </div>
 <span class="card-desc">Importez l'historique des transactions CSV depuis Trading212.</span>
 </a>
 <a href="generic-csv/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" style="color: var(--md-accent-fg-color);"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg>
 <span class="card-title" style="margin: 0;">CSV Générique</span>
 </div>
 <span class="card-desc">Notre analyseur fallback avec mappage manuel des colonnes.</span>
 </a>
 <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
 <span class="card-title" style="margin: 0;">Demander un nouveau plugin</span>
 </div>
 <span class="card-desc">Votre courtier est manquant ? Demandez un nouveau plugin ou contribuez au code !</span>
 </a>
</div>

??? info "📊 Capacités de l'importateur"

    | Courtier | Statut | Format | Achat/Vente | Dividendes | Dépôts/Espèces | Frais/Taxes | Remarques |
    | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
    | <img src="https://www.interactivebrokers.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Interactive Brokers** | 🧪 Bêta | CSV (Flex) | ✅ | ✅ | ✅ | ✅ | Meilleur pour les comptes multi-devises |
    | <img src="https://www.degiro.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Degiro** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Prise en charge des relevés de compte standard |
    | <img src="https://www.etoro.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **eToro** | 🧪 Bêta | XLSX/CSV | ✅ | ✅ | ✅ | ✅ | Prise en charge des plus-values réalisées et des dividendes |
    | <img src="https://www.directa.it/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Directa SIM** | ✅ Stable | CSV | ✅ | ✅ | ✅ | ✅ | Prise en charge des relevés fiscaux des courtiers italiens |
    | <img src="https://www.schwab.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Charles Schwab** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Relevé d'activité standard des courtiers américains |
    | <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Revolut** | 🧪 Bêta | PDF/CSV | ✅ | ✅ | ✅ | ✅ | Prise en charge des transactions d'actions et de crypto |
    | <img src="https://www.coinbase.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Coinbase** | 🧪 Bêta | CSV | ✅ | ❌ | ✅ | ✅ | Rapports de transactions crypto uniquement |
    | <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Freetrade** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Relevés de courtage britanniques simples |
    | <img src="https://www.finpension.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Finpension** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Relevés du pilier 3a suisse |
    | <img src="https://www.trading212.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Trading212** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | CSV d'activité de trading européen |
    | <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" style="color: var(--md-accent-fg-color); vertical-align: middle; margin-right: 4px;"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> **CSV Générique** | ✅ Stable | CSV | ✅ | ✅ | ✅ | ✅ | Analyseur fallback avec mappage manuel des colonnes |

---

## 🗂️ Mappage des actifs {: #asset-mapping }

Lors de l'étape de prévisualisation, LibreFolio tente de **faire correspondre automatiquement** chaque nom d'actif de votre rapport à un actif déjà présent dans votre bibliothèque.

- ✅ **Correspondant** — sera importé par rapport à l'actif existant.
- ⚠️ **Non correspondant** — sélectionnez ou créez l'actif cible avant d'importer.
- ❌ **Erreur** — la ligne n'a pas pu être analysée.

---

## ♻️ Détection des doublons {: #duplicate-detection }

BRIM vérifie les **transactions en double** en se basant sur la date, le type, l'actif, la quantité et le montant. Les lignes en double sont signalées dans l'aperçu — vous pouvez choisir de les ignorer ou de les forcer à être importées.

---

## 🔗 Liens connexes

- 📋 **[Tableau des transactions](../index.md)** — Visualiser et gérer les transactions importées
- 🗂️ **[Fichiers](../../files/index.md)** — Gérer les fichiers de rapports de courtier téléchargés
- 🏦 **[Courtiers](../../brokers/index.md)** — Configurez d'abord vos comptes de courtier
