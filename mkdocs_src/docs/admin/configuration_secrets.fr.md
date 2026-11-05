# 🔐 Configuration : secrets et paramètres des plugins

Cette page décrit ce qui doit rester privé dans une installation LibreFolio : les options qui sont des **secrets** (clés, mots de passe et jetons), qui peuvent aussi être lues depuis des fichiers tels que les secrets Docker, la **clé d'instance** qui protège ce que stocke LibreFolio, et les **paramètres des plugins**, y compris les clés API.

Vous découvrez le fichier `.env` ? Comment le créer, les options principales et la valeur qui l'emporte se trouvent dans [Configuration](configuration.md) ; cette page approfondit les secrets.

---

## 🔐 Secrets {: #secrets }

Ces options sont des secrets : gardez-les aussi privés que la base de données. Chacune peut être écrite dans `.env` ou lue depuis un fichier.

| Secret | Depuis un fichier | Ce que c'est |
| --- | --- | --- |
| `JWT_SECRET` | `JWT_SECRET_FILE` | La clé qui signe les sessions de connexion, dans les [options principales](configuration.md). |
| `LIBREFOLIO_INSTANCE_KEY` | `LIBREFOLIO_INSTANCE_KEY_FILE` | La [clé d'instance](#instance-key). Non définie : LibreFolio en crée une dans le répertoire de données. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` | La clé d'un service de recherche payant, pour le moteur `apikey` de la [recherche web](configuration_accounts.md#optional-web-search-for-new-assets). Contrairement aux deux premières, un fichier qui ne peut pas la fournir n'arrête pas le serveur : il désactive seulement la recherche web. |
| `LIBREFOLIO_SMTP_PASSWORD` | `LIBREFOLIO_SMTP_PASSWORD_FILE` | Le mot de passe du serveur SMTP qui envoie les e-mails de LibreFolio : voir [E-mail](email.md). Comme pour la clé de recherche web, un fichier qui ne peut pas le fournir n'arrête pas le serveur : il désactive seulement l'envoi d'e-mails. |

Un plugin peut avoir ses propres secrets, comme la clé API d'une source de données payante : voir [Paramètres des plugins](#plugin-settings).

### 📄 Secrets dans des fichiers {: #secret-files }

Ajoutez `_FILE` au nom d'un secret et indiquez le chemin d'un fichier qui le contient. C'est ainsi que Docker et Kubernetes transmettent leurs secrets, comme `/run/secrets/jwt_secret` : le secret reste hors de `.env` et hors de l'environnement du conteneur.

- Le secret est le texte du fichier, sans les sauts de ligne à sa fin et sans la marque d'ordre des octets que certains éditeurs Windows placent à son début. Tout autre espace compte, au début comme à la fin.
- Un chemin relatif part du dossier du projet.
- Un secret ou sa variable `_FILE` qui est vide ou ne contient que des espaces est considéré comme non défini : un espace parasite n'est jamais utilisé comme clé.
- Définissez l'un des deux. Lorsque les deux sont définis, la variable elle-même l'emporte, le fichier est ignoré et le journal de démarrage contient un [avertissement](configuration_security.md#startup-checks).
- Pour `JWT_SECRET_FILE`, `LIBREFOLIO_INSTANCE_KEY_FILE` et `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE`, un fichier manquant, illisible, vide ou ne contenant que des espaces et des sauts de ligne, qui n'est pas du texte UTF-8 ou qui dépasse 64 Kio arrête le serveur au démarrage. L'erreur nomme la variable et le chemin, jamais le secret.
- `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` n'est lu que lorsqu'une recherche utilise le moteur `apikey`. Un fichier qui ne peut pas fournir la clé n'arrête pas le serveur : la recherche continue sans la recherche web, avec un avertissement dans le journal (`web_link_finder: …; disabling`), et la recherche propre aux fournisseurs continue de fonctionner.
- `LIBREFOLIO_SMTP_PASSWORD_FILE` n'est lu que lorsque `LIBREFOLIO_SMTP_HOST` est défini. Comme pour le fichier de clé de recherche web, un fichier qui ne peut pas fournir le mot de passe n'arrête pas le serveur : l'envoi d'e-mails reste désactivé, avec une erreur dans le journal (`Email configuration cannot be used: email stays off`).
- LibreFolio lit ces variables depuis son environnement : `./dev.py` et Docker Compose (`env_file: .env`) y placent les valeurs de `.env`, de sorte que `.env` fonctionne avec les deux.

??? example "🐳 Un secret Docker avec Docker Compose"

    1. Enregistrez une nouvelle clé dans un fichier à côté de `docker-compose.yml` :

        ```bash
        python3 -c "import secrets; print(secrets.token_urlsafe(64))" > jwt_secret.txt
        ```

    2. Ajoutez les lignes marquées à `docker-compose.yml`, et conservez le reste du service tel quel :

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

    3. Si `.env` donne une valeur à `JWT_SECRET`, supprimez cette ligne : elle l'emporterait sur le fichier. Une ligne `JWT_SECRET=` vide ne pose pas de problème. Exécutez ensuite `docker compose up -d`.

    Compose monte le fichier dans le conteneur tel qu'il est sur l'hôte, avec son propriétaire et ses permissions.
    LibreFolio y fonctionne en tant qu'utilisateur de l'image, `1000:1000` pour l'image officielle (voir
    [Docker avancé](docker_advanced.md)), et cet utilisateur doit pouvoir lire le fichier. Avec l'image
    officielle, par exemple : `sudo chown 1000:1000 jwt_secret.txt`, puis
    `sudo chmod 600 jwt_secret.txt`. Sinon, le serveur s'arrête au démarrage et l'erreur indique que le
    fichier ne peut pas être lu (`cannot be read`).

    `LIBREFOLIO_INSTANCE_KEY_FILE`, `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` et
    `LIBREFOLIO_SMTP_PASSWORD_FILE` sont montées de la même manière ; ce que fait chacune lorsque son fichier
    ne peut pas fournir le secret est décrit dans [Secrets dans des fichiers](#secret-files).

### 🗝️ La clé d'instance {: #instance-key }

La clé d'instance est un secret propre à chaque installation : LibreFolio en dérive ses clés de chiffrement. Il n'y a rien à configurer. LibreFolio utilise la première clé qu'il trouve :

1. `LIBREFOLIO_INSTANCE_KEY`, la clé elle-même ;
2. `LIBREFOLIO_INSTANCE_KEY_FILE`, un fichier qui la contient, comme un secret Docker ;
3. `secrets/instance.key` dans le répertoire de données, que LibreFolio crée la première fois qu'il a besoin de la clé : 43 caractères aléatoires, dans un dossier et un fichier que seul l'utilisateur exécutant LibreFolio peut ouvrir (`0700` et `0600`).

Une clé que vous fournissez doit être aléatoire et comporter au moins 32 caractères, comme la sortie de
`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. N'utilisez jamais de phrase de passe : les clés
que LibreFolio en dérive ne sont pas plus solides que la phrase de passe.

Dans un déploiement cloud, la clé peut provenir de l'environnement ou d'un secret Docker au lieu du
répertoire de données. Donnez à chaque instance sa propre clé : ne partagez jamais une même clé entre plusieurs instances.

!!! warning "🔑 Ne changez ni ne supprimez jamais la clé une fois utilisée"

    Seule la même clé peut relire ce qui a été chiffré avec elle.

    - Sauvegardez `secrets/` avec le reste du répertoire de données, et gardez les copies aussi privées que la
      base de données : voir [Sauvegarde](filesystem.md#backup).
    - Une fois que la clé existe, LibreFolio ne peut pas distinguer un `instance.key` perdu d'une première utilisation : il crée une
      nouvelle clé, et ce que l'ancienne a chiffré ne peut plus être lu. Lorsque vous restaurez les données, remettez
      `secrets/` avec elles avant de redémarrer LibreFolio. Ne démarrez jamais LibreFolio sur des données restaurées
      sans leur `secrets/`. Si LibreFolio a déjà créé une nouvelle clé, arrêtez-le, placez votre
      copie de `instance.key` à la place de la nouvelle et redémarrez-le, avant que quiconque ne saisisse à nouveau un
      [secret de plugin](#plugin-secrets) : un secret saisi sous la nouvelle clé deviendrait
      illisible une fois l'ancienne clé rétablie.
    - Si `instance.key` est présent mais endommagé ou inaccessible, LibreFolio consigne une erreur et ne le
      remplace jamais : voir quoi faire dans [Contrôles au démarrage](configuration_security.md#startup-checks).
    - Définir `LIBREFOLIO_INSTANCE_KEY` là où `secrets/instance.key` existe déjà change la clé. Pour
      déplacer la clé vers l'environnement ou vers un secret Docker, utilisez le contenu de `secrets/instance.key`
      comme valeur.

### 🔏 Le contrôle de la clé {: #instance-key-check }

LibreFolio conserve, à côté de la clé, une **valeur de contrôle** : une courte empreinte de la clé dans le fichier
`secrets/instance.key.check` du répertoire de données (dossier `0700`, fichier `0600`). Ce n'est pas la clé, et la clé
ne peut pas être déduite de cette valeur. À chaque démarrage, LibreFolio compare l'empreinte de
la clé qu'il possède alors avec celle qu'il a stockée. Elles diffèrent lorsque LibreFolio démarre avec **une autre clé que celle avec laquelle
les données ont été écrites** : une machine qui a reçu la mauvaise clé, un fichier de clé remplacé par un nouveau.

- **Le premier démarrage** écrit le fichier. Si des secrets de plugin enregistrés existent déjà et que la clé actuelle n'en lit
  aucun, LibreFolio ne l'écrit pas : il prendrait la mauvaise clé pour la bonne. Le contrôle
  indique alors que la clé ne correspond pas tant que vous n'avez pas rétabli la bonne clé.
- **Avec une clé qui ne correspond pas**, le journal contient une erreur au démarrage,
  l'onglet Sécurité de Paramètres › Administration l'indique (le contrôle est `platform.instance_key_check`). **L'instance continue de fonctionner** : vos données ne dépendent pas de cette
  clé, seuls les secrets de plugin enregistrés en dépendent.
- **La solution est la bonne clé.** Rétablissez-la, avec `LIBREFOLIO_INSTANCE_KEY`, sa variable `_FILE` ou le fichier
  `secrets/instance.key` des données, puis redémarrez LibreFolio : la réponse suivante est `ok`, sans rien d'autre à faire.
- **Pour changer réellement la clé**, par exemple lorsque vous décidez que les anciens secrets sont perdus et que les secrets de plugin
  sont saisis à nouveau, définissez `LIBREFOLIO_INSTANCE_KEY_ACCEPT=1` pour **un seul démarrage**. Ce démarrage remplace la valeur de contrôle stockée
  par celle de la clé qu'il possède, et consigne un avertissement. **Retirez ensuite la variable et redémarrez** : tant qu'elle est
  définie, chaque démarrage accepte la clé qu'il possède, quelle qu'elle soit, et la protection ne fait rien (l'avertissement est consigné à chaque démarrage, en guise de rappel).
  Les valeurs sont `1` ou `0`, `true` ou `false`, `yes` ou `no`, `on` ou `off` ; toute autre valeur arrête le démarrage, en nommant la variable.

!!! note "📏 Ce que le contrôle ne peut pas voir"

    Sans valeur de contrôle stockée et sans aucun secret de plugin enregistré, il n'y a rien à comparer, donc
    la réponse est `ok` : le premier démarrage d'une instance dont la clé était déjà fausse ne peut pas être détecté. À partir de
    là, la valeur stockée la protège. Si les données reviennent sans leur dossier `secrets/`, la valeur
    est réécrite au démarrage suivant, et les secrets de plugin décident tant qu'elle est absente. Une valeur de contrôle illisible
    (un problème de permissions, un fichier endommagé) n'empêche jamais une sauvegarde : la réponse est `ok` et le journal contient un avertissement, une seule fois.

---

## 🧩 Paramètres des plugins {: #plugin-settings }

Un plugin peut demander ses propres paramètres : la clé API d'une source de données payante, une région, une
préférence. Parmi les plugins fournis avec LibreFolio, deux en demandent un, une préférence de recherche personnelle
chacun : justETF et Borsa Italiana. Aucun ne demande de paramètre à l'échelle de l'instance ; un plugin que vous ajoutez pourrait le faire. Un
paramètre est de l'un des deux types suivants :

- **À l'échelle de l'instance** : une valeur pour toute l'instance, que seul un administrateur peut enregistrer. Chaque
  utilisateur peut lire une valeur non secrète, et, pour une valeur secrète, comme une clé API, uniquement savoir si elle est définie.
- **Personnel** : la valeur propre à chaque utilisateur, que seul cet utilisateur peut enregistrer et lire. Les administrateurs ne
  la voient jamais.

Les paramètres personnels et ceux à l'échelle de l'instance se modifient dans **Paramètres › Plugins**, un onglet dont dispose chaque utilisateur :
chaque utilisateur y modifie les siens, et les administrateurs modifient aussi ceux à l'échelle de l'instance, que
les autres utilisateurs voient en lecture seule. Dans la boîte de dialogue d'actif, **Configurer**, à côté du fournisseur de prix
choisi, ouvre le même formulaire pour ce seul fournisseur. Ce que montre l'onglet, paramètre par paramètre :
[Paramètres des plugins](../user/settings/plugins.md) dans le manuel utilisateur.

Un paramètre à l'échelle de l'instance peut aussi être fourni par une variable d'environnement, dans `.env` ou dans
l'environnement du conteneur comme les autres options ; un paramètre personnel ne le peut pas. Les plugins qui ont
des paramètres, avec les clés de leurs paramètres, sont listés par `GET /api/v1/settings/plugins` pour tout
utilisateur connecté.

### 🏷️ Les variables {: #plugin-variables }

LibreFolio construit le nom de la variable à partir du type de plugin, du code du plugin et de la
clé du paramètre :

```text
LIBREFOLIO_PLUGIN_<KIND>_<PLUGIN CODE>_<SETTING KEY>
```

- `<KIND>` vaut `ASSET` pour un fournisseur de prix et `FX` pour un fournisseur de taux de change.
- Le nom entier est en majuscules, et chaque caractère autre qu'une lettre ou un chiffre devient `_` :
  le paramètre `api_key` du fournisseur de prix `my_provider` est
  `LIBREFOLIO_PLUGIN_ASSET_MY_PROVIDER_API_KEY`.
- Pour un paramètre secret, un plugin peut aussi accepter la variable qu'il lisait avant d'avoir des paramètres, afin
  qu'une installation existante continue de fonctionner. Lorsque les deux sont définies, le nom ci-dessus l'emporte.
- Chaque variable a aussi une forme `_FILE`, le chemin d'un fichier qui contient la valeur, comme un secret
  Docker. Le fichier est lu comme dans [Secrets dans des fichiers](#secret-files), mais un fichier illisible n'arrête jamais
  le serveur : voir ci-dessous.

### 🔒 Une variable verrouille le paramètre {: #plugin-variable-lock }

Tant que sa variable est définie, un paramètre en tire sa valeur, et personne ne peut le modifier depuis
LibreFolio : un enregistrement est refusé (`LOCKED_BY_ENV`), et une valeur enregistrée auparavant est ignorée jusqu'à
ce que vous retiriez la variable et redémarriez. **Paramètres › Plugins** affiche le paramètre en lecture seule, un paramètre secret
uniquement comme *Défini* : *Défini par la variable du serveur* et le nom de la variable pour les administrateurs, *Défini par le
serveur* pour les autres utilisateurs.

- Une valeur incorrecte, que le paramètre n'accepte pas, ou un fichier `_FILE` illisible, verrouille tout de même le
  paramètre, et le plugin n'est alors pas configuré : LibreFolio refuse toutes les requêtes qui lui sont adressées, même lorsque
  le paramètre est facultatif, jusqu'à ce que vous corrigiez la variable. Il ne se rabat jamais sur la valeur enregistrée ni sur
  la valeur par défaut du plugin. Le journal explique pourquoi, avec un avertissement une fois par processus serveur :
  `Plugin setting variable invalid: the plugin is not configured until it is fixed`, avec la
  variable et la raison, jamais la valeur. Dans **Paramètres › Plugins**, le badge du plugin indique
  **À configurer**, et le paramètre indique que sa variable est invalide. Corrigez la valeur, puis redémarrez.

### 🔐 Secrets enregistrés et clé d'instance {: #plugin-secrets }

Un paramètre enregistré dans LibreFolio est conservé dans la base de données. Un paramètre secret est d'abord chiffré
(AES-256-GCM) avec une clé dérivée de la [clé d'instance](#instance-key), et n'est plus jamais affiché,
pas même à celui qui l'a enregistré : LibreFolio indique seulement s'il est défini (dans **Paramètres › Plugins**,
*Défini le* et la date à laquelle il a été enregistré). Une valeur fournie par une variable, secrète ou non, n'est jamais enregistrée dans
la base de données.

Si la clé d'instance change, les secrets enregistrés ne peuvent plus être lus. LibreFolio les conserve et
les signale comme illisibles, et n'utilise jamais une valeur incorrecte. L'onglet l'indique sous chacun :
*Enregistré, mais la clé de cette instance ne peut pas le lire. Si un administrateur peut rétablir l'ancienne clé,
c'est la première chose à faire ; sinon, saisissez-le à nouveau.* Si vous avez encore l'ancienne
clé, rétablissez-la avant que quiconque ne les saisisse à nouveau : un secret saisi sous la nouvelle clé deviendrait
illisible une fois l'ancienne rétablie. Pour les importer dans une autre installation, qui conserve sa propre
clé, restaurez-y une sauvegarde avec l'ancienne clé : `backup restore` avec `--instance-key-file`
les rechiffre avec la clé de cette installation ([La clé d'instance d'une autre
installation](cli_tools.md)). Dès le premier démarrage après le changement, et à chaque démarrage
jusqu'à ce qu'ils soient saisis à nouveau ou que l'ancienne clé soit rétablie, le journal contient une erreur qui recense
ceux à l'échelle de l'instance, s'il y en a : voir [Contrôles au démarrage](configuration_security.md#startup-checks).

Si `secrets/instance.key` est endommagé ou inaccessible, LibreFolio démarre quand même, avec une erreur provenant
des [contrôles au démarrage](configuration_security.md#startup-checks) ; une clé que vous avez définie vous-même et qui ne peut pas être utilisée fait échouer le démarrage
à la place. Jusqu'à ce que vous corrigiez la situation :

- chaque secret enregistré est signalé comme illisible, et les plugins fonctionnent sans eux : un plugin qui en a besoin
  répond qu'il n'est pas configuré ;
- les secrets fournis par des variables continuent de fonctionner ;
- un nouveau secret ne peut pas être enregistré : l'onglet répond *Les secrets ne peuvent pas être enregistrés : la clé de cette instance ne peut pas
  être utilisée (voir les contrôles de configuration).*, et rien de cet enregistrement n'est écrit ;
- le journal contient une erreur de plus, la première fois que chaque processus serveur a besoin d'un secret enregistré :
  `Plugin secrets unreadable: the instance key cannot be used (see the configuration checks)`.

Corrigez le fichier, ou restaurez-le depuis une sauvegarde, et les secrets enregistrés reviennent. Une nouvelle clé ne les fait pas
revenir : il faudrait les saisir à nouveau.

!!! warning "🗄️ La base de données et la clé dans un même dossier"

    La base de données (`sqlite/app.db`) et la clé d'instance que génère LibreFolio
    (`secrets/instance.key`) se trouvent dans le même [répertoire de données](filesystem.md) : quiconque obtient les deux, le
    dossier lui-même ou une copie de celui-ci, peut lire tous les secrets enregistrés.

    - Gardez privés le répertoire de données et toutes ses copies.
    - Mieux encore, fournissez la clé d'instance depuis un magasin de secrets, avec `LIBREFOLIO_INSTANCE_KEY_FILE` (un
      secret Docker) ou `LIBREFOLIO_INSTANCE_KEY` : LibreFolio ne l'écrit alors jamais dans le répertoire
      de données. Si LibreFolio a déjà créé `secrets/instance.key`, utilisez son contenu comme
      valeur, comme l'explique [La clé d'instance](#instance-key) : une autre clé rendrait les secrets enregistrés
      illisibles.

---

## 🔗 Voir aussi

- 📄 **[Configuration](configuration.md)** — Créer le fichier `.env`, options principales, paramètres définis par les outils, …
- 📄 **[Configuration : contrôles et protections](configuration_security.md)** — Contrôles au démarrage, protections du navigateur, arrêt du serveur
- 📄 **[Configuration : comptes et recherche d'actifs](configuration_accounts.md)** — Comptes et inscriptions, ordre des fournisseurs de prix dans la recherche, facultatif : recherche web pour les nouveaux actifs
