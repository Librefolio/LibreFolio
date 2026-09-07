# 🧠 Export IA FX

L'export IA des détails FX prépare un instantané du presse-papiers ou une invite d'analyse ciblée pour
la paire de devises canonique actuellement ouverte. LibreFolio ne l'envoie jamais à un service
d'IA.

## 📍 Emplacement

Ouvrez une page de détails FX. Dans la **barre d'outils de la page**, sélectionnez **Export IA**. Votre
brouillon reste disponible pendant 10 minutes dans la session de connexion actuelle et se réinitialise
après la déconnexion ou une nouvelle connexion.

## 🎯 Analyses FX

| Tâche | Objectif |
| ---------------------- | ------------------------------------------------------------------------------------------- |
| **Analyse de paire FX** | Direction de la paire, rendements, volatilité, preuves techniques, couverture et contexte macro daté. |
| **Impact de l'exposition FX** | Liquidités directes, devise de transaction et devise de valorisation liées à la paire. |

## 🗂️ Portée et données

L'export utilise la paire canonique de la page, la plage de dates sélectionnée, la devise cible,
l'historique des taux, le contexte du fournisseur et les résultats techniques calculés par le backend.

## 📤 Export des données et demande d'analyse

- **Export des données** copie un seul ensemble de données FX factuel.
- **Demande d'analyse** ajoute des instructions spécifiques à la tâche, un contrat de réponse et
 les ensembles de données déclarés pour l'Analyse.
 La langue de réponse demandée suit la langue actuelle de l'interface LibreFolio.
- Les notes facultatives sont incluses uniquement lorsque l'Analyse sélectionnée les prend en charge.

Deux exports publics de données sont disponibles :

- **Marché FX et exposition** — taux actuel (devise de cotation par devise de base), 8/16/30 points de trajectoire
 observés, tendance/momentum/volatilité ciblés, rendements sur 30 jours et 91 jours, position dans la fourchette,
 couverture des sources, entrées utilisateur manquantes et exposition directe ;
- **Historique du marché FX** — compartiments de taux plus denses, rendements, indicateurs, états, événements
 et couverture.

## 📉 Historique partiel

Lorsque la période IA demandée commence avant l'historique des taux enregistré, LibreFolio exporte
l'historique réel qu'il peut utiliser et signale :

- les dates demandées et disponibles ;
- la couverture ;
- les décomptes observés et complétés rétroactivement ;
- le Signal partiel ;
- le Signal omis et les raisons ;
- les avertissements d'historique insuffisant.

Aucun taux futur n'est utilisé. Un Signal partiel n'est pas présenté comme équivalent à un historique
complet.

## 📏 Détail et échantillonnage

| Détail | Échantillonnage exact |
| ------------ | ------------------------------------------------------------------------------------------------------------------- |
| **Compact** | Export général : jusqu'à 8 points de taux observés uniformément répartis. Export détaillé : jusqu'à 5 lignes d'indicateurs non vides par Signal. |
| **Standard** | Export général : jusqu'à 16 points. Export détaillé : jusqu'à 10 lignes d'indicateurs. |
| **Complet** | Export général : jusqu'à 30 points. Export détaillé : chaque compartiment d'indicateurs non vide ; peut être volumineux. |

Un ensemble de données ou une Analyse peut omettre les sections facultatives indisponibles ou non applicables.
La **période IA** se termine à la date de l'instantané.

## 🔒 Applicabilité, erreurs et confidentialité

Des analyses ou des choix de détail peuvent être désactivés lorsque les données requises sont absentes. Les discordances
entre le catalogue et le contrat de réponse échouent en mode fermé. Les erreurs typées signalent des problèmes
d'applicabilité, de source, d'entité ou de contrat.

Le presse-papiers peut contenir des données sensibles de devises et d'exposition de portefeuille. Vérifiez-le
avant de le partager. Voir l'[aperçu de l'export IA](index.md) pour
le flux de travail inter-domaines et le modèle de sécurité.
