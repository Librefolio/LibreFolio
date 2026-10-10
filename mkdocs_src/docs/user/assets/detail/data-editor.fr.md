# ✏️ Éditeur de données

L'éditeur de données vous permet de corriger et de compléter manuellement les données d'un actif : ses cours quotidiens et ses événements, tels que les dividendes. Utilisez-le pour corriger un cours erroné provenant d'un fournisseur, ajouter l'historique d'un actif qui n'en possède pas, combler une lacune ou enregistrer un événement manqué par le fournisseur.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-editor" alt="Éditeur de données de l'actif" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Modifier les cours et les événements

1. En mode **Cours**, cliquez sur **✏️ Modifier les cours et événements** en haut à droite du graphique. L'éditeur s'ouvre sous le graphique, avec un onglet **Cours** et un onglet **Événements**.
2. Modifiez ce dont vous avez besoin :
    - **Ajouter une ligne** ajoute une ligne à une date libre : modifiez la date si nécessaire, puis saisissez les valeurs.
    - Cliquez sur une cellule pour la modifier.
    - **Supprimer**, dans le menu **⋮** d'une ligne, marque la ligne pour suppression, et **Rétablir** la remet. Cochez plusieurs lignes pour les supprimer ensemble.
    - **Importer CSV** charge plusieurs lignes à la fois ([ci-dessous](#import-from-csv)).
3. Cliquez sur **Enregistrer (n)**, où *n* compte vos modifications, ou sur **Annuler** pour les abandonner. Les deux ferment l'éditeur et font réapparaître les autres panneaux ; c'est également le cas de ✕, sans enregistrer.

Tant que vous n'enregistrez pas, les cours nouveaux et modifiés apparaissent sur le graphique sous forme de ligne violette. Un cours enregistré en dehors des dates affichées élargit celles-ci pour l'inclure.

---

## 💰 Onglet Cours

- La **Clôture** est obligatoire et doit être un nombre positif ; **Ouverture**, **Plus haut**, **Plus bas** et **Volume** sont facultatifs, et la gomme dans une cellule efface sa valeur.
- Les cours sont dans la devise de l'actif, indiquée à côté des onglets (*Cours en USD*).
- Les **lignes obsolètes** sont des jours sans cours propre, comblés avec le dernier cours connu. Lorsqu'il y en a, un compteur ⚠️ et un interrupteur apparaissent : activez-le pour les masquer.

---

## 📅 Onglet Événements

Chaque ligne possède un **Type** (Dividende, Intérêt, Division, Ajustement de prix ou Échéance), un **Montant** dans la devise de l'actif (par action pour un dividende, le ratio pour une division) et des **Notes** facultatives. Consultez [Événements d'actif](events.md) pour connaître le rôle de chaque type.

- **Les événements provenant d'un fournisseur sont en lecture seule** : une modification serait écrasée lors de sa prochaine synchronisation. Vous pouvez en supprimer un, mais le fournisseur le rajoute lors de sa prochaine synchronisation ; pour le supprimer définitivement, modifiez les paramètres du fournisseur de l'actif.
- **Modifier l'un de vos événements modifie cet événement**, y compris son **Type** : aucun second événement n'est ajouté. Une transaction qui y est liée reste liée et est lue selon le nouveau type : un **Ajustement** lié à une division, par exemple, ne compte plus comme une division une fois que l'événement est un Ajustement de prix.
- **Changer le Type d'un événement pour celui qu'un autre de vos événements possède à cette date** est refusé à l'enregistrement ; échanger les types de deux événements en un seul enregistrement fonctionne. Si vous supprimez cet autre événement, enregistrez d'abord la suppression. Un enregistrement refusé conserve vos modifications dans l'éditeur pour que vous puissiez les corriger, tandis que les modifications de cours du même enregistrement sont déjà stockées.
- **Un événement auquel une transaction est liée** ne peut pas être supprimé : l'enregistrement vous en avertit à la place.

---

## 📥 Importer depuis un CSV {: #import-from-csv }

**Importer CSV** ouvre une fenêtre où vous déposez un fichier ou collez son texte, et chaque ligne est vérifiée avant l'importation. La première ligne doit nommer les colonnes, dans n'importe quel ordre.

=== "Cours"

    ```text
    date;currency;close;open;high;low;volume
    2024-01-15;USD;145.50;144.00;146.20;143.80;1500000
    2024-01-16;USD;146.10;;;;
    ```

    `date`, `currency` et `close` sont obligatoires : écrivez la devise de l'actif.

=== "Événements"

    ```text
    date;currency;type;amount;notes
    2024-03-15;USD;DIVIDEND;1.25;Q1 payout
    2024-06-01;;SPLIT;2;2:1 split
    ```

    `date`, `type` et `amount` sont obligatoires. `type` est l'un de `DIVIDEND`, `INTEREST`, `SPLIT`, `PRICE_ADJUSTMENT` et `MATURITY_SETTLEMENT`.

    `value` est accepté à la place de `amount`, de sorte qu'un fichier d'événements exporté par LibreFolio (la sauvegarde proposée lorsque vous [modifiez la devise d'un actif](../create-edit.md#editing-an-asset)) puisse être réimporté, ses autres colonnes étant ignorées. Attention à deux limites :

    - **Un événement par date** : les lignes partageant une même date sont toutes écartées comme doublons, donc importez de tels événements depuis des fichiers séparés.
    - **Chaque ligne devient votre propre événement**, y compris celles d'un fournisseur : omettez les lignes dont la colonne `source` vaut `PROVIDER` si le fournisseur les enverra à nouveau, sinon elles apparaîtront deux fois.

- Les dates sont au format `YYYY-MM-DD`, et les décimales peuvent utiliser `.` ou `,`.
- Les colonnes sont séparées par `;` ou `,` ; avec `,`, écrivez les décimales avec `.`.
- Les autres colonnes sont ignorées, de sorte qu'un fichier de cours exporté par LibreFolio s'importe tel quel.
- La colonne `currency` n'est ni vérifiée ni convertie : les montants sont stockés dans la devise de l'actif tels quels, donc convertissez d'abord ceux d'une sauvegarde effectuée avant un changement de devise.
- Une ligne de cours met à jour le cours de sa date ; une ligne d'événement met à jour votre événement ayant la même date et le même type. Une ligne qui ne correspond qu'à l'événement d'un fournisseur est écartée, car une importation ne modifie jamais ceux-ci ; les autres sont ajoutées. Rien n'est stocké tant que vous n'avez pas cliqué sur **Enregistrer**.

---

## 🖱️ Aller à une date depuis le graphique

Avec l'éditeur ouvert, double-cliquez sur un point du graphique (ou appuyez longuement dessus sur un téléphone) pour accéder à cette date : à l'onglet **Événements** lorsque la date comporte un événement, à **Cours** sinon.

---

## 🔗 Liens connexes

- 📈 **[Graphique interactif](chart.md)** — Visualisation graphique avec marqueurs d'événements
- 📅 **[Événements d'actif](events.md)** — Types d'événements et leurs sources
- 📚 **[Événements d'actif (théorie financière)](../../../financial-theory/instruments/asset-events/index.md)** — Analyse détaillée de l'impact pour chaque type d'événement
- 🔌 **[Fournisseurs](../providers/index.md)** — Récupération automatique des cours
- 🛠️ **[Composants de l'éditeur de points de données](../../../developer/frontend/components/core-ui/data-editor.md)** — Pour les développeurs : comment l'éditeur vérifie, fusionne et enregistre les lignes
