# 💸 Transactions

Les transactions représentent chaque mouvement de votre portefeuille : achats, ventes, dividendes, frais, transferts, et entrées ou sorties de liquidités. LibreFolio calcule vos positions, votre performance et vos coûts à partir de celles-ci ; un registre complet garantit donc l'exactitude de chaque chiffre.

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="list" alt="Liste des transactions">
</div>

La page **Transactions** liste les transactions de tous les courtiers auxquels vous avez accès, les plus récentes en premier. Chaque courtier affiche également les siennes dans son propre [onglet Transactions](../brokers/import.md).

---

## 🔎 Trouver et ouvrir une transaction

- **Trier** — cliquez sur l'en-tête d'une colonne.
- **Filtrer** — ouvrez le filtre d'une colonne (date, type, actif, courtier, tags, description…). Vos filtres sont conservés dans l'adresse de la page : un signet rouvre donc la même vue.
- **Ouvrir** — double-cliquez sur une ligne pour la consulter en lecture seule ; le crayon bascule en mode édition.

Sans filtre ni tri, les deux lignes d'une paire liée (un transfert ou un change de devises) restent côte à côte, et l'icône de lien renvoie à la ligne partenaire.

---

## ➕ Ajouter ou importer des transactions

- **Ajouter une Transaction** ouvre l'[espace de travail groupé](#bulk-workspace) sur un formulaire **Nouvelle transaction** : remplissez-le ([Formulaire de transaction](form.md)), cliquez sur **Appliquer**, puis sur **Enregistrer Tout**.
- **Importer** ouvre l'espace de travail avec l'**assistant d'importation**, qui lit les fichiers exportés par votre courtier — voir [Importer depuis un courtier](import/index.md).

---

## ✏️ Modifier, cloner ou supprimer des transactions

- **Une ligne** — faites un clic droit dessus, ou utilisez ses actions de ligne : **Voir**, **Modifier**, **Cloner**, **Séparer la paire** ou **Supprimer**. Vous ne voyez que les actions que votre rôle sur ce courtier autorise.
- **Plusieurs lignes** — cochez-les, puis choisissez **Modifier**, **Cloner** ou **Supprimer** dans la barre de sélection. **Modifier** et **Supprimer** excluent les lignes des courtiers où vous n'êtes que Lecteur.

Chacune de ces actions ouvre l'espace de travail groupé, et rien ne change avant **Enregistrer Tout**. Modifier ou supprimer un côté d'une paire liée entraîne son partenaire.

**Cloner** conserve la date d'origine : c'est ainsi que vous réenregistrez une ligne historique, par exemple sous un autre type.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="clone-flow" alt="Espace de travail groupé avec une ligne de transaction clonée">
</div>

---

## 🔗 Lier ou délier une paire {: #link-pairs }

