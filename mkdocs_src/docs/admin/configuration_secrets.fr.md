# 🔐 Configuration : secrets et paramètres des plugins

Ce qui doit rester privé dans une installation LibreFolio : les options qui sont des **secrets** (clés, mots de passe et jetons), qui peuvent aussi être lues depuis des fichiers tels que les secrets Docker ; la **clé d'instance**, qui protège ce que stocke LibreFolio ; les **paramètres des plugins**, clés API comprises.

Vous découvrez le fichier `.env` ? Comment le créer, les options principales et la valeur qui l'emporte : [Configuration](configuration.md).

---

## 🔐 Secrets {: #secrets }

**Où** : dans le `.env` de LibreFolio, ou dans l'environnement du conteneur (bloc `environment:` de `docker-compose.yml`). Chaque secret peut aussi être lu depuis un fichier, avec sa variable `_FILE` ([Secrets dans des fichiers](#secret-files)). Gardez-les aussi privés que la base de données.

| Secret | Depuis un fichier | Ce que c'est |
| --- | --- | --- |
| `JWT_SECRET` | `JWT_SECRET_FILE` | La clé qui signe les sessions de connexion, dans les [options principales](configuration.md). |
| `LIBREFOLIO_INSTANCE_KEY` | `LIBREFOLIO_INSTANCE_KEY_FILE` | La [clé d'instance](#instance-key). Non définie : LibreFolio en crée une dans le répertoire de données. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` | La clé d'un service de recherche payant, pour le moteur `apikey` de la [recherche web](configuration_accounts.md#optional-web-search-for-new-assets). |
| `LIBREFOLIO_SMTP_PASSWORD` | `LIBREFOLIO_SMTP_PASSWORD_FILE` | Le mot de passe du serveur SMTP qui envoie les e-mails de LibreFolio : [E-mail](email.md). |

Un plugin peut avoir ses propres secrets, comme la clé API d'une source de données payante : [Paramètres des plugins](#plugin-settings).

### 📄 Secrets dans des fichiers {: #secret-files }

Ajoutez `_FILE` au nom du secret et indiquez le chemin d'un fichier qui le contient, par exemple `/run/secrets/jwt_secret`. C'est ainsi que Docker et Kubernetes transmettent leurs secrets : le secret reste hors de `.env` et hors de l'environnement du conteneur.

Règles du fichier :

- Le secret est le texte du fichier, sans les sauts de ligne à sa fin et sans la marque d'ordre des octets que certains éditeurs Windows placent à son début. Tout autre espace compte, au début comme à la fin.
- Un chemin relatif part du dossier du projet.
- Un secret ou sa variable `_FILE` qui est vide ou ne contient que des espaces est considéré comme non défini : un espace parasite n'est jamais utilisé comme clé.
- Définissez l'un des deux. Lorsque les deux sont définis, la variable elle-même l'emporte, le fichier est ignoré et le journal de démarrage contient un [avertissement](configuration_security.md#startup-checks).
- `.env` fonctionne aussi bien avec `./dev.py` qu'avec Docker Compose (`env_file: .env`) : les deux placent ses valeurs dans l'environnement, où LibreFolio les lit.

Si le fichier ne fournit pas le secret :

| Variable | Quand elle est lue | Si le fichier ne fournit pas le secret |
| --- | --- | --- |
| `JWT_SECRET_FILE`, `LIBREFOLIO_INSTANCE_KEY_FILE`, `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` | au démarrage | **Le serveur s'arrête au démarrage.** L'erreur nomme la variable et le chemin, jamais le secret. Cela couvre un fichier manquant, illisible, vide ou blanc (seulement des espaces et des sauts de ligne), qui n'est pas du texte UTF-8 ou qui dépasse 64 Kio. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` | seulement quand une recherche utilise le moteur `apikey` | Le serveur ne s'arrête pas : la recherche continue sans la recherche web, avec un avertissement dans le journal (`web_link_finder: …; disabling`) ; la recherche propre aux fournisseurs continue de fonctionner. |
| `LIBREFOLIO_SMTP_PASSWORD_FILE` | seulement quand `LIBREFOLIO_SMTP_HOST` est défini | Le serveur ne s'arrête pas : l'envoi d'e-mails reste désactivé, avec une erreur dans le journal (`Email configuration cannot be used: email stays off`). |

??? example "🐳 Un secret Docker avec Docker Compose"

    1. **Depuis un terminal, dans le dossier de `docker-compose.yml`**, enregistrez une nouvelle clé dans un fichier :

        ```bash
        python3 -c "import secrets; print(secrets.token_urlsafe(64))" > jwt_secret.txt
        ```

        Vous obtenez `jwt_secret.txt` à côté de `docker-compose.yml`.

    2. **Depuis un terminal**, rendez le fichier lisible par l'utilisateur de l'image, `1000:1000` pour l'image officielle ([Docker avancé](docker_advanced.md)) :

        ```bash
        sudo chown 1000:1000 jwt_secret.txt
        sudo chmod 600 jwt_secret.txt
        ```

        Compose monte le fichier dans le conteneur tel qu'il est sur l'hôte, avec son propriétaire et ses permissions : si l'utilisateur de l'image ne peut pas le lire, le serveur s'arrête au démarrage avec `cannot be read` pour le fichier.

    3. **Dans `docker-compose.yml`**, ajoutez les lignes marquées et conservez le reste du service tel quel :

        ```yaml
        services:
          librefolio:
            environment:
              - LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker
              - HOST=0.0.0.0
              - JWT_SECRET_FILE=/run/secrets/jwt_secret  # added
            secrets:                                     # added
              - jwt_secret                               # added
        secrets:                                         # added
          jwt_secret:                                    # added
            file: ./jwt_secret.txt                       # added
        ```

    4. **Dans `.env`**, si une ligne donne une valeur à `JWT_SECRET`, supprimez-la : elle l'emporterait sur le fichier. Une ligne `JWT_SECRET=` vide ne pose pas de problème.

    5. Redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.

    Les fichiers de `LIBREFOLIO_INSTANCE_KEY_FILE`, `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` et `LIBREFOLIO_SMTP_PASSWORD_FILE` sont montés de la même manière ; ce que fait chaque variable lorsque le fichier ne fournit pas le secret : le tableau de [Secrets dans des fichiers](#secret-files).

### 🗝️ La clé d'instance {: #instance-key }

Un secret par installation : LibreFolio en dérive ses propres clés de chiffrement. Il n'y a rien à configurer. LibreFolio utilise la première clé qu'il trouve :

1. `LIBREFOLIO_INSTANCE_KEY`, la clé elle-même ;
2. `LIBREFOLIO_INSTANCE_KEY_FILE`, un fichier qui la contient, comme un secret Docker ;
3. `secrets/instance.key` dans le répertoire de données, que LibreFolio crée la première fois qu'il en a besoin : 43 caractères aléatoires, dans un dossier et un fichier que seul l'utilisateur exécutant LibreFolio peut ouvrir (`0700` et `0600`).

**Pour fournir une clé de votre choix**, par exemple dans le cloud, depuis l'environnement ou depuis un secret Docker au lieu du répertoire de données. Chaque instance a sa propre clé : ne partagez jamais une même clé entre plusieurs instances.

1. **Depuis un terminal**, générez la clé :

    ```bash
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
    ```

    Vous obtenez une clé aléatoire d'au moins 32 caractères, le minimum. N'utilisez jamais de phrase de passe : les clés que LibreFolio en dérive ne sont pas plus solides que la phrase de passe. Si LibreFolio a déjà créé `secrets/instance.key`, ne générez rien : utilisez son contenu comme valeur, car définir `LIBREFOLIO_INSTANCE_KEY` là où `secrets/instance.key` existe déjà change la clé.

2. **Dans `.env` ou dans l'environnement du conteneur**, définissez la clé, ou enregistrez-la dans un fichier et indiquez le chemin, comme dans l'[exemple Docker](#secret-files) :

    ```env
    LIBREFOLIO_INSTANCE_KEY=<key>
    # or
    LIBREFOLIO_INSTANCE_KEY_FILE=/run/secrets/instance_key
    ```

3. Redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.

!!! warning "🔑 Ne changez ni ne supprimez jamais la clé une fois utilisée"

    Seule la même clé peut relire ce qui a été chiffré avec elle.

    - Sauvegardez `secrets/` avec le reste du répertoire de données, et gardez les copies aussi privées que la base de données : [Sauvegarde](filesystem.md#backup).
    - Une fois que la clé existe, LibreFolio ne peut pas distinguer un `instance.key` perdu d'une première utilisation : il crée une nouvelle clé, et ce que l'ancienne a chiffré ne peut plus être lu. Lorsque vous restaurez les données, remettez `secrets/` avec elles avant de redémarrer LibreFolio. Ne démarrez jamais LibreFolio sur des données restaurées sans leur `secrets/`.
    - Si LibreFolio a déjà créé une nouvelle clé : arrêtez-le, placez votre copie de `instance.key` à la place de la nouvelle et redémarrez-le, avant que quiconque ne saisisse à nouveau un [secret de plugin](#plugin-secrets) : un secret saisi sous la nouvelle clé deviendrait illisible une fois l'ancienne rétablie.
    - `instance.key` présent mais endommagé ou inaccessible : LibreFolio consigne une erreur et ne le remplace jamais. Quoi faire : [Vérifications au démarrage](configuration_security.md#startup-checks).

### 🔏 Le contrôle de la clé {: #instance-key-check }

À côté de la clé, LibreFolio conserve une **valeur de contrôle** : `secrets/instance.key.check` dans le répertoire de données (dossier `0700`, fichier `0600`), une courte empreinte de la clé dont on ne peut pas déduire la clé. À chaque démarrage, il compare l'empreinte de la clé qu'il possède alors avec celle qui est stockée : elles diffèrent lorsqu'il démarre avec **une autre clé que celle avec laquelle les données ont été écrites** (une machine qui a reçu la mauvaise clé, un fichier de clé remplacé par un nouveau).

- **Le premier démarrage** écrit le fichier. Il ne l'écrit pas si des secrets de plugin enregistrés existent déjà et que la clé actuelle n'en lit aucun : il prendrait la mauvaise clé pour la bonne. Le contrôle indique alors que la clé ne correspond pas tant que vous n'avez pas rétabli la bonne.
- **Avec une clé qui ne correspond pas** : une erreur dans le journal au démarrage, et l'onglet **Sécurité** de Paramètres › Administration l'indique (le contrôle est `platform.instance_key_check`). **L'instance continue de fonctionner** : vos données ne dépendent pas de cette clé, seuls les secrets de plugin enregistrés en dépendent.

**La solution est la bonne clé.**

1. **Dans `.env` ou dans l'environnement du conteneur** (`LIBREFOLIO_INSTANCE_KEY` ou sa variable `_FILE`), ou **dans le répertoire de données** (`secrets/instance.key`), remettez la clé avec laquelle les données ont été écrites.
2. Redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`. La réponse suivante est `ok`, sans rien d'autre à faire.

**Pour changer réellement la clé**, par exemple lorsque vous décidez que les anciens secrets sont perdus et que les secrets de plugin sont saisis à nouveau :

1. **Dans `.env` ou dans l'environnement du conteneur**, ajoutez, pour **un seul démarrage** :

    ```env
    LIBREFOLIO_INSTANCE_KEY_ACCEPT=1
    ```

    Valeurs : `1` ou `0`, `true` ou `false`, `yes` ou `no`, `on` ou `off` ; toute autre valeur arrête le démarrage, en nommant la variable.

2. Redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`. Ce démarrage remplace la valeur de contrôle stockée par celle de la clé qu'il possède, et consigne un avertissement.

3. **Retirez la variable et redémarrez à nouveau.** Tant qu'elle est définie, chaque démarrage accepte la clé qu'il possède, quelle qu'elle soit, et la protection ne fait rien ; l'avertissement est consigné à chaque démarrage, en guise de rappel.

!!! note "📏 Ce que le contrôle ne peut pas voir"

    - Sans valeur de contrôle stockée et sans aucun secret de plugin enregistré, il n'y a rien à comparer : la réponse est `ok`. Le premier démarrage d'une instance dont la clé était déjà fausse ne peut pas être détecté ; à partir de là, la valeur stockée la protège.
    - Si les données reviennent sans leur dossier `secrets/`, la valeur est réécrite au démarrage suivant ; tant qu'elle est absente, les secrets de plugin décident.
    - Une valeur de contrôle illisible (une permission, un fichier endommagé) n'arrête jamais une sauvegarde : la réponse est `ok` et le journal contient un avertissement, une seule fois.

---

## 🧩 Paramètres des plugins {: #plugin-settings }

Un plugin peut demander ses propres paramètres : la clé API d'une source de données payante, une région, une préférence. Parmi les plugins fournis avec LibreFolio, deux en demandent un, une préférence de recherche personnelle chacun : justETF et Borsa Italiana. Aucun ne demande de paramètre à l'échelle de l'instance ; un plugin que vous ajoutez pourrait le faire. Deux types :

| Type | Qui l'enregistre | Qui le lit | Depuis une variable d'environnement |
| --- | --- | --- | --- |
| **À l'échelle de l'instance** | seulement un administrateur | chaque utilisateur lit une valeur non secrète ; d'une valeur secrète, comme une clé API, il sait seulement si elle est définie | oui : [Les variables](#plugin-variables) |
| **Personnel** | seulement cet utilisateur | seulement cet utilisateur ; les administrateurs ne le voient jamais | non |

**Où les modifier** : dans **Paramètres › Plugins**, un onglet dont dispose chaque utilisateur : les paramètres personnels chacun pour soi, ceux à l'échelle de l'instance seulement les administrateurs (les autres utilisateurs les voient en lecture seule). Dans la boîte de dialogue d'actif, **Configurer**, à côté du fournisseur de prix choisi, ouvre le même formulaire pour ce seul fournisseur. Ce que montre l'onglet, paramètre par paramètre : [Paramètres des plugins](../user/settings/plugins.md) dans le manuel utilisateur.

Les plugins qui ont des paramètres, avec les clés de leurs paramètres, sont listés par `GET /api/v1/settings/plugins` pour tout utilisateur connecté.

### 🏷️ Les variables {: #plugin-variables }

**Où** : dans `.env` ou dans l'environnement du conteneur, comme les autres options ; seulement pour les paramètres à l'échelle de l'instance. Le nom de la variable :

```text
LIBREFOLIO_PLUGIN_<KIND>_<PLUGIN CODE>_<SETTING KEY>
```

- `<KIND>` vaut `ASSET` pour un fournisseur de prix et `FX` pour un fournisseur de taux de change.
- Tout en majuscules ; chaque caractère autre qu'une lettre ou un chiffre devient `_`. Le paramètre `api_key` du fournisseur de prix `my_provider` :

    ```env
    LIBREFOLIO_PLUGIN_ASSET_MY_PROVIDER_API_KEY=<value>
    ```

- Chaque variable a aussi une forme `_FILE` : le chemin d'un fichier qui contient la valeur, comme un secret Docker, lu comme dans [Secrets dans des fichiers](#secret-files). Un fichier illisible n'arrête jamais le serveur : voir [ci-dessous](#plugin-variable-lock).
- Pour un paramètre secret, un plugin peut aussi accepter la variable qu'il lisait avant d'avoir des paramètres, afin qu'une installation existante continue de fonctionner. Lorsque les deux sont définies, le nom ci-dessus l'emporte.

Redémarrez ensuite LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.

### 🔒 Une variable verrouille le paramètre {: #plugin-variable-lock }

Tant que sa variable est définie, un paramètre en tire sa valeur et personne ne peut le modifier depuis LibreFolio : un enregistrement est refusé (`LOCKED_BY_ENV`), et une valeur enregistrée auparavant est ignorée jusqu'à ce que vous retiriez la variable et redémarriez. **Paramètres › Plugins** affiche le paramètre en lecture seule, un paramètre secret uniquement comme *Défini* : *Défini par la variable du serveur* et le nom de la variable pour les administrateurs, *Défini par le serveur* pour les autres utilisateurs.

**Une valeur incorrecte**, que le paramètre n'accepte pas, ou un fichier `_FILE` illisible, verrouille tout de même le paramètre, et le plugin n'est alors pas configuré : LibreFolio refuse toutes les requêtes qui lui sont adressées, même lorsque le paramètre est facultatif, jusqu'à ce que vous corrigiez la variable. Il ne se rabat jamais sur la valeur enregistrée ni sur la valeur par défaut du plugin.

- Dans le journal, un avertissement une fois par processus serveur : `Plugin setting variable invalid: the plugin is not configured until it is fixed`, avec la variable et la raison, jamais la valeur.
- Dans **Paramètres › Plugins**, le badge du plugin indique **À configurer** et le paramètre indique que sa variable est invalide.

Corrigez la valeur **dans `.env` ou dans l'environnement du conteneur**, puis redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.

### 🔐 Secrets enregistrés et clé d'instance {: #plugin-secrets }

Un paramètre enregistré dans LibreFolio est conservé dans la base de données. Un paramètre secret est d'abord chiffré (AES-256-GCM) avec une clé dérivée de la [clé d'instance](#instance-key), et n'est plus jamais affiché, pas même à celui qui l'a enregistré : **Paramètres › Plugins** indique seulement s'il est défini, *Défini le* et la date de son enregistrement. Une valeur fournie par une variable, secrète ou non, n'est jamais enregistrée dans la base de données.

**Si la clé d'instance change**, les secrets enregistrés ne peuvent plus être lus. LibreFolio les conserve, les signale comme illisibles et n'utilise jamais une valeur incorrecte. L'onglet l'indique sous chacun : *Enregistré, mais la clé de cette instance ne peut pas le lire. Si un administrateur peut remettre l'ancienne clé, c'est à faire d'abord ; sinon, saisissez-le à nouveau.* Dès le premier démarrage après le changement, et à chaque démarrage jusqu'à ce qu'ils soient saisis à nouveau ou que l'ancienne clé soit rétablie, le journal contient une erreur qui recense ceux à l'échelle de l'instance, s'il y en a : [Vérifications au démarrage](configuration_security.md#startup-checks).

| Situation | Que faire |
| --- | --- |
| Vous avez encore l'ancienne clé | Remettez-la, avant que quiconque ne saisisse à nouveau les secrets ([La clé d'instance](#instance-key) explique pourquoi). |
| Vous ne l'avez plus | Saisissez à nouveau chaque secret dans **Paramètres › Plugins**. |
| Vous voulez les importer dans une autre installation, qui conserve sa propre clé | **Depuis un terminal, sur cette installation**, restaurez une sauvegarde avec l'ancienne clé : `backup restore` avec `--instance-key-file` les rechiffre avec la clé de cette installation ([La clé d'instance d'une autre installation](cli_tools.md)). |

**Si `secrets/instance.key` est endommagé ou inaccessible**, LibreFolio démarre quand même, avec une erreur provenant des [vérifications au démarrage](configuration_security.md#startup-checks) ; une clé que vous avez définie vous-même et qui ne peut pas être utilisée fait échouer le démarrage à la place. Jusqu'à ce que vous corrigiez la situation :

- chaque secret enregistré est signalé comme illisible, et les plugins fonctionnent sans eux : un plugin qui en a besoin répond qu'il n'est pas configuré ;
- les secrets fournis par des variables continuent de fonctionner ;
- un nouveau secret ne peut pas être enregistré : l'onglet répond *Les secrets ne peuvent pas être enregistrés : la clé de cette instance est inutilisable (voir les contrôles de la configuration).*, et rien de cet enregistrement n'est écrit ;
- le journal contient une erreur de plus, la première fois que chaque processus serveur a besoin d'un secret enregistré : `Plugin secrets unreadable: the instance key cannot be used (see the configuration checks)`.

Corrigez le fichier **dans le répertoire de données**, ou restaurez-le depuis une sauvegarde : les secrets enregistrés reviennent. Une nouvelle clé ne les fait pas revenir : il faudrait les saisir à nouveau.

!!! warning "🗄️ La base de données et la clé dans un même dossier"

    La base de données (`sqlite/app.db`) et la clé d'instance que génère LibreFolio (`secrets/instance.key`) se trouvent dans le même [répertoire de données](filesystem.md) : quiconque obtient les deux, le dossier lui-même ou une copie de celui-ci, peut lire tous les secrets enregistrés.

    - Gardez privés le répertoire de données et toutes ses copies.
    - Mieux encore, fournissez la clé d'instance depuis un magasin de secrets, avec `LIBREFOLIO_INSTANCE_KEY_FILE` (un secret Docker) ou `LIBREFOLIO_INSTANCE_KEY` : LibreFolio ne l'écrit alors jamais dans le répertoire de données. Si `secrets/instance.key` existe déjà, utilisez son contenu comme valeur ([La clé d'instance](#instance-key)) : une autre clé rendrait les secrets enregistrés illisibles.

---

## 🔗 Voir aussi

- 📄 **[Configuration](configuration.md)** — Créer le fichier `.env`, options principales, paramètres définis par les outils, …
- 📄 **[Configuration : vérifications et protections](configuration_security.md)** — Vérifications au démarrage, protections du navigateur, arrêter le serveur
- 📄 **[Configuration : comptes et recherche d'actifs](configuration_accounts.md)** — Comptes et inscriptions, l'ordre des fournisseurs de prix dans la recherche, facultatif : recherche web pour de nouveaux actifs
