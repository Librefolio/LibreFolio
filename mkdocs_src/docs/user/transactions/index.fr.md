# 💸 Transactions

Les transactions correspondent à chaque mouvement de votre portefeuille : achats, ventes, dividendes, frais, transferts et entrées ou sorties de liquidités. LibreFolio calcule vos positions, votre performance et vos coûts à partir de celles-ci, si bien qu'un registre complet garantit l'exactitude de chaque chiffre.

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="list" alt="Liste des transactions">
</div>

La page **Transactions** liste les transactions de tous les courtiers auxquels vous avez accès, les plus récentes en premier. Chaque courtier affiche également les siennes dans son [onglet Transactions](../brokers/import.md).

---

## 🔎 Trouver et ouvrir une transaction

- **Trier** — cliquez sur un en-tête de colonne.
- **Filtrer** — ouvrez le filtre d'une colonne (date, type, actif, courtier, étiquettes, description…). Dans le filtre de date, saisissez une date dans **Du** uniquement pour voir les transactions à partir de ce jour, ou dans **Au** uniquement pour celles jusqu'à ce jour ; les deux bornes d'une plage doivent être des jours différents. Vos filtres sont conservés dans l'adresse de la page, si bien qu'un signet rouvre la même vue.
- **Ouvrir** — double-cliquez sur une ligne pour la voir en lecture seule ; le crayon bascule en édition.
- **Prix unitaire** — une colonne à côté du montant indique le prix par unité qu'implique une opération (le montant divisé par la quantité, selon la base de cotation de l'actif) ; elle est en lecture seule et vide pour une ligne sans quantité ni montant, ainsi que pour les deux côtés d'une paire liée. Masquez-la depuis le menu des colonnes si vous n'en avez pas besoin. L'éditeur groupé possède la même colonne.

Sans filtre ni tri, les deux lignes d'une paire liée (un transfert ou un change de devises) restent côte à côte, et l'icône de lien saute vers la ligne partenaire.

---

## ➕ Ajouter ou importer des transactions

- **Ajouter une transaction** ouvre l'[espace de travail groupé](#bulk-workspace) sur un formulaire **Nouvelle transaction** : remplissez-le ([Formulaire de transaction](form.md)), cliquez sur **Appliquer**, puis sur **Tout enregistrer**.
- **Importer** ouvre l'espace de travail groupé avec l'**Assistant d'importation**, qui lit les fichiers exportés par votre courtier — voir [Importer depuis un courtier](import/index.md).

---

## ✏️ Modifier, cloner ou supprimer des transactions

- **Une ligne** — faites un clic droit dessus, ou utilisez ses actions de ligne : **Voir**, **Modifier**, **Cloner**, **Séparer la paire** ou **Supprimer**. Vous ne voyez que les actions que votre rôle sur ce courtier autorise.
- **Plusieurs lignes** — cochez-les, puis choisissez **Modifier**, **Cloner** ou **Supprimer** dans la barre de sélection. **Modifier** et **Supprimer** excluent les lignes des courtiers où vous n'êtes que Lecteur.

Chacune de ces actions ouvre l'espace de travail groupé, et rien ne change avant **Tout enregistrer**. Modifier ou supprimer un côté d'une paire liée entraîne son partenaire.

**Cloner** conserve la date d'origine : c'est ainsi que vous réenregistrez une ligne historique, par exemple sous un autre type.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="clone-flow" alt="Espace de travail groupé avec une ligne de transaction clonée">
</div>

---

## 🔗 Lier ou délier une paire {: #link-pairs }

