# 📅 Événements d'actifs

Les événements d'actifs représentent des **opérations sur titres ou des occurrences financières planifiées** qui affectent un actif globalement — indépendamment du portefeuille de chaque investisseur. Ils sont distincts des [transactions](../transaction-types/index.md), qui suivent ce qui se passe au niveau du portefeuille (par exemple, un utilisateur achetant ou vendant des actions).

La compréhension des événements d'actifs est essentielle pour une analyse précise des prix, le calcul du rendement total et l'interprétation des graphiques historiques.

---

## 📊 Aperçu des types d'événements

| Type | Emoji | Impact sur le prix | Actifs typiques | Détails |
|------|-------|-------------------|-----------------|---------|
| **Dividende** | 💰 | Le prix baisse du montant du dividende (ex-date) | Actions, ETF | [📖](dividend.md) |
| **Intérêt** | 📈 | L'accumulation réduit le rendement restant | Obligations, Prêts, Titres à revenu fixe | [📖](interest.md) |
| **Division (Split)** | ✂️ | Le prix est divisé, la quantité est multipliée | Actions, ETF | [📖](split.md) |
| **Ajustement de prix** | 📊 | Changement algébrique (+/−) de la valeur juste | Obligations, Actifs illiquides | [📖](price-adjustment.md) |
| **Règlement à échéance** | 🏁 | Retour final du capital, fin de la valorisation | Obligations, Dépôts à terme | [📖](maturity-settlement.md) |

---

## 🔄 Événements vs Transactions

| Concept | Événements | Transactions |
|---------|--------|-------------|
| **Portée** | Globale — affecte l'actif lui-même | Personnelle — affecte le portefeuille d'un utilisateur |
| **Exemple** | "Apple a déclaré un dividende de 0,25 $ le 2024-05-10" | "J'ai reçu 12,50 $ de mes 50 actions AAPL" |
| **Effet sur le graphique** | Marqueur sur le graphique des prix | Non visible sur le graphique des prix |
| **Création par** | Fournisseur (automatique) ou utilisateur (manuel) | Importation depuis les rapports du courtier (BRIM) |

---

## ⚙️ Sources des événements

### 🤖 Générés par le fournisseur (automatique)

Certains fournisseurs produisent des événements lors de la synchronisation des données :

- **Scheduled Investment** : génère des événements `INTEREST` et `PRICE_ADJUSTMENT` à partir du calendrier d'intérêts configuré
- **Yahoo Finance** : peut produire des événements `DIVIDEND` à partir de données historiques

Les événements générés par le fournisseur possèdent un `provider_assignment_id` et sont automatiquement actualisés lors de la synchronisation (déduplication sur `asset_id + date + type`).

### ✏️ Créés par l'utilisateur (manuel)

Les événements peuvent être ajoutés manuellement via l'**Éditeur de données** ou l'**Import CSV**. Les événements manuels n'ont pas de `provider_assignment_id` et ne sont jamais supprimés automatiquement lors de la synchronisation.

---

## 📈 Marqueurs d'événements sur le graphique

Les événements apparaissent sous forme de **marqueurs en forme de losange colorés** (◆) sur le graphique de prix interactif. Chaque type d'événement possède une couleur distincte. Survolez un marqueur pour voir tous les détails (date, type, valeur, devise, notes).

Un double-clic sur un marqueur d'événement alors que l'Éditeur de données est ouvert **fait défiler directement jusqu'à la ligne de cet événement** dans l'onglet Événements.

---

## 🔗 Liens connexes

- 📈 **[Graphique interactif](../../../user/assets/detail/chart.md)** — Marqueurs d'événements sur le graphique
- ✏️ **[Éditeur de données](../../../user/assets/detail/data-editor.md)** — Gestion manuelle des événements
- 💸 **[Types de transactions](../transaction-types/index.md)** — Opérations au niveau du portefeuille
