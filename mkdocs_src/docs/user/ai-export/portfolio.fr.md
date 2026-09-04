# 🧠 Export IA du portefeuille

L'export IA du portefeuille prépare un instantané du presse-papiers limité au tableau de bord ou une invite d'analyse
ciblée. LibreFolio n'envoie jamais l'export à un service IA.

## 📍 Emplacement

Ouvrez le **Tableau de bord** et sélectionnez **Export IA** dans la barre d'outils supérieure, à côté de
**Actualiser**. Le brouillon reste disponible pendant 10 minutes dans la session de connexion en cours
et se réinitialise après une déconnexion ou une nouvelle connexion.

## 🎯 Analyses du portefeuille

| Tâche | Objectif |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Plan d'investissement récurrent** | Structure du portefeuille, flux de trésorerie, contraintes et contexte d'investissement récurrent. |
| **Rééquilibrage du portefeuille** | Allocation actuelle, concentration, diversification et contexte d'allocation cible. |
| **Performance du portefeuille et facteurs de marché** | Rapprochement de la performance et recherches datées à horizon court et long pour chaque actif détenu. |
| **Stratégies de compensation des pertes en capital** | Moyens conditionnels d'utiliser les pertes fiscales disponibles ou arrivant à expiration contre des gains potentiellement éligibles, en utilisant les preuves économiques FIFO et l'inventaire officiel des pertes fiscales de l'utilisateur. |

## 🗂️ Portée et données

L'export respecte le filtre de courtier actif, la plage de dates et la devise cible.
Selon la sélection, il peut inclure les totaux du portefeuille, la trésorerie, les positions,
les allocations, la performance, les contributions, les revenus, le contexte de qualité des données et
les résultats techniques calculés par le backend.

L'invite distingue :

- Les courtiers inclus dans le périmètre de calcul ;
- Les courtiers ayant des positions actuellement ouvertes ;
- Les courtiers représentés par les contributeurs à la performance sur la période IA.

Un courtier inclus dans le périmètre peut ne pas avoir de position actuelle. Les références B# restent cohérentes avec
l'annuaire des entités.

!!! note "Le FIFO économique n'est pas un traitement fiscal légal"

    L'export général contient un résumé FIFO économique compact par actif.
    **Stratégies de compensation des pertes en capital** reçoit en plus chaque lot applicable.
    Avant de comparer les scénarios sans action, de réalisation de gains, échelonnés ou de récolte de pertes,
    l'invite demande la résidence fiscale, le régime fiscal, le type de compte, l'inventaire officiel des pertes fiscales
    (par exemple le `cassetto fiscale` italien), la catégorie légale,
    les montants restants et utilisés, les dates d'origine/d'expiration, les règles de compensation et les contraintes.

## 📤 Export des données et demande d'analyse

- **Export des données** copie un ensemble de données factuel du portefeuille sans instructions d'analyse
 ni contrat de réponse.
- **Demander une analyse** ajoute des instructions spécifiques à la tâche, un contrat de réponse et
 les ensembles de données déclarés pour l'analyse sélectionnée.
 La langue de réponse demandée suit toujours la langue actuelle de l'interface
 LibreFolio.
- Les notes facultatives ne sont incluses que pour les analyses qui les prennent en charge.

Deux exports de données publics sont disponibles :

- **Aperçu et historique du portefeuille** — positions, trésorerie, allocations, concentration,
 trajectoire de performance, flux, revenus, coûts, rapprochement, résumé FIFO économique,
 historique compact par actif, Drawdown, couverture et provenance ;
- **Historique des actifs du portefeuille** — compartiments plus denses de prix de clôture observés, indicateurs,
 états, événements, couverture et largeur pour l'univers d'actifs éligibles.

## 📅 Plan d'investissement récurrent

L'analyse utilise d'abord les faits fournis et ne demande que les préférences manquantes qui
modifient significativement le plan. Les questions sont regroupées en :

- capital et fréquence de contribution ;
- objectifs et horizon ;
- préférences de risque, y compris la volatilité acceptable ou un Drawdown temporaire ;
- contraintes opérationnelles telles que la liquidité, les courtiers, les ordres minimaux, les exclusions,
 ou si les ventes sont autorisées.

L'invite distingue les réponses indispensables des affinements facultatifs et peut
encore proposer des scénarios conditionnels. Elle n'invente jamais le budget, les objectifs ni la
tolérance au risque.

Elle compare le déploiement immédiat et échelonné. L'attente conditionnelle n'apparaît que
lorsqu'il existe des preuves étendues et persistantes de baisse dans l'ensemble du portefeuille, jamais
à partir d'un seul actif ou d'un seul indicateur.

Le Drawdown du portefeuille et une comparaison compacte du Drawdown par actif ne constituent qu'un contexte
historique. Ils ne sont ni des prévisions ni des signaux d'achat autonomes, et aucun historique de Drawdown
par actif n'est ajouté.

## 📰 Performance et facteurs de marché

L'IA destinataire est chargée de couvrir chaque actif détenu, de citer des sources datées,
d'évaluer la qualité des sources, de fournir des thèses à horizon court et long, de distinguer
la chronologie/corrélation de la causalité et d'étiqueter les liens comme étayés, plausibles,
inférés, spéculatifs ou inexpliqués.

## 📏 Niveau de détail et échantillonnage

| Détail | Échantillonnage exact |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Compact** | Export général : 8 points de trajectoire du portefeuille et jusqu'à 6 points par actif éligible. Export détaillé : jusqu'à 5 lignes d'indicateurs non vides par actif/signal. |
| **Standard** | Export général : 16 points de trajectoire du portefeuille et jusqu'à 12 points par actif éligible. Export détaillé : jusqu'à 10 lignes d'indicateurs. |
| **Complet** | Export général : 30 points de trajectoire du portefeuille et jusqu'à 24 points par actif éligible. Export détaillé : chaque compartiment d'indicateurs non vide ; cela peut être très volumineux. |

Un ensemble de données ou une analyse peut omettre les sections facultatives indisponibles ou non applicables.
La **période IA** utilise 3M, 6M, 1Y ou Personnalisée lorsque cette option est proposée et se termine toujours à la
date de l'instantané. Les lignes temporelles entièrement vides sont omises, tandis que les métadonnées de période/couverture
et les valeurs nulles observées restent.

## 🔒 Applicabilité, erreurs et confidentialité

Les tâches ou les choix de détail indisponibles restent désactivés. L'export IA échoue également en mode sécurisé
lorsque les catalogues du navigateur et du serveur ou les contrats de réponse ne correspondent pas. Des erreurs
typées expliquent l'applicabilité manquante, les entités inaccessibles, les échecs de source
ou les problèmes de contrat sans exposer les détails internes.

Le presse-papiers peut contenir des données financières sensibles. Vérifiez-le avant de le coller
dans un service tiers. Consultez l'[aperçu de l'export IA](index.md)
pour le flux de travail inter-domaines et le modèle de sécurité.
