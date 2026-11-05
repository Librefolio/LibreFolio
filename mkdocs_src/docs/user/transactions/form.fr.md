# 📝 Formulaire de transaction

Le formulaire de transaction ajoute ou modifie une transaction — ou une paire liée — dans l'[espace de travail groupé](index.md#bulk-workspace). Il affiche aussi une transaction en lecture seule lorsque vous double-cliquez dessus dans une liste. Seuls les champs dont le type choisi a besoin apparaissent.

<div class="lf-screenshot-carousel" data-carousel="transactions" data-carousel-interval="3000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> ACHAT' alt="Achat">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VENTE' alt="Vente">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-dividend" data-title='<img src="/LibreFolio/static/icons/transactions/dividend.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DIVIDENDE' alt="Dividende">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-deposit" data-title='<img src="/LibreFolio/static/icons/transactions/deposit.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DÉPÔT' alt="Dépôt">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-adjustment" data-title='<img src="/LibreFolio/static/icons/transactions/adjustment.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> AJUSTEMENT' alt="Ajustement">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRANSFERT' alt="Transfert d'actif">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-fxconversion" data-title='<img src="/LibreFolio/static/icons/transactions/fx-conversion.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> CONVERSION FX' alt="Conversion FX">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-cash-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/cash-transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VIREMENT' alt="Virement">
</div>

---

## ✍️ Remplir le formulaire

1. Choisissez le **Type**, puis le **Courtier** s'il n'est pas déjà défini.
2. Remplissez la section **Obligatoire** : la **Date**, l'**Actif** et sa quantité lorsque le type en a une, et le montant en espèces.
3. Ouvrez **Optionnel** pour les **Étiquettes**, une **Description** ou, sur les dividendes, les intérêts et les ajustements, un **Événement lié**.
4. Cliquez sur **Appliquer** pour placer la ligne dans l'espace de travail ; **Tout enregistrer** dans l'espace de travail l'écrit.

Quelques règles permettent de saisir rapidement :

- **Les montants sont des totaux** — le montant que vous enregistrez est le total payé ou reçu, jamais le prix par part (*Montant total (et non par part)*). Sur un achat ou une vente, vous pouvez saisir l'un ou l'autre : le total, ou le prix unitaire (les boutons à côté du champ indiquent lequel), et le formulaire calcule l'autre — voir [Total ou prix unitaire](#unit-price).
- **Saisissez des nombres positifs** — le formulaire ajoute le signe moins là où l'argent ou les unités sortent : le paiement d'un achat, les unités d'une vente, un retrait, des frais, un impôt. Seule la quantité d'un **Ajustement** prend un signe : positive, elle ajoute des unités ; négative, elle en retire.
- **Des vérifications au fil de la saisie** — une fois les champs obligatoires remplis, le formulaire vérifie la saisie par rapport à votre registre et aux autres lignes de l'espace de travail, et liste tout problème en haut. Le formulaire repère aussi certaines erreurs par lui-même : une date qu'il ne peut pas lire, ou une date dans le futur, reste affichée en rouge à l'écran, et la date précédente n'est pas réutilisée à sa place ; une quantité ou un montant dont le signe ou le format est incorrect, comme une quantité négative sur un achat, passe en rouge ; et un avertissement en haut signale un transfert avec le même courtier des deux côtés, ou un change de devises avec la même devise. Tant que vous ne les corrigez pas, rien n'est vérifié, *valide* n'apparaît pas et **Appliquer** reste désactivé. **⚡ Valider maintenant** les trouve toutes d'un coup — voir [Valider maintenant](#validate-now). Les dates de transaction peuvent remonter jusqu'à l'an 1 et aller jusqu'à demain, mais le formulaire lui-même s'arrête à aujourd'hui. Une date antérieure à 1900 est presque toujours une faute de frappe : le formulaire vous en avertit avec une bannière ambre et **Appliquer** reste désactivé jusqu'à ce que vous cliquiez sur **Oui, la date est correcte** ; si vous changez la date, il redemande confirmation, et une fois confirmée, la date est enregistrée comme n'importe quelle autre. Une date postérieure à demain est refusée avec un message du type *Date : ne doit pas être postérieure au 2026-10-18*, quand nous sommes le 17 octobre 2026.
- **Courtier ou actif manquant ?** — **Créer nouveau** dans la liste des courtiers, ou **Nouvel actif** dans la liste des actifs, le crée sans quitter le formulaire.
- **Événement manquant ?** — **+ Nouvel événement** dans le champ **Événement lié** crée l'événement de l'actif et le lie. Si l'actif possède déjà un événement de ce type à cette date, rien n'est enregistré : la fenêtre affiche cet événement, pour l'utiliser, ou pour le modifier si vous l'avez saisi à la main, et ne l'écrase jamais ([Nouvel événement depuis une transaction](../assets/detail/events.md#new-event)).

