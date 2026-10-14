# 📥 <img src="https://finecobank.com/favicon.ico" alt=""> Fineco

!!! info "Bêta"

    Ce plugin est en **Bêta** — testé avec des fichiers d'exemple, mais des cas limites peuvent se présenter.

LibreFolio importe le rapport **Movimenti Dossier Titoli** de FinecoBank — les mouvements de votre
dossier titres — enregistré au format CSV.

## 📥 Comment exporter

1. Connectez-vous à votre compte **FinecoBank** (sur le web ou dans l'application).
2. Ouvrez les mouvements du **Dossier Titoli** et choisissez le compte et la période souhaités.
3. Exportez la liste : Fineco vous fournit un fichier Excel.
4. Ouvrez-le et **enregistrez-le au format CSV**. Conservez les lignes au-dessus du tableau (**Dossier:**,
   **Intestatario:**) et les noms de colonnes : LibreFolio reconnaît le rapport grâce à eux.

## 🔄 Ce qui est importé

| Dans le rapport (**Descrizione**) | Importé comme |
|:--------------------------------|:------------|
| *Compravendita titoli*, avec **Segno** `A` ou `V` | **Achat** ou **Vente** |
| *Dividendo* | **Dividende** |
| *Stacco Cedole* | **Intérêt** (coupon obligataire) |
| *Rimborso* | **Vente** (remboursement ou échéance) |
| *Aumento capitale* | **Ajustement** de la quantité, sans flux de trésorerie |
| Colonnes de commission, lorsque le rapport en comporte | Des **frais** distincts sur chaque ligne, en euros |

Toute autre opération est écartée et fait l'objet d'un avertissement.

**Obligations remboursées au-dessus du pair.** Lorsqu'une obligation est remboursée au-dessus du pair (100) — un *premio fedeltà* ou une revalorisation liée à l'inflation — la vente est enregistrée au pair et le montant excédentaire comme un **Intérêt** distinct, à l'instar d'un coupon, afin que votre gain reflète uniquement le prix. LibreFolio reconnaît les obligations par leur nom (BTP, BOT, CCT…). Les obligations remboursées au pair ou en dessous, ainsi que les autres remboursements, donnent lieu à une **Vente** unique.

## ⚠️ Bon à savoir

- **Les deux mises en page fonctionnent**, avec ou sans les colonnes de commission : LibreFolio les distingue de lui-même.
- **Montants tels quels.** Chaque ligne conserve sa propre devise (**Divisa**), sans conversion ; la
  colonne **Cambio** est ignorée.
- **Dates.** LibreFolio utilise la date de valeur (**Data valuta**), ou la date de négociation si la date de valeur est absente.

## 🔗 Référence développeur

→ [Architecture BRIM — Notes Fineco](../../../developer/backend/brim/architecture.md#plugin-fineco)
