# <img src="https://www.trading212.com/favicon.ico" alt=""> Trading212

!!! info "Beta"

    Ce plugin est en **Bêta** — testé avec des fichiers d'exemple, mais des cas particuliers peuvent exister.

## 📥 Comment exporter

Pour exporter votre relevé de transactions depuis Trading212 :

1. Connectez-vous au [Portail Client Trading212](https://www.trading212.com) (ou ouvrez l'application sur votre appareil mobile).
2. Allez dans la section menu/profil et cliquez sur **History**.
3. Cliquez sur le bouton **Export** (généralement représenté par une icône d'exportation ou de document en haut de l'onglet historique).
4. Sélectionnez les colonnes souhaitées (assurez-vous que tous les champs tels que le ticker, la date, la quantité, le prix et la devise sont sélectionnés).
5. Choisissez **CSV** comme format et cliquez sur **Export**. Enregistrez le fichier sur votre ordinateur.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Trading212 Portal - History and CSV Export modal] -->
</div>

## ⚠️ Pièges courants

!!! warning "Transactions de Pies"

    Trading212 supporte les « Pies » (paniers d'actifs gérés automatiquement). Si vous tradez à l'intérieur d'une Pie, l'exportation présente ces transactions comme des transactions d'actifs sous-jacents distinctes. Le parseur BRIM traite ces transactions individuelles automatiquement, mais assurez-vous que vos soldes de Pies sont entièrement synchronisés dans la grille de staging avant de valider.

## 📝 Notes

- Prend en charge les achats et ventes d'actions/ETF, les dividendes, l'intérêt sur les liquidités, les dépôts, les retraits et les frais de conversion de devise.
- Les comptes multi-devises sont supportés.

## 🔗 Référence développeur

→ [Fournisseur Trading212 — Détails d'implémentation](../../../developer/backend/brim/providers_list.md)
