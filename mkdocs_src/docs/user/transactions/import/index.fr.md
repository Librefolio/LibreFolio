# 📥 Import depuis un Courtier (BRIM)

**BRIM** (Broker Report Import Module) vous permet d'importer des transactions directement depuis les fichiers d'exportation de votre courtier — aucune saisie manuelle n'est nécessaire. Téléchargez un rapport CSV et LibreFolio analyse, mappe et importe toutes les transactions en un seul flux.

---

## 🚀 Comment Importer

1. Exportez un rapport de transactions depuis votre courtier (généralement un fichier CSV — consultez le centre d'aide de votre courtier).
2. Dans LibreFolio, naviguez vers votre page **Courtier**.
3. Cliquez sur le bouton **Importer** (:material-file-upload:) dans l'en-tête du courtier.
4. La **fenêtre d'importation** s'ouvre.
5. **Glissez-déposez** ou cliquez pour sélectionner votre fichier.
6. LibreFolio **détecte automatiquement** le format du courtier et affiche un **aperçu** des transactions analysées.
7. Révisez l'aperçu — vérifiez que les dates, les montants et les noms des actifs semblent corrects.
8. Cliquez sur **Importer** pour valider toutes les transactions.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Modale d'import rapide" alt="Modale d'import rapide">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Étape 1 : Télécharger le fichier de rapport" alt="Étape de l'assistant 1">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Étape 2 : Configuration de l'analyseur" alt="Étape de l'assistant 2">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Étape 3 : Résolution des actifs" alt="Étape de l'assistant 3">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Détection des doublons" alt="Détection des doublons">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Révision de la mise en attente groupée" alt="Mise en attente groupée">
</div>

!!! tip "Vous pouvez également utiliser la section Fichiers"

    La section **[Fichiers](../../files/index.md)** (onglet BRIM) vous permet de gérer les rapports de courtier téléchargés de manière centralisée, de les ré-importer ou de les supprimer.

---

## 🏦 Courtiers Supportés

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
 <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="IBKR favicon">
 <span class="card-title" style="margin: 0;">Interactive Brokers</span>
 </div>
 <span class="card-desc">Importez des rapports de transactions via Flex Queries.</span>
 </a>
 <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Degiro favicon">
 <span class="card-title" style="margin: 0;">Degiro</span>
 </div>
 <span class="card-desc">Importez les exports CSV de l'historique des transactions de Degiro.</span>
 </a>
 <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="eToro favicon">
 <span class="card-title" style="margin: 0;">eToro</span>
 </div>
 <span class="card-desc">Importez les fichiers XLSX/CSV de relevés de compte d'eToro.</span>
 </a>
 <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Directa SIM favicon">
 <span class="card-title" style="margin: 0;">Directa SIM</span>
 </div>
 <span class="card-desc">Importez les fichiers CSV de l'historique des transactions de Directa SIM.</span>
 </a>
 <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Charles Schwab favicon">
 <span class="card-title" style="margin: 0;">Charles Schwab</span>
 </div>
 <span class="card-desc">Importez l'historique des transactions CSV de Charles Schwab.</span>
 </a>
 <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Revolut favicon">
 <span class="card-title" style="margin: 0;">Revolut</span>
 </div>
 <span class="card-desc">Importez les rapports PDF/CSV de relevés de compte de Revolut.</span>
 </a>
 <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Coinbase favicon">
 <span class="card-title" style="margin: 0;">Coinbase</span>
 </div>
 <span class="card-desc">Importez les fichiers CSV d'historique des transactions de Coinbase.</span>
 </a>
 <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Freetrade favicon">
 <span class="card-title" style="margin: 0;">Freetrade</span>
 </div>
 <span class="card-desc">Importez les relevés de transactions CSV de Freetrade.</span>
 </a>
 <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Finpension favicon">
 <span class="card-title" style="margin: 0;">Finpension</span>
 </div>
 <span class="card-desc">Importez les rapports CSV de l'historique des transactions de Finpension.</span>
 </a>
 <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.trading212.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Trading212 favicon">
 <span class="card-title" style="margin: 0;">Trading212</span>
 </div>
 <span class="card-desc">Importez l'historique des transactions CSV de Trading212.</span>
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
  <span class="card-title" style="margin: 0;">Demander un Nouveau Plugin</span>
  </div>
  <span class="card-desc">Votre courtier manque ? Demandez un nouveau plugin ou contribuez !</span>
 </a>
 </div>

### 📊 Capacités de l'importateur

| Courtier | Format | Achat/Vente | Dividendes | Dépôts/Cash | Frais/Taxes | Notes |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **Interactive Brokers** | CSV (Flex) | ✅ | ✅ | ✅ | ✅ | Idéal pour les comptes multi-devises |
| **Degiro** | CSV | ✅ | ✅ | ✅ | ✅ | Support pour relevés de compte standards |
| **eToro** | XLSX/CSV | ✅ | ✅ | ✅ | ✅ | Support des gains réalisés et dividendes |
| **Directa SIM** | CSV | ✅ | ✅ | ✅ | ✅ | Support des relevés fiscaux du courtier italien |
| **Charles Schwab** | CSV | ✅ | ✅ | ✅ | ✅ | Relevé d'activité standard de courtier US |
| **Revolut** | PDF/CSV | ✅ | ✅ | ✅ | ✅ | Support des transactions actions et crypto |
| **Coinbase** | CSV | ✅ | ❌ | ✅ | ✅ | Rapports de transactions crypto uniquement |
| **Freetrade** | CSV | ✅ | ✅ | ✅ | ✅ | Relevés de courtage UK simples |
| **Finpension** | CSV | ✅ | ✅ | ✅ | ✅ | Relevés de pension suisse 3a |
| **Trading212** | CSV | ✅ | ✅ | ✅ | ✅ | CSV d'activité de trading européenne |
| **CSV Générique** | CSV | ✅ | ✅ | ✅ | ✅ | Solution fallback avec mappage manuel |

!!! note "Tous les fournisseurs sont en Bêta"

    Les plugins d'importation sont maintenus par la communauté et s'améliorent avec le temps. Si un format de rapport spécifique présente des anomalies, le fournisseur **[CSV Générique](generic-csv/)** permet un mappage manuel des colonnes en guise de fallback.

---

## 🗂️ Mappage des Actifs

Pendant l'étape d'aperçu, LibreFolio tente de **faire correspondre automatiquement** chaque nom d'actif de votre rapport à un actif déjà présent dans votre bibliothèque.

- ✅ **Correspondance trouvée** — sera importé vers l'actif existant.
- ⚠️ **Aucune correspondance** — sélectionnez ou créez l'actif cible avant l'importation.
- ❌ **Erreur** — la ligne n'a pas pu être analysée.

---

## ♻️ Détection des Doublons

BRIM vérifie les **transactions en double** en se basant sur la date, le type, l'actif, la quantité et le montant. Les lignes en double sont signalées dans l'aperçu — vous pouvez choisir de les ignorer ou de forcer leur importation.

---

## 🔗 Liens Connexes

- 📋 **[Tableau des Transactions](../index.md)** — Consulter et gérer les transactions importées
- 🗂️ **[Fichiers](../../files/index.md)** — Gérer les fichiers de rapports de courtier téléchargés
- 🏦 **[Courtiers](../../brokers/index.md)** — Configurer d'abord vos comptes de courtage
