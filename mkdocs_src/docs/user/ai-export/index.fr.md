# 🧠 Export IA

L'export IA copie vos données LibreFolio sous forme de texte prêt à coller, avec une question ciblée si vous le souhaitez, afin que vous puissiez interroger l'assistant IA de votre choix sur votre portefeuille, un courtier, un actif ou une paire FX. LibreFolio lui-même ne contacte jamais un service IA.

---

## 🎯 À quoi cela sert

- **Examiner avec des chiffres réels** : un courtier, une position, une paire FX et votre exposition à celle-ci.
- **Planifier** : investissements récurrents, un rééquilibrage, ou comment les moins-values fiscales arrivant à expiration pourraient compenser les plus-values.
- **Expliquer** : ce qui a motivé votre performance, actif par actif, avec des sources datées.
- **Conserver un instantané** : juste les faits, prêt pour votre propre question.

Ce que vous copiez est un contexte factuel, pas un conseil en investissement.

---

## 🚀 Ouvrir

Sélectionnez **Export IA** (:material-brain:) dans la barre d'outils de l'une de ces pages :

| Page | Ce que couvre l'export | Guide |
| :--- | :--- | :--- |
| **Tableau de bord** | Votre portefeuille, tel que le montre le Tableau de bord | [Portefeuille](portfolio.md) |
| Une page de détail d'un **courtier** | Ce courtier uniquement | [Courtier](broker.md) |
| Une page de détail d'un **actif** | Cet actif et, si vous le détenez, votre position | [Actif](asset.md) |
| Une page de détail **FX** | Cette paire FX et votre exposition directe à celle-ci | [FX](fx.md) |

L'export est daté au **dernier jour de la plage de dates de la page** : déplacez cette date pour exporter un moment antérieur.

---

## 🧭 Choisir quoi exporter

Le panneau s'ouvre sur un choix prêt à l'emploi : modifiez uniquement ce dont vous avez besoin.

### 📤 Étape 1 : Choisir le type d'export

Sous **Type d'export** :

- **Exporter les données** copie uniquement les faits : conservez un instantané ou posez votre propre question.
- **Demander une analyse** ajoute une question ciblée, des règles pour vérifier les chiffres et la structure de la réponse attendue.

### 🗂️ Étape 2 : Choisir un jeu de données ou une analyse

Ouvrez **Jeu de données ou analyse** : chaque entrée a une description en une ligne. Chaque page propose un export général des données, un historique de marché détaillé et deux à quatre analyses, listées dans les guides ci-dessus.

### 🔍 Étape 3 : Définir le niveau de détail

Choisissez **Compact**, **Standard** (par défaut) ou **Complet**. Les trois couvrent les mêmes actifs, indicateurs et période ; ils ne conservent qu'une quantité d'historique plus ou moins importante. **Complet** peut être très long.

### 📅 Étape 4 : Définir la période IA

Choisissez **3M** (par défaut), **6M**, **1A** ou **Personnalisé** (jours, semaines, mois ou années), se terminant à la date d'export. Si LibreFolio dispose de moins d'historique, l'export le signale comme partiel : il n'invente jamais de prix et n'utilise pas de prix futurs.

### 📝 Étape 5 : Ajouter des notes (analyses uniquement)

Avec **Demander une analyse**, ajoutez du contexte ou des questions dans **Notes pour l'IA** : un budget mensuel, une allocation cible, ce qui vous préoccupe. L'IA les lit comme des informations, et non comme de nouvelles règles.

### 📋 Étape 6 : Copier

Sélectionnez **Copier l'export IA**. Après **Préparation de l'export…**, un message confirme la copie avec sa taille estimée.

??? warning "📏 Prompt volumineux — lorsque le texte est long"

    Le panneau affiche d'abord la **Taille finale du prompt** avec un avertissement. Choisissez
    **Utiliser Compact** pour un texte plus court (non affiché en Compact), ou **Copier quand
    même** : les mêmes paramètres copient alors sans demander pendant un moment.

LibreFolio se souvient de vos derniers choix sur chaque page pendant quelques minutes ; la déconnexion les réinitialise.

---

## 🤖 Collez-le dans votre assistant IA

Vous copiez du texte brut : un court en-tête (ce qui a été exporté, la date, la période, la devise et le niveau de détail) et vos données dans des tableaux compacts. **Demander une analyse** ajoute la question et la structure de réponse attendue autour de celles-ci.

1. Ouvrez une nouvelle conversation dans un assistant IA à qui vous confiez des données financières.
2. Collez le texte et envoyez-le. Avec **Demander une analyse**, la question y figure déjà.
3. Répondez aux questions de l'IA : il lui est demandé de ne poser que des questions sur ce qui change le résultat (un budget, un objectif, votre situation fiscale) et de ne jamais le deviner.

Bon à savoir :

- Avec **Demander une analyse**, il est demandé à l'IA de répondre dans la langue de votre interface LibreFolio et de garder vos chiffres séparés de son interprétation.
- Les analyses **Performance et moteurs de marché** nécessitent un assistant capable de faire des recherches sur le web ; sans cela, la réponse le dit au lieu d'inventer des sources.
- Les actifs, courtiers, paires FX et lots apparaissent sous forme de codes courts (A1, B1, F1, L1) expliqués dans le texte ; il est demandé à l'IA de répondre avec les noms réels.
- Une analyse peut suggérer un export supplémentaire sous **Données LibreFolio supplémentaires**, avec l'endroit où le trouver. Si l'IA le demande, copiez aussi cet export et collez-le dans la même conversation.

---

## 🔒 Confidentialité

- LibreFolio n'envoie l'export nulle part : il l'écrit uniquement dans votre presse-papiers.
- Le texte contient vos **chiffres réels** ainsi que les noms de vos courtiers et de vos actifs, même lorsque le mode confidentialité est activé.
- Chaque page n'exporte que son propre périmètre :
    - **Tableau de bord** : les courtiers que vous détenez avec une part supérieure à 0 %, filtrés par le filtre de courtier ;
    - **Courtier** : ce courtier uniquement ;
    - **Actif** et **FX** : tous les courtiers que vous pouvez ouvrir, y compris les courtiers partagés avec vous.
- Relisez le texte avant de le coller où que ce soit ; un rappel apparaît après chaque copie.

---

## 🛠️ En cas de problème

- **Export IA est grisé** : la page est encore en cours de chargement ou, sur le Tableau de bord, vous ne détenez aucun courtier avec une part supérieure à 0 %.
- *Cette sélection n'est pas applicable aux données actuelles.* : choisissez une autre analyse. **Revue de position** nécessite une position sur l'actif ; **Impact d'exposition FX** nécessite des liquidités ou une position liée à la paire.
- Un message se terminant par *Actualisez et réessayez.* : rechargez la page.
- *L'accès au presse-papiers n'est pas disponible. Vérifiez les autorisations du navigateur.* : autorisez l'accès au presse-papiers pour LibreFolio dans votre navigateur.

---

## 🔗 Voir aussi

- 🛠️ **[Comment fonctionne l'export IA](../../developer/architecture/patterns/ai_export_snapshot.md)** — pour les développeurs
