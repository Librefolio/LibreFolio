# 💸 Transactions

Les transactions sont le **cœur de LibreFolio** — chaque achat, vente, dividende, frais, transfert et mouvement de trésorerie que vous enregistrez se trouve ici. Chaque courtier possède sa propre liste de transactions, accessible depuis la page de détails du courtier.

## 📋 Tableau des transactions

Le tableau des transactions affiche tous les mouvements d'un courtier par ordre chronologique inverse. Chaque ligne indique :

| Colonne | Description |
|--------|-------------|
| **Date** | Date d'exécution de la transaction |
| **Type** | Icône + libellé : BUY, SELL, DIVIDEND, FEE, TRANSFER, etc. |
| **Actif** | Nom de l'actif lié (vide pour les opérations de trésorerie) |
| **Quantité** | Nombre d'unités achetées/vendues/transférées |
| **Prix** | Prix unitaire à l'exécution |
| **Montant** | Valeur totale (quantité × prix ± frais) |
| **Devise** | Devise de la transaction |
| **Notes** | Note utilisateur facultative |

### Tri et Filtrage

- Cliquez sur l'**en-tête d'une colonne** pour trier par ordre croissant/décroissant.
- Utilisez la **barre de recherche** pour filtrer par nom d'actif, type ou notes.
- Utilisez les boutons de **filtre de type** pour afficher uniquement des types de transactions spécifiques.

---

## ➕ Ajouter des transactions

Cliquez sur **+ Nouvelle transaction** pour ouvrir le [Formulaire de transaction](form.md). Vous pouvez :

- Créer une **transaction unique** (un formulaire par opération)
- Créer des **transactions en masse** via la fenêtre modale d'importation groupée — collez ou téléchargez un tableau de lignes

---

## ✏️ Modification et Suppression

- Cliquez sur n'importe quelle ligne pour **ouvrir le formulaire** pré-rempli avec les données de cette transaction.
- Cliquez sur l'**icône de corbeille** (:material-delete:) pour supprimer une transaction.
- Sélectionnez plusieurs lignes avec la colonne des **cases à cocher**, puis utilisez la barre d'outils pour effectuer une **suppression groupée**.

!!! warning "Les suppressions sont permanentes"

    Il n'y a pas d'annulation possible pour les transactions supprimées. Exportez une sauvegarde au préalable si vous avez un doute.

---

## ✂️ Division et Promotion

Deux opérations spéciales sont disponibles sur les **transactions composites** (TRANSFER et FX_CONVERSION) :

### Division { #split }

Une **division** divise une transaction composite en ses deux composantes. Utilisez cette fonction lorsqu'une seule ligne importée représente en réalité deux événements distincts (par exemple, un CSV de courtier qui enregistre un transfert inter-devises sur une seule ligne).

1. Sélectionnez la ligne de la transaction composite.
2. Cliquez sur **Division** dans la barre d'outils d'action.
3. LibreFolio la sépare en deux transactions indépendantes.

### Promotion

La **promotion** transforme une paire de transactions enregistrées individuellement (par exemple, un WITHDRAWAL du courtier A et un DEPOSIT dans le courtier B) en une transaction composite **TRANSFER** liée. C'est la méthode standard pour enregistrer un mouvement d'actif entre vos propres courtiers.

1. Sélectionnez **exactement deux transactions** de types compatibles.
2. Cliquez sur **Promotion** dans la barre d'outils.
3. LibreFolio valide la compatibilité (même actif, directions opposées, quantité correspondante) et les lie.

---

## 📊 WAC — Coût Moyen Pondéré

Le tableau des transactions intègre le **WAC (Weighted Average Cost)** en ligne. Lorsque vous ajoutez ou modifiez un BUY/SELL :

- Un **aperçu du WAC** apparaît dans le formulaire, affichant la base de coût projetée avant l'enregistrement.
- Après l'enregistrement, les lignes qui affectent la base de coût sont marquées d'un **indicateur ⚡**.
- Le WAC est calculé à l'exécution selon les règles FIFO/WAC — aucune étape séparée n'est nécessaire.

Consultez [Théorie Financière → Coût Moyen Pondéré](../../financial-theory/portfolio-theory/weighted-average-cost.md) pour la méthodologie sous-jacente.

---

## 📥 Importation depuis un Courtier (BRIM)

Au lieu de saisir les transactions manuellement, vous pouvez importer directement depuis le fichier d'exportation de votre courtier. Consultez le guide étape par étape **[Importation depuis un Courtier](import/index.md)**.

---

## 🔗 Liens connexes

- 📝 **[Formulaire de transaction](form.md)** — Champs, validation et options spécifiques au type
- 📥 **[Importation depuis un Courtier](import/index.md)** — Flux de travail d'importation BRIM
- 📖 **[Types de transactions](../../financial-theory/instruments/transaction-types/index.md)** — Théorie financière derrière chaque type
