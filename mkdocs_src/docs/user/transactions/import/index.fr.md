# 📥 Importer depuis un Courtier (BRIM)

**BRIM** (Broker Report Import Module) vous permet d'importer des transactions directement depuis les fichiers d'exportation de votre courtier — pas besoin de saisie manuelle. Téléchargez un rapport CSV et LibreFolio analyse, associe et importe toutes les transactions en un seul flux.

---

## 🚀 Comment Importer

1. Exportez un rapport de transaction depuis votre courtier (généralement un fichier CSV — consultez le centre d'aide de votre courtier).
2. Dans LibreFolio, accédez à la page **[Transactions](../index.md)**.
3. Cliquez sur le bouton **Import** (:material-file-upload:) dans l'en-tête de la page, ou glissez-déposez le fichier directement dans la liste des transactions.
4. L'**Assistant d'Importation** s'ouvre.
5. Examinez l'aperçu — vérifiez que les dates, les montons et les noms d'actifs sont corrects.
6. Cliquez sur **Import** pour valider toutes les transactions.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Fenêtre d'Importation Rapide" alt="Quick Import Modal">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Étape 1: Charger le fichier de rapport" alt="Assistant Étape 1">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Étape 2: Configuration de l'analyseur" alt="Assistant Étape 2">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Étape 3: Analyse" alt="Assistant Étape 3">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Étape 4: Résolution d'actifs" alt="Assistant Étape 4">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Étape 4: Détection des doublons" alt="Détection des Doublons">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Étape 5: Révision finale" alt="Révision Finale">
</div>

!!! tip "Création au vol de courtiers et d'actifs"

    Si le rapport importé contient un compte de courtier ou des actifs qui ne sont pas encore créés dans LibreFolio, vous n'avez pas besoin de quitter le flux d'importation! L'assistant vous guidera pour créer les **[Courtiers](../../brokers/index.md)** et les **[Actifs](../../assets/index.md)** manquants au vol, en pré-remplissant les détails à partir du relevé.

!!! tip "Vous pouvez également utiliser la section Fichiers"

    La section **[Fichiers](../../files/index.md)** (onglet BRIM) vous permet de gérer de manière centralisée les rapports importés, de les ré-importer ou de les supprimer.

---

## 🧙 Les Étapes de l'Assistant d'Importation

L'assistant guidé contient 5 étapes opérationnelles conçues pour analyser, valider, résoudre et importer votre historique de transactions en toute sécurité.

### 🧙 Étape 1: Charger le fichier de rapport

Cette étape accepte les rapports CSV, XLSX ou PDF exportés de votre courtier. Vous pouvez sélectionner des fichiers manuellement ou les glisser-déposer directement dans l'assistant.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Assistant Étape 1 : Charger" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⚙️ Étape 2: Configuration de l'analyseur

Le système détecte automatiquement le format du courtier (par exemple, Degiro, Directa, Interactive Brokers). Si vous chargez une feuille de calcul générique, vous pouvez utiliser l'analyseur **Generic CSV** pour mapper manuellement vos colonnes (date, type, quantité, actif, liquidités nettes) aux champs LibreFolio.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Assistant Étape 2 : Configuration" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧠 Étape 3: Analyse et Lecture

Le système traite les fichiers, validant les dates, les nombres et les devises. Vous verrez une barre de progression indiquant la vitesse et l'état de la lecture. Une fois l'analyse terminée, un résumé de tout avertissement ou erreur d'analyse s'affichera avant de continuer.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Assistant Étape 3 : Analyse" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

À la fin de l'analyse, le tableau affiche un résumé du traitement de chaque fichier avec les colonnes statistiques suivantes identifiées par des émojis :

| Émoji / Colonne | Nom de la Métrique | Signification et Règles de Remplissage |
| :--- | :--- | :--- |
| `📊` | **Transactions** | Le nombre total de transactions financières lues et identifiées dans le fichier. |
| `🏦` | **Actifs Identifiés** | Le nombre d'instruments financiers (actions, ETF, etc.) trouvés dans les transactions analysées. |
| `✗` | **Actifs non Résolus** | Le nombre d'instruments présents dans le fichier qui n'existent pas dans la base de données de LibreFolio (indiqué en rouge si > 0, nécessitant une association à l'Étape 4). |
| `🔴` | **Problèmes de Validation** | Erreurs formales détectées dans les données (ex. formats invalides, dates incorrectes, données obligatoires manquantes). |
| `🔧` | **Actions Requises (TODO)** | Champs ou attributs nécessitant une révision (rouge si bloquants, orange pour les alertes/informations). Il ne s'agit pas nécessairement d'erreurs : ils signalent simplement des données manquantes qui ne peuvent pas être extraites automatiquement du relevé seul, et que vous pourrez saisir manuellement dans le formulaire de transactions en masse à la fin de l'assistant. |
| `⚠️` | **Avertissements** | Notifications générales ou messages d'avertissement générés par l'analyseur pendant le traitement. |

### 🔍 Étape 4: Mappage d'Actifs & Détection des Doublons

C'est la phase de rapprochement. L'assistant effectue deux vérifications essentielles :

#### 🗂️ Résolution d'Actifs

Si le relevé contient des codes ISIN ou des symboles absents de votre bibliothèque, l'assistant les signale. Vous pouvez :
- Les associer à un actif existant dans votre base de données.
- Les créer **au vol** directement dans l'assistant.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Assistant Étape 4 : Résolution d'Actifs" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### ⚠️ Détection des Doublons

Le système compare les entrées lues avec votre base de données pour trouver des doublons potentiels basés sur le type, la date, le montant, la quantité et la description.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Assistant Étape 4 : Détection des Doublons" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Les doublons sont regroupés dans l'interface utilisateur sous deux badges de statut basés sur 4 niveaux de confiance :

| Badge UI | Niveau de Confiance | Critères / Règles de Correspondance |
| :--- | :--- | :--- |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY_WITH_ASSET` | Les champs de base et la description correspondent, et l'actif a été résolu automatiquement (doublon hautement probable). |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY` | Les champs de base et la description correspondent, mais l'actif n'est pas résolu. |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE_WITH_ASSET` | Les champs de base correspondent et l'actif a été résolu automatiquement (mais la description diffère ou est vide). |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE` | Les champs de base (type, date, quantité, montant) correspondent, mais l'actif n'est pas résolu. |
| <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ UNIQUE</span> | — | La transaction ne présente aucune correspondance dans la base de données et est considérée comme nouvelle (aucun doublon détecté). |
| <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ NON RÉSOLU</span> | — | Le courtier ou l'instrument financier n'a pas été associé à une entité existante dans la base de données (nécessite une résolution à l'Étape 4 avant l'importation). |

Par défaut, l'assistant décoche automatiquement les transactions considérées comme des doublons "Probables" afin de prévenir la double saisie, mais vous pouvez modifier ce choix.

### 📦 Étape 5: Révision finale

La révision finale présente la liste des transactions dans une grille similaire à un tableur.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Assistant Étape 5 : Révision Finale" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Le tableau affiche :

- **Date**: La date d'exécution.
- **Type**: ACHAT, VENTE, DIVIDENDE, DÉPÔT, etc.
- **Asset**: L'actif correspondant de votre bibliothèque.
- **Quantity**: Le nombre d'unités/actions.
- **Price**: Le prix unitaire.
- **Net Amount**: L'impact total de trésorerie.
- **Fees/Taxes**: Commissions et taxes incluses.

Cliquez sur **Import** pour finaliser l'importation et inscrire les transactions dans votre portefeuille.

---

## 🏦 Courtiers Supportés

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="IBKR favicon">
            <span class="card-title" style="margin: 0;">Interactive Brokers</span>
        </div>
        <span class="card-desc">Importez des rapports à l'aide de Flex Queries.</span>
    </a>
    <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Degiro favicon">
            <span class="card-title" style="margin: 0;">Degiro</span>
        </div>
        <span class="card-desc">Importez l'historique de vos transactions au format CSV.</span>
    </a>
    <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="eToro favicon">
            <span class="card-title" style="margin: 0;">eToro</span>
        </div>
        <span class="card-desc">Importez vos relevés de compte au format XLSX/CSV.</span>
    </a>
    <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Directa SIM favicon">
            <span class="card-title" style="margin: 0;">Directa SIM</span>
        </div>
        <span class="card-desc">Importez l'historique de vos transactions en CSV.</span>
    </a>
    <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Charles Schwab favicon">
            <span class="card-title" style="margin: 0;">Charles Schwab</span>
        </div>
        <span class="card-desc">Importez l'historique CSV de vos transactions.</span>
    </a>
    <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Revolut favicon">
            <span class="card-title" style="margin: 0;">Revolut</span>
        </div>
        <span class="card-desc">Importez vos rapports PDF/CSV de Revolut.</span>
    </a>
    <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Coinbase favicon">
            <span class="card-title" style="margin: 0;">Coinbase</span>
        </div>
        <span class="card-desc">Importez vos fichiers de transactions CSV.</span>
    </a>
    <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Freetrade favicon">
            <span class="card-title" style="margin: 0;">Freetrade</span>
        </div>
        <span class="card-desc">Importez vos relevés de compte CSV de Freetrade.</span>
    </a>
    <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Finpension favicon">
            <span class="card-title" style="margin: 0;">Finpension</span>
        </div>
        <span class="card-desc">Importez l'historique des transactions en format CSV.</span>
    </a>
    <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.trading212.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Trading212 favicon">
            <span class="card-title" style="margin: 0;">Trading212</span>
        </div>
        <span class="card-desc">Importez votre historique CSV de Trading212.</span>
    </a>
    <a href="generic-csv/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" style="color: var(--md-accent-fg-color);"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg>
            <span class="card-title" style="margin: 0;">CSV Générique</span>
        </div>
        <span class="card-desc">Notre analyseur générique avec mappage manuel des colonnes.</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
      <span class="card-title" style="margin: 0;">Demander un plugin</span>
      </div>
      <span class="card-desc">Votre courtier manque? Demandez un nouveau plugin ou contribuez au code!</span>
    </a>
</div>

??? info "📊 Capacités de l'analyseur d'importation"

    | Courtier | Statut | Format | Achat/Vente | Dividendes | Dépôts/Trésorerie | Frais/Taxes | Notes |
    | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
    | <img src="https://www.interactivebrokers.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Interactive Brokers** | 🧪 Beta | CSV (Flex) | ✅ | ✅ | ✅ | ✅ | Idéal pour les portefeuilles multidevises |
    | <img src="https://www.degiro.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Degiro** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Support complet des relevés standard Degiro |
    | <img src="https://www.etoro.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **eToro** | 🧪 Beta | XLSX/CSV | ✅ | ✅ | ✅ | ✅ | Support des dividendes et gains réalisés |
    | <img src="https://www.directa.it/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Directa SIM** | ✅ Stable | CSV | ✅ | ✅ | ✅ | ✅ | Courtier italien avec rapports fiscaux |
    | <img src="https://www.schwab.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Charles Schwab** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Activité standard courtier US |
    | <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Revolut** | 🧪 Beta | PDF/CSV | ✅ | ✅ | ✅ | ✅ | Support actions et cryptomonnaies |
    | <img src="https://www.coinbase.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Coinbase** | 🧪 Beta | CSV | ✅ | ❌ | ✅ | ✅ | Uniquement pour rapports cryptomonnaies |
    | <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Freetrade** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Relevés de courtage britanniques |
    | <img src="https://www.finpension.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Finpension** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Relevés de prévoyance suisses 3a |
    | <img src="https://www.trading212.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Trading212** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Activité standard courtier européen |
    | <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" style="color: var(--md-accent-fg-color); vertical-align: middle; margin-right: 4px;"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> **Generic CSV** | ✅ Stable | CSV | ✅ | ✅ | ✅ | ✅ | Mappage manuel comme solution de rechange |

---

## 🗂️ Mappage d'Actifs {: #asset-mapping }

Pendant l'étape de prévisualisation, LibreFolio tente d'**associer automatiquement** chaque actif de votre rapport à un actif déjà présent dans votre bibliothèque.

- ✅ **Matched (Associé)** — sera importé sur l'actif existant.
- ⚠️ **Unmatched (Non associé)** — sélectionnez ou créez l'actif cible avant l'importation.
- ❌ **Erreur** — la ligne n'a pas pu être lue.

---

## ♻️ Détection des Doublons {: #duplicate-detection }

BRIM vérifie s'il y a des **doublons** en se basant sur la date, le type, l'actif, la quantité et le montant. Les lignes suspectes sont signalées dans la prévisualisation — vous pouvez choisir de les ignorer ou de forcer l'importation.

---

## 🔗 Relais

- 📋 **[Tableau des Transactions](../index.md)** — Consulter et gérer les transactions importées
- 🗂️ **[Fichiers](../../files/index.md)** — Gérer les relevés de courtiers téléchargés
- 🏦 **[Courtiers](../../brokers/index.md)** — Configurez d'abord vos comptes de courtier
