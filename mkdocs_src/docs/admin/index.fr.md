# 🛡️ Manuel Admin

Ce manuel est destiné aux administrateurs système et aux utilisateurs avancés qui ont besoin d'effectuer la maintenance, de gérer les utilisateurs ou d'interagir avec le système via la ligne de commande.

## 📖 Aperçu

La plupart des tâches d'administration et de maintenance sont gérées via l'interface en ligne de commande principale ou configurées via des variables d'environnement.

---

## 📚 Guides

La documentation est organisée en trois domaines principaux :

### 🐳 Déploiement & Exposition
- 📦 **[Installation sur l'Hôte](host_installation.md)** : Configuration manuelle avec Python, Node.js et Pipenv directement sur la machine hôte.
- 🐳 **[Docker Avancé](docker_advanced.md)** : Déploiement conteneurisé à l'aide de Docker Compose, liaisons de volumes et configuration de la propriété GID/UID de l'utilisateur.
- 🌐 **[Exposer en Sécurité](service_exposure.md)** : Exposez en toute sécurité votre instance privée de LibreFolio sur Internet.

### ⚙️ Configuration du Système
- 📝 **[Variables d'Environnement](configuration.md)** : Liste complète des variables `.env` prises en charge (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, etc.) et ordre de priorité de résolution.
- ⚙️ **[Paramètres Globaux](settings.md)** : Configurez les paramètres d'exécution à l'échelle du système (TTL de session, limites de téléchargement, intervalles de synchronisation des données de marché).

### 🧹 Maintenance & Opérations
- 🛠️ **[Outils CLI Admin](cli_tools.md)** : Comment utiliser le script `dev.py` pour les tâches administratives (gestion des utilisateurs, mises à niveau de la base de données).
- 📂 **[Structure du Système de Fichiers](filesystem.md)** : Détails sur l'emplacement de stockage des bases de données, des journaux, des téléchargements et des dossiers temporaires, et sur la manière d'effectuer des sauvegardes.

---

## 🔐 Authentification & Persistance des Sessions

LibreFolio utilise des **JWT (JSON Web Tokens)** pour l'authentification des utilisateurs. Par défaut :
- Si la variable d'environnement **`JWT_SECRET`** est laissée vide dans votre fichier `.env`, le serveur génère un secret de signature aléatoire au démarrage. Cela offre une sécurité maximale, mais les sessions utilisateur seront perdues si le serveur est redémarré.
- Pour persister les sessions entre les redémarrages du serveur (ou lors de l'exécution de plusieurs instances de serveur indépendantes derrière un répartiteur de charge), définissez une clé **`JWT_SECRET`** stable. Notez que plusieurs processus de travail uvicorn démarrés sur le même hôte partageront automatiquement le secret généré par le processus parent, ce qui signifie que la persistance de session entre les processus de travail est maintenue même lorsque `JWT_SECRET` est laissé vide.

Pour les détails techniques, consultez la page consacrée à la [Sécurité et Authentification](../developer/architecture/security.md) dans le manuel du développeur.
