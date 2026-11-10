# ✏️ Éditeur de données

L'Éditeur de données vous permet de corriger et de compléter à la main les données d'un actif : ses prix quotidiens et ses événements, comme les dividendes. Utilisez-le pour corriger un prix erroné fourni par un fournisseur, ajouter l'historique d'un actif qui n'en a pas, combler une lacune ou enregistrer un événement que le fournisseur a manqué.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-editor" alt="Éditeur de données d'actif" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Modifier les prix et les événements

1. En mode **Prix**, cliquez sur **✏️ Modifier les prix et les événements** en haut à droite du graphique. L'éditeur s'ouvre sous le graphique, avec un onglet **Prix** et un onglet **Événements**.
2. Modifiez ce dont vous avez besoin :
    - **Ajouter une ligne** ajoute une ligne sur une date libre : modifiez la date si nécessaire, puis renseignez les valeurs.
    - Cliquez sur une cellule pour la modifier.
    - **Supprimer**, dans le menu **⋮** d'une ligne, marque la ligne pour suppression, et **Défaire** la fait revenir. Cochez plusieurs lignes pour les supprimer ensemble.
    - **Importer CSV** charge de nombreuses lignes d'un coup ([ci-dessous](#import-from-csv)).
3. Cliquez sur **Enregistrer (n)**, où *n* compte vos modifications, ou sur **Annuler** pour les abandonner. Les deux ferment l'éditeur et font revenir les autres panneaux ; c'est aussi le cas de ✕, sans enregistrer.

Tant que vous n'avez pas enregistré, les prix nouveaux et modifiés apparaissent sur le graphique sous forme de ligne violette. Un prix enregistré en dehors des dates affichées élargit celles-ci pour l'inclure.

---

## 💰 Onglet Prix

- **Clôture** est obligatoire et doit être supérieure à 0 ; **Ouverture**, **Plus haut**, **Plus bas** et **Volume** sont facultatifs, 0 ou plus, et la gomme dans une cellule efface sa valeur. LibreFolio ne conserve aucun prix négatif : une ligne qui en contient un, ce que seul un fichier importé peut apporter, n'est pas enregistrée et compte comme ignorée.
- Les prix sont dans la devise de l'actif, indiquée à côté des onglets (*Prix en USD*).
- Les **lignes obsolètes** sont des jours sans prix spécifique, remplis avec le dernier prix connu. Lorsqu'il y en a, un compteur ⚠️ et un interrupteur apparaissent : activez-le pour les masquer.
- **Tout prix refusé par le serveur est nommé.** S'il refuse certains de vos prix, par exemple une clôture supérieure au **Plus haut** de la ligne ou inférieure à son **Plus bas**, il enregistre les autres. Un avertissement nomme alors jusqu'à cinq dates refusées, chacune avec sa raison, et compte les autres ; il reste affiché 20 secondes, afin que vous puissiez les noter et les saisir à nouveau. S'il refuse l'enregistrement entier, par exemple parce qu'une date est postérieure à demain, rien n'est enregistré : le message en explique la raison, et l'éditeur reste ouvert avec vos modifications.

---

## 📅 Onglet Événements

Chaque ligne possède un **Type** (Dividende, Intérêt, Division, Ajustement de prix ou Échéance), un **Montant** dans la devise de l'actif (par action pour un dividende, le ratio pour une division) et des **Notes** facultatives. Voir [Événements d'actif](events.md) pour ce que fait chaque type.

- **Les événements provenant d'un fournisseur sont en lecture seule** : une modification serait écrasée lors de sa prochaine synchronisation. Vous pouvez en supprimer un, mais le fournisseur l'ajoute de nouveau lors de sa prochaine synchronisation ; pour le supprimer définitivement, modifiez les paramètres du fournisseur de l'actif.
- **Modifier l'un de vos événements modifie cet événement**, son **Type** compris : aucun second événement n'est ajouté. Une transaction qui y est liée reste liée et est lue selon le nouveau type : un **Ajustement** lié à une division, par exemple, ne compte plus comme une division une fois que l'événement est un Ajustement de prix.
- **Les modifications de vos événements sont enregistrées toutes ensemble, ou pas du tout.** Suppressions, modifications et nouvelles lignes sont traitées en une seule étape, les suppressions en premier. Si quoi que ce soit est refusé, aucune modification d'événement n'est stockée, suppressions comprises : *Échec de l'enregistrement : …* vous en indique la raison, dans votre langue, et vos modifications restent dans l'éditeur pour que vous les corrigiez. Les modifications de prix du même enregistrement sont tout de même stockées, car les prix sont enregistrés en premier.

Un enregistrement est refusé, avec un message qui nomme l'événement en cause, lorsque :

