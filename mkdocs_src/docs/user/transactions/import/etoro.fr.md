# 📥 <img src="https://www.etoro.com/favicon.ico" alt=""> eToro

!!! info "Bêta"

    Ce plugin est en **Bêta** — testé avec des fichiers d'exemple, mais des cas limites peuvent subsister.

LibreFolio lit la feuille **Account Activity** du relevé de compte eToro enregistré au format CSV.

## 📥 Comment exporter

1. Connectez-vous à votre [compte eToro](https://www.etoro.com).
2. Ouvrez **Portefeuille**, puis **Historique** (l'icône en forme d'horloge).
3. Cliquez sur l'icône de paramètres en haut à droite et choisissez **Relevé de compte**.
4. Choisissez les dates de début et de fin, puis cliquez sur **Créer**.
5. Téléchargez le relevé avec l'icône **XLS**.
6. Ouvrez le fichier dans un tableur, allez sur la feuille **Account Activity** et enregistrez-le au format **CSV**,
   en conservant les noms de colonnes sur la première ligne. LibreFolio ne lit pas les fichiers PDF ni Excel.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Emplacement de la capture d'écran : historique du portefeuille eToro — création et export du relevé de compte] -->
</div>

## 🔄 Ce qui est importé

| Dans Account Activity (**Type**) | Importé en tant que |
|:-------------------------------|:------------|
| Open Position | **Achat** |
| Position closed | **Vente** |
| Dividend | **Dividende** |
| Interest Payment | **Intérêt** |
| Deposit | **Dépôt** |
| Withdraw Request | **Retrait** |
| Withdraw Fee, Withdrawal Conversion Fee, Conversion Fee | **Frais**, lorsque le montant n'est pas nul |
| Overnight fee (CFD financing) | **Frais**, lorsque le montant n'est pas nul : un coût de l'argent, sans actif |
| Overnight refund (CFD financing given back) | **Intérêt** : argent restitué (montant positif), sans actif et avec la description *Overnight refund* |
| SDRT (UK stamp duty) | **Impôt**, sur l'instrument de la ligne |

L'instrument provient de **Details** (par exemple `NKE/USD`) et la quantité de **Units**.

Tout autre type est ignoré avec un avertissement.

## ⚠️ Pièges courants

!!! warning "Vérifiez la devise des instruments non cotés en USD"

    LibreFolio enregistre chaque ligne dans la devise indiquée après la barre oblique dans **Details** (`KER/EUR` en euros),
    et toutes les autres lignes en dollars américains. eToro exprime ses montants dans la devise de votre compte (généralement
    USD) : vérifiez les lignes des instruments cotés dans une autre devise avant de les enregistrer.

- **Conservez les dates d'eToro** : jour/mois/année, avec ou sans l'heure. Une ligne dont la date ne peut pas être lue
  est ignorée avec un avertissement.
- **Frais de conversion de retrait.** Des frais non nuls deviennent des **Frais** distincts, à côté du **Withdraw Request**
  complet. Comparez les deux avec votre relevé : si les frais ont déjà été déduits de l'argent retiré, décochez-les dans
  [Récapitulatif](how-to.md#review).
- **Les CFD** deviennent des achats et des ventes ordinaires de l'instrument, comme de vraies actions. Leurs **frais
  overnight** sont importés comme des transactions **Frais** distinctes, sans actif : vérifiez ces positions et
  leurs coûts par rapport à votre relevé.
- **Frais overnight et remboursements.** Les frais sont importés comme **Frais** et les remboursements comme **Intérêt** :
  le coût overnight que vous avez réellement payé, net des remboursements, correspond aux frais moins les remboursements.
  Un remboursement est comptabilisé comme un revenu ; il figure donc dans un rapport de revenus.

## 🚧 Limites connues {: #known-limitations }

- **Montants dans la devise de votre compte.** Voir l'avertissement ci-dessus : vérifiez la devise des instruments non
  cotés en USD avant d'enregistrer.
- **Quelque chose ne va pas ?** Merci d'[ouvrir un ticket](https://github.com/Librefolio/LibreFolio/issues) avec
  un fichier d'exemple anonymisé.

## 🔗 Référence pour les développeurs

→ [Architecture BRIM — notes eToro](../../../developer/backend/brim/architecture.md#plugin-etoro)
