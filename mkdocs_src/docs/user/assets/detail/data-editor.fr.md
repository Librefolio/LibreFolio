# ✏️ Éditeur de Données

L'Éditeur de Données vous permet de visualiser, ajouter, modifier ou supprimer manuellement des points de données de prix et des événements d'actifs directement depuis la page de détail de l'actif.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-editor" alt="Éditeur de données d'actif" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Mode d'emploi

1. Cliquez sur le bouton **Modifier les données** (✏️📊) dans la barre d'outils
2. Le panneau de l'éditeur s'ouvre avec deux onglets : **Prix** et **Événements**
3. Dans chaque onglet, vous pouvez :
 - **Ajouter** une nouvelle ligne : cliquez sur ➕ Ajouter une ligne, puis remplissez les champs
 - **Modifier** une ligne existante : cliquez sur une cellule pour la modifier
 - **Supprimer** une ligne : sélectionnez-la et cliquez sur 🗑️ Supprimer
 - **Importer un CSV** : cliquez sur 📥 Importer CSV pour ajouter des données en masse
4. Les modifications sont suivies par un badge d'indicateur de modifications non enregistrées. Cliquez sur **Enregistrer** pour valider tous les changements, ou sur **Annuler** pour les rejeter.
5. Cliquez sur **Fermer** (✕) pour quitter — les autres panneaux (signaux, mesures) sont automatiquement restaurés.

---

## 💰 Onglet Prix

L'onglet Prix affiche tous les points de données de prix pour l'actif. Colonnes :

| Colonne | Requis | Description |
|--------|----------|-------------|
| **Date** | ✅ | Date au format AAAA-MM-JJ |
| **Devise** | ✅ | Code devise ISO 4217 (ex: USD, EUR) |
| **Clôture** | ✅ | Prix de clôture |
| **Ouverture** | | Prix d'ouverture |
| **Plus haut** | | Prix le plus haut de la journée |
| **Plus bas** | | Prix le plus bas de la journée |
| **Volume** | | Volume d'échange |

### Format d'importation CSV

```
date;currency;close
2024-01-15;USD;145.50
2024-01-16;USD;146.10
```

Format étendu avec colonnes optionnelles :
```
date;currency;close;open;high;low;volume
2024-01-15;USD;145.50;144.00;146.20;143.80;1500000
```

---

## 📅 Onglet Événements

L'onglet Événements affiche tous les [événements d'actifs](../../../financial-theory/instruments/asset-events/index.md) (dividendes, splits, etc.). Colonnes :

| Colonne | Requis | Description |
|--------|----------|-------------|
| **Date** | ✅ | Date au format AAAA-MM-JJ |
| **Devise** | | Code ISO 4217 |
| **Type** | ✅ | Type d'événement (DIVIDEND, INTEREST, SPLIT, PRICE_ADJUSTMENT, MATURITY_SETTLEMENT) |
| **Montant** | ✅ | Valeur numérique (ex: dividende par action, ratio de split) |
| **Notes** | | Description optionnelle |

!!! info "Événements Auto vs Manuels"

    Les événements générés par un fournisseur (ex: Investissement programmé) sont marqués comme **auto** et apparaissent comme des lignes en lecture seule. Ils peuvent être supprimés mais pas modifiés. Les événements manuels sont entièrement modifiables.

### Format d'importation CSV

```
date;currency;type;amount;notes
2024-03-15;USD;DIVIDEND;1.25;Q1 payout
2024-06-01;;SPLIT;2;2:1 split
```

---

## ⚠️ Interrupteur des lignes obsolètes

La barre d'outils comprend un **interrupteur de lignes obsolètes** (switch). Les lignes obsolètes sont des points de données comblés vers l'arrière — des entrées de comblement de lacunes copiées depuis le point de données réel le plus proche. L'interrupteur vous permet de les afficher/masquer pour vous concentrer sur les données réelles. Un compteur indique combien de lignes obsolètes existent.

---

## 🖱️ Navigation Graphique ↔ Éditeur

**Double-cliquez** sur un point du graphique de prix (ou appui long sur mobile) pour faire défiler l'éditeur directement jusqu'à cette ligne :

- Double-clic sur un **point de prix** → défilement vers l'onglet Prix
- Double-clic sur un **marqueur d'événement** → défilement vers l'onglet Événements

---

!!! note "Quand utiliser l'Éditeur de Données"

    L'Éditeur de Données est utile pour :

    - Corriger des données de prix erronées provenant d'un fournisseur
    - Ajouter des données historiques pour des actifs sans fournisseur
    - Combler des lacunes dans l'historique des prix (ex: dates manquantes)
    - Enregistrer des événements d'entreprise (dividendes, splits) non capturés par les fournisseurs

---

## 🔗 Liens connexes

- 📈 **[Graphique Interactif](chart.md)** — Visualisation graphique avec marqueurs d'événements
- 📅 **[Événements d'Actifs](events.md)** — Types d'événements et leurs sources
- 📚 **[Événements d'Actifs (Théorie Financière)](../../../financial-theory/instruments/asset-events/index.md)** — Analyse détaillée de l'impact pour chaque type d'événement
- 🔌 **[Fournisseurs](../providers/index.md)** — Récupération automatique des prix
