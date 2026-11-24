# <img src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" alt=""> Investimental

!!! warning "Bêta — retours bienvenus"

    Ce plugin a été écrit à partir des **fichiers d'exemple** et est actuellement en **bêta**. Nous serons ravis de recevoir tout retour pour l'améliorer ou pour mettre à jour la documentation sur la façon d'obtenir l'export.

## 📥 Comment Exporter

Exportez l'historique de vos transactions au format **CSV** depuis Investimental et importez-le dans LibreFolio. Pour la procédure pas à pas, consultez le **[Guide d'Importation](how-to.md)**.

## 📝 Notes

- Écrit à partir des fichiers d'exemple — certains cas limites peuvent ne pas encore être couverts.
- Un ordre exécuté en plusieurs fois devient **une** transaction avec toute la quantité et tout le montant exécutés, datée de sa dernière exécution ; un avertissement vous prévient quand les parties tombent des jours différents ou que leurs chiffres ne concordent pas. Importé avec une version précédente, un tel ordre ne gardait que sa dernière partie : supprimez cette transaction et importez de nouveau le fichier.
- Un export qui commence avec un ordre déjà en cours (sans ses premières lignes) ne peut pas donner la quantité totale de cet ordre : l'ordre est laissé de côté, et un avertissement montre ce que contient le fichier (date, prix, la partie qu'il montre) pour que vous le saisissiez à la main à partir de votre relevé.
- Chaque ordre exécuté apporte sa **commission**, comme frais lié à son trade. L'export donne la commission encore due sur la partie ouverte de l'ordre, donc la commission de chaque exécution est la baisse de ce chiffre ; le résultat vient du registre des ordres, au prix de l'ordre, et peut différer légèrement de votre relevé, c'est pourquoi un avertissement vous demande de la vérifier. Sur les ventes et les obligations le fichier écrit 0, donc aucun frais n'est créé : si le courtier les facture, ajoutez-les à la main. Les ordres importés avec une version précédente reçoivent leurs commissions comme lignes libres quand vous importez de nouveau le fichier : liez-les à leur trade depuis la sélection.
- Vous avez trouvé un problème ou souhaitez documenter les étapes d'export ? [Ouvrez un rapport](../../../community/contribute.md) — les contributions sont les bienvenues !
