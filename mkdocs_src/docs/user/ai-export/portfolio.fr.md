# 🧠 Export IA du portefeuille

Exportez l'intégralité de votre portefeuille, tel que le tableau de bord l'affiche, pour interroger une IA sur sa structure, sa
performance, un plan d'investissement récurrent ou vos moins-values fiscales. Les options et la façon de coller se trouvent dans
la [Vue d'ensemble de l'export IA](index.md).

---

## 📍 Où le trouver

Dans le **Tableau de bord**, sélectionnez **Export IA** dans la barre d'outils, à côté de **Actualiser**. Il s'ouvre d'abord sur
**Plan d'investissement récurrent**.

L'export suit le [Tableau de bord](../dashboard/index.md) :

- les courtiers que vous **détenez** avec une part supérieure à 0 %, restreints par le filtre des courtiers lorsqu'il est activé ;
  les courtiers partagés avec vous en tant qu'éditeur ou lecteur sont exclus ;
- la devise du tableau de bord, avec le dernier jour de sa plage de dates comme date d'export.

Le bouton s'active une fois que le tableau de bord a chargé vos courtiers, et reste désactivé si vous n'en possédez aucun
avec une part supérieure à 0 %.

---

## 📤 Données d'export

| Choix | Ce que vous obtenez |
| :--- | :--- |
| **Vue d'ensemble et historique du portefeuille** | Positions, liquidités, allocations, performance, flux, revenus, coûts enregistrés, un résumé économique FIFO, un contexte de marché compact par actif et le repli |
| **Historique des actifs du portefeuille** | Prix détaillés, rendements, indicateurs, états et événements pour chaque actif que vous détenez, avec couverture |

---

## 🎯 Analyses

| Analyse | Ce que fait l'IA |
| :--- | :--- |
| **Plan d'investissement récurrent** | Planifie des investissements récurrents conditionnels à partir de vos chiffres, en ne demandant que ce qui lui manque |
| **Rééquilibrage du portefeuille** | Compare votre allocation avec les objectifs que vous indiquez et encadre des pistes de rééquilibrage conditionnelles |
| **Performance du portefeuille et facteurs de marché** | Explique votre résultat et recherche des facteurs de marché datés pour chaque actif que vous détenez : utilisez une IA capable de rechercher sur le web |
| **Stratégies de compensation des moins-values** | Explore comment des moins-values fiscales disponibles ou arrivant à expiration pourraient compenser des plus-values, en utilisant vos lots FIFO |

??? note "📅 Plan d'investissement récurrent — ce que l'IA vous demandera"

    L'IA part de vos données et ne demande que ce qui modifie le plan : combien vous pouvez investir et
    à quelle fréquence, votre objectif et votre horizon, l'ampleur d'une baisse que vous pouvez supporter, et les limites pratiques telles
    que la liquidité, les courtiers, les ordres minimum ou les actifs à éviter. Elle ne devine jamais ces réponses, peut
    esquisser des scénarios conditionnels entre-temps, et compare l'investissement en une seule fois avec l'investissement
    par étapes.

??? note "🧾 Stratégies de compensation des moins-values — ayez vos informations fiscales à portée de main"

    Les lots FIFO sont le calcul économique de LibreFolio, pas votre position fiscale légale. Avant de comparer
    des pistes, l'IA demande votre résidence fiscale et votre régime, le type de compte, et votre inventaire
    officiel des moins-values fiscales (par exemple le *cassetto fiscale* italien) avec les montants, les catégories et
    les dates d'expiration. Elle ne suggère jamais une opération uniquement pour des raisons fiscales.

---

## 🔗 Liens connexes

- 🧠 **[Vue d'ensemble de l'export IA](index.md)** — options, collage et confidentialité
- 📊 **[Tableau de bord](../dashboard/index.md)** — le périmètre que suit cet export
