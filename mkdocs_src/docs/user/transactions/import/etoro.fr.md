# <img src="https://www.etoro.com/favicon.ico" alt=""> eToro

!!! info "Beta"

    Ce plugin est en version **Bêta** — testé avec des fichiers d'exemple, mais des cas particuliers peuvent exister.

## 📥 Comment Exporter

Pour exporter l'historique de vos transactions depuis eToro :

1. Connectez-vous à votre [compte eToro](https://www.etoro.com).
2. Cliquez sur **Portefeuille** dans la barre latérale gauche, puis cliquez sur l'icône d'horloge pour ouvrir l'**Historique**.
3. Cliquez sur l'icône d'engrenage des paramètres en haut à droite et sélectionnez **Relevé de compte** (Account Statement).
4. Choisissez la date de début et de fin pour votre relevé, puis cliquez sur **Créer** (Create).
5. Sélectionnez l'option d'exportation **Excel** ou **CSV**. Enregistrez le fichier sur votre ordinateur.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: eToro Portfolio History - Account Statement creation and export] -->
</div>

## ⚠️ Pièges Courants

!!! warning "N'utilisez pas les relevés PDF"

    eToro permet de télécharger des relevés au format PDF. Les fichiers PDF ne peuvent pas être traités par l'importateur BRIM. Assurez-vous de sélectionner le format tableur (XLSX ou CSV).

!!! warning "CFD vs Actifs Réels"

    eToro prend en charge les CFD (contrats pour la différence) et les actifs réels. L'analyseur importera les transactions CFD, mais comme les CFD ne représentent pas des actions sous-jacentes, la base de coût et la logique WAC peuvent nécessiter une validation manuelle dans la grille des transactions.

## 📝 Notes

- Prise en charge des transactions sur actions, ETF, crypto et CFD, des dividendes versés, des dépôts, des retraits et des ajustements de frais.
- Toutes les valeurs dans les fichiers exportés d'eToro sont libellées en USD.

## 🔗 Référence pour les Développeurs

→ [eToro Provider — Détails d'Implémentation](../../../developer/backend/brim/providers_list.md)
