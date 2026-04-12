# ✏️ Éditeur de données & Import CSV

L'Éditeur de données vous permet de **consulter, ajouter, modifier et supprimer** des points de données de taux de change individuels. Pour le chargement massif, il inclut un outil d'**Import CSV** intégré.

---

## 📝 Éditeur de données

Cliquez sur le bouton **Modifier** (✏️) dans la barre d'outils du graphique pour ouvrir le panneau de l'éditeur de données :

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-editor" alt="Éditeur de données FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 👀 Consulter les données

L'éditeur affiche un tableau défilable de tous les points de données pour cette paire de devises, triés par date (la plus récente en premier) :

- 📅 **Date** — La date d'observation
- 💱 **Taux** — La valeur du taux de change
- 🏛️ **Source** — L'origine des données (nom du fournisseur, import CSV ou manuel)

### ➕ Ajouter un point de données

1. Cliquez sur **"Ajouter"** en haut de l'éditeur
2. Sélectionnez la **date** via le sélecteur de date
3. Saisissez la valeur du **taux**
4. Cliquez sur **Enregistrer** — le point est immédiatement ajouté et le graphique est mis à jour

### ✏️ Modifier un point de données

1. Cliquez sur l'**icône crayon** à côté de n'importe quelle ligne
2. Modifiez la valeur du taux
3. Cliquez sur **Enregistrer** pour confirmer

### 🗑️ Supprimer un point de données

1. Cliquez sur l'**icône corbeille** à côté de n'importe quelle ligne
2. Confirmez la suppression

!!! warning "Les données synchronisées écrasent les modifications manuelles"

    Si vous modifiez ou ajoutez manuellement un point de données pour une date qui est ultérieurement couverte par une synchronisation, la valeur du fournisseur **écrasera** votre modification manuelle — le fournisseur est toujours considéré comme la source faisant autorité. Pour les paires pour lesquelles vous souhaitez un contrôle manuel total, utilisez le fournisseur MANUAL (aucune source de données automatique) — voir [Configuration du fournisseur](provider.md).

---

## 📥 Import CSV

Pour le chargement massif de données de taux historiques, utilisez l'outil d'Import CSV.

### 🔓 Comment y accéder

1. Ouvrez l'Éditeur de données (icône crayon ✏️)
2. Cliquez sur **"Importer CSV"** pour ouvrir la fenêtre modale d'importation

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-csv-import" alt="Fenêtre modale d'import CSV" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

### 📄 Format du fichier CSV

Le fichier CSV doit comporter **exactement 2 colonnes** avec une **ligne d'en-tête** spécifiant la direction :

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
2024-01-04;1.0911
```

### 📏 Règles

| Règle | Détails |
|------|---------|
| **Séparateur** | Point-virgule (`;`) |
| **Format de date** | `YYYY-MM-DD` |
| **Valeurs de taux** | Nombres décimaux positifs |
| **En-tête** | Requis — doit contenir la direction (ex: `EUR>USD`) |
| **Flèche de direction** | Utilisez `>` ou `<` (les deux sont supportés) |

### ↔️ Direction dans l'en-tête

L'en-tête indique à LibreFolio dans quelle direction les taux sont exprimés :

- ➡️ `date;EUR>USD` signifie : **1 EUR = X USD** (les taux sont EUR→USD)
- ⬅️ `date;USD>EUR` signifie : **1 USD = X EUR** (les taux sont USD→EUR)

Si vous êtes sur la page EUR/USD et que votre CSV contient des taux `USD>EUR`, LibreFolio inversera automatiquement les valeurs.

---

### 🔀 Direction & Permutation

La fenêtre modale d'importation affiche une **barre de direction** indiquant comment vos données seront interprétées :

- ➡️ **Devise de gauche** → **Devise de droite** : le taux vous indique combien d'unités de la devise de droite vous obtenez pour 1 unité de la devise de gauche
- 🔄 Utilisez le **bouton de permutation (⇄)** pour changer la direction si vos données sont dans le format opposé

L'en-tête de votre CSV détermine la direction automatiquement. Si l'en-tête indique `EUR>USD`, la fenêtre modale définit la direction sur EUR→USD.

---

### 📋 Exemples

#### ✅ Fichier minimal valide

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
```

#### ✅ Direction inversée

```csv
date;USD>EUR
2024-01-02;0.9053
2024-01-03;0.9106
```

Ceci est équivalent au premier exemple — LibreFolio inverse `0.9053` en `1/0.9053 ≈ 1.1045`.

#### ❌ Fichier invalide

```csv
date;GBP>JPY
2024-01-02;188.45
```

Ceci échouera si vous êtes sur la page EUR/USD — les devises de l'en-tête doivent correspondre à la paire de la page.

---

### ⚠️ Erreurs courantes

| Erreur | Cause | Solution |
|-------|-------|-----|
| **"Header currencies don't match"** | L'en-tête contient des devises qui ne sont pas sur cette page | Vérifiez la paire et corrigez l'en-tête |
| **"Missing or invalid header"** | Pas de ligne d'en-tête, ou format incorrect | Ajoutez un en-tête comme `date;EUR>USD` |
| **"Duplicate dates"** | La même date apparaît plusieurs fois | Supprimez les doublons |
| **"Invalid rate"** | Valeur non numérique ou négative | Assurez-vous que tous les taux sont des nombres positifs |
| **"Invalid date format"** | Date non conforme au format `YYYY-MM-DD` | Corrigez le formatage de la date |

---

### 🔀 Comportement de fusion

Lors de l'importation via CSV ou de l'ajout de points manuellement dans l'éditeur :

- Les modifications sont d'abord appliquées au **cache client local** (visibles immédiatement dans le graphique)
- Les modifications ne sont **pas enregistrées** dans la base de données tant que vous ne cliquez pas sur **Enregistrer**
- 🔄 Les **points de données existants** dans la base de données seront **écrasés** par les valeurs importées lors de l'enregistrement
- 🆕 Les **nouvelles dates** sont ajoutées
- ✅ Les **dates absentes de l'importation** restent inchangées

Cela vous permet de mettre à jour sélectivement des plages de dates spécifiques sans affecter le reste de vos données.

!!! tip "Idéal pour les paires MANUAL"

    L'éditeur de données est particulièrement utile pour les paires configurées avec le fournisseur MANUAL (aucune source de données automatique). Pour les paires liées à un fournisseur, les modifications manuelles seront écrasées lors de la prochaine synchronisation.
