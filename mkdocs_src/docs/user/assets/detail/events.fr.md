# 📅 Événements d'actif

Les événements d'actif correspondent aux événements qui affectent l'actif **globalement** — et non au niveau du portefeuille. Ils sont distincts des [transactions](../../../financial-theory/instruments/transaction-types/index.md), qui suivent ce qui se passe dans le portefeuille d'un utilisateur.

Pour une analyse approfondie de chaque type d'événement — incluant l'impact sur le marché, les formules et des exemples pratiques — consultez la section **[Événements d'actif (Théorie Financière)](../../../financial-theory/instruments/asset-events/index.md)**.

---

## 📊 Types d'événements

| Type | Icône | Effet sur le prix | Description | En savoir plus |
|------|------|------------------|-------------|-----------|
| **Dividende** | 💰 | Le prix baisse de la valeur de l'événement (ex-date) | Distribution de liquidités provenant d'une action ou d'un ETF | [📖](../../../financial-theory/instruments/asset-events/dividend.md) |
| **Intérêt** | 📈 | Le prix baisse de la valeur de l'événement | Paiement d'intérêts provenant d'un instrument de dette ou d'un prêt | [📖](../../../financial-theory/instruments/asset-events/interest.md) |
| **Division** | ✂️ | Modifie la quantité, pas la valeur totale | Division d'actions ou d'unités | [📖](../../../financial-theory/instruments/asset-events/split.md) |
| **Ajustement de prix** | 📊 | Changement algébrique (+/-) | Changement de valeur non monétaire : dépréciation, décote, réévaluation | [📖](../../../financial-theory/instruments/asset-events/price-adjustment.md) |
| **Règlement à l'échéance** | 🏁 | Retour final du capital | L'actif atteint son échéance — plus aucun calcul de prix n'est effectué | [📖](../../../financial-theory/instruments/asset-events/maturity-settlement.md) |

## 📈 Marqueurs d'événements sur le graphique

Les événements apparaissent sous forme de **marqueurs colorés** sur le [graphique de prix](chart.md). Chaque type d'événement a une couleur et une icône distinctes. Survolez un marqueur pour voir les détails de l'événement (date, type, valeur, devise).

## ⚙️ Provenance des événements

Les événements peuvent être générés de deux manières :

### 1. Générés par le fournisseur (automatique)

Certains fournisseurs produisent des événements lors de la synchronisation :

- **[Scheduled Investment](../providers/scheduled-investment.md)** : génère des événements INTEREST et PRICE_ADJUSTMENT à partir de la configuration de l'échéancier d'intérêts
- **[Yahoo Finance](../providers/yahoo-finance.md)** : peut produire des événements DIVIDEND à partir de données historiques

Les événements générés par le fournisseur possèdent un `provider_assignment_id` et sont automatiquement mis à jour lors de la synchronisation (déduplication DELETE + INSERT sur `asset_id, date, type`).

### 2. Créés par l'utilisateur (manuel)

Les événements peuvent également être ajoutés manuellement via la fenêtre de modification de l'actif. Les événements manuels n'ont pas de `provider_assignment_id` et ne sont jamais supprimés automatiquement lors de la synchronisation.

---

## 🧮 Comment les événements affectent le calcul du prix

Pour le fournisseur **Scheduled Investment**, les événements font partie intégrante du calcul du prix :

```
price(d) = initial_value + accrued_interest − Σ(INTEREST events) + Σ(PRICE_ADJUSTMENT events)
```

Pour les actifs dont le prix est fixé par le marché (Yahoo Finance, justETF), les événements sont informatifs — ils expliquent les chutes de prix soudaines (dates de détachement (ex-date)) mais ne modifient pas directement le prix récupéré.

---

## 🔗 Articles connexes

- 📈 **[Graphique interactif](chart.md)** — Marqueurs d'événements sur le graphique
- ✏️ **[Éditeur de données](data-editor.md)** — Gestion manuelle des événements avec import CSV
- 🧮 **[Scheduled Investment](../providers/scheduled-investment.md)** — Fournisseur qui génère des événements à partir d'échéanciers d'intérêts
- 📚 **[Événements d'actif (Théorie Financière)](../../../financial-theory/instruments/asset-events/index.md)** — Analyse détaillée de chaque type d'événement
- 💸 **[Types de transactions (Théorie Financière)](../../../financial-theory/instruments/transaction-types/index.md)** — Transactions vs événements
