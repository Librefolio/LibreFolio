# 📝 Formulaire de Transaction

Le formulaire de transaction s'ouvre chaque fois que vous **créez** ou **modifiez** une transaction. Il s'adapte dynamiquement au type de transaction sélectionné, affichant uniquement les champs pertinents pour cette opération.

---

## 🏷️ Types de Transactions

| Type | Icône | Description |
|------|------|-------------|
| **BUY** | 🟢 | Achat d'un actif |
| **SELL** | 🔴 | Vente d'un actif |
| **DIVIDEND** | 💰 | Dividende en espèces reçu |
| **INTEREST** | 📈 | Revenus d'intérêts (obligations, P2P) |
| **FEE** | 💸 | Frais de courtage ou frais de plateforme |
| **DEPOSIT** | ⬇️ | Dépôt d'espèces sur le compte du courtier |
| **WITHDRAWAL** | ⬆️ | Retrait d'espèces du compte du courtier |
| **ADJUSTMENT** | 🔧 | Correction manuelle de la quantité ou du prix |
| **TRANSFER** | 🔄 | Actif déplacé entre deux de vos courtiers (composite) |
| **FX_CONVERSION** | 💱 | Conversion de devise au sein d'un courtier (composite) |

Voir [Théorie Financière → Types de Transactions](../../financial-theory/instruments/transaction-types/index.md) pour la définition conceptuelle de chaque type.

---

## 📋 Champs Communs

Ces champs apparaissent pour **tous** les types de transactions :

| Champ | Requis | Description |
|-------|:--------:|-------------|
| **Type** | ✅ | Sélecteur du type de transaction |
| **Date** | ✅ | Date d'exécution (AAAA-MM-JJ) |
| **Currency** | ✅ | Devise de la transaction |
| **Amount** | ✅ | Montant brut total |
| **Fee** | ❌ | Commission de courtage ou taxe retenue |
| **Notes** | ❌ | Mémo en texte libre |

---

## 🏦 Opérations sur Actifs (BUY / SELL / TRANSFER)

Lorsqu'un actif est impliqué, des champs supplémentaires apparaissent :

| Champ | Requis | Description |
|-------|:--------:|-------------|
| **Asset** | ✅ | L'actif négocié (recherchable) |
| **Quantity** | ✅ | Nombre d'unités |
| **Unit Price** | ✅ | Prix par unité |

!!! tip "Auto-calcul"

    Si vous renseignez la **Quantity** et le **Unit Price**, le **Amount** est calculé automatiquement, et vice versa.

---

## 💰 Aperçu WAC

Pour les transactions **BUY** et **SELL**, un panneau d'**aperçu WAC (Coût Moyen Pondéré)** apparaît sous les champs principaux. Il affiche en temps réel :

- Le **prix de revient actuel** avant cette transaction
- Le **nouveau prix de revient projeté** après l'enregistrement
- Le **gain/perte réalisé** (SELL uniquement)

Cet aperçu est calculé en direct — nul besoin d'enregistrer au préalable.

!!! note "Surcharge manuelle du WAC"

    Vous pouvez passer le mode WAC de **Auto** (calculé par LibreFolio) à **Manual** (saisissez votre propre prix de revient). Ceci est utile lors de la migration de données historiques depuis un autre système.

---

## 🔄 Transactions Composites

**TRANSFER** et **FX_CONVERSION** sont *composites* — ils lient deux volets :

- **TRANSFER** : spécifie un **courtier source** et un **courtier de destination**, ainsi que l'actif et la quantité. LibreFolio enregistre les deux volets de manière atomique.
- **FX_CONVERSION** : spécifie le **montant de la devise source** et le **montant de la devise de destination** au sein du même courtier.

Pour effectuer la division d'une transaction composite en deux transactions indépendantes, utilisez l'opération [Split](index.md#split) dans le tableau des transactions.

---

## ✅ Validation

Le formulaire valide les données lors de l'enregistrement :

- Les dates doivent être dans une plage valide (pas dans le futur par défaut).
- La quantité et le prix doivent être positifs.
- Pour SELL : la quantité ne peut pas excéder la position actuelle (avertissement, pas d'erreur bloquante).
- Le montant doit correspondre à la quantité × prix avec une faible tolérance.

---

## 🔗 Liens connexes

- 📋 **[Tableau des Transactions](index.md)** — Vue en liste, filtrage, opérations groupées
- 📥 **[Import depuis Courtier](import/index.md)** — Évitez la saisie manuelle avec l'import BRIM
