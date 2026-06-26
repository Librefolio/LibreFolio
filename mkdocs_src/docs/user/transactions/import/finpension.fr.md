# <img src="https://www.finpension.ch/favicon.ico" alt=""> Finpension

!!! info "Beta"

    Ce plugin est en version **Bêta** — testé avec des fichiers d'exemple, mais des cas particuliers peuvent exister.

## 📥 Comment exporter

Pour exporter vos transactions depuis Finpension :

1. Connectez-vous à votre [compte Finpension](https://app.finpension.ch).
2. Accédez au tableau de bord de votre portefeuille/compte actif.
3. Cliquez sur l'onglet **Transactions** (Transazioni / Transaktionen).
4. Cliquez sur le bouton **Exporter** ou de téléchargement et sélectionnez **CSV**.
5. Enregistrez le fichier sur votre ordinateur.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Finpension Portal - Transactions page and Export button] -->
</div>

## ⚠️ Pièges courants

!!! warning "Do Not Modify Delimiters"

    Les exports de Finpension utilisent le point-virgule `;` comme séparateur de colonnes et des formats allemands/suisses. Le parseur BRIM détecte automatiquement ces paramètres régionaux. Évitez d'ouvrir le fichier dans des tableurs (comme Excel) et de le réenregistrer, car cela pourrait modifier la structure brute du CSV.

## 📝 Notes

- Plateforme de prévoyance suisse.
- Prend en charge les dépôts d'espèces, les achats, les ventes, les retenues d'impôts et les frais de gestion.
- Dénommé en CHF.
