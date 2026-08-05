# 🧠 Export IA d'actif

L'export IA de détail d'actif prépare un instantané dans le presse-papiers ou une invite d'analyse ciblée
pour l'actif actuellement ouvert. LibreFolio ne l'envoie jamais à un service d'IA.

## 📍 Emplacement

Ouvrez une page de détail d'actif. Dans l'en-tête **Signaux**, sélectionnez **Export IA**. Votre
brouillon reste disponible pendant 10 minutes dans la session de connexion actuelle et se réinitialise
après une déconnexion ou une nouvelle connexion.

## 🎯 Analyses d'actifs

| Tâche | Focus |
| ------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Examen de position** | Taille de position, base de coût, performance, revenus et concentration. |
| **Analyse de marché d'actif** | Historique des clôtures observées, rendements, tendance, momentum, volatilité, Drawdown, états, événements et couverture. |

## 🗂️ Portée et données

L'export utilise l'actif actuel, la plage de dates sélectionnée, la devise d'affichage/cible,
et le périmètre de courtier accessible à l'utilisateur lorsqu'un contexte de portefeuille est requis.
Selon la sélection, il peut inclure des identifiants, des prix, des rendements, une valorisation,
des faits de position et FIFO, des revenus, des événements d'entreprise et des résultats techniques
calculés par le backend. Le navigateur ne recalcule pas les indicateurs.

## 📤 Export de données et demande d'analyse

- **Exporter les données** copie un ensemble de données d'actif factuel sélectionné sans instructions
 d'analyse ni interprétation.
- **Demander une analyse** utilise les faits pertinents et ajoute des instructions spécifiques à la tâche
 ainsi qu'un contrat de réponse pour que l'IA réceptrice puisse les interpréter. La langue de réponse
 demandée suit la langue d'interface actuelle de LibreFolio.
- Des notes facultatives sont incluses uniquement lorsqu'elles sont prises en charge par l'Analyse sélectionnée.

Deux exports de données publics sont disponibles :

- **Position d'actif et historique** — positions par courtier, coût, valeur, P&L,
 sémantique des périodes à zéro enregistré, lots économiques avec frais/taxes alloués, historique
 de marché compact, Drawdown et provenance ;
- **Historique de marché d'actif** — compartiments de clôtures observées, rendements, indicateurs, états,
 événements, Drawdown et couverture.

## 📏 Détail et échantillonnage

| Détail | Échantillonnage exact |
| ------------ | --------------------------------------------------------------------------------------------------------------------- |
| **Compact** | Export de position : jusqu'à 8 points uniformes d'historique observé. Export de marché : jusqu'à 5 lignes d'indicateurs non vides par Signal. |
| **Standard** | Export de position : jusqu'à 16 points. Export de marché : jusqu'à 10 lignes d'indicateurs. |
| **Complet** | Export de position : jusqu'à 30 points. Export de marché : tous les compartiments d'indicateurs non vides ; l'export peut être volumineux. |

Un ensemble de données ou une Analyse peut omettre les sections facultatives indisponibles ou non applicables.
La **période IA** se termine à la date de l'instantané. Les dates disponibles, la couverture, le Signal
partiel et les raisons d'omission restent explicites.

## 🔒 Applicabilité, erreurs et confidentialité

L'examen de position nécessite un contexte de position. D'autres tâches peuvent être désactivées lorsque
les faits requis sont absents. Les incompatibilités de catalogue et de contrat de réponse échouent en mode fermé.
Les erreurs typées signalent l'applicabilité, les entités manquantes, les échecs de source ou les
problèmes de contrat.

Le presse-papiers peut contenir des données sensibles de positions et de performance. Examinez-les avant
de les partager. Consultez l'[aperçu de l'export IA](index.md) pour
le flux de travail inter-domaines et le modèle de sécurité.
