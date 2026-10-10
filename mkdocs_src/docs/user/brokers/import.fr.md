# 📥 Transactions du courtier

L'onglet **Transactions** d'un courtier liste toutes ses transactions, de la plus récente à la plus ancienne. Il affiche toujours tout l'historique du courtier : la plage de dates dans la barre d'outils ne le filtre pas.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="transactions-tab" alt="Onglet Transactions du courtier">
</div>

Au-dessus de la liste, vous trouvez **Rapports téléversés**, **Voir dans Transactions** et le sélecteur de colonnes. Les Propriétaires et les Éditeurs ont également accès à **Importer** et **Ajouter une transaction**.

---

## ➕ Ajouter une transaction

1. Cliquez sur **Ajouter une transaction**. L'espace de travail des transactions s'ouvre sur un formulaire **Nouvelle transaction**, avec ce courtier déjà sélectionné.
2. Choisissez le **Type** et remplissez les champs obligatoires — voir [Formulaire de transaction](../transactions/form.md).
3. Cliquez sur **Appliquer** pour placer la ligne dans l'espace de travail, puis sur **Tout enregistrer** pour l'enregistrer.

Rien n'est enregistré avant **Tout enregistrer** : jusque-là, vous pouvez ajouter d'autres lignes, les modifier ou annuler (voir [L'espace de travail groupé](../transactions/index.md#bulk-workspace)).

---

## 🔎 Ouvrir, modifier ou supprimer des transactions

- **Double-cliquez** sur une ligne pour l'ouvrir en lecture seule.
- Pour modifier, cloner ou supprimer des lignes, cliquez sur **Voir dans Transactions** : la page [Transactions](../transactions/index.md) s'ouvre, filtrée sur ce courtier et sur les filtres de colonnes que vous avez définis ici.

---

## 🧙 Importer un relevé

**Importer** ouvre l'espace de travail avec l'**Assistant d'importation** (BRIM, le module d'importation des rapports de courtier). L'assistant d'importation lit les fichiers exportés par votre courtier, vous permet de vérifier chaque ligne et transmet le résultat à l'espace de travail : rien n'est enregistré avant **Tout enregistrer**.

- 📥 **[Importer depuis un courtier](../transactions/import/index.md)** — courtiers et formats pris en charge.
- 🧙 **[Comment importer des transactions](../transactions/import/how-to.md)** — l'assistant d'importation, étape par étape.

Le même assistant d'importation s'ouvre depuis **Importer** sur la page [Transactions](../transactions/index.md).

??? tip "🧩 Votre courtier n'est pas encore pris en charge — ce que vous pouvez faire"

    - **Demander un plugin** : ouvrez une [demande de plugin](https://github.com/Librefolio/LibreFolio/issues/new?template=plugin_request.yml) sur GitHub et joignez un échantillon anonymisé de l'export du courtier.
    - **Écrire un plugin** : le [Guide des plugins BRIM](../../developer/architecture/patterns/brim_plugin_guide.md) explique le contrat de plugin, et [Contribuer](../../community/contribute.md) le flux de travail.
    - Si les lignes importées semblent toujours erronées, l'étape **Corrections** de l'assistant d'importation renvoie vers GitHub pour signaler un éventuel bug d'importation.

---

## 🗂️ Rapports téléversés

**Rapports téléversés** ouvre les fichiers de rapports stockés pour ce courtier :

- **Téléverser** des fichiers CSV ou Excel : ils sont associés à ce courtier et listés à l'étape **Sélectionner les fichiers** de l'assistant d'importation. Les fichiers que vous téléversez ensemble forment un lot — c'est ainsi que sont importées les banques qui répartissent un compte sur plusieurs exports, comme Danske Bank.
- **Prévisualiser** ou **Supprimer** un fichier. La suppression d'un rapport ne supprime jamais les transactions importées depuis celui-ci.
- Vérifiez les badges **Statut** et **Lot de rapports** de chaque fichier — voir [Lots de rapports](../files/index.md#report-sets).
- **Gérer tous les fichiers** ouvre la page [Fichiers et téléversements](../files/index.md#broker-reports), filtrée sur ce courtier.

Le téléversement et la suppression de rapports nécessitent un accès Propriétaire ou Éditeur au courtier.
