# <img src="https://www.degiro.com/favicon.ico" alt=""> Degiro

!!! info "Beta"

    Ce plugin est en **Bêta** — testé avec des fichiers d'exemple, mais des cas particuliers peuvent exister.

## 📥 Comment Exporter

Pour exporter vos transactions depuis Degiro :

1. Connectez-vous au [Portail Client Degiro](https://www.degiro.eu).
2. Allez dans **Boîte de réception** (ou Compte) dans la barre latérale gauche, puis cliquez sur **Relevé de compte**.
3. Sélectionnez la **Date de début** et la **Date de fin** souhaitées pour couvrir l'historique de vos transactions.
4. Cliquez sur le bouton **Exporter** et sélectionnez le format **CSV**.
5. Enregistrez le fichier sur votre ordinateur.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Degiro Portal - Inbox and Account Statement page] -->
</div>

## ⚠️ Pièges Courants

!!! warning "Rapports Séparés"

    Degiro propose différents menus d'exportation. Assurez-vous de télécharger le **Relevé de compte** (qui enregistre tous les mouvements de trésorerie, les achats, les ventes et les dividendes) plutôt que la simple liste des « Transactions », qui pourrait omettre les événements de trésorerie.

!!! warning "Formats de Langue"

    L'analyseur prend en charge plusieurs modèles locaux de Degiro (anglais, néerlandais, italien, allemand, etc.). Cependant, veillez à ne pas modifier manuellement les en-têtes de colonnes ou les délimiteurs CSV après l'exportation.

## 📝 Notes

- Prise en charge des opérations d'achat/vente, des dividendes, des frais de transaction, des dépôts et des retraits.
- Les conversion de devise effectuées par Degiro sont traitées automatiquement.

## 🔗 Référence Développeur

→ [Fournisseur Degiro — Détails d'Implémentation](../../../developer/backend/brim/providers_list.md)
