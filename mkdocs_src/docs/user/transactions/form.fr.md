# 📝 Formulaire de transaction

Le formulaire de transaction ajoute ou modifie une transaction — ou une paire liée — dans l'[espace de travail groupé](index.md#bulk-workspace). Il affiche également une transaction en lecture seule lorsque vous double-cliquez dessus dans une liste. Seuls les champs nécessaires au type choisi apparaissent.

<div class="lf-screenshot-carousel" data-carousel="transactions" data-carousel-interval="3000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> ACHAT' alt="Achat">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VENTE' alt="Vente">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-dividend" data-title='<img src="/LibreFolio/static/icons/transactions/dividend.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DIVIDENDE' alt="Dividende">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-deposit" data-title='<img src="/LibreFolio/static/icons/transactions/deposit.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DÉPÔT' alt="Dépôt">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-adjustment" data-title='<img src="/LibreFolio/static/icons/transactions/adjustment.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> AJUSTEMENT' alt="Ajustement">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRANSFERT D&#39;ACTIF' alt="Transfert d'actif">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-fxconversion" data-title='<img src="/LibreFolio/static/icons/transactions/fx-conversion.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> CONVERSION FX' alt="Conversion FX">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-cash-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/cash-transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VIREMENT' alt="Virement">
</div>

---

## ✍️ Remplir le formulaire

1. Choisissez le **Type**, puis le **Courtier** si ce n'est pas déjà défini.
2. Remplissez la section **Obligatoire** : la **Date**, l'**Actif** et sa quantité lorsque le type en comporte une, ainsi que le montant en espèces.
3. Ouvrez la section **Facultatif** pour les **Étiquettes**, une **Description** ou, sur les dividendes, intérêts et ajustements, un **Événement lié**.
4. Cliquez sur **Appliquer** pour placer la ligne dans l'espace de travail ; **Tout enregistrer** dans l'espace de travail l'enregistre.

Quelques règles permettent de saisir rapidement :

- **Les montants sont des totaux** — saisissez le total payé ou reçu, et non le prix par action (*Montant total (pas par action)*).
- **Saisissez des nombres positifs** — le formulaire ajoute le signe moins là où l'argent ou les unités sortent : le paiement d'un achat, les unités d'une vente, un retrait, des frais, un impôt. Seule une quantité d'**Ajustement** prend un signe : positif ajoute des unités, négatif les retire.
- **Vérifications au fur et à mesure** — une fois les champs obligatoires remplis, le formulaire vérifie la saisie par rapport à votre registre et aux autres lignes de l'espace de travail, et liste tout problème en haut. **⚡ Valider maintenant** vérifie immédiatement.
- **Courtier ou actif manquant ?** — **Créer nouveau** dans la liste des courtiers, ou **Nouvel actif** dans la liste des actifs, le crée sans quitter le formulaire.

??? info "💰 Coût de base des unités entrantes — pour les Ajustements et les Transferts d'actif"

    Lorsqu'un **Ajustement** ajoute des unités, ou du côté récepteur d'un **Transfert d'actif**, le formulaire demande combien ces unités ont coûté :

    - **Auto** — LibreFolio le calcule comme un [prix de revient unitaire (PRU)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md) ; appuyez sur **⚡ Valider maintenant** pour le voir.
    - **Manuel** — vous le saisissez.

    En **Auto**, la moyenne est prise chez le courtier émetteur d'un transfert, ou chez le courtier propre à l'ajustement. Si ce courtier n'a aucune autre transaction sur l'actif jusqu'à la date d'arrivée des unités, il n'y a rien à moyenner, et le coût est de 0 par conception : si ces unités ont bien eu un coût, ouvrez la transaction plus tard et saisissez leur coût en **Manuel**. En **Manuel**, le champ ne peut pas rester vide : LibreFolio signale la ligne et n'enregistre rien tant que vous ne le remplissez pas ou ne passez pas en **Auto**. Pour des unités qui ne coûtent rien, comme un don, saisissez 0. Si un taux de change est manquant, le lien **Synchroniser les taux de change** le récupère.

---

## 🏷️ Types de transactions

Le [guide de théorie financière](../../financial-theory/instruments/transaction-types/index.md) explique chaque type en profondeur.

### 🧾 Transactions simples

| Type | Ce qu'il enregistre | Théorie |
|------|-----------------|--------|
| ![](../../static/icons/transactions/buy.png){: width="24" style="vertical-align: middle;" } **Achat** | Unités d'un actif achetées, et le total payé | [📖 Lire](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/sell.png){: width="24" style="vertical-align: middle;" } **Vente** | Unités d'un actif vendues, et le total reçu | [📖 Lire](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/dividend.png){: width="24" style="vertical-align: middle;" } **Dividende** | Espèces versées par un actif que vous détenez | [📖 Lire](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/interest.png){: width="24" style="vertical-align: middle;" } **Intérêt** | Intérêts reçus, avec ou sans actif | [📖 Lire](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/deposit.png){: width="24" style="vertical-align: middle;" } **Dépôt** | Espèces que vous déposez chez le courtier | [📖 Lire](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/withdrawal.png){: width="24" style="vertical-align: middle;" } **Retrait** | Espèces que vous retirez du courtier | [📖 Lire](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/fee.png){: width="24" style="vertical-align: middle;" } **Frais** | Une commission ou un autre coût, éventuellement lié à un actif | [📖 Lire](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/tax.png){: width="24" style="vertical-align: middle;" } **Impôt** | Un impôt payé, éventuellement lié à un actif | [📖 Lire](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/adjustment.png){: width="24" style="vertical-align: middle;" } **Ajustement** | Unités ajoutées ou retirées sans espèces : une division, un don, une position ouverte ailleurs | [📖 Lire](../../financial-theory/instruments/transaction-types/adjustment.md) |

### 🔗 Transactions appariées {: #composite-transactions }

Une opération appariée est enregistrée comme deux transactions liées, que le formulaire affiche comme une seule, avec un côté **Depuis** et un côté **Vers**. Chaque côté a sa propre date, et la flèche **Inverser les côtés** inverse le sens.

| Type | Ce qu'il enregistre | Théorie |
|------|-----------------|--------|
| ![](../../static/icons/transactions/transfer.png){: width="24" style="vertical-align: middle;" } **Transfert d'actif** | Unités d'un actif déplacées entre deux de vos courtiers | [📖 Lire](../../financial-theory/instruments/transaction-types/transfer.md) |
| ![](../../static/icons/transactions/cash-transfer.png){: width="24" style="vertical-align: middle;" } **Virement** | Espèces déplacées entre deux de vos courtiers, dans une même devise | [📖 Lire](../../financial-theory/instruments/transaction-types/cash-transfer.md) |
| ![](../../static/icons/transactions/fx-conversion.png){: width="24" style="vertical-align: middle;" } **Change de devises** | Une devise convertie en une autre, au sein d'un même courtier | [📖 Lire](../../financial-theory/instruments/transaction-types/fx-conversion.md) |

Un transfert nécessite deux courtiers différents ; une opération de change de devises nécessite deux devises différentes. Deux lignes simples peuvent aussi être liées en une paire plus tard, et une paire scindée à nouveau — voir [Lier ou délier une paire](index.md#link-pairs).

---

## 🔗 Voir aussi

- 📋 **[Transactions](index.md)** — la liste, les filtres et l'espace de travail groupé
- 📥 **[Importer depuis un courtier](import/index.md)** — évitez la saisie manuelle avec un import BRIM
