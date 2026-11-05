# 🛡️ Configuration : vérifications et protections

Cette page couvre ce que LibreFolio vérifie dans sa configuration au démarrage, ce que signifie chaque
constat et ce qu'il faut faire, les protections qu'il demande au navigateur (la **Content-Security-Policy**
et la protection des cadres), et comment il s'arrête.

Les options que ces vérifications examinent sont expliquées dans [Configuration](configuration.md), la
première page du guide, et les secrets qu'elles mentionnent dans
[Configuration : secrets et paramètres des plugins](configuration_secrets.md).

---

## 🩺 Vérifications au démarrage {: #startup-checks }

Juste après sa ligne `Starting LibreFolio`, le serveur vérifie sa configuration. Il ne change rien :
chaque constat est une ligne du journal, à son niveau, avec le nom de la vérification dans `check`, par
exemple `platform.jwt_secret`.

Les mêmes vérifications, à la demande, se trouvent dans l'onglet **Sécurité** de **Paramètres › Administration**,
pour les administrateurs : formulées dans la langue de l'application, les erreurs et avertissements comptés
par un nombre sur l'onglet, et relues avec **Vérifier à nouveau** une fois que vous avez corrigé la
configuration et redémarré (voir « Sécurité » dans [Paramètres globaux](settings.md)).

