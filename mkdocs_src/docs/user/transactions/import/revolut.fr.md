# <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" alt=""> Revolut

!!! info "Bêta"

    Ce plugin est en **Bêta** — testé avec des fichiers d’exemple, mais des cas limites peuvent exister.

## 📥 Comment exporter

Pour exporter l’historique de vos transactions d’actions/crypto depuis Revolut :

1. Ouvrez votre **application mobile Revolut** ou connectez-vous via le client web.
2. Accédez à l’onglet **Invest** (ou Actions/Crypto).
3. Appuyez sur **... (Plus)** à côté du solde de votre portefeuille, puis sélectionnez **Relevés**.
4. Sélectionnez le compte souhaité (par exemple, un compte Actions) et appuyez sur **Relevé des transactions**.
5. Définissez la période, choisissez **CSV** comme format, puis exportez. Transférez le fichier sur votre ordinateur.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Revolut App - Invest Statements selection and CSV export] -->
</div>

## ⚠️ Pièges courants

!!! warning "Compte de trading vs compte principal"

    Assurez-vous d’exporter le relevé depuis le sous-compte **Invest/Trading**. Le relevé principal de la carte de débit Revolut utilise un format de fichier totalement différent et ne peut pas être analysé par ce plugin.

## 📝 Remarques

- Prend en charge les opérations sur actions, les achats de crypto, les dividendes versés, les frais de conservation et les virements.
- Gère automatiquement les montants en plusieurs devises dans un même fichier.
- Les virements entre vos propres comptes sont écartés discrètement, car ils ne changent rien.

## 🔀 Divisions d’actions {: #stock-splits }

Dans un fichier **Invest**, une ligne **STOCK SPLIT** avec une **Quantity** positive est importée comme un **Ajustement** entrant portant sur les actions ajoutées (la **Quantity** de la ligne correspond au nombre de nouvelles actions, et non au total après la division), sans coût.

L’importateur ne pouvant pas distinguer une division d’un don ou d’une scission, il signale donc la ligne. La fin de l’assistant d’importation (l’étape **Vérification**) vous indique combien de lignes ressemblent à des divisions, et l’éditeur groupé affiche une bannière, *N lignes peuvent être des divisions d’actions*. Pour chaque ligne, il liste le ticker, les actions ajoutées et la date. Lorsque les lignes situées au-dessus dans le fichier indiquent combien d’actions vous déteniez avant la division, il affiche aussi le **ratio** obtenu (par exemple 3 pour une division 3 pour 1) et les actions détenues.

Deux boutons vous permettent de régler cela :

- **Créer l’événement DIVISION et le lier** ouvre le petit formulaire d’événement avec le type déjà défini sur **Division** et le ratio prérempli avec la valeur suggérée. Vous pouvez le modifier : saisissez `3` pour une division 3 pour 1, `0.25` pour un regroupement 1 pour 4.
- **Lier à un événement existant** vous permet de choisir l’un des événements de l’actif, si vous avez déjà créé la division.

Une fois la ligne liée, l’entrée de la bannière disparaît. Si l’actif de la ligne n’est pas encore choisi, la bannière vous demande de le choisir d’abord. Pour en savoir plus sur les événements, consultez [Événements d’actif](../../assets/detail/events.md).

!!! note "🔢 Quand le courtier arrondit la quantité"

    Les courtiers arrondissent parfois les actions qu’ils inscrivent (par exemple 0,1643 au lieu de 0,16431924). Si la quantité de la ligne diffère de votre position multipliée par (le ratio moins un), la bannière le signale et indique la différence en nombre d’actions. La vue **Lots** suit le ratio de l’événement, tandis que le **Tableau de bord** et le coût moyen suivent la quantité de la ligne. L’écart est faible, mais après la vente de toute la position, un minuscule lot qui ne peut pas être vendu peut subsister.

!!! warning "Liez la division à un événement Division"

    Tant que la ligne n’est pas liée à un événement **Division**, les nouvelles actions entrent sans coût et diluent le coût moyen de l’actif. La vue **Lots** affiche un lot avec un coût de 0. Si vous vendez une partie de la position, LibreFolio vend d’abord les anciens lots coûteux au prix après la division, de sorte que vous voyez une perte, puis un gain lorsque le lot à coût nul est épuisé. Un actif sans cotation reste également surévalué : les nouvelles actions comptent à leur pleine valeur, même si le prix n’a pas été divisé. Lier l’événement aligne le coût sur les anciennes actions, ce qui est correct pour une division. Le fichier ne précise pas si les actions proviennent d’une division, d’un don ou d’une scission ; le choix vous revient donc.

## 🚧 Limites connues

- **Les regroupements d’actions ne sont pas importés.** Une ligne **STOCK SPLIT** avec une **Quantity** négative, nulle ou absente (ou sans ticker) est listée dans un avertissement ambré, avec un lien pour ouvrir une issue sur GitHub : ajoutez-la manuellement.
- **Fichiers Invest uniquement.** Les divisions d’actions sont lues dans les relevés Invest, et non dans les relevés Crypto.
- **Quelque chose ne va pas ?** Veuillez [ouvrir une issue](https://github.com/Librefolio/LibreFolio/issues) avec un fichier d’exemple anonymisé.

## 🔗 Référence développeur

→ [Fournisseur Revolut — Détails d’implémentation](../../../developer/backend/brim/providers_list.md)
