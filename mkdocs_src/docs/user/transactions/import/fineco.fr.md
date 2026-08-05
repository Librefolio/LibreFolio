# <img src="https://finecobank.com/favicon.ico" alt=""> Fineco

!!! info "Beta"

    Ce plugin est en **Beta** — testé avec des fichiers d'exemple mais des cas limites peuvent exister.

## 📥 Comment exporter

LibreFolio importe le rapport **"Movimenti Dossier Titoli"** (mouvements du dossier titres)
exporté depuis FinecoBank.

1. Connectez-vous à votre compte **FinecoBank** (web ou application).
2. Ouvrez la section **Dossier Titoli** et sélectionnez le compte ou la période souhaités.
3. Exportez la liste des mouvements. Fineco propose le rapport sous forme de fichier Excel.
4. Si le fichier est `.xls`/`.xlsx`, ouvrez-le et **enregistrez-le en CSV** avant l'importation — le
   plugin lit le format **CSV**.

## 📝 Remarques

- **Les avertissements d'importation sont affichés en italien.** Le seul export pris en charge aujourd'hui
  est le *Movimenti Dossier Titoli* italien de FinecoBank, donc tous les avertissements émis lors de l'analyse
  apparaissent en italien pour correspondre au rapport. FinecoBank opère également au Royaume-Uni — si un
  format d'export britannique (ou autre) est ajouté ultérieurement, ses avertissements suivront la langue de ce format.
- Deux formats d'export sont pris en charge automatiquement :
    - **sans frais** (11 colonnes), et
    - **avec frais** (15 colonnes). Les colonnes de frais sont importées comme des transactions
      **frais** distinctes.
- Opérations prises en charge : achats et ventes (*Compravendita titoli*), dividendes (*Dividendo*),
  coupons d'obligations (*Stacco Cedole*), remboursements/échéances (*Rimborso*), et augmentations
  de capital (*Aumento capitale*, importées comme un **ajustement** de quantité sans mouvement de trésorerie).
- **Obligation remboursée au-dessus du pair** — lorsqu'une ligne *Rimborso* concerne une obligation
  évaluée **au-dessus du pair (100)**, le montant crédité au-dessus du pair (un *premio fedeltà* / réévaluation d'inflation)
  est comptabilisé comme un **intérêt** distinct et la **vente** est enregistrée au pair 100. Cela reflète le
  traitement des coupons (*reddito di capitale*) et maintient la plus-value réalisée basée uniquement sur le
  prix par rapport au coût. Les obligations remboursées au pair ou en dessous, et les remboursements d'actions,
  sont importés comme une seule vente.
- **Les montants sont importés textuellement** dans la devise rapportée par Fineco : la colonne *Divisa*
  de chaque ligne détermine la devise des chiffres de cette ligne. Aucune conversion de devise n'est
  effectuée et la colonne *Cambio* (taux de change) est ignorée — les chiffres atterrissent dans LibreFolio
  exactement tels qu'ils apparaissent dans le rapport.
- La *Data valuta* (date de valeur) est utilisée comme date de règlement de la transaction.

## 🔗 Référence développeur

→ [BRIM Providers — Détails d'implémentation](../../../developer/backend/brim/providers_list.md)