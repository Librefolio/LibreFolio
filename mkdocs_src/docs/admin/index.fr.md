# 🛡️ Manuel d'administration

Ce manuel s'adresse aux administrateurs système et aux utilisateurs avancés qui doivent effectuer de la maintenance, gérer des utilisateurs ou interagir avec le système via la ligne de commande.

## 📖 Vue d'ensemble

La plupart des tâches administratives sont gérées via l'outil CLI principal :

1. **`dev.py`** : Le script d'orchestration principal pour le développement et la maintenance. Il fournit une CLI en arborescence pour toutes les tâches : exécution des tests, gestion de la base de données, construction du frontend, gestion des utilisateurs, traductions, et bien plus encore.

## 📚 Guides

- 🛠️ **[Outils CLI](cli_tools.md)** : Documentation détaillée des commandes et sous-commandes de `dev.py`.
- ⚙️ **[Paramètres globaux](settings.md)** : Configuration des paramètres globaux (durée de vie de session, limites de téléversement, intervalles de synchronisation, valeurs par défaut).
- 📂 **[Structure du système de fichiers](filesystem.md)** : Structure du système de fichiers : emplacement des données, sauvegarde et accès depuis le terminal hôte.
- 🐳 **[Docker avancé](docker_advanced.md)** : Exploration approfondie de la configuration Docker, incluant le réseau, les volumes et la personnalisation pour les environnements de production.
- 🌐 **[Exposition avec Tailscale](tailscale_exposure.md)** : Exposition sécurisée de votre instance LibreFolio sur Internet en utilisant Tailscale.

## 🔐 Authentification

LibreFolio utilise **JWT (JSON Web Tokens)** pour l'authentification. Le serveur génère un secret de signature aléatoire au démarrage, partagé entre tous les workers. Les jetons expirent après un nombre configurable d'heures (voir [Paramètres globaux](settings.md)). Pour les détails techniques, voir [Architecture de sécurité](../developer/architecture/security.md).
