# 📝 Configuration

LibreFolio utilise un fichier `.env` pour la configuration, propulsé par `BaseSettings` de Pydantic. Cela permet une gestion simplifiée des variables d'environnement, tant pour le développement local que pour les déploiements Docker.

## 🔧 Démarrage Rapide : Initialiser la Configuration

Le fichier `.env` se trouve à la racine du projet. Un fichier exemple, `.env.example`, est fourni. Pour commencer, copiez-le simplement :

```bash
cp .env.example .env
```

## ✏️ Options de Configuration (Fichier `.env`)

Ces variables permettent de personnaliser le comportement de LibreFolio dans le fichier `.env`. Ce sont les mêmes variables chargées par défaut par Docker Compose.

- **`PORT`** (Par défaut : `6040`) : Le port sur lequel le serveur FastAPI de production sera exécuté.
- **`TEST_PORT`** (Par défaut : `6041`) : Le port sur lequel le serveur de test sera exécuté lorsque le mode test est activé.
- **`LIBREFOLIO_DATA_DIR`** (Par défaut : `./backend/data/prod`) : Le chemin du répertoire racine où sont stockées les données persistantes (base de données SQLite, logs, uploads, etc.). Résolu au niveau du système : les chemins relatifs sont résolus en chemins absolus par rapport à la racine du projet, tandis que dans Docker, cette valeur est surchargée et forcée à `/app/backend/data/prod-docker` via les mappages de volumes de Compose.
- **`LOG_LEVEL`** (Par défaut : `INFO`, Options : `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) : Le niveau de journalisation principal pour l'application.
- **`PORTFOLIO_BASE_CURRENCY`** (Par défaut : `EUR`) : La devise de base par défaut pour les calculs du portefeuille (code ISO 4217).
- **`PREVIEW_CACHE_MAX_MB`** (Par défaut : `50`) : Taille maximale (en MB) du cache d'aperçu d'images en mémoire. Les miniatures mises en cache sont évincées via l'algorithme LRU lorsque la limite est atteinte.

## 💻 Paramètres Système (Variables d'Environnement)

Ces variables gèrent l'intégration de bas niveau entre les modules de l'application, l'isolation des tests et les scripts CLI de développement. En règle générale, l'utilisateur n'a pas besoin de les modifier directement, car le système (Docker Compose ou le script `dev.py`) les affecte ou les gère automatiquement.

- **`HOST`** (Par défaut : `0.0.0.0`) : L'adresse de liaison réseau (bind address) pour le serveur web FastAPI, injectée automatiquement dans Docker et les commandes CLI.
- **`JWT_SECRET`** : La clé secrète utilisée pour signer et décoder les sessions utilisateurs (JSON Web Tokens). Cette variable ne fait **pas** partie de la validation Pydantic `Settings` et est lue à l'exécution directement à partir de l'environnement du système d'exploitation. Si elle est laissée vide, l'application auto-affecte une clé aléatoire sécurisée à chaque démarrage (`secrets.token_urlsafe(64)`). Lors du démarrage du serveur local via `./dev.py server`, le script génère et injecte automatiquement un secret partagé pour garantir la persistance des sessions entre les processus de travail.
- **`LIBREFOLIO_TEST_MODE`** : Un indicateur pour préciser si l'application s'exécute en mode test. Lorsqu'il est défini sur `1` ou `true`, il force l'application à s'isoler complètement en redirigeant le répertoire de données vers `backend/data/test/`. Ceci est géré automatiquement par les exécuteurs de tests.
- **`LIBREFOLIO_LOG_LEVEL`** : Surcharge de priorité pour le niveau de journalisation. S'il est défini, il a la priorité absolue et remplace à l'exécution la propriété `LOG_LEVEL` chargée par Pydantic (utilisé par `./dev.py server --debug`).

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
