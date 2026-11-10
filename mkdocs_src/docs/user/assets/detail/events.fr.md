# 📅 Événements d'actifs

Les événements d'actifs sont des faits qui se produisent sur l'actif lui-même, pour toutes les personnes qui le détiennent : un dividende, une division, le paiement d'un intérêt. Ils ne sont pas vos [transactions](../../../financial-theory/instruments/transaction-types/index.md), qui enregistrent ce qui se passe dans votre portefeuille.

---

## 📊 Types d'événements

Chaque type, avec son effet sur le prix et sa page théorique :

- 💰 **Dividende** (`DIVIDEND`) — montant en espèces versé par une action ou un ETF ; le prix baisse à peu près de ce montant à la date ex-dividende → [📖](../../../financial-theory/instruments/asset-events/dividend.md)
- 📈 **Intérêt** (`INTEREST`) — intérêts payés par une obligation, un prêt ou un dépôt ; la valeur baisse du montant versé → [📖](../../../financial-theory/instruments/asset-events/interest.md)
- ✂️ **Division** (`SPLIT`) — les unités sont divisées ; leur nombre change, pas la valeur totale → [📖](../../../financial-theory/instruments/asset-events/split.md)
- 📊 **Ajustement de prix** (`PRICE_ADJUSTMENT`) — une variation de valeur sans flux de trésorerie, à la hausse ou à la baisse : une dépréciation, une décote, une réévaluation → [📖](../../../financial-theory/instruments/asset-events/price-adjustment.md)
- 🏁 **Règlement à l'échéance** (`MATURITY_SETTLEMENT`) — l'actif arrive à échéance et rembourse son capital ; sa valeur cesse de changer → [📖](../../../financial-theory/instruments/asset-events/maturity-settlement.md)

Les codes entre parenthèses sont ceux qu'attend un [import CSV](data-editor.md#import-from-csv).

---

## 📈 Événements sur le graphique

En mode **Prix**, les événements apparaissent sous forme de marqueurs sur le [graphique des prix](chart.md), chaque type ayant sa propre forme : un triangle pour un dividende, un losange pour un intérêt, un carré pour un ajustement de prix, un carré arrondi pour l'échéance, une flèche pour une division. Survolez un marqueur pour afficher sa date, son type, son montant et ses notes.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-events" alt="Graphique d'actif avec un marqueur d'événement survolé">
</div>

- **Dans une autre devise**, le montant est converti, avec le montant d'origine en dessous ; un événement qui ne peut pas être converti est masqué.
- **Les actifs comparés** affichent eux aussi leurs événements, dans la couleur de leur ligne.

---

## ⚙️ D'où viennent les événements

- **Depuis un fournisseur**, à chaque synchronisation : les dividendes et divisions de [Yahoo Finance](../providers/yahoo-finance.md), les dividendes de [justETF](../providers/justetf.md), et, depuis [Investissement programmé](../providers/scheduled-investment.md), les paiements d'intérêts et le règlement final à l'échéance de **Générer un coupon**, ainsi que les événements listés dans son calendrier d'intérêts (**Ajouter un événement** dans le formulaire d'actif).
- **De votre côté** : dans l'onglet **Événements** de l'[Éditeur de données](data-editor.md), un par un ou à partir d'un fichier CSV, ou avec **+ Nouvel événement** dans le champ **Événement lié** d'une transaction ([ci-dessous](#new-event)).

Une synchronisation actualise les événements du fournisseur et ne touche jamais aux vôtres. Un événement provenant d'un fournisseur est en lecture seule dans l'éditeur, et sa suppression ne dure que jusqu'à ce que le fournisseur le renvoie : pour modifier les événements d'un investissement programmé, modifiez son calendrier d'intérêts. Retirer le fournisseur (**Aucun fournisseur** dans le [formulaire d'actif](../create-edit.md#editing-an-asset)) supprime ses événements, et cette opération est refusée tant qu'une transaction est liée à l'un d'eux.

### ✨ Nouvel événement depuis une transaction {: #new-event }

**+ Nouvel événement**, dans le champ **Événement lié** d'un dividende, d'un intérêt ou d'un ajustement, crée un événement pour l'actif de la transaction et le lie à la transaction. Il n'écrase jamais un événement : si l'actif en possède déjà un de ce type à cette date, saisi manuellement ou provenant d'un fournisseur de données, rien n'est enregistré et la fenêtre affiche ce qui s'y trouve sous *Cet événement existe déjà*. Pour chaque événement : son type, sa date, son montant et ses notes, sa provenance et le nombre de transactions qui lui sont liées. Choisissez ensuite :

- **Utiliser celui-ci** — lie cet événement à la transaction, sans rien modifier d'autre.
- **Modifier celui-ci** — uniquement pour un événement saisi manuellement : la fenêtre devient *Modifier l'événement pour …*, remplie avec les valeurs de cet événement. Modifiez ce qui est nécessaire et cliquez sur **Enregistrer** : ce même événement est mis à jour, y compris pour les transactions qui y sont déjà liées, et cette transaction y est liée.
- **Annuler** — retour au formulaire, avec ce que vous avez saisi (le bouton **Annuler** en bas ferme la fenêtre).

Un événement provenant d'un fournisseur de données ne propose que **Utiliser celui-ci**, avec une note : le fournisseur met à jour ses propres événements. Il n'est pas possible d'ajouter ici un second événement du même type à la même date. Dans l'[Éditeur de données](data-editor.md), en revanche, une nouvelle ligne ou une ligne CSV à la date et au type de l'un de vos événements met à jour cet événement.

Après **Modifier celui-ci**, le champ **Événement lié** affiche l'événement avec ses nouvelles valeurs.

---

## 🧮 Événements dans un investissement programmé

Pour un [Investissement programmé](../providers/scheduled-investment.md#how-value-is-calculated), les événements font partie du prix lui-même :

$$
P(d) = V_0 + I(d) - \sum \text{Intérêts} + \sum \text{Ajustements de prix}
$$

avec $V_0$ la valeur initiale et $I(d)$ les intérêts courus à ce jour. Pour un actif valorisé au marché, les événements expliquent seulement les mouvements du prix, comme la baisse à une date ex-dividende ; ils ne modifient pas les prix envoyés par le fournisseur.

---

## 🔗 Voir aussi

- 📈 **[Graphique interactif](chart.md)** — Marqueurs d'événements sur le graphique
- ✏️ **[Éditeur de données](data-editor.md)** — Gestion manuelle des événements avec import CSV
- 🧮 **[Investissement programmé](../providers/scheduled-investment.md)** — Fournisseur qui génère des événements à partir des calendriers d'intérêts
- 📚 **[Événements d'actifs (Théorie financière)](../../../financial-theory/instruments/asset-events/index.md)** — Analyse détaillée de chaque type d'événement
- 💸 **[Types de transactions (Théorie financière)](../../../financial-theory/instruments/transaction-types/index.md)** — Transactions vs événements
- 🛠️ **[Événements d'actifs (développeur)](../../../developer/backend/assets/events.md)** — Pour les développeurs : comment les événements sont stockés et actualisés