Certaines opérations consistent en deux transactions liées — voir [Transactions appariées](form.md#composite-transactions).

- **Lier** — cochez deux lignes simples qui vont ensemble et cliquez sur **🔗 Promouvoir en paire**. Deux **Ajustements** deviennent un **Transfert d'actif** ; un **Retrait** et un **Dépôt** deviennent un **Change de devises** (même courtier, deux devises) ou un **Virement** (deux courtiers, même devise et même montant). Si les lignes ont une description ou des étiquettes différentes, vous choisissez ce qu'il faut conserver ; chaque ligne garde sa propre date. Une description contient au maximum 500 caractères : la boîte de dialogue les compte et garde **Confirmer la promotion** désactivé jusqu'à ce que la description tienne.
- **Délier** — **Séparer la paire** sur une ligne liée la retransforme en deux lignes simples. Un **Transfert d'actif** devient deux **Ajustements** : celui qui reçoit conserve son coût, et celui qui envoie sort les unités sans valeur : chez son courtier, elles ne font que diminuer la quantité, et leur coût compte comme une moins-value réalisée (voir [Ajustements sortants](../../financial-theory/instruments/transaction-types/adjustment.md#outgoing-adjustments)).

Les deux demandent une confirmation, puis enregistrent immédiatement, sans passer par l'espace de travail groupé.

---

## 🔁 Relier les événements {: #relink-events }

Un dividende, un paiement d'intérêts ou un ajustement peut être lié à l'**événement** de l'actif (le dividende annoncé par le fournisseur, une division…). Le lien est perdu lorsque la [modification de la devise d’un actif](../assets/create-edit.md#changing-the-currency) supprime les événements vers lesquels il pointait, et un dividende que vous avez enregistré avant le téléchargement de son événement n'en a jamais eu. **Relier les événements**, dans la barre d'outils au-dessus du tableau, trouve ces transactions et propose l'événement à lier.

La fenêtre liste vos **dividendes, intérêts et ajustements** qui ont un actif et aucun événement, sur les courtiers où vous êtes au moins Éditeur, les plus récents en premier. Chaque ligne indique l'actif, la date, le type et ce qui a été trouvé :

| Ce que vous voyez | Signification | Ce que vous pouvez faire |
|--------------|---------|-----------------|
| **Un événement ce jour-là** | Exactement un événement du même actif, le même jour, du type correspondant | **Lier** la ligne |
| **Aucun événement ce jour-là** | L'actif n'a aucun événement de ce type ce jour-là | Rien ici : ajoutez l'événement, ou liez-en un autre dans la transaction |
| **N événements ce jour-là** | Plus d'un candidat | Rien ici : LibreFolio ne devine jamais. Choisissez le bon dans la transaction |

**Lier toutes les lignes avec un seul événement** lie d'un coup toutes les lignes du premier type, en un seul enregistrement : si l'une est refusée, aucune n'est liée. Rien n'est lié tant que vous ne cliquez pas.

!!! info "L'événement doit être à la même date"

    Un candidat n'est proposé que s'il est **daté du même jour** que la transaction. Il doit aussi concerner le même actif et être du type correspondant : un dividende avec un dividende, un paiement d'intérêts avec un événement d'intérêts, un ajustement avec un ajustement de prix ou une division.

    Par exemple, vous avez enregistré un dividende le **12 mars**. Un événement du même actif daté du **12 mars** est proposé. Un événement daté du **10 mars** ne l'est **pas**, même s'il est le seul à proximité : la ligne affiche *Aucun événement ce jour-là*.

    C'est ce qui se produit lorsque votre courtier a crédité le dividende quelques jours après l'événement. Ouvrez la transaction et choisissez vous-même l'événement dans **Événement lié** ([Formulaire de transaction](form.md)).

---

## 🧰 L'espace de travail groupé {: #bulk-workspace }

L'espace de travail groupé est une grille de lignes de brouillon — marquées **nouvelle**, **modifiée** ou **supprimée** — où vous préparez les modifications avant de les écrire :

- **Ajouter une ligne**, **Importer** et **Tout réinitialiser** se trouvent au-dessus de la grille. Cocher des lignes ajoute **Réinitialiser la sélection**, **Supprimer la sélection** et, pour une paire correspondante, **🔗 Promouvoir en paire**.
- Les lignes sont vérifiées au fur et à mesure : les problèmes apparaissent en haut sous *Des erreurs de validation ont été trouvées*, et un clic vous amène à la ligne. Avec beaucoup de lignes, la vérification automatique se met en pause — appuyez sur **⚡ Valider maintenant** avant d'enregistrer.
- Lorsque deux lignes ressemblent aux deux moitiés d'un même transfert ou échange, une bannière verte propose de les **Fusionner** — deux nouvelles lignes, deux lignes enregistrées, ou une de chaque. Lorsqu'elle propose plus d'une paire, **Tout fusionner (N)** les fusionne d'un coup. Quand les deux lignes d'une paire ont une description différente ou des étiquettes différentes, un seul choix s'applique à toutes les paires : **Tout à gauche** conserve la description et les étiquettes de la première ligne, telle que la bannière la liste ; **Tout à droite**, celles de la deuxième ligne ; **Combiner**, l'option par défaut, conserve les deux descriptions et les étiquettes des deux lignes. Une description contient au maximum 500 caractères, comme pour toute transaction : avec **Combiner**, une paire dont les deux descriptions réunies dépasseraient cette limite n'est pas fusionnée, et un message indique combien de paires ont été laissées de côté — fusionnez-les une par une avec **Fusionner**, où vous pouvez raccourcir la description.
- Lorsque l'autre moitié est déjà enregistrée mais absente de l'espace de travail groupé — un transfert dont vous avez importé le premier côté le mois dernier, par exemple —, le bouton 💡, au-dessus de la grille et dans le menu de la ligne, propose de l'ajouter : une fois qu'elle est là, la bannière propose la paire.
- **Tout enregistrer** écrit tout d'un coup. S'il existe des suggestions de fusion que vous n'avez pas examinées — le 💡 jamais ouvert, la bannière verte jamais cliquée —, il demande d'abord (*Suggestions que vous n'avez pas examinées*) : **Afficher les suggestions** ouvre la liste du 💡, ou amène la bannière à l'écran ; **Enregistrer quand même** poursuit. Une fois que vous les avez examinées, il ne redemande plus jusqu'à ce que vous fermiez l'espace de travail groupé. **Annuler** ferme l'espace de travail groupé, en demandant d'abord si vous avez des modifications non enregistrées.

??? warning "🚦 Bannières après un import — quand elles apparaissent"

    Après un import, des bannières au-dessus de la grille listent ce qu'il faut vérifier avant **Tout enregistrer** :

    - **rouge** — les lignes que l'importateur n'a pas entièrement comprises : **Tout enregistrer** reste désactivé jusqu'à ce que vous les complétiez ;
    - **orange** — des champs dérivés automatiquement à vérifier : **Tout enregistrer** vous demande d'abord de cliquer sur **Vérifier** ou sur **Enregistrer quand même** ;
    - **orange, dates** — les lignes datées d'avant le 1er janvier 1900, listées une par une (cliquez sur une ligne pour aller à la ligne correspondante) : **Tout enregistrer** demande une seule fois pour toutes (*Oui, les dates sont correctes*). Une date aussi ancienne est généralement une faute de frappe ; une fois confirmée, elle est enregistrée comme n'importe quelle autre.
    - **orange** — les lignes qui peuvent être des divisions d'actions (imports Revolut et Trading212) : liez un événement Division à chacune, ou créez-le depuis la bannière ; voir [Revolut](import/revolut.md#stock-splits).

    Cliquez sur une bannière pour déplier sa liste, puis sur une entrée : la grille passe à la page de cette ligne et la met en évidence. Les problèmes de solde listent les lignes qui les causent (*Lignes de l'espace de travail groupé : …*), et un clic ouvre la première dans l'ordre de tri actuel. Si vos filtres de colonnes masquent la ligne, un message vous en informe.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="bulk-todo-banner" alt="Espace de travail groupé avec la bannière des champs à vérifier dépliée et la ligne de l'entrée cliquée mise en évidence dans la grille">
</div>

Après un enregistrement, ou après une action **Promouvoir en paire** ou **Séparer la paire**, la page Transactions efface sa sélection, car ces lignes ont pu changer ; la fermeture ou l'annulation la conserve. Si une action **Promouvoir en paire** ou **Séparer la paire** est refusée, rien ne change : un message d'erreur en explique la raison, et la confirmation reste ouverte.

---

## 🧭 Guides contextuels

La page Transactions, le formulaire **Ajouter une transaction**, l'espace de travail groupé et l'[Assistant d'importation](import/how-to.md#guided-first-import) disposent chacun d'un court guide. Un guide ne démarre que lorsque son écran est prêt et ne modifie jamais un brouillon ni n'appuie sur un bouton à votre place ; dans l'espace de travail groupé, il affiche une notice à la fois, fermée par **Compris**.

Relancez n'importe quel guide depuis [Paramètres → Préférences → Prise en main et guides](../settings/preferences.md#onboarding-and-guides).

---

## 🔗 Voir aussi

* 📝 **[Formulaire de transaction](form.md)** — champs et types de transactions
* 📥 **[Importer depuis un courtier](import/index.md)** — le flux d'import BRIM
* 📖 **[Types de transactions](../../financial-theory/instruments/transaction-types/index.md)** — la théorie financière derrière chaque type
