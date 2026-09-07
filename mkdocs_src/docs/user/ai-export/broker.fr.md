# 🧠 Export IA du courtier

L'Export IA du courtier prépare un instantané de presse-papiers ou une invite
d'analyse limitée à un courtier accessible. LibreFolio ne l'envoie jamais à un
service d'IA.

## 📍 Emplacement

Ouvrez une page de détail du courtier et sélectionnez **Export IA** dans la barre
d'outils supérieure. Le brouillon reste disponible pendant 10 minutes dans la
session de connexion en cours et se réinitialise après une déconnexion ou une
nouvelle connexion.

## 🎯 Analyses du courtier

| Tâche | Focus |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **Revue du courtier** | Positions, liquidités, activité, performance et couverture des données. |
| **Performance du courtier et moteurs de marché** | Rapprochement des performances plus recherche datée pour chaque actif détenu via le courtier. |
| **Stratégies de compensation des pertes en capital** | Moyens conditionnels d'utiliser les pertes fiscales disponibles ou expirantes contre des gains potentiellement éligibles en utilisant les preuves FIFO économiques du courtier sélectionné. |

## 🗂️ Portée et données

L'export est limité au courtier sélectionné ainsi qu'à la période et à la devise
cible actuelles. Selon la sélection, il peut inclure les soldes de trésorerie,
les positions, les transactions, la performance, les coûts, l'allocation, la
concentration, les revenus et les résumés de lots FIFO. Les contrôles d'accès
côté serveur empêchent l'exportation d'un courtier que l'utilisateur actuel ne
peut pas lire.

!!! important "Les coûts alloués et non alloués restent distincts"

    Les lignes FIFO contiennent uniquement les frais et taxes alloués de manière
    déterministe aux lots. Les coûts non alloués au niveau du courtier restent
    dans les preuves financières générales et ne sont jamais présentés comme des
    coûts de lot nuls.

## 📤 Données d'export et demande d'analyse

- **Exporter les données** copie un seul ensemble de données factuel du courtier.
- **Demander une analyse** ajoute des instructions spécifiques à la tâche, un
 contrat de réponse et les ensembles de données déclarés pour l'Analyse.
 La langue de réponse demandée suit la langue actuelle de l'interface
 LibreFolio.
- Les notes optionnelles sont incluses uniquement lorsque l'Analyse sélectionnée
 les prend en charge.

Deux exports de données publics sont disponibles :

- **Vue d'ensemble et historique du courtier** — positions du courtier
 sélectionné, liquidités, concentration, trajectoire de performance, flux,
 coûts, ratios, résumé FIFO économique, historique compact par actif,
 Drawdown, couverture et provenance ;
- **Historique des actifs du courtier** — compartiments de prix de clôture
 observés limités au courtier, indicateurs, états, événements, largeur et
 raisons explicites pour les actifs actuels exclus de l'éligibilité technique.

## 🧾 Stratégies de compensation des pertes en capital

L'invite utilise les lots FIFO économiques du courtier sélectionné pour
identifier les candidats conditionnels aux gains et aux pertes, mais ne les
traite jamais automatiquement comme légalement éligibles. Elle demande d'abord
la résidence fiscale, le régime, le type de compte, l'inventaire officiel des
pertes fiscales, les montants par catégorie légale, les dates d'origine et
d'expiration, les soldes déjà utilisés, les règles de compensation, et si les
soldes entre courtiers/comptes peuvent être combinés.

Elle peut ensuite comparer l'absence d'action, la réalisation de gains éligibles
avant expiration, la réalisation échelonnée alignée sur le rééquilibrage, et la
récolte de pertes lorsque cela est pertinent. Chaque voie montre les coûts, les
changements d'exposition, la liquidité, la concentration, le moment et
l'incertitude juridique ; aucune transaction n'est recommandée uniquement pour
des raisons fiscales.

## 📏 Niveau de détail et échantillonnage

| Détail | Échantillonnage exact |
| ------------ | --------------------------------------------------------------------------------------- |
| **Compact** | Même univers de données avec les compartiments temporels les plus espacés pris en charge (jusqu'à 30 jours). |
| **Standard** | Même univers de données avec des compartiments temporels jusqu'à 14 jours. |
| **Complet** | Même univers de données avec des compartiments temporels jusqu'à 7 jours. |

L'export général utilise 8/16/30 points de trajectoire du courtier et jusqu'à
6/12/24 points d'historique compact par actif éligible. L'export détaillé
conserve la politique complète d'échantillonnage technique et peut être
volumineux.

Un ensemble de données ou une Analyse peut omettre les sections optionnelles
indisponibles ou non applicables. La **période IA** se termine à la date de
l'instantané. L'historique partiel et la couverture restent explicites.

## 🔒 Applicabilité, erreurs et confidentialité

Les Analyses peuvent être indisponibles lorsque les faits requis n'existent pas.
Les choix échouent également en mode sécurisé (fail closed) en cas
d'inadéquation de catalogue ou de contrat. Des erreurs typées signalent des
problèmes d'accès, d'applicabilité, de source ou de contrat.

Le presse-papiers peut contenir des données sensibles de compte et de
transaction. Révisez-le avant de le partager. Voir la
[vue d'ensemble de l'Export IA](index.md) pour le flux de travail inter-domaines
et le modèle de sécurité.