Certaines opérations sont constituées de deux transactions liées — voir [Transactions appariées](form.md#composite-transactions).

- **Lier** — cochez deux lignes simples qui vont ensemble et cliquez sur **🔗 Promote pair**. Deux **Ajustements** deviennent un **Transfert d'actif** ; un **Retrait** et un **Dépôt** deviennent un **Change de devises** (même courtier, deux devises) ou un **Virement** (deux courtiers, même devise et même montant). Si les lignes diffèrent sur la date, la description, les tags ou le coût de base, vous choisissez ce qu'il faut conserver.
- **Délier** — **Séparer la paire** sur une ligne liée la transforme à nouveau en deux lignes simples.

Les deux demandent une confirmation, puis enregistrent immédiatement, sans l'espace de travail.

---

## 🧰 L'espace de travail groupé {: #bulk-workspace }

L'espace de travail groupé est une grille de lignes en brouillon — marquées **nouveau**, **modif.** ou **suppr.** — où vous préparez vos modifications avant de les écrire :

- **Ajouter une ligne**, **Importer** et **Tout réinitialiser** se trouvent au-dessus de la grille. Cocher des lignes ajoute **Réinitialiser la sélection**, **Supprimer sélectionnées** et, pour une paire correspondante, **🔗 Promouvoir la paire**.
- Les lignes sont vérifiées au fur et à mesure : les problèmes apparaissent en haut sous *Des erreurs de validation ont été détectées*, et un clic vous amène à la ligne concernée. Avec de nombreuses lignes, la vérification automatique se met en pause — appuyez sur **⚡ Valider maintenant** avant d'enregistrer.
- Lorsque deux lignes ressemblent aux deux moitiés d'un même transfert ou échange, une bannière verte propose de les **Fusionner** — deux nouvelles lignes, deux lignes enregistrées, ou une de chaque. Lorsqu'elle propose plus d'une paire, **Tout fusionner (N)** les fusionne en une seule fois. Lorsque les deux lignes d'une paire ont une description ou des tags différents, un choix s'applique à toutes les paires : **Tout à gauche** conserve la description et les tags de la première ligne, telle que la bannière la liste ; **Tout à droite**, ceux de la seconde ligne ; **Combiner**, l'option par défaut, conserve les deux descriptions et les tags des deux lignes. Une description compte au plus 500 caractères, comme pour toute transaction : deux longues descriptions combinées peuvent les dépasser, et l'enregistrement est alors refusé.
- Lorsque l'autre moitié est déjà enregistrée mais absente de l'espace de travail groupé — un transfert dont vous avez importé le premier côté le mois dernier, par exemple — le bouton 💡, au-dessus de la grille et dans le menu de la ligne, propose de l'ajouter : une fois qu'elle est présente, la bannière propose la paire.
- **Enregistrer Tout** écrit tout en une seule fois. S'il existe des suggestions de fusion que vous n'avez pas examinées — le 💡 jamais ouvert, la bannière verte jamais cliquée — il demande d'abord confirmation (*Suggestions pas encore consultées*) : **Afficher les suggestions** ouvre la liste du 💡, ou amène la bannière à l'écran ; **Enregistrer quand même** poursuit. Une fois que vous avez regardé, il ne redemande plus jusqu'à ce que vous fermiez l'espace de travail groupé. **Annuler** ferme l'espace de travail groupé, en demandant d'abord confirmation si vous avez des modifications non enregistrées.

??? warning "🚦 Bannières après un import — quand elles apparaissent"

    Après un import, les bannières au-dessus de la grille listent ce qu'il faut vérifier avant **Enregistrer Tout** :

    - **rouge** — lignes que l'importateur n'a pas entièrement comprises : **Enregistrer Tout** reste désactivé jusqu'à ce que vous les complétiez ;
    - **orange** — champs dérivés automatiquement à vérifier : **Enregistrer Tout** vous demande d'abord de les **Vérifier** ou d'**Enregistrer quand même**.

    Cliquez sur une bannière pour dérouler sa liste, puis sur une entrée : la grille passe à la page de cette ligne et la met en surbrillance. Les problèmes de solde listent les lignes qui les causent (*Lignes de l’espace de travail : …*), et un clic ouvre la première dans l'ordre de tri actuel. Si vos filtres de colonnes masquent la ligne, un message vous en informe.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="bulk-todo-banner" alt="Espace de travail groupé avec la bannière des champs à vérifier déroulée et la ligne de l'entrée cliquée mise en surbrillance dans la grille">
</div>

Après un enregistrement, un **Promouvoir la paire** ou un **Séparer la paire**, la page Transactions efface sa sélection, car ces lignes ont pu changer ; la fermeture ou l'annulation la conserve. Si un **Promouvoir la paire** ou un **Séparer la paire** est refusé, rien ne change : un message d'erreur dit pourquoi, et la confirmation reste ouverte.

---

## 🧭 Guides contextuels

La page Transactions, le formulaire **Ajouter une Transaction**, l'espace de travail groupé et l'[assistant d'importation](import/how-to.md#guided-first-import) disposent chacun d'un court guide. Un guide ne démarre que lorsque son écran est prêt et ne modifie jamais un brouillon ni n'appuie sur un bouton à votre place ; dans l'espace de travail, il affiche une seule consigne à la fois, fermée avec **Compris**.

Vous pouvez relancer n'importe quel guide depuis [Paramètres → Préférences → Prise en main et guides](../settings/preferences.md#onboarding-and-guides).

---

## 🔗 Voir aussi

* 📝 **[Formulaire de transaction](form.md)** — champs et types de transactions
* 📥 **[Importer depuis un courtier](import/index.md)** — le flux d'import BRIM
* 📖 **[Types de transactions](../../financial-theory/instruments/transaction-types/index.md)** — la théorie financière derrière chaque type