| Niveau | Ce que dit le journal | Que faire |
| --- | --- | --- |
| ℹ️ `info` | `The session key is random: every restart signs everyone out. To stay signed in, set JWT_SECRET.` | Rien, si déconnecter tout le monde à chaque redémarrage vous convient. Sinon, voir [Garder les utilisateurs connectés](index.md#session-persistence). |
| ⚠️ `warning` | `The session signing key from JWT_SECRET is … characters long: use at least 32 random characters` (ou `from JWT_SECRET_FILE (<path>)`) | Générez une clé plus longue, comme dans [Garder les utilisateurs connectés](index.md#session-persistence), et placez-la là où l'indique la ligne. |
| ⚠️ `warning` | `Set both directly and through a *_FILE variable: …` | Pour chaque secret listé, ne gardez qu'un seul des deux : la variable elle-même l'emporte, le fichier est ignoré. |
| ❌ `error` | `The instance key cannot be used: …`, se terminant par `cannot be reached (Permission denied)` ou `cannot be read (…)` | Le dossier `secrets/` ou `instance.key` appartient à un autre utilisateur, ou ses permissions empêchent LibreFolio d'y accéder. Rendez-les tous deux à l'utilisateur qui exécute LibreFolio (`chown`), puis `chmod 700` sur le dossier et `chmod 600` sur le fichier. Ne remplacez jamais la clé par une nouvelle. Le serveur démarre quand même. |
| ❌ `error` | `The instance key cannot be used: …`, se terminant par une autre raison, par exemple `is empty or blank` | `instance.key` est endommagée : restaurez-la depuis une sauvegarde, ne la remplacez jamais par une nouvelle clé. Le serveur démarre quand même. |
| ⚠️ `warning` | `… is open to other users (…): the folder should be 0700 and the file 0600` | Restreignez-les : `chmod 700` sur le dossier `secrets/`, `chmod 600` sur `instance.key`. |
| ⚠️ `warning` | `SESSION_COOKIE_SECURE=never: the session cookie is sent over plain HTTP too; prefer auto` | Revenez à `auto` sauf si vous avez vraiment besoin de `never` : voir [HTTPS et proxys inverses](configuration.md). |
| ℹ️ `info` | `The log level is DEBUG: the log records operational detail; …` (ou `TRACE`) | Revenez à `INFO` une fois le dépannage terminé. |
| ❌ `error` | `LIBREFOLIO_TEST_MODE is on outside a test lane: test-only providers are served, the data are kept in the test data directory <path> and .env is not read; unset it on a production instance` (`check` est `platform.test_mode`) | Le mode test est réservé aux exécutions de test propres à LibreFolio (`./dev.py test`, `./dev.py server --test`), qui l'activent et le désactivent d'eux-mêmes : retirez `LIBREFOLIO_TEST_MODE` de l'environnement du serveur, ou mettez-le à `0`, puis redémarrez : cherchez d'où vient l'environnement du serveur, par exemple une unité de service. D'ici là, le serveur travaille sur le dossier nommé par la ligne au lieu de votre [répertoire de données](filesystem.md) : ce qui est saisi entre-temps y est enregistré, pas avec vos données. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore uploads answer 503 until it is fixed` (`check` est `backup.upload_limit`) | Écrivez un nombre entier de mégaoctets, `0` pour aucune limite, ou retirez la variable, puis redémarrez ([La limite de téléversement d'une restauration](backup_restore.md#restore-upload-limit)). D'ici là, Paramètres › Administration › Sauvegarde ne peut pas téléverser d'archive à restaurer ; la ligne de commande en restaure toujours une. Le serveur démarre quand même. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore checks answer 503 until it is fixed` (`check` est `backup.restore_limit`) | Écrivez un nombre entier de mégaoctets, `0` pour aucune limite, dans la variable nommée par la ligne, ou retirez-la, puis redémarrez ([La limite de téléversement d'une restauration](backup_restore.md#restore-upload-limit)). D'ici là, toute vérification d'une restauration est refusée avec `backup_restore_unavailable`, depuis Paramètres › Administration › Sauvegarde et depuis la ligne de commande, où `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` devant `backup restore` lève la limite pour cette commande. Le serveur démarre quand même. |
| ❌ `error` | `LIBREFOLIO_BACKUP_RECIPIENTS: item 2 is not an age recipient: …; the hosting panel's backups answer 503 until it is fixed` (ou `expected at most 2 recipients`, `repeats an earlier recipient`) (`check` est `backup.recipients`) | Écrivez une ou deux clés publiques `age1…`, séparées par des virgules, telles que les fournit `backup keygen`, puis redémarrez ([Sauvegardes scellées](backup_sealed.md#sealed)). Le serveur démarre quand même. |
| ⚠️ `warning` | `LIBREFOLIO_LOGIN_LIMIT=off: failed sign-ins are not limited; turn it back on unless this is a test instance` (`check` est `accounts.login_limit`) | Rien, sur une instance réservée aux tests. Sinon, retirez la variable, ou mettez-la à `on`, puis redémarrez : voir [Connexions échouées](configuration_accounts.md#login-limit). |
| ❌ `error` | `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` (`check` est `email.smtp`) | L'e-mail est désactivé, rien d'autre ne l'est : corrigez la variable nommée par la ligne, puis redémarrez. Ce que signifie chaque code : [Problèmes de configuration](email_troubleshooting.md#configuration-problems). Le serveur démarre quand même. |
| ⚠️ `warning` | `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | Mettez `LIBREFOLIO_SMTP_TLS` à `starttls` ou `tls`, ou envoyez via un relais de votre propre réseau : voir [Notes de sécurité](email_troubleshooting.md#security). |
| ℹ️ `info` | `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` (`check` est `email.links`) | Rien, si aucun lien ne doit partir par e-mail. Sinon, mettez `LIBREFOLIO_PUBLIC_URL` à l'adresse à laquelle vos utilisateurs ouvrent LibreFolio ([Comptes et inscriptions](configuration_accounts.md#accounts)), puis redémarrez : voir [E-mail](email.md). |
| ⚠️ `warning` | `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` (`check` est `email.links`) | Écrivez l'adresse avec `http://` ou `https://` et un nom d'hôte, sans nom d'utilisateur, mot de passe, `?` ni `#`, par exemple `https://librefolio.example.com`, puis redémarrez : voir [E-mail](email.md). |
| ❌ `error` | `Stored plugin secrets that the instance key cannot read: <N>. Enter them again in the plugin settings, or restore the instance key they were saved with` (`check` est `platform.plugin_secrets` ; celle-ci intervient plus tard au démarrage, une fois la base de données prête) | La clé d'instance a changé après l'enregistrement de ces [secrets de plugin](configuration_secrets.md#plugin-secrets) propres à l'instance : un `secrets/instance.key` perdu que LibreFolio a remplacé par une nouvelle clé, des données restaurées sans leur `secrets/`, ou un autre `LIBREFOLIO_INSTANCE_KEY`. Si vous avez encore l'ancienne clé (votre copie de `secrets/instance.key`, sauvegardée avec le répertoire de données comme l'explique [La clé d'instance](configuration_secrets.md#instance-key), puisqu'une archive en clair de **Sauvegarder l'instance** omet la clé, tandis qu'une archive [sécurisée](backup_restore.md#secure) transporte la clé générée par LibreFolio et sa restauration rechiffre ces secrets ; ou l'ancienne valeur de la variable), arrêtez LibreFolio, mettez-la à la place de la nouvelle et redémarrez. Faites-le avant que quiconque ne saisisse à nouveau un secret : un secret saisi à nouveau est enregistré sous la nouvelle clé, et devient illisible une fois l'ancienne rétablie. Seulement si l'ancienne clé est perdue, saisissez à nouveau les secrets dans **Paramètres › Plugins** : à partir de là, la nouvelle clé est celle à sauvegarder. Si le journal indique aussi `The instance key cannot be used: …`, corrigez cela d'abord : voir ci-dessus. Les secrets personnels ne sont pas comptés : chaque utilisateur voit les siens dans son propre onglet. Le serveur démarre quand même. |

En revanche, certains secrets que vous avez configurés empêchent le démarrage lorsqu'ils ne peuvent pas
être utilisés : un `JWT_SECRET_FILE` ou un
`LIBREFOLIO_INSTANCE_KEY_FILE` qui ne peut pas fournir son secret (voir [Secrets dans des fichiers](configuration_secrets.md#secret-files)),
ou une clé d'instance que vous avez définie vous-même et qui fait moins de 32 caractères. L'erreur figure dans la sortie
console du serveur (`docker compose logs librefolio` avec Docker) : elle nomme la variable, et le fichier
lorsqu'il y en a un, jamais le secret. Corrigez-la, puis redémarrez.

Il en va de même pour un `LIBREFOLIO_LOGIN_LIMIT` autre que `on` ou `off`
([Connexions échouées](configuration_accounts.md#login-limit)).

---

## 🛡️ Protections du navigateur {: #browser-protections }

Chaque réponse de LibreFolio porte des en-têtes qui indiquent au navigateur comment protéger ses pages.
Trois sont toujours présents, sans rien à configurer :

- `X-Content-Type-Options: nosniff` : le navigateur utilise le type que LibreFolio envoie et n'en devine
  jamais un autre, si bien qu'un fichier téléversé n'est jamais exécuté comme un script ni affiché comme
  une page.
- `Referrer-Policy: strict-origin-when-cross-origin` : un autre site apprend au plus l'adresse de
  LibreFolio, par exemple `https://librefolio.example.com`, jamais la page d'où vient une requête.
- Une `Content-Security-Policy` sur chaque page, dans chaque profil, sans aucun interrupteur pour la
  désactiver : voir [La Content-Security-Policy](#csp).

Deux autres sont des interrupteurs, définis chacun séparément, désactivés sur une installation qui vous est
propre : [Protection des cadres](#frame-protection) et
[La politique Report-Only](#csp-report-only). LibreFolio lit les deux au démarrage : redémarrez-le après
un changement. Pour les développeurs : [En-têtes de réponse](../developer/architecture/security.md#response-headers).

### 🛡️ La Content-Security-Policy {: #csp }

Une Content-Security-Policy indique au navigateur ce qu'une page peut exécuter et où elle peut se
connecter. LibreFolio **en applique toujours** une, dans chaque profil : aucun paramètre ne permet de la
désactiver. Elle reste aussi étroite que possible tout en permettant à LibreFolio de fonctionner comme il l'a toujours fait,
et n'est élargie que là où LibreFolio en a réellement besoin. Elle ne vous demande rien dans le cas
habituel : elle ne compte que lorsque quelque chose entre LibreFolio et le navigateur ajoute un script à la page
([Un script que vous n'avez pas envoyé](#csp-blocked-script)).

| Quoi | Politique | Pourquoi |
|---|---|---|
| Chaque page de LibreFolio : l'application web, la documentation (`/mkdocs`) et, là où elles sont activées, les pages propres à l'API à `/api/v1/docs` et `/api/v1/redoc` | `object-src 'none'; base-uri 'self'; form-action 'self'` | Aucun contenu de plugin (`<object>`, `<embed>`) ; aucun élément `<base>` envoyant les liens de la page vers un autre site ; aucun formulaire envoyant ses données vers un autre site. LibreFolio n'en utilise aucun. Un PDF n'est pas une page : il ne porte rien de tout cela |
| Les pages de l'application web | `script-src` : uniquement les scripts propres à LibreFolio. Ses scripts inline sont autorisés par leur empreinte (hash), que LibreFolio calcule à partir des fichiers de l'application web, si bien qu'un script écrit dans la page par quelqu'un d'autre ne s'exécute pas | Un script que LibreFolio n'a pas envoyé est le moyen par lequel une page est détournée |
| Les pages de l'application web | `worker-src 'self' blob:` | Les workers du lecteur PDF |
| Les pages propres à l'API à `/api/v1/docs` et `/api/v1/redoc`, uniquement lorsque `LIBREFOLIO_API_DOCS` est activé | `script-src 'self' https://cdn.jsdelivr.net`, `worker-src 'self' blob:`, `connect-src 'self'` | Les deux pages sont celles de LibreFolio, non celles de FastAPI : elles chargent Swagger UI et ReDoc depuis `cdn.jsdelivr.net` à une version exacte, et le navigateur refuse un fichier dont la somme de contrôle (Subresource Integrity) n'est pas celle attendue par LibreFolio. Leurs scripts de démarrage viennent de votre instance, si bien que les pages ne contiennent aucun script inline et n'utilisent aucune police Google Fonts. Le worker est celui de la recherche de ReDoc. Là où les pages sont désactivées, rien de tout cela n'existe |
| Les scripts du build de l'application web, les fichiers sous `/_app/` | `script-src 'self'`, le même `connect-src` que les pages, `worker-src 'self' blob:`, `object-src 'none'`, `base-uri 'self'` | Une politique pour le cas où un navigateur exécute l'un de ces fichiers comme un **worker** : il peut charger les scripts propres à LibreFolio et rien d'autre, et se connecter uniquement là où les pages le peuvent. Un navigateur l'ignore pour tout script qui n'est pas un worker. Aujourd'hui, le seul worker lancé à partir d'un fichier est celui qui traite les prix ; le worker du lecteur PDF démarre à partir d'un `blob:` et conserve la politique de la page |
| Les pages de l'application web | `connect-src 'self'`, l'origine de [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) lorsqu'elle est définie, et `https://api.github.com` uniquement sur une installation auto-hébergée | Où la page peut envoyer des requêtes. L'adresse publique est celle que vous indiquez aux utilisateurs de LibreFolio pour y accéder ; GitHub sert à vérifier l'existence d'une version plus récente, vérification que votre navigateur effectue lorsqu'un administrateur se connecte (le profil `managed` ne l'effectue jamais) |
| Chaque réponse, lorsque la [Protection des cadres](#frame-protection) est activée | `frame-ancestors 'self'` | Seules les pages propres à LibreFolio peuvent l'afficher dans un cadre |

**L'aperçu PDF ne demande rien à un tiers.** Le moteur du lecteur est la copie propre à LibreFolio, et
`connect-src` reste sur l'adresse propre à LibreFolio. Si cette copie est inaccessible, l'aperçu affiche à
la place le lecteur PDF de votre navigateur. Le texte chinois, japonais et coréen est la seule chose que
le lecteur récupère, et il la récupère depuis votre instance, non depuis un tiers : lorsqu'un PDF a
besoin d'une telle police, la page la demande à LibreFolio (`/api/v1/files/pdf-fonts/…`, pour les
utilisateurs connectés uniquement). La première fois, **le serveur** télécharge le fichier depuis
`cdn.jsdelivr.net` (une adresse fixe, à une version fixe), ne le conserve que si sa somme de contrôle
(sha256) correspond à la liste livrée avec LibreFolio, et le stocke dans `cache/pdf-fonts/` à l'intérieur du
[répertoire de données](filesystem.md). Il est sans danger de supprimer ce dossier : les polices sont
retéléchargées lorsqu'un PDF en a besoin, et il ne fait pas partie d'une sauvegarde. Une instance qui ne peut
pas atteindre `cdn.jsdelivr.net` affiche un tel PDF sans ces caractères ; un fichier qui ne correspond pas à
la liste est rejeté, et le journal contient un avertissement le nommant.

Ce que la politique n'applique **pas** : `default-src`, `style-src`, `img-src`, `font-src` et
`frame-src`. Les images (les icônes des actifs et des courtiers sont définies par un lien vers n'importe
quelle adresse), les styles, les polices et les cadres restent libres ; la possibilité qu'une autre page
affiche LibreFolio dans un cadre est décidée par `LIBREFOLIO_FRAME_PROTECTION` seule, puisqu'afficher
LibreFolio dans un tableau de bord est un usage légitime d'une installation qui vous est propre.

Rien ne change pour ce que LibreFolio fait de lui-même. Lorsque vous reconstruisez l'application web à
partir des sources pendant que LibreFolio fonctionne, les empreintes suivent le nouveau build : vous n'avez
pas besoin de le redémarrer.

#### 🕵️ Un script que vous n'avez pas envoyé {: #csp-blocked-script }

Un proxy, un CDN ou une extension de navigateur qui **ajoute un script** aux pages de LibreFolio est bloqué,
comme tout autre élément que LibreFolio n'a pas envoyé. Cas typiques :

- Le **Rocket Loader** de Cloudflare, son **Email Address Obfuscation** et la configuration automatique de
  son **Web Analytics**, qui réécrivent la page ou y ajoutent un script à son passage ;
- un `sub_filter` Nginx qui écrit un `<script>` dans les pages ;
- une extension de navigateur qui ajoute un script qui lui est propre à chaque page.

Ce que vous voyez :

- la page fonctionne, mais peut perdre l'élément que fournissait ce script : un compteur, une adresse
  obfusquée, un widget de l'extension ;
- la console du navigateur affiche, une fois par chargement de page, `LibreFolio blocked a script it did not send
  (<source>): a proxy, a CDN or a browser extension adds it. Guide:
  https://<your address>/mkdocs/admin/configuration_security/#csp`, où `<source>` est l'adresse d'où venait
  le script, ou `inline` pour un script écrit dans la page ;
- dans l'onglet [Sécurité](settings.md) de **Paramètres › Administration**, le navigateur
  qui l'a rencontré liste un avertissement, *un script a été bloqué*, nommant les sources. L'avertissement
  appartient à cet onglet du navigateur et disparaît à sa fermeture.

Rien n'est envoyé à votre serveur : ni rapport, ni requête. La console et l'onglet sont les seuls
endroits où le navigateur le signale.

Que faire : **désactivez l'ajout pour l'adresse de LibreFolio**. La politique n'est pas élargie par un
paramètre, car un script ajouté en chemin est exactement ce qu'elle est là pour arrêter.

- **Cloudflare** : pour le nom d'hôte de LibreFolio, désactivez Rocket Loader (*Speed › Optimization*), Email
  Address Obfuscation (*Scrape Shield*) et la configuration automatique de Web Analytics (*Analytics & Logs ›
  Web Analytics*). Une *Configuration Rule* peut le faire pour cet hôte seul et laisser vos autres sites tels
  qu'ils sont. Les noms des menus changent de temps à autre.
- **Nginx** : retirez, du bloc `server` ou `location` qui fait proxy vers LibreFolio, le `sub_filter` qui ajoute le script.
- **Une extension de navigateur** : désactivez-la pour l'adresse de LibreFolio, ou essayez la page dans une fenêtre privée,
  qui s'exécute généralement sans extensions.

Rechargez ensuite la page : la ligne a disparu de la console. L'avertissement de l'onglet Sécurité reste
jusqu'à ce que vous fermiez cet onglet du navigateur.

#### 🔗 Une adresse publique qui ne peut pas être utilisée {: #csp-public-url }

`LIBREFOLIO_PUBLIC_URL` ajoute son origine (`scheme://host`, avec le port uniquement lorsqu'il ne s'agit pas de
celui par défaut) à `connect-src`. Une valeur inutilisable, par exemple sans `http://` ou
`https://`, ou avec un nom d'utilisateur ou un mot de passe, n'ajoute rien : le serveur démarre et sert comme d'habitude,
et le journal contient un avertissement, *LIBREFOLIO_PUBLIC_URL cannot be used*. Corrigez la valeur, puis redémarrez : voir
[Comptes et inscriptions](configuration_accounts.md#accounts).

#### 📡 La vérification d'adresse d'un lien de partage {: #csp-address-check }

La vérification de l'**Adresse du serveur** dans les dialogues d'invitation et de réinitialisation de mot de passe de
l'onglet [Utilisateurs](users.md#server-address) ne demande plus de données à l'adresse : la politique empêcherait la
page de le faire. Elle charge une minuscule image transparente depuis l'adresse que vous avez saisie,
`/api/v1/auth/address-probe.png`, ce que la politique autorise, et lit sa taille : une taille indique que
**cette** instance répond à cette adresse, une autre qu'autre chose y répond. Ce que disent les messages est
identique à avant.

### 🖼️ Protection des cadres {: #frame-protection }

`LIBREFOLIO_FRAME_PROTECTION` décide si une page à une autre adresse peut afficher LibreFolio dans un
cadre. Une autre adresse, c'est un autre nom d'hôte, ou le même sur un autre port : un tableau de bord Home Assistant
à `http://homeassistant.local:8123` qui affiche LibreFolio depuis
`http://homeassistant.local:6040` est une page à une autre adresse.

- **Désactivé** (`false`), la valeur par défaut sur une installation qui vous est propre : n'importe quelle page peut afficher LibreFolio dans un cadre.
- **Activé** (`true`) : seules les pages propres à LibreFolio peuvent l'afficher dans
  un cadre. Partout ailleurs, le navigateur refuse de l'afficher.

Lorsque l'interrupteur est activé :

- chaque réponse porte `X-Frame-Options: SAMEORIGIN` et
  `Content-Security-Policy: frame-ancestors 'self'`, la même règle dans l'en-tête plus ancien et dans le
  plus récent ;
- le même champ `Content-Security-Policy` porte aussi les trois règles que
  [LibreFolio applique à ses pages](#csp) dans chaque profil : `object-src 'none'`,
  `base-uri 'self'` et `form-action 'self'`. Elles ne dépendent pas de cet interrupteur. Un PDF ne conserve que
  `frame-ancestors 'self'`, pour que le navigateur puisse encore l'afficher ;
- une réponse `304 Not Modified` ne reçoit que `X-Frame-Options`, pour que le navigateur conserve la politique de
  la copie qu'il possède déjà.

Quand le modifier :

- **Sur une installation qui vous est propre**, laissez-le désactivé si une de vos pages affiche LibreFolio dans un cadre, comme
  un tableau de bord Home Assistant : avec l'interrupteur activé, le navigateur refuserait d'y afficher LibreFolio.
  Si aucune de vos pages ne le fait, vous pouvez l'activer, afin qu'aucun autre site ne puisse afficher LibreFolio
  dans ses propres pages.

C'est la vérification `platform.frame_protection` des [vérifications au démarrage](#startup-checks), également dans
l'onglet [Sécurité](settings.md) de **Paramètres › Administration** :

- La vérification passe, et le journal n'en dit rien. L'onglet la liste parmi les
  [vérifications réussies](settings.md) : *Seules les pages propres à LibreFolio peuvent l'afficher dans un
  cadre.* lorsque l'interrupteur est activé, *Les pages à une autre adresse, comme vos tableaux de bord, peuvent afficher
  LibreFolio dans un cadre : la valeur par défaut d'une installation qui vous est propre.* lorsque l'interrupteur est désactivé sur une installation
  qui vous est propre.

### 📋 La politique Report-Only {: #csp-report-only }

La [Content-Security-Policy](#csp) que LibreFolio applique est étroite à dessein : elle laisse libres les images,
les styles, les polices et les cadres. `LIBREFOLIO_CSP_REPORT_ONLY` ajoute une seconde politique, **plus large**, aux
pages de l'application web : l'ensemble de la politique visée par LibreFolio, qui indique aussi d'où une page peut charger
ses images, ses styles, ses polices et ses cadres. Elle est en mode rapport uniquement : le navigateur la vérifie et ne bloque
rien. Elle signale dans la console de développement ce qui sort de son périmètre, et nulle part ailleurs, puisque la politique
ne nomme aucune adresse où envoyer un rapport. La politique appliquée reste active quelle que soit la valeur de cet interrupteur.

- **Désactivé** (`false`), la valeur par défaut sur une installation qui vous est propre.
- **Activé** (`true`).

Lorsque l'interrupteur est activé :

- les pages de l'application web portent un en-tête `Content-Security-Policy-Report-Only`. La documentation
  (`/mkdocs`), tout ce qui se trouve sous `/api/`, y compris les pages de documentation de l'API, et les fichiers que
  chargent les pages ne le portent pas, pas plus qu'une réponse `304 Not Modified` ;
- la politique autorise ce qui vient de l'adresse propre à LibreFolio, et quelques exceptions dont l'application a besoin,
  comme les images de n'importe quelle adresse `https://` (les icônes des actifs et des courtiers sont définies par un lien),
  les styles inline et le WebAssembly du lecteur PDF. Pour les développeurs, la politique entière, directive
  par directive :
  [La Content-Security-Policy et la protection des cadres](../developer/architecture/security.md#managed-headers) ;
- les scripts inline propres à l'application web sont autorisés par leurs empreintes, qui suivent les fichiers de l'application web, comme dans la politique appliquée : après avoir reconstruit l'application web à partir des sources, vous n'avez pas besoin
  de redémarrer LibreFolio ;
- chaque ligne que cette politique ajoute à la console dit ce qu'elle aurait bloqué : rien ne l'a été. Un script
  que la politique appliquée bloque est une autre chose, et a sa propre ligne : voir
  [Un script que vous n'avez pas envoyé](#csp-blocked-script).

Quand la modifier :

- **Sur une installation qui vous est propre**, il n'est pas nécessaire de l'activer : vos utilisateurs ne voient aucune différence
  dans un sens ou dans l'autre. Activez-la si vous voulez voir, dans la console de développement du navigateur, ce qu'une telle politique
  bloquerait sur votre instance.

C'est la vérification `platform.csp_report_only` des [vérifications au démarrage](#startup-checks), également dans
l'onglet [Sécurité](settings.md) de **Paramètres › Administration** :

- La vérification passe, et le journal n'en dit rien. L'onglet la liste parmi les
  [vérifications réussies](settings.md) : une ligne indiquant que les pages de l'application web portent une
  politique en mode rapport uniquement, lorsque l'interrupteur est activé, *Aucune Content-Security-Policy en mode rapport uniquement : la valeur par défaut
  d'une installation qui vous est propre.* lorsque l'interrupteur est désactivé sur une installation qui vous est propre.

---

## ⏹️ Arrêter le serveur {: #shutdown }

Lorsqu'on demande au serveur de s'arrêter, cela doit se faire dans une limite de temps, le **budget d'arrêt** :
8 secondes sauf si vous le modifiez, comptées à partir du signal (SIGTERM venant de `docker stop`,
`docker compose down` ou d'un redémarrage ; SIGINT venant de Ctrl+C). La plupart du temps, les utilisateurs ne remarquent rien,
si ce n'est des redémarrages plus rapides et plus propres.

| Variable | Valeur par défaut | Ce qu'elle fait |
| --- | --- | --- |
| `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` | `8` | Le budget d'arrêt, en secondes : un nombre entier de `2` à `600`, ou `0` pour aucune limite, comme avant la version 1.3. Une valeur inutilisable n'empêche pas le serveur de démarrer, contrairement aux [options principales](configuration.md) : le journal indique `Shutdown budget setting cannot be used: the default applies`, et le budget reste à 8 secondes. |
| `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` | 3/8 du budget | Combien de secondes uvicorn, le serveur web, attend les requêtes en cours : `3` avec le budget par défaut. L'image Docker et `./dev.py server` le calculent à partir du budget. Une valeur que vous définissez vous-même l'emporte : gardez-la inférieure au budget, qui compte toujours pour l'arrêt complet. |

Le budget est consommé dans cet ordre :

1. **Les requêtes en cours** : le serveur web n'en accepte plus de nouvelles et accorde à celles déjà en cours 3/8 du
   budget, 3 secondes par défaut. Il annule ensuite celles qui sont encore en cours, comme un long import de courtier
   : ce qu'elles n'avaient pas encore enregistré est annulé, si bien qu'elles peuvent simplement être répétées une fois
   LibreFolio revenu.
2. **Le travail propre au serveur** : les synchronisations planifiées, les processus worker, les caches… s'arrêtent les uns après
   les autres, chacun dans le temps restant. La dernière étape termine les processus enfants encore en cours
   (imports de courtiers, simulations de risque, Outils), afin qu'aucun ne survive au serveur.
3. **Quand le budget est épuisé** : si quelque chose retient encore le serveur, il se termine quand même, avec le code
   de sortie 1, et son journal indique ce qui était encore en cours : `Shutdown budget exhausted: ending the process`.

!!! warning "🐳 Accordez au conteneur plus de temps que le budget"

    Docker accorde par défaut 10 secondes à un conteneur pour s'arrêter, puis le tue : le budget par défaut de
    8 secondes convient. Si vous augmentez `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`, accordez au conteneur au moins
    2 secondes de plus : définissez `stop_grace_period` sur le service `librefolio` de `docker-compose.yml`, laissez
    le reste du service tel quel, puis exécutez `docker compose up -d`.

    ```yaml
    services:
      librefolio:
        stop_grace_period: 32s  # for LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=30
    ```

    Sinon, Docker tue le serveur au bout de 10 secondes, quel que soit son budget.

`./dev.py server` conserve cette marge de lui-même : après un Ctrl+C, il attend jusqu'au budget plus 2 secondes
pour cet arrêt, puis termine le serveur ([Démarrer le serveur](cli_tools.md#start-the-server)).

---

## 🔗 Voir aussi

- 📄 **[Configuration](configuration.md)** — Créer le fichier `.env`, Options principales, Paramètres définis par les outils, …
- 📄 **[Configuration : secrets et paramètres des plugins](configuration_secrets.md)** — Secrets, Paramètres des plugins
- 📄 **[Configuration : comptes et recherche d'actifs](configuration_accounts.md)** — Comptes et inscriptions, L'ordre des fournisseurs de prix dans la recherche, Facultatif : recherche web pour de nouveaux actifs
