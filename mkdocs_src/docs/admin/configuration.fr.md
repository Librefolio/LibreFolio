# 📝 Configuration

LibreFolio utilise un fichier `.env` pour la configuration, basé sur `BaseSettings` de Pydantic. Cela permet une gestion facile des variables d'environnement pour le développement local et les déploiements Docker.

## 🔧 Démarrage rapide : Initialiser la configuration

Le fichier `.env` se trouve à la racine du projet. Un exemple de fichier, `.env.example`, est fourni. Pour commencer, copiez-le simplement :

```bash
cp .env.example .env
```

## ✏️ Options de configuration (Fichier `.env`)

Ces variables vous permettent de personnaliser le comportement de LibreFolio dans le fichier `.env`. Ce sont les mêmes variables chargées par défaut par Docker Compose.

| Variable | Par défaut | Description |
| --- | --- | --- |
| `PORT` | `6040` | Le port sur lequel le serveur FastAPI de production s'exécutera. |
| `TEST_PORT` | `6041` | Le port sur lequel le serveur de test s'exécutera lorsque le mode de test est activé. |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Le chemin du répertoire racine où sont stockées les données persistantes (base de données SQLite, téléversements, journaux, etc.). Résolu au niveau système : les chemins relatifs sont résolus en absolus par rapport à la racine du projet, tandis que dans Docker il est remplacé et forcé à `/app/backend/data/prod-docker` via le mappage de volume Compose. |
| `LOG_LEVEL` | `INFO` | Le niveau de journalisation principal de l'application. Options : `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `PORTFOLIO_BASE_CURRENCY` | `EUR` | La devise de référence par défaut pour les calculs du portefeuille (code ISO 4217). |
| `PREVIEW_CACHE_MAX_MB` | `50` | Taille maximale (en Mo) du cache de prévisualisation d'images en mémoire. Les vignettes en cache sont expulsées selon l'algorithme LRU lorsque la limite est atteinte. |

## 💻 Paramètres système (Variables d'environnement)

Ces variables gèrent l'intégration de bas niveau entre les modules de l'application, l'isolement des tests et les scripts CLI de développement. Généralement, l'utilisateur n'a pas besoin de les modifier directement, car le système (Docker Compose ou le script `dev.py`) les attribue ou les gère automatiquement.

| Variable | Par défaut | Description |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | L'adresse de liaison réseau pour le serveur web FastAPI, injectée automatiquement dans Docker et les commandes CLI. |
| `JWT_SECRET` | _auto-generated_ | La clé secrète utilisée pour signer et déchiffrer les sessions utilisateur (JSON Web Tokens). Cette variable n'est **pas** incluse dans la validation Pydantic `Settings` et est lue au moment de l'exécution directement à partir de l'environnement du système d'exploitation. Si elle est laissée vide, l'application attribue automatiquement une clé aléatoire sécurisée au démarrage (`secrets.token_urlsafe(64)`). Lors du démarrage local via `./dev.py server`, le script génère et injecte automatiquement un secret partagé pour assurer la persistance des sessions. |
| `LIBREFOLIO_TEST_MODE` | — | Un indicateur pour préciser si l'application s'exécute en mode test. Lorsqu'il est défini sur `1` ou `true`, il force l'application à s'isoler complètement en réorientant le répertoire de données vers `backend/data/test/`. Ceci est géré automatiquement par les exécuteurs de tests. |
| `LIBREFOLIO_LOG_LEVEL` | — | Surcharge haute priorité pour le niveau de journalisation. S'il est défini, il prend la priorité absolue et surcharge la propriété `LOG_LEVEL` chargée par Pydantic à l'exécution (utilisé par `./dev.py server --debug`). |

## 🔎 Recherche d'actifs — Recherche de liens Web (Optionnel)

