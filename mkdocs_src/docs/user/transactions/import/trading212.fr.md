# <img src="https://www.trading212.com/favicon-32x32.png" alt=""> Trading212

!!! info "Bêta"

    Ce plugin est en phase **Bêta** — testé avec des fichiers d'exemple, mais des cas limites peuvent subsister.

## 📥 Comment exporter

Pour exporter votre relevé de transactions depuis Trading212 :

1. Connectez-vous au [portail client Trading212](https://www.trading212.com) (ou ouvrez l'application sur votre appareil mobile).
2. Rendez-vous dans la section menu/profil et cliquez sur **Historique**.
3. Cliquez sur le bouton **Exporter** (généralement représenté par une icône d'exportation ou de document en haut de l'onglet historique).
4. Sélectionnez les colonnes souhaitées (assurez-vous que tous les champs comme le ticker, la date, la quantité, le prix et la devise sont sélectionnés).
5. Choisissez **CSV** comme format et cliquez sur **Exporter**. Enregistrez le fichier sur votre ordinateur.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Emplacement de capture d'écran : portail Trading212 - Historique et fenêtre modale d'export CSV] -->
</div>

## ⚠️ Pièges courants

!!! warning "Transactions dans les Pies"

    Trading212 prend en charge les « Pies » (paniers d'actifs gérés automatiquement). Si vous négociez à l'intérieur d'un Pie, l'exportation présente ces transactions comme des transactions distinctes sur les actifs sous-jacents. Le parseur BRIM traite automatiquement ces transactions individuelles, mais assurez-vous que les soldes de votre Pie sont entièrement synchronisés dans la grille de préparation avant de valider.

## 📝 Remarques

- Prend en charge les achats et ventes d'actions/ETF, les dividendes, les intérêts sur liquidités, les dépôts et les retraits.
- Les comptes multidevises sont pris en charge.
- Les transferts entre vos propres comptes sont omis sans avertissement, car ils ne changent rien.

## 🔀 Divisions d'actions

Trading212 écrit une division sous la forme de deux lignes, **Stock split close** (les anciennes actions sortent) et **Stock split open** (les nouvelles actions arrivent), pour le même ISIN au même instant. Lorsque les actions après la division sont **plus nombreuses** qu'avant, LibreFolio importe la paire comme un seul **Ajustement** entrant correspondant à la différence, sans coût.

L'importateur ne peut pas distinguer une division d'un don ou d'une scission ; il signale donc la ligne. La fin de l'assistant d'importation (l'étape **Vérification**) vous indique combien de lignes ressemblent à des divisions, et l'éditeur groupé affiche une bannière : *N lignes peuvent être des divisions d'actions*. Pour chaque ligne, elle indique le ticker, les actions ajoutées et la date. Étant donné que la ligne **Stock split close** contient les actions que vous déteniez auparavant, elle affiche également le **ratio** obtenu (par exemple 3 pour une division 3 pour 1) ainsi que les actions détenues.

Deux boutons vous permettent de régler la situation :

- **Créer l'événement DIVISION et le lier** ouvre le petit formulaire d'événement avec le type déjà défini sur **Division** et le ratio prérempli avec la valeur suggérée. Vous pouvez le modifier : saisissez `3` pour une division 3 pour 1, `0.25` pour une division inversée 1 pour 4.
- **Lier à un événement existant** vous permet de choisir l'un des événements de l'actif, si vous avez déjà créé la division.

Une fois la ligne liée, l'entrée de la bannière disparaît. Si l'actif de la ligne n'a pas encore été choisi, la bannière vous demande de le choisir d'abord. Pour en savoir plus sur les événements, consultez [Événements d'actifs](../../assets/detail/events.md).

!!! note "🔢 Quand le courtier arrondit la quantité"

    Les courtiers arrondissent parfois les actions qu'ils enregistrent (par exemple 0.1643 au lieu de 0.16431924). Si la quantité de la ligne diffère du produit de votre position par (le ratio − 1), la bannière le signale et donne la différence en actions. La vue **Lots** suit le ratio de l'événement, tandis que le **Tableau de bord** et le coût moyen suivent la quantité de la ligne. L'écart est faible, mais après la vente de toute la position, un minuscule lot invendable peut subsister.

!!! warning "Liez la division à un événement Division"

    Tant que la ligne n'est pas liée à un événement **Division**, les nouvelles actions entrent sans coût et diluent le coût moyen de l'actif. La vue **Lots** affiche un lot avec un coût de 0. Si vous vendez une partie de la position, LibreFolio vend d'abord les anciens lots coûteux au prix d'après la division : vous constatez donc une perte, puis un gain lorsque le lot à coût nul est épuisé. Un actif sans cotation reste également surévalué : les nouvelles actions comptent à leur pleine valeur, alors même que le prix n'a pas été divisé. Lier l'événement aligne le coût sur les anciennes actions, ce qui est correct pour une division. Le fichier n'indique pas si les actions proviennent d'une division, d'un don ou d'une scission ; le choix vous revient donc.

## 🚧 Limitations connues

- **Divisions non importées.** Une division inversée (moins d'actions après l'opération qu'avant), une division avec le même nombre d'actions et une ligne de division sans sa contrepartie sont listées dans un avertissement orange, avec un lien pour ouvrir une issue sur GitHub : ajoutez-les à la main.
- **Les distributions d'actions et les conversions de devises ne sont pas importées.** Les lignes **Stock distribution** et **Currency conversion** sont listées dans le même avertissement : ajoutez-les à la main.
- **Quelque chose cloche ?** Merci d'[ouvrir une issue](https://github.com/Librefolio/LibreFolio/issues) avec un fichier d'exemple anonymisé.

## 🔗 Référence développeur

→ [Fournisseur Trading212 — Détails d'implémentation](../../../developer/backend/brim/providers_list.md)
