# 💱 Taux de change (Change de devises)

LibreFolio convertit vos montants entre devises avec les taux conservés ici. Chaque paire de devises
télécharge ses taux auprès d'une banque centrale (ECB, FED, BOE ou SNB), ou conserve les taux que vous saisissez vous-même.

---

## 📋 La page de liste des taux de change

Ouvrez **Taux de change** depuis la barre latérale pour voir vos paires de devises :

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="list" data-title="🔲 Vue grille de cartes" alt="Page de liste FX (Grille)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="list-table" data-title="📋 Vue tableau de données" alt="Page de liste FX (Tableau)">
</div>

Chaque paire affiche ses drapeaux (par ex. 🇪🇺 EUR → 🇺🇸 USD), son **dernier taux**, la variation sur la période
sélectionnée et un mini graphique. Un badge ✏️ **Manuel** marque les paires sans fournisseur. Cliquez sur une paire pour ouvrir
sa [page de détail](detail/index.md).

### 🔀 Cartes ou tableau

- Le bouton de bascule d'affichage à côté de **Ajouter une paire** permet de passer entre les cartes et le tableau ; LibreFolio se souvient de votre
  choix.
- Dans le tableau, les colonnes **Δ** affichent la variation sur le dernier jour, sur la période sélectionnée et, pour les périodes longues,
  de 1 semaine à 5 ans. Le bouton **Colonnes** permet d'ajouter des colonnes masquées, telles que les **Fournisseurs** de chaque paire.
- Sélectionnez des lignes pour agir sur plusieurs paires à la fois, ou faites un clic droit sur une ligne.

### 🔍 Filtrer par devise

Choisissez une devise dans **Filtrer par devise** pour ne lister que ses paires, et une **Seconde devise** pour réduire
la liste à une seule paire ; ✕ efface les deux.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="list-filtered" alt="Liste FX filtrée" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧰 Actions de la page et des paires

- Le sélecteur de **période** en haut définit la plage de chaque graphique et variation ; en vue cartes,
  **Abs** / **%** affiche toutes les cartes sous forme de taux ou de variation en %.
- **Synchroniser tout** télécharge les nouveaux taux ([Synchronisation](sync.md)) ; **Recharger tout** relit les taux
  stockés. Le bouton **Paramètres** permet de définir l'apparence de chaque carte ([Paramètres du graphique](chart-settings.md)).
- Sur une carte, ⇄ inverse la direction affichée (USD → EUR au lieu de EUR → USD) ; les boutons en bas
  ouvrent ses propres paramètres du graphique, permettent de la **synchroniser** ou de la **recharger**, ou de la supprimer.

!!! warning "Supprimer une paire supprime ses taux"

    Supprimer une paire supprime ses paramètres de fournisseur **et tous ses taux stockés**, une fois que vous confirmez.

---

## 🔮 Et ensuite ?

- ➕ **[Ajouter une paire](add-pair.md)** — Créez une paire avec une route directe ou en chaîne
- 🔄 **[Synchronisation](sync.md)** — Téléchargez les taux, manuellement ou selon un calendrier
- 📊 **[Page de détail d'une paire](detail/index.md)** — Graphique, signaux, mesures, éditeur de taux et fournisseurs
- ⚙️ **[Paramètres du graphique](chart-settings.md)** — Apparence du graphique et signaux superposés
- 🔌 **[Fournisseurs](providers/index.md)** — Les banques centrales que LibreFolio lit (ECB, FED, BOE, SNB)
