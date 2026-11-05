# 📝 Configuration

Les options de démarrage se trouvent dans un fichier `.env` : ports, dossier de données, journalisation, sessions de connexion, inscriptions, secrets et quelques fonctionnalités facultatives. Il se trouve à la racine du projet, ou à côté de `docker-compose.yml` avec Docker. Les options que vous modifiez depuis l'application sont quant à elles les [Paramètres globaux](settings.md).

Cette page est le point de départ du guide de configuration : comment créer le fichier `.env`, les **options principales** avec leurs valeurs par défaut, et quelle valeur l'emporte lorsque la même option est définie à plusieurs endroits.

!!! info "📚 Ce guide est réparti sur plusieurs pages"

    Le reste du guide approfondit le sujet, une fois les bases présentées ici :

    - [Configuration : secrets et paramètres des plugins](configuration_secrets.md) : les options qui sont des secrets, comment les lire depuis des fichiers, la clé d'instance et les paramètres des plugins.
    - [Configuration : contrôles et protections](configuration_security.md) : ce que LibreFolio vérifie à son démarrage, les protections du navigateur (Content-Security-Policy, protection contre l'encadrement) et comment il s'arrête.
    - [Configuration : comptes et recherche d'actifs](configuration_accounts.md) : qui peut s'inscrire, la limite des connexions échouées, l'administrateur initial, l'ordre des fournisseurs de prix dans la recherche et la recherche web.

---

## 🔧 Créer le fichier `.env`

Dans le dossier du projet, copiez le fichier d'exemple, puis modifiez les valeurs dont vous avez besoin :

```bash
cp .env.example .env
```

Avec l'image Docker préconstruite, le guide [Installation Docker](../user/installation.md) télécharge le même exemple sous le nom `.env`.

- L'exemple regroupe les options par fonction. Une option commentée, comme `# SESSION_COOKIE_SECURE=auto`, indique sa valeur par défaut : retirez le `#` uniquement pour changer la valeur.
- LibreFolio lit `.env` à son démarrage : redémarrez-le après une modification. Avec Docker Compose, exécutez `docker compose up -d`, car `docker compose restart` conserve les anciennes valeurs.
- Les noms sont sensibles à la casse. Dans les options principales et les paramètres de risque ci-dessous, une valeur du mauvais type ou hors plage arrête le serveur au démarrage avec une erreur.

---

## ✏️ Options principales {: #main-options }

| Variable | Valeur par défaut | Ce qu'elle fait |
| --- | --- | --- |
| `PORT` | `6040` | Port du serveur web. Avec Docker Compose, le port ouvert sur l'hôte (le conteneur écoute toujours sur `6040`). |
| `TEST_PORT` | `6041` | Port du serveur de test (`./dev.py server --test`). |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Dossier de la base de données, des fichiers téléversés, des rapports de courtiers et des journaux ; un chemin relatif part du dossier du projet. Docker le fixe à `/app/backend/data/prod-docker` : pour déplacer les données sur l'hôte, modifiez la partie gauche du volume `./LibreFolio-data` dans `docker-compose.yml`. |
| `LOG_LEVEL` | `INFO` | Niveau de journalisation du serveur : `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL`. À `DEBUG` ou `TRACE`, l'application web écrit aussi dans la console du navigateur chaque appel au serveur ayant échoué, y compris un appel refusé (une réponse `4xx`) ; aux autres niveaux, seulement les erreurs du serveur, les appels restés sans réponse et les réponses qu'elle ne peut pas lire. |
| `JWT_SECRET` | _non défini_ | Clé qui signe les sessions de connexion. Non définie, vide ou composée uniquement d'espaces : une nouvelle clé à chaque démarrage, donc tout le monde se reconnecte après un redémarrage. `JWT_SECRET_FILE` la lit plutôt depuis un fichier : voir [Secrets](configuration_secrets.md#secrets). Voir [Garder les utilisateurs connectés](index.md#session-persistence). |
| `SESSION_COOKIE_SECURE` | `auto` | Quand le cookie de session de connexion est envoyé uniquement via HTTPS : `auto` (si le navigateur utilise HTTPS), `always` ou `never`. Voir [HTTPS et proxys inverses](#session-cookie-secure). |
| `LIBREFOLIO_CLIENT_IP_HEADER` | _non défini_ | Derrière un proxy inverse, l'en-tête dans lequel il transmet l'adresse du visiteur, comme `Fly-Client-IP` sur Fly.io : ne le définissez que si chaque requête passe par ce proxy. Voir [L'adresse du visiteur](connection_proxy.md#client-address). |
| `PREVIEW_CACHE_MAX_MB` | `50` | Mémoire, en Mo, du cache d'aperçus d'images dans chaque processus serveur. |
| `LIBREFOLIO_FRAME_PROTECTION` | `false` | Laissez-la non définie sur votre propre installation : des tableaux de bord à une autre adresse, comme les panneaux Home Assistant, peuvent alors afficher LibreFolio dans un cadre. `true` permet uniquement aux pages de LibreFolio de l'afficher dans un cadre, avec `X-Frame-Options: SAMEORIGIN` et `Content-Security-Policy: frame-ancestors 'self'`, sur chaque réponse. Les trois règles `object-src 'none'; base-uri 'self'; form-action 'self'` n'en dépendent pas : les pages de LibreFolio les portent toujours ([La Content-Security-Policy](configuration_security.md#csp)). `true` ou `false` ; `1`/`0`, `yes`/`no` et `on`/`off` fonctionnent aussi, quelle que soit la casse ; toute autre valeur arrête le serveur au démarrage. Voir [Protection contre l'encadrement](configuration_security.md#frame-protection). |
| `LIBREFOLIO_CSP_REPORT_ONLY` | `false` | Laissez-la non définie sur votre propre installation. `true` ajoute une seconde Content-Security-Policy, plus large, aux pages de l'application web, mais pas à la documentation ni à l'API, en mode report-only : elle ne bloque rien, et le navigateur liste dans sa console de développeur ce que cette politique plus large bloquerait, sans envoyer de rapport nulle part. La [Content-Security-Policy](configuration_security.md#csp) appliquée est toujours active, avec ou sans elle. Mêmes valeurs que `LIBREFOLIO_FRAME_PROTECTION`. Voir [La politique en mode report-only](configuration_security.md#csp-report-only). |
| `LIBREFOLIO_API_DOCS` | `false` | Laissez-la non définie. `true` sert les pages de documentation propres à l'API, Swagger UI à `/api/v1/docs` et ReDoc à `/api/v1/redoc`, avec le schéma de l'API à `/api/v1/openapi.json`. Lorsqu'elle est désactivée, ces pages répondent `404`, dans tous les profils et avec Docker aussi : une instance en cours d'utilisation ne publie aucune cartographie de son API. Un navigateur qui ouvre l'une de ces adresses, ou toute autre adresse sous `/api/`, ou une page de documentation qui n'existe pas sous `/mkdocs/`, est redirigé vers l'application (`/`) ; un programme qui appelle l'API reçoit toujours `404` avec `{"detail": "Not Found"}`. Dans l'application web, une page qui n'existe pas vous ramène à la page d'où vous venez, ou au tableau de bord. C'est un outil pour les développeurs, donc `./dev.py server --debug` l'active, et les exécutions de test internes de LibreFolio l'ont aussi activée. `true` ou `false` ; `1` et `0` fonctionnent aussi. La politique propre à ces pages se trouve dans [La Content-Security-Policy](configuration_security.md#csp). |
| `LIBREFOLIO_SUPPORT_URL` | _non défini_ | Là où les utilisateurs de l'instance demandent de l'aide, par exemple pour un actif que la recherche ne trouve pas ([Faites-le-nous savoir](../user/assets/create-edit.md#let-us-know), sous les résultats de recherche) : une page avec `http://` ou `https://`, ou une adresse e-mail sous la forme `mailto:help@example.org`. Avec une adresse e-mail, l'application de messagerie de l'utilisateur ouvre un message avec les détails de la recherche ; avec une page, celle-ci s'ouvre dans un nouvel onglet et reçoit le rapport dans son adresse, via les paramètres de requête `title` et `body`, comme une issue GitHub préremplie, afin qu'un formulaire d'assistance puisse se remplir automatiquement, et les détails sont également copiés, pour être collés dans ce formulaire. Non définie : sur votre propre installation (le profil `selfhosted`), une nouvelle issue publique sur le GitHub de LibreFolio s'ouvre avec les détails, pour que l'utilisateur les vérifie avant de l'envoyer. Toute autre valeur est ignorée, comme si elle n'était pas définie, et le serveur l'inscrit une fois dans les journaux. Une page dont l'adresse contient un nom d'utilisateur ou un mot de passe est également considérée comme non définie. L'adresse est publique : quiconque peut atteindre le serveur peut la lire à `/api/v1/system/instance`. |
| `LIBREFOLIO_TOS_URL` | _non défini_ | Les conditions d'utilisation de l'instance : une page avec `http://` ou `https://`. La mention légale que chaque utilisateur voit, dans Paramètres › À propos, sur la page de bienvenue, sous la carte de chaque page de connexion et au pied de la barre latérale, renvoie à celles-ci par un lien intitulé **Conditions d'utilisation**, qui s'ouvre dans un nouvel onglet. Non définie : aucun lien, la mention seule. Contrairement à `LIBREFOLIO_SUPPORT_URL`, pas de `mailto:`. Une valeur que LibreFolio ne peut pas utiliser, y compris une adresse contenant un nom d'utilisateur ou un mot de passe, n'arrête pas le serveur : le lien reste masqué, et le journal contient une erreur (voir ci-dessous). L'adresse est publique : quiconque peut atteindre le serveur peut la lire à `/api/v1/system/instance`. |
| `LIBREFOLIO_PRIVACY_URL` | _non défini_ | La politique de confidentialité de l'instance, liée sous le libellé **Politique de confidentialité**, à côté des conditions d'utilisation : les mêmes règles que `LIBREFOLIO_TOS_URL`. |
| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | _non défini_ | Laissez-la non définie. La taille maximale d'une archive qu'un administrateur peut téléverser pour la vérifier en vue d'une restauration, en mégaoctets ; `0` signifie aucune limite. Non définie : aucune limite. Une valeur qui n'est pas un nombre entier n'arrête pas le serveur : les téléversements répondent `503`, et le journal contient une erreur, dès le démarrage ([Contrôles au démarrage](configuration_security.md#startup-checks)) puis chaque fois que la limite est lue. Lue uniquement depuis l'environnement. Voir [La limite de téléversement d'une restauration](backup_restore.md#restore-upload-limit). |
| `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` | _non défini_ | Laissez-la non définie. La taille maximale qu'une archive peut atteindre une fois décompressée pendant sa vérification en vue d'une restauration, en mégaoctets, d'après les tailles déclarées dans son manifeste ; `0` signifie aucune limite. Non définie : aucune limite. Une valeur que vous définissez l'emporte toujours, `0` compris, et `backup restore` en ligne de commande la suit aussi. Une archive dépassant la limite est refusée avant toute décompression (`unpacked_too_large`). Une valeur qui n'est pas un nombre entier n'arrête pas le serveur : les contrôles d'une restauration répondent `503` (`backup_restore_unavailable`), le journal contient une erreur, dès le démarrage ([Contrôles au démarrage](configuration_security.md#startup-checks)) puis à chaque contrôle, et l'onglet **Sécurité** de Paramètres › Administration le signale (`backup.restore_limit`). Lue uniquement depuis l'environnement. Voir [La limite de téléversement d'une restauration](backup_restore.md#restore-upload-limit). |
| `LIBREFOLIO_BACKUP_RECIPIENTS` | _non défini_ | Une ou deux clés publiques age (`age1…`, telles que les affichent `backup keygen` ou `age-keygen`), séparées par des virgules : deux uniquement pendant un changement de clé. Ce n'est pas un secret. Définie, `backup create --sealed` crée une sauvegarde [scellée](backup_sealed.md#sealed) : un `.tar` dont l'ouverture n'est possible qu'avec les clés privées correspondantes, jamais avec la clé d'instance. Une valeur que LibreFolio ne peut pas utiliser (pas une clé `age1…`, plus de deux, la même deux fois) n'arrête pas le serveur : le journal contient une erreur, et l'onglet **Sécurité** de Paramètres › Administration le signale (`backup.recipients`). Lue uniquement depuis l'environnement. |
| `LIBREFOLIO_STORAGE_LIMIT_MB` | _non défini_ | Laissez-la non définie sur votre propre installation : vous définissez la limite dans la barre d’occupation de l’espace de la page **Fichiers**. L'espace que l'instance peut occuper, en mégaoctets ; `0` signifie aucune limite. Définie, elle l'emporte sur le paramètre **Limite d'espace (Mo)**, quelle que soit la valeur qu'un administrateur a enregistrée auparavant, et le verrouille : le champ de la barre d’occupation de l’espace est grisé et tout enregistrement est refusé. Non définie : le paramètre décide, `0` jusqu'à ce qu'un administrateur enregistre une autre valeur. Une valeur qui n'est pas un nombre entier est ignorée, et le paramètre fait foi. C'est une ligne tracée sur la barre, pas un quota : LibreFolio affiche un avertissement lorsque les données la dépassent, et ne supprime rien. Lue uniquement depuis l'environnement. Voir [La barre d’occupation de l’espace](backup_restore.md#space-used). |
| `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS` | `60` | La première pause d'un fournisseur de prix qui répond « trop de requêtes » (HTTP 429) : aucune requête ne l'atteint avant la fin de la pause, et chaque refus consécutif double la suivante. Un nombre entier de secondes de `0` à `86400` ; `0` désactive les pauses, comme avant la version 1.3. Activée par défaut, par décision de développement 34 : une exception à la règle selon laquelle une nouvelle option laisse une installation telle quelle. Une valeur inutilisable n'arrête pas non plus le serveur : le journal contient une erreur, et les deux valeurs par défaut s'appliquent. Voir [Pauses des fournisseurs](settings.md#provider-pauses). |
| `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS` | `3600` | La pause la plus longue que le doublement atteint : un nombre entier de secondes de `1` à `86400`, pas inférieure à la première pause tant que les pauses sont activées. Un `Retry-After` d'un fournisseur peut encore demander davantage, jusqu'à un jour. Une valeur inutilisable n'arrête pas non plus le serveur : le journal contient une erreur, et les deux valeurs par défaut s'appliquent. Voir [Pauses des fournisseurs](settings.md#provider-pauses). |
| `LIBREFOLIO_PROBE_RATE_LIMIT` | `30` | Combien de fois par minute un utilisateur peut tester les paramètres d'un fournisseur de prix (**Tester la configuration** dans le formulaire d'actif ; **Interroger le fournisseur** compte aussi), ce qui peut appeler le fournisseur ; au-delà, le formulaire indique à l'utilisateur quand réessayer. Un nombre entier de `0` à `10000` ; `0` désactive la limite, pour une instance de test uniquement (`./dev.py server --test` le fait), et le journal contient un avertissement à chaque démarrage. Lue à chaque test : une modification s'applique sans redémarrage. Une valeur inutilisable n'arrête pas le serveur : le journal contient une erreur, et `30` s'applique. |
| `LIBREFOLIO_BRIM_PREWARM` | `false` (`true` en mode test) | Facultative. `true` prépare les workers d'import de courtiers au démarrage, avec les plugins d'import chargés : le premier import de courtier après un démarrage est alors environ 4 secondes plus rapide, pour environ 80 Mo de mémoire retenus dès le départ et environ 1,4 seconde de CPU à chaque démarrage. Désactivée par défaut, par décision N56 : sur une petite machine cloud, cette mémoire et ce CPU coûtent plus que les secondes qu'ils font gagner. `true` ou `false` ; `1`/`0`, `yes`/`no` et `on`/`off` fonctionnent aussi, quelle que soit la casse. Toute autre valeur n'arrête pas le serveur, contrairement aux options principales : le journal contient un avertissement au démarrage, et l'option reste désactivée. Voir [Architecture BRIM → Préchargement et préchauffage](../developer/backend/brim/architecture.md#parse-pool-warm-up). |
| `LIBREFOLIO_SMTP_HOST` | _non défini_ : e-mail désactivé | Facultative. Le serveur SMTP qui envoie les e-mails de LibreFolio, comme `smtp.example.com`. Voir [E-mail](email.md#variables). |
| `LIBREFOLIO_SMTP_TLS` | `starttls` | Comment la connexion au serveur SMTP est chiffrée : `starttls`, `tls` ou `none`. Voir [Modes de chiffrement](email.md#encryption-modes). |
| `LIBREFOLIO_SMTP_PORT` | `587` avec `starttls`, `465` avec `tls`, `25` avec `none` | Le port du serveur SMTP, uniquement lorsqu'il ne s'agit pas du port habituel de son mode de chiffrement. Voir [E-mail](email.md#variables). |
| `LIBREFOLIO_SMTP_USER` | _non défini_ : pas d'identifiant de connexion | L'identifiant de connexion au serveur SMTP, défini avec `LIBREFOLIO_SMTP_PASSWORD` ([Secrets](configuration_secrets.md#secrets)). Voir [E-mail](email.md#variables). |
| `LIBREFOLIO_SMTP_FROM` | _non défini_ | L'expéditeur des e-mails, requis dès qu'un serveur est défini. Voir [E-mail](email.md#variables). |
| `LIBREFOLIO_SMTP_REPLY_TO` | _non défini_ : les réponses vont à l'expéditeur | Où vont les réponses aux e-mails de LibreFolio. Voir [E-mail](email.md#variables). |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` | `50` | Combien d'e-mails l'instance peut envoyer par heure, par processus serveur. Voir [E-mail](email.md#variables). |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` | `20` | Combien d'e-mails d'inscription une adresse cliente peut déclencher par heure, par processus serveur : un nombre entier, au moins 1. Un seul compteur pour les inscriptions, **Renvoyer le lien** et **Mot de passe oublié ?**. Au-delà, un nouveau compte est créé et attend, et son e-mail est retenu. Voir [Limites sur les e-mails d'activation et de réinitialisation du mot de passe](email_flows.md#activation-limits). |

Une valeur que LibreFolio ne peut pas utiliser dans `LIBREFOLIO_TOS_URL` ou `LIBREFOLIO_PRIVACY_URL` n'arrête jamais le serveur : ce lien reste masqué, et la mention légale s'affiche sans lui. La première fois que chaque processus serveur répond à `/api/v1/system/instance`, que l'application lit dès son ouverture, le journal contient une erreur, `Invalid instance link`, avec la variable et sa valeur dans `problem` (une valeur contenant un `@` n'est pas affichée : elle peut porter un nom d'utilisateur ou un mot de passe), et dans `consequence` ce que cela coûte jusqu'à ce que vous la corrigiez : par exemple `the terms of service link stays hidden until it is fixed: the legal notice shows without it`. Corrigez la valeur, puis redémarrez. Une `LIBREFOLIO_SUPPORT_URL` inutilisable journalise la même erreur, avec son propre `consequence`.

Les anciens fichiers `.env` peuvent encore contenir `PORTFOLIO_BASE_CURRENCY` : LibreFolio l'ignore, et les nouveaux utilisateurs partent de la **Devise par défaut** dans les [Paramètres globaux](settings.md).

??? info "🔒 HTTPS et proxys inverses — le cookie de session"

    `SESSION_COOKIE_SECURE` décide quand le cookie qui garde les utilisateurs connectés est `Secure` : le navigateur ne l'envoie alors que via HTTPS, afin que la session ne circule jamais sur une connexion non chiffrée. La casse et les espaces autour de la valeur n'ont pas d'importance ; toute autre valeur arrête le serveur au démarrage avec une erreur.
    {: #session-cookie-secure }

    - **`auto`** (par défaut) : `Secure` lorsque le navigateur a atteint LibreFolio via HTTPS. LibreFolio sert lui-même du HTTP en clair, donc HTTPS provient d'un proxy inverse devant lui, qui l'indique avec l'en-tête `X-Forwarded-Proto: https` ; seule sa première valeur compte. Il n'y a aucune liste de proxys de confiance à configurer : l'en-tête peut seulement activer `Secure`, jamais le désactiver. En HTTP en clair, comme `http://localhost:6040`, une IP de réseau local ou l'IP Tailscale des niveaux 1 et 2 dans [Exposer en toute sécurité](service_exposure.md), le cookie n'est pas `Secure`, donc la connexion continue de fonctionner.
    - **`always`** : toujours `Secure`, pour une installation accessible uniquement via HTTPS. En HTTP en clair, le navigateur supprime le cookie, donc la connexion ne tient pas : la page suivante renvoie l'utilisateur à la page de connexion.
    - **`never`** : jamais `Secure`. C'est la solution de secours lorsqu'un proxy envoie `X-Forwarded-Proto: https` à un navigateur qui utilise en réalité du HTTP en clair, comme Nginx avec un `proxy_set_header X-Forwarded-Proto https;` codé en dur dans un bloc `server` en HTTP clair : en `auto`, ce navigateur serait renvoyé à la page de connexion après chaque connexion. Mieux vaut corriger le proxy (`$scheme` au lieu de `https`) ; `never` est le fallback.

    Derrière un proxy inverse HTTPS, `auto` s'appuie sur son en-tête `X-Forwarded-Proto` :

    - **Tailscale Serve et Funnel** (niveaux 3 et 4 dans [Exposer en toute sécurité](service_exposure.md)), **Caddy** et **Traefik** l'envoient d'eux-mêmes : rien à configurer.
    - **Nginx** ne le fait pas : ajoutez `proxy_set_header X-Forwarded-Proto $scheme;` à la `location` qui fait proxy vers LibreFolio.
    - **Tout autre proxy** : faites-lui envoyer l'en-tête ou, si LibreFolio n'est accessible qu'à travers lui, définissez `SESSION_COOKIE_SECURE=always`.

    Pour vérifier dans votre navigateur si le cookie de session est marqué `Secure`, voir [Vérifier la sécurité de la connexion](connection_checks.md#session-cookie).

??? info "🧮 Workers du moteur de risque — réglage avancé"

    Les simulations de risque et les optimisations de portefeuille s'exécutent dans des processus workers séparés, démarrés à la première utilisation. Les valeurs par défaut conviennent à la plupart des installations : ajoutez une variable à `.env` uniquement pour les modifier.

    | Variable | Valeur par défaut | Ce qu'elle fait |
    | --- | --- | --- |
    | `RISK_SIMULATION_WORKERS`, `RISK_OPTIMIZATION_WORKERS` | `1` (1–8) | Processus workers par type de tâche : plus il y en a, plus de tâches peuvent s'exécuter simultanément. |
    | `RISK_SIMULATION_QUEUE_CAPACITY`, `RISK_OPTIMIZATION_QUEUE_CAPACITY` | `2` (0–64) | Tâches pouvant attendre un worker ; au-delà, les nouvelles demandes sont refusées. |
    | `RISK_SIMULATION_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_TIMEOUT_SECONDS` | `120` / `60` | Limite de temps d'une tâche, en secondes. |
    | `RISK_SIMULATION_IDLE_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS` | `600` | Les workers inactifs s'arrêtent après ce nombre de secondes et redémarrent à la tâche suivante ; `0` les maintient en fonctionnement. |

---

## 💻 Paramètres définis par les outils

`./dev.py` et Docker Compose définissent ces paramètres pour vous : ne les modifiez que si vous savez pourquoi.

| Variable | Valeur par défaut | Ce qu'elle fait |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Adresse sur laquelle `./dev.py server` écoute ; `127.0.0.1` n'accepte que les connexions locales. Docker Compose utilise toujours `0.0.0.0`. |
| `LIBREFOLIO_LOG_LEVEL` | — | Remplace `LOG_LEVEL` lorsqu'elle est définie ; `./dev.py server --debug` et `./dev.py server --test` la définissent à `DEBUG`. |
| `LIBREFOLIO_API_DOCS` | — | Définie à `1` par `./dev.py server --debug`, ce qui active les pages de documentation de l'API (la variable du même nom, ci-dessus). |
| `LIBREFOLIO_NO_SCHEDULER` | — | Toute valeur non vide, `0` compris, désactive les synchronisations planifiées des prix et des FX. Définie par `./dev.py server --no-scheduler`. |
| `LIBREFOLIO_TEST_MODE` | — | `1`, `true` ou `yes`, quelle que soit la casse, bascule vers le dossier de données de test. Uniquement pour les exécutions de test internes de LibreFolio : `./dev.py server --test` et les lanceurs de test la définissent, et `./dev.py server` la désactive. Un serveur démarré sans `./dev.py`, par exemple avec `uvicorn` directement ou depuis une unité de service, la reprend depuis son environnement. Sur une instance en cours d'utilisation, en dehors du lanceur de test, les [contrôles au démarrage](configuration_security.md#startup-checks) la signalent comme une erreur. |
| `LIBREFOLIO_TEST_DATA_DIR` | `./backend/data/test` | Dossier des données de test ; il ne doit pas chevaucher celui de production. |

---

## 🔝 Quelle valeur l'emporte

De la priorité la plus élevée à la plus faible :

1. Les options `--host`, `--port` et `--data-dir` de `./dev.py server`.
2. Les variables définies dans le shell.
3. Le fichier `.env`.
4. Les valeurs par défaut listées sur cette page.

Avec Docker Compose, le bloc `environment:` de `docker-compose.yml` l'emporte sur `.env` : il fixe `HOST`, `LIBREFOLIO_DATA_DIR` et, à l'intérieur du conteneur, `PORT=6040` (votre `PORT` définit toujours le port de l'hôte). Voir [Docker avancé](docker_advanced.md#resolution-priority).

Pour un [paramètre de plugin](configuration_secrets.md#plugin-settings), de la priorité la plus élevée à la plus faible : sa variable (`LIBREFOLIO_PLUGIN_…` avant l'ancien nom que le plugin utilise pour elle, chacune avant sa forme `_FILE`), la valeur enregistrée dans LibreFolio, puis la valeur par défaut du plugin. Une variable dont la valeur est incorrecte l'emporte quand même, et laisse le plugin non configuré. Un paramètre personnel n'a pas de variable : la valeur enregistrée par l'utilisateur, puis la valeur par défaut.

---

## 📂 Où vont les données

- **Production** : `backend/data/prod/`, ou `LIBREFOLIO_DATA_DIR`. Il contient la base de données (`sqlite/app.db`), `custom-uploads/`, `broker_reports/`, `logs/` et, une fois que LibreFolio a créé la [clé d'instance](configuration_secrets.md#instance-key), `secrets/`.
- **Test** : `backend/data/test/`, ou `LIBREFOLIO_TEST_DATA_DIR`. Même organisation, tenue à l'écart.

[Structure du système de fichiers](filesystem.md) détaille chaque dossier et comment le sauvegarder.

---

## 🔗 Voir aussi

- 📄 **[Configuration : secrets et paramètres des plugins](configuration_secrets.md)** — Secrets, paramètres des plugins
- 📄 **[Configuration : contrôles et protections](configuration_security.md)** — Contrôles au démarrage, protections du navigateur, arrêt du serveur
- 📄 **[Configuration : comptes et recherche d'actifs](configuration_accounts.md)** — Comptes et inscriptions, l'ordre des fournisseurs de prix dans la recherche, facultatif : recherche web pour les nouveaux actifs
- ⚙️ **[Paramètres globaux](settings.md)** — Options modifiées depuis l'application
- 🐳 **[Docker avancé](docker_advanced.md)** — Fichier Compose, volumes, ID d'utilisateur et de groupe
- 🧑‍💻 Pour les développeurs : **[Système de paramètres](../developer/architecture/settings.md)** — Comment ces valeurs sont chargées
- 🔒 Pour les développeurs : **[Architecture de sécurité](../developer/architecture/security.md)** — Secrets, clé d'instance, contrôles au démarrage et limite des connexions échouées
- 🧩 Pour les développeurs : **[Paramètres des plugins](../developer/architecture/patterns/plugin_settings.md)** — Comment les plugins déclarent des paramètres et comment les secrets sont protégés
