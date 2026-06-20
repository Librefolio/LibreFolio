# 📝 Configuration

LibreFolio utilise un fichier `.env` pour la configuration, propulsé par `BaseSettings` de Pydantic. Cela permet une gestion simplifiée des variables d'environnement, tant pour le développement local que pour les déploiements Docker.

## 📄 Fichier `.env`

Le fichier `.env` se trouve à la racine du projet. Un fichier exemple, `.env.example`, est fourni. Pour commencer, copiez-le simplement :

```bash
cp .env.example .env
```

### 🔑 Variables d'environnement clés

- **`PORT`**: Le port sur lequel le serveur FastAPI sera exécuté.
 - Par défaut : `6040`

- **`TEST_PORT`**: Le port sur lequel le serveur de test sera exécuté lorsque le mode test est activé.
 - Par défaut : `6041`

- **`LIBREFOLIO_DATA_DIR`**: Le chemin du répertoire où sont stockées les données de production (base de données SQLite, logs, uploads).
 - Par défaut : `./backend/data/prod`

- **`JWT_SECRET`**: La clé secrète utilisée pour signer les JWT (JSON Web Tokens) des sessions utilisateurs.
 - **Important** : Cette valeur doit être stable si vous souhaitez empêcher les clients de perdre leurs sessions lors des redémarrages du serveur (ou en cas d'utilisation de plusieurs workers uvicorn). Cependant, pour une sécurité maximale, la laisser vide et permettre son recalcul dynamique à l'exécution est le choix recommandé.

- **`LOG_LEVEL`**: Le niveau de journalisation pour l'application.
 - Options : `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
 - Par défaut : `INFO`

- **`PORTFOLIO_BASE_CURRENCY`**: La devise de base par défaut pour les calculs du portefeuille.
 - Par défaut : `EUR`

- **`PREVIEW_CACHE_MAX_MB`**: Taille maximale (en MB) du cache d'aperçu d'images en mémoire.
 - Par défaut : `50`
 - Les miniatures mises en cache sont évincées via LRU lorsque la limite est atteinte.

- **`BACKEND_CORS_ORIGINS`**: Une liste JSON des origines CORS autorisées pour le développement.
 - Par défaut : `["http://localhost:3000", "http://localhost:5173"]`

- **`LIBREFOLIO_TEST_MODE`**: Un indicateur pour préciser si l'application s'exécute en mode test (forçant l'isolation via la base de données de test).
 - Réglez sur `1` pour activer le mode test.

## 🔝 Priorité de résolution

Lors de la résolution des variables de configuration, LibreFolio respecte un ordre de priorité allant du plus bas (valeurs par défaut du code) au plus haut (surcharges Docker Compose). Pour un plan et un diagramme détaillés des priorités, consultez la [Section Priorité de Résolution Docker](docker_advanced.md#resolution-priority).

## 📂 Séparation des données

LibreFolio utilise des répertoires de données distincts pour la production et les tests :

- **Production** : `backend/data/prod/` (sqlite, custom-uploads, broker_reports, logs)
- **Test** : `backend/data/test/` (même structure, complètement isolée)

La fonction `get_data_dir()` dans `config.py` sélectionne automatiquement le chemin correct en fonction de `LIBREFOLIO_TEST_MODE`.

## ⚙️ Fonctionnement

Les paramètres sont chargés dans une classe Pydantic `Settings` située dans `backend/app/config.py`. Cette classe lit automatiquement les variables du fichier `.env` et valide leurs types.

Cette approche offre :

- **Sécurité des types** : Les paramètres sont validés au démarrage de l'application.
- **Configuration centralisée** : Tous les paramètres sont définis en un seul endroit.
- **Flexibilité** : Les paramètres peuvent être fournis via un fichier `.env` ou comme variables d'environnement réelles, facilitant la configuration dans différents environnements (local, Docker, etc.).
