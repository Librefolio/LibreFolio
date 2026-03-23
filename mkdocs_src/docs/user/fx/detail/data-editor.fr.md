# ✏️ Éditeur de données et importation CSV

L'éditeur de données vous permet de **consulter, ajouter, modifier et supprimer** des points de données de taux de change individuels. Pour le chargement en masse, il inclut un outil d'**importation CSV** intégré.

---

## 📝 Éditeur de données

Cliquez sur le bouton **Éditer** (✏️) dans la barre d'outils du graphique pour ouvrir le panneau de l'éditeur de données :

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-editor" alt="FX Data Editor" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 👀 Consultation des données

L'éditeur affiche un tableau déroulant de tous les points de données pour cette paire de devises, triés par date (la plus récente en premier) :

- 📅 **Date** — La date d'observation
- 💱 **Taux** — La valeur du taux de change
- 🏛️ **Source** — L'origine des données (nom du fournisseur, importation CSV ou manuelle)

### ➕ Ajout d'un point de données

1. Cliquez sur **"Ajouter"** en haut de l'éditeur
2. Sélectionnez la **date** dans le sélecteur de date
3. Entrez la valeur du **taux**
4. Cliquez sur **Enregistrer** — le point est immédiatement ajouté et le graphique est mis à jour

### ✏️ Modification d'un point de données

1. Cliquez sur l'**icône crayon** à côté de n'importe quelle ligne
2. Modifiez la valeur du taux
3. Cliquez sur **Enregistrer** pour confirmer

### 🗑️ Suppression d'un point de données

1. Cliquez sur l'**icône corbeille** à côté de n'importe quelle ligne
2. Confirmez la suppression

!!! avertissement "Les données synchronisées écrasent les modifications manuelles"

    Si vous modifiez manuellement un point de données pour une date ensuite couverte par une synchronisation, la valeur du fournisseur **écrasera** votre modification — le fournisseur est toujours considéré comme la source faisant autorité. Pour les paires où vous souhaitez un contrôle manuel complet, utilisez le fournisseur MANUAL (pas de source automatique) — voir [Configuration du fournisseur](provider.md).

---

## 📥 Importation CSV

Pour le chargement en masse de données historiques de taux de change, utilisez l'outil d'importation CSV.

### 🔓 Accès

1. Ouvrez l'éditeur de données (icône crayon ✏️)
2. Cliquez sur **"Importer CSV"** pour ouvrir la boîte de dialogue d'importation

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-csv-import" alt="CSV Import Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

### 📄 Format du fichier CSV

Le fichier CSV doit avoir **exactement 2 colonnes** avec une **ligne d'en-tête** qui spécifie le sens :

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
2024-01-04;1.0911
```

### 📏 Règles

| Règle | Détails |
|-------|---------|
| **Séparateur** | Point-virgule (`;`) |
| **Format de date** | `AAAA-MM-JJ` |
| **Valeurs de taux** | Nombres décimaux positifs |
| **En-tête** | Requis — doit contenir le sens (par ex., `EUR>USD`) |
| **Flèche de sens** | Utilisez `>` ou `<` (les deux sont supportés) |

### ↔️ Sens dans l'en-tête

L'en-tête indique à LibreFolio dans quel **sens** les taux sont exprimés :

- ➡️ `date;EUR>USD` signifie : **1 EUR = X USD** (les taux sont EUR→USD)
- ⬅️ `date;USD>EUR` signifie : **1 USD = X EUR** (les taux sont USD→EUR)

Si vous êtes sur la page EUR/USD et que votre CSV a des taux `USD>EUR`, LibreFolio inversera automatiquement les valeurs.

---

### 🔀 Sens et inversion

La boîte de dialogue d'importation affiche une **barre de sens** indiquant comment vos données seront interprétées :

- ➡️ **Devise gauche** → **Devise droite** : le taux vous indique combien de la devise droite vous obtenez pour 1 unité de la devise gauche
- 🔄 Utilisez le **bouton d'inversion** (⇄) pour retourner le sens si vos données sont dans le format opposé

L'en-tête de votre CSV détermine automatiquement le sens. Si l'en-tête dit `EUR>USD`, la boîte de dialogue définit le sens sur EUR→USD.

---

### 📋 Exemples

#### ✅ Exemple valide minimal
```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
```

#### ✅ Sens inversé
```csv
date;USD>EUR
2024-01-02;0.9053
2024-01-03;0.9106
```

Cela équivaut au premier exemple — LibreFolio inverse `0.9053` en `1/0.9053 ≈ 1.1045`.

#### ❌ Fichier invalide
```csv
date;GBP>JPY
2024-01-02;188.45
```

Cela échouera si vous êtes sur la page EUR/USD — les devises de l'en-tête doivent correspondre à la paire de la page.

---

### ⚠️ Erreurs courantes

| Erreur | Cause | Solution |
|-------|-------|----------|
| **"Les devises de l'en-tête ne correspondent pas"** | L'en-tête contient des devises qui ne sont pas sur cette page | Vérifiez la paire et corrigez l'en-tête |
| **"En-tête manquant ou invalide"** | Pas de ligne d'en-tête, ou mauvais format | Ajoutez un en-tête comme `date;EUR>USD` |
| **"Dates en double"** | La même date apparaît plusieurs fois | Supprimez les doublons |
| **"Taux invalide"** | Valeur non numérique ou négative | Assurez-vous que tous les taux sont des nombres positifs |
| **"Format de date invalide"** | Date non au format `AAAA-MM-JJ` | Corrigez le format de date |

---

### 🔀 Comportement de fusion

Lors de l'importation CSV ou de l'ajout manuel de points dans l'éditeur :

- Les modifications sont d'abord appliquées au **cache local du client** (visibles immédiatement dans le graphique)
- Les modifications **ne sont pas enregistrées** dans la base de données tant que vous n'appuyez pas sur **Enregistrer**
- 🔄 Les **points de données existants** dans la base de données seront **remplacés** par les valeurs importées lors de l'enregistrement
- 🆕 Les **nouvelles dates** sont ajoutées
- ✅ Les **dates non présentes dans l'importation** restent inchangées

!!! tip "Idéal pour les paires MANUAL"

    L'éditeur de données est particulièrement utile pour les paires configurées avec le fournisseur MANUAL (pas de source de données automatique). Pour les paires avec fournisseur, les modifications manuelles seront écrasées lors de la prochaine synchronisation.