<div id="cost-basis"></div>

??? info "💰 Coût de base des unités entrantes — pour les Ajustements et les Transferts d'actifs"

    Lorsqu'un **Ajustement** ajoute des unités, ou du côté récepteur d'un **Transfert d'actif**, le formulaire demande combien ces unités ont coûté :

    - **Auto** — LibreFolio le calcule selon le [prix de revient unitaire (PRU)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md) ; appuyez sur **⚡ Valider maintenant** pour le voir.
    - **Manuel** — vous le saisissez.

    Un **Ajustement** qui retire des unités ne demande aucun coût : il n'a pas de valeur. Les unités quittent seulement la quantité, et leur coût est comptabilisé comme une moins-value réalisée. Pour enregistrer une vente, utilisez une **Vente**.

    En **Auto**, la moyenne est calculée chez le courtier d'envoi d'un transfert, ou chez le courtier de l'ajustement lui-même. Si ce courtier ne détient aucune unité de cet actif le jour où les unités quittent ce courtier ou y entrent, ou s'il ne détient que des unités dont le coût est inconnu, il n'y a rien à moyenner : **Auto** est refusé et rien n'est enregistré — choisissez **Manuel** et saisissez ce que ces unités vous ont coûté (0 pour un don). En **Manuel**, le champ ne peut pas rester vide : LibreFolio signale la ligne et n'enregistre rien tant que vous ne l'avez pas rempli et que vous n'êtes pas passé en **Auto** ; un coût négatif est refusé de la même manière — saisissez 0 ou plus. La modification d'une transaction enregistrée ne fait pas exception : si vous videz son coût en **Manuel**, l'enregistrement est refusé, car la transaction a besoin d'un coût de base — choisissez **Auto** ou saisissez une valeur. Saisissez 0 pour les nouvelles actions d'une division d'actions. Pour un don, au lieu de 0, vous pouvez saisir ce que le donateur a payé pour ces unités : cela maintient le prix de revient unitaire (PRU), ainsi que la plus-value sur laquelle vous pourriez être imposé, plus proches des valeurs réelles. Les unités saisies avec un coût de 0 comptent comme gratuites, et non comme inconnues : une moyenne **Auto** ultérieure chez leur courtier les compte à 0. Si un taux de change manque, le lien **Synchroniser les taux de change** le récupère.

---

## 🧮 Total ou prix unitaire {: #unit-price }

Sur un **Achat** ou une **Vente** (et sur tout autre type simple comportant à la fois une quantité et un montant en espèces), le libellé du champ de montant comporte deux petits boutons, **Total** et **Prix unitaire**. Le formulaire reste un montant unique et sa devise : les boutons indiquent seulement **comment lire le nombre que vous avez saisi** dans ce champ.

- **Total** (par défaut) — le nombre est le montant payé ou reçu. Sous le champ, le formulaire affiche le prix unitaire qu'il calcule : *= 83,40 par unité*.
- **Prix unitaire** — le nombre est le prix d'une unité. Sous le champ, le formulaire affiche le total qu'il calcule : *= 1 000,80 au total*.

