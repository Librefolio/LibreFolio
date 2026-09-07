# 📥 Transactions du courtier

L'onglet **Transactions** est le centre de contrôle pour modifier le registre du courtier. Il répertorie toutes les opérations financières enregistrées (achats, ventes, dividendes, dépôts, retraits, transferts et conversions FX) rattachées à ce courtier.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="transactions-tab" alt="Broker Transactions Tab">
</div>

Depuis cet onglet, vous pouvez enregistrer des transactions manuellement ou lancer des importations groupées de relevés.

---

## ➕ Transactions manuelles

Cliquez sur le bouton **Ajouter une transaction** (icône `Plus`) pour ouvrir l'assistant modal de transaction unique. Cela vous permet d'enregistrer manuellement :

- **Achat / Vente** : Négocier des actifs, en précisant la date, le prix, la quantité et la devise.
- **Dividende / Revenu** : Revenus perçus sur les actifs détenus.
- **Dépôt / Retrait** : Entrées ou sorties externes de liquidités vers ou depuis le solde de trésorerie du courtier.
- **Transfert** : Transfert de liquidités ou d'actifs entre courtiers (par exemple, approvisionner le compte depuis un courtier bancaire).
- **Conversion FX** : Échanges de devises dans le compte du courtier.

Pour une explication détaillée des champs de transaction et des règles de validation, consultez le guide **[Formulaire de transaction](../transactions/form.md)**.

---

## 🧙 Import groupé (BRIM)

Le bouton **Importer** (icône `Upload`) lance l'assistant **BRIM** (Broker Report Import Module), qui importe en masse les relevés exportés de votre courtier : il analyse les fichiers, valide chaque ligne, unifie les titres trouvés, détecte les doublons et vous permet de tout passer en revue avant que quoi que ce soit ne soit écrit. Les lignes approuvées arrivent dans l'**éditeur groupé**, où un **Tout enregistrer** final les consigne dans le registre.

Le même assistant est également disponible depuis la page globale **[Transactions](../transactions/index.md)**. Pour la procédure complète, consultez les guides dédiés :

- 📥 **[Import depuis le courtier (BRIM)](../transactions/import/index.md)** — courtiers pris en charge, formats et notes par plugin.
- 🧙 **[Comment importer des transactions](../transactions/import/how-to.md)** — l'assistant, étape par étape.

---

## 🧩 Votre courtier est introuvable ?

Si votre courtier n'a pas encore de plugin d'importation, vous pouvez aider :

- **Demander un plugin** — ouvrez une [demande de plugin](https://github.com/Librefolio/LibreFolio/issues/new?template=plugin_request.yml) sur GitHub, en joignant un échantillon anonymisé du fichier d'exportation du courtier afin que le format puisse être compris. (L'étape Corrections de l'assistant comporte également une bannière « ouvrir une issue » pour signaler les lignes qui semblent incorrectes.)
- **Écrire un plugin** — le [Guide des plugins BRIM](../../developer/architecture/patterns/brim_plugin_guide.md) guide les développeurs à travers le contrat de fournisseur ; consultez [Contribuer](../../community/contribute.md) pour la démarche générale.

---

## 🗂️ Rapports téléversés

Cliquez sur le bouton **Rapports téléversés** (icône `FileText`) pour gérer les fichiers de rapports BRIM stockés pour ce courtier. La fenêtre modale vous permet de :

- Examiner les rapports téléversés (nom, date de téléversement, taille, statut), avec un **aperçu** rapide du contenu de chaque fichier.
- **Téléverser** de nouveaux rapports directement — ils sont automatiquement attribués à ce courtier et deviennent disponibles à l'étape Sélection des fichiers de l'assistant.
- **Supprimer** les rapports dont vous n'avez plus besoin.
- Accéder à la page complète **[Fichiers et téléversements](../files/index.md#broker-reports)**, pré-filtrée sur ce courtier.
