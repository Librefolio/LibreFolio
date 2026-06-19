# <img src="https://www.interactivebrokers.com/favicon.ico" alt=""> Interactive Brokers (IBKR)

!!! info "Beta"

    Ce plugin est en **Beta** — testé avec des fichiers d'échantillons, mais des cas particuliers peuvent exister.

## 📥 Comment exporter

Pour exporter vos transactions depuis Interactive Brokers, suivez ces étapes :

1. Connectez-vous au [Portail Client Interactive Brokers](https://www.interactivebrokers.com).
2. Accédez à **Reports** (Rapports) dans le menu supérieur, puis sélectionnez **Statements** (Relevés).
3. Sous la section **Activity** (Activité), cliquez sur la carte **Activity Statement** (Relevé d'activité).
4. Sélectionnez la **Date Range** (Plage de dates) souhaitée (ex: Year to Date, Custom) et choisissez **CSV** comme format.
5. Cliquez sur **Run** (Exécuter) ou téléchargez le rapport CSV généré sur votre ordinateur.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Interactive Brokers Portal - Statements & Reports menu] -->
</div>

### ⚙️ Utilisation des Flex Queries (Recommandé)

Pour des portefeuilles plus avancés, vous pouvez configurer une **Flex Query** (requête Flex) pour exporter des données spécifiques :

1. Sous **Reports**, allez dans **Flex Queries** et cliquez sur le bouton **+ (Create)**.
2. Sélectionnez **Activity Flex Query**.
3. Ajoutez **Trades** (Transactions), **Cash Transactions** (Transactions de trésorerie, pour les dividendes et les frais), et **Corporate Actions** (Opérations sur titres) à la requête.
4. Réglez le format sur **CSV** et enregistrez la requête. Vous pouvez exécuter cette requête personnalisée à tout moment.

## ⚠️ Pièges courants

!!! warning "Format de fichier"

    Assurez-vous d'exporter au format **CSV**. Les relevés PDF ne sont pas pris en charge par l'analyseur et l'importation échouera.

!!! warning "Paramètres de langue"

    L'analyseur est conçu pour des en-têtes CSV en anglais. Assurez-vous que la langue de votre Portail Client IBKR est réglée sur l'anglais avant de lancer l'exportation.

## 📝 Notes

- Prend en charge les rapports d'activité standard d'IBKR (transactions, dividendes, retenues fiscales, frais, dépôts, retraits).
- Les comptes multi-devises sont pris en charge.
- Les opérations sur titres (divisions, fusions) peuvent nécessiter des ajustements manuels dans la grille de staging.

## 🔗 Référence développeur

→ [Fournisseur IBKR — Détails d'implémentation](../../../developer/backend/brim/providers_list.md)
