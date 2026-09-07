# 🧠 Export IA

L'Export IA transforme le contexte LibreFolio actuel en texte structuré que vous
pouvez coller dans un assistant IA ou conserver comme instantané portable.

!!! important "Export vers le presse-papiers uniquement"

    LibreFolio ne contacte **pas** un service d'IA. Il génère l'instantané
    financier et technique sur votre serveur, l'affiche dans votre navigateur et
    le copie dans le presse-papiers. Vous choisissez si et où le coller.

## 📋 Ce qu'il fait

L'Export IA est disponible depuis :

- la barre d'outils du Tableau de bord pour les tâches de portefeuille ;
- la barre d'outils du Courtier pour les tâches de courtier ;
- la barre d'outils de la page sur les pages de détail Actif et FX.

Le backend fournit les valorisations, la performance, les allocations, les
données économiques FIFO, l'exposition FX et les indicateurs techniques. Le
catalogue public n'expose volontairement que **huit choix autonomes d'Export de
données** et **onze Analyses orientées vers les tâches**. Les jeux de données
backend plus petits restent des blocs de composition internes.

**Export de données** copie un instantané factuel sélectionné sans instructions
d'analyse. **Demande d'analyse** ajoute un objectif et un contrat de réponse à
un instantané autonome, ainsi qu'une suggestion d'export public complémentaire
lorsque cela est utile. Les notes facultatives et la langue de réponse demandée
ne s'appliquent qu'aux analyses.

## 🚀 Comment l'utiliser

1. Ouvrez la page Portefeuille, Courtier, Actif ou FX concernée.
2. Sélectionnez **Export IA** (:material-brain:).
3. Choisissez **Export de données** ou **Demande d'analyse**, puis sélectionnez
 un jeu de données ou une Analyse.
4. Choisissez la période IA et le niveau de détail.
5. Pour une analyse, ajoutez des notes facultatives lorsque l'Analyse les prend
 en charge.
6. Sélectionnez **Copier l'export IA**, puis collez le résultat dans l'outil de
 votre choix.

## 🎛️ Options d'export

| Option | Description |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type d'export** | **Export de données** crée un prompt contenant un jeu de données factuel. **Demande d'analyse** ajoute l'objectif de l'Analyse, les instructions de vérification, le contrat de réponse et les jeux de données pertinents. |
| **Jeu de données ou analyse** | Les choix disponibles proviennent du catalogue runtime LibreFolio actuel pour la page/le domaine. |
| **Période IA** | **3M**, **6M**, **1Y** ou Personnalisée lorsque proposée. La période se termine à la date de l'instantané. L'historique source partiel reste explicite. |
| **Niveau de détail** | **Compact**, **Standard** et **Complet** conservent le même univers d'entités. Les instantanés généraux utilisent des mini-histoires uniformes de plus en plus denses ; les exports de marché détaillés utilisent la politique d'échantillonnage technique complète. Complet peut être volumineux et n'est pas toujours nécessaire. |
| **Notes pour l'IA** | Disponible pour les analyses prises en charge. Ajoute un contexte utilisateur facultatif sous forme de bloc de données sérialisé en toute sécurité. |

Le brouillon d'export (type d'export, sélection, détail, période IA et notes)
reste en mémoire du navigateur pendant 10 minutes par contexte de page. Fermer
le panneau ou naviguer ailleurs le conserve dans cette fenêtre. L'expiration du
délai, la déconnexion ou toute nouvelle connexion réinitialise chaque panneau
d'Export IA à ses valeurs par défaut ; les brouillons ne sont pas persistés
dans `localStorage`.

## 📤 Données d'export disponibles

| Page | Instantané général | Historique de marché détaillé |
| --------------- | ---------------------------------------- | --------------------------------- |
| Tableau de bord | **Aperçu et historique du portefeuille** | **Historique des actifs du portefeuille** |
| Courtier | **Aperçu et historique du courtier** | **Historique des actifs du courtier** |
| Actif | **Position et historique de marché (complet)** | **Historique de marché uniquement (sans positions)** |
| FX | **Marché FX et exposition** | **Historique du marché FX** |

Les instantanés généraux combinent les données économiques actuelles avec une
trajectoire historique compacte et un contexte de marché ciblé. Les historiques
de marché détaillés contiennent des prix ou taux observés plus denses, des
indicateurs, des états, des événements et une couverture.

## 🗂️ Analyses disponibles

### 📊 Portefeuille

| Tâche | Objectif |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Plan d'investissement récurrent | Examiner la structure du portefeuille, les flux de trésorerie et les contraintes pour les investissements récurrents. |
| Rééquilibrage du portefeuille | Comparer l'allocation actuelle avec le contexte de diversification et d'allocation cible. |
| Performance du portefeuille et facteurs de marché | Rapprocher la performance, puis rechercher les facteurs datés à court et à long horizon pour chaque actif détenu sans exagérer la causalité. |
| Stratégies de compensation des pertes en capital | Explorer comment les pertes fiscales disponibles ou arrivant à expiration pourraient compenser les gains éligibles à l'aide des données économiques FIFO et d'un inventaire officiel explicite des pertes fiscales. |

