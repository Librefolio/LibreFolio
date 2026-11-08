# 🛡️ Configuration : vérifications et protections

Cette page traite de :

- les **vérifications au démarrage** : ce que signifie chaque constat, où le corriger et avec quelle valeur ;
- les **protections du navigateur** : la Content-Security-Policy et la protection des cadres ;
- l'**arrêt du serveur**.

Les options que ces vérifications examinent sont expliquées dans [Configuration](configuration.md) ; les secrets, dans
[Configuration : secrets et paramètres des plugins](configuration_secrets.md).

---

## 🩺 Vérifications au démarrage {: #startup-checks }

Juste après la ligne `Starting LibreFolio`, le serveur vérifie sa propre configuration sans rien modifier.

**Où les lire :**

| Où | Comment |
| --- | --- |
| Le journal du serveur | Une ligne par constat, au niveau correspondant, avec le nom de la vérification dans `check` (par exemple `platform.jwt_secret`). |
| **Paramètres › Administration › Sécurité** (administrateurs uniquement) | Les mêmes vérifications, dans la langue de l'application ; un nombre sur l'onglet compte les erreurs et les avertissements. Une fois que vous avez corrigé et redémarré, cliquez sur **Vérifier à nouveau** ([Sécurité](settings.md#security-tab)). |

**Où les corriger :** sauf indication contraire du tableau, dans le **fichier `.env`** de LibreFolio.
Redémarrez ensuite LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.

| Niveau | Ce que dit le journal (`check`) | Où | Que faire |
| --- | --- | --- | --- |
| ℹ️ `info` | `The session key is random: every restart signs everyone out. To stay signed in, set JWT_SECRET.` | `.env` | Rien, si déconnecter tout le monde à chaque redémarrage vous convient. Sinon, définissez `JWT_SECRET` : [Garder les utilisateurs connectés](index.md#session-persistence). |
| ⚠️ `warning` | `The session signing key from JWT_SECRET is … characters long: use at least 32 random characters` (ou `from JWT_SECRET_FILE (<path>)`) | `.env`, ou le fichier que nomme la ligne | Générez une clé d'au moins 32 caractères aléatoires, comme dans [Garder les utilisateurs connectés](index.md#session-persistence), et placez-la là où l'indique la ligne. |
| ⚠️ `warning` | `Set both directly and through a *_FILE variable: …` | `.env` | Pour chaque secret listé, ne gardez qu'un seul des deux : la variable elle-même l'emporte, le fichier est ignoré. |
| ❌ `error` | `The instance key cannot be used: …`, se terminant par `cannot be reached (Permission denied)` ou `cannot be read (…)` | Ligne de commande, sur le serveur : le dossier `secrets/` et `instance.key` | Ils appartiennent à un autre utilisateur, ou leurs permissions empêchent LibreFolio d'y accéder. Rendez-les tous deux à l'utilisateur qui exécute LibreFolio (`chown`), puis `chmod 700` sur le dossier et `chmod 600` sur le fichier. Ne remplacez jamais la clé par une nouvelle. Le serveur démarre quand même. |
| ❌ `error` | `The instance key cannot be used: …`, avec une autre raison, par exemple `is empty or blank` | Le fichier `secrets/instance.key` | Il est endommagé : restaurez-le depuis une sauvegarde, ne le remplacez jamais par une nouvelle clé. Le serveur démarre quand même. |
| ⚠️ `warning` | `… is open to other users (…): the folder should be 0700 and the file 0600` | Ligne de commande, sur le serveur | `chmod 700` sur le dossier `secrets/`, `chmod 600` sur `instance.key`. |
| ⚠️ `warning` | `SESSION_COOKIE_SECURE=never: the session cookie is sent over plain HTTP too; prefer auto` | `.env` | Revenez à `auto`, sauf si vous avez vraiment besoin de `never` : [`SESSION_COOKIE_SECURE`](configuration.md#session-cookie-secure). |
| ℹ️ `info` | `The log level is DEBUG: the log records operational detail; …` (ou `TRACE`) | `.env` | Revenez à `INFO` une fois le dépannage terminé. |
| ❌ `error` | `LIBREFOLIO_TEST_MODE is on outside a test lane: test-only providers are served, the data are kept in the test data directory <path> and .env is not read; unset it on a production instance` (`platform.test_mode`) | L'environnement du serveur, pas `.env` : cherchez d'où il vient, par exemple une unité de service | Retirez `LIBREFOLIO_TEST_MODE`, ou mettez-le à `0`, puis redémarrez. Le mode test est réservé aux tests propres à LibreFolio (`./dev.py test`, `./dev.py server --test`), qui l'activent et le désactivent d'eux-mêmes. D'ici là, le serveur travaille sur le dossier que nomme la ligne, pas sur votre [répertoire de données](filesystem.md) : ce que vous saisissez entre-temps y est enregistré. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore uploads answer 503 until it is fixed` (`backup.upload_limit`) | `.env` | Un nombre entier de mégaoctets, `0` pour aucune limite, ou retirez la variable ([La limite de téléversement d'une restauration](backup_restore.md#restore-upload-limit)). D'ici là, Paramètres › Administration › Sauvegarde ne peut pas téléverser d'archive à restaurer ; la ligne de commande en restaure toujours une. Le serveur démarre quand même. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore checks answer 503 until it is fixed` (`backup.restore_limit`) | `.env` | Comme ci-dessus, dans la variable que nomme la ligne. D'ici là, toute vérification d'une restauration est refusée avec `backup_restore_unavailable`, depuis Paramètres › Administration › Sauvegarde et depuis la ligne de commande, où `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` devant `backup restore` lève la limite pour cette commande. Le serveur démarre quand même. |
| ❌ `error` | `LIBREFOLIO_BACKUP_RECIPIENTS: item 2 is not an age recipient: …; the hosting panel's backups answer 503 until it is fixed` (ou `expected at most 2 recipients`, `repeats an earlier recipient`) (`backup.recipients`) | `.env` | Une ou deux clés publiques `age1…`, séparées par des virgules, telles que les fournit `backup keygen` ([Sauvegardes scellées](backup_sealed.md#sealed)). Le serveur démarre quand même. |
| ⚠️ `warning` | `LIBREFOLIO_LOGIN_LIMIT=off: failed sign-ins are not limited; turn it back on unless this is a test instance` (`accounts.login_limit`) | `.env` | Rien, sur une instance réservée aux tests. Sinon, retirez la variable, ou mettez-la à `on` : [Connexions échouées](configuration_accounts.md#login-limit). |
| ❌ `error` | `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` (`email.smtp`) | `.env`, la variable que nomme la ligne | Seul l'e-mail est désactivé, rien d'autre. Ce que signifie chaque code : [Problèmes de configuration](email_troubleshooting.md#configuration-problems). Le serveur démarre quand même. |
| ⚠️ `warning` | `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | `.env` | `LIBREFOLIO_SMTP_TLS=starttls` ou `tls`, ou envoyez via un relais de votre propre réseau : [Notes de sécurité](email_troubleshooting.md#security). |
| ℹ️ `info` | `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` (`email.links`) | `.env` | Rien, si aucun lien ne doit partir par e-mail. Sinon, mettez `LIBREFOLIO_PUBLIC_URL` à l'adresse à laquelle vos utilisateurs ouvrent LibreFolio ([Comptes et inscriptions](configuration_accounts.md#accounts), [E-mail](email.md)). |
| ⚠️ `warning` | `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` (`email.links`) | `.env` | Écrivez l'adresse avec `http://` ou `https://` et un nom d'hôte, sans nom d'utilisateur, mot de passe, `?` ni `#`, par exemple `https://librefolio.example.com` ([E-mail](email.md)). |
| ❌ `error` | `Stored plugin secrets that the instance key cannot read: <N>. Enter them again in the plugin settings, or restore the instance key they were saved with` (`platform.plugin_secrets` ; celle-ci intervient plus tard, une fois la base de données prête) | `secrets/instance.key` ou `LIBREFOLIO_INSTANCE_KEY` ; seulement en dernier recours **Paramètres › Plugins** | La clé d'instance a changé après l'enregistrement de ces [secrets de plugin](configuration_secrets.md#plugin-secrets) : procédure ci-dessous. Le serveur démarre quand même. |

??? note "🔑 Secrets de plugin illisibles : remettre l'ancienne clé"

    Causes : un `secrets/instance.key` perdu que LibreFolio a remplacé par une nouvelle clé, des données restaurées
    sans leur `secrets/`, ou un autre `LIBREFOLIO_INSTANCE_KEY`.

    Si le journal indique aussi `The instance key cannot be used: …`, corrigez cela d'abord (tableau ci-dessus).

    1. **Avez-vous encore l'ancienne clé ?** Votre copie de `secrets/instance.key`, sauvegardée avec le répertoire de
       données comme l'explique [La clé d'instance](configuration_secrets.md#instance-key), ou l'ancienne valeur de la
       variable. Une archive en clair créée avec **Sauvegarder l'instance** omet la clé ; une archive
       [sécurisée](backup_restore.md#secure) transporte la clé générée par LibreFolio, et sa restauration rechiffre
       ces secrets.
    2. **Arrêtez LibreFolio**, mettez l'ancienne clé à la place de la nouvelle, puis redémarrez.
       Les secrets sont de nouveau lisibles.

    !!! warning "⚠️ Avant que quiconque ne saisisse à nouveau un secret"

        Un secret saisi à nouveau est enregistré sous la nouvelle clé, et devient illisible une fois l'ancienne
        rétablie.

    Seulement si l'ancienne clé est perdue : saisissez à nouveau les secrets dans **Paramètres › Plugins**. À partir
    de là, la clé à sauvegarder est la nouvelle.

    Les secrets personnels ne sont pas comptés : chaque utilisateur voit les siens dans son propre onglet.

**Erreurs qui empêchent le démarrage.** Le serveur ne démarre pas, et l'erreur figure dans la sortie console (avec
Docker, `docker compose logs librefolio`) : elle nomme la variable et, lorsqu'il y en a un, le fichier, jamais le
secret. Corrigez-la, puis redémarrez.

| Cause | Où |
| --- | --- |
| Un `JWT_SECRET_FILE` ou un `LIBREFOLIO_INSTANCE_KEY_FILE` qui ne peut pas fournir son secret | Le fichier vers lequel pointe la variable ([Secrets dans des fichiers](configuration_secrets.md#secret-files)) |
| Une clé d'instance de votre cru de moins de 32 caractères | `.env`, `LIBREFOLIO_INSTANCE_KEY` |
| Un `LIBREFOLIO_LOGIN_LIMIT` autre que `on` ou `off` | `.env` ([Connexions échouées](configuration_accounts.md#login-limit)) |

---

## 🛡️ Protections du navigateur {: #browser-protections }

Chaque réponse de LibreFolio porte des en-têtes qui indiquent au navigateur comment protéger ses pages.

| En-tête | À définir ? | Ce qu'il fait |
| --- | --- | --- |
| `X-Content-Type-Options: nosniff` | Non, toujours présent | Le navigateur utilise le type que LibreFolio envoie : un fichier téléversé n'est jamais exécuté comme un script ni affiché comme une page. |
| `Referrer-Policy: strict-origin-when-cross-origin` | Non, toujours présent | Un autre site apprend au plus l'adresse de LibreFolio (`https://librefolio.example.com`), jamais la page d'où vient une requête. |
| `Content-Security-Policy` | Non, sur chaque page dans chaque profil, sans interrupteur | [La Content-Security-Policy](#csp). |
| `X-Frame-Options` + `frame-ancestors` | `LIBREFOLIO_FRAME_PROTECTION` dans `.env`, désactivé sur une installation personnelle | [Protection des cadres](#frame-protection). |
| `Content-Security-Policy-Report-Only` | `LIBREFOLIO_CSP_REPORT_ONLY` dans `.env`, désactivé sur une installation personnelle | [La politique en mode rapport seul](#csp-report-only). |

Les deux interrupteurs sont lus au démarrage : après un changement, redémarrez LibreFolio. Avec Docker Compose,
exécutez `docker compose up -d`. Pour les développeurs : [En-têtes de réponse](../developer/architecture/security.md#response-headers).

### 🛡️ La Content-Security-Policy {: #csp }

Elle indique au navigateur ce qu'une page peut exécuter et où elle peut se connecter. LibreFolio en **applique
toujours** une, dans chaque profil, sans aucun paramètre pour la désactiver. Dans le cas habituel, elle ne vous demande
rien : elle ne compte que lorsque quelque chose entre LibreFolio et le navigateur ajoute un script à la page
([Un script que vous n'avez pas envoyé](#csp-blocked-script)).

| Quoi | Politique | Effet |
|---|---|---|
| Chaque page de LibreFolio : l'application web, la documentation (`/mkdocs`) et, là où elles sont activées, les pages propres à l'API à `/api/v1/docs` et `/api/v1/redoc` | `object-src 'none'; base-uri 'self'; form-action 'self'` | Aucun contenu de plugin (`<object>`, `<embed>`), aucun `<base>` et aucun formulaire vers un autre site : LibreFolio n'en utilise aucun. Un PDF n'est pas une page : il ne porte rien de tout cela. |
| Les pages de l'application web | `script-src` : uniquement les scripts propres à LibreFolio ; ses scripts inline sont autorisés par leur empreinte (hash), calculée à partir des fichiers de l'application web | Un script écrit dans la page par quelqu'un d'autre ne s'exécute pas. |
| Les pages de l'application web | `worker-src 'self' blob:` | Les workers du lecteur PDF. |
| Les pages propres à l'API à `/api/v1/docs` et `/api/v1/redoc`, uniquement là où `LIBREFOLIO_API_DOCS` est activé | `script-src 'self' https://cdn.jsdelivr.net`, `worker-src 'self' blob:`, `connect-src 'self'` | Ce sont les pages de LibreFolio, pas celles de FastAPI : Swagger UI et ReDoc depuis `cdn.jsdelivr.net` à une version fixe, avec une somme de contrôle que le navigateur vérifie (Subresource Integrity). Les scripts de démarrage viennent de votre instance : aucun script inline, aucune police Google Fonts. Le worker est celui de la recherche de ReDoc. Là où les pages sont désactivées, rien de tout cela n'existe. |
| Les scripts du build de l'application web, les fichiers sous `/_app/` | `script-src 'self'`, le même `connect-src` que les pages, `worker-src 'self' blob:`, `object-src 'none'`, `base-uri 'self'` | Elle ne s'applique que si un navigateur exécute l'un de ces fichiers comme un **worker** : il charge les scripts de LibreFolio et rien d'autre, et ne se connecte que là où les pages le peuvent. Aujourd'hui, le seul worker lancé à partir d'un fichier est celui qui traite les prix ; le worker du lecteur PDF démarre à partir d'un `blob:` et conserve la politique de la page. |
| Les pages de l'application web | `connect-src 'self'`, l'origine de [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) lorsqu'elle est définie, et `https://api.github.com` uniquement sur une installation auto-hébergée | Où la page peut envoyer des requêtes. GitHub sert à vérifier l'existence d'une nouvelle version, vérification que votre navigateur effectue lorsqu'un administrateur se connecte (jamais dans le profil `managed`). |
| Chaque réponse, avec la [Protection des cadres](#frame-protection) activée | `frame-ancestors 'self'` | Seules les pages propres à LibreFolio peuvent l'afficher dans un cadre. |

Elle n'applique **pas** `default-src`, `style-src`, `img-src`, `font-src` ni `frame-src` : les images (les icônes des
actifs et des courtiers sont un lien vers n'importe quelle adresse), les styles, les polices et les cadres restent
libres. La possibilité qu'une autre page affiche LibreFolio dans un cadre est décidée par
[`LIBREFOLIO_FRAME_PROTECTION`](#frame-protection) seule.

Lorsque vous reconstruisez l'application web à partir des sources pendant que LibreFolio fonctionne, les empreintes
suivent le nouveau build : vous n'avez pas besoin de le redémarrer.

??? note "📄 L'aperçu PDF ne demande rien à un tiers"

    Le moteur du lecteur est la copie propre à LibreFolio, et `connect-src` reste limité à l'adresse propre à
    LibreFolio. Si cette copie est inaccessible, l'aperçu affiche le lecteur PDF de votre navigateur.

    La seule chose que le lecteur télécharge est le texte chinois, japonais et coréen, et il le demande à votre
    instance (`/api/v1/files/pdf-fonts/…`, pour les utilisateurs connectés uniquement). La première fois, **le
    serveur** télécharge la police depuis `cdn.jsdelivr.net` (adresse et version fixes), ne la conserve que si sa somme
    de contrôle (sha256) correspond à la liste livrée avec LibreFolio, et la stocke dans `cache/pdf-fonts/` à
    l'intérieur du [répertoire de données](filesystem.md).

    - Vous pouvez supprimer ce dossier : les polices sont retéléchargées lorsqu'un PDF en a besoin. Il ne fait pas
      partie d'une sauvegarde.
    - Une instance qui ne peut pas atteindre `cdn.jsdelivr.net` affiche ce PDF sans ces caractères.
    - Un fichier qui ne correspond pas à la liste est rejeté, et le journal contient un avertissement le nommant.

#### 🕵️ Un script que vous n'avez pas envoyé {: #csp-blocked-script }

Un proxy, un CDN ou une extension de navigateur qui **ajoute un script** aux pages de LibreFolio est bloqué, comme tout
autre élément que LibreFolio n'a pas envoyé.

**Ce que vous voyez :**

- la page fonctionne, mais peut perdre l'élément que fournissait ce script : un compteur, une adresse obfusquée, un
  widget de l'extension ;
- la console du navigateur affiche, une fois par chargement de page :

    ```text
    LibreFolio blocked a script it did not send (<source>): a proxy, a CDN or a browser extension adds it. Guide: https://<your address>/mkdocs/admin/configuration_security/#csp
    ```

    `<source>` est l'adresse d'où venait le script, ou `inline` pour un script écrit dans la page ;

- dans **Paramètres › Administration › Sécurité** ([Sécurité](settings.md#security-tab)), le navigateur qui l'a
  rencontré affiche l'avertissement *un script a été bloqué*, avec les sources. L'avertissement appartient à cet
  onglet du navigateur et disparaît à sa fermeture.

Rien n'est envoyé à votre serveur : ni rapport, ni requête. La console et l'onglet sont les seuls endroits où le
navigateur le signale.

**Que faire :** désactivez l'ajout pour l'adresse de LibreFolio. Aucun paramètre n'élargit la politique.

| Qui ajoute le script | Où le corriger | Que faire |
| --- | --- | --- |
| **Cloudflare** : Rocket Loader, Email Address Obfuscation, la configuration automatique de Web Analytics | Le tableau de bord Cloudflare, pour le nom d'hôte de LibreFolio | Désactivez Rocket Loader (*Speed › Optimization*), Email Address Obfuscation (*Scrape Shield*) et la configuration automatique de Web Analytics (*Analytics & Logs › Web Analytics*). Une *Configuration Rule* peut le faire pour cet hôte seul et laisser vos autres sites tels qu'ils sont. Les noms des menus changent de temps à autre. |
| **Nginx** : un `sub_filter` qui écrit un `<script>` dans les pages | La configuration Nginx, dans le `server` ou le `location` qui fait proxy vers LibreFolio | Retirez ce `sub_filter`. |
| **Une extension de navigateur** qui ajoute un script qui lui est propre à chaque page | Le navigateur | Désactivez-la pour l'adresse de LibreFolio, ou essayez la page dans une fenêtre privée, qui s'exécute généralement sans extensions. |

Rechargez ensuite la page : la ligne a disparu de la console. L'avertissement de l'onglet Sécurité reste jusqu'à ce que
vous fermiez cet onglet du navigateur.

#### 🔗 Une adresse publique qui ne peut pas être utilisée {: #csp-public-url }

`LIBREFOLIO_PUBLIC_URL` ajoute son origine (`scheme://host`, avec le port uniquement lorsqu'il ne s'agit pas de celui
par défaut) à `connect-src`. Une valeur inutilisable (sans `http://` ou `https://`, ou avec un nom d'utilisateur ou un
mot de passe) n'ajoute rien : le serveur démarre et sert comme d'habitude, et le journal contient l'avertissement
*LIBREFOLIO_PUBLIC_URL cannot be used*.

Corrigez la valeur dans **`.env`** ([Comptes et inscriptions](configuration_accounts.md#accounts)).
Redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.

#### 📡 La vérification d'adresse d'un lien de partage {: #csp-address-check }

Le champ **Adresse du serveur** des dialogues d'invitation et de réinitialisation de mot de passe de l'onglet
[Utilisateurs](users.md#server-address) ne demande pas de données à l'adresse : la politique l'en empêcherait. Il
charge une minuscule image transparente depuis l'adresse que vous avez saisie, `/api/v1/auth/address-probe.png`, que la
politique autorise, et lit sa taille : une taille indique que **cette** instance répond à cette adresse, une autre
qu'autre chose y répond. Les messages disent les mêmes choses qu'avant.

### 🖼️ Protection des cadres {: #frame-protection }

Elle décide si une page à **une autre adresse** peut afficher LibreFolio dans un cadre. Une autre adresse, c'est un
autre nom d'hôte, ou le même sur un autre port : un tableau de bord Home Assistant à `http://homeassistant.local:8123`
qui affiche LibreFolio depuis `http://homeassistant.local:6040`.

| `LIBREFOLIO_FRAME_PROTECTION` | Effet |
| --- | --- |
| `false`, la valeur par défaut sur une installation personnelle | N'importe quelle page peut afficher LibreFolio dans un cadre. |
| `true` | Seules les pages propres à LibreFolio peuvent l'afficher dans un cadre ; partout ailleurs, le navigateur refuse de l'afficher. |

**Quand l'activer :** sur une installation personnelle, laissez-la désactivée si une de vos pages affiche LibreFolio
dans un cadre, comme un tableau de bord Home Assistant : avec l'interrupteur activé, le navigateur refuserait d'y
afficher LibreFolio. Si aucune de vos pages ne le fait, activez-la : aucun autre site ne pourra afficher LibreFolio
dans ses propres pages.

1. **Dans le fichier `.env`**, ajoutez :

    ```env
    LIBREFOLIO_FRAME_PROTECTION=true
    ```

2. Redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.
   Chaque réponse porte désormais `X-Frame-Options: SAMEORIGIN` et `Content-Security-Policy: frame-ancestors 'self'`, la
   même règle dans l'en-tête plus ancien et dans le plus récent.

Lorsque l'interrupteur est activé :

- le même champ `Content-Security-Policy` porte aussi les trois règles que [LibreFolio applique à ses pages](#csp) dans
  chaque profil (`object-src 'none'`, `base-uri 'self'`, `form-action 'self'`) : elles ne dépendent pas de cet
  interrupteur. Un PDF ne conserve que `frame-ancestors 'self'`, pour que le navigateur puisse encore l'afficher ;
- une réponse `304 Not Modified` ne reçoit que `X-Frame-Options`, pour que le navigateur conserve la politique de la
  copie qu'il possède déjà.

C'est la vérification `platform.frame_protection` des [vérifications au démarrage](#startup-checks). Elle passe
toujours, et le journal n'en dit rien ; **Paramètres › Administration › Sécurité** la liste parmi les
[vérifications réussies](settings.md#security-passed) :

| Interrupteur | L'onglet dit |
| --- | --- |
| Activé | *Seules les pages de LibreFolio peuvent l'afficher dans un cadre.* |
| Désactivé, sur une installation personnelle | *Des pages à une autre adresse, comme vos tableaux de bord, peuvent afficher LibreFolio dans un cadre : le réglage par défaut d'une installation personnelle.* |

### 📋 La politique en mode rapport seul {: #csp-report-only }

`LIBREFOLIO_CSP_REPORT_ONLY` ajoute aux pages de l'application web une seconde politique, **plus large** que la
[Content-Security-Policy](#csp) appliquée : elle indique aussi d'où une page peut charger ses images, ses styles, ses
polices et ses cadres. Elle est en mode rapport seul : le navigateur ne bloque rien et liste ce qui sort de son
périmètre dans sa console de développement, et nulle part ailleurs. La politique appliquée reste active quelle que soit
la valeur.

| `LIBREFOLIO_CSP_REPORT_ONLY` | Effet |
| --- | --- |
| `false`, la valeur par défaut sur une installation personnelle | Aucune politique en mode rapport seul. |
| `true` | Les pages de l'application web portent `Content-Security-Policy-Report-Only`. |

**Quand l'activer :** sur une installation personnelle, ce n'est pas nécessaire : vos utilisateurs ne voient aucune
différence. Activez-la pour voir, dans la console de développement du navigateur, ce qu'une politique de ce type
bloquerait sur votre instance.

1. **Dans le fichier `.env`**, ajoutez :

    ```env
    LIBREFOLIO_CSP_REPORT_ONLY=true
    ```

2. Redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.
   Les pages de l'application web portent désormais l'en-tête `Content-Security-Policy-Report-Only`.

Lorsque l'interrupteur est activé :

- la documentation (`/mkdocs`), tout ce qui se trouve sous `/api/`, y compris les pages de documentation de l'API, les
  fichiers que chargent les pages et une réponse `304 Not Modified` ne la portent pas ;
- la politique autorise ce qui vient de l'adresse propre à LibreFolio et quelques exceptions dont l'application a
  besoin : les images de n'importe quelle adresse `https://` (les icônes des actifs et des courtiers sont un lien), les
  styles inline et le WebAssembly du lecteur PDF. Pour les développeurs, directive par directive :
  [La Content-Security-Policy et la protection des cadres](../developer/architecture/security.md#managed-headers) ;
- les scripts inline de l'application web sont autorisés par leurs empreintes, comme dans la politique appliquée : après
  avoir reconstruit l'application web à partir des sources, vous n'avez pas besoin de redémarrer LibreFolio ;
- chaque ligne que cette politique ajoute à la console dit ce qu'elle **aurait** bloqué : rien ne l'a été. Un script que
  la politique appliquée bloque a sa propre ligne : [Un script que vous n'avez pas envoyé](#csp-blocked-script).

C'est la vérification `platform.csp_report_only` des [vérifications au démarrage](#startup-checks). Elle passe
toujours, et le journal n'en dit rien ; **Paramètres › Administration › Sécurité** la liste parmi les
[vérifications réussies](settings.md#security-passed) :

| Interrupteur | L'onglet dit |
| --- | --- |
| Activé | Une ligne indiquant que les pages de l'application web portent une politique en mode rapport seul. |
| Désactivé, sur une installation personnelle | *Aucune Content-Security-Policy en mode rapport seul : le réglage par défaut d'une installation personnelle.* |

---

## ⏹️ Arrêter le serveur {: #shutdown }

Lorsqu'on lui demande de s'arrêter, le serveur doit le faire dans le **budget d'arrêt** : 8 secondes sauf si vous le
modifiez, comptées à partir du signal (SIGTERM venant de `docker stop`, `docker compose down` ou d'un redémarrage ;
SIGINT venant de Ctrl+C).

**Où :** dans le **fichier `.env`**.

| Variable | Valeur par défaut | Ce qu'elle fait |
| --- | --- | --- |
| `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` | `8` | Le budget d'arrêt, en secondes : un nombre entier de `2` à `600`, ou `0` pour aucune limite, comme avant la version 1.3. Une valeur inutilisable n'empêche pas le serveur de démarrer, contrairement aux [options principales](configuration.md#main-options) : le journal indique `Shutdown budget setting cannot be used: the default applies`, et le budget reste à 8 secondes. |
| `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` | 3/8 du budget | Combien de secondes uvicorn, le serveur web, attend les requêtes en cours : `3` avec le budget par défaut. L'image Docker et `./dev.py server` le calculent à partir du budget. Une valeur de votre cru l'emporte : gardez-la inférieure au budget, qui compte toujours pour l'arrêt complet. |

Le budget est consommé dans cet ordre :

1. **Les requêtes en cours** : le serveur web n'en accepte plus de nouvelles et accorde à celles déjà en cours 3/8 du
   budget, 3 secondes par défaut. Il annule ensuite celles qui sont encore en cours, comme un long import de courtier :
   ce qu'elles n'avaient pas encore enregistré revient à l'état précédent (rollback), et elles sont répétées une fois
   LibreFolio revenu.
2. **Le travail propre au serveur** : les synchronisations planifiées, les processus worker, les caches… s'arrêtent les
   uns après les autres, chacun dans le temps restant. La dernière étape termine les processus enfants encore en cours
   (imports de courtiers, simulations de risque, Outils) : aucun ne survit au serveur.
3. **Budget épuisé** : si quelque chose retient encore le serveur, il se termine quand même avec le code de sortie 1, et
   le journal indique ce qui était encore en cours : `Shutdown budget exhausted: ending the process`.

!!! warning "🐳 Accordez au conteneur plus de temps que le budget"

    Docker accorde 10 secondes à un conteneur pour s'arrêter, puis le tue : le budget par défaut de 8 secondes convient.
    Si vous augmentez `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`, accordez au conteneur au moins 2 secondes de plus, sinon
    Docker tue le serveur au bout de 10 secondes, quel que soit son budget.

    **Dans `docker-compose.yml`**, sur le service `librefolio`, laissez le reste tel quel et ajoutez :

    ```yaml
    services:
      librefolio:
        stop_grace_period: 32s  # for LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=30
    ```

    Exécutez ensuite `docker compose up -d`.

`./dev.py server` conserve cette marge de lui-même : après un Ctrl+C, il attend jusqu'au budget plus 2 secondes, puis
termine le serveur ([Démarrer le serveur](cli_tools.md#start-the-server)).

---

## 🔗 Voir aussi

- 📄 **[Configuration](configuration.md)** — Créer le fichier `.env`, Options principales, Paramètres définis par les outils, …
- 📄 **[Configuration : secrets et paramètres des plugins](configuration_secrets.md)** — Secrets, Paramètres des plugins
- 📄 **[Configuration : comptes et recherche d'actifs](configuration_accounts.md)** — Comptes et inscriptions, L'ordre des fournisseurs de prix dans la recherche, Facultatif : recherche web pour de nouveaux actifs
- 📄 **[Paramètres globaux](settings.md#security-tab)** — L'onglet Sécurité
