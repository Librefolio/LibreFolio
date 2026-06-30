# <img src="https://www.coinbase.com/favicon.ico" alt=""> Coinbase

!!! info "Beta"

    Ce plugin est en **Beta** — testé avec des fichiers d'échantillon, mais des cas particuliers peuvent exister.

## 📥 Comment Exporter

Pour exporter votre relevé de transactions depuis Coinbase :

1. Connectez-vous à votre [compte Coinbase](https://www.coinbase.com).
2. Cliquez sur votre photo de profil dans le coin supérieur droit, puis sélectionnez **Taxes** ou **Statements**.
3. Sous la section **Reports**, localisez **Transaction History**.
4. Cliquez sur **Generate Report**, sélectionnez **CSV** comme type de fichier et choisissez la plage de dates souhaitée.
5. Une fois le rapport prêt, téléchargez le fichier CSV sur votre ordinateur.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Coinbase Taxes/Reports - Generate Transaction History CSV report] -->
</div>

## ⚠️ Pièges Courants

!!! warning "Type de Rapport Incorrect"

    Assurez-vous de télécharger le rapport **Transaction History**. Les autres rapports (comme les déclarations fiscales, les résumés de solde ou les rapports de registre d'actifs spécifiques) sont structurés différemment et ne seront pas analysés correctement.

!!! warning "Conversions USD/EUR"

    L'analyseur Coinbase traite les échanges de cryptos, les achats, les ventes et les frais. Assurez-vous que la devise d'affichage de votre compte correspond à la devise principale de votre portefeuille LibreFolio pour éviter les écarts de taux de change.

## 📝 Notes

- Prend en charge les achats, les ventes, les conversions, les envois, les réceptions, les récompenses de staking et l'évaluation des frais.
- Prend en charge les principales devises fiduciaires de base (USD, EUR, GBP).

## 🔗 Référence pour les Développeurs

→ [Coinbase Provider — Détails d'Implémentation](../../../developer/backend/brim/providers_list.md)
