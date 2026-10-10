# 📝 Configuration

Les options de démarrage se trouvent dans un fichier `.env` : ports, dossier de données, journalisation, sessions de connexion et quelques fonctionnalités facultatives. Il se trouve à la racine du projet, ou à côté de `docker-compose.yml` avec Docker. Les options que vous modifiez depuis l’application relèvent des [Paramètres globaux](settings.md).

---

## 🔧 Créer le fichier `.env`

Dans le dossier du projet, copiez le fichier d’exemple, puis modifiez les valeurs dont vous avez besoin :

```bash
cp .env.example .env
```

Avec l’image Docker préconstruite, le guide [Installation Docker](../user/installation.md) télécharge le même exemple sous le nom `.env`.

- LibreFolio lit `.env` au démarrage : redémarrez-le après une modification. Avec Docker Compose, exécutez
  `docker compose up -d`, car `docker compose restart` conserve les anciennes valeurs.
- Les noms sont sensibles à la casse. Dans les options principales et les paramètres de risque ci-dessous, une valeur du mauvais
  type ou hors limites arrête le serveur au démarrage avec une erreur.

---

## ✏️ Options principales

| Variable | Défaut | Ce qu'il fait |
| --- | --- | --- |
| `PORT` | `6040` | Port du serveur web. Avec Docker Compose, le port ouvert sur l’hôte (le conteneur écoute toujours sur `6040`). |
| `TEST_PORT` | `6041` | Port du serveur de test (`./dev.py server --test`). |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Dossier de la base de données, des téléversements, des rapports de courtier et des journaux ; un chemin relatif part du dossier du projet. Docker le définit à `/app/backend/data/prod-docker` : pour déplacer les données sur l’hôte, modifiez le côté gauche du volume `./LibreFolio-data` dans `docker-compose.yml`. |
| `LOG_LEVEL` | `INFO` | Niveau de détail des journaux du serveur : `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL`. |
| `JWT_SECRET` | _non défini_ | Clé qui signe les sessions de connexion. Non définie : une nouvelle clé à chaque démarrage, donc tout le monde doit se reconnecter après un redémarrage. Voir [Maintenir les utilisateurs connectés](index.md#session-persistence). |
| `SESSION_COOKIE_SECURE` | `auto` | Quand le cookie de session de connexion est envoyé uniquement via HTTPS : `auto` (si le navigateur utilise HTTPS), `always` ou `never`. Voir [HTTPS et proxies inverses](#session-cookie-secure). |
| `PREVIEW_CACHE_MAX_MB` | `50` | Mémoire, en Mo, du cache d’aperçu des images dans chaque processus serveur. |

Les anciens fichiers `.env` peuvent encore contenir `PORTFOLIO_BASE_CURRENCY` : LibreFolio l’ignore, et les nouveaux
utilisateurs partent de la **Devise par défaut** dans les [Paramètres globaux](settings.md).

??? info "🔒 HTTPS et proxies inverses — le cookie de session"

    `SESSION_COOKIE_SECURE` détermine quand le cookie qui garde les utilisateurs connectés est `Secure` : le
    navigateur ne l’envoie alors que via HTTPS, donc la session ne circule jamais sur une connexion
    non chiffrée. La casse et les espaces autour de la valeur n’ont pas d’importance ; toute autre valeur arrête le serveur au
    démarrage avec une erreur.
    {: #session-cookie-secure }

    - **`auto`** (par défaut) : `Secure` lorsque le navigateur a atteint LibreFolio via HTTPS. LibreFolio
      lui-même sert du HTTP en clair, donc HTTPS provient d’un proxy inverse placé devant lui, qui l’indique
      avec l’en-tête `X-Forwarded-Proto: https` ; seule sa première valeur compte. Il n’y a pas de liste de
      proxies de confiance à configurer : l’en-tête peut uniquement activer `Secure`, jamais le désactiver. En HTTP en clair,
      comme `http://localhost:6040`, une IP de réseau local ou l’IP Tailscale des niveaux 1 et 2 dans
      [Exposition sécurisée](service_exposure.md), le cookie n’est pas `Secure`, donc la connexion continue de
      fonctionner.
    - **`always`** : toujours `Secure`, pour une installation accessible uniquement via HTTPS. En HTTP en clair, le
      navigateur abandonne le cookie, donc la connexion ne persiste pas : la page suivante renvoie l’utilisateur
      vers la page de connexion.
    - **`never`** : jamais `Secure`. C’est la solution de secours lorsqu’un proxy envoie `X-Forwarded-Proto: https`
      à un navigateur qui utilise en réalité du HTTP en clair, comme Nginx avec un
      `proxy_set_header X-Forwarded-Proto https;` codé en dur dans un bloc `server` en HTTP en clair : en `auto`, ce
      navigateur serait renvoyé vers la page de connexion après chaque connexion. Mieux vaut corriger le proxy
      (`$scheme` au lieu de `https`) ; `never` est le fallback.

    Derrière un proxy inverse HTTPS, `auto` s’appuie sur son en-tête `X-Forwarded-Proto` :

    - **Tailscale Serve et Funnel** (niveaux 3 et 4 dans [Exposition sécurisée](service_exposure.md)),
      **Caddy** et **Traefik** l’envoient d’eux-mêmes : rien à configurer.
    - **Nginx** ne le fait pas : ajoutez `proxy_set_header X-Forwarded-Proto $scheme;` au bloc `location` qui
      fait proxy vers LibreFolio.
    - **Tout autre proxy** : faites-lui envoyer l’en-tête ou, si LibreFolio n’est accessible qu’à travers lui,
      définissez `SESSION_COOKIE_SECURE=always`.

??? info "🧮 Workers du moteur de risque — réglage avancé"

    Les simulations de risque et les optimisations de portefeuille s’exécutent dans des processus workers séparés, démarrés à
    la première utilisation. Les valeurs par défaut conviennent à la plupart des installations : ajoutez une variable à `.env` uniquement pour modifier ce réglage.

    | Variable | Défaut | Ce qu'il fait |
    | --- | --- | --- |
    | `RISK_SIMULATION_WORKERS`, `RISK_OPTIMIZATION_WORKERS` | `1` (1–8) | Processus workers par type de tâche : plus ils sont nombreux, plus de tâches s’exécutent en même temps. |
    | `RISK_SIMULATION_QUEUE_CAPACITY`, `RISK_OPTIMIZATION_QUEUE_CAPACITY` | `2` (0–64) | Tâches pouvant attendre un worker ; au-delà, les nouvelles requêtes sont refusées. |
    | `RISK_SIMULATION_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_TIMEOUT_SECONDS` | `120` / `60` | Limite de temps d’une tâche, en secondes. |
    | `RISK_SIMULATION_IDLE_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS` | `600` | Les workers inactifs s’arrêtent après ce nombre de secondes et redémarrent à la tâche suivante ; `0` les maintient en fonctionnement. |

---

## 💻 Paramètres définis par les outils

`./dev.py` et Docker Compose les définissent pour vous : ne les modifiez que si vous savez pourquoi.

| Variable | Défaut | Ce qu'il fait |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Adresse sur laquelle `./dev.py server` écoute ; `127.0.0.1` accepte uniquement les connexions locales. Docker Compose utilise toujours `0.0.0.0`. |
| `LIBREFOLIO_LOG_LEVEL` | — | Remplace `LOG_LEVEL` lorsqu’il est défini ; `./dev.py server --debug` le définit à `DEBUG`. |
| `LIBREFOLIO_TEST_MODE` | — | `1`, `true` ou `yes` bascule vers le dossier de données de test. Défini par `./dev.py server --test` et les lanceurs de tests. |
| `LIBREFOLIO_TEST_DATA_DIR` | `./backend/data/test` | Dossier des données de test ; il ne doit pas chevaucher celui de production. |

---

## 🔎 Facultatif : recherche web pour les nouveaux actifs

Lorsque vous créez un actif, y compris depuis l’assistant d’importation de courtier, et que la recherche propre d’un fournisseur ne trouve
rien, LibreFolio peut trouver la page de l’actif par une recherche web via la
bibliothèque [`ddgs`](https://pypi.org/project/ddgs/). Elle est activée par défaut et n’est jamais utilisée pour les mises à jour de prix.
Toutes ces variables sont facultatives : décommentez une ligne de `.env.example` pour en modifier une.

| Variable | Défaut | Ce qu'il fait |
| --- | --- | --- |
| `LIBREFOLIO_WEB_LINK_FINDER_ENABLED` | `1` | `0` désactive la recherche web ; la recherche propre des fournisseurs continue de fonctionner. |
| `LIBREFOLIO_WEB_LINK_FINDER_ENGINE` | `ddgs` | `ddgs` ne nécessite aucune configuration. `apikey` est réservé à un service de recherche payant et ne renvoie encore aucun résultat. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION` | `wt-wt` | Région de recherche. `wt-wt` (monde entier) évite que les sites nationaux tels que Borsa Italiana soient rétrogradés. Exemples : `it-it`, `us-en`. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND` | `auto` | Moteurs que `ddgs` interroge : `auto` les fait tourner pour une couverture maximale ; une liste comme `google,bing,duckduckgo` donne des résultats plus stables. |
| `LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT` | `6` | Limite de temps d’une recherche, en secondes. |
| `LIBREFOLIO_WEB_LINK_FINDER_MAX` | `5` | Nombre maximal de liens renvoyés par une recherche. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | _vide_ | Clé pour le moteur `apikey`. |

??? tip "🔁 Les résultats changent d’une tentative à l’autre — quand un actif connu n’est parfois pas trouvé"

    Avec `auto`, chaque recherche peut atteindre différents moteurs, donc la même requête peut donner de meilleurs ou de moins bons résultats
    d’un essai à l’autre. Réessayez une fois, ou définissez
    `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND=google,bing,duckduckgo`.

---

## 🔝 Quelle valeur l’emporte

De la priorité la plus élevée à la plus faible :

1. Les options `--host`, `--port` et `--data-dir` de `./dev.py server`.
2. Les variables définies dans le shell.
3. Le fichier `.env`.
4. Les valeurs par défaut listées sur cette page.

Avec Docker Compose, le bloc `environment:` de `docker-compose.yml` l’emporte sur `.env` : il définit
`HOST` et `LIBREFOLIO_DATA_DIR`. Voir [Docker avancé](docker_advanced.md#resolution-priority).

---

## 📂 Où vont les données

- **Production** : `backend/data/prod/`, ou `LIBREFOLIO_DATA_DIR`. Ce dossier contient la base de données
  (`sqlite/app.db`), `custom-uploads/`, `broker_reports/` et `logs/`.
- **Test** : `backend/data/test/`, ou `LIBREFOLIO_TEST_DATA_DIR`. Même organisation, tenue à part.

[Structure du système de fichiers](filesystem.md) détaille chaque dossier et comment le sauvegarder.

---

## 🔗 Voir aussi

- ⚙️ **[Paramètres globaux](settings.md)** — Options modifiées depuis l’application
- 🐳 **[Docker avancé](docker_advanced.md)** — Fichier Compose, volumes, ID d’utilisateur et de groupe
- 🧑‍💻 Pour les développeurs : **[Système de paramètres](../developer/architecture/settings.md)** — Comment ces
  valeurs sont chargées
