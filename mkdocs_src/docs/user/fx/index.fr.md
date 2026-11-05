# 💱 Taux de change (change de devises)

LibreFolio convertit vos montants entre devises à l'aide des taux conservés ici. Chaque paire de devises
télécharge ses taux depuis une banque centrale (ECB, FED, BOE ou SNB), ou conserve les taux que vous saisissez vous-même.

---

## 📋 La page de liste des taux de change

Ouvrez **Taux de change** depuis la barre latérale pour voir vos paires de devises :

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="list" data-title="🔲 Vue en grille de cartes" alt="Page de liste des taux de change (grille)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="list-table" data-title="📋 Vue en tableau de données" alt="Page de liste des taux de change (tableau)">
</div>

Chaque paire affiche ses drapeaux (par ex. 🇪🇺 EUR → 🇺🇸 USD), son **dernier taux**, la variation sur la
période sélectionnée et un mini graphique. Lorsque le graphique regroupe les taux par semaine ou par mois
parce que la zone de tracé est trop étroite pour autant de jours, un badge **Hebdomadaire** ou
**Mensuel** en haut à gauche l'indique, comme sur la
[page de détail](detail/chart.md). Un badge ✏️ **Manuel** signale les paires sans fournisseur. Cliquez sur une paire pour ouvrir
sa [page de détail](detail/index.md).

### 🔀 Cartes ou tableau

- Le sélecteur de vue à côté de **Ajouter une paire** bascule entre les cartes et le tableau ; LibreFolio
  se souvient de votre choix.
- Dans le tableau, les colonnes **Δ** affichent la variation sur le dernier jour, sur la période et, sur les
  périodes longues, de 1S à 5A. L'option **Colonnes** permet d'ajouter des colonnes masquées, comme les **Fournisseurs** de
  chaque paire.
- Sélectionnez des lignes pour agir sur plusieurs paires à la fois, ou faites un clic droit sur une ligne.

### 🔍 Filtrer par devise

Choisissez une devise dans **Filtrer par devise** pour n'afficher que ses paires, et une **Seconde devise**
pour réduire la liste à une seule paire ; ✕ efface les deux.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="list-filtered" alt="Liste des taux de change filtrée" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧰 Actions de la page et des paires

- Le sélecteur de **période** en haut définit la plage de tous les graphiques et de toutes les variations ; en
  vue cartes, l'icône de courbe (infobulle **Afficher en absolu**), **%** et l'icône de calendrier (**Rendement glissant**) affichent
  toutes les cartes sous forme de taux, de variation en % ou de rendement glissant. La
  liste s'ouvre sur **Abs** ; une fois que vous avez choisi une vue, elle est mémorisée pour vous dans ce navigateur.
- Le bouton de vue d'une carte enchaîne **%** → **Rendement glissant** → **Abs** et indique la vue vers laquelle il
  bascule. La carte conserve son propre choix d'un rechargement à l'autre jusqu'à ce que vous modifiiez la barre d'outils, ce qui réinitialise toutes les cartes.
  En **Rendement glissant**, une carte trace le rendement glissant du taux correspondant à la paire affichée par la carte
  (inversée avec ⇄ : le rendement du taux inversé), et par-dessus, les rendements glissants des paires FX
  comparées sur cette carte. Le taux et sa variation en haut restent tels quels, et avec un historique
  trop court, la carte affiche un court message à la place du graphique. La fenêtre glissante est celle définie dans
  les [Paramètres du graphique](chart-settings.md).
- Une carte trace les comparaisons enregistrées dans ses [Paramètres du graphique](chart-settings.md), avec une autre paire FX
  ou avec un actif. La courbe d'un actif est son prix dans la devise de l'actif lui-même, comparez-la donc dans
  la vue **%** ; les prix ne sont chargés qu'une seule fois pour toutes les cartes qui comparent un actif.
- **Tout synchroniser** télécharge les nouveaux taux ([Synchronisation](sync.md)) ; **Tout recharger** relit les
  taux stockés. Le bouton **Paramètres** définit l'apparence de chaque carte ([Paramètres du graphique](chart-settings.md)). Survolez
  l'un des trois pendant une demi-seconde pour lire ce qu'il fait.
- Sur une carte, ⇄ inverse le sens affiché (USD → EUR au lieu de EUR → USD) ; les boutons en bas permettent d'ouvrir ses propres paramètres du graphique, de la **synchroniser**, de la **recharger** ou de la supprimer.

!!! warning "Supprimer une paire supprime ses taux"

    Supprimer une paire supprime ses paramètres de fournisseur **et tous ses taux stockés**, une fois que vous confirmez.

---

## 🔮 Et ensuite ?

- ➕ **[Ajouter une paire](add-pair.md)** — Créer une paire avec une route directe ou en chaîne
- 🔄 **[Synchronisation](sync.md)** — Télécharger les taux, manuellement ou selon un planning
- 📊 **[Page de détail d'une paire](detail/index.md)** — Graphique, signaux, mesures, éditeur de taux et fournisseurs
- ⚙️ **[Paramètres du graphique](chart-settings.md)** — Apparence du graphique et signaux superposés
- 🔌 **[Fournisseurs](providers/index.md)** — Les banques centrales que LibreFolio lit (ECB, FED, BOE, SNB)
