# <img src="https://traderepublic.com/favicon.ico" alt=""> Trade Republic

!!! warning "Bêta — les retours de la communauté sont les bienvenus"

    Ce plugin a été développé à partir de **fichiers d'export d'exemple** et se trouve actuellement en **bêta**. Nous serons ravis de recevoir tout signalement permettant de l'améliorer ou de mettre à jour la documentation sur la façon d'obtenir l'export.

## 📥 Comment exporter

Exportez votre historique de transactions au format **CSV** depuis Trade Republic et importez-le dans LibreFolio. Pour connaître le déroulement pas à pas de l'importation, consultez le **[Guide d'importation](how-to.md)**.

## 📝 Remarques

- Développé à partir d'exports d'exemple — certains cas particuliers ne sont peut-être pas encore couverts.
- **Les colonnes de frais et d'impôt (*Kosten*, *Belasting*) ne sont pas encore importées** : la ligne elle-même est importée, et un avertissement orange liste les lignes comportant des frais ou un impôt, avec un lien pour ouvrir un ticket sur GitHub. Ajoutez les frais ou l'impôt à la main. Le même avertissement liste les lignes que LibreFolio ne connaît pas ou ne parvient pas à lire.
- **Vous n'êtes pas sûr que la valeur nette soit réellement nette** : voir [Vérifier le montant net](#check-the-net-amount) ci-dessous.
- Vous avez trouvé un problème ou vous souhaitez documenter les étapes de l'export ? [Ouvrez un signalement](../../../community/contribute.md) — les contributions sont les bienvenues !

## 🔍 Vérifier le montant net {: #check-the-net-amount }

!!! warning "Nous ne savons pas si la valeur nette inclut déjà les frais et l'impôt"

    LibreFolio importe chaque Achat ou Vente en utilisant la colonne **`Waarde (netto)`** (« valeur nette ») comme
    montant de trésorerie. Nous **ne savons pas** si cette valeur contient déjà les frais (**`Kosten`**) et l'impôt
    (**`Belasting`**) de la ligne : le développeur ne dispose d'aucun export récent et sûr de Trade Republic pour
    le vérifier.

    Un exemple simple : vous achetez des actions et Trade Republic vous facture des frais de 1,00 EUR.

    - **Si la valeur nette inclut déjà les frais** (par exemple 101,00 EUR, dont 1,00 EUR de frais),
      l'Achat est déjà correct. Ajouter ces frais de 1,00 EUR à la main, comme le suggère l'avertissement orange,
      reviendrait à compter ces frais **deux fois**.
    - **Si la valeur nette n'inclut pas les frais** (elle affiche 100,00 EUR), le montant de trésorerie
      de l'Achat est inférieur de 1,00 EUR, et les frais doivent être ajoutés à la main.

    Le même raisonnement s'applique à une Vente et à l'impôt.

**Ce qu'il faut vérifier, avant d'ajouter quoi que ce soit :**

1. Choisissez un Achat ou une Vente comportant des frais ou un impôt (l'avertissement orange les liste).
2. Comparez cette opération avec votre **relevé de compte** ou avec le total affiché par l'application Trade Republic :
   la trésorerie qui a quitté votre compte (ou qui y est entrée, pour une vente) correspond-elle à ce que LibreFolio affiche pour
   cette ligne ?
3. Si les deux **correspondent**, les frais sont déjà inclus : ne les ajoutez **pas**. Si LibreFolio affiche **moins**
   que le mouvement de trésorerie réel, ajoutez les **`Kosten`** et **`Belasting`** à la main sous forme de transactions
   distinctes de frais et d'impôt.

Un véritable **fichier d'exemple anonymisé** permettrait de trancher définitivement la question. Si vous pouvez en partager un, veuillez
[ouvrir un ticket](https://github.com/Librefolio/LibreFolio/issues) : nous corrigerons alors l'importateur et
cette page.
