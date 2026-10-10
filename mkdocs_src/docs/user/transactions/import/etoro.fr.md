# 📥 <img src="https://www.etoro.com/favicon.ico" alt=""> eToro

!!! info "Bêta"

    Ce plugin est en **Bêta** — testé avec des fichiers d'exemple, mais des cas limites peuvent exister.

LibreFolio lit la feuille **Account Activity** du relevé de compte d'eToro, une fois cette feuille enregistrée au format CSV.

## 📥 Comment exporter

1. Connectez-vous à votre [compte eToro](https://www.etoro.com).
2. Ouvrez **Portefeuille**, puis **Historique** (l'icône d'horloge).
3. Cliquez sur l'icône de paramètres en haut à droite et choisissez **Relevé de compte**.
4. Choisissez les dates de début et de fin, puis cliquez sur **Créer**.
5. Téléchargez le relevé avec l'icône **XLS**.
6. Ouvrez le fichier dans un tableur, allez à la feuille **Account Activity** et enregistrez cette feuille au format **CSV**,
   en conservant les noms de colonnes sur la première ligne. LibreFolio ne lit pas les fichiers PDF ou Excel.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: eToro Portfolio History - Account Statement creation and export] -->
</div>

## 🔄 Ce qui est importé

| Dans la feuille Account Activity (**Type**) | Importé comme |
|:-------------------------------|:------------|
| Open Position | **Achat** |
| Position closed | **Vente** |
| Dividend | **Dividende** |
| Interest Payment | **Intérêt** |
| Deposit | **Dépôt** |
| Withdraw Request | **Retrait** |
| Withdraw Fee, Withdrawal Conversion Fee, Conversion Fee | **Frais**, lorsque le montant n'est pas nul |

L'instrument provient de **Details** (par exemple `NKE/USD`) et la quantité provient de **Units**.

**Non importés** : **Overnight fee** et **Overnight refund** (financement CFD) et **SDRT** (droit de timbre
britannique) sont ignorés sans avertissement, donc ajoutez-les manuellement si vous les suivez. Tout autre type est
ignoré avec un avertissement.

## ⚠️ Pièges courants

!!! warning "Vérifiez la devise des instruments non cotés en USD"

    LibreFolio enregistre chaque ligne dans la devise après la barre oblique dans **Details** (`KER/EUR` en euro),
    et toutes les autres lignes en dollars américains. eToro indique ses montants dans la devise de votre compte (généralement
    USD) : vérifiez les lignes des instruments cotés dans une autre devise avant de les enregistrer.

- **Conservez les dates d'eToro** : jour/mois/année, avec ou sans l'heure. Une ligne dont la date ne peut pas être lue
  est ignorée avec un avertissement.
- **Frais de conversion de retrait.** Des frais non nuls deviennent des **Frais** distincts, à côté du **Withdraw Request** complet. Comparez les deux avec votre relevé : si les frais ont déjà été déduits de l'argent retiré, décochez-les dans [Récapitulatif](how-to.md#review).
- Les **CFD** deviennent des achats et des ventes ordinaires de l'instrument, comme de vraies actions, sans leurs
  frais de financement nocturnes : vérifiez ces positions et leurs coûts.

## 🔗 Référence développeur

→ [Architecture BRIM — notes eToro](../../../developer/backend/brim/architecture.md#plugin-etoro)
