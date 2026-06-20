# <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" alt=""> Revolut

!!! info "Beta"

    Ce plugin est en version **Beta** — testé avec des fichiers d'exemple, mais des cas particuliers peuvent exister.

## 📥 Comment Exporter

Pour exporter l'historique de vos transactions d'actions/crypto depuis Revolut :

1. Ouvrez votre **application mobile Revolut** ou connectez-vous via le client web.
2. Naviguez vers l'onglet **Invest** (ou Actions/Crypto).
3. Appuyez sur **... (Plus)** à côté du solde de votre portefeuille, puis sélectionnez **Relevés**.
4. Sélectionnez le compte souhaité (ex. compte Actions) et appuyez sur **Relevé de transactions**.
5. Définissez la période, choisissez **CSV** comme format, et exportez. Transférez le fichier sur votre ordinateur.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Revolut App - Invest Statements selection and CSV export] -->
</div>

## ⚠️ Pièges Courants

!!! warning "Compte de Trading vs Compte Principal"

    Assurez-vous d'exporter le relevé du sous-compte **Invest/Trading**. Le relevé de la carte de débit principale Revolut utilise un format de fichier complètement différent et ne peut pas être traité par ce plugin.

## 📝 Notes

- Prend en charge les transactions d'actions, achats de crypto, dividendes versés, frais de garde et transferts de fonds.
- Gère automatiquement les montants multi-devises dans un même fichier.

## 🔗 Référence Développeur

→ [Fournisseur Revolut — Détails d'Implémentation](../../../developer/backend/brim/providers_list.md)
