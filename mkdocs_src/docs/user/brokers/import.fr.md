# 📥 Transactions du broker

L'onglet **Transactions** est le centre de contrôle pour modifier le registre du courtier. Il répertorie toutes les opérations financières enregistrées (achats, ventes, dividendes, dépôts, retraits, transferts et conversions de devise) limitées à ce courtier.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="transactions-tab" alt="Onglet Transactions du courtier">
</div>

Depuis cet onglet, vous pouvez effectuer des transactions manuelles ou lancer des importations groupées de relevés.

---

## ➕ Transactions manuelles

Cliquez sur le bouton **Ajouter une transaction** (icône `Plus`) pour ouvrir l'assistant modal de transaction unique. Cela vous permet d'enregistrer manuellement :

- **Achat / Vente** : Négocier des actifs, en spécifiant la date, le prix, la quantité et la devise.
- **Dividende / Revenu** : Revenus perçus provenant des actifs détenus.
- **Dépôt / Retrait** : Entrées ou sorties de trésorerie externes vers/depuis le solde de trésorerie du courtier.
- **Transfert** : Transfert de trésorerie ou d'actifs entre courtiers (par exemple, approvisionnement du compte depuis un courtier bancaire).
- **Conversion de devise** : Échanges de devises à l'intérieur du compte du courtier.

Pour une explication détaillée des champs de transaction et des règles de validation, consultez le guide **[Formulaire de transaction](../transactions/form.md)**.

---

## 🧙 BRIM : Module d'importation des relevés de courtier

Le bouton **Importer** (icône `Télécharger`) lance l'assistant **BRIM**. Ce module vous permet d'importer en masse les relevés exportés de votre courtier (formats CSV ou Excel), d'exécuter des validations de cohérence automatiques et de mapper les tickers aux actifs locaux avant la validation finale.

### Le flux d'importation

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-import" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Fenêtre modale d'importation rapide" alt="Fenêtre modale d'importation">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Assistant — Étape 1 : Importation" alt="Assistant d'importation Étape 1">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Assistant — Étape 2 : Configuration de l'analyseur" alt="Assistant d'importation Étape 2">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Assistant — Étape 3 : Analyse" alt="Assistant d'importation Étape 3">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Assistant — Étape 4 : Résolution d'actifs" alt="Résolution d'actifs de l'assistant d'importation">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Détection des doublons" alt="Détection des doublons de l'assistant d'importation">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Zone de préparation en masse" alt="Zone de préparation en masse de l'importation">
</div>

L'assistant progresse à travers les étapes suivantes :

1. **Sélectionner le fichier et l'analyseur** : Choisissez le fichier de relevé et sélectionnez la configuration d'analyseur appropriée (par exemple, Interactive Brokers, Degiro, Directa, Charles Schwab, CSV générique, etc.).
2. **Vérifier les en-têtes et le mappage** : Affiche les en-têtes CSV pour confirmer que l'analyseur s'aligne correctement avec les colonnes.
3. **Analyse des opérations** : Traite le fichier et affiche une grille de prévisualisation des actions analysées (Achats, Ventes, Dividendes, etc.).
 * **Badges** : Les opérations sont étiquetées comme `UNIQUE` (nouvelle transaction), `DUPLICATE` (existe déjà dans la base de données) ou `UNRESOLVED` (nécessite un mapping ticker/ISIN).
 * **Notes TODO** : Met en évidence les champs nécessitant une attention ou les éléments qui n'ont pas pu être analysés automatiquement.
4. **Résolution d'actifs** : Si le relevé contient des tickers ou ISIN qui n'existent pas dans votre registre d'actifs local, BRIM affiche une étape de mappage. Vous pouvez :
 * Mapper le ticker à un actif existant.
 * Créer un nouvel actif directement depuis cet écran, pré-rempli avec les détails extraits du relevé.
5. **Zone de préparation en masse et validation** : Passez en revue la liste de contrôle préparée des transactions propres et uniques. Décochez les opérations que vous souhaitez exclure, puis cliquez sur **Valider** pour écrire les enregistrements dans le registre de votre portefeuille.

---

## 📑 Historique des importations

Cliquez sur le bouton **Afficher l'historique des importations** (icône `FileText`) pour voir un registre complet des tâches d'importation précédentes. Il affiche :

- Le nom du fichier importé et sa taille.
- Les lignes traitées et le total des transactions validées.
- L'horodatage de l'importation.
- L'utilisateur qui a effectué l'importation.