### 🏦 Courtier

| Tâche | Objectif |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Revue du courtier | Résumer les positions, la trésorerie, l'activité, la performance et la couverture des données pour un courtier. |
| Performance du courtier et facteurs de marché | Rapprocher la performance du courtier sélectionné et rechercher les facteurs datés pour chaque actif détenu. |
| Stratégies de compensation des pertes en capital | Explorer les pistes de compensation des pertes fiscales à l'aide des données économiques FIFO du courtier sélectionné et de l'inventaire officiel des pertes fiscales de l'utilisateur. |

### 📈 Actif

| Tâche | Objectif |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Revue de position | Examiner la taille, le prix de revient, la performance, les revenus et le contexte de concentration. |
| Analyse de marché de l'actif | Examiner l'historique des clôtures observées, les rendements, la tendance, le momentum, la volatilité, le Drawdown, les états, les événements et la couverture. |

### 💱 FX

| Tâche | Objectif |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Analyse de paire FX | Examiner la direction de la paire, les rendements, la volatilité, les éléments techniques, la couverture et le contexte macroéconomique daté. |
| Impact de l'exposition FX | Examiner les liens directs de trésorerie, de devise de négociation et de devise de valorisation avec la paire. |

Les analyses qui comparent des trajectoires futures utilisent une **Thèse de
scénario** : éléments probants fournis, hypothèses, horizon, compromis,
conditions de déclenchement, conditions d'invalidation et décisions utilisateur
manquantes. Elle est obligatoire pour les scénarios PAC, de rééquilibrage et de
compensation des pertes en capital.

## 🧩 Historique partiel et données supplémentaires

LibreFolio peut exporter l'historique réellement disponible lorsqu'il est plus
court que la période IA demandée. Le prompt affiche les dates
demandées/disponibles, la couverture, les avertissements et tout Signal partiel
ou omis. Il n'utilise jamais de prix ou de taux futurs.

Une Analyse peut recommander des **Données LibreFolio supplémentaires**
lorsqu'un autre export améliorerait sensiblement la réponse. Le prompt indique
le nom public de l'export, le chemin dans l'interface, la période/le détail
recommandés, la raison et si ces données sont requises ou facultatives.

!!! info "Le Drawdown porte toujours sur tout l'historique"

    Partout où une section Drawdown apparaît dans un export, elle est calculée sur
    **tout l'historique disponible** — depuis le premier prix enregistré pour un
    Actif, ou depuis la première transaction pour un Portefeuille ou un Courtier —
    jamais par rapport à la période IA sélectionnée. Une courte fenêtre d'export
    contient tout de même le véritable sommet-creux historique.

## 🔗 Références locales

Le prompt utilise des références locales pour relier les tableaux compacts :

- A# pour les actifs ;
- B# pour les courtiers ;
- F# pour les paires FX ;
- L# pour les lots FIFO.

Le Répertoire d'entités résout les références A#, B# et F#. Les lots L# sont
différents : ce sont des **lignes intégrées** dans les tableaux FIFO de l'export
lui-même, pas des entrées du répertoire — le modèle les lit sur place. Le modèle
destinataire doit utiliser des noms lisibles dans sa réponse ; les identifiants de
base de données ne sont pas nécessaires.

## 🔒 Portée et confidentialité

- Les exports de portefeuille suivent le filtre de courtier actif, la plage de
 dates et la devise cible.
- Les exports de courtier ne contiennent que le courtier sélectionné et
 nécessitent d'y avoir accès.
- Les exports d'actif et de FX utilisent l'entité actuelle, la plage
 sélectionnée, la devise cible et le périmètre de courtiers accessible à
 l'utilisateur lorsque le contexte de portefeuille est nécessaire.
- Le texte du presse-papiers peut contenir des données financières sensibles.
 Examinez-le avant de le partager ou de le coller dans un service tiers.

## ⚠️ Disponibilité et sécurité

L'Export IA échoue en se fermant par défaut si les catalogues ou les contrats de
réponse du navigateur et du serveur ne correspondent pas. Une option peut
également être indisponible lorsque ses données ne s'appliquent pas — par
exemple, une Revue de position sans position ouverte ou un Impact de l'exposition
FX sans exposition liée directe.

L'export fournit un contexte factuel, et non des conseils en investissement ou
des instructions de trading automatisé.

## 🔗 Pages associées

- [Export IA du portefeuille](portfolio.md)
- [Export IA du courtier](broker.md)
- [Export IA de l'actif](asset.md)
- [Export IA FX](fx.md)
