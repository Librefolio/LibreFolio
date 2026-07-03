# 📝 Formulaire de Transaction

Le Formulaire de Transaction s'ouvre chaque fois que vous **créez** ou **modifiez** une transaction. Il s'adapte dynamiquement au type de transaction sélectionné, n'affichant que les champs pertinents pour cette opération.

<div class="lf-screenshot-carousel" data-carousel="transactions" data-carousel-interval="3000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> ACHAT' alt="Achat">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VENTE' alt="Vente">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-dividend" data-title='<img src="/LibreFolio/static/icons/transactions/dividend.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DIVIDENDE' alt="Dividende">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-deposit" data-title='<img src="/LibreFolio/static/icons/transactions/deposit.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DÉPÔT' alt="Dépôt">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-adjustment" data-title='<img src="/LibreFolio/static/icons/transactions/adjustment.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> AJUSTEMENT' alt="Ajustement">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRANSFERT' alt="Transfert d'actif">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-fxconversion" data-title='<img src="/LibreFolio/static/icons/transactions/fx-conversion.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> CONVERSION FX' alt="Conversion FX">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-cash-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/cash-transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRANSFERT DE LIQUIDITÉS' alt="Transfert de cash">
</div>

---

## 📋 L'Interface du Formulaire

Le formulaire est conçu pour être intuitif et dynamique. Lorsque vous sélectionnez un **Type de Transaction**, le formulaire s'ajuste automatiquement pour n'afficher que les champs pertinents.

- **Dettails de base :** Date, Type, Devise et Montant.
- **Spécificités de l'actif :** Si la transaction implique un actif (comme ACHAT ou VENTE), des champs pour sélectionner l'actif, saisir la quantité et définir le prix unitaire apparaîtront.
- **Panneau de prévisualisation (PMP) :** Pour les opérations affectant votre portefeuille, une prévisualisation en temps réel apparaît en bas. Elle affiche votre prix de revient actuel, le nouveau prix de revient projeté, ainsi que tout gain ou perte réalisé.

!!! note "Calculs Automatiques"

    Le système gère automatiquement les calculs standard pour vous (comme la multiplication de la quantité par le prix unitaire) afin que vous n'ayez pas à faire les calculs manuellement.

---

## 🏷️ Types de Transactions

Pour une définition conceptuelle approfondie de chaque opération, veuillez vous référer au [guide de Théorie Financière](../../financial-theory/instruments/transaction-types/index.md).

### Transactions Simples

Celles-ci opèrent indépendamment sur un seul compte de courtage.

| Type | Description | Guide Théorique |
|------|-------------|--------------|
| ![](../../static/icons/transactions/buy.png){: width="24" style="vertical-align: middle;" } **ACHAT / VENTE** ![](../../static/icons/transactions/sell.png){: width="24" style="vertical-align: middle;" } | Achat ou vente d'un actif | [📖 Lire](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/deposit.png){: width="24" style="vertical-align: middle;" } **DÉPÔT / RETRAIT** ![](../../static/icons/transactions/withdrawal.png){: width="24" style="vertical-align: middle;" } | Ajout ou retrait de liquidités d'un compte de courtage | [📖 Lire](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/dividend.png){: width="24" style="vertical-align: middle;" } **DIVIDENDE / INTÉRÊT** ![](../../static/icons/transactions/interest.png){: width="24" style="vertical-align: middle;" } | Rendement d'actifs actions ou à taux fixe | [📖 Lire](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/fee.png){: width="24" style="vertical-align: middle;" } **FRAIS / TAXE** ![](../../static/icons/transactions/tax.png){: width="24" style="vertical-align: middle;" } | Coûts tels que les frais de courtage ou les taxes | [📖 Lire](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/adjustment.png){: width="24" style="vertical-align: middle;" } **AJUSTEMENT** | Correction manuelle des soldes | [📖 Lire](../../financial-theory/instruments/transaction-types/adjustment.md) |

### Transactions Composites {: #composite-transactions }

Celles-ci représentent des mouvements **entre** des comptes ou des devises. Elles produisent deux entrées liées qui s'équilibrent.

| Type | Description | Guide Théorique |
|------|-------------|--------------|
| ![](../../static/icons/transactions/transfer.png){: width="24" style="vertical-align: middle;" } **TRANSFERT** | Actif déplacé entre deux de vos courtiers | [📖 Lire](../../financial-theory/instruments/transaction-types/transfer.md) |
| ![](../../static/icons/transactions/cash-transfer.png){: width="24" style="vertical-align: middle;" } **TRANSFERT DE LIQUIDITÉS** | Virement bancaire entre courtiers | [📖 Lire](../../financial-theory/instruments/transaction-types/cash-transfer.md) |
| ![](../../static/icons/transactions/fx-conversion.png){: width="24" style="vertical-align: middle;" } **CONVERSION FX** | Change de devises au sein d'un courtier | [📖 Lire](../../financial-theory/instruments/transaction-types/fx-conversion.md) |

Pour maintenir l'intégrité des données et permettre des analyses avancées, les transactions composites regroupent plusieurs mouvements de liquidités et d'actifs:

* **Transfert d'actif**: spécifie un **courtier source** et un **courtier de destination**, ainsi que l'actif et la quantité.
* **Conversion FX**: spécifie le **montant de la devise source** et le **montant de la devise de destination** au sein du même courtier.

Vous pouvez créer des transactions composites directement depuis le formulaire, ou par la **Promotion** de transactions simples (comme la liaison d'un dépôt et d'un retrait compatibles) depuis le tableau des transactions. Si nécessaire, une transaction composite peut être **divisée** à nouveau en transactions simples individuelles.

---

## 🔗 Liens connexes

- 📋 **[Tableau des Transactions](index.md)** — Vue en liste, filtrage, opérations groupées
- 📥 **[Importer depuis un Courtier](import/index.md)** — Évitez la saisie manuelle avec l'import BRIM
