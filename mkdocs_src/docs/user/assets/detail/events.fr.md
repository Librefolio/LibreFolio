# 📅 Événements d'actifs

Les événements d'actifs sont des choses qui arrivent à l'actif lui-même, pour tous ceux qui le détiennent : un dividende, une division, un paiement d'intérêt. Ce ne sont pas vos [transactions](../../../financial-theory/instruments/transaction-types/index.md), qui enregistrent ce qui se passe dans votre portefeuille.

---

## 📊 Types d'événements

Chaque type, avec son effet sur le prix et sa page théorique :

- 💰 **Dividende** (`DIVIDEND`) — espèces versées par une action ou un ETF ; le prix baisse d'environ ce montant à la date de détachement → [📖](../../../financial-theory/instruments/asset-events/dividend.md)
- 📈 **Intérêt** (`INTEREST`) — intérêt payé par une obligation, un prêt ou un dépôt ; la valeur baisse du montant payé → [📖](../../../financial-theory/instruments/asset-events/interest.md)
- ✂️ **Division** (`SPLIT`) — les unités sont divisées ; leur nombre change, pas la valeur totale → [📖](../../../financial-theory/instruments/asset-events/split.md)
- 📊 **Ajustement de prix** (`PRICE_ADJUSTMENT`) — un changement de valeur sans espèces, à la hausse ou à la baisse : une dépréciation, une décote, une revalorisation → [📖](../../../financial-theory/instruments/asset-events/price-adjustment.md)
- 🏁 **Règlement à l'échéance** (`MATURITY_SETTLEMENT`) — l'actif atteint son échéance et rembourse son capital ; sa valeur cesse de changer → [📖](../../../financial-theory/instruments/asset-events/maturity-settlement.md)

Les codes entre parenthèses sont ceux qu'attend un [import CSV](data-editor.md#import-from-csv).

---

## 📈 Événements sur le graphique

En mode **Prix**, les événements apparaissent sous forme de marqueurs sur le [graphique de prix](chart.md), chaque type ayant sa propre forme : un triangle pour un dividende, un losange pour l'intérêt, un carré pour un ajustement de prix, un carré arrondi pour l'échéance, une flèche pour une division. Survolez un marqueur pour afficher sa date, son type, son montant et ses notes.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-events" alt="Graphique d'actif avec un marqueur d'événement survolé">
</div>

- **Dans une autre devise**, le montant est converti, avec le montant d'origine en dessous ; un événement qui ne peut pas être converti est masqué.
- **Les actifs comparés** affichent aussi leurs événements, dans la couleur de leur ligne.

---

## ⚙️ D'où viennent les événements

- **D'un fournisseur**, à chaque synchronisation : les dividendes et divisions de [Yahoo Finance](../providers/yahoo-finance.md), les dividendes de [justETF](../providers/justetf.md), et, depuis l'[investissement programmé](../providers/scheduled-investment.md), les paiements d'intérêt et le règlement final à l'échéance de **Generate Coupon**, plus les événements listés dans le calendrier de l'investissement programmé (**Ajouter un événement** dans le formulaire de l'actif).
- **De vous** : dans l'onglet **Événements** de l'[éditeur de données](data-editor.md), un par un ou depuis un fichier CSV, ou avec **Nouvel événement** dans le champ **Événement lié** d'une transaction.

Une synchronisation actualise les événements du fournisseur et ne touche jamais aux vôtres. Un événement d'un fournisseur est en lecture seule dans l'éditeur, et sa suppression ne dure que jusqu'à ce que le fournisseur le renvoie : pour modifier les événements d'un investissement programmé, modifiez son calendrier.

---

## 🧮 Événements dans un investissement programmé

Pour un [investissement programmé](../providers/scheduled-investment.md#how-value-is-calculated), les événements font partie du prix lui-même :

$$
P(d) = V_0 + I(d) - \sum \text{Intérêt} + \sum \text{Ajustements de prix}
$$

avec $V_0$ la valeur initiale et $I(d)$ les intérêts courus jusqu'ici. Pour un actif coté sur le marché, les événements expliquent seulement les mouvements du prix, comme la baisse à une date de détachement de dividende ; ils ne modifient pas les prix envoyés par le fournisseur.

---

## 🔗 Voir aussi

- 📈 **[Graphique interactif](chart.md)** — Marqueurs d'événements sur le graphique
- ✏️ **[Éditeur de données](data-editor.md)** — Gestion manuelle des événements avec import CSV
- 🧮 **[Investissement programmé](../providers/scheduled-investment.md)** — Fournisseur qui génère des événements à partir de calendriers d'intérêts
- 📚 **[Événements d'actifs (Théorie financière)](../../../financial-theory/instruments/asset-events/index.md)** — Analyse détaillée de chaque type d'événement
- 💸 **[Types de transactions (Théorie financière)](../../../financial-theory/instruments/transaction-types/index.md)** — Transactions vs événements
- 🛠️ **[Événements d'actifs (développeur)](../../../developer/backend/assets/events.md)** — Pour les développeurs : comment les événements sont stockés et actualisés
