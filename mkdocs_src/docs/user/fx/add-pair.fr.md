# ➕ Ajouter une paire de devises

Une paire indique à LibreFolio d'où provient le taux de change entre deux devises : un fournisseur
de banque centrale, une chaîne de fournisseurs, ou des taux que vous saisissez vous-même.

Cliquez sur **Ajouter une paire** sur la [page FX](index.md). La même fenêtre s'ouvre depuis le
tableau de bord, depuis une page d'actif et depuis l'étape Change de l'allocateur PAC.

---

## 🧭 Ajouter une paire étape par étape

### 💱 Étape 1 : Choisir les deux devises

Dans **Ajouter une nouvelle paire de devises**, choisissez la **Devise de base** et la **Devise de
cotation**. Chaque liste masque les devises déjà appariées avec l'autre, afin qu'une paire ne puisse
pas être ajoutée deux fois.

### 🛤️ Étape 2 : Choisir une route

Cliquez sur **Ajouter une route de conversion** pour voir toutes les façons dont les fournisseurs
peuvent produire ce taux :

- 🔗 **Conversion directe (1 étape)** — un fournisseur publie la paire ;
- 🔀 **Conversion en chaîne** — passe par d'autres devises, regroupées par nombre d'étapes ;
- 🚫 **Non utilisable** — fournisseurs qui ne peuvent pas atteindre cette paire.

Filtrez avec la zone de recherche (fournisseur, devise ou pays), puis cliquez sur une route pour
l'ajouter.

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-routes" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="add-pair-routes" data-title="🔗 Routes directes" alt="Ajouter Paire — Routes directes">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="add-pair-chain" data-title="🔀 Routes en chaîne (plusieurs étapes)" alt="Ajouter Paire — Routes en chaîne">
</div>

??? tip "🛟 Routes de secours — lorsque vous en ajoutez plusieurs"

    LibreFolio utilise d'abord la route **#1** et essaie la **#2** si elle échoue lors d'une
    synchronisation, et ainsi de suite. Faites glisser les routes pour les réordonner ; 🗑️ en
    supprime une, et ⚠️ affiche une note de son fournisseur.

??? note "🔀 Créer aussi les paires intermédiaires — lorsque vous choisissez une route en chaîne"

    Cochez **Créer aussi les paires intermédiaires** pour enregistrer chaque étape comme une paire à
    part entière. Vous pouvez alors synchroniser chaque étape séparément et convertir également vers
    la devise intermédiaire : une chaîne ne stocke que le taux de sa propre paire.

??? note "✏️ Aucune route — taux manuels uniquement"

    Vous pouvez enregistrer sans route, puis saisir vous-même les taux dans l'[éditeur de
    données](detail/data-editor.md) de la paire.

### 💾 Étape 3 : Enregistrer

Cliquez sur **Enregistrer la configuration** ; la fenêtre se ferme immédiatement.

- **Avec un fournisseur**, LibreFolio télécharge **tout l'historique** de la paire jusqu'à
  aujourd'hui, quelle que soit la période affichée par la page, paires intermédiaires comprises. Un
  message indique le résultat, en vert uniquement si tout a fonctionné.
- **Sans fournisseur**, un message confirme que la paire a été créée.

Cliquez sur le nom de la paire dans le message pour ouvrir sa page.

---

## 🛤️ Routes directes et en chaîne

Une **route directe** utilise un seul fournisseur qui publie les deux devises, comme la BCE pour
EUR 🇪🇺 / USD 🇺🇸. Lorsqu'aucune banque centrale ne publie la paire, une **route en chaîne**
multiplie les taux de ses étapes. RON 🇷🇴 / USD 🇺🇸, par exemple, passe par RON → EUR → USD, les deux
étapes provenant de la BCE, qui publie EUR/RON et EUR/USD :

$$
r_{\text{RON}\to\text{USD}} = r_{\text{RON}\to\text{EUR}} \times r_{\text{EUR}\to\text{USD}}
$$

- Une chaîne n'a de taux que les jours où **chaque étape** en a un.
- Si une étape échoue lors d'une synchronisation, toute la chaîne échoue : les chaînes plus courtes
  sont plus fiables.
- Le taux d'une chaîne peut légèrement différer d'une cotation directe du marché.

---

## 🔗 Voir aussi

- 🔄 **[Synchronisation](sync.md)** — Télécharger à nouveau les taux plus tard
- 🔌 **[Configuration du fournisseur](detail/provider.md)** — Modifier les routes d'une paire après sa création
- 🧑‍💻 Pour les développeurs : **[Configuration & routage FX](../../developer/backend/fx/configuration.md)** et **[Algorithme de chaîne FX](../../developer/frontend/fx-chain-algorithm.md)**
