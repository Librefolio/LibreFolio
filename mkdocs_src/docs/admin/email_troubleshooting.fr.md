# 🛠️ E-mail : quand cela ne fonctionne pas

Page de diagnostic : les e-mails ne partent pas.
Pour chaque erreur, vous trouvez **ce que vous voyez**, **pourquoi** et **que faire**, avec l’endroit où agir.

Comment configurer l’e-mail et son e-mail de test : [E-mail](email.md).
Les messages que LibreFolio envoie : [E-mail : liens et messages](email_flows.md).

---

## 🛠️ Quand cela ne fonctionne pas {: #troubleshooting }

Deux sortes de problèmes :

| Ce que vous voyez | Pourquoi | Où regarder |
| --- | --- | --- |
| État **Ne fonctionne pas** dès l’ouverture de l’onglet **E-mail** | Une variable que LibreFolio ne peut pas utiliser | [Problèmes de configuration](#configuration-problems) |
| L’erreur n’apparaît qu’à l’envoi d’un e-mail | Le serveur SMTP refuse l’e-mail ou ne répond pas | [Erreurs d’envoi](#sending-errors) |

Une configuration inutilisable désactive seulement l’e-mail : le serveur démarre comme d’habitude et tout le reste fonctionne.

Où agir, dans les tableaux de cette page :

| Où | Quoi | Ensuite |
| --- | --- | --- |
| **`.env`** — le fichier `.env` de LibreFolio ([où il se trouve](email.md#where-it-lives)) | Les variables `LIBREFOLIO_SMTP_…` et `LIBREFOLIO_PUBLIC_URL` | Redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`. |
| **Serveur SMTP** — le serveur ou le fournisseur | Identifiant, expéditeurs autorisés, certificat, relais | Réessayez l’e-mail de test. |
| **Interface** — **Paramètres › Administration › E-mail**, [Profil](../user/settings/profile.md), [Utilisateurs et invitations](users.md#actions) | L’état, l’e-mail de test, votre adresse, les comptes | Aucun redémarrage. |
| **Journal** | La réponse exacte du serveur et le code | [Ce que dit le journal](#logs) : où le lire. |

### ⚙️ Problèmes de configuration {: #configuration-problems }

**Où : le fichier `.env` de LibreFolio.** L’onglet **E-mail** nomme la variable ; le code se trouve dans le journal, juste après `Starting LibreFolio`.
Après chaque correction : redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.

| Ce que vous voyez (onglet) | Code | Pourquoi | Que faire |
| --- | --- | --- | --- |
| `LIBREFOLIO_SMTP_HOST` n’est pas un nom de serveur valide… | `SMTP_HOST_INVALID` | Plus qu’un simple nom ou une adresse IP | `smtp.example.com`, et non `smtp://smtp.example.com`, `smtp.example.com:587` ou `user@smtp.example.com`. Le port va dans `LIBREFOLIO_SMTP_PORT` ; une adresse IPv6 s’écrit sans crochets. |
| `LIBREFOLIO_SMTP_TLS` doit valoir starttls, tls ou none. | `SMTP_TLS_INVALID` | Mot non autorisé | L’un des trois. Chiffrement dès le premier octet, port 465 : `tls`. |
| `LIBREFOLIO_SMTP_PORT` doit être un nombre entier de 1 à 65535. | `SMTP_PORT_INVALID` | Hors plage ou non numérique | Uniquement des chiffres, ou supprimez la ligne : le port du mode s’applique. |
| Le fichier du mot de passe indiqué par `LIBREFOLIO_SMTP_PASSWORD_FILE` ne peut pas être lu. | `SMTP_PASSWORD_UNREADABLE` | Le fichier n’existe pas à ce chemin (avec Docker, le chemin à l’intérieur du conteneur), l’utilisateur qui exécute LibreFolio ne peut pas le lire, il est vide ou ne contient que des espaces, n’est pas en UTF-8, ou dépasse 64 Kio | Le journal indique laquelle : système de fichiers ou chemin. |
| `LIBREFOLIO_SMTP_USER` est définie seule… (ou `LIBREFOLIO_SMTP_PASSWORD`) | `SMTP_CREDENTIALS_INCOMPLETE` | Un utilisateur sans mot de passe, ou l’inverse. Un mot de passe venant de `LIBREFOLIO_SMTP_PASSWORD_FILE` compte comme `LIBREFOLIO_SMTP_PASSWORD` | Les deux, ou aucun. |
| Il manque `LIBREFOLIO_SMTP_FROM`… | `SMTP_FROM_MISSING` | Obligatoire dès qu’un serveur est défini | Ajoutez l’expéditeur. |
| `LIBREFOLIO_SMTP_FROM` doit être une seule adresse… | `SMTP_FROM_INVALID` | Une liste ou un saut de ligne | Une seule adresse, avec ou sans nom : `LibreFolio <noreply@example.com>`. |
| `LIBREFOLIO_SMTP_REPLY_TO` doit être une seule adresse. | `SMTP_REPLY_TO_INVALID` | La même règle que pour l’expéditeur | Une seule adresse, ou supprimez la ligne. |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` doit être un nombre entier d’au moins 1. | `SMTP_MAX_PER_HOUR_INVALID` | Pas un nombre entier ≥ 1 | Uniquement des chiffres, au moins `1`. Pour arrêter l’envoi, supprimez plutôt `LIBREFOLIO_SMTP_HOST`. |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` doit être un nombre entier d’au moins 1. | `SIGNUP_EMAILS_PER_ADDRESS_INVALID` | Pas un nombre entier ≥ 1. Comme les autres, elle désactive l’e-mail jusqu’à correction ; le serveur démarre quand même | Uniquement des chiffres, au moins `1`, ou supprimez la ligne : valeur par défaut `20`. |

### 📤 Erreurs d’envoi {: #sending-errors }

L’e-mail de test, dans **Paramètres › Administration › E-mail**, indique pourquoi il n’est pas parti.
La réponse exacte du serveur se trouve dans le journal ([Ce que dit le journal](#logs)).

| Ce que vous voyez (e-mail de test) | Code | Pourquoi | Que faire — où |
| --- | --- | --- | --- |
| LibreFolio n’arrive pas à joindre le serveur SMTP… | `CONNECTION_FAILED` | Nom du serveur, port ou pare-feu. Le nom compte depuis l’endroit où LibreFolio s’exécute : dans un conteneur, `localhost` est le conteneur lui-même | **`.env`** : `LIBREFOLIO_SMTP_HOST`, `LIBREFOLIO_SMTP_PORT`. **Réseau** : un pare-feu qui refuse la connexion. |
| La connexion sécurisée a échoué… | `TLS_FAILED` | Le mode et le port ne vont pas ensemble ; avec `starttls`, le serveur ne propose pas le chiffrement ; certificat non valide ou non émis pour le nom présent dans `LIBREFOLIO_SMTP_HOST` (un certificat auto-signé, ou une IP à la place du nom, échoue) | **`.env`** : `starttls` avec 587, `tls` avec 465 ; dans `LIBREFOLIO_SMTP_HOST`, le nom du certificat. **Serveur SMTP** : un certificat valide. |
| Le serveur SMTP a refusé la connexion… | `AUTH_FAILED` | Utilisateur ou mot de passe erroné. Un serveur sans identification refuse l’identification | **`.env`** : l’utilisateur et le mot de passe ; chez un fournisseur, un mot de passe d’application. Serveur sans identification : supprimez les deux. |
| Le serveur SMTP a refusé l’adresse de l’expéditeur… | `SENDER_REFUSED` | Le serveur n’accepte que les adresses avec lesquelles votre compte peut envoyer. Sans utilisateur, il peut aussi exiger une identification | **`.env`** : dans `LIBREFOLIO_SMTP_FROM`, l’une de ces adresses, ou ajoutez l’identification. |
| Le serveur SMTP a refusé votre adresse. | `RECIPIENT_REFUSED` | L’adresse e-mail de votre compte. Sans identification, un serveur peut refuser de relayer vers d’autres domaines : la réponse dans le journal le précise | **Interface** : votre adresse dans [Profil](../user/settings/profile.md). **Serveur SMTP** : le relais. |
| Le serveur SMTP n’a pas répondu à temps. | `TIMEOUT` | Au-delà des 20 secondes que LibreFolio attend à chaque étape : un pare-feu qui abandonne la connexion sans la refuser, ou `starttls` sur le port 465 | **`.env`** : le couple mode/port. **Réseau** : le pare-feu. |
| Le serveur SMTP n’a pas accepté le message. | `SEND_FAILED` | Le serveur a refusé le message lui-même. Des lettres hors ASCII avant le `@`, comme `zoë@example.com`, demandent SMTPUTF8 : sans lui, l’e-mail ne quitte jamais LibreFolio et le journal indique `SMTPNotSupportedError` | **Journal** : la réponse du serveur en donne la raison. **Serveur SMTP** : SMTPUTF8, ou une adresse en ASCII. |
| La limite de … e-mails par heure est atteinte… (état), ou La limite d’e-mails par heure est atteinte : réessayez dans … min. (test) | `EMAIL_RATE_LIMITED` | Maximum de l’heure atteint | Patientez le nombre de minutes indiqué. Pour en autoriser davantage, **`.env`** : augmentez `LIBREFOLIO_SMTP_MAX_PER_HOUR` et redémarrez. |
| L’e-mail est désactivé ou ne fonctionne pas sur cette instance. | `EMAIL_UNAVAILABLE` | La configuration a changé depuis le chargement de l’onglet, par exemple après un redémarrage | **Interface** : l’onglet affiche maintenant l’état et son problème. |
| L’adresse de votre compte n’est pas une adresse e-mail valide. | `EMAIL_RECIPIENT_INVALID` | L’adresse e-mail de votre compte | **Interface** : corrigez-la dans [Profil](../user/settings/profile.md). |
| L’e-mail de test n’a pas pu être envoyé. | — | Aucune réponse connue, par exemple une erreur réseau | Rechargez la page et regardez le **journal**. |
| E-mail de test envoyé à votre adresse…, mais rien n’arrive | — | Le serveur a accepté le message : à partir de là, la distribution lui incombe. Un expéditeur sur un domaine qui n’autorise pas ce serveur peut être rejeté, ou classé comme indésirable, en chemin | Le dossier des indésirables, puis les **journaux du serveur ou du fournisseur**. |

**L’état de l’e-mail n’a pas pu être lu.** : l’onglet n’a pas joint le serveur. Rechargez ; si cela persiste, regardez le journal.

**Envoyer par e-mail**, dans les boîtes de dialogue d’invitation et de réinitialisation, indique pourquoi un lien n’est pas parti :

| Ce que vous voyez (boîte de dialogue) | Code | Pourquoi | Que faire — où |
| --- | --- | --- | --- |
| L’e-mail est désactivé ou ne fonctionne pas sur cette instance. | `EMAIL_UNAVAILABLE` | La configuration a changé depuis l’ouverture de la boîte de dialogue, par exemple après un redémarrage | **Interface** : [Paramètres › Administration › E-mail](email.md#email-tab). |
| Les e-mails ne peuvent pas contenir de lien : LIBREFOLIO_PUBLIC_URL n’est pas définie, ou ne peut pas commencer un lien. | `EMAIL_LINKS_UNAVAILABLE` | Le début des liens manque | **`.env`** : définissez `LIBREFOLIO_PUBLIC_URL`, puis redémarrez ([E-mails contenant un lien](email_flows.md#public-url)). |
| Ce lien ne fonctionne plus : créez-en un nouveau. | `EMAIL_LINK_INVALID` | Lien expiré, utilisé ou révoqué | **Interface** : créez un nouveau lien et envoyez celui-là. |
| Le compte n’est pas actif : activez-le avant de lui envoyer un lien de réinitialisation. | `EMAIL_ACCOUNT_INACTIVE` | Compte désactivé | **Interface** : **Réactiver** dans [Utilisateurs et invitations](users.md#actions) ; ou **ligne de commande** : `user activate` ([CLI](cli_tools.md)). Puis renvoyez le lien. |
| Indiquez l’adresse à laquelle envoyer l’invitation. | `EMAIL_RECIPIENT_REQUIRED` | L’invitation ne contient aucune adresse | **Interface** : saisissez-en une dans **Envoyer à**. |
| Ce n’est pas une seule adresse e-mail valide. | `EMAIL_RECIPIENT_INVALID` | Adresse non valide. Pour une réinitialisation, c’est celle du compte lui-même | **Interface** : corrigez **Envoyer à**. Pour la réinitialisation, copiez plutôt le lien. |
| La limite horaire d’e-mails est atteinte : réessayez dans … min. | `EMAIL_RATE_LIMITED` | Maximum de l’heure atteint | Patientez le nombre de minutes indiqué. Pour en autoriser davantage, **`.env`** : augmentez `LIBREFOLIO_SMTP_MAX_PER_HOUR` et redémarrez. |
| Le serveur SMTP a refusé l’adresse du destinataire. | `RECIPIENT_REFUSED` | L’adresse du lien : **Envoyer à** pour une invitation, l’adresse e-mail du compte pour une réinitialisation. Sans identification, un serveur peut refuser de relayer vers d’autres domaines | **Interface** : l’adresse. **Journal** : la réponse du serveur. **Serveur SMTP** : le relais. |
| Les autres messages de l’e-mail de test | `CONNECTION_FAILED`, `TLS_FAILED`, `AUTH_FAILED`, … | Comme dans le tableau ci-dessus | Comme dans le tableau ci-dessus. |
| L’e-mail n’a pas pu être envoyé. | — | Aucune réponse connue, par exemple une erreur réseau | Rechargez la page et regardez le **journal**. |

`EMAIL_RECIPIENT_NOT_ALLOWED` (une autre adresse pour un lien de réinitialisation) ne vient que de l’API : la boîte de dialogue ne le renvoie jamais.

### 📜 Ce que dit le journal {: #logs }

**Où le lire :**

| Installation | Commande ou fichier |
| --- | --- |
| Docker | `docker compose logs librefolio` |
| Sur l’hôte | `logs/librefolio.log` dans le dossier de données ([Structure du système de fichiers](filesystem.md)) ; le serveur l’affiche aussi dans la console |

À chaque démarrage, juste après `Starting LibreFolio`, le serveur vérifie la configuration, e-mail compris ([Vérifications au démarrage](configuration_security.md#startup-checks)) : une configuration inutilisable (les deux premières lignes ci-dessous), `none` vers un serveur hors de votre réseau local (une ligne), `LIBREFOLIO_PUBLIC_URL` manquante ou non valide (une ligne).
Aucune d’elles n’empêche le démarrage.
Les trois mêmes contrôles figurent dans **Paramètres › Administration › Sécurité**, relus à votre demande ; un constat renvoie à l’[onglet E-mail](email.md#email-tab) (voir « Sécurité » dans [Paramètres globaux](settings.md)).

**Démarrage et envoi**

| Le journal dit | Niveau | Quand |
| --- | --- | --- |
| `Email configuration cannot be used: email stays off` | `error` | Une variable ne peut pas être utilisée. Une fois par processus serveur, au démarrage, avec `variable`, `problem` (le code) et `reason` : la règle qu’elle enfreint, ou pourquoi le fichier de mot de passe ne peut pas être lu. |
| `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` | `error` | Au démarrage, après la ligne ci-dessus, avec `check` défini sur `email.smtp` : les vérifications au démarrage signalent le même problème. |
| `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | `warning` | Au démarrage, avec `check` défini sur `email.smtp_encryption` : `none` vers un serveur hors de votre réseau local, que la ligne nomme ([Notes de sécurité](#security)). |
| `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` | `info` | Au démarrage, avec `check` défini sur `email.links` : l’e-mail fonctionne, mais `LIBREFOLIO_PUBLIC_URL` n’est pas définie ([E-mails contenant un lien](email_flows.md#public-url)). |
| `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` | `warning` | Au démarrage, avec `check` défini sur `email.links` : l’e-mail fonctionne, mais la variable ne peut pas commencer un lien ([E-mails contenant un lien](email_flows.md#public-url)). |
| `Email sent` | `info` | Le serveur a accepté un e-mail ; `kind` indique lequel : `test`, `invite`, `password_reset`, `email_verification`, `email_changed` ou `email_change_confirmation`. |
| `Email not sent` | `warning` | Le serveur a refusé l’e-mail ou n’a pas répondu : `code`, comme dans [Erreurs d’envoi](#sending-errors), et `detail`, la réponse du serveur lui-même, l’indice le plus précis. |
| `Email not sent: the hourly limit of the instance is reached` | `warning` | La limite horaire a bloqué un e-mail ; `retry_after` est en secondes. |
| `Test email sent by an administrator` | `info` | Un e-mail de test est parti, avec `admin_id` et `language`. |
| `Link emailed by an administrator` | `info` | Un administrateur a envoyé un lien par e-mail : `admin_id`, `purpose` (`invite` ou `password_reset`), `token_id`, le `user_id` du compte pour un lien de réinitialisation, et `language`. |

**Mots de passe oubliés**

| Le journal dit | Niveau | Quand |
| --- | --- | --- |
| `Forgotten password: reset link emailed` | `info` | Un lien de réinitialisation est parti : `user_id`, `token_id` et `language`. |
| `Forgotten password: no active account matches, nothing sent` | `info` | Aucun compte actif n’a ce nom d’utilisateur ou cette adresse e-mail. Ce qui a été saisi n’est jamais journalisé. |
| `Forgotten password: the account had a reset link moments ago, nothing sent` | `info` | Les limites du compte : un lien de réinitialisation il y a moins de 5 minutes, ou 3 dans la dernière heure ; avec `user_id`. |
| `Forgotten password: an administrator's reset link is still live, nothing sent` | `info` | Une demande n’annule jamais un lien donné par un administrateur ; avec `user_id`. |
| `Forgotten password: the hourly limit of the instance is reached, nothing sent` | `warning` | La limite horaire a été atteinte après la réponse ; avec `user_id`. |
| `Forgotten password: the mailbox had reset emails moments ago, nothing sent` | `info` | Cette boîte aux lettres avait déjà 3 e-mails de réinitialisation dans la dernière heure, y compris ceux qui ne sont pas partis ; avec `user_id`. |
| `Forgotten password: another request won the race, nothing sent` | `info` | Deux demandes pour le compte au même moment : l’autre envoie l’e-mail ; avec `user_id`. |
| `Forgotten password: no email sent` | `warning` | L’e-mail ou `LIBREFOLIO_PUBLIC_URL` a cessé de fonctionner après la réponse, ou l’e-mail a été refusé : `reason` et `code` l’indiquent. Le lien créé est révoqué. |
| `Forgotten password: the request failed` | `error` | Une erreur inattendue, avec son type dans `error` et rien de plus : aucun détail de la demande n’atteint le journal. |

Chaque lien de réinitialisation laisse aussi une ligne `Password reset link created`, avec `user_id`, `token_id` et, si un administrateur l’a créé, `created_by_user_id`.

**Vérification de l’adresse e-mail**

| Le journal dit | Niveau | Quand |
| --- | --- | --- |
| `Registration waits for email verification` | `info` | Un nouveau compte attend son lien ; avec `user_id`. La ligne `User registered` de la même inscription a `waits_for_email` défini sur true. |
| `Verification email held: address limit or instance budget reached` | `info` | L’adresse avait déjà reçu ses `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` e-mails (20 par défaut) dans l’heure, ou la limite horaire de l’instance est épuisée : le compte attend sans son e-mail, et la page de connexion l’indique à son propriétaire ; avec `user_id`. |
| `Verification link emailed` | `info` | Un lien de vérification est parti : `user_id`, `token_id` et `language`. |
| `Verification email: not sent` | `warning` | L’e-mail d’une inscription n’est pas parti : `reason` et `code` en donnent la raison. La page avait annoncé que l’e-mail était en route : seule cette ligne indique qu’il n’est pas parti. Le compte attend toujours ; son propriétaire peut redemander le lien. |
| `Verification email: the account no longer waits, nothing sent` | `info` | Un administrateur a activé, désactivé ou supprimé le compte avant le départ de l’e-mail ; avec `user_id`. |
| `Verification email: the request failed` | `error` | Une erreur inattendue, avec son type dans `error` et le `user_id`, rien de plus. |
| `Login refused: email not verified` | `info` | Un compte en attente s’est connecté avec le bon mot de passe ; avec `user_id`. |
| `Verification resend refused: wrong credentials` | `warning` | Demande d’un nouveau lien de vérification avec un mot de passe erroné, ou pour un compte qui n’existe pas. Ni ce qui a été saisi ni l’adresse ne sont journalisés. |
| `Email verified` | `info` | Le propriétaire a confirmé sur la page du lien : le compte est actif ; `user_id` et `token_id`. |
| `Email verification refused: the link's email did not go out` | `info` | Confirmation avec un lien dont l’e-mail a été compté par LibreFolio comme non envoyé : le compte attend toujours, et **Renvoyer le lien** fonctionne. |
| `Email verification refused: the link was sent to another address` | `info` | L’adresse du compte a changé après l’envoi du lien : ce lien cesse de fonctionner. |

**Changement d’adresse e-mail**

| Le journal dit | Niveau | Quand |
| --- | --- | --- |
| `Email change notice sent to the previous address` | `info` | L’avis est parti à l’ancienne adresse. La ligne contient `user_id` et `language`, aucune des deux adresses. |
| `Email change notice: email is off, nothing sent` | `info` | L’e-mail est désactivé : rien à envoyer, rien d’anormal. |
| `Email change notice: past its limits, nothing sent` | `info` | Le compte, ou l’ancienne boîte aux lettres, avait déjà reçu 3 avis dans l’heure : le changement a été effectué, l’avis non. Avec `user_id`. |
| `Email change notice: the account no longer exists, nothing sent` | `info` | Le compte a été supprimé avant le départ de l’e-mail. |
| `Email change notice: not sent` | `warning` | L’e-mail est configuré mais ne peut pas être utilisé pour le moment, la limite horaire est atteinte, l’ancienne adresse n’est pas une adresse simple, ou l’envoi a échoué : `reason` et `code` l’indiquent. |
| `Email change notice: the request failed` | `error` | Une erreur inattendue, avec son type dans `error` et le `user_id`, rien de plus. |

Aucune de ces lignes ne contient le mot de passe SMTP, le contenu d’un e-mail, un lien ou sa partie secrète, ce que quelqu’un a saisi pour demander un lien de réinitialisation ou de vérification, ni l’adresse complète du destinataire : seulement son domaine, dans `recipient_domain`.
La réponse du serveur est masquée elle aussi, car elle cite souvent l’adresse refusée : `550 5.1.1 <***@example.com>: Recipient address rejected`.
L’avis de changement d’adresse e-mail ne nomme ni l’ancienne adresse ni la nouvelle.

---

## 🔒 Notes de sécurité {: #security }

- **`starttls` ne revient jamais au texte en clair.** Un serveur qui ne propose pas de chiffrement ne reçoit ni le mot de passe ni le message : l’e-mail de test échoue avec `TLS_FAILED`.
- **Le certificat est toujours vérifié**, avec `starttls` et avec `tls` : aucune option ne permet de l’ignorer.
- **`none` envoie tout en clair** : les messages, les liens et le mot de passe SMTP. Ne l’utilisez que pour un relais sur votre propre machine ou votre propre réseau. Vers tout autre serveur, Paramètres › Administration › E-mail affiche un avertissement : *Les e-mails, leurs liens et le mot de passe SMTP circulent en clair vers un serveur hors du réseau local* ; le journal de démarrage en affiche un aussi ([Ce que dit le journal](#logs)).
- **Gardez le mot de passe dans un fichier secret** (`LIBREFOLIO_SMTP_PASSWORD_FILE`) que seul l’utilisateur qui exécute LibreFolio peut lire, hors de `.env` et hors du dossier de données. Utilisez un mot de passe d’application, ou un compte réservé à LibreFolio, que vous pouvez révoquer séparément.
- **Les liens viennent uniquement de `LIBREFOLIO_PUBLIC_URL`**, jamais d’une requête : personne ne peut faire envoyer par LibreFolio à l’un de vos utilisateurs un lien vers un site tiers ([E-mails contenant un lien](email_flows.md#public-url)).
- **Un lien de vérification ne va qu’à l’adresse du compte lui-même**, et personne ne le voit, administrateur compris. **Renvoyer le lien** demande le mot de passe du compte, comme la connexion, et un nouveau lien désactive les précédents.
- **Les noms restent sur une seule ligne.** Le nom d’utilisateur, le nom de la personne qui invite et le nom de l’instance entrent dans un e-mail sur une seule ligne : les caractères de contrôle et les sauts de ligne deviennent des espaces, les contrôles bidirectionnels sont supprimés. Un nom d’utilisateur fabriqué ne peut ni ajouter des lignes à un e-mail ni déguiser son texte.
- **Aucun mot d’un inconnu dans un e-mail.** La réinitialisation du mot de passe, la vérification de l’adresse e-mail et l’avis de changement d’adresse peuvent être envoyés, par une personne qui n’est pas administrateur, à une adresse de son choix. Ces e-mails commencent par un simple « Bonjour, », sans le nom d’utilisateur, et l’avis ne montre aucune partie de la nouvelle adresse : LibreFolio ne résout pas les domaines, donc même la fin d’une adresse est choisie librement. Un lien de réinitialisation que vous envoyez par e-mail est rédigé de la même manière ; le nom d’utilisateur apparaît une fois le lien ouvert. Seuls l’e-mail de test et le lien de configuration de l’administrateur initial s’adressent au destinataire par son nom : c’est vous, ou la personne qui gère le serveur, qui les envoyez.
- **Les mots de passe oubliés ne révèlent à personne quels comptes existent** : la même réponse pour tout le monde, la recherche après la réponse, et des limites par adresse, par nom d’utilisateur ou adresse e-mail, par boîte aux lettres et par compte ([Mots de passe oubliés](email_flows.md#forgot-password)).
- **Changer l’adresse e-mail d’un compte demande son mot de passe actuel.** Sans cela, un instant dans la session de quelqu’un (un cookie de session volé, un ordinateur laissé déverrouillé) suffirait pour mettre sa propre adresse sur le compte, puis réinitialiser son mot de passe : la réinitialisation par e-mail n’existe qu’avec cette règle. Lorsque l’e-mail fonctionne, l’ancienne adresse reçoit aussi un avis ([Changements d’adresse e-mail](email_flows.md#email-change-notice)).
- **La limite horaire** plafonne ce que l’instance peut envoyer, quoi qu’il arrive : ne l’augmentez que dans la mesure de vos besoins.

??? info "🏠 Ce qui compte comme votre réseau local — quand l’avertissement apparaît"

    LibreFolio juge `LIBREFOLIO_SMTP_HOST` tel qu’il est écrit, sans résoudre le nom. Local signifie :

    - `localhost`, ou un nom sans point, comme un service Docker Compose (`smtp-relay`) ou une
      machine de votre réseau local ;
    - un nom se terminant par `.local`, `.lan`, `.home.arpa`, `.internal` ou `.localhost` ;
    - une adresse de bouclage, privée ou de lien local, comme `127.0.0.1`, `192.168.1.10` ou
      `fd00::25`, ou une adresse Tailscale (`100.64.0.0/10`, `fd7a:115c:a1e0::/48`).

    Tout autre serveur reçoit l’avertissement, même un serveur de votre réseau connu par un nom complet tel que
    `relay.example.com`. Un nom Tailscale comme `relay.tailnet.ts.net` le reçoit aussi, alors que son
    adresse `100.x` ne le reçoit pas.

---

## 🔗 Voir aussi

- 📄 **[E-mail](email.md)** — Où se trouve la configuration, les variables, exemples, …
- 📄 **[E-mail : liens et messages](email_flows.md)** — E-mails contenant un lien, Liens envoyés par un administrateur, Mots de passe oubliés, …
