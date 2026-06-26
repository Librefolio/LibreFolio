# <img src="https://www.schwab.com/favicon.ico" alt=""> Charles Schwab

!!! info "Beta"

    Ce plugin est en **Bêta** — testé avec des fichiers d'exemple, mais des cas particuliers peuvent exister.

## 📥 Comment exporter

Pour exporter l'historique de vos transactions depuis Charles Schwab :

1. Connectez-vous à votre [Charles Schwab Client Portal](https://www.schwab.com).
2. Allez dans l'onglet **Accounts** et sélectionnez **History**.
3. Sélectionnez le compte que vous souhaitez exporter (si vous possédez plusieurs comptes).
4. Sélectionnez la plage de dates souhaitée.
5. Cliquez sur le lien **Export** (généralement situé dans le coin supérieur droit du tableau des transactions) et sélectionnez **CSV**.
6. Enregistrez le fichier sur votre ordinateur.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Charles Schwab Portal - History tab and Export link] -->
</div>

## ⚠️ Pièges courants

!!! warning "Ne modifiez pas la structure du fichier"

    Les fichiers CSV de Schwab ont une mise en page spécifique avec des lignes de métadonnées en bas (commençant généralement par "Transactions Total"). Le parseur BRIM détecte et ignore automatiquement ces lignes de métadonnées. Ne supprimez pas manuellement les lignes du bas du CSV.

## 📝 Notes

- Prise en charge des paramètres CSV au format US (structures de date MM/DD/YYYY et devises en USD).
- Analyse les transactions d'achat/vente, les paiements de dividendes, les réinvestissements et les frais de transaction.