- **un événement est dans une autre devise que celle de l'actif** : cela vient d'une ligne CSV, qui conserve la devise dans laquelle elle a été écrite ([ci-dessous](#import-from-csv)) ;
- **le nouveau Type d'un événement est celui qu'un autre de vos événements possède à cette date** : échanger les types de deux événements dans un même enregistrement fonctionne, tout comme supprimer cet autre événement dans le même enregistrement ;
- **vous supprimez un événement auquel une transaction est liée** : le message nomme l'événement et le nombre de transactions qui l'utilisent. Supprimez d'abord ce lien dans ces transactions. Avant LibreFolio 1.3, le reste de l'enregistrement était appliqué et cette suppression était ignorée avec un avertissement ;
- **vous modifiez le Type d'une division dont les ajustements liés n'ont pas de coût d'achat** : sans la division, ces unités compteraient comme achetées à un prix inconnu. Le message compte ces ajustements, y compris ceux chez un courtier que vous ne pouvez pas voir ; donnez-leur d'abord un coût d'achat, puis modifiez le Type ;
- **un Type n'est pas l'un des cinq** : cela vient aussi d'une ligne CSV.

---

## 📥 Importer depuis un CSV {: #import-from-csv }

**Importer CSV** ouvre une fenêtre où vous déposez un fichier ou collez son texte, et chaque ligne est vérifiée avant l'importation. La première ligne doit nommer les colonnes, dans n'importe quel ordre.

=== "Prix"

    ```text
    date;currency;close;open;high;low;volume
    2024-01-15;USD;145.50;144.00;146.20;143.80;1500000
    2024-01-16;USD;146.10;;;;
    ```

    `date`, `currency` et `close` sont obligatoires : indiquez la devise de l'actif.

=== "Événements"

    ```text
    date;currency;type;amount;notes
    2024-03-15;USD;DIVIDEND;1.25;Q1 payout
    2024-06-01;;SPLIT;2;2:1 split
    ```

    `date`, `type` et `amount` sont obligatoires. `type` doit être l'un des suivants : `DIVIDEND`, `INTEREST`, `SPLIT`, `PRICE_ADJUSTMENT` et `MATURITY_SETTLEMENT`. Toute autre valeur est refusée lors de l'enregistrement.

    `value` est accepté à la place de `amount`, afin qu'un fichier d'événements exporté par LibreFolio (la sauvegarde proposée lorsque vous [changez la devise d'un actif](../create-edit.md#editing-an-asset)) puisse être réimporté, ses autres colonnes étant ignorées. Attention à deux limites :

    - **Un événement par date et par type** : les lignes partageant à la fois une date et un type sont toutes écartées comme doublons ; un dividende et une division le même jour s'importent ensemble.
    - **Lignes marquées `PROVIDER`** : lorsque l'actif a un fournisseur, elles sont écartées et l'éditeur vous indique combien ; synchronisez l'actif pour les charger. Lorsque l'actif n'a pas de fournisseur, elles sont ajoutées comme vos propres événements.

    Dans ce fichier, une note qui commence par `=`, `+`, `-` ou `@` est précédée d'une apostrophe, afin qu'un tableur l'affiche comme du texte au lieu de l'interpréter comme une formule : l'importation retire cette apostrophe, et la note revient telle qu'elle était.

- Les dates sont au format `YYYY-MM-DD`, et les décimales peuvent utiliser `.` ou `,`.
- Les colonnes sont séparées par `;` ou `,` ; avec `,`, écrivez les décimales avec `.`.
- Les autres colonnes sont ignorées, si bien qu'un fichier de prix exporté par LibreFolio s'importe tel quel.
- La colonne `currency` n'est jamais convertie. Sur une ligne de prix, elle n'est pas vérifiée non plus : le prix est stocké tel quel dans la devise de l'actif. Une ligne d'événement conserve sa devise, et une ligne dans une autre devise que celle de l'actif est refusée lors de l'enregistrement ; une devise vide prend celle de l'actif. Ainsi, avant d'importer une sauvegarde prise avant un changement de devise, convertissez ses montants et écrivez la nouvelle devise de l'actif.
- Une ligne de prix met à jour le prix de sa date ; une ligne d'événement met à jour votre événement de même date et de même type. Une ligne qui ne correspond qu'à un événement d'un fournisseur est écartée, car une importation ne modifie jamais ceux-ci ; les autres sont ajoutées. Rien n'est stocké avant que vous cliquiez sur **Enregistrer**.

---

## 🖱️ Sauter depuis le graphique

Avec l'éditeur ouvert, double-cliquez sur un point du graphique (ou appuyez longuement dessus sur un téléphone) pour accéder à cette date : vous arrivez sur l'onglet **Événements** lorsque la date a un événement, sur **Prix** sinon.

---

## 🔗 Voir aussi

- 📈 **[Graphique interactif](chart.md)** — Visualisation du graphique avec marqueurs d'événements
- 📅 **[Événements d'actif](events.md)** — Types d'événements et leurs sources
- 📚 **[Événements d'actif (théorie financière)](../../../financial-theory/instruments/asset-events/index.md)** — Analyse détaillée de l'impact pour chaque type d'événement
- 🔌 **[Fournisseurs](../providers/index.md)** — Récupération automatique des prix
- 🛠️ **[Composants de l'éditeur de points de données](../../../developer/frontend/components/core-ui/data-editor.md)** — Pour les développeurs : comment l'éditeur vérifie, fusionne et enregistre les lignes
