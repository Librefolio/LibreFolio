# 🧙 Comment Importer des Transactions

Apprenez à utiliser le module d'import de relevés de courtier (BRIM) pour importer vos transactions étape par étape.

---

## 🚀 Guide Pas à Pas

1. Exportez un relevé de transactions depuis votre courtier (généralement un fichier CSV — vérifiez le centre d'aide de votre courtier).
2. Dans LibreFolio, accédez à la page **[Transactions](../index.md)**.
3. Cliquez sur le bouton **Importer** (:material-file-upload:) dans l'en-tête de la page, ou glissez-déposez directement votre fichier de relevé dans la liste des transactions.
4. **L'assistant d'importation** s'ouvre.
5. Examinez l'aperçu — vérifiez que les dates, les montants et les noms des actifs semblent corrects.
6. Cliquez sur **Importer** pour valider toutes les transactions.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Fenêtre d'import rapide" alt="Fenêtre d'import rapide">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Étape 1 : Téléverser le fichier de relevé" alt="🧙 Étape 1 : Téléverser le fichier de relevé">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Étape 2 : Configuration de l'analyseur" alt="Assistant - Étape 2">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Étape 3 : Analyse" alt="Assistant - Étape 3">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Étape 4 : Résolution des actifs" alt="Assistant - Étape 4">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Étape 4 : Détection des doublons" alt="⚠️ Étape 4 : Détection des doublons">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Étape 5 : Revue groupée préparatoire" alt="📦 Étape 5 : Revue groupée préparatoire">
</div>

!!! tip "Création à la volée de courtiers et d'actifs"

    Si le relevé importé contient un compte courtier ou des actifs qui ne sont pas encore créés dans LibreFolio, vous n'avez pas besoin de quitter le flux d'import ! L'assistant vous guidera pour créer les **[Courtiers](../../brokers/index.md)** et **[Actifs](../../assets/index.md)** manquants à la volée, en pré-remplissant les détails à partir du relevé.

!!! tip "Vous pouvez également utiliser la section Fichiers"

    La section **[Fichiers](../../files/index.md)** (onglet BRIM) vous permet de gérer centralement les relevés de courtier téléversés, de les réimporter ou de les supprimer.

---

## 🧙 Les Étapes de l'Assistant d'Importation

L'assistant guidé comprend 5 étapes opérationnelles conçues pour analyser, valider, résoudre et importer votre historique de transactions en toute sécurité.

### 🧙 Étape 1 : Téléverser le fichier de relevé

Cette étape accepte les relevés CSV, XLSX ou PDF exportés depuis votre courtier. Vous pouvez sélectionner les fichiers manuellement ou les glisser-déposer directement dans l'assistant.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="🧙 Étape 1 : Téléverser le fichier de relevé" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⚙️ Étape 2 : Configuration de l'analyseur

Le système détecte automatiquement le format du courtier (ex. Degiro, Directa, Interactive Brokers). Si vous téléversez un tableur générique, vous pouvez utiliser l'analyseur **CSV Générique** pour mapper manuellement vos colonnes (date, type, quantité, actif, montant net) aux champs LibreFolio.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Assistant - Étape 2 : Configuration de l'analyseur" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧠 Étape 3 : Analyse et Parsing

Le système analyse les fichiers, en validant les dates, les nombres et les devises. Vous verrez une barre de progression indiquant la vitesse et le statut de l'analyse. Une fois l'analyse terminée, tout avertissement ou erreur de parsing sera résumé avant de continuer.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Assistant - Étape 3 : Analyse" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

À la fin du parsing, le tableau affiche un résumé du traitement pour chaque fichier avec les colonnes statistiques suivantes, marquées par des émojis :

| Emoji / Colonne | Nom de la métrique | Signification et règles de renseignement |
| :--- | :--- | :--- |
| `📊` | **Transactions** | Le nombre total de transactions financières lues et identifiées dans le fichier. |
| `🏦` | **Actifs Identifiés** | Le nombre d'instruments financiers (actions, ETF, etc.) trouvés dans les transactions analysées. |
| `✗` | **Actifs Non Résolus** | Le nombre d'instruments dans le fichier qui n'ont pas été trouvés dans la base de données de LibreFolio (marqué en rouge si > 0, nécessitant un mappage à l'étape 4). |
| `🔴` | **Problèmes de Validation** | Erreurs formelles détectées dans les données (ex. formats invalides, dates incorrectes, données requises manquantes). |
| `🔧` | **Action Requise (À FAIRE)** | Champs ou attributs nécessitant une attention (rouge si bloquant, orange pour les actions de niveau avertissement/information). Ce ne sont pas nécessairement des erreurs : ils indiquent simplement des données manquantes qui ne peuvent pas être extraites automatiquement du seul relevé, et que vous pouvez facilement remplir manuellement dans le formulaire de transactions groupées à la fin de l'assistant. |
| `⚠️` | **Avertissements** | Notifications générales ou messages d'avertissement générés par l'analyseur pendant le traitement. |

### 🔍 Étape 4 : Mappage des actifs et Détection des doublons

C'est la phase de réconciliation. L'assistant effectue deux vérifications principales :

#### 🗂️ Résolution des actifs

Si le relevé contient des symboles boursiers ou des ISIN qui ne sont pas dans votre bibliothèque, l'assistant les signale. Vous pouvez :

- Les mapper à un actif existant dans votre base de données.
- Les créer **à la volée** directement dans l'assistant.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Assistant - Étape 4 : Résolution des actifs" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### ⚠️ Détection des doublons

Le système compare les entrées analysées avec votre base de données pour trouver des doublons potentiels en fonction du type, de la date, du montant, de la quantité et de la description.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="⚠️ Étape 4 : Détection des doublons" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Les doublons sont signalés dans l'interface à l'aide de deux badges de statut basés sur 4 niveaux de confiance :

| Badge UI | Niveau de Confiance | Critères / Règles de Correspondance |
| :--- | :--- | :--- |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ PROBABLE</span> | `LIKELY_WITH_ASSET` | Les champs de base et la description correspondent, et l'actif est auto-résolu (doublon hautement probable). |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ PROBABLE</span> | `LIKELY` | Les champs de base et la description correspondent, mais l'actif n'est pas résolu. |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE_WITH_ASSET` | Les champs de base correspondent, et l'actif est auto-résolu (mais la description diffère ou est vide). |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE` | Les champs de base (type, date, quantité, montant) correspondent, mais l'actif n'est pas résolu. |
| <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ UNIQUE</span> | — | La transaction n'a aucun enregistrement correspondant dans la base de données et est classée comme nouvelle (aucun doublon détecté). |
| <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ NON RÉSOLU</span> | — | Le courtier ou l'instrument financier n'a pas été associé à une entité existante dans la base de données (nécessite une résolution à l'étape 4 avant l'importation). |

Par défaut, l'assistant décoche automatiquement les doublons "Probables" pour éviter une double saisie, mais vous pouvez passer outre ce choix.

### 📦 Étape 5 : Revue groupée préparatoire

La revue finale affiche la liste analysée dans une grille de type tableur.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="📦 Étape 5 : Revue groupée préparatoire" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Le tableau affiche :

- **Date** : La date d'exécution.
- **Type** : ACHAT, VENTE, DIVIDENDE, DÉPÔT, etc.
- **Actif** : L'actif correspondant de votre bibliothèque.
- **Quantité** : Le nombre d'unités/actions.
- **Prix** : Le prix unitaire.
- **Montant Net** : L'impact financier total.
- **Frais/Taxes** : Commissions et taxes incluses.

Cliquez sur **Importer** pour finaliser l'importation et écrire les transactions dans votre journal.