Ces variables ajustent la **recherche externe de dernier recours** utilisée *uniquement* lors de la recherche interactive d'actifs (Créer un actif et assistant "créer un actif" lors de l'importation de courtier) lorsqu'une recherche interne d'un fournisseur ne renvoie aucun résultat. Elles ne sont **jamais** utilisées pour les récupérations automatiques de prix. Le transport est la bibliothèque de méta-recherche [`ddgs`](https://pypi.org/project/ddgs/). **Toutes sont optionnelles et livrées avec des valeurs par défaut sûres** — vous n'avez besoin d'y toucher que pour ajuster, diagnostiquer ou désactiver la fonctionnalité. Consultez le guide du développeur [Recherche d'actifs & Recherche de liens](../developer/backend/assets/search_link_finder.md) pour la conception complète.

| Variable | Par défaut | Description |
| --- | --- | --- |
| `LIBREFOLIO_WEB_LINK_FINDER_ENABLED` | `1` | Interrupteur principal marche/arrêt. Définir à `0` pour désactiver complètement le recours externe ; la recherche interne du fournisseur continue de fonctionner. |
| `LIBREFOLIO_WEB_LINK_FINDER_ENGINE` | `ddgs` | Transport de recherche. Options : `ddgs`, `apikey`. `ddgs` est l'agrégateur de méta-recherche sans configuration. `apikey` est réservé à un moteur avec clé (nécessite `..._API_KEY`) ; `searxng` est réservé pour une future phase auto-hébergée. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION` | `wt-wt` | Indication de région `ddgs`. `wt-wt` (monde entier) évite un biais américain afin que les pages localisées (par ex. Borsa Italiana) ne soient pas déclassées. Exemples : `fr-fr`, `us-en`. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND` | `auto` | Quels moteurs sous-jacents `ddgs` interroge. `auto` alterne entre plusieurs moteurs par appel (couverture maximale, mais la **qualité des résultats varie d'un appel à l'autre**). Fixer un sous-ensemble séparé par des virgules (par ex. `google,bing,duckduckgo`) pour des résultats **plus déterministes** au détriment de la couverture. |
| `LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT` | `6` | Délai d'expiration par requête, en secondes. |
| `LIBREFOLIO_WEB_LINK_FINDER_MAX` | `5` | Nombre maximal d'URL candidates renvoyées par recherche. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | _vide_ | Clé API, utilisée uniquement lorsque `ENGINE=apikey`. |

!!! tip "Résultats non déterministes avec `auto`"

    Avec la valeur par défaut `DDGS_BACKEND=auto`, la même requête peut renvoyer des résultats de qualité différente lors d'appels consécutifs, car `ddgs` alterne les moteurs. Si une recherche interactive ne renvoie parfois rien pour un instrument que vous savez indexé, réessayez une fois — ou fixez `DDGS_BACKEND` à un sous-ensemble stable comme `google,bing,duckduckgo`.

## 🔝 Priorité de résolution

Lors de la résolution des variables de configuration, LibreFolio respecte un ordre de priorité du plus bas (valeurs par défaut du code) au plus élevé (surcharges Docker Compose). Pour une carte détaillée des priorités et un schéma, consultez la [Section Priorité de résolution Docker](docker_advanced.md#resolution-priority).

## 📂 Séparation des données

LibreFolio utilise des répertoires de données distincts pour la production et les tests :

- **Production** : `backend/data/prod/` (sqlite, custom-uploads, broker_reports, logs)
- **Test** : `backend/data/test/` (même structure, complètement isolée)

La fonction `get_data_dir()` dans `config.py` sélectionne automatiquement le chemin correct en fonction de `LIBREFOLIO_TEST_MODE`.

## ⚙️ Comment cela fonctionne

Les paramètres sont chargés dans une classe Pydantic `Settings` située dans `backend/app/config.py`. Cette classe lit automatiquement les variables du fichier `.env` et valide leurs types.

Cette approche offre :

- **Sécurité des types** : Les paramètres sont validés au démarrage de l'application.
- **Configuration centralisée** : Tous les paramètres sont définis au même endroit.
- **Flexibilité** : Les paramètres peuvent être fournis via un fichier `.env` ou sous forme de variables d'environnement réelles, ce qui facilite la configuration dans différents environnements (local, Docker, etc.).