Changer de bouton conserve le nombre que vous avez écrit et le lit dans l'autre sens. Ce qui est enregistré est toujours le **total** : avec **Prix unitaire** activé, le total affiché sous le champ est celui qui entre dans la transaction. Lorsque vous ouvrez une transaction enregistrée, le champ affiche le total, avec les boutons sur **Total**.

Le calcul est fait par le formulaire lui-même, immédiatement, sur les chiffres exacts que vous avez saisis (aucune erreur d'arrondi due aux nombres à virgule flottante). Il utilise la même convention de prix que le reste de l'application : la quantité est divisée par le *prix pour N unités* de l'actif puis multipliée par le prix, si bien qu'une obligation cotée pour 100 fonctionne comme se lit sa cotation (*= 98,55 pour 100 unités*). Le résultat est arrondi à ce qui est stocké : les montants gardent 6 décimales et les prix unitaires 12. Les cas d'égalité sont arrondis au chiffre pair (*half-even*). Une valeur trop longue est signalée en rouge, comme d'habitude. Le prix unitaire est dans la même devise que le montant. L'actif et la quantité doivent être renseignés ; sans eux, rien n'est calculé et le champ affiche son indication habituelle (ce qu'il faut saisir).

!!! example "Exemple"

    Vous avez acheté 12 actions à 83,40. Appuyez sur **Prix unitaire**, saisissez *83,40* dans le champ de montant, et sous celui-ci vous lisez *= 1 000,80 au total*. Votre courtier vous a en fait facturé 1 000,90 : appuyez sur **Total**, saisissez *1 000,90*, et sous le champ vous lisez *= 83,408333333333 par unité*. Le montant enregistré est *1 000,90*.

Lorsque vous ouvrez une transaction enregistrée juste pour la consulter, vous voyez le total et, en dessous, le prix unitaire calculé à partir du total et de la quantité. Les boutons n'apparaissent que lorsque vous pouvez modifier.

Les types sans quantité ou sans montant, les transferts et les changes n'ont pas de boutons. La grille de l'[éditeur groupé](index.md#bulk-workspace) ne les a pas encore.

---

## ⚡ Valider maintenant {: #validate-now }

**⚡ Valider maintenant** est toujours cliquable, même sur un formulaire que vous venez d'ouvrir. Appuyez dessus chaque fois que vous voulez savoir ce qui manque encore ou ce qui ne va pas. Il fonctionne de la même manière pour une transaction simple, une paire de transfert et un change de devises.

Quand vous appuyez dessus, il examine le formulaire en deux étapes, avant que quoi que ce soit ne quitte votre ordinateur :

1. **Champs obligatoires** — la date, le courtier, l'actif et sa quantité lorsque le type en a une, et le montant en espèces. Pour une paire, il vérifie aussi l'autre côté : le courtier récepteur et la seconde date, et, pour un change de devises, les deux montants et les deux devises.
2. **Ce que vous avez saisi** — une date illisible, une quantité ou un montant qui n'est pas un nombre valide ou qui comporte trop de chiffres, un signe incorrect, ou la même devise ou le même courtier des deux côtés.

Chaque cellule erronée passe en rouge immédiatement :

- une valeur obligatoire **manquante** reçoit un contour rouge ;
- une valeur **mal écrite** est en rouge sur le champ lui-même.

Le focus saute sur la première cellule erronée, en partant du haut, et un petit compteur à côté du bouton indique combien de champs doivent être corrigés. Tant que quelque chose ne va pas, rien n'est envoyé au serveur. Chaque marque disparaît dès que vous corrigez son champ.

Lorsque tous les champs sont corrects, le bouton interroge le serveur, comme il l'a toujours fait, et affiche *valide* ou les problèmes que le serveur trouve dans votre registre et dans les autres lignes de l'espace de travail.

!!! example "Exemple"

    Vous laissez la quantité vide et saisissez *abc* comme date. Appuyez sur **⚡ Valider maintenant** : les deux cellules passent en rouge, le focus se place sur la date, le compteur affiche *2 champs à corriger*, et rien n'est envoyé. Corrigez la date et sa marque disparaît ; remplissez la quantité et le compteur s'efface, et l'appui suivant interroge le serveur.

---

## 🏷️ Types de transactions

Le [guide de théorie financière](../../financial-theory/instruments/transaction-types/index.md) explique chaque type en détail.

### 🧾 Transactions simples

| Type | Ce qu'il enregistre | Théorie |
|------|-----------------|--------|
| ![](../../static/icons/transactions/buy.png){: width="24" style="vertical-align: middle;" } **Achat** | Unités d'un actif achetées, et le total payé | [📖 Lire](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/sell.png){: width="24" style="vertical-align: middle;" } **Vente** | Unités d'un actif vendues, et le total reçu | [📖 Lire](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/dividend.png){: width="24" style="vertical-align: middle;" } **Dividende** | Espèces versées par un actif que vous détenez | [📖 Lire](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/interest.png){: width="24" style="vertical-align: middle;" } **Intérêt** | Intérêts reçus, avec ou sans actif | [📖 Lire](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/deposit.png){: width="24" style="vertical-align: middle;" } **Dépôt** | Espèces que vous versez chez le courtier | [📖 Lire](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/withdrawal.png){: width="24" style="vertical-align: middle;" } **Retrait** | Espèces que vous retirez du courtier | [📖 Lire](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/fee.png){: width="24" style="vertical-align: middle;" } **Frais** | Des frais ou un autre coût, éventuellement liés à un actif | [📖 Lire](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/tax.png){: width="24" style="vertical-align: middle;" } **Impôt** | Un impôt payé, éventuellement lié à un actif | [📖 Lire](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/adjustment.png){: width="24" style="vertical-align: middle;" } **Ajustement** | Unités ajoutées ou retirées sans espèces : une division, un don, une position ouverte ailleurs | [📖 Lire](../../financial-theory/instruments/transaction-types/adjustment.md) |

### 🔗 Transactions liées {: #composite-transactions }

Une opération liée est enregistrée sous la forme de deux transactions liées, que le formulaire affiche comme une seule, avec un côté **De** et un côté **Vers**. Chaque côté a sa propre date, et la flèche **Inverser les côtés** inverse le sens. Dans un change de devises, les deux dates coïncident généralement : elles diffèrent lorsque le courtier crédite la nouvelle devise un autre jour.

| Type | Ce qu'il enregistre | Théorie |
|------|-----------------|--------|
| ![](../../static/icons/transactions/transfer.png){: width="24" style="vertical-align: middle;" } **Transfert d'actif** | Unités d'un actif déplacées entre deux de vos courtiers | [📖 Lire](../../financial-theory/instruments/transaction-types/transfer.md) |
| ![](../../static/icons/transactions/cash-transfer.png){: width="24" style="vertical-align: middle;" } **Virement** | Espèces déplacées entre deux de vos courtiers, dans une seule devise | [📖 Lire](../../financial-theory/instruments/transaction-types/cash-transfer.md) |
| ![](../../static/icons/transactions/fx-conversion.png){: width="24" style="vertical-align: middle;" } **Change de devises** | Une devise convertie en une autre, au sein d'un même courtier | [📖 Lire](../../financial-theory/instruments/transaction-types/fx-conversion.md) |

Un transfert exige deux courtiers différents ; un change de devises exige deux devises différentes. Deux lignes simples peuvent aussi être liées en une paire plus tard, et une paire peut être dissociée — voir [Lier ou dissocier une paire](index.md#link-pairs).

---

## 🔗 Voir aussi

- 📋 **[Transactions](index.md)** — la liste, les filtres et l'espace de travail groupé
- 📥 **[Importer depuis le courtier](import/index.md)** — évitez la saisie manuelle grâce à un import BRIM
