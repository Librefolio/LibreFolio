# 💱 Taux FX (Change de devises)

LibreFolio inclut un système complet de gestion du **change de devises (FX)**. Il vous permet de suivre les taux de change entre n'importe quelle paire de devises, avec une synchronisation automatique à partir de sources officielles de banques centrales.

---

## 📋 La page de liste FX

Accédez à **Taux FX** depuis la barre latérale pour voir toutes vos paires de devises configurées :

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="list" data-title="🔲 Vue en grille de cartes" alt="Page de liste FX (Grille)">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="list-table" data-title="📋 Vue en tableau de données" alt="Page de liste FX (Tableau)">
</div>

Chaque paire de devises est affichée avec des détails incluant :

- 🔀 **Mises en page Grille / Tableau** : Basculez entre une grille de cartes visuelle et un tableau de données compact. La sélection est enregistrée dans le `localStorage` de votre navigateur pour les sessions ultérieures.
- 🏷️ La **paire de devises** avec les drapeaux (ex: 🇪🇺 EUR → 🇺🇸 USD)
- 📈 Le **dernier taux de change** et la tendance des prix
- 🏛️ Le **fournisseur de données actif** (ECB, FED, BOE, SNB ou MANUAL)
- 📊 Un **graphique sparkline** montrant la tendance du taux sur les 30 derniers jours
- 🖱️ **Menu contextuel** : Faites un clic droit sur n'importe quelle ligne du tableau pour des actions rapides (Modifier, Synchroniser, Supprimer)

Vous pouvez **filtrer** par devise pour trouver rapidement une paire spécifique :

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="list-filtered" alt="Liste FX filtrée" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 Et après ?

- ➕ **[Ajouter une paire](add-pair.md)** — Comment créer une nouvelle paire de devises avec des routes directes ou en chaîne
- 🔄 **[Synchronisation](sync.md)** — Synchronisation automatique et manuelle depuis les fournisseurs
- 📊 **[Page de détail de la paire](detail/index.md)** — Graphique interactif, mesures de signal, éditeur de données, configuration du fournisseur
- ⚙️ **[Paramètres du graphique](chart-settings.md)** — Personnaliser l'apparence du graphique et les superpositions de signal
- 🔌 **[Fournisseurs](providers/index.md)** — Sources de banques centrales supportées pour les taux FX (ECB, FED, BOE, SNB)
