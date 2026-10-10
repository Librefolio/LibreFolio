---
title: Outils
description: Ce qu'est un Outil, les outils disponibles aujourd'hui, et comment en ouvrir un.
---

# 🧰 Outils

Un **Outil** est un calcul autonome : vous fournissez les données d'une opération, et il renvoie un résultat ou une erreur structurée. Ce n'est pas une instruction visant à modifier votre portefeuille.

La plateforme Outils est **expérimentale**. Le catalogue ne propose actuellement qu'**un seul**
outil :

| Outil | Ce qu'il fait |
|---|---|
| [Allocateur PAC](pac-allocator/index.md) | Planifie les achats qui rapprochent le plus possible une allocation de sa cible, en utilisant les liquidités et les versements disponibles maintenant. |

Sa carte ouvre un planificateur guidé. Sa propre page explique comment l'utiliser et ce que
fait le moteur de calcul qui le sous-tend.

!!! note "Un second outil a été retiré"

    Le catalogue proposait auparavant un Rééquilibreur de portefeuille à côté de
    l'allocateur PAC. Tous deux étaient des prototypes et tous deux ont été supprimés. Seul
    l'allocateur PAC a été reconstruit jusqu'à présent, donc un signet vers la page de
    documentation du Rééquilibreur n'est plus valide.

## 🖱️ Ouvrir un outil

Ouvrez **Outils** depuis la barre latérale pour voir le catalogue sous forme de grille de cartes. Pour un outil prêt, la **carte entière** est cliquable, pas seulement son titre ou une icône ; un indicateur en forme de flèche le signale comme ouvrable. Un outil dont l'interface est manquante n'a ni l'un ni l'autre, et indique sa situation sur la carte à la place.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="hub" alt="Catalogue d'outils avec la carte de l'allocateur PAC, sa paire de versions, et les actions Documentation et Recharger">
</div>

Le catalogue et un outil ouvert affichent tous deux :

- une action **Documentation** renvoyant vers la page de cet outil, avec un libellé qui apparaît à côté de l'icône sur les écrans larges et se réduit à une commande avec icône seule sur les écrans étroits ;
- une action **Recharger** qui recharge le catalogue (depuis le hub) ou l'interface de l'outil courant (depuis un outil ouvert), avec le même comportement adaptatif de commande avec icône seule ; recharger un outil ouvert demande d'abord une confirmation (**Recharger l'outil ?**), car cela remplace l'interface et abandonne son brouillon en cours ;
- la paire de compatibilité de l'outil, `Backend/API <contract_version> · UI <ui.version>`, sans numéro de build ou d'implémentation distinct affiché à côté.

Lorsque certaines entrées du catalogue ou interfaces sont indisponibles, le hub indique combien et renvoie vers **Paramètres → À propos → Diagnostics du plugin**.

## ℹ️ Bon à savoir

- **Un outil ne modifie jamais votre portefeuille.** Il n'enregistre aucune transaction, ne
  passe aucun ordre et ne sauvegarde rien dans votre portefeuille : c'est à vous d'agir sur
  son résultat.
- **Serveur occupé ou délai dépassé ?** Vous n'obtenez aucun résultat, et cela ne dit rien sur
  vos chiffres : attendez un instant, puis réessayez.
- **Un outil est manquant ou ne peut pas être ouvert ?** Consultez **Paramètres → À propos →
  Diagnostics du plugin** : son panneau **Outils** indique, outil par outil, s'il est
  disponible et, sinon, pourquoi. Voir [À propos](../settings/about.md).
