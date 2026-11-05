# 🛠️ E-mail : quand cela ne fonctionne pas

Cette page traite des cas où les e-mails ne partent pas : les erreurs affichées par l’e-mail de test et les boîtes de dialogue, ce que dit le journal, et les notes de sécurité de la configuration SMTP.

La façon de configurer l’e-mail, avec l’onglet **Email** des Paramètres et son e-mail de test, est décrite dans [E-mail](email.md) ; les messages que LibreFolio envoie sont décrits dans [E-mail : liens et messages](email_flows.md).

---

## 🛠️ Quand cela ne fonctionne pas {: #troubleshooting }

Les problèmes sont de deux ordres :

- une variable que LibreFolio ne peut pas utiliser : l’état est **Ne fonctionne pas** dès l’ouverture de l’onglet ([Problèmes de configuration](#configuration-problems)) ;
- un serveur qui refuse l’e-mail ou ne répond pas : cela n’apparaît qu’au moment de l’envoi d’un e-mail ([Erreurs d’envoi](#sending-errors)).

Une configuration inutilisable désactive l’e-mail, rien de plus : le serveur démarre comme d’habitude et tout le reste fonctionne. Le journal de démarrage nomme déjà la variable en cause, juste après `Starting LibreFolio`, et l’onglet fait de même ([Ce que dit le journal](#logs)).

### ⚙️ Problèmes de configuration {: #configuration-problems }

L’onglet nomme la variable en cause ; le code se trouve dans le journal.

| Ce que dit l’onglet | Code | À vérifier |
| --- | --- | --- |
| `LIBREFOLIO_SMTP_HOST` n’est pas un nom de serveur valide… | `SMTP_HOST_INVALID` | Uniquement le nom ou l’adresse IP : `smtp.example.com`, et non `smtp://smtp.example.com`, `smtp.example.com:587` ou `user@smtp.example.com`. Le port se met dans `LIBREFOLIO_SMTP_PORT` ; une adresse IPv6 s’écrit sans crochets. |
| `LIBREFOLIO_SMTP_TLS` doit être starttls, tls ou none. | `SMTP_TLS_INVALID` | L’un des trois mots. Pour un chiffrement dès le premier octet, sur le port 465, le mot est `tls`. |
| `LIBREFOLIO_SMTP_PORT` doit être un nombre entier de 1 à 65535. | `SMTP_PORT_INVALID` | Uniquement des chiffres, ou aucune ligne du tout pour utiliser le port du mode. |
| Le fichier de mot de passe indiqué par `LIBREFOLIO_SMTP_PASSWORD_FILE` ne peut pas être lu. | `SMTP_PASSWORD_UNREADABLE` | Le journal en donne la raison : le fichier n’existe pas à ce chemin (avec Docker, le chemin à l’intérieur du conteneur), l’utilisateur qui exécute LibreFolio ne peut pas le lire, ou il est vide ou ne contient que des espaces, n’est pas du texte UTF-8 ou dépasse 64 Kio. |
| `LIBREFOLIO_SMTP_USER` est défini seul… (ou `LIBREFOLIO_SMTP_PASSWORD`) | `SMTP_CREDENTIALS_INCOMPLETE` | Définissez à la fois l’utilisateur et le mot de passe, ou ni l’un ni l’autre. Un mot de passe fourni par `LIBREFOLIO_SMTP_PASSWORD_FILE` est signalé comme `LIBREFOLIO_SMTP_PASSWORD`. |
| `LIBREFOLIO_SMTP_FROM` est manquant… | `SMTP_FROM_MISSING` | Ajoutez l’expéditeur : il est obligatoire dès qu’un serveur est défini. |
| `LIBREFOLIO_SMTP_FROM` doit être une seule adresse… | `SMTP_FROM_INVALID` | Une seule adresse, avec ou sans nom, comme `LibreFolio <noreply@example.com>` : pas de liste, pas de saut de ligne. |
| `LIBREFOLIO_SMTP_REPLY_TO` doit être une seule adresse. | `SMTP_REPLY_TO_INVALID` | La même règle que pour l’expéditeur, ou supprimez la ligne. |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` doit être un nombre entier d’au moins 1. | `SMTP_MAX_PER_HOUR_INVALID` | Uniquement des chiffres, au moins `1`. Pour arrêter l’envoi, supprimez plutôt `LIBREFOLIO_SMTP_HOST`. |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` doit être un nombre entier d’au moins 1. | `SIGNUP_EMAILS_PER_ADDRESS_INVALID` | Uniquement des chiffres, au moins `1`, ou aucune ligne du tout pour la valeur par défaut de `20`. Comme les autres, elle désactive l’e-mail jusqu’à correction ; le serveur démarre quand même. |

### 📤 Erreurs d’envoi {: #sending-errors }

L’e-mail de test indique pourquoi il n’est pas parti. Pour la réponse du serveur lui-même, consultez le journal.

| Ce que dit l’onglet | Code | À vérifier |
| --- | --- | --- |
| LibreFolio ne peut pas joindre le serveur SMTP… | `CONNECTION_FAILED` | Le nom du serveur, tel qu’il est vu depuis l’endroit où LibreFolio s’exécute (dans un conteneur, `localhost` est le conteneur lui-même), le port, et un pare-feu qui refuse la connexion. |
| La connexion sécurisée a échoué… | `TLS_FAILED` | Le mode et le port vont ensemble : `starttls` avec 587, `tls` avec 465. Avec `starttls`, le serveur doit proposer le chiffrement. Son certificat doit être valide et émis pour le nom présent dans `LIBREFOLIO_SMTP_HOST` : un certificat auto-signé, ou une adresse IP au lieu du nom, échoue au contrôle. |
| Le serveur SMTP a refusé l’identification… | `AUTH_FAILED` | L’utilisateur et le mot de passe : chez un fournisseur, un mot de passe d’application. Un serveur qui accepte le courrier sans identification refuse l’identification : supprimez l’utilisateur et le mot de passe. |
| Le serveur SMTP a refusé l’adresse de l’expéditeur… | `SENDER_REFUSED` | Le serveur n’accepte que les adresses avec lesquelles votre compte peut envoyer : utilisez l’une d’elles dans `LIBREFOLIO_SMTP_FROM`. Sans utilisateur, le serveur peut aussi exiger une identification. |
| Le serveur SMTP a refusé votre adresse. | `RECIPIENT_REFUSED` | L’adresse e-mail de votre compte, dans [Profil](../user/settings/profile.md). Sans identification, un serveur peut refuser de transmettre le courrier vers d’autres domaines : sa réponse dans le journal le précise. |
| Le serveur SMTP n’a pas répondu à temps. | `TIMEOUT` | LibreFolio attend jusqu’à 20 secondes à chaque étape. Un pare-feu qui abandonne la connexion sans la refuser aboutit ici, et `starttls` sur le port 465 peut aussi le faire. |
| Le serveur SMTP n’a pas pris le message. | `SEND_FAILED` | Le serveur a refusé le message lui-même : sa réponse dans le journal en donne la raison. Une adresse contenant des lettres hors ASCII avant le `@`, comme `zoë@example.com`, nécessite un serveur qui prend en charge SMTPUTF8 : sans cela, l’e-mail ne quitte jamais LibreFolio, et le journal indique `SMTPNotSupportedError`. |
| La limite horaire de … e-mails est atteinte… (état), ou La limite horaire d’e-mails est atteinte : réessayez dans … min. (test) | `EMAIL_RATE_LIMITED` | Patientez le nombre de minutes indiqué. Pour en autoriser davantage, augmentez `LIBREFOLIO_SMTP_MAX_PER_HOUR` et redémarrez. |
| L’e-mail est désactivé ou ne fonctionne pas sur cette instance. | `EMAIL_UNAVAILABLE` | La configuration a changé depuis le chargement de l’onglet, par exemple après un redémarrage : l’onglet affiche maintenant l’état et son problème. |
| L’adresse de votre compte n’est pas une adresse e-mail valide. | `EMAIL_RECIPIENT_INVALID` | Corrigez l’adresse e-mail de votre compte dans [Profil](../user/settings/profile.md). |
| L’e-mail de test n’a pas pu être envoyé. | — | Aucune réponse connue n’est revenue, par exemple après une erreur réseau : rechargez la page et consultez le journal. |
| E-mail de test envoyé à votre adresse…, mais rien n’arrive | — | Le serveur a accepté le message : à partir de là, la distribution lui incombe. Regardez dans le dossier des indésirables, puis dans les journaux du serveur ou de votre fournisseur. Un expéditeur sur un domaine qui n’autorise pas ce serveur à envoyer pour lui peut être rejeté, ou classé comme indésirable, en chemin. |

**L’état de l’e-mail n’a pas pu être lu.** signifie que l’onglet n’a pas pu joindre le serveur : rechargez la page et, si cela persiste, consultez le journal.

**Envoyer par e-mail**, dans les boîtes de dialogue d’invitation et de réinitialisation, indique pourquoi un lien n’est pas parti :

| Ce que dit la boîte de dialogue | Code | Que faire |
| --- | --- | --- |
| L’e-mail est désactivé ou ne fonctionne pas sur cette instance. | `EMAIL_UNAVAILABLE` | La configuration a changé depuis l’ouverture de la boîte de dialogue, par exemple après un redémarrage : consultez [Paramètres › Administration › Email](email.md#email-tab). |
| Les e-mails ne peuvent pas contenir de liens : LIBREFOLIO_PUBLIC_URL n’est pas défini, ou ne peut pas servir de base à un lien. | `EMAIL_LINKS_UNAVAILABLE` | Définissez-la, puis redémarrez : voir [E-mails avec un lien](email_flows.md#public-url). |
| Ce lien ne fonctionne plus : créez-en un nouveau. | `EMAIL_LINK_INVALID` | Le lien a expiré, a été utilisé ou a été révoqué : créez un nouveau lien et envoyez celui-là. |
| Le compte n’est pas actif : activez-le avant de lui envoyer un lien de réinitialisation. | `EMAIL_ACCOUNT_INACTIVE` | **Réactivez** le compte dans [Utilisateurs et invitations](users.md#actions), ou exécutez `user activate` sur la [ligne de commande](cli_tools.md), puis renvoyez le lien. |
| Saisissez l’adresse à laquelle envoyer l’invitation. | `EMAIL_RECIPIENT_REQUIRED` | L’invitation ne contient aucune adresse : saisissez-en une dans **Envoyer à**. |
| Ce n’est pas une adresse e-mail valide. | `EMAIL_RECIPIENT_INVALID` | Corrigez l’adresse dans **Envoyer à**. Pour un lien de réinitialisation, l’adresse du compte lui-même n’est pas valide : copiez plutôt le lien. |
| La limite horaire d’e-mails est atteinte : réessayez dans … min. | `EMAIL_RATE_LIMITED` | Patientez le nombre de minutes indiqué. Pour en autoriser davantage, augmentez `LIBREFOLIO_SMTP_MAX_PER_HOUR` et redémarrez. |
| Le serveur SMTP a refusé l’adresse du destinataire. | `RECIPIENT_REFUSED` | L’adresse à laquelle le lien a été envoyé : celle dans **Envoyer à** pour une invitation, l’adresse e-mail du compte pour un lien de réinitialisation. Sans identification, un serveur peut refuser de transmettre le courrier vers d’autres domaines : sa réponse dans le journal le précise. |
| Les autres messages de l’e-mail de test | `CONNECTION_FAILED`, `TLS_FAILED`, `AUTH_FAILED`, … | Comme dans le tableau ci-dessus. |
| L’e-mail n’a pas pu être envoyé. | — | Aucune réponse connue n’est revenue, par exemple après une erreur réseau : rechargez la page et consultez le journal. |

`EMAIL_RECIPIENT_NOT_ALLOWED`, une autre adresse pour un lien de réinitialisation, ne vient que de l’API : la boîte de dialogue ne renvoie aucun de ces codes.

### 📜 Ce que dit le journal {: #logs }

Le journal est le fichier `logs/librefolio.log` du dossier de données, et le serveur l’affiche aussi dans sa console : `docker compose logs librefolio` avec Docker ([Structure du système de fichiers](filesystem.md)).

À chaque démarrage, juste après `Starting LibreFolio`, le serveur vérifie sa configuration, e-mail compris ([Contrôles au démarrage](configuration_security.md#startup-checks)). Une configuration inutilisable y apparaît en deux lignes, les deux premières ci-dessous ; `none` vers un serveur hors de votre réseau local, et un `LIBREFOLIO_PUBLIC_URL` manquant ou invalide, chacun sur une ligne. Aucune d’elles n’empêche le démarrage. Les mêmes trois contrôles figurent dans l’onglet **Sécurité** de **Paramètres › Administration**, relus à votre demande, où un constat renvoie à l’[onglet Email](email.md#email-tab) (voir « Sécurité » dans [Paramètres globaux](settings.md)).

| Ce que dit le journal | Niveau | Quand |
| --- | --- | --- |
| `Email configuration cannot be used: email stays off` | `error` | Une variable ne peut pas être utilisée. Chaque processus serveur l’enregistre une fois, au démarrage, avec `variable`, `problem` (le code) et `reason` : la règle qu’elle enfreint, ou pourquoi le fichier de mot de passe ne peut pas être lu. |
| `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` | `error` | Au démarrage, après la ligne ci-dessus, avec `check` défini sur `email.smtp` : les contrôles au démarrage signalent le même problème. |
| `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | `warning` | Au démarrage, avec `check` défini sur `email.smtp_encryption` : `none` vers un serveur hors de votre réseau local, que la ligne nomme ([Notes de sécurité](#security)). |
| `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` | `info` | Au démarrage, avec `check` défini sur `email.links` : l’e-mail fonctionne, mais `LIBREFOLIO_PUBLIC_URL` n’est pas défini ([E-mails avec un lien](email_flows.md#public-url)). |
| `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` | `warning` | Au démarrage, avec `check` défini sur `email.links` : l’e-mail fonctionne, mais la variable ne peut pas servir de base à un lien ([E-mails avec un lien](email_flows.md#public-url)). |
| `Email sent` | `info` | Le serveur a accepté un e-mail ; `kind` indique lequel : `test`, `invite`, `password_reset`, `email_verification`, `email_changed` ou `email_change_confirmation`. |
| `Email not sent` | `warning` | Le serveur a refusé l’e-mail ou n’a pas répondu : `code`, comme dans [Erreurs d’envoi](#sending-errors), et `detail`, la réponse du serveur lui-même, l’indice le plus précis. |
| `Email not sent: the hourly limit of the instance is reached` | `warning` | La limite horaire a bloqué un e-mail ; `retry_after` est en secondes. |
| `Test email sent by an administrator` | `info` | Un e-mail de test est parti, avec `admin_id` et `language`. |
| `Link emailed by an administrator` | `info` | Un administrateur a envoyé un lien par e-mail : `admin_id`, `purpose` (`invite` ou `password_reset`), `token_id`, le `user_id` du compte pour un lien de réinitialisation, et `language`. |
| `Forgotten password: reset link emailed` | `info` | Un lien de réinitialisation est parti pour un mot de passe oublié : `user_id`, `token_id` et `language`. |
| `Forgotten password: no active account matches, nothing sent` | `info` | Aucun compte actif ne correspond à ce nom d’utilisateur ou à cette adresse e-mail. Ce qui a été saisi n’est jamais journalisé. |
| `Forgotten password: the account had a reset link moments ago, nothing sent` | `info` | Les limites propres au compte : un lien de réinitialisation il y a moins de 5 minutes, ou 3 dans la dernière heure ; avec `user_id`. |
| `Forgotten password: an administrator's reset link is still live, nothing sent` | `info` | Une demande n’annule jamais un lien qu’un administrateur a donné au compte ; avec `user_id`. |
| `Forgotten password: the hourly limit of the instance is reached, nothing sent` | `warning` | La limite horaire a été atteinte après la réponse ; avec `user_id`. |
| `Forgotten password: the mailbox had reset emails moments ago, nothing sent` | `info` | Cette boîte aux lettres avait déjà 3 e-mails de réinitialisation dans la dernière heure, y compris ceux qui ne sont pas partis ; avec `user_id`. |
| `Forgotten password: another request won the race, nothing sent` | `info` | Deux demandes pour le compte au même moment : l’autre envoie l’e-mail ; avec `user_id`. |
| `Forgotten password: no email sent` | `warning` | L’e-mail ou `LIBREFOLIO_PUBLIC_URL` a cessé de fonctionner après la réponse, ou l’e-mail a été refusé : `reason` et `code` l’indiquent. Un lien créé pour cela est révoqué. |
| `Forgotten password: the request failed` | `error` | Une erreur inattendue, avec son type dans `error` et rien de plus : aucun détail de la demande n’atteint le journal. |
| `Registration waits for email verification` | `info` | Un nouveau compte attend son lien ; avec `user_id`. La ligne `User registered` de la même inscription a `waits_for_email` défini sur true. |
| `Verification email held: address limit or instance budget reached` | `info` | L’adresse de l’inscription avait déjà reçu ses `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` e-mails (20 par défaut) dans l’heure, ou la limite horaire de l’instance est épuisée : le compte attend sans son e-mail, et la page de connexion l’indique à son propriétaire ; avec `user_id`. |
| `Verification link emailed` | `info` | Un lien de vérification est parti : `user_id`, `token_id` et `language`. |
| `Verification email: not sent` | `warning` | L’e-mail d’une inscription n’est pas parti : `reason` et `code` en donnent la raison. La page avait annoncé que l’e-mail était en route, donc seule cette ligne indique qu’il ne l’était pas. Le compte attend toujours, et son propriétaire peut redemander le lien. |
| `Verification email: the account no longer waits, nothing sent` | `info` | Un administrateur a activé, désactivé ou supprimé le compte avant le départ de son e-mail ; avec `user_id`. |
| `Verification email: the request failed` | `error` | Une erreur inattendue, avec son type dans `error` et le `user_id`, rien de plus. |
| `Login refused: email not verified` | `info` | Un compte en attente a tenté de se connecter avec le bon mot de passe ; avec `user_id`. |
| `Verification resend refused: wrong credentials` | `warning` | Quelqu’un a demandé un nouveau lien de vérification avec un mot de passe erroné, ou pour un compte qui n’existe pas. Ni ce qui a été saisi ni l’adresse ne sont journalisés. |
| `Email verified` | `info` | Le propriétaire a confirmé sur la page du lien : le compte est actif ; `user_id` et `token_id`. |
| `Email verification refused: the link's email did not go out` | `info` | Quelqu’un a confirmé avec un lien dont l’e-mail a été compté par LibreFolio comme non envoyé : le compte attend toujours, et **Renvoyer le lien** fonctionne. |
| `Email verification refused: the link was sent to another address` | `info` | L’adresse du compte a changé après l’envoi du lien : ce lien cesse de fonctionner. |
| `Email change notice sent to the previous address` | `info` | L’avis est parti à l’ancienne adresse. La ligne contient `user_id` et `language`, et aucune des deux adresses. |
| `Email change notice: email is off, nothing sent` | `info` | L’e-mail est désactivé : rien à envoyer, et rien d’anormal. |
| `Email change notice: past its limits, nothing sent` | `info` | Le compte, ou l’ancienne boîte aux lettres, avait déjà reçu 3 avis dans l’heure : le changement a été effectué, l’avis non. Avec `user_id`. |
| `Email change notice: the account no longer exists, nothing sent` | `info` | Le compte a été supprimé avant le départ de l’e-mail. |
| `Email change notice: not sent` | `warning` | L’e-mail est configuré mais ne peut pas être utilisé pour le moment, la limite horaire est atteinte, l’ancienne adresse n’est pas une adresse simple, ou l’envoi a échoué : `reason` et `code` l’indiquent. |
| `Email change notice: the request failed` | `error` | Une erreur inattendue, avec son type dans `error` et le `user_id`, rien de plus. |

Chaque lien de réinitialisation laisse aussi une ligne `Password reset link created`, avec `user_id`, `token_id` et, lorsqu’un administrateur l’a créé, `created_by_user_id`.

Aucune de ces lignes ne contient le mot de passe SMTP, le contenu d’un e-mail, un lien ou sa partie secrète, ce que quelqu’un a saisi pour demander un lien de réinitialisation ou un nouveau lien de vérification, ni l’adresse complète du destinataire : seulement son domaine, dans `recipient_domain`. Les serveurs citent souvent l’adresse qu’ils refusent, leur réponse est donc masquée elle aussi, par exemple `550 5.1.1 <***@example.com>: Recipient address rejected`. L’avis de changement d’adresse e-mail ne nomme ni l’ancienne adresse ni la nouvelle.

---

## 🔒 Notes de sécurité {: #security }

- **`starttls` ne fait jamais de fallback vers le texte en clair.** Un serveur qui ne propose pas de chiffrement ne reçoit ni le mot de passe ni le message : l’e-mail de test échoue avec `TLS_FAILED`.
- **Le certificat est toujours vérifié**, avec `starttls` et avec `tls` : aucune option ne permet d’ignorer le contrôle.
- **`none` envoie tout en clair** : les messages, leurs liens et le mot de passe SMTP. Réservez-le à un relais sur votre propre machine ou votre propre réseau. Vers tout autre serveur, Paramètres › Administration › Email affiche un avertissement : *Les e-mails, leurs liens et le mot de passe SMTP circulent sans chiffrement vers un serveur hors du réseau local* ; le journal de démarrage en affiche un aussi ([Ce que dit le journal](#logs)).
- **Gardez le mot de passe dans un fichier secret** (`LIBREFOLIO_SMTP_PASSWORD_FILE`) que seul l’utilisateur qui exécute LibreFolio peut lire, hors de `.env` et hors du dossier de données. Utilisez un mot de passe d’application, ou un compte réservé à LibreFolio, que vous pouvez révoquer séparément.
- **Les liens viennent uniquement de `LIBREFOLIO_PUBLIC_URL`**, jamais d’une requête : personne ne peut faire envoyer par LibreFolio à l’un de vos utilisateurs un lien vers un site appartenant à un tiers ([E-mails avec un lien](email_flows.md#public-url)).
- **Un lien de vérification ne va qu’à l’adresse du compte lui-même**, et personne ne le voit, administrateur compris. **Renvoyer le lien** demande le mot de passe du compte, comme la connexion, et un nouveau lien invalide les anciens.
- **Les noms restent sur une seule ligne.** Un nom d’utilisateur, le nom de la personne qui invite ou le nom de l’instance est écrit dans un e-mail sur une seule ligne : les caractères de contrôle et les sauts de ligne deviennent des espaces, et les caractères qui réordonnent le texte (contrôles bidirectionnels) sont supprimés. Un nom d’utilisateur fabriqué ne peut ni ajouter ses propres lignes à un e-mail ni déguiser son texte.
- **Aucun mot d’un inconnu dans un e-mail.** Une réinitialisation de mot de passe, une vérification d’adresse e-mail et l’avis de changement d’adresse e-mail peuvent être envoyés, par une personne qui n’est pas administrateur, à une adresse de son choix. Ces e-mails commencent par un simple « Bonjour, », sans le nom d’utilisateur, et l’avis ne montre aucune partie de la nouvelle adresse : LibreFolio ne résout pas les domaines, donc même la fin d’un domaine est choisie librement. Un lien de réinitialisation que vous envoyez par e-mail est rédigé de la même manière. Le nom d’utilisateur apparaît toutefois une fois le lien ouvert. Seuls l’e-mail de test et le lien de configuration de l’administrateur initial s’adressent au destinataire par son nom : c’est vous, ou la personne qui gère le serveur, qui les envoyez.
- **Les mots de passe oubliés ne révèlent à personne quels comptes existent** : la même réponse pour tout le monde, la recherche après la réponse, et des limites par adresse, par nom d’utilisateur ou adresse e-mail, par boîte aux lettres et par compte ([Mots de passe oubliés](email_flows.md#forgot-password)).
- **Changer l’adresse e-mail d’un compte demande son mot de passe actuel.** Sans cela, un instant dans la session de quelqu’un (un cookie de session volé, un ordinateur laissé déverrouillé) suffirait pour mettre sa propre adresse sur le compte, puis réinitialiser son mot de passe depuis celle-ci : la réinitialisation par e-mail n’a été rendue possible qu’avec cette règle. Lorsque l’e-mail fonctionne, l’ancienne adresse reçoit aussi un avis ([Changements d’adresse e-mail](email_flows.md#email-change-notice)).
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
- 📄 **[E-mail : liens et messages](email_flows.md)** — E-mails avec un lien, Liens envoyés par un administrateur, Mots de passe oubliés, …
