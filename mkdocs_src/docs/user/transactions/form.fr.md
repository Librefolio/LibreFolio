# 📝 Formulaire de Transaction

Le Formulaire de Transaction s'ouvre chaque fois que vous **créez** ou **modifiez** une transaction. Il s'adapte dynamiquement au type de transaction sélectionné, n'affichant que les champs pertinents pour cette opération.

---

## 🏷️ Types de Transactions

Pour une définition conceptuelle approfondie de chaque opération, veuillez vous référer au [guide de Théorie Financière](../../financial-theory/instruments/transaction-types/index.md).

<div class="lf-screenshot-carousel" data-carousel="transactions" data-carousel-interval="3000" data-show-titles="true">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> ACHAT' alt="Achat">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VENTE' alt="Vente">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-dividend" data-title='<img src="/LibreFolio/static/icons/transactions/dividend.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DIVIDENDE' alt="Dividende">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-deposit" data-title='<img src="/LibreFolio/static/icons/transactions/deposit.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DÉPÔT' alt="Dépôt">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-adjustment" data-title='<img src="/LibreFolio/static/icons/transactions/adjustment.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> AJUSTEMENT' alt="Ajustement">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRANSFERT' alt="Transfert d'actif">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-fxconversion" data-title='<img src="/LibreFolio/static/icons/transactions/fx-conversion.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> CONVERSION FX' alt="Conversion FX">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-cash-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/cash-transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRANSFERT DE LIQUIDITÉS' alt="Transfert de cash">
</div>

### Transactions Simples

Celles-ci opèrent indépendamment sur un seul compte de courtage.

| Type | Description | Guide Théorique |
|------|-------------|--------------|
| ![](../../static/icons/transactions/buy.png){: width="24" style="vertical-align: middle;" } **ACHAT / VENTE** ![](../../static/icons/transactions/sell.png){: width="24" style="vertical-align: middle;" } | Achat ou vente d'un actif | [📖 Lire](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/deposit.png){: width="24" style="vertical-align: middle;" } **DÉPÔT / RETRAIT** ![](../../static/icons/transactions/withdrawal.png){: width="24" style="vertical-align: middle;" } | Ajout ou retrait de liquidités d'un compte de courtage | [📖 Lire](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/dividend.png){: width="24" style="vertical-align: middle;" } **DIVIDENDE / INTÉRÊT** ![](../../static/icons/transactions/interest.png){: width="24" style="vertical-align: middle;" } | Rendement d'actifs actions ou à taux fixe | [📖 Lire](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/fee.png){: width="24" style="vertical-align: middle;" } **FRAIS / TAXE** ![](../../static/icons/transactions/tax.png){: width="24" style="vertical-align: middle;" } | Coûts tels que les frais de courtage ou les taxes | [📖 Lire](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/adjustment.png){: width="24" style="vertical-align: middle;" } **AJUSTEMENT** | Correction manuelle des soldes | [📖 Lire](../../financial-theory/instruments/transaction-types/adjustment.md) |

### Transactions Composites

Celles-ci représentent des mouvements **entre** des comptes ou des devises. Elles produisent deux entrées liées qui s'équilibrent.

| Type | Description | Guide Théorique |
|------|-------------|--------------|
| ![](../../static/icons/transactions/transfer.png){: width="24" style="vertical-align: middle;" } **TRANSFERT** | Actif déplacé entre deux de vos courtiers | [📖 Lire](../../financial-theory/instruments/transaction-types/transfer.md) |
| ![](../../static/icons/transactions/cash-transfer.png){: width="24" style="vertical-align: middle;" } **TRANSFERT DE LIQUIDITÉS** | Virement bancaire entre courtiers | [📖 Lire](../../financial-theory/instruments/transaction-types/cash-transfer.md) |
| ![](../../static/icons/transactions/fx-conversion.png){: width="24" style="vertical-align: middle;" } **CONVERSION FX** | Change de devises au sein d'un courtier | [📖 Lire](../../financial-theory/instruments/transaction-types/fx-conversion.md) |

---

## 📋 L'Interface du Formulaire

Le formulaire est conçu pour être intuitif et dynamique. Lorsque vous sélectionnez un **Type de Transaction**, le formulaire s'ajuste automatiquement pour n'afficher que les champs pertinents.

- **Détails de base :** Date, Type, Devise et Montant.
- **Spécificités de l'actif :** Si la transaction implique un actif (comme ACHAT ou VENTE), des champs pour sélectionner l'actif, saisir la quantité et définir le prix unitaire apparaîtront.
- **Panneau de prévisualisation (WAC) :** Pour les opérations affectant votre portefeuille, une prévisualisation en temps réel apparaît en bas. Elle affiche votre prix de revient actuel, le nouveau prix de revient projeté, ainsi que tout gain ou perte réalisé.

> **💡 Note :** Le système gère automatiquement les calculs standard pour vous (comme la multiplication de la quantité par le prix unitaire) afin que vous n'ayez pas à faire les calculs manuellement.

---

## 🔄 Transactions Composites

**TRANSFERT** et **CONVERSION FX** sont *composites* — ils lient deux volets :

- **TRANSFERT** : spécifie un **courtier source** et un **courtier de destination**, ainsi que l'actif et la quantité. LibreFolio enregistre les deux volets de manière atomique.
- **CONVERSION FX** : spécifie le **montant de la devise source** et le **montant de la devise de destination** au sein du même courtier.

Pour diviser une transaction composite en deux transactions indépendantes, utilisez l'opération [division](index.md) dans le tableau des transactions.

---

## 🔗 Liens connexes

- 📋 **[Tableau des Transactions](index.md)** — Vue en liste, filtrage, opérations groupées
- 📥 **[Importer depuis un Courtier](import/index.md)** — Évitez la saisie manuelle avec l'import BRIM
